#!/bin/bash
# COWORK_OUTPUT: ../Outputs/Mac Evidence 2026-09-15
# The build command exactly as docs/install/claude-cowork-mac.md states it.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
echo "cmd: python3 scripts/build_plugin.py --strict --platform macos"
python3 scripts/build_plugin.py --strict --platform macos 2>&1
echo "build_exit: $?"
ls -l "Outputs/Skills Plugin/" 2>&1
