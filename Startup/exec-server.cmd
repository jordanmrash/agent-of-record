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
REM  %COWORK_ROOT%\CommandJobs. Deliverables belong under
REM  %COWORK_ROOT%\Outputs. No command strings, executables,
REM  interpreters, cmd.exe switches, working directories, output
REM  paths, timeouts or elevation options may be supplied by the
REM  MCP caller.
REM
REM  COWORK_ROOT is derived from this file's own location - the
REM  clone can live in any directory. The Windows twin of
REM  posix\exec-server.sh. Optional overrides (COWORK_CONFIG_ROOT
REM  and friends) come from cowork-env.cmd beside this file, which
REM  is gitignored; copy cowork-env.example.cmd to create it.
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

set "HERE=%~dp0"
for %%I in ("%HERE%..") do set "COWORK_ROOT=%%~fI"
if exist "%HERE%cowork-env.cmd" call "%HERE%cowork-env.cmd"

if not exist "%COWORK_ROOT%\CommandJobs\" mkdir "%COWORK_ROOT%\CommandJobs"
if not exist "%COWORK_ROOT%\Outputs\" mkdir "%COWORK_ROOT%\Outputs"
cd /d "%COWORK_ROOT%\CommandJobs"

node "%COWORK_ROOT%\Startup\CommandBridge\batch-exec-server.js"
