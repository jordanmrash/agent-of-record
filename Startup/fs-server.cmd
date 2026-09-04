@echo off
REM ============================================================
REM  Filesystem MCP server - child process for supergateway:8932
REM  Location: C:\Users\YOURUSER\Documents\COPILOT_COWORK\Startup\
REM
REM  This file exists to remove ALL nested quoting. tasks.json
REM  points --stdio at this path (a single token, no spaces),
REM  so nothing can be mangled by cmd or by VS Code's arg parser.
REM
REM  2026-08-24: ADDED the OneDrive Cowork root. Skills and
REM  cowork-memory can now be written DIRECTLY instead of uploaded
REM  to the cloud and waited on. Cloud-to-desktop replication was
REM  running hours behind and blocking the git commit of memory
REM  files; writing locally reverses the direction so OneDrive
REM  syncs UP and the repo sees the change immediately.
REM
REM  Roots are defined ONLY here. tasks.json and _bridge-watchdog.ps1
REM  both point --stdio at this file and neither lists a root, and
REM  KnownGood holds no copy of it - so no recovery path reverts this.
REM
REM  ROLLBACK: restore the original single line -
REM  npx -y @modelcontextprotocol/server-filesystem C:\Users\YOURUSER\Documents\COPILOT_COWORK C:\Users\YOURUSER\Downloads
REM ============================================================

npx -y @modelcontextprotocol/server-filesystem C:\Users\YOURUSER\Documents\COPILOT_COWORK C:\Users\YOURUSER\Downloads "C:\Users\YOURUSER\OneDrive\Documents\Cowork"
