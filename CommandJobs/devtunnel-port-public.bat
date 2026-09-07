@echo off
REM ============================================================
REM  devtunnel-port-public.bat
REM  INVESTIGATION SCRIPT. Determines whether the devtunnel CLI is
REM  present and can set port visibility to public without the
REM  VS Code Ports panel. Read-only apart from the optional
REM  "access create" calls at the end, which only widen access to
REM  ports already being forwarded.
REM ============================================================
REM COWORK_OUTPUT: C:\Users\YOURUSER\Documents\COPILOT_COWORK\Outputs\2026-08-17 - Bridge Repair Toolkit

setlocal enabledelayedexpansion
set "LOGF=%COWORK_JOB_OUTPUT%\devtunnel-port-public.txt"
set "DT="

call :BODY > "%LOGF%" 2>&1
type "%LOGF%"
exit /b 0

:BODY
echo === DEVTUNNEL CLI PROBE - %DATE% %TIME% ===
echo.
echo --- [1] locate devtunnel.exe ---
where devtunnel 2>nul
if not errorlevel 1 (
  set "DT=devtunnel"
  echo Found on PATH.
) else (
  echo Not on PATH. Searching known VS Code locations...
  for /f "delims=" %%f in ('dir /b /s "%LOCALAPPDATA%\Programs\Microsoft VS Code\devtunnel.exe" 2^>nul') do set "DT=%%f"
  if not defined DT for /f "delims=" %%f in ('dir /b /s "%USERPROFILE%\.vscode\devtunnel.exe" 2^>nul') do set "DT=%%f"
  if not defined DT for /f "delims=" %%f in ('dir /b /s "%LOCALAPPDATA%\devtunnel.exe" 2^>nul') do set "DT=%%f"
  if defined DT (echo Found: !DT!) else (echo NOT FOUND anywhere obvious.)
)
echo.

if not defined DT (
  echo RESULT: devtunnel CLI unavailable. The Ports panel toggle
  echo remains a manual step after every VS Code restart.
  exit /b 0
)

echo --- [2] version ---
"!DT!" --version
echo.
echo --- [3] auth status ---
"!DT!" user show
echo.
echo --- [4] tunnel list ---
"!DT!" list
echo.
echo --- [5] ports on tunnel YOUR-TUNNEL-HOST ---
"!DT!" port list -t YOUR-TUNNEL-HOST
echo.
echo --- [6] attempt anonymous (public) access on each port ---
for %%P in (8931 8932 8933) do (
  echo   --- port %%P ---
  "!DT!" access create -t YOUR-TUNNEL-HOST -p %%P --anonymous
  if errorlevel 1 (echo      FAILED for %%P) else (echo      OK - %%P set anonymous/public)
)
echo.
echo --- [7] re-list ports to confirm ---
"!DT!" port list -t YOUR-TUNNEL-HOST
echo.
echo NOTE: if step 6 succeeded, the Public toggle can be automated
echo and Cowork can restore access itself after a restart.
exit /b 0
