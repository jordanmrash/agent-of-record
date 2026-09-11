#!/usr/bin/env bash
# ============================================================
#  Filesystem MCP server - child process for supergateway:8932
#  POSIX sibling of ../fs-server.cmd
#
#  Roots are defined ONLY here, exactly as on Windows: the tasks
#  file and the watchdog both point --stdio at this script and
#  neither lists a root, so no recovery path can silently widen
#  them.
#
#  THREE ROOTS, and the third one matters. The tooling root and
#  Downloads are local. The third is what Cowork itself loads -
#  skills, instructions and cowork-memory - so the agent can
#  write them DIRECTLY instead of uploading to the cloud and
#  waiting on replication.
#
#  On a Mac that third root is NOT a fixed path: OneDrive's local
#  folder name depends on the tenant, and iCloud or Dropbox users
#  differ again. Set COWORK_CONFIG_ROOT in cowork-env.sh rather
#  than editing this file, so a pull does not overwrite it. With
#  it unset the bridge runs with two roots and the agent keeps
#  its corpus inside the repository instead.
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
  echo "fs-server.sh: npx was not found (COWORK_NODE='${COWORK_NODE:-}', PATH='$PATH')." >&2
  echo "fs-server.sh: install Node 20 or later, or set COWORK_NODE in Startup/posix/cowork-env.sh," >&2
  echo "fs-server.sh: or run Startup/posix/install-mac.sh, which does both." >&2
  exit 127
fi

ROOTS=("$COWORK_ROOT" "$HOME/Downloads")

if [ -n "${COWORK_CONFIG_ROOT:-}" ]; then
  if [ -d "$COWORK_CONFIG_ROOT" ]; then
    ROOTS+=("$COWORK_CONFIG_ROOT")
  else
    echo "fs-server: COWORK_CONFIG_ROOT is set but does not exist:" >&2
    echo "fs-server:   $COWORK_CONFIG_ROOT" >&2
    echo "fs-server: starting with two roots; fix the path in cowork-env.sh" >&2
  fi
fi

exec "$NPX_BIN" -y @modelcontextprotocol/server-filesystem "${ROOTS[@]}"
