# Roadmap

## v0.1: Foundation layer

Released 2026-09-04.

- Four governed bridges.
- Two-tier memory.
- Lessons corpus and generated delivery.
- Behavioral verification harness.
- Nightly consolidation and measurement.
- Clean-room publication.
- Public-accounting vision and control map.

## v0.2: Verification and integrity

Released 2026-09-07.

- Cross-surface bridge facts manifest and drift check (`docs/bridge-facts.json`, `scripts/facts_check.py`). Shipped.
- Self-tests consolidated under one runner (`scripts/release_check.py`). Shipped.
- Machine-readable release results (`release_check.py --json`, published by CI). Shipped.
- Runnable synthetic control-loop demonstration (`examples/synthetic-control-loop/run.py`). Shipped.
- Expand behavioral verification to at least ten rules. Carried to v0.4.
- Reduce duplicate configuration statements. Carried to v0.4; the facts check now measures the bridge subset.
- 0.2.1: installable - setup guide from zero, placeholder personalizer with self-test, connector packages for all four bridges under the facts check, configuration guide with an empty-corpus start. Shipped 2026-09-07.

## v0.3: Portable

Released 2026-09-07.

- One command bridge for Windows and POSIX, one refusal set, proven live by
  `scripts/exec_bridge_selftest.py` in each platform's own script language.
  Shipped.
- POSIX launchers under `Startup/posix/` that derive their root from their own
  location; machine values in a gitignored `cowork-env.sh`. Shipped.
- `scripts/install_check.py`: a real stdio MCP handshake per own-code bridge,
  the pinned runtime, the 1024-character skill description cap, and the corpus
  checks, with `--json` results meant to be committed as evidence. Shipped.
- Install contract in `AGENTS.md`; `docs/setup-macos.md`; launchd watchdog.
  Shipped.
- CI gate on `windows-latest` and `macos-latest`; `main` keeps its history,
  protected, with a contributor on the macOS side. Shipped.
- Skill host-adapter sections and a lesson `Applies-to` field, so the shipped
  skills describe more than one operator's machine. Carried to v0.4.
- Portable was pulled forward ahead of the applied-work contract because a
  contributor on a second platform needed it first. The contract, and the two
  verification items carried from v0.2, move to v0.4 unchanged.
- 0.3.1: documentation release ahead of the first public link - both routes on
  every architecture page, counts reconciled to the shipped corpus, attribution
  completed, release metadata matched to `main`. Shipped 2026-09-10.

## v0.4: Applied-work contract

Carried from v0.2: behavioral verdicts for at least ten routed rules; reduction
of duplicated configuration statements. Carried from v0.3: skill host-adapter
sections and the lesson `Applies-to` field.

Define a common contract for every applied public-accounting skill:

- Purpose and accountable owner.
- Input and schema requirements.
- Evidence and provenance.
- Deterministic calculations.
- Hard-stop conditions.
- Review and approval points.
- Output and audit record.
- Test and release requirements.

## v0.5: Applied skills

Add independently tested, synthetic-data versions of selected workflows:

- Tax provision support.
- State apportionment.
- Journal entries and footnotes.
- Workpaper intake and validation.
- Reconciliation and close support.
- Research and professional communication.
- Workflow conversion from desktop automation into tested Python packages.

Each applied skill is expected to define its inputs, evidence, deterministic calculations,
failure behavior, review points, audit record, and tests before it is treated as reusable.

## v0.6: Portfolio governance

- Environment promotion model.
- Release and rollback standards.
- Role and responsibility matrix.
- Retention and retirement policy.
- Common monitoring and incident response.

## v1.0: Reference operating model

- Reproducible installation. Delivered for Windows and macOS in v0.3; kept here for the applied-skill layer.
- Stable interfaces.
- Complete documentation.
- Maintainer and contribution model.
- Demonstrated applied-skill portfolio.
- Published findings from repeated behavioral verification.
