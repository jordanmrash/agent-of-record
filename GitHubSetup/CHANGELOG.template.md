# Changelog

All notable changes to the published snapshot. The private working repository
keeps the full commit history; each entry here summarizes one publication.

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
