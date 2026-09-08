# Claude Cowork on a Windows PC

> **Status: not yet operated.** Written 2026-09-08 from the published files (`main` at
> `29593a9`) and the operated Windows machine; nobody has run this page end to end. The
> repository's own guides cover the Copilot Cowork route only — this page is the first
> written for Claude Cowork. Steps marked *expected* describe what the design says should
> happen. If you run it, open a pull request with your `install_check.py` result and any
> correction — that is how this page becomes operated.

**How this configuration connects.** Claude Cowork runs on this machine. It starts each
bridge itself as a stdio process and talks to it directly. There is no tunnel, nothing to
make public, and nothing that has to keep running between sessions.

**What you get.** The bridges (browser, filesystem, approval-gated batch executor), the
executor's refusal contract, the job conventions under `CommandJobs`, the release gate,
and the lessons machinery. **What you don't.** Anything that lives in a Microsoft 365
tenant — mail, calendar, Teams, SharePoint, Power BI — and the Power Platform environment
the fourth bridge (Power Automate) authenticates against. That bridge is safe to register
anyway: it refuses every call until an environment is deliberately allowed in
`Startup\FlowBridge\flow-bridge.config.json`. On a personal machine, leave it unconfigured
or leave it out.

---

## 1. Prerequisites

| Need | Notes |
|---|---|
| Windows 10 or 11 | |
| Git | `git --version` |
| Node.js 20 LTS or later | Runs the two own-code bridges; `npx` fetches the two upstream ones on first start. `node --version`, `npx --version` |
| Python 3.10 or later | The gate, the checkers, `personalize.py`, `install_check.py`. `python --version` |
| Microsoft Edge | The Windows Playwright launcher drives an Edge profile (`--browser msedge`). |
| Claude Cowork | Installed and able to add stdio MCP servers. |
| GitHub CLI | Optional — only for opening the pull request at the end. |

Not required for this configuration (*expected*): VS Code, a tunnel or port forwarding of
any kind, a Microsoft 365 tenant. Those belong to the hosted setups.

## 2. Clone and install

```bash
git clone https://github.com/jordanmrash/agent-of-record.git "<tooling root>"
cd "<tooling root>"
python scripts/release_check.py
cd Startup
npm install
cd ..
```

`<tooling root>` is fixed on Windows and yours to choose on macOS — step 3 says which.

Run the gate **before** installing anything: `release_check.py` must end with
`RELEASE_CHECK: CLEAN (22 checks)`. On a fresh clone anything else means the tree is wrong
before you have changed a single file — stop and open an issue with the output rather
than working around it. Do not adjust a check to make it pass.

`npm install` runs inside `Startup/`, not at the root: `Startup/package.json` pins
`supergateway 3.4.3`, and the tasks launch it from `Startup/node_modules` so the version
that starts is the version that was tested. The two own-code bridges need no packages at
all; the browser and filesystem bridges are fetched by `npx` on their first start.

## 3. Choose your folders

On Windows the tooling root is **not** yours to choose. The `.cmd` launchers, `tasks.json`,
the watchdog and the shipped jobs all carry the literal path
`C:\Users\YOURUSER\Documents\COPILOT_COWORK`, so clone to exactly

    %USERPROFILE%\Documents\COPILOT_COWORK

and replace the placeholder in one pass. The script is a dry run until `--apply`:

```powershell
python scripts\personalize.py --user <your account name>
python scripts\personalize.py --user <your account name> --apply
```

It rewrites `Startup\`, `CommandJobs\`, `CoworkConfig\` and `docs\bridge-facts.json`,
prints every file it touched, and refuses a user name that is itself a placeholder. Leave
out `--tunnel-host`: there is no tunnel in this configuration. A personalized tree fails
`public_scan.py` by design — keep it on a local branch and never push it.

| Root | Holds | Where |
|---|---|---|
| **Tooling root** | `Startup\` (bridges), `CommandJobs\` (approved scripts), `CommandJobs\Logs\`, `Outputs\` | `%USERPROFILE%\Documents\COPILOT_COWORK` — the clone. Create `CommandJobs`, `CommandJobs\Logs` and `Outputs` beside `Startup\` if the clone did not bring them. |
| **Config root** | Skills, standing instructions, `cowork-memory\` | `[verify: where Claude Cowork loads skills and instructions from]`. The repo ships a complete set in `CoworkConfig\`. The Copilot host reads `<OneDrive>\Documents\Cowork`; this client may not. |

**Where each root is defined — and only there.** After personalizing, the `.cmd` launchers
in `Startup\` are the source of truth for every server's command line.

- **Executor** — `Startup\exec-server.cmd` changes directory into `CommandJobs` and runs
  `node Startup\CommandBridge\batch-exec-server.js`. `CommandJobs` is wherever that `cd`
  lands; a job's `REM COWORK_OUTPUT:` directive must resolve under the sibling `Outputs` or
  the job is **refused**, never redirected. Per-run logs (`.log`, `.exit`, `.json`) go to
  `CommandJobs\Logs\`.
- **Filesystem** — the three directory arguments on the one command line in
  `Startup\fs-server.cmd` are the allowed list: the tooling root, `Downloads`, and a third
  root that `personalize.py` sets to `<OneDrive>\Documents\Cowork`. The upstream server
  exits at start if any root does not exist, so on a machine without that folder edit the
  third argument to your config root (or to `CoworkConfig` inside the clone) before the
  first run.
- **Browser** — `Startup\pw-server.cmd` drives Edge with the profile
  `%USERPROFILE%\pw-sso-profile` and writes screenshots to `<tooling root>\playwright-output`.
  Create the profile once and sign in to whatever the bridge will need:
  `msedge.exe --user-data-dir="%USERPROFILE%\pw-sso-profile"`. The bridge never sees a
  password. Use a test account until you have watched the approval flow work.

**Known gap.** The three bridge skills (`command-bridge`, `local-file-bridge`,
`playwright-skill`) address the bridges by the Copilot connector ids
(`jordan-approved-batch-8933-v1` and siblings) and describe `.bat` jobs on this layout.
Under Claude Cowork the tool names will differ; their host-adapter sections are issue #6
work.

## 4. Start the bridges

*Expected:* you don't. In this configuration the host starts each bridge when it needs
it and stops it when the session ends.

To confirm a bridge starts at all, run its launcher by hand — it waits on standard input
for an MCP client and prints nothing until one connects:

```bat
Startup\exec-server.cmd
```

Press Ctrl+C to stop it. The four launchers are `pw-server.cmd` (browser), `fs-server.cmd`
(filesystem), `exec-server.cmd` (batch executor) and `flow-server.cmd` (Power Automate).
The executor is plain `node` with no dependencies and fetches nothing at start; the browser
and filesystem launchers use `npx -y`, so their **first** start downloads a package and
needs the network. `Startup\GO.bat` and `.vscode\tasks.json` belong to the **hosted**
Windows setup (they open VS Code and wrap each server for a tunnel); you do not need them
here.

## 5. Check they answer

Step 2 already did this. Inside `release_check.py`, `exec_bridge_selftest.py` opens a live
session with the executor and runs 31 cases in `.bat` form through `cmd.exe` — the line
that reads `EXEC_SELFTEST: OK - 31 of 31 cases passed`. That run was proven on Windows on
2026-09-08. If it passed, the executor answers and refuses what it should.

## 6. Connect your agent host

**Option A — the designed path.** Point Claude Cowork at the cloned folder and ask it to
install the bridges according to `AGENTS.md`. The install contract there is written for an
agent: validate the checkout, install the runtime, run `personalize.py` with your account
name (which it must ask you for, never guess), prove it with `install_check.py`. This is
the claim v0.3 makes; running it is the test.

**Option B — by hand.** In the host's connector settings, add each bridge as a **stdio**
server:

| Bridge | Command | Notes |
|---|---|---|
| Filesystem | `%USERPROFILE%\Documents\COPILOT_COWORK\Startup\fs-server.cmd` | Allowed directories are the three arguments inside this file (step 3). |
| Approved batch executor | `%USERPROFILE%\Documents\COPILOT_COWORK\Startup\exec-server.cmd` | One tool: `run_batch_file`. Runs `.bat`/`.cmd` only. |
| Browser | `%USERPROFILE%\Documents\COPILOT_COWORK\Startup\pw-server.cmd` | Edge, profile `pw-sso-profile` (step 3). |
| Power Automate | `%USERPROFILE%\Documents\COPILOT_COWORK\Startup\flow-server.cmd` | Optional. Refuses everything until configured; needs a Power Platform tenant to be useful. |

These are the `stdio` entries in `docs/bridge-facts.json` (`pw-server.cmd`, `fs-server.cmd`,
`exec-server.cmd`, `flow-server.cmd`). If the client cannot spawn a `.cmd` file directly,
use `cmd /c <path>` as the command. `[verify: how this client spawns a stdio server on
Windows]`

**Expected environment difference.** The hosted Windows setup measured a stripped job
environment — `%APPDATA%`, `%LOCALAPPDATA%` and `%USERPROFILE%` empty, the user PATH
missing, `timeout /t` failing for lack of a console. Those are properties of how *that*
machine spawns the executor. A locally-hosted spawn may differ in either direction.
Re-measure before porting any workaround from `docs/setup.md`.

## 7. Where skills and instructions live

The repo ships a complete configuration under `CoworkConfig\`:

```
CoworkConfig\
  Skills\<skill-name>\SKILL.md      eleven skills, the three bridge skills among them
  copilot-instructions.md           standing instructions (the Copilot host's filename)
  cowork-memory\cowork-lessons.md   the lessons corpus, beside the memory files
  README.md                         which files are generated from which
```

Start with an **empty** corpus, as `CoworkConfig\README.md` describes. The shipped lessons
and memory files are one operator's record of one machine — the right thing to read and
the wrong thing to operate under.

Where this client loads skills from is `[verify]`. The Copilot host reads
`<OneDrive>\Documents\Cowork\skills\` and the setup guides copy `CoworkConfig\Skills\*`
there; put the skills wherever Claude Cowork reads them, and point `--config-root` in step 9
at the same folder. Two limits carried from the operated tenant: a skill whose
`description` exceeds 1024 characters is dropped silently, and `copilot-instructions.md`
never took effect there, which is why the lesson digest is also routed into the skills.

## 8. Keep them running

*Expected:* nothing to do. The host owns each bridge's lifetime, so there is no watchdog
to install, no scheduled task, and no port to monitor. If a bridge misbehaves, end the
session and start a new one; do not restart anything on the machine.

## 9. Prove it

```bash
python scripts/install_check.py --config-root "<config root>" --json install-results.json
```

`INSTALL_CHECK: CLEAN` is the finish line. The check starts each own-code bridge as a real
stdio MCP server and completes a handshake — not a test that a file exists — checks the
pinned runtime, enforces the 1024-character cap on skill descriptions, and runs the corpus
checks. Each `FAIL` line names its own remedy. Read the JSON before deciding anything
works: a bridge that starts but fails its handshake is not installed.

Do not commit `install-results.json`. It names your machine, and `.gitignore` excludes it
at the repo root. A redacted, committable form is planned (issue #6, deliverable 6);
until it exists, paste the result into your pull-request description instead.

## 10. What this setup refuses to do

**Every setup, on every platform:**

- The batch executor runs only a script that **already exists** under `CommandJobs`,
  named by **relative path** — `.bat` or `.cmd` on Windows, `.sh` on macOS. It takes no
  command string, arguments, interpreter, working directory, environment, timeout, or
  elevation; there is no parameter for any of them.
- It rejects absolute, drive-qualified, UNC, URL-style, home-relative (`~`) and
  environment-variable paths, `..` traversal, any colon, names over 240 characters,
  anything under the `Logs` folder, symlinks or junctions that escape `CommandJobs`, and
  any name containing a shell metacharacter (`& | < > ^ " ' * ? ; $`, a backtick, CR, LF or
  TAB). Containment is decided on canonical paths, never by string prefix, so
  `CommandJobsEvil` cannot masquerade as `CommandJobs`.
- The filesystem bridge reads and writes only inside the directories you allow when you
  register it. Everything else is refused.
- A refusal is the control working. Do not widen a scan or a check to make a run pass.

**This configuration in particular:**

- No `.sh` — on Windows the executor accepts `.bat` and `.cmd` only.
- **Execution controls are fixed, not parameters:** 300 s timeout, after which the whole
  process tree is killed and exit code 9999 reported; 5 MB caps on stdout and stderr; one
  job at a time — a second call is refused, not queued; stdin closed; hidden window; no
  automatic retry; the script is left in place afterwards.
- No elevation. A job that needs administrator rights must be redesigned or run by you.
- No tunnel, so there is nothing to make public and no remote party can reach the bridges.
- No Microsoft 365 surface. Skills that assume mail, calendar, Teams or SharePoint tools
  will not find them here.
