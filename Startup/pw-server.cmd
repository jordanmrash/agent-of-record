@echo off
REM ============================================================
REM  Playwright MCP server - child process for supergateway:8931
REM  Location: C:\Users\YOURUSER\Documents\COPILOT_COWORK\Startup\
REM
REM  This file is the source of truth for the 8931 server command.
REM  tasks.json points --stdio at this file; do not copy arguments
REM  back from tasks.json.
REM
REM  Persistent Edge profile (--user-data-dir, no --isolated) is
REM  intentional: the transport is stateless, the browser is not.
REM ============================================================

npx -y @playwright/mcp@latest --browser msedge --user-data-dir C:\Users\YOURUSER\pw-sso-profile --output-dir C:\Users\YOURUSER\Documents\COPILOT_COWORK\playwright-output
