#!/usr/bin/env bash
# ============================================================
#  Cowork Command Bridge  --  raw stdio MCP server  (port 8933)
#  POSIX sibling of ../exec-server.cmd
#
#  HARDENED. Exposes exactly one tool:
#
#      run_batch_file  { "file": "<relative name>.sh" }
#
#  Executes ONLY existing .sh files that canonicalise under
#  COPILOT_COWORK/CommandJobs. Deliverables belong under
#  COPILOT_COWORK/Outputs. No command strings, executables,
#  interpreters, shell switches, working directories, output
#  paths, timeouts or elevation options may be supplied by the
#  MCP caller.
#
#  The refusals are the same set the Windows launcher enforces,
#  and scripts/exec_bridge_selftest.py proves them on whichever
#  platform the gate runs on. Approved scripts are handed to
#  bash as an argument rather than executed directly, so a
#  missing execute bit is a clear error and a script's own
#  shebang cannot redirect execution elsewhere.
#
#  Implementation:  Startup/CommandBridge/batch-exec-server.js
#  Operating notes: Startup/CommandBridge/README.txt
#
#  Uses the already-installed Node runtime. No npx. No installs.
#  No package dependencies.
# ============================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COWORK_ROOT="$(cd "$HERE/../.." && pwd)"
export COWORK_ROOT

# Optional local overrides (COWORK_CONFIG_ROOT and friends). Gitignored;
# copy cowork-env.example.sh to cowork-env.sh to use it.
[ -f "$HERE/cowork-env.sh" ] && . "$HERE/cowork-env.sh"

mkdir -p "$COWORK_ROOT/CommandJobs" "$COWORK_ROOT/Outputs"
cd "$COWORK_ROOT/CommandJobs"

exec node "$COWORK_ROOT/Startup/CommandBridge/batch-exec-server.js"
