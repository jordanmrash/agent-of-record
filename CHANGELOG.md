# Changelog

All notable changes to the published repository. Through 0.3.0 each entry
summarized one rebuilt snapshot; from 0.3.0 `main` keeps its history and each
entry summarizes a release.

## Unreleased

Three bridges on a Mac, not one; the filesystem bridge pinned to a release this
client can actually call; and the reserved-name entry the 0.3.2 installer left
behind is retired on upgrade.

- **Upgrading from 0.3.2 on a Mac.** The 0.3.2 installer registered the executor
  under the name `cowork-batch-exec`. Claude Desktop reserves the `cowork` prefix
  and refuses that entry at every launch, and because `install-mac.sh` merges
  into `claude_desktop_config.json` rather than replacing it, upgrading alone left
  the dead entry in place. `install-mac.sh --register` now retires it when it
  points at an agent-of-record launcher, prints what it removed, and keeps the
  dated backup it always took. A `cowork-batch-exec` that is not this
  repository's is left alone with a warning. If you registered by hand, remove
  the key yourself. The names are now `aor-batch-exec`, `aor-filesystem` and
  `aor-playwright`.
- **`install-mac.sh` registers all three bridges**, not only the executor, and
  `--verify` reads the desktop app's logs for all three names. Before this a Mac
  user who followed the quickstart ended up with one connector and no sign the
  other two existed.
- **`fs-server.sh` pins `@modelcontextprotocol/server-filesystem@2025.8.21`.**
  Measured across twelve published releases: from 2025.11.25 onward the package
  declares draft-07 output schemas on all 14 tools, and Claude Cowork supports
  JSON Schema 2020-12 only, so an unpinned bridge handshakes, advertises 14 tools
  and fails every call. 2025.8.21 is the last release with no output schemas and
  carries the same 14 tools. `COWORK_FS_SERVER_VERSION` overrides the pin;
  `docs/bridge-facts.json` records it as `posix_package_pin`. The Windows
  launcher stays unpinned: the hosted route accepts draft-07.

## 0.3.2 - 2026-09-11

Installable on a Mac in one command, and every POSIX launcher finds its own
runtime rather than assuming the caller's PATH holds one.

- **`Startup/posix/install-mac.sh`** - one command from the macOS Terminal:
  it places the tree, installs Node without sudo when it is missing and pins
  it in `cowork-env.sh`, creates the folders and sets the execute bits, runs
  `release_check.py` and `install_check.py` in a real Terminal rather than an
  agent's shell, completes an MCP handshake under a deliberately minimal PATH,
  registers the executor in `claude_desktop_config.json` behind a dated backup,
  and prints the steps only a person can do. `--verify` reads the desktop app's
  own MCP logs and says whether the server was started; `--register` rewrites
  only the config entry; `--replace` refreshes an existing tree while keeping
  `CommandJobs`, `Outputs` and `cowork-env.sh`.
- **Every POSIX launcher resolves its runtime.** A desktop app that starts a
  launcher as a child process hands it a minimal PATH, which on macOS holds no
  node, so `exec node` or a bare `npx` died with a command-not-found that only
  the host's per-server log recorded. `exec-server.sh`, `pw-server.sh`,
  `fs-server.sh` and `flow-server.sh` now prepend the folders node is installed
  in, honour `COWORK_NODE` from `cowork-env.sh`, resolve `npx` beside a pinned
  node, and exit 127 with a message naming the fix. The facts-check fixture for
  a launcher pointed at the wrong server re-anchors on the new exec line.
- **The Mac page says what the first run measured.** The executor, packaged as
  a plugin because the Connectors dialog takes a remote URL only, installed and
  enabled and never connected in a cloud chat, and the cause is not isolated
  because nothing in that run executed on macOS itself. The page now names the
  three routes that do accept a local stdio server, says to validate in the
  machine's own Terminal because an agent's shell is a Linux VM that proves the
  repository rather than the host, and keeps its `not yet operated` status.
- `docs/install/claude-cowork-mac-quickstart.md`, the short version of that
  page, and `docs/install/claude-cowork-mac-first-run.md`, the record of the
  run itself.
- `CITATION.cff` 0.3.2.

## 0.3.1 - 2026-09-10

Documentation. The pages that still described one host describe both routes,
the counts agree with the shipped corpus, and the release metadata matches
`main` before the repository is linked publicly.

- **Both routes on every architecture page.** The README diagram and its Host
  and Install rows, the `docs/architecture.md` system view and the opening of
  `SECURITY.md` now state the hosted route (Copilot Cowork reaching the bridges
  through a dev tunnel) and the local route (Claude Cowork starting the servers
  as stdio processes) side by side, and the executor's file types read
  `.bat`/`.cmd` on Windows and `.sh` on POSIX wherever they are named.
- `CoworkConfig/README.md` counted 126 shipped lesson entries; the shipped
  corpus has 123, as the README and `docs/measured-results.md` say.
- `docs/measured-results.md` no longer lists as future targets the facts check
  and the consolidated CI runner, both shipped in 0.2.0.
- `dream-cycle` carries the attribution block every other skill carries, as
  `CONTRIBUTING.md` promises for all of them.
- `GitHubSetup/README.template.md`, a stale copy of the README whose
  root-relative links did not resolve from its folder, is reduced to a note plus
  the one table `facts_check.py` still reads from it: `README.md` is edited on
  `main` directly.
- The published-writing lists name the two newest articles.
- `CITATION.cff` 0.3.1.

- **The Claude Cowork route installs only what that host lacks.** Read against
  Anthropic's published description of Claude Cowork: in a local session its
  agent loop is native but every shell command runs in a Linux VM isolated from
  the host, so the approved batch executor is the only path from a session to
  the operating system - and the one required component. Both Claude Cowork
  pages are rewritten around that: the browser and filesystem bridges become
  optional, the package install for `supergateway` (an HTTP wrapper only the
  tunnel route uses) is gone, the pages state that a local desktop session is
  required because local MCP servers do not run in a cloud session, and they
  say what to do with skills, instructions and memory on a host that already
  has a memory. `install_check.py --route local` reports `supergateway` as
  skipped rather than required. Three new pages: `docs/install/README.md`
  (choose your route, with a host-by-host feature matrix),
  `docs/install/copilot-cowork.md` and `docs/install/claude-cowork.md` (what the
  repository adds to each host and what that lets you do). `AGENTS.md`,
  `docs/quickstart.md`, `docs/limitations.md`, `llms.txt`, the README picker and
  the banners on both hosted pages point at them, and the new pages join the
  facts check's stale-phrase surfaces.
- **The executor normalizes script line endings** (`batch-exec-server.js` 1.3.0).
  Before an approved script runs, its line terminators are rewritten in place
  to the platform's convention: an LF-only `.bat`/`.cmd` becomes CRLF on
  Windows, where cmd.exe mis-parses LF-only files silently, and a CRLF `.sh`
  becomes LF on POSIX, where bash rejects the CR. Nothing but the terminators
  changes, a file that already mixes both is left alone, and the result reports
  what happened as `line_endings`. Scripts written by the filesystem bridge
  (LF) no longer need a separate normalizing job before their first run.
- **The executor hands jobs a complete environment.** It is still built by the
  server alone - the MCP caller has no parameter that reaches it - but it now
  carries what an interactive session of the same account would: on Windows the
  profile variables (`USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, `TEMP`,
  `HOMEDRIVE`/`HOMEPATH`, `USERNAME`, the `ProgramFiles` family) derived from
  the account when the launching process lacks them, and the user's PATH from
  `HKCU\Environment` appended to the machine PATH; on POSIX `HOME`, `USER`,
  `LOGNAME` and the conventional user bin directories. A bridge started by the
  scheduled-task watchdog had been handing its jobs empty profile variables and
  the machine PATH only, so per-user tools had to be located by hand inside
  every script. The result reports `user_path_entries`.
- `scripts/exec_bridge_selftest.py` grows from 31 to 40 cases: a script written
  in the other platform's convention runs and is reported normalized, its
  on-disk terminators are checked, a mixed file is proven untouched, and a
  second server started with the profile variables stripped must still hand a
  job every one of them. Run against the 1.2.0 server, seven of the new cases
  fail.
- **The Windows launchers derive their root.** `Startup/*.cmd` compute
  `COWORK_ROOT` from their own location (`%~dp0`), the way `Startup/posix/*.sh`
  already did, so a clone runs from any directory without personalization.
  `exec-server.cmd` creates `CommandJobs` and `Outputs` if the clone did not
  bring them; `fs-server.cmd` passes `%COWORK_ROOT%`, `%USERPROFILE%\Downloads`
  and - only when it is set and exists - `%COWORK_CONFIG_ROOT%`, otherwise it
  says so on stderr and starts with two roots rather than letting the upstream
  server exit on a missing folder. Machine-specific values live in a gitignored
  `Startup/cowork-env.cmd`, documented by `cowork-env.example.cmd`; the file is
  refused by name in `scripts/public_scan.py`, as `cowork-env.sh` is.
- **Roots by variable.** The Windows arguments in `Startup/.vscode/tasks.json`
  (and the KnownGood copy) use `${workspaceFolder}` like the `osx` and `linux`
  overrides; `docs/bridge-facts.json` states the filesystem roots as the launcher
  variables. `scripts/personalize.py` now finds nothing to rewrite in the
  launchers, the task file or the manifest roots - its scope is the watchdog,
  the connector packages, the shipped jobs and the skills. Issue #6, item 5.
- `facts_check.py` enforces the Windows half of the derivation rule: every
  `.cmd` launcher must set `COWORK_ROOT` from `%~dp0` and may not carry a
  `C:\Users\` path, and a filesystem root counts only when it is on the command
  line that starts the server. Two new negative controls, one re-anchored;
  `personalize_selftest.py` now asserts the launchers stay free of account paths
  before and after personalization.
- `docs/setup.md`, `docs/setup-macos.md`, `docs/install/claude-cowork-windows.md`
  and `AGENTS.md` describe the new shape: the hosted route still clones to the
  fixed path because its watchdog and jobs are personalized; a client that
  starts the launchers directly clones anywhere and sets its config root in
  `cowork-env.cmd`.

## 0.3.0 - 2026-09-07

Portable. Runs where the contributor is. 0.2.1 made the tree installable on Windows; this
makes it installable on a Mac, and makes "installed" a thing a machine can
prove rather than a thing a person believes.

- **The command bridge is cross-platform.** `batch-exec-server.js` now runs on
  Windows and POSIX from one source. The platform chooses the shell (`cmd.exe`
  vs `bash`), the executable extension (`.bat`/`.cmd` vs `.sh`), the comment
  marker the `COWORK_OUTPUT` directive hides behind, and how a runaway tree is
  killed. It chooses nothing else: the path validation, the containment checks,
  the single-flight lock and the fixed timeout are one implementation used by
  both. `scripts/exec_bridge_selftest.py` starts the real server as a stdio MCP
  process and tries 31 ways out of it, in the platform's own script language -
  so a refusal that holds on Windows and not on a Mac fails the gate.
- **The server carries no personalized path.** The tooling root comes from
  `COWORK_ROOT`, set by the launcher, and the lessons path from
  `COWORK_CONFIG_ROOT`. Two fewer files the personalizer has to rewrite.
- **POSIX launchers** under `Startup/posix/`, one per bridge, deriving the
  tooling root from their own location - so a clone runs from any directory
  without personalization. Machine-specific values live in a gitignored
  `cowork-env.sh`; `cowork-env.example.sh` documents each one.
- **One task file, two platforms.** `Startup/.vscode/tasks.json` gained `osx`
  and `linux` overrides that point at the POSIX launchers via
  `${workspaceFolder}`. The Windows arguments are unchanged, byte for byte.
- **A launchd watchdog** (`Startup/posix/watchdog/`) with the same contract as
  the Windows one: restart only a port that refuses connections, never kill,
  honour a cooldown, and say plainly that it cannot restore tunnel visibility.
- **`scripts/install_check.py`** - the definition of done for the install
  contract now in `AGENTS.md`. It completes a real stdio MCP handshake against
  each own-code bridge rather than testing that a file exists, checks the pinned
  runtime, enforces the 1024-character skill description cap that silently drops
  a skill, and runs the corpus checks. `--json` writes the evidence.
- **`docs/setup-macos.md`** - the POSIX path from zero, and an explicit table of
  the seven things that differ from Windows.
- **The disclosure scan reads shell scripts.** `.sh`, `.bash` and `.zsh` were
  not in the scanned extension set, so every file added above would have been
  unscanned; a POSIX home-directory pattern (`/Users/...`, `/home/...`) was
  added alongside the Windows one, and `cowork-env.sh` is refused by name. The
  gap was found by running the negative control, not by reading the code.
- `facts_check.py` verifies the POSIX launcher for each bridge, that it derives
  its root rather than hard-coding one, and that the task file actually starts
  it per platform - five new negative controls, 16 of 16 caught.
- **The snapshot model ends with this release.** Through 0.3.0 `main` was one
  commit, force-pushed on each publication from a private working copy. From
  here it keeps its history: changes arrive as pull requests, CI runs the gate on
  `windows-latest` **and** `macos-latest`, and merge needs a review from the
  owner named in `.github/CODEOWNERS`. `CONTRIBUTING.md`, `SECURITY.md`,
  `GitHubSetup/PUBLISHING.md`, `docs/architecture.md` and `docs/limitations.md`
  now describe that model and mark the old one as history. The macOS layer has
  a contributor, and a force-pushed root would have destroyed their fork.
- `docs/evidence/` is the reviewed home for `install_check.py --json` results
  from real machines. The checker now writes the file to be committed: the
  config root and home directory are replaced with placeholders before the
  file is written, so the disclosure scan does not have to catch them after.

## 0.2.1 - 2026-09-07

Installable. The 0.2.0 audit found a reference implementation that could be read
and validated but not stood up: no from-zero guide, placeholders in 65 files with
nothing to replace them, a connector package for one bridge out of four, and a
lessons corpus with no way to start empty. This snapshot closes those four gaps.

- `docs/setup.md`: from a bare Windows PC to four reachable bridges and an
  installed configuration, in twelve steps, each stated from the files in the
  tree rather than from memory. Tenant-dependent steps say so.
- `scripts/personalize.py`: replaces `YOURUSER`, the OneDrive folder name,
  `YOUR-TUNNEL-HOST` and the shared placeholder app id across `Startup/`,
  `CommandJobs/`, `CoworkConfig/` and `docs/bridge-facts.json`; dry run by
  default; leaves the documentation, the publishing tooling and the skill
  attribution lines alone. `scripts/personalize_selftest.py` proves each of
  those properties on a throwaway copy and that `public_scan.py` refuses the
  personalized result; the release gate runs it.
- Connector packages for all four bridges under `Startup/Plugins/` (the 8934
  package moves there from `Startup/FlowBridge/plugin/`). `facts_check.py` now
  verifies each package's connector id against the name the skills address, its
  URL against its port, and that no two personalized packages share an app id -
  three new negative controls in its self-test.
- `CoworkConfig/README.md`: what installs where, which blocks are generated from
  what, and the procedure for starting with an empty corpus - including what the
  checkers report on an empty file and why.
- `GO.bat` and `Startup/README.txt` corrected: the launcher comment still
  described two bridges and two ports.

## 0.2.0 - 2026-09-07

Verification and integrity. Three of the five v0.2 roadmap items ship here; the
other two - behavioral verdicts for ten routed rules, and reduction of duplicated
configuration statements - carry to v0.3.

- Cross-surface bridge facts check (`scripts/facts_check.py`, `docs/bridge-facts.json`):
  one manifest of ports, names, statefulness and roots, verified against the README,
  the Startup README, `tasks.json`, the watchdog and both bridge skills. Wired into
  the release check and CI. Closes #3. On first run it found two stale statements
  in the published skills (a "three bridges" count and a claim that port 8934 did
  not exist); both are corrected in this release.
- Runnable synthetic control loop (`examples/synthetic-control-loop/run.py`): a
  deterministic manifest validator that stops on a missing required segment, then
  the recorded three-arm-plus-control transcripts judged by `verify_delivery.py`
  into a demonstration ledger. No host, tunnel or network required. Wired into the
  release check and CI. Closes #4.
- Machine-readable release results: `release_check.py --json` writes
  `release-results.json`; CI publishes it as a build artifact.
- README: status, platform and host stated in the first screen; the bridges are
  described as standard MCP servers with Cowork as the client they were built
  against. Tagline changed from "proven in" to "built and operated in public
  accounting" to match the evidence table.
- Publication model restored to a single rebuilt commit on `main`; `v0.1.0` re-cut
  as a single commit carrying the released tree minus the editorial roadmap files
  and the links to them, otherwise unchanged.
- Removed: the editorial article roadmap (publishing intent, not documentation);
  `GitHubSetup/public-template/`, a duplicate of `docs/`, `examples/`, `scripts/`
  and `.github/`; `docs/initial-issues.md` (the issues are open on GitHub); the
  Cowork runtime folder notice that shipped as `CoworkConfig/AGENTS.md`.
- Added: root `AGENTS.md` for agents working in this repository;
  `GitHubSetup/PUBLISHING.md` (formerly `PLAN.md`) with current settings; a
  substitution statement for the published lessons corpus in `SECURITY.md`.
- Corrected in `CoworkConfig/Skills`: `git-bridge` no longer states that port 8934
  does not exist and scopes its never-push rule to the working repository;
  `local-file-bridge` counts four bridges and four tasks.

## 0.1.0 - 2026-09-03

Foundation-layer publication.

- Four bridges: Playwright (8931), filesystem (8932), approved batch executor
  (8933, v1.1.0), Power Automate (8934, v0.5.0 with 29 tools and a plugin
  manifest). Watchdog covering all four ports; bounded auto-recovery policy
  with a self-test.
- Eleven skills, each carrying a generated `SKILL-LESSONS` block where lessons
  route to it.
- The self-improvement toolchain: lessons corpus (123 entries), always-on
  digest with tiering, per-surface gate with receipts, job linter, skill and
  plugin lesson delivery, delivery verification (three carried runs plus a
  control), nightly consolidation analyser and measurement, and a self-test for
  every checker.
- Two-tier memory files and their index.
- The publish gate itself (`GitHubSetup/`): preflight scan, clean-room build
  with sanitization of contents and file names, name-shape autoscans, and a
  prose sweep for engagement vocabulary.
- Public-accounting positioning: vision, control map, architecture, measured
  results, limitations, roadmap, and published-writing assessment.
- Synthetic control-loop demonstration showing a missing input becoming a
  hard-stop rule and a behavioral verification case.
- Public repository infrastructure: CI, issue forms, CODEOWNERS, pull-request
  controls, support boundary, citation metadata, and machine-readable
  `llms.txt`.
- One-command public scan and release check.
- Anonymized throughout: account, firm, tenant, environments, tunnel host,
  client and colleague names replaced with placeholders; firm-abbreviated file
  names renamed (`cowork-close.bat`, `deck-builder`).

Withheld from this and every snapshot: engagement-shaped skills, the firm's
brand-standard skill, two memory files describing non-public work, outputs,
logs, local configuration, and the verification jobs that embed the strings
they check for.
