# Claude Cowork on a Mac

> **Status: not yet operated.** Written 2026-09-08 from the published files, revised
> 2026-09-09 against Anthropic's published description of how Claude Cowork executes, and
> corrected 2026-09-11 after the first run on a Mac someone uses. That run stopped one step
> short: the executor was registered and never connected (the note below says what is known;
> [the first-run record](claude-cowork-mac-first-run.md) is the evidence). The POSIX
> launchers and the executor's `.sh` form were proven in a Linux container and by CI on
> `macos-latest`. Steps marked *expected* describe what the design says should happen. If
> you run it, open a pull request with your `install_check.py` result and any correction —
> that is how this page becomes operated. **If you just want it installed, use
> [the short version](claude-cowork-mac-quickstart.md); this page is the long form.**

> **Where the executor runs, and what reaches it.** Anthropic's *Claude Cowork architecture
> overview* says sessions run in the cloud by default, that local execution remains
> available for existing desktop deployments, that local MCP servers do not run *in* a cloud
> session, and that on a managed device the MDM key `isLocalDevMcpEnabled` set to false
> disables them outright. Its page on surfaces says local connectors and plugins with local
> MCP servers work *through the desktop app*, the same bridge a cloud session uses to reach
> connected folders and the browser, and that the session has to be started in the desktop
> app. Every bridge on this page is a local MCP server. On the first run (desktop app
> 1.52386.0, a personal account, a fresh install) no local-session label or toggle was found
> in the app; the chat was a cloud session bridged to the Mac; the executor, uploaded as a
> plugin because the Connectors dialog takes a remote URL only, installed and enabled but
> never connected; and the cause was not isolated, because nothing in that run executed on
> macOS itself. Two suspects remain: the launcher was spawned with the minimal PATH a desktop
> app hands its children and could not find `node` (this version of `exec-server.sh` finds
> it and says so when it cannot), or plugin-bundled local servers need a session type a
> fresh install does not offer. **Validate in the macOS Terminal, never in a Cowork chat: the
> Cowork shell is a Linux VM, and a `PASS` there proves the repository, not the Mac.** The
> Cowork sandbox also cannot reach github.com or the npm registry (its proxy answers 403),
> so clone or download on the host.

**How this configuration connects.** The Claude desktop app on this machine starts each
registered bridge as a stdio child process and brokers the session's calls to it. There is
no tunnel, nothing to make public, and nothing that has to keep running between sessions.

**What this page installs, and why.** Claude Cowork already reads and writes
the folders you connect, fetches the web, remembers across sessions and runs shell
commands — in a Linux virtual machine under Apple's Virtualization framework, never on
macOS itself. Nothing it does natively can run `osascript`, open an application, or change
a preference on the Mac. The approved batch executor is the only path from a session to
the host's `/bin/bash`, so it is the one required component, and with it come the job
conventions, the release gate and the lessons machinery. The browser and filesystem
bridges are registered alongside it by `install-mac.sh`. The fourth bridge in this repository, Power Automate,
is Copilot Cowork on Windows only and has no place on this route. What each part lets
you do is in [What this repository adds to Claude Cowork](claude-cowork.md).

---

## 1. Prerequisites

| Need | Notes |
|---|---|
| macOS 13 or later | Apple silicon or Intel. Every path is `$HOME`-relative; nothing requires root. |
| Claude desktop app, installed and signed in | Cowork runs in it. A stdio server is registered in its configuration file, not in the Connectors dialog (step 6). |
| Git | Ships with the Xcode Command Line Tools: `xcode-select --install` |
| Node.js 20 LTS or later | Runs the executor. `node --version`. `install-mac.sh` fetches it into `~/.local/node`, without sudo, if the Mac has none. |
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

`Startup/posix/install-mac.sh` does steps 2, 3, 5, 9 and the by-hand half of step 6 in one
run from the macOS Terminal, then prints the short list of things only you can do;
[the short version](claude-cowork-mac-quickstart.md) is built around it. The rest of this
page says what each step does and why.

Run the gate **before** anything else: `release_check.py` must end with
`RELEASE_CHECK: CLEAN (24 checks)`. On a fresh clone anything else means the tree is wrong
before you have changed a single file — stop and open an issue with the output rather
than working around it. Do not adjust a check to make it pass.

**Executable bits.** The launchers are committed with mode `100755`, but a clone can arrive
without the execute bit and they will not start without it; the `chmod` above is not
optional. `install_check.py` names the file if you forget.

There is nothing else to install. The executor is plain `node` with no packages and
fetches nothing at start. The hosted route's `Startup/package.json` pins `supergateway`, the
HTTP wrapper a cloud client needs to reach a stdio server through a tunnel; this route has
no tunnel and never starts it. Nothing on this route fetches a package at start.

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
| `COWORK_CONFIG_ROOT` | unset | Where the executor's operating-rules reminder reads the live corpus. |
| `COWORK_ROOT` | derived | Only to point the executor at a different tree. |

`public_scan.py` refuses any tracked file containing a real home-directory path;
`cowork-env.sh` is where yours belongs.

**Where each root is defined — and only there.**

- **Executor** — `exec-server.sh`: `cd "$COWORK_ROOT/CommandJobs"`, then
  `node Startup/CommandBridge/batch-exec-server.js`. A job's `# COWORK_OUTPUT:` directive
  (`#`, not `REM`, on POSIX) must resolve under `Outputs/` or the job is **refused**, never
  redirected. Jobs run as `/bin/bash <script>` with `HOME`, `USER` and a PATH that includes
  `~/.local/bin` and Homebrew; per-run logs go to `CommandJobs/Logs/`.
- **Filesystem** (registered by the installer) — `fs-server.sh` passes `"$COWORK_ROOT"`, `"$HOME/Downloads"`
  and, if set and present, `"$COWORK_CONFIG_ROOT"` to the upstream server. That is the
  whole allowed list.
- **Browser** (registered by the installer) — `pw-server.sh` runs `@playwright/mcp` with the browser and
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

**Option B — by hand.** The desktop app's Customize › Connectors › Add dialog takes a
**remote URL only**; it has no field for a local command, so the executor cannot be
registered there. Three routes do accept a local stdio server:

1. **The configuration file**, which is what `install-mac.sh` writes. Settings › Developer ›
   Edit Config opens `~/Library/Application Support/Claude/claude_desktop_config.json`. Add
   the launcher under `mcpServers` with `command` `/bin/bash`, the launcher's absolute path
   as its one argument, and an `env.PATH` that contains your `node` directory, then quit the
   app completely and reopen it. Absolute paths, never `${HOME}`.
2. **A plugin** uploaded under Customize › Plugins whose `.mcp.json` declares a `stdio`
   server. Operated on the first run: it installs and enables, and in a cloud chat it did
   not connect; the status note above says what is and is not known about why.
3. **A desktop extension** (`.mcpb`) via Settings › Extensions › Advanced settings › Install
   Extension.

One server is registered on this route, and one only: `aor-batch-exec`, the approved
executor. If an earlier version of this repository registered `aor-filesystem` and
`aor-playwright` as well, `install-mac.sh --register` removes both — they are no longer
part of this route, because the host reads and writes connected folders and drives a
browser itself.

Registration is a step the person does on this host: a Cowork session has no tool that
edits the app's configuration or its plugin list, which bounds Option A. Afterwards, in a
Cowork chat started in the desktop app, the **+** button › Connectors lists the servers
actually connected; `~/Library/Logs/Claude/mcp.log` and `mcp-server-<name>.log` say why one
did not start, and `install-mac.sh --verify` reads them for you. The launchers to register:

| What | Command | Register it? |
|---|---|---|
| Approved batch executor | `<clone>/Startup/posix/exec-server.sh` | **Yes** — registered as `aor-batch-exec`. One tool: `run_batch_file`. Runs `.sh` only. Plain `node`, no dependencies, fetches nothing at start. Finds `node` under the minimal PATH a desktop app passes (`COWORK_NODE` in `cowork-env.sh` wins) and says so on stderr when it cannot. |

That is the whole table. There is no POSIX launcher for anything else in this repository:
the two that existed were retired on 2026-09-15 because the host already does both jobs,
and the filesystem one was additionally unusable — measured 2026-09-15, the pinned
`@modelcontextprotocol/server-filesystem@2025.8.21` emits an `inputSchema` carrying only a
`$schema` key on 13 of its 14 tools, and Cowork rejects the whole tool list. Keeping a
bridge in that state to duplicate a capability the host already has was the wrong trade.

`docs/bridge-facts.json` records the `stdio_posix` entry; the command above should match it
exactly. If it does not, the facts file wins and this page is wrong.

## 7. Skills, instructions and memory on this host

The repo ships a complete configuration under `CoworkConfig/`:

```
CoworkConfig/
  Skills/<skill-name>/SKILL.md      five skills, the command executor among them
  copilot-instructions.md           standing instructions (the Copilot host's filename)
  cowork-memory/cowork-lessons.md   the lessons corpus, beside the memory files
  README.md                         which files are generated from which
```

Start with an **empty** corpus, as `CoworkConfig/README.md` describes. The shipped lessons
and memory files are one operator's record of one machine — the right thing to read and
the wrong thing to operate under.

**Skills.** Build the repository's plugin; do not upload individual `SKILL.md` files:

```bash
python3 scripts/build_plugin.py --strict --platform macos
```

In Claude, open **Customize -> Plugins -> Add -> Upload plugin** and select
`Outputs/Skills Plugin/agent-of-record-skills-macos.plugin`. Restart the app and confirm
`ListSkills` returns all five repository skills. The same five skills ship on Windows and
macOS; each skill states the platform-specific launcher, path or job-script shape in the
same instructions.

Do not double-click the `.plugin` file. Claude registers no document type for that
extension, so Finder reports `kLSApplicationNotFoundErr` and nothing happens; the upload
picker inside Claude is the install path. A directory copy into `~/.claude/skills/` is not
an install either -- Cowork sessions do not read that directory (Claude Code does).

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
to install and no port to monitor. The repository has no POSIX watchdog: Claude Cowork
owns each stdio child's lifetime, while the hosted watchdog is Copilot Cowork on Windows
only. If a bridge misbehaves, end the session and start a new one.

## 9. Prove it

```bash
python scripts/install_check.py --route local --config-root "<config root>" --json install-results.json
```

`INSTALL_CHECK: CLEAN` is the finish line, and the servers section opens with
`bridges in scope: 3 of 4` - the three this route has. The check starts each own-code bridge as a real
stdio MCP server and completes a handshake — not a test that a file exists — checks the
runtime, enforces the 1024-character cap on skill descriptions, and runs the corpus checks.
`--route local` records `supergateway` as skipped rather than required: this route never
starts it. Each `FAIL` line names its own remedy. Read the JSON before deciding anything
works: a bridge that starts but fails its handshake is not installed. Run it from the macOS
Terminal, not from a Cowork chat: on the first run it came back `CLEAN` inside the agent's
Linux VM while the executor had never started on the Mac, because that shell is not the
Mac. `install-mac.sh` runs it in the right place and logs to `CommandJobs/Logs/`, then
starts the executor the way the desktop app does, with a minimal PATH, and completes a
handshake with it.

`install-results.json` is written to be committed: its `host` block carries only the OS
name, release, machine type and Python version, and the checker replaces your home
folder and config root with `<home>` and `<config-root>` before writing. The root-level
filename is gitignored so a private run never lands by accident; copy it into
`docs/evidence/` under the name that folder's README gives and open a pull request.

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
  the bridge — the Claude desktop app. A job cannot answer it; grant it
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
- `install-mac.sh` never uses `sudo` or `curl | bash`, writes nothing outside the tooling
  root except the desktop app's own configuration file (backed up with a date stamp first),
  and never edits a check to make a run pass. If it stops, the `STOP` line is a finding to
  report.


## Addendum 2026-09-15 - skills by configuration, and the model behind the session

Every skill in the repository ships to this route; the ones that duplicate a host capability
here say so in their own "When this skill is redundant" section, and the matrix is in
`docs/skills-by-configuration.md`. Disable a redundant skill in the host; re-enable it when
the configuration changes. If the session runs under third-party inference (a gateway or a
local model), the route is identical - the host, its folders, browser, plugins and MCP
servers are unchanged - but keep `persistent-memory` enabled until account memory is
confirmed present when signed out, and expect enforced controls to carry more weight than
delivered rules with a smaller model.
