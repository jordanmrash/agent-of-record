#!/bin/bash
# COWORK_OUTPUT: ../Outputs/Mac Evidence 2026-09-15
#
# Real-device macOS evidence for the 2026-09-14 handoff, step 2.
# Runs install_check.py on THIS Mac (Darwin), not in the desktop Linux VM.
set -uo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

OUT="$COWORK_JOB_OUTPUT/install-check-macos-$(date +%Y%m%d-%H%M%S).txt"

{
  echo "host:     $(uname -s) $(uname -r) $(uname -m)"
  echo "macOS:    $(sw_vers -productVersion)"
  echo "user:     $(whoami)"
  echo "repo:     $REPO"
  echo "commit:   $(git rev-parse --short HEAD) $(git rev-parse --abbrev-ref HEAD)"
  echo "python:   $(python3 --version 2>&1)"
  echo "node:     $(command -v node) $(node --version 2>/dev/null)"
  echo "date:     $(date)"
  echo "========================================================"
  python3 scripts/install_check.py --route local 2>&1
  echo "exit_code: $?"
} | tee "$OUT"

echo
echo "Wrote: $OUT"
