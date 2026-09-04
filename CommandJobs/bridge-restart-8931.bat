@echo off
REM ============================================================
REM  bridge-restart-8931.bat
REM  Clears the Playwright side ONLY. Kills whatever listens on
REM  8931 (plus its child tree) and removes a stale SSO profile
REM  lock. Does NOT touch 8932 or 8933, so the command bridge
REM  stays connected while this runs.
REM
REM  After this completes, re-run the "Cowork Playwright Bridge
REM  (8931)" task in VS Code (Terminal > Run Task) - or run
REM  bridge-restart-all.bat for a full relaunch.
REM ============================================================
REM COWORK_OUTPUT: C:\Users\YOURUSER\Documents\COPILOT_COWORK\Outputs\2026-08-17 - Bridge Repair Toolkit

setlocal enabledelayedexpansion
set "LOGF=%COWORK_JOB_OUTPUT%\bridge-restart-8931.txt"

call :BODY > "%LOGF%" 2>&1
type "%LOGF%"
exit /b 0

:BODY
echo === RESTART 8931 (Playwright only) - %DATE% %TIME% ===
echo.
set "FOUND=0"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R /C:":8931 " ^| findstr LISTENING') do (
  echo Killing PID %%a and its child tree...
  taskkill /PID %%a /T /F
  set "FOUND=1"
)
if "!FOUND!"=="0" echo Nothing was listening on 8931.
echo.
echo --- stale profile lock ---
if exist "C:\Users\YOURUSER\pw-sso-profile\SingletonLock" (
  del /f /q "C:\Users\YOURUSER\pw-sso-profile\SingletonLock"
  echo Removed SingletonLock.
) else (
  echo No SingletonLock present.
)
if exist "C:\Users\YOURUSER\pw-sso-profile\SingletonCookie" del /f /q "C:\Users\YOURUSER\pw-sso-profile\SingletonCookie" >nul 2>&1
echo.
echo --- verification ---
netstat -ano | findstr /R /C:":8931 " | findstr LISTENING
if errorlevel 1 (echo 8931 is now free.) else (echo WARNING: something is still listening on 8931.)
echo.
echo 8932/8933 left untouched:
netstat -ano | findstr /R /C:":8932 " /C:":8933 " | findstr LISTENING
echo.
echo NEXT STEP: re-run the 8931 task in VS Code, or bridge-restart-all.bat
exit /b 0
