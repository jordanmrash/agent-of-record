@echo off
REM ============================================================
REM  COWORK STANDARD JOB TEMPLATE
REM  Copy this file, rename it, and put the real work in :main.
REM
REM  VERIFIED EXECUTION-ENVIRONMENT FACTS (do not violate):
REM   * The environment is STRIPPED. %LOCALAPPDATA%, %APPDATA% and
REM     %USERPROFILE% expand to EMPTY. Use absolute paths only.
REM     %COWORK_JOB_OUTPUT% is the only reliable supplied variable.
REM   * `timeout /t N` DOES NOT WORK (no stdin). It fails instantly,
REM     so an intended pause silently becomes zero and a later check
REM     may read pre-change state. Use: ping -n N 127.0.0.1 >nul
REM   * %ERRORLEVEL% inside a parenthesized if/else block is stale
REM     (parse-time expansion). Use `if not exist X goto label`.
REM   * Jobs cannot elevate.
REM
REM  CONTRACT: :main must echo exactly one verdict line -
REM     COWORK_RESULT: OK
REM     COWORK_RESULT: FAIL <short reason>
REM  The exit code is derived from it, so the bridge never reports
REM  success for a job that actually failed.
REM ============================================================
REM COWORK_OUTPUT: C:\Users\YOURUSER\Documents\COPILOT_COWORK\Outputs\YYYY-MM-DD - Task Name
setlocal
set "OUT=%COWORK_JOB_OUTPUT%"
if not defined OUT goto no_output
if not exist "%OUT%" mkdir "%OUT%"
set "REPORT=%OUT%\report.txt"
set "STATE=%OUT%\_job-state.txt"

REM --- refuse to start if a previous run is still marked RUNNING ---
if not exist "%STATE%" goto start_job
findstr /b /c:"STATUS=RUNNING" "%STATE%" >nul
if not errorlevel 1 goto already_running

:start_job
echo STATUS=RUNNING STARTED=%DATE% %TIME% > "%STATE%"
call :main > "%REPORT%" 2>&1
type "%REPORT%"
findstr /b /c:"COWORK_RESULT: FAIL" "%REPORT%" >nul
if not errorlevel 1 goto failed
findstr /b /c:"COWORK_RESULT: OK" "%REPORT%" >nul
if errorlevel 1 goto no_verdict
echo STATUS=DONE EXIT=0 ENDED=%DATE% %TIME% > "%STATE%"
endlocal & exit /b 0

:failed
echo STATUS=DONE EXIT=1 ENDED=%DATE% %TIME% > "%STATE%"
endlocal & exit /b 1

:no_verdict
echo BUG: :main emitted no COWORK_RESULT line - treating as failure.
echo STATUS=DONE EXIT=2 ENDED=%DATE% %TIME% > "%STATE%"
endlocal & exit /b 2

:already_running
echo REFUSED: a previous run is still marked RUNNING in "%STATE%".
echo Check that job before re-running. Do NOT assume it failed.
echo COWORK_RESULT: FAIL prior run still in progress
endlocal & exit /b 3

:no_output
echo REFUSED: COWORK_JOB_OUTPUT was not supplied by the executor.
echo COWORK_RESULT: FAIL no output directory
endlocal & exit /b 4


REM ============================================================
REM  JOB LOGIC
REM ============================================================
:main
echo === TASK NAME ===
echo Started %DATE% %TIME%
echo.

REM --- your work goes here ---
REM
REM  Delay (never use timeout):
REM     ping -n 6 127.0.0.1 >nul
REM
REM  Optional parameters written by Cowork just before the run:
REM     if exist "%~dp0job.params.txt" for /f "usebackq tokens=1,* delims==" %%A in ("%~dp0job.params.txt") do set "%%A=%%B"
REM
REM  MANDATORY guard before ANY rd /s /q or del /f /q - a stripped
REM  environment turns an unset variable into an empty string, which
REM  can retarget a recursive delete. Never skip this:
REM     if not defined TARGET goto bad_target
REM     if not exist "%TARGET%" goto bad_target
REM     rd /s /q "%TARGET%"
REM
REM  Inventory destructive work BEFORE doing it so stdout records
REM  exactly what was removed.

echo.
echo Finished %DATE% %TIME%
echo COWORK_RESULT: OK
goto :eof
