@echo off
setlocal
cd /d C:\Users\YOURUSER\Documents\COPILOT_COWORK

rem Standing job. DRY RUN unless the first argument is APPLY.
rem Builds COWORK_PUBLIC by copying named folders in - never clone-and-filter.

set "GS=C:\Users\YOURUSER\Documents\COPILOT_COWORK\GitHubSetup"
set "ARG=%~1"

echo === Build the clean public repo
if /I "%ARG%"=="APPLY" (echo MODE: APPLY - files will be written) else (echo MODE: DRY RUN - pass APPLY to write)
echo.

if /I "%ARG%"=="APPLY" goto :apply
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%GS%\02-build-clean-repo.ps1"
set "RC=%ERRORLEVEL%"
goto :done

:apply
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%GS%\02-build-clean-repo.ps1" -Apply
set "RC=%ERRORLEVEL%"

:done
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
