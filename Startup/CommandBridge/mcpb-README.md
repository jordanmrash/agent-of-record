# aor-batch-exec (MCP Bundle)

The approved batch executor from Agent of Record, packaged for desktop hosts that install MCP Bundles.

One tool, `run_batch_file`, whose only input is the relative name of a script that already exists under `<tooling root>/CommandJobs` (`.bat`/`.cmd` on Windows, `.sh` on macOS and Linux). No command, arguments, interpreter, working directory, environment, output directory, timeout override or elevation option can be supplied. Fixed 300 second timeout with process-tree kill, 5 MB output caps, one job at a time, no console, no elevation, no interactive input. The result carries stdout, stderr, the exit code, timing and every file the job created, modified or deleted.

Install: open your host's extension or connector settings and install this `.mcpb`, then choose the tooling root. The executor creates `CommandJobs/`, `CommandJobs/Logs/` and `Outputs/` under it if they are absent.

Source, tests and the refusal contract: https://github.com/jordanmrash/agent-of-record
