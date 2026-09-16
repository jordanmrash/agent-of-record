# Claude Cowork on a Mac: the short version

> **Status: the executor route ran on a Mac on 2026-09-15** ([evidence](../evidence/mac-operated-2026-09-15.md)):
> `install-mac.sh --register`, `install_check.py --route local` (CLEAN) and `run_batch_file` on the
> machine itself. Step 6 under "The things only you can do" - uploading the skills plugin and
> confirming `ListSkills` - is not yet confirmed on a Mac. Whatever happens, send it back (step 5).

One download, one command in Terminal, then a short list of clicks that only you can do.
The long form of this page, with every design decision and every refusal the executor
makes, is [claude-cowork-mac.md](claude-cowork-mac.md). You do not need it to install.

## Before you start

- A Mac, Apple silicon or Intel, macOS 13 or later.
- The Claude desktop app installed and signed in. Cowork works in it.
- **Python 3.10 or later.** macOS ships 3.9.6, which the installer refuses, so unless
  you have installed a newer one for something else you will need to. Check with
  `python3 --version`. The quickest route is the installer from
  [python.org](https://www.python.org/downloads/macos/) — note that its `.pkg` **does**
  ask for an administrator password. If you would rather not give one, use a user-local
  tool instead (`uv python install 3.12`, or `brew install python@3.12` on an existing
  Homebrew), which does not.
- About ten minutes. Nothing else here needs an administrator password.

> **Do not put the tree in `~/Documents`, `~/Desktop` or `~/Downloads`.** macOS privacy
> controls cover those folders, and the Claude desktop app starts the executor as a
> child process that gets the app's permissions rather than yours. A tree there can
> install cleanly and then fail at run time with `Operation not permitted`, while the
> same script run from Terminal works — Terminal has its own grant. Nothing in that
> failure names the cause. The installer defaults to `~/agent-of-record` and refuses a
> protected folder unless you pass `--allow-protected-root`.

## 1. Get the files

Either download one file:

1. Open the repository's **Releases** page and, under the newest release, click
   **Source code (zip)**.
2. In Finder, open Downloads and double-click the zip. You get a folder named
   `agent-of-record-<version>`.

Or, if you already use git, clone it:

```bash
git clone https://github.com/jordanmrash/agent-of-record.git ~/agent-of-record
```

## 2. Run the installer

Open Terminal (Spotlight, type `Terminal`) and paste one line. For the download:

```bash
bash ~/Downloads/agent-of-record-*/Startup/posix/install-mac.sh
```

For a clone:

```bash
bash ~/agent-of-record/Startup/posix/install-mac.sh
```

It puts the tree at `~/agent-of-record`, checks for git, python3 and node
(and fetches node into your home folder if the Mac has none), creates the job and
output folders, runs the repository's own release gate and install check **on the Mac
itself**, starts the executor the way the desktop app will and completes a handshake
with it, and registers the executor in the Claude desktop app's own configuration file
(keeping a dated backup). Every line it prints starts with `PASS`, `WARN` or `STOP`.

Two things can interrupt it, and both are one click:

- **A dialog offers to install the Command Line Tools.** Click Install, wait for it to
  finish, then paste the same line again.
- **It says Claude Desktop is not installed.** Install the app, open it once, then run
  `bash ~/agent-of-record/Startup/posix/install-mac.sh --register`.

It ends with a numbered list headed **THINGS ONLY YOU CAN DO**. The same list is saved
at `~/agent-of-record/Outputs/agent-of-record-next-steps.txt`.

## 3. The things only you can do

1. Quit Claude completely (Claude menu, Quit Claude, or Cmd+Q) and open it again. It
   reads its configuration only at launch.
2. Start a **new** Cowork chat **in the desktop app** (choose Cowork in the message
   box). A chat started on the web cannot reach this Mac.
3. Click the **+** at the bottom of the message box, then **Connectors**. You should see
   one connector: `aor-batch-exec`, with one tool, `run_batch_file`. That is the whole
   list — Claude reads and writes your connected folders and drives a browser on its own,
   so this repository registers nothing for those.
4. Ask Claude: *Use run_batch_file to run hello-mac.sh*. Approve it when asked. The
   result should name `~/agent-of-record/Outputs/Executor Test/result.txt`.
5. The first time a job controls another application (AppleScript), macOS asks for
   permission once. Click OK.
6. In Terminal, build the skills plugin:
   `cd ~/agent-of-record && python3 scripts/build_plugin.py --strict --platform macos`.
   Then in Claude: **Customize -> Plugins -> Add -> Upload plugin**, select
   `Outputs/Skills Plugin/agent-of-record-skills-macos.plugin`, restart Claude, and
   confirm `ListSkills` returns all ten repository skills. Double-clicking the file
   does not work; use the upload picker.

## 4. If the connector is not there

```bash
bash ~/agent-of-record/Startup/posix/install-mac.sh --verify
```

This reads the desktop app's own log files and tells you which of two things happened:
the app started the launcher and it died (the lines it prints say why, usually node or
a path), or the app never tried to start it at all. Either way, copy that output into
step 5. Do not edit the executor to get past it; a refusal is the control working.

## 5. Send it back

Open a pull request or an issue on the repository with:

- the `RELEASE_CHECK:` and `INSTALL_CHECK:` lines from the installer's log
  (`~/agent-of-record/CommandJobs/Logs/install-mac-<stamp>.log`),
- the output of `--verify`, pass or fail,
- your macOS version and the Claude desktop app version (Claude menu, About).

`install-results.json` is safe to attach: its `host` block carries only the OS name,
release, machine type and Python version, and the checker replaces your home folder and
config root with placeholders before writing it. `docs/evidence/README.md` says where it
goes and how to name it. The status line at the top of this page changes only when a run
like yours comes back.

## Where things are

| What | Where |
|---|---|
| The tree (tooling root) | `~/agent-of-record` |
| Jobs the executor may run | `~/agent-of-record/CommandJobs/*.sh` |
| What jobs produce | `~/agent-of-record/Outputs/` |
| Installer and executor logs | `~/agent-of-record/CommandJobs/Logs/` |
| Your machine's settings (gitignored) | `~/agent-of-record/Startup/posix/cowork-env.sh` |
| The entry the installer wrote | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| What the desktop app logged | `~/Library/Logs/Claude/mcp.log` and `mcp-server-aor-batch-exec.log` |

## What the installer refuses to do

- No `sudo`. If node is missing it goes into `~/.local/node`, checked against the
  published checksum, never into a system folder.
- No `curl | bash`. You download a file you can read, then run it.
- Nothing outside the tooling root is written, except the Claude desktop app's
  configuration file, and that is backed up with a date stamp first.
- It never edits a check to make a run pass. A `STOP` line is a finding to report.
