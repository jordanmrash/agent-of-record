@echo off
REM ============================================================
REM  Cowork Command Bridge  --  raw stdio MCP server  (port 8933)
REM
REM  HARDENED. Does not launch mcp-server-commands, which accepted
REM  arbitrary command strings. Launches a local, zero-dependency
REM  server exposing exactly one tool:
REM
REM      run_batch_file  { "file": "<relative name>.bat" }
REM
REM  Executes ONLY existing .bat/.cmd files that canonicalise under
REM  COPILOT_COWORK\CommandJobs. Deliverables belong under
REM  COPILOT_COWORK\Outputs. No command strings, executables,
REM  interpreters, cmd.exe switches, working directories, output
REM  paths, timeouts or elevation options may be supplied by the
REM  MCP caller.
REM
REM  Implementation:  Startup\CommandBridge\batch-exec-server.js
REM  Operating notes: Startup\CommandBridge\README.txt
REM
REM  Uses the already-installed Node runtime. No npx. No installs.
REM  No package dependencies.
REM
REM  Supergateway is invoked by tasks.json, which points --stdio at
REM  this file -- unchanged.
REM
REM  Backups: exec-server.cmd.20260817-005145.bak   (previous hardened)
REM           exec-server.cmd.unrestricted-backup   (original, unsafe)
REM ============================================================

cd /d "C:\Users\YOURUSER\Documents\COPILOT_COWORK\CommandJobs"

node "C:\Users\YOURUSER\Documents\COPILOT_COWORK\Startup\CommandBridge\batch-exec-server.js"
