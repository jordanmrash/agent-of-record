@echo off
REM ============================================================
REM  COWORK ASYNC JOB TEMPLATE  (v3 - 2026-08-18)
REM
REM  WHY THIS EXISTS - MEASURED, NOT GUESSED
REM  The 8933 executor holds the run_batch_file call open for the whole
REM  PROCESS TREE, and a call held open past roughly a minute kills the
REM  bridge (127.0.0.1:8933 then refuses connections).
REM    * --stateful --sessionTimeout: did NOT fix it (tested, 101s job).
REM    * start /min ... <nul >nul 2>&1: did NOT fix it. A 15s worker
REM      still reported duration_ms 15925, so it is not stdout-pipe
REM      inheritance - the executor waits on the tree.
REM    * Task Scheduler DOES fix it. The worker belongs to the Task
REM      Scheduler service, not to the bridge, so the launcher returns
REM      in ~2s no matter how long the work takes. Measured: launcher
REM      1860 ms, worker 15.5s, STATUS=DONE EXIT=0.
REM
REM  BATTERY TRAP - do not use raw schtasks.exe
REM  schtasks.exe defaults to "No Start On Batteries / Stop On Battery
REM  Mode". On this laptop unplugged that produced Last Result 0 and
REM  ZERO output - a silent no-op. _async-launch.ps1 registers the task
REM  with -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries, so it
REM  runs on battery too. Always launch through that script.
REM
REM  RULE OF THUMB
REM    work under ~20s  -> _template-job.bat (sync, exit code is verdict)
REM    anything longer  -> this template (verdict in _job-state.txt)
REM
REM  CONTRACT
REM  The bridge exit code only says whether the job was LAUNCHED.
REM  The real verdict is the last line of _job-state.txt:
REM     STATUS=RUNNING STARTED=...        still working
REM     STATUS=DONE EXIT=0 ENDED=...      success
REM     STATUS=DONE EXIT=1 ENDED=...      job reported COWORK_RESULT: FAIL
REM  Launcher exit 3 = refused, a prior run is still RUNNING.
REM  Poll _job-state.txt through the 8932 filesystem bridge; report.txt
REM  fills in progressively and can be tailed for progress.
REM
REM  AUTHORING RULES (violating these has bitten us before)
REM   * Set OUT as an ABSOLUTE path in BOTH branches. The worker is
REM     started by Task Scheduler and does NOT receive
REM     %COWORK_JOB_OUTPUT%; the environment is stripped, so
REM     %USERPROFILE% / %APPDATA% / %LOCALAPPDATA% are EMPTY.
REM   * Give every job a UNIQUE TaskName below.
REM   * Do not use `call :label`. Files written through the 8932 bridge
REM     arrive LF-only and cmd cannot resolve a called label in an
REM     LF-only file. Top-level `goto` works. If you must use labels,
REM     run 2026-08-18-fix-crlf.bat first.
REM   * `timeout /t N` does not work (no stdin). Use: ping -n N 127.0.0.1 >nul
REM   * %VAR% inside a parenthesized for/if block expands at PARSE time.
REM     Use setlocal enabledelayedexpansion and !VAR! inside loops.
REM   * Guard every destructive command:
REM       if not defined TARGET goto bad_target
REM       if not exist "%TARGET%" goto bad_target
REM   * Jobs cannot elevate.
REM ============================================================
REM COWORK_OUTPUT: C:\Users\YOURUSER\Documents\COPILOT_COWORK\Outputs\YYYY-MM-DD - Task Name

set "OUT=C:\Users\YOURUSER\Documents\COPILOT_COWORK\Outputs\YYYY-MM-DD - Task Name"
set "TASKNAME=CoworkJob_ChangeMe"

if /i "%~1"=="WORKER" goto worker

REM ---------- LAUNCHER: returns in ~2s, does no real work ----------
if not exist "%OUT%" mkdir "%OUT%"
if not exist "%OUT%\_job-state.txt" goto launch
findstr /b /c:"STATUS=RUNNING" "%OUT%\_job-state.txt" >nul
if not errorlevel 1 goto already_running

:launch
echo STATUS=RUNNING STARTED=%DATE% %TIME% JOB=%~nx0 > "%OUT%\_job-state.txt"
echo (worker starting - this file fills in as the job runs) > "%OUT%\report.txt"
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\YOURUSER\Documents\COPILOT_COWORK\CommandJobs\_async-launch.ps1" -Script "%~f0" -TaskName %TASKNAME%
if errorlevel 1 goto launch_failed
echo === ASYNC LAUNCH ===
echo Job    : %~nx0
echo Output : %OUT%
echo The work now runs under Task Scheduler, detached from this bridge call.
echo Poll _job-state.txt until STATUS=DONE. Tail report.txt for progress.
echo COWORK_RESULT: OK launched
exit /b 0

:launch_failed
echo STATUS=DONE EXIT=1 ENDED=%DATE% %TIME% launch failed > "%OUT%\_job-state.txt"
echo COWORK_RESULT: FAIL could not register or start the scheduled task
exit /b 1

:already_running
echo REFUSED: a previous run is still marked RUNNING in "%OUT%\_job-state.txt".
echo Check that job before re-running. Do NOT assume it failed.
echo COWORK_RESULT: FAIL prior run still in progress
exit /b 3

REM ---------- WORKER: detached, may run for hours ----------
:worker
setlocal enabledelayedexpansion
set "REPORT=%OUT%\report.txt"
set "STATE=%OUT%\_job-state.txt"

echo === TASK NAME === > "%REPORT%"
echo Started %DATE% !TIME! >> "%REPORT%"

REM ---------- your work goes here, appending to "%REPORT%" ----------
REM   delay:                 ping -n 6 127.0.0.1 >nul
REM   per-iteration stamp:   use !TIME! inside loops, never %%TIME%%
REM   on failure:            goto w_failed
REM ------------------------------------------------------------------

echo Finished %DATE% !TIME! >> "%REPORT%"
echo COWORK_RESULT: OK >> "%REPORT%"
echo STATUS=DONE EXIT=0 ENDED=%DATE% !TIME! > "%STATE%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Unregister-ScheduledTask -TaskName '%TASKNAME%' -Confirm:$false" >nul 2>&1
endlocal
exit /b 0

:w_failed
echo COWORK_RESULT: FAIL >> "%REPORT%"
echo STATUS=DONE EXIT=1 ENDED=%DATE% !TIME! > "%STATE%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Unregister-ScheduledTask -TaskName '%TASKNAME%' -Confirm:$false" >nul 2>&1
endlocal
exit /b 1
