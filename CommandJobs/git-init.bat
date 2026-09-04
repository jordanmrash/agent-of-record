@echo off
REM COWORK_OUTPUT: Outputs\2026-08-18 - Git Init
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0git-init.ps1"
exit /b %ERRORLEVEL%
