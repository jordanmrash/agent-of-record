#!/bin/bash
# COWORK_OUTPUT: ../Outputs/Mac Evidence 2026-09-15
#
# Push the operated-evidence commit from the Mac, where the user's git
# credential helper lives. Read-only except for the push itself.
set -uo pipefail
export GIT_TERMINAL_PROMPT=0

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

echo "credential.helper: $(git config --get credential.helper || echo '(none)')"
echo "remote:            $(git remote get-url origin)"
echo "head:              $(git rev-parse --short HEAD) $(git rev-parse --abbrev-ref HEAD)"
echo "gh cli:            $(command -v gh || echo 'not installed')"
echo "=================================================="
git push origin main 2>&1
echo "push_exit: $?"
echo "=================================================="
git status --short --branch 2>&1
