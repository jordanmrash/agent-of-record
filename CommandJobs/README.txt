COMMANDJOBS -- approved batch scripts for the 8933 Command Bridge
================================================================

This folder is the ONLY place the Command Bridge (port 8933) will execute
anything from. Implementation: Startup\CommandBridge\batch-exec-server.js


WHERE THINGS GO
---------------
  Scripts       COPILOT_COWORK\CommandJobs\        <- .bat / .cmd live here
  Logs          COPILOT_COWORK\CommandJobs\Logs\   <- run records
  Deliverables  COPILOT_COWORK\Outputs\            <- task output lives HERE,
                                                      NOT under CommandJobs

Task output goes to a task-specific folder chosen at the proposal stage:

  COPILOT_COWORK\Outputs\YYYY-MM-DD - Short Descriptive Task Name

  e.g.  Outputs\2026-08-17 - Website PDF Extraction
        Outputs\2026-08-17 - Client Data Files
        Outputs\2026-08-17 - Billing Session Analysis

CommandJobs\Output\ is DEPRECATED and no longer used by the server.


THE WORKFLOW
------------
  1. You describe a task.
  2. Cowork proposes a solution, showing the exact commands AND the exact
     output folder under Outputs.
  3. You approve.
  4. Cowork writes a .bat into this folder (via the 8932 filesystem bridge --
     writing a file is not executing it), containing the approved output path
     on a  REM COWORK_OUTPUT:  line.
  5. Cowork calls run_batch_file with that filename. No second approval.
  6. Cowork returns stdout, stderr, exit code, timing, files created or
     modified, and the output location.

There is NO allowlist of individual script names. Any .bat/.cmd Cowork writes
here can be run. The boundary is the FOLDER and the FILE TYPE, not a list of
approved job names.


THE ONE TOOL
------------
  run_batch_file { "file": "<relative name>.bat" }

That is the entire input surface. No command, arguments, executable,
interpreter, working directory, environment variable, output directory,
timeout override or elevation option can be passed. Extra properties are
rejected. Absolute, drive-qualified, UNC and %VAR% paths are rejected --
supply a path RELATIVE to CommandJobs.


DECLARING THE OUTPUT FOLDER
---------------------------
The script declares its own destination. The server reads this line,
confirms it canonicalises under Outputs, creates it if needed, and exposes
it as %COWORK_JOB_OUTPUT%:

  REM COWORK_OUTPUT: C:\Users\YOURUSER\Documents\COPILOT_COWORK\Outputs\2026-08-17 - Task Name

If the declared path resolves outside Outputs the job is REFUSED -- the
server will not silently redirect it. If no line is present, the job still
runs and %COWORK_JOB_OUTPUT% points at the Outputs root, with nothing
created.


TEMPLATE
--------
  @echo off
  setlocal
  REM COWORK_OUTPUT: C:\Users\YOURUSER\Documents\COPILOT_COWORK\Outputs\2026-08-17 - Short Descriptive Task Name

  echo Job:    %COWORK_JOB_NAME%
  echo Output: %COWORK_JOB_OUTPUT%

  REM ... approved commands here ...

  if errorlevel 1 (
      echo FAILED
      exit /b 1
  )
  echo OK
  exit /b 0

Always end with an explicit  exit /b <code>.


LONG JOBS MUST RUN ASYNC  (added 2026-08-18, SOLVED and verified same day)
--------------------------------------------------------------------------
Verified failure: a 101-second job completed correctly but KILLED the 8933
bridge. run_batch_file returned a server error with no payload and
127.0.0.1:8933 then refused all connections until GO.bat was re-run.

What was tried and MEASURED:
  --stateful --sessionTimeout 1800000   FAILED. 101s job still killed it.
  start /min ... <nul >nul 2>&1         FAILED. A 15s worker still reported
                                        duration_ms 15925, so it is NOT
                                        stdout-pipe inheritance. The executor
                                        waits on the whole PROCESS TREE.
  Windows Task Scheduler                WORKS. Launcher 1906 ms for a 102s
                                        job; bridge answered fine afterwards.

Rule:
  work under ~20 seconds  ->  _template-job.bat        (sync)
  anything longer         ->  _template-async-job.bat  (Task Scheduler)

The async template splits one .bat into two roles. The LAUNCHER runs inside
the bridge and hands the work to Task Scheduler via _async-launch.ps1, then
returns in about two seconds. The WORKER is owned by the Task Scheduler
service, so it is not a descendant of the bridge and can run for hours.

BATTERY TRAP - do not call schtasks.exe directly.
Its defaults are "No Start On Batteries / Stop On Battery Mode". Measured on
this laptop unplugged: the task reported Last Result 0 and produced ZERO
output - a silent no-op. _async-launch.ps1 registers with
-AllowStartIfOnBatteries -DontStopIfGoingOnBatteries and also prints whether
the machine is on battery. Always launch through it.

Authoring rules for async jobs:
  * Set OUT to an ABSOLUTE path in BOTH branches. The worker is started by
    Task Scheduler and does NOT receive %COWORK_JOB_OUTPUT%.
  * Give every job a UNIQUE TaskName, and unregister it when the worker ends.
  * Do not use  call :label  - files written through the 8932 bridge arrive
    LF-only and cmd cannot resolve a called label in an LF-only file.
    Top-level  goto  works. Otherwise run 2026-08-18-fix-crlf.bat first.

In async mode the bridge exit code only says whether the job was LAUNCHED.
The real verdict is in the output folder:

  _job-state.txt   STATUS=RUNNING STARTED=...      still working
                   STATUS=DONE EXIT=0 ENDED=...    success
                   STATUS=DONE EXIT=1 ENDED=...    job reported FAIL
  report.txt       fills in progressively; tail it for progress

Cowork polls those two files with the 8932 filesystem bridge. Launcher exit 3
means refused because a prior run is marked RUNNING (verified 2026-08-18);
exit 1 from the launcher means the scheduled task could not be registered.


IF 8933 IS DOWN
---------------
There is NO fallback execution path. Retry the call once (a single dropped
call is usually the tunnel hop, not the bridge), then stop and report. The
autorun queue that this section used to describe was removed on 2026-08-21
as an unapproved execution path.

LINE ENDINGS - RUN THE NORMALIZER AFTER EVERY BATCH OF WRITES
-------------------------------------------------------------
2026-08-18: 23 of 24 scripts in CommandJobs and Startup were LF-only, which is
how the supergateway install worker managed to exit 1 in under two seconds
without writing a single line - a silent failure that looks like nothing ran.

  CommandJobs\2026-08-18-fix-crlf-all.bat

normalizes every CommandJobs\*.bat and Startup\*.ps1, skips files already
correct, and skips ITSELF (a batch file that rewrites itself while running
shifts cmd's byte offsets mid-parse - the first run tried to execute a command
called 'eady', from the word 'already'). Run it after any batch of file writes
and before executing anything new.


WATCHDOG  (added 2026-08-18)
----------------------------
Scheduled task CoworkBridgeWatchdog runs Startup\_bridge-watchdog.ps1 every
2 minutes. It probes 8931/8932/8933 and restarts ONLY a port that is refusing
connections, with a 5 minute per-port cooldown. It never kills anything.

  Status snapshot (one file, cheap to poll):
    Outputs\2026-08-18 - Bridge Hardening\watchdog\status.txt

A restart is enough only while VS Code is still open, because the dev tunnel's
port forwarding belongs to VS Code. Confirmed by the kill test below: the port
did NOT need to be set back to Public. If VS Code is closed, GO.bat is still
the only fix.

KILL TEST RESULT (2026-08-18) - WHAT IT DOES AND DOES NOT FIX
The 8933 node process was killed deliberately. Measured:
  00:23:19  killed
  00:23:35  watchdog saw it DOWN
  00:23:43  listening again  ->  ~24 seconds, unattended, no GO.bat
Local probe HTTP 400 and PUBLIC TUNNEL probe HTTP 400, both identical to the
untouched 8931/8932 controls. So the process and the tunnel fully recover.

WHAT IT DOES NOT FIX: the Cowork connector could not use the restarted bridge.
run_batch_file failed three times with a server error even though every layer
below it was healthy. The MCP session is bound to the process that died, and
it cannot re-initialize inside an existing chat.

So the practical rule is:
  * a bridge death still costs you the CURRENT conversation
  * it no longer costs you a trip to the machine - the watchdog restores the
    process in ~24s, and a NEW chat should connect straight to it

Re-register with: Startup\_watchdog-install.ps1
Two things that will NOT work there, both measured: an -AtLogOn trigger needs
elevation ("Access is denied"), and -RepetitionDuration ([TimeSpan]::MaxValue)
is rejected as out of range.


CONTROLS
--------
  300 s timeout, then the process TREE is killed (exit code 9999)
  5 MB stdout cap, 5 MB stderr cap, truncation flagged
  1 concurrent job; a second call is refused, not queued
  no elevation, no interactive input, no hidden prompts
  no automatic rerun of a failed script
  the batch file is never deleted after execution

Full details: Startup\CommandBridge\README.txt


RESIDUAL RISK
-------------
The boundary is the FOLDER, not the script CONTENTS. A .bat here may contain
any command Windows can run, including powershell.exe, with your full user
privileges. Your control point is reviewing the proposed commands and output
path before approving. Treat write access to this folder as equivalent to
execute access.
