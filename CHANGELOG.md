# Changelog

All notable changes to the published snapshot. The private working repository
keeps the full commit history; each entry here summarizes one publication.

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
