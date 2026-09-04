@echo off
setlocal
cd /d C:\Users\YOURUSER\Documents\COPILOT_COWORK

rem Built-mode scan. Its own file for the same reason as the APPLY build: the
rem bridge passes no arguments, so "github-01-scan.bat Built" is unreachable.
rem
rem This is the scan that MATTERS. The Source scan predicts from the include and
rem exclude lists; this one inspects what actually landed. They can disagree -
rem an exclusion can be wrong, robocopy can carry something an /XD missed, and
rem the sanitise pass can silently not have run. On this side an unsanitised
rem term is FATAL, not a prediction.

set "GS=C:\Users\YOURUSER\Documents\COPILOT_COWORK\GitHubSetup"

echo === GitHub preflight scan - mode Built
echo Inspects COWORK_PUBLIC, the tree that will actually be pushed.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%GS%\01-preflight-scan.ps1" -Mode Built
set "RC=%ERRORLEVEL%"

echo.
echo === scan exit %RC%
if "%RC%"=="0" (
  echo COWORK_RESULT: OK built tree is clean - safe to add a remote and push
) else if "%RC%"=="1" (
  echo COWORK_RESULT: OK scan complete - findings above, DO NOT PUSH until fixed
) else (
  echo COWORK_RESULT: FAIL scan could not run
)
endlocal & exit /b 0
