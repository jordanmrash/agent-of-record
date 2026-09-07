@echo off
REM ============================================================
REM  bridge-restore-tasksjson.bat
REM  Restores .vscode\tasks.json from the known-good snapshot at
REM  Startup\KnownGood\tasks.json. The current file is backed up
REM  first (never overwritten blindly). Also copies both versions
REM  into the output folder for review.
REM
REM  Takes effect only after a VS Code restart (GO.bat).
REM ============================================================
REM COWORK_OUTPUT: C:\Users\YOURUSER\Documents\COPILOT_COWORK\Outputs\2026-08-17 - Bridge Repair Toolkit

setlocal
set "CW=C:\Users\YOURUSER\Documents\COPILOT_COWORK"
set "LIVE=%CW%\Startup\.vscode\tasks.json"
set "GOOD=%CW%\Startup\KnownGood\tasks.json"
set "LOGF=%COWORK_JOB_OUTPUT%\bridge-restore-tasksjson.txt"

call :BODY > "%LOGF%" 2>&1
type "%LOGF%"
exit /b 0

:BODY
echo === RESTORE tasks.json - %DATE% %TIME% ===
echo.
if not exist "%GOOD%" (
  echo ERROR: known-good snapshot missing: %GOOD%
  echo Nothing restored.
  exit /b 1
)

if exist "%LIVE%" (
  copy /y "%LIVE%" "%COWORK_JOB_OUTPUT%\tasks.json.before-restore" >nul
  copy /y "%LIVE%" "%LIVE%.pre-restore.bak" >nul
  echo Backed up current file to:
  echo   %LIVE%.pre-restore.bak
  echo   %COWORK_JOB_OUTPUT%\tasks.json.before-restore
) else (
  echo No live tasks.json found - this will be a fresh install.
)
echo.

copy /y "%GOOD%" "%LIVE%" >nul
if errorlevel 1 (
  echo ERROR: copy failed. Live file unchanged.
  exit /b 1
)
echo Restored known-good tasks.json to %LIVE%
copy /y "%GOOD%" "%COWORK_JOB_OUTPUT%\tasks.json.restored" >nul
echo.

echo --- verification ---
findstr /C:"--stateful" "%LIVE%" >nul 2>&1
if errorlevel 1 (echo   WARNING: --stateful missing after restore) else (echo   OK: --stateful present)
findstr /C:"--isolated" "%LIVE%" >nul 2>&1
if errorlevel 1 (echo   OK: --isolated absent) else (echo   WARNING: --isolated present)
for %%P in (8931 8932 8933) do (
  findstr /C:"\"%%P\"" "%LIVE%" >nul 2>&1
  if errorlevel 1 (echo   WARNING: port %%P not found) else (echo   OK: port %%P configured)
)
echo.
echo NEXT STEP: restart VS Code via GO.bat, then set ports to PUBLIC.
exit /b 0
