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
#
#  Finding node. A desktop app that starts this launcher as a
#  child process hands it a minimal PATH (on macOS typically
#  /usr/bin:/bin:/usr/sbin:/sbin), which holds no node at all.
#  So the launcher looks where macOS installs actually put it,
#  honours COWORK_NODE from cowork-env.sh first, and if nothing
#  is found says so on stderr, where the host's per-server log
#  will show it, instead of dying with a bare "command not found".
# ============================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COWORK_ROOT="$(cd "$HERE/../.." && pwd)"
export COWORK_ROOT

# Optional local overrides (COWORK_CONFIG_ROOT, COWORK_NODE and friends).
# Gitignored; copy cowork-env.example.sh to cowork-env.sh to use it.
[ -f "$HERE/cowork-env.sh" ] && . "$HERE/cowork-env.sh"

# Where node tends to live when the caller's PATH does not say.
export PATH="$HOME/.local/bin:$HOME/.local/node/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

NODE_BIN="${COWORK_NODE:-}"
if [ -z "$NODE_BIN" ]; then
  NODE_BIN="$(command -v node 2>/dev/null || true)"
fi
if [ -z "$NODE_BIN" ] || [ ! -x "$NODE_BIN" ]; then
  echo "exec-server.sh: node was not found (COWORK_NODE='${COWORK_NODE:-}', PATH='$PATH')." >&2
  echo "exec-server.sh: install Node 20 or later, or set COWORK_NODE in Startup/posix/cowork-env.sh," >&2
  echo "exec-server.sh: or run Startup/posix/install-mac.sh, which does both." >&2
  exit 127
fi

mkdir -p "$COWORK_ROOT/CommandJobs" "$COWORK_ROOT/Outputs"
cd "$COWORK_ROOT/CommandJobs"

exec "$NODE_BIN" "$COWORK_ROOT/Startup/CommandBridge/batch-exec-server.js"
