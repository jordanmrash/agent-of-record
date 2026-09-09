COWORK COMMAND BRIDGE -- port 8933 implementation
=================================================
Startup\CommandBridge\batch-exec-server.js        v1.3.0

Launched by  Startup\exec-server.cmd  on Windows and  Startup/posix/exec-server.sh
on macOS and Linux; tasks.json points --stdio at whichever fits the host.

PLATFORM. One source file runs on both. The platform decides four things and
no security property: the shell (cmd.exe /d /s /c vs /bin/bash <script>), the
executable extension (.bat/.cmd vs .sh), the comment marker the COWORK_OUTPUT
directive hides behind (REM/:: vs #), and how a runaway process tree is killed
(taskkill /T vs a process-group SIGKILL). Everything in PATH BOUNDARY below is
one implementation used by both, and scripts/exec_bridge_selftest.py starts the
real server and tries forty ways out of it in the host's own script
language - so a refusal that held on one platform and not the other fails the
gate rather than shipping. The tooling root comes from COWORK_ROOT, set by the
launcher, never from the MCP caller, who cannot set an environment variable
through the one tool this server exposes.
Plain Node, already installed. No npx, no installs, no package dependencies,
nothing fetched from the network at start time.


THE ONE TOOL
------------
  run_batch_file { "file": "<relative filename or relative path under CommandJobs>" }

Input schema, exactly:
  type                  object
  properties.file       string, required
  additionalProperties  false

Deliberately absent -- there is no parameter for any of these:
  command      arguments    executable    interpreter
  workingDir   environment  outputDir     timeout override    elevation

Extra JSON properties are rejected before validation begins.


PATH BOUNDARY
-------------
The file must resolve under COPILOT_COWORK\CommandJobs. Rejected:

  absolute paths                 environment-variable paths (%VAR%, $env:, ${})
  drive-qualified paths (C:\,C:) home-relative paths (~)
  UNC / network (\\server\share) URL-style paths (file://, http://)
  any colon (blocks ADS)         shell metacharacters (& | ; < > ^ " ' ` $ * ? CR LF TAB)
  .. traversal                   NUL bytes, empty, over 240 chars
  extensions other than .bat/.cmd on Windows, .sh on POSIX (checked on the CANONICAL path)
  nonexistent files              directories        non-regular files
  symlinks/junctions escaping CommandJobs           anything under Logs\

Containment is decided by canonicalising BOTH sides with the OS realpath
(fs.realpathSync.native) and comparing with path.relative -- never a string
prefix test. "CommandJobsEvil" cannot masquerade as "CommandJobs", and a
junction planted inside CommandJobs is caught after resolution.


OUTPUT ORGANISATION
-------------------
  Scripts       COPILOT_COWORK\CommandJobs\
  Logs          COPILOT_COWORK\CommandJobs\Logs\
  Deliverables  COPILOT_COWORK\Outputs\<YYYY-MM-DD - Short Descriptive Task Name>\

The server NEVER invents or substitutes an output folder, and never redirects
to CommandJobs\Output. The approved batch file declares its own destination:

    REM COWORK_OUTPUT: C:\Users\YOURUSER\Documents\COPILOT_COWORK\Outputs\2026-08-17 - Website PDF Extraction

The server reads that directive from the approved file, verifies it
canonicalises under COPILOT_COWORK\Outputs, creates it if absent, re-checks
after creation to catch a planted junction, and exposes it as
%COWORK_JOB_OUTPUT%.

  directive present, inside Outputs   -> used, created if needed
  directive present, outside Outputs  -> job REFUSED (never silently redirected)
  directive absent                    -> %COWORK_JOB_OUTPUT% = Outputs root,
                                         nothing created, nothing invented

This keeps the destination under Jordan's control at approval time: it lives
in the file he reviewed, and the MCP caller cannot pass an output path.

Environment handed to the script (server-built; caller contributes nothing):
  %COWORK_JOB_OUTPUT%    approved task-output folder
  %COWORK_OUTPUT_ROOT%   COPILOT_COWORK\Outputs
  %COWORK_JOB_ROOT%      COPILOT_COWORK\CommandJobs
  %COWORK_JOB_NAME%      script base name
  %COWORK_JOB_TAG%       name_timestamp, matching the log filenames

Plus, since v1.3.0, a COMPLETE user environment -- what an interactive session
of the same account would carry:
  Windows  SystemRoot, windir, SystemDrive, ComSpec, PATHEXT, COMPUTERNAME,
           USERNAME, USERPROFILE, HOMEDRIVE, HOMEPATH, APPDATA, LOCALAPPDATA,
           ProgramData, ProgramFiles, ProgramFiles(x86), ProgramW6432, TEMP,
           TMP, NUMBER_OF_PROCESSORS, and Path = the machine PATH the server
           was started with followed by the user's PATH from HKCU\Environment
           (%VAR% references expanded)
  POSIX    PATH (the server's, plus ~/.local/bin, ~/bin, /opt/homebrew/bin,
           /opt/homebrew/sbin, /usr/local/bin, /usr/local/sbin where they
           exist), HOME, USER, LOGNAME, SHELL, LANG, TMPDIR
Every value the launching process supplied is kept; the rest is DERIVED from
the account the server runs as (os.homedir, os.userInfo, the registry) -- never
from the MCP caller, who still has no parameter that reaches the environment.
Until 1.3.0 a bridge started by the scheduled-task watchdog handed its jobs an
environment with the profile variables empty and only the machine PATH, so
per-user tools had to be located by hand inside every script. The result
reports user_path_entries, the number of user PATH entries appended.

Line endings (v1.3.0): before a script runs, its line terminators are rewritten
to the platform's convention IN PLACE -- an LF-only .bat/.cmd becomes CRLF on
Windows (cmd.exe mis-parses LF-only files silently), a CRLF .sh becomes LF on
POSIX (bash rejects CR). Nothing but the terminators changes; a file that
already mixes both is left alone. The result reports line_endings as one of
unchanged, lf-to-crlf, crlf-to-lf, mixed-left-alone, skipped-large,
not-writable, unreadable.


EXECUTION CONTROLS
------------------
  timeout       300 s fixed, then the whole process TREE is killed
                (taskkill /T /F), reported as exit code 9999
  stdout cap    5 MB, flagged truncated beyond that
  stderr cap    5 MB, flagged truncated beyond that
  concurrency   1; a second call is refused, not queued
  elevation     none -- signed-in user, never elevated, no new console
  stdin         closed -- no interactive input is possible
  window        hidden (windowsHide) -- nothing can prompt
  cmd.exe flags /d /s /c, server-supplied (/d skips AutoRun registry hooks)
  environment   server-built and COMPLETE (profile variables and the user PATH
                derived from the account; the caller contributes nothing)
  line endings  rewritten to the platform convention in place before the run;
                mixed files left alone; reported as line_endings
  retries       none -- a failed script is never rerun automatically
  cleanup       none -- the batch file is deliberately left in place

Exit codes: 9999 timeout, 9998 failed to start, 9997 no exit code reported.

Returned per run: stdout, stderr, exit code, timed_out, start/end/duration,
line_endings, user_path_entries,
files created / modified / deleted across CommandJobs and Outputs, the
output folder and its files, and the log path.

Logs, per run, in CommandJobs\Logs\:
  NAME_<timestamp>.log    human-readable, AUTORUN.ps1 conventions
  NAME_<timestamp>.exit   exit code alone
  NAME_<timestamp>.json   full structured result


BATCH TEMPLATE
--------------
  @echo off
  setlocal
  REM COWORK_OUTPUT: C:\Users\YOURUSER\Documents\COPILOT_COWORK\Outputs\2026-08-17 - Short Descriptive Task Name

  echo Job:    %COWORK_JOB_NAME%
  echo Output: %COWORK_JOB_OUTPUT%

  REM ... approved commands here, writing deliverables to %COWORK_JOB_OUTPUT% ...

  if errorlevel 1 (
      echo FAILED
      exit /b 1
  )
  echo OK
  exit /b 0

Always end with an explicit  exit /b <code>  so the exit code is meaningful.


RESIDUAL RISK
-------------
The boundary is the FOLDER and FILE TYPE, not script CONTENTS. A .bat inside
CommandJobs may contain any command Windows can run, including powershell.exe,
with full user privileges. That is inherent to the approved workflow: Cowork
authors a new script per task, so contents cannot be pre-approved by a list.

The control point is the proposal stage -- reviewing the exact commands and
the output path before approving. The server guarantees only that nothing runs
except a .bat/.cmd placed in CommandJobs, and that deliverables cannot be
written outside Outputs by way of the declared directive.

Anything able to write into CommandJobs can cause execution on the next
run_batch_file call. Treat write access to CommandJobs as execute access.


FILE MAP
--------
  Startup\exec-server.cmd                       launcher (tasks.json --stdio target)
  Startup\CommandBridge\batch-exec-server.js    implementation (this server)
  Startup\CommandBridge\README.txt              this file
  Startup\batch-exec-server.js                  OBSOLETE loose copy, retained as a
                                                backup during testing -- not launched
  Startup\exec-server.cmd.20260817-005145.bak   previous hardened launcher
  Startup\exec-server.cmd.unrestricted-backup   original unsafe launcher
  CommandJobs\README.txt                        workflow notes
  CommandJobs\README.txt.20260817-005145.bak    previous workflow notes
