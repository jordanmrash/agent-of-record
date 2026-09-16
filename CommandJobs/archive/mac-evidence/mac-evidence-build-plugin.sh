#!/bin/bash
# COWORK_OUTPUT: ../Outputs/Mac Evidence 2026-09-15
#
# Step 4 of the 2026-09-14 handoff: build the macOS skills plugin on this Mac.
set -uo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

OUT="$COWORK_JOB_OUTPUT/build-plugin-macos-$(date +%Y%m%d-%H%M%S).txt"

{
  echo "host:   $(uname -s) $(uname -r) $(uname -m) / macOS $(sw_vers -productVersion)"
  echo "commit: $(git rev-parse --short HEAD) $(git rev-parse --abbrev-ref HEAD)"
  echo "python: $(python3 --version 2>&1)"
  echo "date:   $(date)"

  echo "=== build_plugin_selftest.py ==="
  python3 scripts/build_plugin_selftest.py 2>&1
  echo "selftest_exit: $?"

  echo
  echo "=== build_plugin.py --list ==="
  python3 scripts/build_plugin.py --list 2>&1
  echo "list_exit: $?"

  echo
  echo "=== build_plugin.py --platform macos ==="
  python3 scripts/build_plugin.py --platform macos 2>&1
  echo "build_exit: $?"

  echo
  echo "=== artifacts ==="
  ls -l "Outputs/Skills Plugin/" 2>&1
} | tee "$OUT"

echo
echo "Wrote: $OUT"
