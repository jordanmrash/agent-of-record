#!/usr/bin/env node
/* ============================================================================
 *  Cowork Command Bridge -- hardened script-only MCP server   v1.3.0
 *  <tooling root>/Startup/CommandBridge/batch-exec-server.js
 *
 *  Replaces the unrestricted `mcp-server-commands` package behind port 8933.
 *
 *  Runs on Windows and on POSIX (macOS, Linux). The platform decides the shell
 *  and the executable extension; it does not decide any security property.
 *  See the PLATFORM note in the config block.
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
 *    Scripts       <tooling root>/CommandJobs/    (.bat/.cmd on Windows, .sh on POSIX)
 *    Logs          <tooling root>/CommandJobs/Logs/
 *    Deliverables  <tooling root>/Outputs/<YYYY-MM-DD - Task Name>/
 *
 *  OUTPUT DESTINATION
 *    The server NEVER invents or substitutes an output folder. The approved
 *    script declares its own destination on a directive line, behind its own
 *    language's comment marker:
 *
 *        REM COWORK_OUTPUT: <tooling root>\Outputs\2026-08-17 - Task Name
 *        #   COWORK_OUTPUT: <tooling root>/Outputs/2026-08-17 - Task Name
 *
 *    The server reads that directive, verifies it canonicalises under
 *    COPILOT_COWORK\Outputs, creates it if absent, and exposes it to the
 *    script as %COWORK_JOB_OUTPUT%. If the directive is missing the job still
 *    runs, with COWORK_JOB_OUTPUT left pointing at the Outputs root and no
 *    folder created. If the directive is present but resolves outside Outputs,
 *    the job is REFUSED rather than silently redirected.
 *
 *  LINE ENDINGS (v1.3.0)
 *    cmd.exe mis-parses an LF-only .bat silently -- a `call :label` misses,
 *    a block ends early, and the job reports a clean exit having skipped work.
 *    bash fails a CRLF .sh loudly instead ("$'\r': command not found").
 *    Scripts reach CommandJobs from tools that write the other convention
 *    (the 8932 filesystem bridge writes LF), so before running an approved
 *    script the server rewrites its line terminators to the platform's own
 *    convention, in place, and reports that it did. Nothing but the
 *    terminators changes, and a file with mixed endings is left alone.
 *
 *  JOB ENVIRONMENT (v1.3.0)
 *    The environment a job runs in is built by the server -- the MCP caller
 *    still contributes nothing -- but it is now COMPLETE: the profile
 *    variables (USERPROFILE, APPDATA, LOCALAPPDATA, TEMP on Windows; HOME,
 *    USER on POSIX) are derived from the account the server runs as when the
 *    launching process lacks them, and the user's own PATH (HKCU\Environment
 *    on Windows; the conventional user bin directories on POSIX) is appended
 *    to the machine PATH. Until 1.3.0 a bridge started by a scheduled task
 *    handed jobs an environment with those variables empty, so per-user tools
 *    had to be located by hand inside every script.
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

/* PLATFORM
 *
 *  The bridge runs on Windows and on POSIX (macOS, Linux). Four things differ:
 *  the shell that executes an approved script, the extension that may be
 *  executed, the comment marker the COWORK_OUTPUT directive hides behind, and
 *  how a runaway process tree is killed.
 *
 *  Everything that carries a security property is IDENTICAL on both: the path
 *  validation, the containment checks against the canonicalised root, the
 *  single-flight lock, the fixed timeout, the server-built environment (see
 *  buildJobEnvironment -- complete, but never caller-supplied), and the rule
 *  that the caller supplies nothing but a relative filename. A port that
 *  relaxed one of those would not be the same bridge.
 *
 *  The tooling root comes from COWORK_ROOT when the launcher sets it and from
 *  the platform's home-relative default otherwise. That is deliberate: it is
 *  why this file carries no personalized path, and why an operator's account
 *  name never has to be written into the server. COWORK_ROOT is read from the
 *  process the OPERATOR launched, never from the MCP caller, who cannot set an
 *  environment variable through the one tool this server exposes.
 */
const IS_WINDOWS = process.platform === 'win32';

const COWORK_ROOT  = process.env.COWORK_ROOT ||
                     path.join(os.homedir(), 'Documents', 'COPILOT_COWORK');
const JOB_ROOT_RAW = path.join(COWORK_ROOT, 'CommandJobs');
const LOG_DIR      = path.join(JOB_ROOT_RAW, 'Logs');
const OUTPUT_ROOT  = path.join(COWORK_ROOT, 'Outputs');

const TIMEOUT_MS     = 300 * 1000;        // fixed; no caller override
const MAX_STDOUT     = 5 * 1024 * 1024;
const MAX_STDERR     = 5 * 1024 * 1024;
const ALLOWED_EXT    = IS_WINDOWS ? new Set(['.bat', '.cmd']) : new Set(['.sh']);
const ALLOWED_EXT_TEXT = IS_WINDOWS ? '.bat and .cmd' : '.sh';
const MAX_SCAN_FILES = 20000;
const MAX_DIRECTIVE_BYTES = 256 * 1024;   // how much of a script we read to find the directive
const MAX_NORMALIZE_BYTES = 4 * 1024 * 1024; // a script larger than this runs as-is, unnormalised

/* Path separator handling. A caller may write either separator; it is folded
 * to the platform's own before resolution. On POSIX a backslash is a legal
 * filename character, so folding the OTHER direction there would turn
 * "sub\job.sh" into one strange filename instead of a traversal check. */
const SEP      = IS_WINDOWS ? '\\' : '/';
const SEP_FROM = IS_WINDOWS ? /\//g : /\\/g;

/* The POSIX interpreter. bash rather than sh: the jobs in CommandJobs/ use
 * bash constructs, and pinning it here means the script's own shebang cannot
 * choose a different interpreter. */
const POSIX_SHELL = '/bin/bash';

/* The COWORK_OUTPUT directive hides behind the script language's own comment
 * marker: REM or :: in a .bat, # in a .sh. The rest of the line is identical,
 * so an operator reading either script sees the same declaration. */
const DIRECTIVE_RE = IS_WINDOWS
  ? /^\s*(?:REM|::)\s*COWORK_OUTPUT\s*[:=]\s*(.+?)\s*$/i
  : /^\s*#\s*COWORK_OUTPUT\s*[:=]\s*(.+?)\s*$/i;

/* The name the server gives itself in serverInfo and on stderr. Matches the
 * SERVER_KEY install-mac.sh registers; the old value collided with the prefix
 * Claude Desktop reserves, and a config entry under it is refused at launch. */
const SERVER_NAME      = 'aor-batch-exec';
const SERVER_VERSION   = '1.3.0';
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
 *   extensions outside ALLOWED_EXT (.bat/.cmd on Windows, .sh on POSIX),
 *                             checked on the CANONICAL path
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

  const slashed = raw.replace(SEP_FROM, SEP);

  // --- UNC / device / network paths ------------------------------------------
  // Checked on BOTH platforms: a leading double separator is never a legitimate
  // relative job path, and refusing it on POSIX costs nothing.
  if (raw.startsWith('\\\\') || raw.startsWith('//'))
    throw new RejectError('UNC and network paths are not permitted', raw);
  if (/^[a-z]+:\/\//i.test(raw))
    throw new RejectError('URL-style paths are not permitted', raw);

  // --- absolute paths of every flavour ----------------------------------------
  // ':' is already refused above, so this catches root-relative "\foo" / "/foo".
  // Both flavours are refused on both platforms -- win32.isAbsolute still runs
  // on POSIX so that a Windows-shaped absolute path cannot slip through a mac.
  if (raw.startsWith('\\') || raw.startsWith('/'))
    throw new RejectError('absolute paths are not permitted; supply a path relative to CommandJobs', raw);
  if (path.isAbsolute(raw) || path.win32.isAbsolute(raw) || path.posix.isAbsolute(raw))
    throw new RejectError('absolute paths are not permitted; supply a path relative to CommandJobs', raw);

  // --- shell metacharacters ----------------------------------------------------
  // ';' and '$' matter on POSIX the way '&' and '%' matter on cmd. None of them
  // can chain a command here, because the path is passed as its own argv entry
  // and never concatenated into a command string -- but a filename containing
  // one has no legitimate use, and refusing it by NAME beats refusing it
  // incidentally because the file happened not to exist.
  if (/[&|;<>^"'`$\r\n\t*?]/.test(raw))
    throw new RejectError('file contains illegal characters', raw);

  // --- textual traversal --------------------------------------------------------
  // Split on BOTH separators regardless of platform: "..\x" must not survive on
  // POSIX just because a backslash is a legal character there.
  if (raw.split(/[\\/]/).some(seg => seg === '..'))
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
    throw new RejectError(`only ${ALLOWED_EXT_TEXT} may be executed (got "${ext || 'none'}")`, real);

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
    const m = line.match(DIRECTIVE_RE);
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

/* ------------------------------------------------ script line endings -- */
/*
 * Rewrites an approved script's line terminators to the platform's own
 * convention, IN PLACE, before it runs: LF-only .bat/.cmd -> CRLF on Windows,
 * CRLF .sh -> LF on POSIX. The file that runs is the file that exists, changed
 * in nothing but its terminators. Byte-level (latin1 round trip), so a script
 * in any encoding is rewritten losslessly. A file that already mixes the two
 * conventions is left exactly as it is and reported as such; a file over
 * MAX_NORMALIZE_BYTES runs as-is. Never throws: a normalisation that cannot
 * happen is reported, not fatal.
 */
function normalizeLineEndings(realPath) {
  let buf;
  try { buf = fs.readFileSync(realPath); }
  catch (_) { return 'unreadable'; }
  if (buf.length > MAX_NORMALIZE_BYTES) return 'skipped-large';
  const text  = buf.toString('latin1');
  const crlf  = (text.match(/\r\n/g) || []).length;
  const lf    = (text.match(/\n/g) || []).length - crlf;      // bare LFs
  const cr    = (text.match(/\r/g) || []).length - crlf;      // bare CRs
  if (IS_WINDOWS) {
    if (lf === 0) return 'unchanged';                          // already CRLF (or no newlines)
    if (crlf > 0 || cr > 0) return 'mixed-left-alone';
    try { fs.writeFileSync(realPath, Buffer.from(text.replace(/\n/g, '\r\n'), 'latin1')); }
    catch (_) { return 'not-writable'; }
    return 'lf-to-crlf';
  }
  if (crlf === 0) return 'unchanged';
  if (lf > 0 || cr > 0) return 'mixed-left-alone';
  try { fs.writeFileSync(realPath, Buffer.from(text.replace(/\r\n/g, '\n'), 'latin1')); }
  catch (_) { return 'not-writable'; }
  return 'crlf-to-lf';
}

/* ------------------------------------------------------ job environment -- */
/*
 * The environment an approved script runs in. Built entirely by the server:
 * the MCP caller has no parameter that reaches it, and nothing from the
 * request is read here. It is COMPLETE, meaning it carries what an
 * interactive session of the same account would carry --
 *
 *   Windows  SystemRoot, windir, SystemDrive, ComSpec, PATHEXT, COMPUTERNAME,
 *            USERNAME, USERPROFILE, HOMEDRIVE, HOMEPATH, APPDATA, LOCALAPPDATA,
 *            ProgramData, ProgramFiles, ProgramFiles(x86), ProgramW6432,
 *            TEMP, TMP, NUMBER_OF_PROCESSORS, and Path = the machine PATH the
 *            server was started with, followed by the user's PATH read from
 *            HKCU\Environment (with %VAR% references expanded).
 *   POSIX    PATH (the server's, plus the conventional user bin directories
 *            that exist: ~/.local/bin, ~/bin, /opt/homebrew/{bin,sbin},
 *            /usr/local/{bin,sbin}), HOME, USER, LOGNAME, SHELL, LANG, TMPDIR.
 *
 * -- derived from the account the server runs as whenever the launching
 * process did not supply them. A bridge started by a scheduled task or a
 * launchd job gets a stripped environment; until 1.3.0 that stripping reached
 * every job, and per-user tools had to be located by hand inside scripts.
 * Values the launching process DID supply are kept as they are.
 */
function readUserPathWindows(lookup) {
  try {
    const reg = path.join(process.env.SystemRoot || 'C:\\Windows', 'System32', 'reg.exe');
    const r = spawnSync(reg, ['query', 'HKCU\\Environment', '/v', 'Path'],
                        { encoding: 'utf8', timeout: 5000, windowsHide: true });
    const m = /^\s*Path\s+REG_(?:EXPAND_)?SZ\s+(.*)$/im.exec(r.stdout || '');
    if (!m) return '';
    return m[1].trim().replace(/%([^%]+)%/g, (whole, name) => {
      const v = lookup(name);
      return v === undefined ? whole : v;
    });
  } catch (_) { return ''; }
}

function mergePath(entries, caseInsensitive) {
  const out = [], seen = new Set();
  for (const e of entries) {
    const t = (e || '').trim();
    if (!t) continue;
    const k = caseInsensitive ? t.toLowerCase().replace(/[\\/]+$/, '') : t.replace(/\/+$/, '');
    if (seen.has(k)) continue;
    seen.add(k); out.push(t);
  }
  return out;
}

function buildJobEnvironment(jobEnv) {
  const pe = process.env;
  if (IS_WINDOWS) {
    const systemRoot  = pe.SystemRoot || 'C:\\Windows';
    const systemDrive = pe.SystemDrive || systemRoot.slice(0, 2);
    let profile = pe.USERPROFILE || '';
    if (!profile) { try { profile = os.homedir() || ''; } catch (_) { profile = ''; } }
    const appdata = pe.APPDATA      || (profile ? path.join(profile, 'AppData', 'Roaming') : '');
    const local   = pe.LOCALAPPDATA || (profile ? path.join(profile, 'AppData', 'Local') : '');
    const temp    = pe.TEMP || pe.TMP || (local ? path.join(local, 'Temp') : os.tmpdir());
    let username = pe.USERNAME || '';
    if (!username) { try { username = os.userInfo().username || ''; } catch (_) { username = ''; } }
    const env = {
      SystemRoot:  systemRoot,
      windir:      pe.windir || systemRoot,
      SystemDrive: systemDrive,
      ComSpec:     pe.ComSpec || path.join(systemRoot, 'System32', 'cmd.exe'),
      PATHEXT:     pe.PATHEXT || '.COM;.EXE;.BAT;.CMD',
      COMPUTERNAME: pe.COMPUTERNAME || '',
      NUMBER_OF_PROCESSORS: pe.NUMBER_OF_PROCESSORS || String(os.cpus().length),
      USERNAME:    username,
      USERPROFILE: profile,
      HOMEDRIVE:   pe.HOMEDRIVE || (profile ? profile.slice(0, 2) : ''),
      HOMEPATH:    pe.HOMEPATH  || (profile ? profile.slice(2) : ''),
      APPDATA:     appdata,
      LOCALAPPDATA: local,
      ProgramData: pe.ProgramData || (systemDrive + '\\ProgramData'),
      ProgramFiles: pe.ProgramFiles || (systemDrive + '\\Program Files'),
      'ProgramFiles(x86)': pe['ProgramFiles(x86)'] || (systemDrive + '\\Program Files (x86)'),
      ProgramW6432: pe.ProgramW6432 || pe.ProgramFiles || (systemDrive + '\\Program Files'),
      TEMP:        temp,
      TMP:         temp
    };
    const lookup = (name) => {
      const hit = Object.keys(env).find(k => k.toLowerCase() === name.toLowerCase());
      return hit === undefined ? undefined : env[hit];
    };
    const machinePath = pe.Path || pe.PATH || '';
    const userPath    = readUserPathWindows(lookup);
    env.Path = mergePath([...machinePath.split(';'), ...userPath.split(';')], true).join(';');
    return { env: Object.assign(env, jobEnv),
             userPathEntries: userPath ? userPath.split(';').filter(Boolean).length : 0 };
  }
  let home = pe.HOME || '';
  if (!home) { try { home = os.homedir() || ''; } catch (_) { home = ''; } }
  let user = pe.USER || pe.LOGNAME || '';
  if (!user) { try { user = os.userInfo().username || ''; } catch (_) { user = ''; } }
  const candidates = [
    home && path.join(home, '.local', 'bin'), home && path.join(home, 'bin'),
    '/opt/homebrew/bin', '/opt/homebrew/sbin', '/usr/local/bin', '/usr/local/sbin'
  ].filter(p => { try { return p && fs.statSync(p).isDirectory(); } catch (_) { return false; } });
  const basePath = pe.PATH || '/usr/bin:/bin:/usr/sbin:/sbin';
  const env = {
    PATH:    mergePath([...basePath.split(':'), ...candidates], false).join(':'),
    HOME:    home,
    USER:    user,
    LOGNAME: pe.LOGNAME || user,
    TMPDIR:  pe.TMPDIR || os.tmpdir(),
    LANG:    pe.LANG || 'en_US.UTF-8',
    SHELL:   POSIX_SHELL
  };
  return { env: Object.assign(env, jobEnv), userPathEntries: candidates.length };
}

/* -------------------------------------------------------------- execute -- */

/* Kill the whole tree, not just the shell. On Windows taskkill /T walks the
 * child list. On POSIX the child is spawned into its own process group
 * (detached: true) so that a negative pid signals the group -- otherwise a
 * timed-out script's own children keep running after the shell dies. */
function killTree(pid) {
  try {
    if (IS_WINDOWS) {
      spawnSync('taskkill', ['/PID', String(pid), '/T', '/F'], {
        windowsHide: true, stdio: 'ignore', timeout: 20000
      });
    } else {
      try { process.kill(-pid, 'SIGKILL'); }
      catch (_) { process.kill(pid, 'SIGKILL'); }
    }
  } catch (_) { /* best effort */ }
}

function runBatch(realPath, approvedOutput, lineEndings) {
  return new Promise((resolve) => {
    const jobDir  = path.dirname(realPath);
    const jobName = path.basename(realPath, path.extname(realPath));
    const started = new Date();
    const tag     = `${jobName}_${stamp(started)}`;

    const jobRoot = realJobRoot();
    const outRoot = realOutputRoot();
    const before  = snapshot([jobRoot, outRoot], ['logs']);

    // Server-built environment: complete (see buildJobEnvironment), and the
    // MCP caller contributes nothing to it. The job-facing COWORK_* names are
    // identical on both platforms, so an approved script reads the same
    // variables wherever it runs.
    const jobEnv = {
      COWORK_JOB_NAME:    jobName,
      COWORK_JOB_TAG:     tag,
      COWORK_JOB_ROOT:    jobRoot,
      COWORK_OUTPUT_ROOT: outRoot,
      COWORK_JOB_OUTPUT:  approvedOutput.dir,    // approved in the script, not by the caller
      COWORK_ROOT:        COWORK_ROOT
    };
    const built = buildJobEnvironment(jobEnv);
    const env   = built.env;

    // Windows: /d skip AutoRun registry hooks, /s treat the quoted path
    //          verbatim, /c run then terminate.
    // POSIX:   the script is passed to bash as an argument rather than executed
    //          directly, so a missing execute bit is not a silent failure and
    //          the shebang cannot redirect execution to another interpreter.
    // On both, the path is its own argv entry -- never concatenated into a
    // command string, which is what keeps a filename from becoming an argument.
    const child = IS_WINDOWS
      ? spawn('cmd.exe', ['/d', '/s', '/c', realPath], {
          cwd: jobDir,
          env,
          windowsHide: true,                  // hidden window; nothing can prompt
          stdio: ['ignore', 'pipe', 'pipe'],  // stdin closed: no interactive input
          detached: false                     // no elevation, no new console
        })
      : spawn(POSIX_SHELL, [realPath], {
          cwd: jobDir,
          env,
          stdio: ['ignore', 'pipe', 'pipe'],  // stdin closed: no interactive input
          detached: true                      // own process group, so killTree reaches children
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
        line_endings:      lineEndings || 'unchanged',
        user_path_entries: built.userPathEntries,
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
          `line endings: ${result.line_endings}`,
          `environment : server-built, complete; user PATH entries appended: ${result.user_path_entries}`,
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

/* Where the operating corpus lives. COWORK_CONFIG_ROOT is what Cowork itself
 * loads -- the OneDrive "Cowork" folder on Windows, the equivalent on a Mac --
 * and the launcher sets it because only the operator knows their OneDrive
 * folder name. The in-repo copy is the fallback, so a checkout with no
 * configured host still produces a reminder. Both are read-only here. */
const CONFIG_ROOT = process.env.COWORK_CONFIG_ROOT || '';
const LESSON_PATHS = [
  ...(CONFIG_ROOT ? [path.join(CONFIG_ROOT, 'cowork-memory', 'cowork-lessons.md')] : []),
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

// ---- rule scope --------------------------------------------------------
//  A rules block is spent attention: it is prepended to a job result, every job,
//  and an operator reads it or does not. Measured 2026-09-15 on macOS under Claude
//  Cowork: eight rules were served and two applied. The other six were about a dev
//  tunnel, setting ports PUBLIC, resyncing tasks.json and running bridge-health.bat
//  - none of which exist on that route. A rule that cannot apply is not neutral;
//  it competes with the ones that can.
//
//  So an entry may carry "Routes:" and/or "Platforms:". BOTH ARE OPTIONAL and
//  absent means everywhere, so an untagged corpus behaves exactly as it did before
//  this existed. Narrowing is opt-in per entry and never deletes anything.
//
//  Platform is known here: this process is the bridge. Route is not - the Windows
//  launcher serves both products - so COWORK_ROUTE is read when the launcher sets
//  it and no route filtering happens when it does not. Guessing a route would drop
//  rules an operator needs; not guessing only keeps a few they do not.
const THIS_PLATFORM = process.platform === 'win32' ? 'windows'
                    : process.platform === 'darwin' ? 'macos' : 'linux';
const THIS_ROUTE = (process.env.COWORK_ROUTE || '').trim().toLowerCase() || null;

function inScope(block) {
  try {
    const routes = (block.match(/^- \*\*Routes:\*\* (.+)$/m) || [])[1];
    if (routes && THIS_ROUTE) {
      const list = routes.toLowerCase().split(/[,\s]+/).filter(Boolean);
      if (list.length && !list.includes(THIS_ROUTE)) return false;
    }
    const plats = (block.match(/^- \*\*Platforms:\*\* (.+)$/m) || [])[1];
    if (plats) {
      const list = plats.toLowerCase().split(/[,\s]+/).filter(Boolean);
      if (list.length && !list.includes(THIS_PLATFORM)) return false;
    }
    return true;
  } catch (_) {
    return true;   // a malformed scope line must never cost a rule
  }
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
      if (!inScope(block)) continue;               // and applicable to THIS route/platform
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

/* Everything below is text a MODEL reads to decide how to call this tool, so it
 * has to describe the platform the server is actually running on. The POSIX port
 * changed the enforcement -- ALLOWED_EXT, DIRECTIVE_RE, POSIX_SHELL -- but left
 * this text Windows-only, which told an agent on a Mac that its .sh job would be
 * refused and pointed it at `cd /d` and `reg query`. Derive the wording from the
 * same constants the checks use so the two cannot drift again. */
/* ALLOWED_EXT_TEXT joins with "and", which is right for a refusal ("only .bat
 * and .cmd may be executed") but wrong for naming one file, so the prose form
 * is separate. */
const FILE_KIND      = IS_WINDOWS ? '.bat or .cmd'           : '.sh';
const JOBS_HINT      = IS_WINDOWS ? 'COPILOT_COWORK\\CommandJobs' : '<tooling root>/CommandJobs';
const OUTPUTS_HINT   = IS_WINDOWS ? 'COPILOT_COWORK\\Outputs'     : '<tooling root>/Outputs';
const DIRECTIVE_HINT = IS_WINDOWS ? 'REM COWORK_OUTPUT: <path>'   : '# COWORK_OUTPUT: <path>';
const JOB_OUTPUT_VAR = IS_WINDOWS ? '%COWORK_JOB_OUTPUT%'         : '$COWORK_JOB_OUTPUT';
const NORMALIZE_HINT = IS_WINDOWS ? 'an LF-only .bat becomes CRLF' : 'a CRLF .sh becomes LF';
const EXAMPLE_FILE   = IS_WINDOWS ? 'reconcile-q3.bat'            : 'reconcile-q3.sh';
const EXAMPLE_NESTED = IS_WINDOWS ? 'jobs\\\\reconcile-q3.bat'    : 'jobs/reconcile-q3.sh';
const REFUSED_HINT   = IS_WINDOWS
  ? 'Absolute, drive-qualified, UNC and environment-variable paths are rejected.'
  : 'Absolute paths, ~ expansion and environment-variable paths are rejected.';

const TOOL = {
  name: 'run_batch_file',
  title: IS_WINDOWS ? 'Run an approved batch file' : 'Run an approved job script',
  description:
    `Execute an existing ${FILE_KIND} file already present under ` +
    `${JOBS_HINT}. Write the script first (filesystem bridge), ` +
    `then pass its RELATIVE name here. Deliverables belong under ${OUTPUTS_HINT}; ` +
    `the script declares its own destination with a "${DIRECTIVE_HINT}" line, ` +
    `which is exposed to it as ${JOB_OUTPUT_VAR}. Returns stdout, stderr, exit code, ` +
    'timing, and the files created or modified. No command, arguments, executable, ' +
    'interpreter, working directory, environment variable, output directory, timeout ' +
    'override or elevation option can be supplied -- the only input is the filename. ' +
    'This response carries the current rules verbatim on the first job of a session ' +
    'and on any job that does not exit clean. Before running, the server rewrites the ' +
    `script's line terminators to the platform convention in place (${NORMALIZE_HINT}) ` +
    'and builds a complete user environment for it (profile variables and ' +
    'the user PATH included); both are reported in the result. '
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
          `Relative filename or relative path of an existing ${FILE_KIND} file under ` +
          `CommandJobs, e.g. "${EXAMPLE_FILE}" or "${EXAMPLE_NESTED}". ${REFUSED_HINT}`
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
        const endings = normalizeLineEndings(real);
        result = await runBatch(real, approvedOutput, endings);
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
  process.stderr.write(`[${SERVER_NAME}] FATAL: required root unavailable: ${e.message}\n`);
  process.exit(1);
}

process.stderr.write(
  `[${SERVER_NAME}] v${SERVER_VERSION} ready. Tool: run_batch_file\n` +
  `[${SERVER_NAME}] scripts: ${realJobRoot()}\n` +
  `[${SERVER_NAME}] outputs: ${realOutputRoot()}\n` +
  `[${SERVER_NAME}] ${ALLOWED_EXT_TEXT} only, relative paths only, 300s timeout, ` +
  `5MB output caps, 1 concurrent job.\n` +
  `[${SERVER_NAME}] line endings normalised to the platform before a run; ` +
  `job environment server-built and complete.\n`);

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
