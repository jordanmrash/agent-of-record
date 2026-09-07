@echo off
setlocal
cd /d C:\Users\YOURUSER\Documents\COPILOT_COWORK
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "CommandJobs\github-11-autoscan-built.ps1"
set RC=%ERRORLEVEL%
if %RC%==0 (echo COWORK_RESULT: OK) else (echo COWORK_RESULT: FAIL rc=%RC%)
endlocal & exit /b 0
