#!/usr/bin/env bash
# ============================================================
#  Cowork Power Automate Bridge -- raw stdio MCP server (8934)
#  POSIX sibling of ../flow-server.cmd
#
#  SAFETY: the server refuses by default. No environment is
#  allowlisted, read_only is true, allow_delete is false, and
#  auth_strategy is "none" - so every flow tool returns a clear
#  NOT_CONFIGURED or REFUSED message until deliberately widened
#  in FlowBridge/flow-bridge.config.json.
#
#  Authentication is interactive on the first call: a browser
#  opens for delegated sign-in. That works the same way on macOS,
#  but it is the one bridge whose usefulness depends on tenant
#  policy rather than on this repository.
#
#  Implementation: Startup/FlowBridge/flow-mcp-server.js
#
#  Uses the already-installed Node runtime. No npx. No installs.
#  No package dependencies.
#
#  Finding the runtime. A desktop app that starts this launcher
#  as a child process hands it a minimal PATH (on macOS typically
#  /usr/bin:/bin:/usr/sbin:/sbin), which holds no node at all. So
#  the launcher looks where installs actually put it, honours
#  COWORK_NODE from cowork-env.sh first, and if nothing is found
#  says so on stderr, where the host's per-server log will show
#  it, instead of dying with a bare "command not found".
# ============================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COWORK_ROOT="$(cd "$HERE/../.." && pwd)"
export COWORK_ROOT

[ -f "$HERE/cowork-env.sh" ] && . "$HERE/cowork-env.sh"

# Where node tends to live when the caller's PATH does not say.
export PATH="$HOME/.local/bin:$HOME/.local/node/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

NODE_BIN="${COWORK_NODE:-}"
if [ -z "$NODE_BIN" ]; then
  NODE_BIN="$(command -v node 2>/dev/null || true)"
fi
if [ -z "$NODE_BIN" ] || [ ! -x "$NODE_BIN" ]; then
  echo "flow-server.sh: node was not found (COWORK_NODE='${COWORK_NODE:-}', PATH='$PATH')." >&2
  echo "flow-server.sh: install Node 20 or later, or set COWORK_NODE in Startup/posix/cowork-env.sh," >&2
  echo "flow-server.sh: or run Startup/posix/install-mac.sh, which does both." >&2
  exit 127
fi

cd "$COWORK_ROOT/Startup/FlowBridge"

exec "$NODE_BIN" "$COWORK_ROOT/Startup/FlowBridge/flow-mcp-server.js"
