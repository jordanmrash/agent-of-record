#!/bin/bash
# COWORK_OUTPUT: ../Outputs/Mac Evidence 2026-09-15
# Exercise the new install_check handshake on the real Mac.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
echo "branch: $(git rev-parse --abbrev-ref HEAD)"
echo "=== install_check --route local (with upstream handshake) ==="
time python3 scripts/install_check.py --route local 2>&1
echo "exit: $?"
