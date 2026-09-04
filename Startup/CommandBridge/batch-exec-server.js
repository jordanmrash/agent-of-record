#!/usr/bin/env node
/* ============================================================================
 *  Cowork Command Bridge -- hardened batch-only MCP server   v1.1.0
 *  C:\Users\YOURUSER\Documents\COPILOT_COWORK\Startup\CommandBridge\batch-exec-server.js
 *
 *  Replaces the unrestricted `mcp-server-commands` package behind port 8933.
 *
 *  ONE tool:  run_batch_file  { "file": "<relative path under CommandJobs>" }
 *
 *  The caller CANNOT supply: a command, arguments, an executable, an
 *  interpreter, a working directory, environment variables, an output
 *  directory, a timeout override, or an elevation option. The only
 *  caller-controlled value is a RELATIVE filename. Absolute, drive-qualified,
 *  UNC and environment-variable paths are refused outright.
 *
 *  LAYOUT
 *    Scripts       COPILOT_COWORK\CommandJobs\           (.bat / .cmd only)
 *    Logs          COPILOT_COWORK\CommandJobs\Logs\
 *    Deliverables  COPILOT_COWORK\Outputs\<YYYY-MM-DD - Task Name>\
 *
 *  OUTPUT DESTINATION
 *    The server NEVER invents or substitutes an output folder. The approved
 *    batch file declares its own destination on a directive line:
 *
 *        REM COWORK_OUTPUT: C:\Users\YOURUSER\Documents\COPILOT_COWORK\Outputs\2026-08-17 - Task Name
 *
 *    The server reads that directive, verifies it canonicalises under
 *    COPILOT_COWORK\Outputs, creates it if absent, and exposes it to the
 *    script as %COWORK_JOB_OUTPUT%. If the directive is missing the job still
 *    runs, with COWORK_JOB_OUTPUT left pointing at the Outputs root and no
 *    folder created. If the directive is present but resolves outside Outputs,
 *    the job is REFUSED rather than silently redirected.
 *
 *  Zero npm dependencies. Speaks MCP JSON-RPC 2.0 over newline-delimited
 *  stdio directly. Nothing is fetched from the network at start time.
 * ==========================================================================*/

'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn, spawnSync } = require('child_process');

/* ---------------------------------------------------------------- config -- */

const COWORK_ROOT  = 'C:\\Users\\YOURUSER\\Documents\\COPILOT_COWORK';
const JOB_ROOT_RAW = path.join(COWORK_ROOT, 'CommandJobs');
const LOG_DIR      = path.join(JOB_ROOT_RAW, 'Logs');
const OUTPUT_ROOT  = path.join(COWORK_ROOT, 'Outputs');

const TIMEOUT_MS     = 300 * 1000;        // fixed; no caller override
const MAX_STDOUT     = 5 * 1024 * 1024;
const MAX_STDERR     = 5 * 1024 * 1024;
const ALLOWED_EXT    = new Set(['.bat', '.cmd']);
const MAX_SCAN_FILES = 20000;
const MAX_DIRECTIVE_BYTES = 256 * 1024;   // how much of a script we read to find the directive

const SERVER_NAME      = 'cowork-batch-exec';
const SERVER_VERSION   = '1.1.0';
const DEFAULT_PROTOCOL = '2025-06-18';

/* Maximum concurrent executions: 1, enforced process-wide. */
let RUNNING = false;

/* --------------------------------------------------------------- helpers -- */

function ensureDirs() {
  for (const d of [JOB_ROOT_RAW, LOG_DIR, OUTPUT_ROOT]) {
    try { fs.mkdirSync(d, { recursive: true }); } catch (_) { /* non-fatal */ }
  }
}

function realOf(p) { return fs.realpathSync.native(p); }
function realJobRoot()   { return realOf(JOB_ROOT_RAW); }
function realOutputRoot() { return realOf(OUTPUT_ROOT); }

function stamp(d) {
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-` +
         `${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}

/* True when `child` is the same as, or nested inside, `parent`.
 * path.relative on canonicalised paths -- NOT a string-prefix test, so
 * "...\CommandJobsEvil" cannot masquerade as "...\CommandJobs". */
function isInside(parent, child) {
  const rel = path.relative(parent, child);
  if (rel === '') return true;
  if (rel.startsWith('..')) return false;
  if (path.isAbsolute(rel)) return false;
  return true;
}

class RejectError extends Error {
  constructor(reason, detail) {
    super(reason);
    this.reason = reason;
    this.detail = detail || null;
  }
}

/* ------------------------------------------------------- path validation -- */
/*
 * The caller may supply ONLY a relative path under CommandJobs.
 * Rejected, before any process exists:
 *   non-string / empty / oversized / NUL bytes
 *   ABSOLUTE paths            (C:\..., \foo, /foo)
 *   DRIVE-QUALIFIED paths     (C:\..., C:foo)
 *   UNC and network paths     (\\server\share, //server, \\?\, \\.\)
 *   URL-style paths           (file://, http://)
 *   environment-variable paths (%VAR%, $env:VAR, ${VAR}, ~)
 *   colons in any position    -> blocks alternate data streams (file.bat:ads)
 *   shell metacharacters      (& | < > ^ " ' ` * ? newline tab)
 *   .. traversal, textual and post-canonicalisation
 *   extensions other than .bat / .cmd, checked on the CANONICAL path
 *   nonexistent paths, directories, non-regular files
 *   symlinks/junctions whose real target escapes CommandJobs
 *   anything inside CommandJobs\Logs
 */
function validateBatchPath(input) {
  if (typeof input !== 'string')
    throw new RejectError('file must be a string');

  const raw = input.trim();

  if (raw.length === 0)   throw new RejectError('file must not be empty');
  if (raw.length > 240)   throw new RejectError('file path is too long');
  if (raw.includes('\0')) throw new RejectError('file contains a NUL byte');

  // --- environment-variable expansion attempts ------------------------------
  if (raw.includes('%'))
    throw new RejectError('environment-variable paths are not permitted', raw);
  if (/\$env:/i.test(raw) || /\$\{/.test(raw) || /\$[A-Za-z_]/.test(raw))
    throw new RejectError('environment-variable paths are not permitted', raw);
  if (raw.startsWith('~'))
    throw new RejectError('home-relative paths are not permitted', raw);

  // --- colons: no drive qualifiers, no alternate data streams ---------------
  // A relative path has no legitimate use for ':' at all.
  if (raw.includes(':'))
    throw new RejectError(
      'colons are not permitted (blocks drive-qualified paths and alternate data streams)', raw);

  const slashed = raw.replace(/\//g, '\\');

  // --- UNC / device / network paths ------------------------------------------
  if (slashed.startsWith('\\\\'))
    throw new RejectError('UNC and network paths are not permitted', raw);
  if (/^[a-z]+:\/\//i.test(raw))
    throw new RejectError('URL-style paths are not permitted', raw);

  // --- absolute paths of every flavour ----------------------------------------
  // ':' is already refused above, so this catches root-relative "\foo" / "/foo".
  if (slashed.startsWith('\\'))
    throw new RejectError('absolute paths are not permitted; supply a path relative to CommandJobs', raw);
  if (path.isAbsolute(raw) || path.win32.isAbsolute(slashed))
    throw new RejectError('absolute paths are not permitted; supply a path relative to CommandJobs', raw);

  // --- shell metacharacters ----------------------------------------------------
  if (/[&|<>^"'`\r\n\t*?]/.test(raw))
    throw new RejectError('file contains illegal characters', raw);

  // --- textual traversal --------------------------------------------------------
  if (slashed.split('\\').some(seg => seg === '..'))
    throw new RejectError('.. traversal is not permitted', raw);

  const root = realJobRoot();
  const candidate = path.resolve(root, slashed);

  // Cheap pre-canonicalisation containment check.
  if (!isInside(root, candidate))
    throw new RejectError('path resolves outside CommandJobs', candidate);

  // --- existence and type --------------------------------------------------------
  let lst;
  try { lst = fs.lstatSync(candidate); }
  catch (_) { throw new RejectError('file does not exist', candidate); }

  if (lst.isDirectory())
    throw new RejectError('path is a directory, not a batch file', candidate);

  // --- canonicalise, resolving every symlink and junction in the chain -----------
  let real;
  try { real = realOf(candidate); }
  catch (_) { throw new RejectError('file could not be canonicalised', candidate); }

  // Authoritative containment check: real target vs real root.
  if (!isInside(root, real))
    throw new RejectError(
      'file resolves outside CommandJobs (symlink or junction escape)', real);

  const st = fs.statSync(real);
  if (!st.isFile())
    throw new RejectError('target is not a regular file', real);

  // --- extension, checked on the CANONICAL path ------------------------------------
  const ext = path.extname(real).toLowerCase();
  if (!ALLOWED_EXT.has(ext))
    throw new RejectError(`only .bat and .cmd may be executed (got "${ext || 'none'}")`, real);

  // --- the log store is not an execution source -------------------------------------
  let realLogs;
  try { realLogs = realOf(LOG_DIR); } catch (_) { realLogs = LOG_DIR; }
  if (isInside(realLogs, real))
    throw new RejectError('scripts may not be executed from the Logs directory', real);

  return real;
}

/* --------------------------------------------- approved output directive -- */
/*
 * Reads  REM COWORK_OUTPUT: <path>   (or ::  or  = ) from the approved script.
 * The MCP caller cannot influence this -- it lives in the file Jordan approved.
 * Returns { dir, declared, created } or throws RejectError.
 */
function resolveApprovedOutput(realScriptPath) {
  let text = '';
  try {
    const fd = fs.openSync(realScriptPath, 'r');
    const buf = Buffer.alloc(MAX_DIRECTIVE_BYTES);
    const n = fs.readSync(fd, buf, 0, MAX_DIRECTIVE_BYTES, 0);
    fs.closeSync(fd);
    text = buf.subarray(0, n).toString('utf8');
  } catch (_) {
    return { dir: realOutputRoot(), declared: null, created: false };
  }

  let declared = null;
  for (const line of text.split(/\r?\n/)) {
    const m = line.match(/^\s*(?:REM|::)\s*COWORK_OUTPUT\s*[:=]\s*(.+?)\s*$/i);
    if (m) { declared = m[1].replace(/^["']|["']$/g, '').trim(); break; }
  }

  if (!declared) {
    // No declaration: hand over the Outputs root, create nothing, invent nothing.
    return { dir: realOutputRoot(), declared: null, created: false };
  }

  if (declared.includes('%') || /\$env:/i.test(declared) || declared.includes('\0'))
    throw new RejectError(
      'COWORK_OUTPUT directive must be a literal path (no environment variables)', declared);
  if (declared.replace(/\//g, '\\').startsWith('\\\\'))
    throw new RejectError('COWORK_OUTPUT directive may not be a UNC or network path', declared);

  const outRoot = realOutputRoot();
  const target = path.isAbsolute(declared)
    ? path.resolve(declared)
    : path.resolve(outRoot, declared);

  if (!isInside(outRoot, target))
    throw new RejectError(
      `COWORK_OUTPUT directive resolves outside ${OUTPUT_ROOT}`, target);

  let created = false;
  if (!fs.existsSync(target)) {
    try { fs.mkdirSync(target, { recursive: true }); created = true; }
    catch (e) {
      throw new RejectError(
        `COWORK_OUTPUT directory could not be created: ${e.message}`, target);
    }
  }

  // Re-check AFTER creation, so a junction planted at the target is caught.
  let realTarget;
  try { realTarget = realOf(target); }
  catch (_) { throw new RejectError('COWORK_OUTPUT directory could not be canonicalised', target); }

  if (!isInside(outRoot, realTarget))
    throw new RejectError(
      'COWORK_OUTPUT resolves outside Outputs (symlink or junction escape)', realTarget);

  if (!fs.statSync(realTarget).isDirectory())
    throw new RejectError('COWORK_OUTPUT is not a directory', realTarget);

  return { dir: realTarget, declared, created };
}

/* ------------------------------------------------- file-change detection -- */

function snapshot(roots, skipDirs) {
  const map = new Map();
  let count = 0;
  const skip = new Set((skipDirs || []).map(s => s.toLowerCase()));

  function walk(dir, isTop) {
    if (count > MAX_SCAN_FILES) return;
    let entries;
    try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch (_) { return; }
    for (const e of entries) {
      if (count > MAX_SCAN_FILES) return;
      const full = path.join(dir, e.name);
      if (e.isSymbolicLink()) continue;          // never follow links while scanning
      if (e.isDirectory()) {
        if (isTop && skip.has(e.name.toLowerCase())) continue;
        walk(full, false);
      } else if (e.isFile()) {
        count++;
        try {
          const st = fs.statSync(full);
          map.set(full, `${st.size}:${st.mtimeMs}`);
        } catch (_) { /* ignore races */ }
      }
    }
  }

  for (const r of roots) {
    try { if (fs.existsSync(r)) walk(r, true); } catch (_) {}
  }
  return map;
}

function diffSnapshots(before, after) {
  const created = [], modified = [], deleted = [];
  for (const [f, sig] of after) {
    if (!before.has(f)) created.push(f);
    else if (before.get(f) !== sig) modified.push(f);
  }
  for (const f of before.keys()) if (!after.has(f)) deleted.push(f);
  return { created: created.sort(), modified: modified.sort(), deleted: deleted.sort() };
}

/* -------------------------------------------------------------- execute -- */

function killTree(pid) {
  try {
    spawnSync('taskkill', ['/PID', String(pid), '/T', '/F'], {
      windowsHide: true, stdio: 'ignore', timeout: 20000
    });
  } catch (_) { /* best effort */ }
}

function runBatch(realPath, approvedOutput) {
  return new Promise((resolve) => {
    const jobDir  = path.dirname(realPath);
    const jobName = path.basename(realPath, path.extname(realPath));
    const started = new Date();
    const tag     = `${jobName}_${stamp(started)}`;

    const jobRoot = realJobRoot();
    const outRoot = realOutputRoot();
    const before  = snapshot([jobRoot, outRoot], ['logs']);

    // Minimal, server-built environment. The MCP caller contributes nothing.
    const env = {
      SystemRoot:  process.env.SystemRoot || 'C:\\Windows',
      windir:      process.env.windir || 'C:\\Windows',
      Path:        process.env.Path || process.env.PATH || '',
      PATHEXT:     process.env.PATHEXT || '.COM;.EXE;.BAT;.CMD',
      TEMP:        process.env.TEMP || os.tmpdir(),
      TMP:         process.env.TMP || os.tmpdir(),
      USERPROFILE: process.env.USERPROFILE || '',
      COMPUTERNAME: process.env.COMPUTERNAME || '',
      NUMBER_OF_PROCESSORS: process.env.NUMBER_OF_PROCESSORS || '',
      COWORK_JOB_NAME:    jobName,
      COWORK_JOB_TAG:     tag,
      COWORK_JOB_ROOT:    jobRoot,
      COWORK_OUTPUT_ROOT: outRoot,
      COWORK_JOB_OUTPUT:  approvedOutput.dir     // approved in the script, not by the caller
    };

    // /d skip AutoRun registry hooks   /s treat the quoted path verbatim
    // /c run then terminate.  Path passed as its own argv entry -- never concatenated.
    const child = spawn('cmd.exe', ['/d', '/s', '/c', realPath], {
      cwd: jobDir,
      env,
      windowsHide: true,                  // hidden window; nothing can prompt
      stdio: ['ignore', 'pipe', 'pipe'],  // stdin closed: no interactive input
      detached: false                     // no elevation, no new console
    });

    let out = Buffer.alloc(0), err = Buffer.alloc(0);
    let outTrunc = false, errTrunc = false;
    let timedOut = false, spawnErr = null;

    child.stdout.on('data', (c) => {
      if (out.length >= MAX_STDOUT) { outTrunc = true; return; }
      out = Buffer.concat([out, c]);
      if (out.length > MAX_STDOUT) { out = out.subarray(0, MAX_STDOUT); outTrunc = true; }
    });
    child.stderr.on('data', (c) => {
      if (err.length >= MAX_STDERR) { errTrunc = true; return; }
      err = Buffer.concat([err, c]);
      if (err.length > MAX_STDERR) { err = err.subarray(0, MAX_STDERR); errTrunc = true; }
    });

    const timer = setTimeout(() => {
      timedOut = true;
      if (child.pid) killTree(child.pid);
      try { child.kill('SIGKILL'); } catch (_) {}
    }, TIMEOUT_MS);

    child.on('error', (e) => { spawnErr = e; });

    child.on('close', (code, signal) => {
      clearTimeout(timer);
      const ended = new Date();

      const changes = diffSnapshots(before, snapshot([jobRoot, outRoot], ['logs']));

      let outputFiles = [];
      try {
        outputFiles = fs.readdirSync(approvedOutput.dir, { withFileTypes: true })
          .filter(e => e.isFile())
          .map(e => path.join(approvedOutput.dir, e.name));
      } catch (_) {}

      const exitCode = timedOut ? 9999
                     : spawnErr ? 9998
                     : (code === null ? 9997 : code);

      const result = {
        script:            realPath,
        job_tag:           tag,
        working_dir:       jobDir,
        output_dir:        approvedOutput.dir,
        output_declared:   approvedOutput.declared,
        output_dir_created: approvedOutput.created,
        exit_code:         exitCode,
        timed_out:         timedOut,
        signal:            signal || null,
        spawn_error:       spawnErr ? spawnErr.message : null,
        started_at:        started.toISOString(),
        ended_at:          ended.toISOString(),
        duration_ms:       ended - started,
        stdout:            out.toString('utf8'),
        stderr:            err.toString('utf8'),
        stdout_truncated:  outTrunc,
        stderr_truncated:  errTrunc,
        files_created:     changes.created,
        files_modified:    changes.modified,
        files_deleted:     changes.deleted,
        output_files:      outputFiles,
        rerun_performed:   false          // failures are never retried automatically
      };

      try {
        const lines = [
          `script      : ${realPath}`,
          `job tag     : ${tag}`,
          `working dir : ${jobDir}`,
          `output dir  : ${approvedOutput.dir}`,
          `declared    : ${approvedOutput.declared || '(none -- Outputs root used, nothing created)'}`,
          `started     : ${result.started_at}`,
          `finished    : ${result.ended_at}`,
          `duration    : ${result.duration_ms} ms`,
          `exit code   : ${exitCode}`,
          timedOut ? `*** TIMED OUT after ${TIMEOUT_MS / 1000}s -- process tree killed ***` : '',
          spawnErr ? `*** FAILED TO START: ${spawnErr.message} ***` : '',
          '',
          '----- STDOUT -----', result.stdout + (outTrunc ? '\r\n*** stdout truncated at 5 MB ***' : ''),
          '----- STDERR -----', result.stderr + (errTrunc ? '\r\n*** stderr truncated at 5 MB ***' : ''),
          '----- FILES CREATED -----',  changes.created.join('\r\n'),
          '----- FILES MODIFIED -----', changes.modified.join('\r\n'),
          '----- FILES DELETED -----',  changes.deleted.join('\r\n')
        ].filter(l => l !== '');
        fs.writeFileSync(path.join(LOG_DIR, `${tag}.log`),  lines.join('\r\n'), 'utf8');
        fs.writeFileSync(path.join(LOG_DIR, `${tag}.exit`), String(exitCode), 'utf8');
        fs.writeFileSync(path.join(LOG_DIR, `${tag}.json`), JSON.stringify(result, null, 2), 'utf8');
        result.log_file = path.join(LOG_DIR, `${tag}.log`);
      } catch (_) { /* logging must never break execution reporting */ }

      // The batch file is deliberately left in place.
      resolve(result);
    });
  });
}

/* ------------------------------------------------------------- MCP layer -- */

/* ---------------------------------------------- operating rules (v1.2.0) -- */
/*
 *  Surfaces the bridge's own hard-won rules AT THE MOMENT OF USE, instead of
 *  hoping they were read beforehand. Between 2026-08-24 and 2026-08-28 the same
 *  bridge mistakes recurred across three sessions while the lessons describing
 *  them sat unread in cowork-lessons.md. A rule delivered in the tool response
 *  cannot be skipped the way a pre-task scan can.
 *
 *  Read LIVE from the lessons file, so there is no digest to regenerate and the
 *  text can never go stale.
 *
 *  Fires only when it is worth reading: the first job of this process, and any
 *  job that exits non-zero or times out. A reminder attached to every successful
 *  call becomes wallpaper and gets skimmed, which is the exact failure being
 *  fixed here.
 *
 *  NEVER throws and NEVER blocks execution. A missing, huge or malformed lessons
 *  file simply means no reminder. Job execution is untouched by this whole block.
 */

const LESSON_PATHS = [
  'C:\\Users\\YOURUSER\\OneDrive\\Documents\\Cowork\\cowork-memory\\cowork-lessons.md',
  path.join(COWORK_ROOT, 'CoworkConfig', 'cowork-memory', 'cowork-lessons.md')
];
const MAX_LESSON_BYTES = 4 * 1024 * 1024;
const MAX_RULES        = 8;

/*  MEASURED 2026-08-28, and it changed this design.
 *  supergateway runs 8933 STATELESS: a FRESH node process is spawned per
 *  request. Two consecutive jobs both reported "first job of this session"
 *  because an in-process flag resets every call. A module-level boolean cannot
 *  throttle anything here, so the reminder would have fired on EVERY call and
 *  become the wallpaper this was built to avoid.
 *
 *  State therefore lives in a file. A clean job inside the throttle window stays
 *  quiet; a job that does not exit clean ALWAYS gets the rules, because that is
 *  the moment they are worth reading.
 */
const REMINDER_THROTTLE_MS = 45 * 60 * 1000;
const REMINDER_MARKER      = path.join(LOG_DIR, '_last-operating-rules.txt');

let RULES_CACHE = null;   // null = not yet attempted

function reminderSentRecently() {
  try {
    const t = parseInt(fs.readFileSync(REMINDER_MARKER, 'utf8').trim(), 10);
    if (isNaN(t)) return false;
    const age = Date.now() - t;
    return age >= 0 && age < REMINDER_THROTTLE_MS;
  } catch (_) {
    return false;   // no marker, unreadable, or clock oddity -> send it
  }
}

function markReminderSent() {
  try { fs.writeFileSync(REMINDER_MARKER, String(Date.now()), 'utf8'); }
  catch (_) { /* never let bookkeeping affect a job */ }
}

function loadOperatingRules() {
  if (RULES_CACHE !== null) return RULES_CACHE;
  RULES_CACHE = [];
  try {
    let text = null;
    for (const p of LESSON_PATHS) {
      try {
        const st = fs.statSync(p);
        if (st.isFile() && st.size > 0 && st.size <= MAX_LESSON_BYTES) {
          text = fs.readFileSync(p, 'utf8');
          break;
        }
      } catch (_) { /* try the next candidate */ }
    }
    if (!text) return RULES_CACHE;

    const found = [];
    for (const block of text.split(/^### /m).slice(1)) {
      const key  = (block.match(/^- \*\*Pattern-Key:\*\* (\S+)/m) || [])[1];
      const rule = (block.match(/^- \*\*Rule:\*\* (.+)$/m) || [])[1];
      if (!key || !rule) continue;
      if (!/^(bridge|git)-/.test(key)) continue;   // rules about USING this bridge
      const hits = parseInt((block.match(/^- \*\*Hits:\*\* (\d+)/m) || [])[1] || '1', 10);
      found.push({ key, rule: rule.trim(), hits: isNaN(hits) ? 1 : hits });
    }
    found.sort((a, b) => b.hits - a.hits);
    RULES_CACHE = found.slice(0, MAX_RULES);
  } catch (_) {
    RULES_CACHE = [];
  }
  return RULES_CACHE;
}

function reminderBlock(why) {
  try {
    const rules = loadOperatingRules();
    if (!rules || rules.length === 0) return null;
    const lines = rules.map(r =>
      `  - ${r.rule}` + `  [${r.key}${r.hits > 1 ? `, ${r.hits} hits` : ''}]`);
    return `OPERATING RULES FOR THIS BRIDGE  (${why})\n` +
           `Read live from cowork-lessons.md. Each was learned by getting it wrong.\n\n` +
           lines.join('\n') +
           `\n\nScope: these cover USING the bridge. A bridge that appears ABSENT is a ` +
           `different failure and this message cannot reach you for it, because you ` +
           `would not be calling the tool. That rule lives in copilot-instructions.md.`;
  } catch (_) {
    return null;
  }
}

const TOOL = {
  name: 'run_batch_file',
  title: 'Run an approved batch file',
  description:
    'Execute an existing .bat or .cmd file already present under ' +
    'COPILOT_COWORK\\CommandJobs. Write the batch file first (filesystem bridge), ' +
    'then pass its RELATIVE name here. Deliverables belong under COPILOT_COWORK\\Outputs; ' +
    'the script declares its own destination with a "REM COWORK_OUTPUT: <path>" line, ' +
    'which is exposed to it as %COWORK_JOB_OUTPUT%. Returns stdout, stderr, exit code, ' +
    'timing, and the files created or modified. No command, arguments, executable, ' +
    'interpreter, working directory, environment variable, output directory, timeout ' +
    'override or elevation option can be supplied -- the only input is the filename. ' +
    'This response carries the current rules verbatim on the first job of a session ' +
    'and on any job that does not exit clean.'
    /* PLUGIN-LESSONS:start run_batch_file */
    + 'OPERATING RULES, each learned from a real failure and regenerated from '
    + 'cowork-lessons.md - do not hand-edit: Files written through 8932 arrive LF-only and '
    + 'cmd mis-parses them. Run the CRLF fix job after writing any new .bat. 8933 does not '
    + 'inherit a working directory, so start every job with `cd /d <repo>`. PATH is intact '
    + 'and bare interpreter names resolve; only user-profile variables are empty. After a '
    + 'transport error, check whether the job already ran before retrying. Never '
    + 'blind-retry a state-changing job. 8933 jobs inherit the MACHINE PATH only, not the '
    + 'USER PATH. `where <tool>` therefore finds nothing for anything installed per-user '
    + '(PAC CLI, npm globals, dotnet global tools, VS Code CLIs) even when it resolves fine '
    + 'in Jordan\'s own shell. Read the user PATH with `reg query "HKCU\\Environment" /v '
    + 'Path` and locate the tool from there. '
    /* PLUGIN-LESSONS:end */
  ,
  inputSchema: {
    type: 'object',
    properties: {
      file: {
        type: 'string',
        description:
          'Relative filename or relative path of an existing .bat/.cmd under CommandJobs, ' +
          'e.g. "reconcile-q3.bat" or "jobs\\\\reconcile-q3.bat". Absolute, drive-qualified, ' +
          'UNC and environment-variable paths are rejected.'
      }
    },
    required: ['file'],
    additionalProperties: false
  }
};

function send(msg) { process.stdout.write(JSON.stringify(msg) + '\n'); }
function ok(id, result)          { send({ jsonrpc: '2.0', id, result }); }
function fail(id, code, message) { send({ jsonrpc: '2.0', id, error: { code, message } }); }
function toolErr(id, message)    { ok(id, { isError: true, content: [{ type: 'text', text: message }] }); }

async function handle(msg) {
  const { id, method, params } = msg;
  const isNotification = (id === undefined || id === null);

  switch (method) {
    case 'initialize': {
      const asked = params && params.protocolVersion;
      return ok(id, {
        protocolVersion: typeof asked === 'string' ? asked : DEFAULT_PROTOCOL,
        capabilities: { tools: { listChanged: false } },
        serverInfo: { name: SERVER_NAME, version: SERVER_VERSION }
      });
    }

    case 'notifications/initialized':
    case 'initialized':
      return;

    case 'ping':
      return isNotification ? undefined : ok(id, {});

    case 'tools/list':     return ok(id, { tools: [TOOL] });
    case 'resources/list': return ok(id, { resources: [] });
    case 'prompts/list':   return ok(id, { prompts: [] });

    case 'tools/call': {
      const name = params && params.name;
      const args = (params && params.arguments) || {};

      if (name !== TOOL.name)
        return fail(id, -32602, `Unknown tool: ${name}`);

      // Reject unexpected arguments outright -- nothing can be smuggled alongside "file".
      const extra = Object.keys(args).filter(k => k !== 'file');
      if (extra.length)
        return toolErr(id, `REJECTED: unexpected parameter(s): ${extra.join(', ')}. ` +
                           'run_batch_file accepts only "file".');

      let real, approvedOutput;
      try {
        real = validateBatchPath(args.file);
        approvedOutput = resolveApprovedOutput(real);
      } catch (e) {
        if (e instanceof RejectError)
          return toolErr(id, `REJECTED: ${e.reason}` + (e.detail ? ` -- ${e.detail}` : ''));
        return toolErr(id, `REJECTED: validation failed: ${e.message}`);
      }

      if (RUNNING)
        return toolErr(id, 'REJECTED: another batch job is already running. ' +
                           'Maximum concurrent executions is 1. Try again when it finishes.');

      RUNNING = true;
      let result;
      try {
        result = await runBatch(real, approvedOutput);
      } catch (e) {
        return toolErr(id, `Execution failed: ${e.message}`);
      } finally {
        RUNNING = false;
      }

      const summary =
        `exit code ${result.exit_code}` +
        (result.timed_out ? ' (TIMED OUT -- process tree killed)' : '') +
        `, ${result.duration_ms} ms`;

      const content = [
        { type: 'text', text: `${path.basename(real)}: ${summary}` },
        { type: 'text', text: JSON.stringify(result, null, 2) }
      ];

      /* Attach the operating rules only when they are worth reading.
       * A failed job always gets them. A clean job gets them only outside the
       * throttle window. See the REMINDER_THROTTLE_MS note above for why this
       * cannot be an in-process flag. */
      const didNotExitClean = (result.exit_code !== 0) || result.timed_out;
      let why = null;
      if (didNotExitClean)             why = 'this job did not exit clean';
      else if (!reminderSentRecently()) why = 'first job in the last 45 minutes';

      if (why) {
        const reminder = reminderBlock(why);
        if (reminder) {
          content.push({ type: 'text', text: reminder });
          markReminderSent();
        }
      }

      return ok(id, {
        content,
        isError: result.exit_code !== 0
      });
    }

    default:
      if (isNotification) return;
      return fail(id, -32601, `Method not found: ${method}`);
  }
}

/* ---------------------------------------------------------------- stdio -- */

ensureDirs();

try {
  realJobRoot();
  realOutputRoot();
} catch (e) {
  process.stderr.write(`[cowork-batch-exec] FATAL: required root unavailable: ${e.message}\n`);
  process.exit(1);
}

process.stderr.write(
  `[cowork-batch-exec] v${SERVER_VERSION} ready. Tool: run_batch_file\n` +
  `[cowork-batch-exec] scripts: ${realJobRoot()}\n` +
  `[cowork-batch-exec] outputs: ${realOutputRoot()}\n` +
  `[cowork-batch-exec] .bat/.cmd only, relative paths only, 300s timeout, ` +
  `5MB output caps, 1 concurrent job.\n`);

let buf = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  buf += chunk;
  let nl;
  while ((nl = buf.indexOf('\n')) >= 0) {
    const line = buf.slice(0, nl).trim();
    buf = buf.slice(nl + 1);
    if (!line) continue;
    let msg;
    try { msg = JSON.parse(line); }
    catch (_) {
      send({ jsonrpc: '2.0', id: null, error: { code: -32700, message: 'Parse error' } });
      continue;
    }
    Promise.resolve(handle(msg)).catch((e) => {
      if (msg && msg.id !== undefined && msg.id !== null)
        fail(msg.id, -32603, `Internal error: ${e.message}`);
    });
  }
});

process.stdin.on('end', () => process.exit(0));
