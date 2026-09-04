@echo off
setlocal
cd /d C:\Users\YOURUSER\Documents\COPILOT_COWORK

rem The cut that matters. github-04 sorted by frequency, which buries a client
rem name under the word "Key". A client name is RARE - this looks for the SHAPE
rem instead: two capitalised words in a row, and words appearing in one file only.

echo === Two-word proper nouns and one-off mentions in the built tree
echo Read-only. No typing required.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\YOURUSER\Documents\COPILOT_COWORK\CommandJobs\github-05-autoscan-orgnames.ps1"
set "RC=%ERRORLEVEL%"

echo.
echo === exit %RC%
if "%RC%"=="0" (
  echo COWORK_RESULT: OK candidates listed - nothing was changed
) else (
  echo COWORK_RESULT: FAIL could not scan - is the tree built?
)
endlocal & exit /b %RC%
