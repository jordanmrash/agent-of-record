# Claude Cowork on a Windows PC

> **Status: not yet operated.** Written 2026-09-08 from the published files and revised
> 2026-09-09 against Anthropic's published description of how Claude Cowork executes;
> nobody has run this page end to end. Steps marked *expected* describe what the design
> says should happen. If you run it, open a pull request with your `install_check.py`
> result and any correction — that is how this page becomes operated.

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

**Why this page installs one bridge of three.** Claude Cowork already reads and writes
the folders you connect, fetches the web, remembers across sessions and runs shell
commands — in a Linux virtual machine, never on Windows. Nothing it does natively can run
a `.bat`, read the registry, or drive a Windows application. The approved batch executor
is the only path from a session to `cmd.exe`, so it is the one required component, and
with it come the job conventions, the release gate and the lessons machinery. The browser
and filesystem bridges are optional here. The fourth bridge in this repository, Power Automate,
is Copilot Cowork only and not part of this route. What
each part lets you do is in [What this repository adds to Claude Cowork](claude-cowork.md).

---

## 1. Prerequisites

| Need | Notes |
|---|---|
| Windows 10 or 11 | |
| Claude Cowork desktop app, in a **local** session | Able to add stdio MCP servers (see the note above). |
| Git | `git --version` |
| Node.js 20 LTS or later | Runs the executor. `node --version` |
| Python 3.10 or later | The gate, the checkers, `install_check.py`. `python --version` |
| Microsoft Edge | **Optional** — only if you register the browser bridge, which drives an Edge profile. |
| GitHub CLI | **Optional** — only for opening the pull request at the end. |

Not required for this configuration (*expected*): VS Code, a tunnel or port forwarding of
any kind, a package install under `Startup/`, a Microsoft 365 tenant. Those belong to the
hosted setup.

## 2. Clone and validate

```bash
git clone https://github.com/jordanmrash/agent-of-record.git "<tooling root>"
cd "<tooling root>"
python scripts/release_check.py
```

`<tooling root>` is yours to choose — step 3 says what the launchers derive from it.

Run the gate **before** anything else: `release_check.py` must end with
`RELEASE_CHECK: CLEAN (24 checks)`. On a fresh clone anything else means the tree is wrong
before you have changed a single file — stop and open an issue with the output rather
than working around it. Do not adjust a check to make it pass.

There is nothing to install. The executor is plain `node` with no packages and fetches
nothing at start. The hosted route's `Startup/package.json` pins `supergateway`, the HTTP
wrapper a cloud client needs to reach a stdio server through a tunnel; this route has no
tunnel and never starts it. Only the optional browser and filesystem bridges fetch a
package, by `npx`, on their first start.

## 3. Choose your folders

Every Windows launcher derives the tooling root from its own location (`%~dp0`, one
directory above `Startup\`), so a clone can live anywhere and nothing needs personalizing.
On first start `exec-server.cmd` changes directory into `CommandJobs`; the executor creates
`CommandJobs\Logs\` and `Outputs\` beside `Startup\` if they are absent.

| Root | Holds | Where |
|---|---|---|
| **Tooling root** | `Startup\`, `CommandJobs\`, `CommandJobs\Logs\`, `Outputs\` | The clone, wherever you put it (`COWORK_ROOT`, derived) |
| **Config root** | The lessons corpus and the memory files the tooling reads | The in-repo `CoworkConfig\` unless you keep the corpus elsewhere. Under Claude Cowork this is *not* where skills load from — skills are uploaded (step 7) — so leave `COWORK_CONFIG_ROOT` unset unless you move the corpus. |

Machine-specific settings live in one gitignored file created from the template. Nothing
in it is required — every launcher runs with defaults when it is absent:

```bat
copy Startup\cowork-env.example.cmd Startup\cowork-env.cmd
```

| Variable | Default | Sets |
|---|---|---|
| `COWORK_CONFIG_ROOT` | unset | Where the executor's operating-rules reminder reads the live corpus, and the filesystem bridge's third root if you register that bridge. |
| `COWORK_PW_PROFILE` | `%USERPROFILE%\pw-sso-profile` | The browser bridge's persistent profile, if registered. |
| `COWORK_ROOT` | derived | Only to point the bridges at a different tree. |

`public_scan.py` refuses any tracked file containing a real `C:\Users\<name>` path;
`cowork-env.cmd` is where yours belongs.

**Where each root is defined — and only there.**

- **Executor** — `exec-server.cmd`: `cd /d "%COWORK_ROOT%\CommandJobs"`, then
  `node Startup\CommandBridge\batch-exec-server.js`. A job's `REM COWORK_OUTPUT:` directive
  must resolve under `Outputs\` or the job is **refused**, never redirected. Jobs run as
  `cmd.exe /d /s /c <script>` with a complete user environment; per-run logs go to
  `CommandJobs\Logs\`.
- **Filesystem** (optional) — `fs-server.cmd` passes `%COWORK_ROOT%`,
  `%USERPROFILE%\Downloads` and, if set and present, `%COWORK_CONFIG_ROOT%` to the
  upstream server. That is the whole allowed list.
- **Browser** (optional) — `pw-server.cmd` runs `@playwright/mcp` against the Edge profile
  above and writes to `%COWORK_ROOT%\playwright-output`.

## 4. Start the bridges

*Expected:* you don't. In this configuration the host starts each registered bridge when
it needs it and stops it when the session ends.

To confirm the executor starts at all, run its launcher by hand — it waits on standard
input for an MCP client and prints nothing until one connects:

```bat
Startup\exec-server.cmd
```

Press Ctrl+C to stop it. `Startup\GO.bat` and `.vscode\tasks.json` belong to the **hosted**
Windows setup (they open VS Code and wrap each server for a tunnel); you do not need them
here.

## 5. Check it answers

Step 2 already did this. Inside `release_check.py`, `exec_bridge_selftest.py` opens a live
session with the executor and runs 40 cases in `.bat` form through `cmd.exe` — the line
that reads `EXEC_SELFTEST: OK - 40 of 40 cases passed on Windows`. That run was proven on
Windows on 2026-09-09. If it passed, the executor answers, refuses what it should,
normalizes a script's line endings before running it, and hands jobs a complete
environment.

## 6. Connect your agent host

**Option A — the designed path.** Point Claude Cowork at the cloned folder and ask it to
install the executor according to `AGENTS.md`. The install contract there is written for an
agent: validate the checkout, write your config root into `Startup\cowork-env.cmd` if you
moved the corpus (a value it must ask you for, never guess), register the launcher, prove
it with `install_check.py --route local`. This is the claim v0.3 makes; running it is the
test.

**Option B — by hand.** In the host's connector settings, add the executor as a **stdio**
server, and any optional bridge you want:

| Bridge | Command | Register it? |
|---|---|---|
| Approved batch executor | `<tooling root>\Startup\exec-server.cmd` | **Yes.** One tool: `run_batch_file`. Runs `.bat`/`.cmd` only. Plain `node`, no dependencies, fetches nothing at start. |
| Browser | `<tooling root>\Startup\pw-server.cmd` | Optional — a signed-in Edge profile with traces to disk. Uses `npx -y`, so its **first** start downloads a package and needs the network. |
| Filesystem | `<tooling root>\Startup\fs-server.cmd` | Optional — only for tool parity with the hosted route. Connect the clone as a folder instead and the host's own file tools cover it. |

These are the `stdio` entries in `docs/bridge-facts.json`; the commands above should match
it exactly, and if they do not, the facts file wins and this page is wrong. If the client
cannot spawn a `.cmd` file directly, use `cmd /c <path>` as the command. `[verify: how this
client spawns a stdio server on Windows]`

## 7. Skills, instructions and memory on this host

The repo ships a complete configuration under `CoworkConfig\`:

```
CoworkConfig\
  Skills\<skill-name>\SKILL.md      ten skills, the three bridge skills among them
  copilot-instructions.md           standing instructions (the Copilot host's filename)
  cowork-memory\cowork-lessons.md   the lessons corpus, beside the memory files
  README.md                         which files are generated from which
```

Start with an **empty** corpus, as `CoworkConfig\README.md` describes. The shipped lessons
and memory files are one operator's record of one machine — the right thing to read and
the wrong thing to operate under.

**Skills.** Build the repository's plugin; do not upload individual `SKILL.md` files:

```bat
python scripts\build_plugin.py --strict --platform windows
```

In Claude, open **Customize -> Plugins -> Add -> Upload plugin** and select
`Outputs\Skills Plugin\agent-of-record-skills-windows.plugin`. Restart the app and confirm
`ListSkills` returns all ten repository skills. The same ten skills ship on Windows and
macOS; each skill states the platform-specific launcher, path or job-script shape in the
same instructions.

Do not double-click the `.plugin` file; Claude registers no document type for that
extension. The upload picker inside Claude is the install path. A directory copy into
`~/.claude/skills/` is not an install either -- Cowork sessions do not read that directory
(Claude Code does).

**Instructions.** `copilot-instructions.md` is the Copilot host's file and has no
equivalent here *(expected)*. It carries the lessons digest, and that digest is also
regenerated into every skill's `SKILL-LESSONS` block — which is how the rules reach this
host.

**Memory.** Claude's own memory — one store shared with chat, editable topic files — is the
pointer tier: preferences, standing context, who is who. On Team and Enterprise plans it is
off until the user turns it on. The deep tier stays in files:
`CoworkConfig\cowork-memory\*.md`, one home per fact, with evidence and dates, under git.
Do not duplicate a fact across both.

**Running the lessons tooling.** `lesson_check.py`, `digest_apply.py` and
`skill_lessons.py` are Python. They run in the session's own VM if the connected folder is
visible there *(unverified)*, or as a `.bat` job through the executor, as the hosted route
does.

## 8. Keep them running

*Expected:* nothing to do. The host owns each bridge's lifetime, so there is no watchdog
to install, no scheduled task, and no port to monitor. If a bridge misbehaves, end the
session and start a new one; do not restart anything on the machine.

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

- No `.sh` — on Windows the executor accepts `.bat` and `.cmd` only.
- **Execution controls are fixed, not parameters:** 300 s timeout, after which the whole
  process tree is killed and exit code 9999 reported; 5 MB caps on stdout and stderr; one
  job at a time — a second call is refused, not queued; stdin closed; hidden window; no
  automatic retry; the script is left in place afterwards.
- No elevation. A job that needs administrator rights must be redesigned or run by you.
- No tunnel, so there is nothing to make public and no remote party can reach the bridges.
- Nothing the host runs in its own terminal reaches Windows: that shell is a Linux VM. The
  executor is the only host path, which is the point of registering it.
- No Microsoft 365 surface. Skills that assume mail, calendar, Teams or SharePoint tools
  will not find them here.
