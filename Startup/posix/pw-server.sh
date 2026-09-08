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
# ============================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COWORK_ROOT="$(cd "$HERE/../.." && pwd)"
export COWORK_ROOT

[ -f "$HERE/cowork-env.sh" ] && . "$HERE/cowork-env.sh"

BROWSER="${COWORK_PW_BROWSER:-chrome}"
PROFILE="${COWORK_PW_PROFILE:-$HOME/pw-sso-profile}"

mkdir -p "$PROFILE" "$COWORK_ROOT/playwright-output"

exec npx -y @playwright/mcp@latest \
  --browser "$BROWSER" \
  --user-data-dir "$PROFILE" \
  --output-dir "$COWORK_ROOT/playwright-output"
