@echo off
REM ============================================================
REM  Restart the OneDrive client and re-test hydration.
REM
REM  APPROVED BY JORDAN 2026-09-01 as the least invasive step on the
REM  remedy ladder, ahead of onedrive.exe /reset.
REM
REM  Measured first: 149 dehydrated files across 18 areas of the
REM  Cowork tree, 48 of 48 sampled failing to fetch, every failure
REM  returning in about 0.03s. Too fast for a network attempt, so
REM  the client is refusing locally - stuck, not corrupted.
REM
REM  Stops the client, starts it, waits, then re-reads files that
REM  are KNOWN to be failing. Nothing is deleted, no setting is
REM  changed, the sync database is untouched. The cloud stays the
REM  source of truth the whole time.
REM
REM  Success is judged only by a previously-failing file now
REM  reading. A running process proves nothing about hydration.
REM
REM  exit 0  hydration recovered (or was never broken)
REM  exit 1  restarted but hydration still fails - a real finding
REM  exit 2  could not run - NOT a finding
REM ============================================================
REM COWORK_OUTPUT: C:\Users\YOURUSER\Documents\COPILOT_COWORK\Outputs\2026-09-01 - OneDrive Restart
setlocal
set "OUT=%COWORK_JOB_OUTPUT%"
if not defined OUT goto no_output
if not exist "%OUT%" mkdir "%OUT%"
set "REPORT=%OUT%\restart.txt"

call :main > "%REPORT%" 2>&1
type "%REPORT%"
findstr /b /c:"COWORK_RESULT: CANNOTRUN" "%REPORT%" >nul
if not errorlevel 1 goto cannot_run
findstr /b /c:"COWORK_RESULT: FAIL" "%REPORT%" >nul
if not errorlevel 1 goto failed
findstr /b /c:"COWORK_RESULT: OK" "%REPORT%" >nul
if errorlevel 1 goto no_verdict
endlocal & exit /b 0

:failed
endlocal & exit /b 1

:cannot_run
endlocal & exit /b 2

:no_verdict
echo BUG: no COWORK_RESULT line was emitted - treating as could-not-run.
endlocal & exit /b 2

:no_output
echo COWORK_RESULT: CANNOTRUN no output directory
endlocal & exit /b 2


REM ============================================================
:main
set "JOBS=C:\Users\YOURUSER\Documents\COPILOT_COWORK\CommandJobs"
set "SK=C:\Users\YOURUSER\OneDrive\Documents\Cowork\Skills"

if not exist "%JOBS%\2026-09-01-restart-onedrive.ps1" goto no_checker

cd /d "%JOBS%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%JOBS%\2026-09-01-restart-onedrive.ps1" -SkillsRoot "%SK%" -SettleSeconds 90 -PollSeconds 10
goto :eof

:no_checker
echo The restart script is missing from CommandJobs.
echo That is NOT a finding about OneDrive.
echo COWORK_RESULT: CANNOTRUN restart script not found
goto :eof
