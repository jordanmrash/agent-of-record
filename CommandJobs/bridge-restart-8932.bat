@echo off
REM ============================================================
REM  bridge-restart-8932.bat
REM  Restarts the FILESYSTEM bridge ONLY, to pick up a change to
REM  Startup\fs-server.cmd (the allowed-roots definition).
REM  Leaves 8931 and 8933 untouched, so the command bridge stays
REM  connected and can verify the result.
REM
REM  A VS Code restart alone does NOT apply an fs-server.cmd change:
REM  the existing listener keeps the port and the new roots never
REM  take effect. PID turnover is the only proof it is live.
REM
REM  Relaunch uses Start-Process so the new listener is detached and
REM  survives this job exiting - a `start /b` child would be taken
REM  down with the job's process tree.
REM ============================================================
REM COWORK_OUTPUT: C:\Users\YOURUSER\Documents\COPILOT_COWORK\Outputs\2026-08-24 - Bridge Scope Change
setlocal enabledelayedexpansion
set "STARTUP=C:\Users\YOURUSER\Documents\COPILOT_COWORK\Startup"
set "SG=%STARTUP%\node_modules\supergateway\dist\index.js"
set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"

echo === [1] LIVE ROOTS IN fs-server.cmd ===
findstr /b /c:"npx" "%STARTUP%\fs-server.cmd"

echo.
echo === [2] BEFORE - all three listeners ===
netstat -ano | findstr /R /C:":8931 " /C:":8932 " /C:":8933 " | findstr LISTENING

echo.
echo === [3] KILL 8932 ONLY ===
set "OLDPID=none"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R /C:":8932 " ^| findstr LISTENING') do set "OLDPID=%%a"
echo old 8932 PID: !OLDPID!
if "!OLDPID!"=="none" echo Nothing was listening on 8932.
if not "!OLDPID!"=="none" taskkill /PID !OLDPID! /T /F

ping -n 4 127.0.0.1 >nul

echo.
echo === [4] RELAUNCH 8932 DETACHED ===
"%PS%" -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'node' -ArgumentList '%SG%','--port','8932','--outputTransport','streamableHttp','--stdio','%STARTUP%\fs-server.cmd' -WorkingDirectory '%STARTUP%' -WindowStyle Hidden"
echo relaunch issued, waiting for the listener to bind...
ping -n 12 127.0.0.1 >nul

echo.
echo === [5] AFTER - all three listeners ===
netstat -ano | findstr /R /C:":8931 " /C:":8932 " /C:":8933 " | findstr LISTENING

echo.
echo === [6] PID TURNOVER CHECK ===
set "NEWPID=none"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R /C:":8932 " ^| findstr LISTENING') do set "NEWPID=%%a"
echo old 8932 PID: !OLDPID!
echo new 8932 PID: !NEWPID!
if "!NEWPID!"=="none" echo RESULT: 8932 did NOT come back - the watchdog should retry within 2 minutes.
if "!NEWPID!"=="!OLDPID!" echo RESULT: PID UNCHANGED - the old process kept the port, change is NOT live.
if not "!NEWPID!"=="!OLDPID!" if not "!NEWPID!"=="none" echo RESULT: PID CHANGED - the new roots are live.

echo.
echo === [7] LOCAL PROBE - any HTTP status means the process answers ===
curl -s -i -m 5 http://127.0.0.1:8932/mcp 2>nul | findstr /b "HTTP/"

echo.
echo COWORK_RESULT: OK
endlocal
exit /b 0
