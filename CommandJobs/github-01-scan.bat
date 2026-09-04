@echo off
setlocal
cd /d C:\Users\YOURUSER\Documents\COPILOT_COWORK

rem Standing job. Lives in CommandJobs so it is bridge-runnable AND gets picked
rem up by the CRLF normalizer - the copies under GitHubSetup are LF-only,
rem because that is how the 8932 bridge writes, and cmd mis-parses those.

set "GS=C:\Users\YOURUSER\Documents\COPILOT_COWORK\GitHubSetup"
set "MODE=%~1"
if "%MODE%"=="" set "MODE=Source"

echo === GitHub preflight scan - mode %MODE%
echo Read-only. Copies nothing, writes nothing.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%GS%\01-preflight-scan.ps1" -Mode %MODE%
set "RC=%ERRORLEVEL%"

echo.
echo === scan exit %RC%
if "%RC%"=="0" (
  echo COWORK_RESULT: OK scan clean
) else if "%RC%"=="1" (
  echo COWORK_RESULT: OK scan complete - findings above, fix before pushing
) else (
  echo COWORK_RESULT: FAIL scan could not run
)
endlocal & exit /b 0
