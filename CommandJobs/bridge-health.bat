@echo off
REM ============================================================
REM  bridge-health.bat  -  read-only diagnostics for 8931/8932/8933
REM  Safe to run at any time. Changes nothing.
REM ============================================================
REM COWORK_OUTPUT: C:\Users\YOURUSER\Documents\COPILOT_COWORK\Outputs\2026-08-17 - Bridge Repair Toolkit

setlocal enabledelayedexpansion
set "CW=C:\Users\YOURUSER\Documents\COPILOT_COWORK"
set "REPORT=%COWORK_JOB_OUTPUT%\bridge-health-report.txt"

call :BODY > "%REPORT%" 2>&1
type "%REPORT%"
exit /b 0

:BODY
echo ============================================================
echo  COWORK BRIDGE HEALTH REPORT
echo  Generated: %DATE% %TIME%
echo ============================================================
echo.
echo --- [1] LOCAL LISTENERS (expect one LISTENING row per port) ---
netstat -ano | findstr /R /C:":8931 " /C:":8932 " /C:":8933 " | findstr LISTENING
if errorlevel 1 echo    NONE FOUND - bridges are not running locally.
echo.
echo --- [2] LOCAL ENDPOINT PROBE (any HTTP status = process alive) ---
for %%P in (8931 8932 8933) do (
  echo   port %%P:
  curl -s -m 5 -o nul -D - http://127.0.0.1:%%P/mcp 2^>nul | findstr /R "^HTTP/"
  if errorlevel 1 echo      NO RESPONSE
)
echo.
echo --- [3] PUBLIC TUNNEL PROBE (401/302 = port is PRIVATE, needs Public) ---
for %%P in (8931 8932 8933) do (
  echo   https://YOUR-TUNNEL-HOST-%%P.use.devtunnels.ms/mcp :
  curl -s -m 10 -o nul -D - https://YOUR-TUNNEL-HOST-%%P.use.devtunnels.ms/mcp 2^>nul | findstr /R "^HTTP/"
  if errorlevel 1 echo      NO RESPONSE
)
echo.
echo --- [4] NODE PROCESSES BOUND TO THE BRIDGE PORTS ---
for %%P in (8931 8932 8933) do (
  set "BPID="
  for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R /C:":%%P " ^| findstr LISTENING') do set "BPID=%%a"
  if defined BPID (
    echo   port %%P  -^>  PID !BPID!
    tasklist /FI "PID eq !BPID!" /FO TABLE /NH
  ) else (
    echo   port %%P  -^>  NO LISTENER
  )
)
echo.
for /f %%n in ('tasklist /FI "IMAGENAME eq node.exe" /FO CSV /NH ^| find /c /v ""') do echo   total node.exe processes on this machine: %%n
echo.
echo --- [5] VS CODE / TUNNEL PROCESSES ---
tasklist /FI "IMAGENAME eq Code.exe" /FO TABLE | findstr /I "Code.exe"
if errorlevel 1 echo    VS Code is NOT running - GO.bat has not been launched.
tasklist /FI "IMAGENAME eq devtunnel.exe" /FO TABLE | findstr /I "devtunnel"
if errorlevel 1 echo    no devtunnel.exe process
echo.
echo --- [6] KEY FILES PRESENT ---
for %%F in (GO.bat pw-server.cmd fs-server.cmd exec-server.cmd) do (
  if exist "%CW%\Startup\%%F" (echo    OK      %%F) else (echo    MISSING %%F)
)
if exist "%CW%\Startup\.vscode\tasks.json" (echo    OK      .vscode\tasks.json) else (echo    MISSING .vscode\tasks.json)
if exist "%CW%\Startup\KnownGood\tasks.json" (echo    OK      KnownGood\tasks.json) else (echo    MISSING KnownGood\tasks.json)
if exist "%CW%\Startup\CommandBridge\batch-exec-server.js" (echo    OK      CommandBridge\batch-exec-server.js) else (echo    MISSING CommandBridge\batch-exec-server.js)
echo.
echo --- [7] 8931 STATEFUL FLAG CHECK ---
REM Comment lines in tasks.json are NOT live flags - ignore // lines when matching.
findstr /C:"--stateful" "%CW%\Startup\.vscode\tasks.json" 2>nul | findstr /V /R /C:"^ *//" >nul
if errorlevel 1 (echo    WARNING: --stateful NOT present. 8931 will fail with "Browser is already in use".) else (echo    OK: --stateful present in tasks.json)
findstr /C:"--isolated" "%CW%\Startup\.vscode\tasks.json" 2>nul | findstr /V /R /C:"^ *//" >nul
if errorlevel 1 (echo    OK: --isolated absent - SSO profile preserved.) else (echo    WARNING: --isolated present - this DESTROYS the pw-sso-profile session.)
echo.
echo --- [8] PLAYWRIGHT PROFILE LOCK ---
if exist "C:\Users\YOURUSER\pw-sso-profile\SingletonLock" (echo    LOCK PRESENT - stale lock likely; run bridge-restart-8931.bat) else (echo    no stale SingletonLock)
echo.
echo --- [9] 5 MOST RECENT COMMAND-BRIDGE LOGS ---
dir /b /o-d "%CW%\CommandJobs\Logs\*.log" 2>nul | findstr /N "^" | findstr /R "^[1-5]:"
if errorlevel 1 echo    no logs found
echo.
echo ============================================================
echo  END OF REPORT
echo ============================================================
exit /b 0
