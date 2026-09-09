# Claude Cowork on a Mac

> **Status: not yet operated.** Written 2026-09-08 from the published files and revised
> 2026-09-09 against Anthropic's published description of how Claude Cowork executes;
> nobody has run this page end to end on a Mac. The POSIX launchers and the executor's
> `.sh` form were proven in a Linux container and by CI on `macos-latest`; a Mac someone
> uses has not been exercised. Steps marked *expected* describe what the design says should
> happen. If you run it, open a pull request with your `install_check.py` result and any
> correction — that is how this page becomes operated.

> **A local desktop session is required.** Anthropic's *Claude Cowork architecture
> overview* (read 2026-09-09) says sessions run in the cloud by default, that local
> execution remains available for existing desktop deployments, and that local MCP
> servers do not run in a cloud session. Every bridge on this page is a local MCP server.
> A cloud session will follow every step and find no executor. On a managed device, the
> MDM key `isLocalDevMcpEnabled` set to false disables local MCP servers outright.
> `[verify: how the desktop app labels a local session, and whether a new install can
> start one]`

**How this configuration connects.** Claude Cowork runs on this machine. It starts each
registered bridge itself as a stdio process and talks to it directly. There is no tunnel,
nothing to make public, and nothing that has to keep running between sessions.

**Why this page installs one bridge, not four.** Claude Cowork already reads and writes
the folders you connect, fetches the web, remembers across sessions and runs shell
commands — in a Linux virtual machine under Apple's Virtualization framework, never on
macOS itself. Nothing it does natively can run `osascript`, open an application, or change
a preference on the Mac. The approved batch executor is the only path from a session to
the host's `/bin/bash`, so it is the one required component, and with it come the job
conventions, the release gate and the lessons machinery. The browser and filesystem
bridges are optional here; the Power Automate bridge needs a tenant. What each part lets
you do is in [What this repository adds to Claude Cowork](claude-cowork.md).

---

## 1. Prerequisites

| Need | Notes |
|---|---|
| macOS 13 or later | Apple silicon or Intel. Every path is `$HOME`-relative; nothing requires root. |
| Claude Cowork desktop app, in a **local** session | Able to add stdio MCP servers (see the note above). |
| Git | Ships with the Xcode Command Line Tools: `xcode-select --install` |
| Node.js 20 LTS or later | Runs the executor. `node --version` |
| Python 3.10 or later | The scripts are invoked as `python`. On macOS that name may be missing — either alias it (`alias python=python3`) or substitute `python3` wherever this page says `python`. |
| A Chromium browser | **Optional** — only if you register the browser bridge: Chrome by default, `COWORK_PW_BROWSER` to change. |
| GitHub CLI | **Optional** — only for opening the pull request at the end. |

Not required for this configuration (*expected*): VS Code, a tunnel or port forwarding of
any kind, a launchd job, a package install under `Startup/`, a Microsoft 365 tenant. Those
belong to the hosted setups.

## 2. Clone and validate

```bash
git clone https://github.com/jordanmrash/agent-of-record.git "<tooling root>"
cd "<tooling root>"
python scripts/release_check.py
chmod +x Startup/posix/*.sh
```

`<tooling root>` is yours to choose — step 3 says what the launchers derive from it.

Run the gate **before** anything else: `release_check.py` must end with
`RELEASE_CHECK: CLEAN (22 checks)`. On a fresh clone anything else means the tree is wrong
before you have changed a single file — stop and open an issue with the output rather
than working around it. Do not adjust a check to make it pass.

**Executable bits.** The launchers are committed with mode `100755`, but a clone can arrive
without the execute bit and they will not start without it; the `chmod` above is not
optional. `install_check.py` names the file if you forget.

There is nothing else to install. The executor is plain `node` with no packages and
fetches nothing at start. The hosted route's `Startup/package.json` pins `supergateway`, the
HTTP wrapper a cloud client needs to reach a stdio server through a tunnel; this route has
no tunnel and never starts it. Only the optional browser and filesystem bridges fetch a
package, by `npx`, on their first start.

## 3. Choose your folders

The location is yours. Every POSIX launcher derives the tooling root from its own location
(two directories above `Startup/posix/`), so nothing is hard-coded and nothing needs
personalizing. On first start `exec-server.sh` creates `CommandJobs/` and `Outputs/` beside
`Startup/` and changes directory into `CommandJobs` before starting the executor.

| Root | Holds | Where |
|---|---|---|
| **Tooling root** | `Startup/`, `CommandJobs/`, `CommandJobs/Logs/`, `Outputs/` | The clone, wherever you put it (`COWORK_ROOT`, derived) |
| **Config root** | The lessons corpus and the memory files the tooling reads | The in-repo `CoworkConfig/` unless you keep the corpus elsewhere. Under Claude Cowork this is *not* where skills load from — skills are uploaded (step 7) — so leave `COWORK_CONFIG_ROOT` unset unless you move the corpus. |

Machine-specific settings live in one gitignored file created from the template. Nothing
in it is required — every launcher runs with defaults when it is absent:

```bash
cp Startup/posix/cowork-env.example.sh Startup/posix/cowork-env.sh
```

| Variable | Default | Sets |
|---|---|---|
| `COWORK_CONFIG_ROOT` | unset | Where the executor's operating-rules reminder reads the live corpus, and the filesystem bridge's third root if you register that bridge. If set but missing, `fs-server.sh` warns and starts with two roots. |
| `COWORK_PW_BROWSER` | `chrome` | `msedge`, `chromium` or `webkit` also work — browser bridge only. |
| `COWORK_PW_PROFILE` | `$HOME/pw-sso-profile` | The browser bridge's persistent profile; created if absent. Sign in once with a test account. |
| `COWORK_ROOT` | derived | Only to point the bridges at a different tree. |

`public_scan.py` refuses any tracked file containing a real home-directory path;
`cowork-env.sh` is where yours belongs.

**Where each root is defined — and only there.**

- **Executor** — `exec-server.sh`: `cd "$COWORK_ROOT/CommandJobs"`, then
  `node Startup/CommandBridge/batch-exec-server.js`. A job's `# COWORK_OUTPUT:` directive
  (`#`, not `REM`, on POSIX) must resolve under `Outputs/` or the job is **refused**, never
  redirected. Jobs run as `/bin/bash <script>` with `HOME`, `USER` and a PATH that includes
  `~/.local/bin` and Homebrew; per-run logs go to `CommandJobs/Logs/`.
- **Filesystem** (optional) — `fs-server.sh` passes `"$COWORK_ROOT"`, `"$HOME/Downloads"`
  and, if set and present, `"$COWORK_CONFIG_ROOT"` to the upstream server. That is the
  whole allowed list.
- **Browser** (optional) — `pw-server.sh` runs `@playwright/mcp` with the browser and
  profile above and writes to `$COWORK_ROOT/playwright-output`.

## 4. Start the bridges

*Expected:* you don't. In this configuration the host starts each registered bridge when
it needs it and stops it when the session ends.

To confirm the executor starts at all, run its launcher by hand — it waits on standard
input for an MCP client and prints nothing until one connects:

```bash
Startup/posix/exec-server.sh
```

Press Ctrl+C to stop it. `Startup/posix/GO.sh` belongs to the **hosted** Mac setup: it
opens VS Code on `Startup/`, whose tasks wrap each launcher for a tunnel. You do not need
it, VS Code, or `Startup/.vscode/tasks.json` here.

## 5. Check it answers

Step 2 already did this. Inside `release_check.py`, `exec_bridge_selftest.py` opens a live
session with the executor and runs 40 cases in `.sh` form — the line that reads
`EXEC_SELFTEST: OK - 40 of 40 cases passed on POSIX`. That run was proven on Linux on
2026-09-09 and by CI on `macos-latest`; yours is the first on a Mac someone uses. If it
passed, the executor answers, refuses what it should, rewrites a CRLF `.sh` to LF before
running it, and hands jobs `HOME`, `USER` and a PATH that includes `~/.local/bin` and
Homebrew even when launched with none of them.

## 6. Connect your agent host

**Option A — the designed path.** Point Claude Cowork at the cloned folder and ask it to
install the executor according to `AGENTS.md`. The install contract there is written for an
agent, and the launchers derive their own paths, so the agent should not need to be told
where anything is. This is the claim v0.3 makes; running it is the test.

**Option B — by hand.** In the host's connector settings, add the executor as a **stdio**
server whose command is the launcher, and any optional bridge you want:

| Bridge | Command | Register it? |
|---|---|---|
| Approved batch executor | `<clone>/Startup/posix/exec-server.sh` | **Yes.** One tool: `run_batch_file`. Runs `.sh` only. Plain `node`, no dependencies, fetches nothing at start. |
| Browser | `<clone>/Startup/posix/pw-server.sh` | Optional — a signed-in browser profile with traces to disk. Uses `npx -y`, so its **first** start downloads a package and needs the network. |
| Filesystem | `<clone>/Startup/posix/fs-server.sh` | Optional — only for tool parity with the hosted route. Connect the clone as a folder instead and the host's own file tools cover it. |
| Power Automate | `<clone>/Startup/posix/flow-server.sh` | Optional — needs a Power Platform tenant; refuses everything until configured. |

`docs/bridge-facts.json` records the `stdio_posix` entry for each bridge; the commands
above should match it exactly. If they do not, the facts file wins and this page is wrong.

## 7. Skills, instructions and memory on this host

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

**Skills.** Claude Cowork takes a `SKILL.md` you upload as your own skill (Customize ›
Skills), or one delivered by a plugin; skills installed from its directory are view-only.
Upload `self-improvement` first — its scripts are host-agnostic and the corpus depends on
them — then whichever bridge skill matches a bridge you registered. The shipped skills
address the bridges by the Copilot host's connector ids and describe `.bat` jobs on a
Windows layout; read `.bat` as `.sh`. Their host-adapter sections are issue #6 work, so
until then read them as reference. `[verify: the uploader tolerates the skills' `cowork:`
and `metadata:` frontmatter keys; where it caps a description]`

**Instructions.** `copilot-instructions.md` is the Copilot host's file and has no
equivalent here *(expected)*. It carries the lessons digest, and that digest is also
regenerated into every skill's `SKILL-LESSONS` block — which is how the rules reach this
host.

**Memory.** Claude's own memory — one store shared with chat, editable topic files — is the
pointer tier: preferences, standing context, who is who. On Team and Enterprise plans it is
off until the user turns it on. The deep tier stays in files:
`CoworkConfig/cowork-memory/*.md`, one home per fact, with evidence and dates, under git.
Do not duplicate a fact across both.

**Running the lessons tooling.** `lesson_check.py`, `digest_apply.py` and
`skill_lessons.py` are Python. They run in the session's own VM if the connected folder is
visible there *(unverified)*, or as a `.sh` job through the executor, as the hosted route
does.

## 8. Keep them running

*Expected:* nothing to do. The host owns each bridge's lifetime, so there is no watchdog
to install and no port to monitor. `Startup/posix/watchdog/install-launchd.sh` exists for
the **hosted** Mac setup, where the bridges must stay up for a tunnel; do not install it
here. If a bridge misbehaves, end the session and start a new one.

## 9. Prove it

```bash
python scripts/install_check.py --route local --config-root "<config root>" --json install-results.json
```

`INSTALL_CHECK: CLEAN` is the finish line. The check starts each own-code bridge as a real
stdio MCP server and completes a handshake — not a test that a file exists — checks the
runtime, enforces the 1024-character cap on skill descriptions, and runs the corpus checks.
`--route local` records `supergateway` as skipped rather than required: this route never
starts it. Each `FAIL` line names its own remedy. Read the JSON before deciding anything
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
- The filesystem bridge, if registered, reads and writes only inside the directories you
  allow when you register it. Everything else is refused.
- A refusal is the control working. Do not widen a scan or a check to make a run pass.

**This configuration in particular:**

- No `.bat` or `.cmd` — on macOS the executor accepts `.sh` only.
- **Execution controls are fixed, not parameters:** 300 s timeout, after which the whole
  process tree is killed and exit code 9999 reported; 5 MB caps on stdout and stderr; one
  job at a time — a second call is refused, not queued; stdin closed; no automatic retry;
  the script is left in place afterwards.
- No `sudo`. A job has no terminal and its stdin is closed, so a password prompt cannot
  happen; a job that needs root must be redesigned or run by you.
- **macOS asks before a script controls another application** *(expected, not measured)*.
  The first `osascript` that targets an application triggers an Automation permission
  prompt in System Settings › Privacy & Security, attributed to the process that launched
  the bridge — the Claude desktop app in a local session. A job cannot answer it; grant it
  once by hand, per target application. UI scripting needs Accessibility permission the
  same way, and an application must be able to run in your logged-in session.
- `public_scan.py` refuses a tree containing `Startup/posix/cowork-env.sh` or a
  `/Users/<name>` path. If it refuses your branch, the branch carries your machine —
  remove the file or the path; do not widen the scan.
- No tunnel, so there is nothing to make public and no remote party can reach the bridges.
- Nothing the host runs in its own terminal reaches macOS: that shell is a Linux VM. The
  executor is the only host path, which is the point of registering it.
- No Microsoft 365 surface. Skills that assume mail, calendar, Teams or SharePoint tools
  will not find them here.
