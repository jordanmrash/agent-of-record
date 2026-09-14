# Working in this repository as an agent

This file is for AI coding agents and assistants operating on this repository. The
human-facing entry point is `README.md`.

## What this repository is

The public repository of a governed agent foundation: four local MCP bridges, a
two-tier memory, a lessons corpus with generated delivery into skills, a behavioral
verification harness, and clean-room publication tooling. It is a reference
implementation, not a service, and it contains no client, firm, tenant or credential
material. Placeholders are `YOURUSER`, `YOUR-TUNNEL-HOST`, `you@example.com`,
`yourorg.crm.dynamics.com` and the zero GUID.

## The install contract

An agent pointed at a clone of this repository and asked to "set this up" has a
defined job with a defined end. This is that definition. Do not improvise a
different one, and do not report success on any evidence weaker than step 5.

1. **Determine the host.** Windows and POSIX (macOS, Linux) are both supported
   and they differ in four places only: the launcher directory (`Startup/` vs
   `Startup/posix/`), the executable script extension (`.bat`/`.cmd` vs `.sh`),
   the watchdog mechanism (Task Scheduler vs `launchd`), and the browser the
   Playwright bridge drives. Everything else is shared. `docs/setup.md` is the
   Windows path; `docs/setup-macos.md` is the POSIX one.
   Both describe a client that runs in the cloud and reaches the bridges through a dev
   tunnel - the **hosted** route. A client that runs on the machine itself (Claude
   Cowork) is the **local** route: it registers the launchers as stdio servers and skips
   the tunnel, `supergateway`, the connector packages, the Copilot-only personalizer and the Windows watchdog,
   and it installs only what that host lacks - the executor is required, the browser and
   filesystem bridges are optional. `docs/install/README.md` compares the routes;
   `docs/install/claude-cowork-*.md` are the pages. The local route needs a **local**
   desktop session: the vendor states that local MCP servers do not run in a cloud
   session, so an agent in a cloud session cannot complete it and must say so.

2. **Validate the checkout before changing it.** `python scripts/release_check.py`
   must print `RELEASE_CHECK: CLEAN`. If it does not, stop and report - the tree
   is not what was published and nothing below will behave as documented.

3. **Install the runtime.** Hosted route: `cd Startup && npm install` (pins
   supergateway, the HTTP wrapper the tunnel needs). Local route: nothing - the executor
   is plain `node` and the host starts it directly, so do not install `supergateway`.
   On POSIX also `chmod +x Startup/posix/*.sh` on either route; a clone can arrive
   without the execute bit, and the launchers will not start without it.

4. **Configure the machine, never the repository.** Real paths belong in
   `Startup/cowork-env.cmd` (Windows) or `Startup/posix/cowork-env.sh` (POSIX),
   both gitignored and both refused by name in `scripts/public_scan.py`; copy the
   `cowork-env.example.*` beside each and set `COWORK_CONFIG_ROOT` to the folder
   the host loads skills from. The launchers derive the tooling root from their
   own location on both platforms, so a client that starts them directly
   (`docs/install/`) can use a clone in any directory. The hosted (tunnel)
   route still runs `scripts/copilot/personalize.py` for the connector manifests, the
   watchdog, the shipped jobs and the skills, and those expect the clone at the
   path `docs/setup.md` names. The operator's OneDrive folder name and account
   name are things you must ASK for or read from the environment - never guess,
   and never write either into a tracked file. `scripts/public_scan.py` exists
   to catch you if you do.

5. **Prove it, and let the proof be the report.**

   ```bash
   python scripts/install_check.py --json install-results.json                # hosted route
   python scripts/install_check.py --route local --json install-results.json  # local route
   ```

   This performs a real stdio MCP handshake against each own-code bridge,
   checks the pinned runtime, enforces the 1024-character skill description cap,
   and runs the corpus checks. `INSTALL_CHECK: CLEAN` is the completion
   criterion. A `FAIL` line is the work that remains; each one names its own
   remedy.

**What you cannot verify, you must not claim.** Three things decide whether the
bridges are reachable from a Cowork session and none of them are observable from
the machine: whether the dev tunnel ports are set Public, whether the connector
packages were uploaded, and whether tenant policy permits custom apps at all.
`install_check.py` deliberately does not guess at them. Report them as operator
steps with their evidence unknown rather than as passing checks.

## Before you change anything

1. Run the gate on a clean checkout and keep the output:

   ```bash
   python scripts/public_scan.py
   python scripts/release_check.py --json release-results.json
   ```

   Both must exit zero before and after your change. The release check runs the
   integrity checks, the bridge facts check, the synthetic demonstration and the
   negative-control self-test suites.

2. Read `docs/architecture.md` and `SECURITY.md`. Two of the bridges execute with
   the signed-in user's authority on a real machine; the documentation states the
   trust boundaries and the residual risks. Do not narrow them in prose without
   narrowing them in code.

## Rules that are enforced by the checks

- **Generated blocks are not edited by hand.** Every `SKILL.md` carries a block
  between `<!-- SKILL-LESSONS:start -->` and `<!-- SKILL-LESSONS:end -->`, and
  `CoworkConfig/copilot-instructions.md` carries one between the `LESSON-DIGEST`
  markers. They are regenerated from `CoworkConfig/cowork-memory/cowork-lessons.md`
  by `skill_lessons.py` and `digest_apply.py`. Edit the lesson entry; rerun the
  generator; the currency checks fail otherwise.
- **Bridge facts have one home.** Ports, names, statefulness and roots live in
  `docs/bridge-facts.json`. `scripts/facts_check.py` verifies every surface that
  restates them. Change the manifest first, then the surfaces.
- **A checker change needs a self-test change.** Each script under
  `CoworkConfig/Skills/self-improvement/scripts/` has a `_selftest.py` sibling that
  breaks it on purpose. A change to a checker without a change to its self-test is
  incomplete, and `release_check.py` runs the suites.
- **No identifiers.** `scripts/public_scan.py` refuses real user paths, tunnel
  hostnames, tenant or environment identifiers and credential shapes. It runs in CI.
- **Connector packages have one home.** Each bridge's Cowork connector package is
  under `Startup/Plugins/<name>/`; `docs/bridge-facts.json` names the package and
  the connector id the skills address, and `facts_check.py` verifies both.

## Installing is not publishing

`scripts/copilot/personalize.py` turns the placeholders into one operator's real values
across the operating trees (`Startup/`, `CommandJobs/`, `CoworkConfig/`,
`docs/bridge-facts.json`). A personalized tree fails `public_scan.py` by design.
Never run the personalizer on a tree you intend to push; never "fix" the scan by
widening its patterns. `docs/setup.md` is the installation path.

## Conventions

- `main` keeps its history and is protected: changes arrive as pull requests,
  pass the gate on Windows and macOS in CI, and merge after review by the owner
  named in `.github/CODEOWNERS`. Never force-push. The history before v0.3.0
  is a series of single-commit snapshots; see `GitHubSetup/PUBLISHING.md`.
- `CHANGELOG.md` gets one entry per publication. The README measurements table is
  updated from the release output, never typed in.
- Attribution blocks inside each skill are license terms. Add a name alongside;
  never remove one.
- Prose states evidence, not aspiration. A control that cannot observe a surface
  says so; a rule that has not been behaviorally verified is not called effective.
