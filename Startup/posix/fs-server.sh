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
# ============================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COWORK_ROOT="$(cd "$HERE/../.." && pwd)"
export COWORK_ROOT

[ -f "$HERE/cowork-env.sh" ] && . "$HERE/cowork-env.sh"

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

exec npx -y @modelcontextprotocol/server-filesystem "${ROOTS[@]}"
