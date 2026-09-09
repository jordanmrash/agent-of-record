@echo off
REM ============================================================
REM  Filesystem MCP server - child process for supergateway:8932
REM  Location: %COWORK_ROOT%\Startup\  (the Windows twin of
REM  posix\fs-server.sh)
REM
REM  This file exists to remove ALL nested quoting. tasks.json
REM  points --stdio at this path (a single token, no spaces),
REM  so nothing can be mangled by cmd or by VS Code's arg parser.
REM
REM  Roots are defined ONLY here. tasks.json and _bridge-watchdog.ps1
REM  both point --stdio at this file and neither lists a root, and
REM  KnownGood holds no copy of it - so no recovery path reverts this.
REM
REM  THREE ROOTS, and the third one matters. The tooling root
REM  (derived from this file's own location) and Downloads are
REM  local. The third is what Cowork itself loads - skills,
REM  instructions and cowork-memory - so the agent can write them
REM  DIRECTLY instead of uploading to the cloud and waiting on
REM  replication (added 2026-08-24; cloud-to-desktop replication
REM  was running hours behind and blocking the git commit of memory
REM  files).
REM
REM  That third root is NOT a fixed path: the OneDrive folder name
REM  depends on the tenant. Set COWORK_CONFIG_ROOT in cowork-env.cmd
REM  (gitignored; copy cowork-env.example.cmd) rather than editing
REM  this file, so a pull does not overwrite it. With it unset, or
REM  pointing at a folder that does not exist, the bridge starts
REM  with two roots and says so on stderr - the upstream server
REM  would otherwise exit at start on a missing root.
REM ============================================================

set "HERE=%~dp0"
for %%I in ("%HERE%..") do set "COWORK_ROOT=%%~fI"
if exist "%HERE%cowork-env.cmd" call "%HERE%cowork-env.cmd"

set "R3="
if defined COWORK_CONFIG_ROOT if exist "%COWORK_CONFIG_ROOT%\" set "R3=1"

if defined R3 (
  npx -y @modelcontextprotocol/server-filesystem "%COWORK_ROOT%" "%USERPROFILE%\Downloads" "%COWORK_CONFIG_ROOT%"
) else (
  echo [fs-server] COWORK_CONFIG_ROOT is not set or is not a directory - starting with two roots. Set it in Startup\cowork-env.cmd. 1>&2
  npx -y @modelcontextprotocol/server-filesystem "%COWORK_ROOT%" "%USERPROFILE%\Downloads"
)
