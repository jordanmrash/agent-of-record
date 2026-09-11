#!/usr/bin/env bash
# ============================================================
#  Playwright MCP server - child process for supergateway:8931
#  POSIX sibling of ../pw-server.cmd
#
#  This file is the source of truth for the 8931 server command.
#  The tasks file points --stdio at this script; do not copy
#  arguments back from it.
#
#  Persistent browser profile (--user-data-dir, no --isolated) is
#  intentional: the transport is stateless, the browser is not.
#
#  BROWSER CHOICE differs from Windows. The Windows launcher pins
#  msedge because that is where the author's signed-in profile
#  lives. On macOS Edge is not a safe assumption, so the browser
#  is configurable and defaults to chrome. Set COWORK_PW_BROWSER
#  in cowork-env.sh to msedge, chrome, chromium or webkit.
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

NPX_BIN=""
if [ -n "${COWORK_NODE:-}" ]; then
  NPX_BIN="$(dirname "$COWORK_NODE")/npx"
fi
if [ -z "$NPX_BIN" ] || [ ! -x "$NPX_BIN" ]; then
  NPX_BIN="$(command -v npx 2>/dev/null || true)"
fi
if [ -z "$NPX_BIN" ] || [ ! -x "$NPX_BIN" ]; then
  echo "pw-server.sh: npx was not found (COWORK_NODE='${COWORK_NODE:-}', PATH='$PATH')." >&2
  echo "pw-server.sh: install Node 20 or later, or set COWORK_NODE in Startup/posix/cowork-env.sh," >&2
  echo "pw-server.sh: or run Startup/posix/install-mac.sh, which does both." >&2
  exit 127
fi

BROWSER="${COWORK_PW_BROWSER:-chrome}"
PROFILE="${COWORK_PW_PROFILE:-$HOME/pw-sso-profile}"

mkdir -p "$PROFILE" "$COWORK_ROOT/playwright-output"

exec "$NPX_BIN" -y @playwright/mcp@latest \
  --browser "$BROWSER" \
  --user-data-dir "$PROFILE" \
  --output-dir "$COWORK_ROOT/playwright-output"
