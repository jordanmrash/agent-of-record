# Working in this repository as an agent

This file is for AI coding agents and assistants operating on this repository. The
human-facing entry point is `README.md`.

## What this repository is

A published snapshot of a governed agent foundation: four local MCP bridges, a
two-tier memory, a lessons corpus with generated delivery into skills, a behavioral
verification harness, and clean-room publication tooling. It is a reference
implementation, not a service, and it contains no client, firm, tenant or credential
material. Placeholders are `YOURUSER`, `YOUR-TUNNEL-HOST`, `you@example.com`,
`yourorg.crm.dynamics.com` and the zero GUID.

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

## Conventions

- One commit per publication. `main` is rebuilt and force-pushed; do not stack
  commits on it. See `GitHubSetup/PUBLISHING.md`.
- `CHANGELOG.md` gets one entry per publication. The README measurements table is
  updated from the release output, never typed in.
- Attribution blocks inside each skill are license terms. Add a name alongside;
  never remove one.
- Prose states evidence, not aspiration. A control that cannot observe a surface
  says so; a rule that has not been behaviorally verified is not called effective.
