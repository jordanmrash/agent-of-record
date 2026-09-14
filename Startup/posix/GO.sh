#!/usr/bin/env bash
# ============================================================
#   ONE-COMMAND COWORK BRIDGE  (macOS / Linux)
#   POSIX sibling of ../GO.bat
#
#   Opens VS Code on the Startup folder, which auto-starts the
#   three bridge tasks and auto-forwards ports 8931-8933; the fourth task,
#   Power Automate, is Windows-only and prints a note instead.
#
#   The one thing left to do in VS Code: set each port PUBLIC in
#   the Ports panel. Visibility does not persist across restarts,
#   and nothing on this machine can do it for you.
#
#   First-time installation: docs/setup-macos.md.
# ============================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STARTUP="$(cd "$HERE/.." && pwd)"

if ! command -v code >/dev/null 2>&1; then
  echo "GO: the 'code' command is not on PATH."
  echo "GO: in VS Code run: Cmd+Shift+P -> Shell Command: Install 'code' command in PATH"
  echo "GO: or open this folder manually: $STARTUP"
  exit 1
fi

exec code "$STARTUP"
