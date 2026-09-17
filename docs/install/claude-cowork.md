# What this repository adds to Claude Cowork

Claude Cowork runs on the machine. In a local desktop session its agent loop is native —
it reads and writes the folders you connect, fetches the web, remembers across sessions
and starts local MCP servers — while every shell command and every piece of code it writes
runs inside a Linux virtual machine the hypervisor isolates from the host (Hyper-V on
Windows, Apple Virtualization on macOS). That last fact decides what this repository is
for here: Claude Cowork has a terminal, and that terminal cannot run a `.bat`, an
AppleScript, or anything else that acts on the operating system or an application you
use. The only path from a session to the host is a local MCP server. The approved batch
executor is that path, and it is the reason to install this repository on this host.

Sources, read 2026-09-09: Anthropic's *Claude Cowork architecture overview* (Help Center),
*Claude's memory works everywhere, and you decide what's in it* (blog), and *Browse skills,
connectors, and plugins in one directory* (Help Center). Install pages:
[Windows PC](claude-cowork-windows.md) · [Mac](claude-cowork-mac.md). Windows is not yet operated; on a Mac the executor route ran on
2026-09-15 ([evidence](../evidence/mac-operated-2026-09-15.md)), with the skills-plugin upload
not yet confirmed. The route comparison is in [Choose your route](README.md).

**Two conditions before anything else.** Sessions now run in the cloud by default; local
execution "remains available for existing desktop deployments", and local MCP servers do
not run in a cloud session — a cloud session reaches your device only through the desktop
app, for connected folders and the browser. Every page in this route assumes a **local**
session. On a managed device, an administrator can disable local MCP servers with an MDM
key (`isLocalDevMcpEnabled`), which disables this route entirely.

## What the host does on its own

| Already there | So the repository does not ship |
|---|---|
| Reads and writes connected folders, permission-gated | Any file-access bridge — connect the clone instead |
| A shell and code execution, in the Linux VM | Anything for computing, parsing or file generation |
| Web fetch; the device's browser through the desktop app *(expected)* | A browser bridge as a requirement |
| One memory shared with chat, editable topic files | A pointer-tier workaround. Use the host's memory for preferences and standing context; on Team and Enterprise plans it is off until the user turns it on |
| Skills as `SKILL.md` uploaded as your own, or delivered by a plugin | A skills loader or folder convention |
| Owns each MCP server's lifetime | A watchdog, scheduled task, launchd job, tunnel, connector package or personalizer |

## What it cannot do without this repository

- **Act on the host OS or an application.** No `.bat`/`.cmd` on Windows, no `.sh` against
  macOS, no `osascript`, no per-user CLI such as `gh` or the Power Platform CLI against
  your real profile. The VM is Linux and isolated by design.
- **Remember a mechanism.** The host's memory stores what you told it and what it inferred
  about you; it does not hold evidence, dates, supersession or a place where a fact has
  exactly one home.
- **Turn a failure into a tested rule.** Nothing native records a trap with its cause,
  counts repeats, requires a distinction before a new entry, or regenerates rules into the
  surfaces that load.
- **Reach a Microsoft 365 tenant or Power Platform.** Not available on this host at all.
- **Version control.** No git tool; whether the VM sees a connected repository is
  unverified.

## What the repository adds, and what each part lets you do

**Required — the approved batch executor** (`Startup/exec-server.cmd` on Windows,
`Startup/posix/exec-server.sh` on a Mac). One tool, `run_batch_file`, which runs an
existing script under `CommandJobs` named by relative path — `.bat`/`.cmd` on Windows,
`.sh` on macOS — with fixed controls and no parameter for a command, arguments, working
directory, environment, timeout or elevation. Registered as a stdio server, it lets a
session do what a person at that machine's own shell could do — drive Excel or Mail through
AppleScript, run `pac` or `gh`, move files with Finder — only through a script the person
has read and approved, with stdout, stderr, exit code and every changed file reported back.
Since executor 1.3.0 the script's line endings are normalized before it runs and the job
gets the account's full environment and user PATH.

**Required — the job conventions.** `CommandJobs/`, the `COWORK_RESULT: OK|FAIL` contract,
per-run logs, and the standing parameterized jobs that turn "propose, approve once, run,
read back" into a habit rather than a hope.

**Required — the release gate and `install_check.py`.** Proof by doing: a real stdio
handshake with each own-code bridge, the executor's forty-case self-test in the platform's
script form, negative-control self-tests for every checker, and a disclosure scan. Run with
`--route local`, the check does not ask for `supergateway`, which this route never uses.

**Required — the lessons machinery and the deep-tier memory files.** The corpus format,
the checkers, the digest and skill-block generators, the duplicate gate, and the
behavioral verification harness are host-agnostic Python and run unchanged. They are the
part of the repository with no counterpart on any host, and on this host they may run
closer to the work: shell commands execute in the session's own VM, so the close routine
can run there if the connected folder is visible to it (*unverified*) — otherwise as a job
through the executor, as on the hosted route.

**Removed from this route on 2026-09-15 — browsing and file access.** The table above says
why: the host already browses and already reads and writes connected folders, so the two
bridges that offered those only duplicated first-party capability, while adding an `npx`
fetch, an upstream dependency and a second set of file roots to reason about. Both remain
Copilot Cowork on Windows, where the hosted route has no equivalent.

**Not on this host — Power Automate.** The fourth bridge in this repository administers
Power Platform flows and is Copilot Cowork on Windows only: this host cannot reach a tenant,
and the bridge has no POSIX launcher. Nothing on this route registers it.

So this route registers exactly one bridge: the approved command executor. That is the
single thing the host cannot do for itself.

**Not applicable here.** The dev tunnel, `supergateway`, the Ports panel, the connector
packages, the watchdog, the personalizer, the pointer-tier memory conventions written for
the Copilot store, and `copilot-instructions.md` as a loaded file — the digest it carries
reaches this host through the generated blocks in the skills instead.

## The executor as a bundle

From 0.3.5 each release also carries the executor on its own as an MCP Bundle,
`aor-batch-exec-<version>.mcpb`, beside the skills plugin. A bundle is a zip the desktop app
installs from its own settings dialog. It holds the server, a manifest that declares one
setting - the tooling root - and nothing else: no launcher, no clone, no `PATH` of your own to
get right, and the host is expected to start the server on the Node runtime it bundles (to be
confirmed by the first real install). Choose the tooling root when the dialog asks; the
executor creates `CommandJobs/`, `CommandJobs/Logs/` and `Outputs/` under it if they are
absent, and everything in the executor paragraph above applies unchanged, because the file
inside the bundle is the same `batch-exec-server.js` the launcher starts.

One difference is deliberate. The packaged copy carries no operating-rules block in its tool
description: that block is the operator's own record, regenerated from their corpus, and a new
install starts with an empty corpus. The live reminder the executor reads from
`cowork-lessons.md` at run time is unchanged and simply stays empty until you have one.

`scripts/build_mcpb.py` builds the bundle from the same source, deterministically, and the
release gate refuses a manifest whose name or version has drifted from the server it packages.
Verify the download against the `.sha256` sidecar on the release before installing it. The
bundle install is **not yet operated** on a real machine; the script route above is the one
with evidence behind it. When a bundle install runs end to end, the result belongs in
`docs/evidence/` and this line changes.

## Skills on this host

Two install paths, neither yet operated on a real machine.

**From the repository as a marketplace** (Claude Code; Claude Cowork where the app offers to add a
marketplace): the root `.claude-plugin/marketplace.json` lists one plugin whose root is
`CoworkConfig/plugin/` - the manifest plus a `skills/` tree generated from `CoworkConfig/Skills/`
and checked by the release gate.

```text
/plugin marketplace add jordanmrash/agent-of-record
/plugin install agent-of-record-skills@agent-of-record
```

**From a built file.** Build the same ten-skill plugin for either platform:

```bash
python3 scripts/build_plugin.py --strict --platform macos     # Mac
python  scripts\build_plugin.py --strict --platform windows  # Windows
```

Install it through **Customize -> Plugins -> Add -> Upload plugin**, restart Claude, and
confirm `ListSkills` returns all ten. Each `SKILL.md` is one portable instruction set: where
a mechanism differs, the Windows and macOS forms are stated together.

Opening the `.plugin` file from Finder or Explorer does not work -- Claude registers no
document type for the extension -- and copying the directory into `~/.claude/skills/` is not
an installation for Cowork, which does not read that directory.


## Addendum 2026-09-15 - skills by configuration, and the model behind the session

Every skill in the repository ships to this route; the ones that duplicate a host capability
here say so in their own "When this skill is redundant" section, and the matrix is in
`docs/skills-by-configuration.md`. Disable a redundant skill in the host; re-enable it when
the configuration changes. If the session runs under third-party inference (a gateway or a
local model), the route is identical - the host, its folders, browser, plugins and MCP
servers are unchanged - but keep `persistent-memory` enabled until account memory is
confirmed present when signed out, and expect enforced controls to carry more weight than
delivered rules with a smaller model.
