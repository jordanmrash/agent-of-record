@echo off
setlocal
cd /d C:\Users\YOURUSER\Documents\COPILOT_COWORK

set "GS=C:\Users\YOURUSER\Documents\COPILOT_COWORK\GitHubSetup"
set "MODE=%~1"
if "%MODE%"=="" set "MODE=Source"

echo === GitHub preflight scan - mode %MODE%
echo Read-only. Copies nothing.
echo   Source = what WOULD ship from COPILOT_COWORK
echo   Built  = what actually landed in COWORK_PUBLIC
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%GS%\01-preflight-scan.ps1" -Mode %MODE%
set "RC=%ERRORLEVEL%"

echo.
echo === scan exit %RC%
if "%RC%"=="0" (
  echo COWORK_RESULT: OK scan clean - safe to proceed
) else if "%RC%"=="1" (
  echo COWORK_RESULT: OK scan complete - findings listed above, fix before pushing
) else (
  echo COWORK_RESULT: FAIL scan could not run
)
endlocal & exit /b 0
