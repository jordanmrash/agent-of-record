@echo off
setlocal
cd /d C:\Users\YOURUSER\Documents\COPILOT_COWORK

set "GS=C:\Users\YOURUSER\Documents\COPILOT_COWORK\GitHubSetup"
set "ARG=%~1"

echo === Build the clean public repo
echo Copies named folders INTO a fresh tree at COWORK_PUBLIC.
echo Never clones, never filters history - that is the whole point.
echo.
if /I "%ARG%"=="APPLY" (
  echo MODE: APPLY - files will be written
) else (
  echo MODE: DRY RUN - pass APPLY as the first argument to write
)
echo.

if /I "%ARG%"=="APPLY" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%GS%\02-build-clean-repo.ps1" -Apply
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%GS%\02-build-clean-repo.ps1"
)
set "RC=%ERRORLEVEL%"

echo.
echo === build exit %RC%
if "%RC%"=="0" (
  echo COWORK_RESULT: OK build step completed - scan the result before pushing
) else if "%RC%"=="1" (
  echo COWORK_RESULT: FAIL build refused - see the reason above
) else (
  echo COWORK_RESULT: FAIL build could not run
)
endlocal & exit /b %RC%
