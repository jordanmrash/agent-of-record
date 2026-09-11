#!/bin/bash
# COWORK_OUTPUT: ../Outputs/Executor Test
#
# The first job to ask Claude Cowork for, once the executor shows up in a chat:
#     "Use run_batch_file to run hello-mac.sh"
# install-mac.sh copies this file into CommandJobs/ as hello-mac.sh. It proves the
# executor reaches this Mac itself, not a sandboxed VM, and that the job output
# convention works. It changes nothing except one file under Outputs/Executor Test/.
set -euo pipefail

echo "Hello from this Mac, via the agent-of-record executor."
echo "Running as:        $(whoami)"
echo "Machine:           $(uname -m), macOS $(sw_vers -productVersion 2>/dev/null || echo 'unknown')"
echo "Working directory: $(pwd)"
echo "Date:              $(date)"
echo "Node the jobs see: $(command -v node 2>/dev/null || echo 'not on PATH')"

echo "executor test ran ok at $(date)" > "$COWORK_JOB_OUTPUT/result.txt"
echo "Wrote:             $COWORK_JOB_OUTPUT/result.txt"
