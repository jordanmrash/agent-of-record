@echo off
setlocal
cd /d C:\Users\YOURUSER\Documents\COPILOT_COWORK

rem Auto-derive candidate client, person and org names from the BUILT tree, so
rem the denylist does not have to be typed. Read-only, reports only.

echo === Auto-scan the built tree for name-shaped tokens
echo No typing required. This finds the candidates instead of asking for them.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\YOURUSER\Documents\COPILOT_COWORK\CommandJobs\github-04-autoscan-names.ps1"
set "RC=%ERRORLEVEL%"

echo.
echo === exit %RC%
if "%RC%"=="0" (
  echo COWORK_RESULT: OK candidates listed - read them, nothing was changed
) else (
  echo COWORK_RESULT: FAIL could not scan - is the tree built?
)
endlocal & exit /b %RC%
