# Claude Cowork on a Mac

> **Status: not yet operated.** Written 2026-09-08 from the published files (`main` at
> `29593a9`); nobody has run this page end to end on a Mac. The POSIX launchers and the
> executor's `.sh` form were proven in a Linux container on 2026-09-07; macOS itself has
> not been exercised, and the repository's own macOS guide covers the Copilot Cowork route
> only — this page is the first written for Claude Cowork. Steps marked *expected* describe
> what the design says should happen. If you run it, open a pull request with your
> `install_check.py` result and any correction — that is how this page becomes operated.

**How this configuration connects.** Claude Cowork runs on this machine. It starts each
bridge itself as a stdio process and talks to it directly. There is no tunnel, nothing to
make public, and nothing that has to keep running between sessions.

**What you get.** The bridges (browser, filesystem, approval-gated batch executor), the
executor's refusal contract, the job conventions under `CommandJobs`, the release gate,
and the lessons machinery. **What you don't.** Anything that lives in a Microsoft 365
tenant — mail, calendar, Teams, SharePoint, Power BI — and the Power Platform environment
the fourth bridge (Power Automate) authenticates against. That bridge is safe to register
anyway: it refuses every call until an environment is deliberately allowed in
`Startup/FlowBridge/flow-bridge.config.json`. On a personal machine, leave it unconfigured
or leave it out.

---

## 1. Prerequisites

| Need | Notes |
|---|---|
| macOS 13 or later | Apple silicon or Intel. Every path is `$HOME`-relative; nothing requires root. |
| Git | Ships with the Xcode Command Line Tools: `xcode-select --install` |
| Node.js 20 LTS or later | Runs the two own-code bridges; `npx` fetches the two upstream ones on first start. `node --version` |
| Python 3.10 or later | The scripts are invoked as `python`. On macOS that name may be missing — either alias it (`alias python=python3`) or substitute `python3` wherever this page says `python`. |
| A Chromium browser | The Playwright bridge drives a profile: Chrome by default, `COWORK_PW_BROWSER` to change. |
| Claude Cowork | Installed and able to add stdio MCP servers. |
| GitHub CLI | Optional — only for opening the pull request at the end. |

Not required for this configuration (*expected*): VS Code, a tunnel or port forwarding of
any kind, a launchd job, a Microsoft 365 tenant. Those belong to the hosted setups.

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

**Executable bits.** Then, and not optionally:

```bash
chmod +x Startup/posix/*.sh Startup/posix/watchdog/*.sh
```

The launchers are committed with mode `100755`, but a clone can arrive without the execute
bit and the launchers will not start without it. `install_check.py` names the file if you
forget.

## 3. Choose your folders

The location is yours. Every POSIX launcher derives the tooling root from its own location
(two directories above `Startup/posix/`), so nothing is hard-coded and nothing needs
personalizing. On first start `exec-server.sh` creates `CommandJobs/` and `Outputs/` beside
`Startup/` and changes directory into `CommandJobs` before starting the executor.

| Root | Holds | Where |
|---|---|---|
| **Tooling root** | `Startup/`, `CommandJobs/`, `CommandJobs/Logs/`, `Outputs/`, `playwright-output/` | The clone, wherever you put it (`COWORK_ROOT`, derived) |
| **Config root** | Skills, standing instructions, `cowork-memory/` | `[verify: where Claude Cowork loads skills and instructions from]`. Leave `COWORK_CONFIG_ROOT` unset to keep the corpus in the in-repo `CoworkConfig/`; set it to add that folder as the filesystem bridge's third root. |

Machine-specific settings live in one gitignored file created from the template. Nothing
in it is required — every launcher runs with defaults when it is absent:

```bash
cp Startup/posix/cowork-env.example.sh Startup/posix/cowork-env.sh
```

| Variable | Default | Sets |
|---|---|---|
| `COWORK_CONFIG_ROOT` | unset | Third filesystem root. If set but missing, `fs-server.sh` warns and starts with two roots. |
| `COWORK_PW_BROWSER` | `chrome` | `msedge`, `chromium` or `webkit` also work. |
| `COWORK_PW_PROFILE` | `$HOME/pw-sso-profile` | The persistent browser profile; created if absent. Sign in once with a test account. |
| `COWORK_ROOT` | derived | Only to point the bridges at a different tree. |

`public_scan.py` refuses any tracked file containing a real home-directory path;
`cowork-env.sh` is where yours belongs.

**Where each root is defined — and only there.**

- **Executor** — `exec-server.sh`: `cd "$COWORK_ROOT/CommandJobs"`, then
  `node Startup/CommandBridge/batch-exec-server.js`. A job's `# COWORK_OUTPUT:` directive
  (`#`, not `REM`, on POSIX) must resolve under `Outputs/` or the job is **refused**, never
  redirected. Jobs run as `/bin/bash <script>`; per-run logs go to `CommandJobs/Logs/`.
- **Filesystem** — `fs-server.sh` passes `"$COWORK_ROOT"`, `"$HOME/Downloads"` and, if set
  and present, `"$COWORK_CONFIG_ROOT"` to the upstream server. That is the whole allowed
  list.
- **Browser** — `pw-server.sh` runs `@playwright/mcp` with the browser and profile above and
  writes to `$COWORK_ROOT/playwright-output`.

**Known gap.** The three bridge skills (`command-bridge`, `local-file-bridge`,
`playwright-skill`) address the bridges by the Copilot connector ids
(`jordan-approved-batch-8933-v1` and siblings) and describe `.bat` jobs on a Windows layout.
Under Claude Cowork the tool names will differ; read `.bat` as `.sh`. Their host-adapter
sections are issue #6 work.

## 4. Start the bridges

*Expected:* you don't. In this configuration the host starts each bridge when it needs
it and stops it when the session ends.

To confirm a bridge starts at all, run its launcher by hand — it waits on standard input
for an MCP client and prints nothing until one connects:

```bash
Startup/posix/exec-server.sh
```

Press Ctrl+C to stop it. The four launchers are `pw-server.sh` (browser), `fs-server.sh`
(filesystem), `exec-server.sh` (batch executor) and `flow-server.sh` (Power Automate,
optional). `Startup/posix/GO.sh` belongs to the **hosted** Mac setup: it opens VS Code on
`Startup/`, whose tasks wrap each launcher for a tunnel. You do not need it, VS Code, or
`Startup/.vscode/tasks.json` here.

## 5. Check they answer

Step 2 already did this. Inside `release_check.py`, `exec_bridge_selftest.py` opens a live
session with the executor and runs 40 cases in `.sh` form — the line that reads
`EXEC_SELFTEST: OK - 40 of 40 cases passed on POSIX`. That run was proven on Linux on
2026-09-09 and by CI on `macos-latest`; yours is the first on a Mac someone uses. If it
passed, the executor answers, refuses what it should, rewrites a CRLF `.sh` to LF before
running it, and hands jobs `HOME`, `USER` and a PATH that includes `~/.local/bin` and
Homebrew even when launched with none of them.

## 6. Connect your agent host

**Option A — the designed path.** Point Claude Cowork at the cloned folder and ask it to
install the bridges according to `AGENTS.md`. The install contract there is written for an
agent, and the launchers derive their own paths, so the agent should not need to be told
where anything is. This is the claim v0.3 makes; running it is the test.

**Option B — by hand.** In the host's connector settings, add each bridge as a **stdio**
server whose command is the launcher:

| Bridge | Command | Notes |
|---|---|---|
| Filesystem | `<clone>/Startup/posix/fs-server.sh` | Allowed directories: the clone, `~/Downloads`, and `COWORK_CONFIG_ROOT` if set (step 3). |
| Approved batch executor | `<clone>/Startup/posix/exec-server.sh` | One tool: `run_batch_file`. Runs `.sh` only. Plain `node`, no dependencies, fetches nothing at start. |
| Browser | `<clone>/Startup/posix/pw-server.sh` | Uses `npx -y`, so its **first** start downloads a package and needs the network. Set the browser, profile and output folder to yours. |
| Power Automate | `<clone>/Startup/posix/flow-server.sh` | Optional. Refuses everything until configured; needs a Power Platform tenant to be useful. |

`docs/bridge-facts.json` records the `stdio_posix` entry for each bridge; the commands
above should match it exactly. If they do not, the facts file wins and this page is wrong.

## 7. Where skills and instructions live

The repo ships a complete configuration under `CoworkConfig/`:

```
CoworkConfig/
  Skills/<skill-name>/SKILL.md      eleven skills, the three bridge skills among them
  copilot-instructions.md           standing instructions (the Copilot host's filename)
  cowork-memory/cowork-lessons.md   the lessons corpus, beside the memory files
  README.md                         which files are generated from which
```

Start with an **empty** corpus, as `CoworkConfig/README.md` describes. The shipped lessons
and memory files are one operator's record of one machine — the right thing to read and
the wrong thing to operate under.

Where this client loads skills from is `[verify]`. The Copilot host reads
`<OneDrive>/Documents/Cowork/skills/` and the setup guides copy `CoworkConfig/Skills/*`
there; put the skills wherever Claude Cowork reads them, and point `--config-root` in step 9
at the same folder (or leave `COWORK_CONFIG_ROOT` unset and use `CoworkConfig/` in place).
Two limits carried from the operated tenant: a skill whose `description` exceeds 1024
characters is dropped silently, and `copilot-instructions.md` never took effect there, which
is why the lesson digest is also routed into the skills.

## 8. Keep them running

*Expected:* nothing to do. The host owns each bridge's lifetime, so there is no watchdog
to install and no port to monitor. `Startup/posix/watchdog/install-launchd.sh` exists for
the **hosted** Mac setup, where the bridges must stay up for a tunnel; do not install it
here. If a bridge misbehaves, end the session and start a new one.

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

- No `.bat` or `.cmd` — on macOS the executor accepts `.sh` only.
- **Execution controls are fixed, not parameters:** 300 s timeout, after which the whole
  process tree is killed and exit code 9999 reported; 5 MB caps on stdout and stderr; one
  job at a time — a second call is refused, not queued; stdin closed; no automatic retry;
  the script is left in place afterwards.
- No `sudo`. A job that needs root must be redesigned or run by you.
- `public_scan.py` refuses a tree containing `Startup/posix/cowork-env.sh` or a
  `/Users/<name>` path. If it refuses your branch, the branch carries your machine —
  remove the file or the path; do not widen the scan.
- No tunnel, so there is nothing to make public and no remote party can reach the bridges.
- No Microsoft 365 surface. Skills that assume mail, calendar, Teams or SharePoint tools
  will not find them here.
