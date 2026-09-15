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

# Pinned, deliberately, and measured rather than assumed.
#
#   THIS PIN IS NOT SUFFICIENT. Read before trusting it.
#
#   The 2026-09-13 measurement read outputSchema dialects only, and concluded that
#   2025.8.21 - the last release with no output schemas at all - was therefore safe.
#   Re-measured on macOS 2026-09-15 against the same pin, reading inputSchema too:
#
#     version      tools  inputSchema missing type  input draft-07  output draft-07
#     2025.8.21      14            13                     13               0
#     2025.11.25     14             0                     14              14
#     2026.8.31      14             0                     14              14
#
#   So 2025.8.21 fails WORSE than the later releases, in a different way. 13 of its
#   14 tools emit an inputSchema of literally {"$schema": "...draft-07..."} - no type,
#   no properties. Cowork rejects the whole tools/list with "expected object" at
#   tools[0].inputSchema.type and the bridge drops out entirely. That is the
#   aor-filesystem outage observed on this Mac on 2026-09-15.
#
#   Root cause, measured the same day: the package declares zod-to-json-schema ^3.23.5
#   and no zod of its own, so npx resolves zod 4.x through @modelcontextprotocol/sdk
#   1.30.0. zod-to-json-schema@3 cannot read zod 4 internals and silently emits an
#   empty schema. Installing 2025.8.21 with an npm override of zod to ^3.25.0 restores
#   complete schemas (type, properties, required) on all 14 tools - still labelled
#   draft-07, but structurally valid.
#
#   The later releases are the opposite trade: structurally complete, dialect wrong.
#   Whether Cowork actually refuses a well-formed draft-07 schema has NOT been
#   verified on this machine; the 2026-09-13 note asserts it.
#
#   Fixing this properly means controlling the dependency tree rather than handing
#   npx a version string. Until that lands, this bridge is known-broken on the local
#   Claude route. scripts/install_check.py now handshakes this server and reports both
#   faults, so the failure is visible at check time instead of at first tool call.
#
#   The Windows sibling (Startup/fs-server.cmd) is deliberately NOT pinned: the hosted
#   Copilot route accepts draft-07 and is in daily use unpinned.
FS_SERVER_VERSION="${COWORK_FS_SERVER_VERSION:-2025.8.21}"

exec "$NPX_BIN" -y "@modelcontextprotocol/server-filesystem@${FS_SERVER_VERSION}" "${ROOTS[@]}"
