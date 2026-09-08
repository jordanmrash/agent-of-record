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
# ============================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COWORK_ROOT="$(cd "$HERE/../.." && pwd)"
export COWORK_ROOT

[ -f "$HERE/cowork-env.sh" ] && . "$HERE/cowork-env.sh"

cd "$COWORK_ROOT/Startup/FlowBridge"

exec node "$COWORK_ROOT/Startup/FlowBridge/flow-mcp-server.js"
