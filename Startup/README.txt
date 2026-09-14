COWORK LOCAL BRIDGE -- STARTUP
=============================

First-time installation (prerequisites, npm install, personalizing the paths,
registering the connector packages under Startup\Plugins) is docs\setup.md at
the repository root. This file is the operating card once that is done.

1. Double-click GO.bat. It opens VS Code on this folder, which auto-starts
   four tasks.

2. Open the PORTS panel. Confirm 8931, 8932, 8933 and 8934 are listed and set each
   to PUBLIC (right-click > Port Visibility > Public). This does NOT persist
   across restarts -- you must redo it every launch.

3. Start a NEW Cowork session. Connectors only load at session start; starting
   the bridges mid-conversation does nothing for a session already running.


WHAT RUNS
---------
  8931  Playwright      pw-server.cmd    browser automation
  8932  Filesystem      fs-server.cmd    read/write three roots: %COWORK_ROOT% (this clone), %USERPROFILE%\Downloads, %COWORK_CONFIG_ROOT% (your Cowork folder, from cowork-env.cmd)
  8933  Commands        exec-server.cmd  runs approved .bat/.cmd from CommandJobs
  8934  Power Automate  flow-server.cmd  cloud-flow lifecycle (FlowBridge\flow-mcp-server.js)

Each task wraps a stdio MCP server in supergateway.
The .cmd files are the source of truth for their server arguments --
tasks.json only points --stdio at them. Do not copy arguments between them.

WHERE THE PATHS COME FROM
-------------------------
No launcher carries a C:\Users path. Each .cmd derives COWORK_ROOT (the
clone) from its own location with %~dp0, and tasks.json points at the
launchers through ${workspaceFolder}, so the launchers work for a clone in
any directory. The one value the repository cannot know is your Cowork
folder - the third filesystem root, where skills, copilot-instructions.md
and cowork-memory live. Set it once:

  copy cowork-env.example.cmd cowork-env.cmd
  (edit: set "COWORK_CONFIG_ROOT=%USERPROFILE%\OneDrive - <Org>\Documents\Cowork")

cowork-env.cmd is gitignored and refused by name in scripts\public_scan.py,
so your account name never reaches the repository. With it absent, or
pointing at a folder that does not exist, fs-server.cmd starts with two
roots and says so on stderr. The same file can override COWORK_PW_BROWSER
and COWORK_PW_PROFILE for the Playwright bridge. The watchdog
(_bridge-watchdog.ps1) and the shipped jobs still carry personalized paths
and expect the clone at %USERPROFILE%\Documents\COPILOT_COWORK;
scripts\copilot\personalize.py handles those. A client that starts the launchers
directly (docs\install\claude-cowork-windows.md) needs neither.


8933 COMMAND BRIDGE -- HARDENED 2026-08-17
------------------------------------------
exec-server.cmd no longer launches `mcp-server-commands`. That package
accepted arbitrary command strings and amounted to unrestricted local
execution over a Public tunnel. It now launches:

  Startup\CommandBridge\batch-exec-server.js     v1.3.0
  Startup\CommandBridge\README.txt               full operating notes

Plain Node, already installed. No npx, no installs, no dependencies.

One tool only:  run_batch_file { "file": "<relative name>.bat" }

Executes ONLY existing .bat/.cmd files that canonicalise under
COPILOT_COWORK\CommandJobs, supplied as a RELATIVE path. No command,
arguments, executable, interpreter, working directory, environment variable,
output directory, timeout override or elevation option can be passed.
300 s timeout with process-tree kill, 5 MB stdout/stderr caps, one concurrent
job, no elevation, no interactive input, no auto-retry, no cleanup.

  Scripts       CommandJobs\
  Logs          CommandJobs\Logs\    .log / .exit / .json per run
  Deliverables  ..\Outputs\YYYY-MM-DD - Short Descriptive Task Name\

Deliverables go under COPILOT_COWORK\Outputs, NOT under CommandJobs. The
approved script declares its own destination with a
"REM COWORK_OUTPUT: <path>" line; the server verifies it resolves under
Outputs, creates it, and exposes it as %COWORK_JOB_OUTPUT%. A directive
pointing outside Outputs REFUSES the job rather than being redirected.

tasks.json was NOT changed -- it still points --stdio at exec-server.cmd.
Restart VS Code (or rerun the 8933 task) and start a NEW Cowork session for
the replacement to take effect.

Backups / rollback:
  exec-server.cmd.20260817-005145.bak    previous hardened launcher
  exec-server.cmd.unrestricted-backup    ORIGINAL UNSAFE version -- do not
                                         restore without accepting
                                         unrestricted local execution
  Startup\batch-exec-server.js           obsolete loose copy of the server,
                                         retained as a backup during testing.
                                         NOT launched. Safe to delete once the
                                         CommandBridge version is proven.

Note: the boundary is the FOLDER and FILE TYPE, not script contents. A .bat
inside CommandJobs can still run anything as your user. Your control point is
reviewing the proposed commands and output path before approving. Treat write
access to CommandJobs as equivalent to execute access.


NO FALLBACK RUNNER
------------------
There is deliberately NO alternative execution path. If 8933 is unreachable,
retry once, then stop and report. (An autorun queue existed until 2026-08-21
and was removed as an unapproved execution path.)

IF A BRIDGE WON'T START
-----------------------
EADDRINUSE means something already holds that port -- almost always a leftover
process from a previous session.

  Close every VS Code window, then:
    Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force

  Check what is listening:
    Get-NetTCPConnection -LocalPort 8931,8932,8933,8934 -State Listen
  ("No matching MSFT_NetTCPConnection objects" means the ports are free.)

If 8933 starts and immediately exits, check that `node` is on PATH --
batch-exec-server.js is launched with `node`, not `npx`.

Do not run a second copy of this Startup folder from another location -- its
tasks compete for the same ports. The only correct launcher is
COPILOT_COWORK\Startup\GO.bat.
