@echo off
setlocal
cd /d C:\Users\YOURUSER\Documents\COPILOT_COWORK

rem APPLY variant. It exists as its own file because the 8933 bridge takes a
rem filename and NOTHING else - no arguments - so "github-02-build.bat APPLY"
rem is unreachable through the bridge. Two files, one behaviour each.
rem
rem Writes to COWORK_PUBLIC, deliberately OUTSIDE this repo so cowork-close's
rem `git add -A` can never sweep it in.

set "GS=C:\Users\YOURUSER\Documents\COPILOT_COWORK\GitHubSetup"

echo === Build the clean public repo - APPLY
echo Copies named folders into COWORK_PUBLIC, sanitises, then git init + commit.
echo The source repo is never modified.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%GS%\02-build-clean-repo.ps1" -Apply
set "RC=%ERRORLEVEL%"

echo.
echo === build exit %RC%
if "%RC%"=="0" (
  echo COWORK_RESULT: OK built - now run github-01-scan-built.bat before pushing
) else if "%RC%"=="1" (
  echo COWORK_RESULT: FAIL build refused - see the reason above
) else (
  echo COWORK_RESULT: FAIL build could not run
)
endlocal & exit /b %RC%
