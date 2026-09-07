COWORK COMMAND BRIDGE -- port 8933 implementation
=================================================
Startup\CommandBridge\batch-exec-server.js        v1.1.0

Launched by  Startup\exec-server.cmd , which tasks.json points --stdio at.
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
  any colon (blocks ADS)         shell metacharacters (& | < > ^ " ' ` * ? CR LF TAB)
  .. traversal                   NUL bytes, empty, over 240 chars
  extensions other than .bat/.cmd (checked on the CANONICAL path)
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
  environment   minimal and server-built
  retries       none -- a failed script is never rerun automatically
  cleanup       none -- the batch file is deliberately left in place

Exit codes: 9999 timeout, 9998 failed to start, 9997 no exit code reported.

Returned per run: stdout, stderr, exit code, timed_out, start/end/duration,
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
