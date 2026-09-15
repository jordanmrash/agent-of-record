#!/bin/bash
# COWORK_OUTPUT: ../Outputs/Mac Evidence 2026-09-15
#
# Step 4, second half: hand the built .plugin to Claude so the in-app accept
# dialog appears. Accepting it, and the restart after, are the operator's.
set -uo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
PLUGIN="$REPO/Outputs/Skills Plugin/agent-of-record-skills-macos.plugin"

if [ ! -f "$PLUGIN" ]; then
  echo "plugin not found: $PLUGIN"
  exit 1
fi

echo "plugin:  $PLUGIN"
echo "size:    $(stat -f %z "$PLUGIN") bytes"
echo "handler: $(/usr/bin/mdls -name kMDItemContentType "$PLUGIN" 2>/dev/null || echo unknown)"
open "$PLUGIN" 2>&1
echo "open_exit: $?"
