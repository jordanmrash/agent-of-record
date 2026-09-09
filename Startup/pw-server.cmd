@echo off
REM ============================================================
REM  Playwright MCP server - child process for supergateway:8931
REM  Location: %COWORK_ROOT%\Startup\  (the Windows twin of
REM  posix\pw-server.sh)
REM
REM  This file is the source of truth for the 8931 server command.
REM  tasks.json points --stdio at this file; do not copy arguments
REM  back from tasks.json.
REM
REM  Persistent Edge profile (--user-data-dir, no --isolated) is
REM  intentional: the transport is stateless, the browser is not.
REM
REM  The browser defaults to msedge on Windows and the profile to
REM  %USERPROFILE%\pw-sso-profile. Override either with
REM  COWORK_PW_BROWSER / COWORK_PW_PROFILE in cowork-env.cmd.
REM ============================================================

set "HERE=%~dp0"
for %%I in ("%HERE%..") do set "COWORK_ROOT=%%~fI"
if exist "%HERE%cowork-env.cmd" call "%HERE%cowork-env.cmd"

if not defined COWORK_PW_BROWSER set "COWORK_PW_BROWSER=msedge"
if not defined COWORK_PW_PROFILE set "COWORK_PW_PROFILE=%USERPROFILE%\pw-sso-profile"

if not exist "%COWORK_PW_PROFILE%\" mkdir "%COWORK_PW_PROFILE%"
if not exist "%COWORK_ROOT%\playwright-output\" mkdir "%COWORK_ROOT%\playwright-output"

npx -y @playwright/mcp@latest --browser %COWORK_PW_BROWSER% --user-data-dir "%COWORK_PW_PROFILE%" --output-dir "%COWORK_ROOT%\playwright-output"
