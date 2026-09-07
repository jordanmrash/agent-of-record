# Synthetic Control-Loop Demonstration

```bash
python examples/synthetic-control-loop/run.py
```

Runs in about a second on a clean checkout. No tenant, tunnel, browser or network is
involved, and nothing in the repository is modified.

## Scenario

A fictional month-end workpaper workflow receives a source bundle with a required
segment missing. The agent's first design continues processing and produces a
complete-looking result. A reviewer detects the omission.

No real client, firm, tax calculation, or production system is represented here.
Every figure is invented and every transcript is synthetic.

## What runs

1. **The gate accepts a complete input set.** `validate_manifest.py inputs/complete`
   reads the manifest, finds all four required segments, and exits 0.
2. **The gate refuses an incomplete one.** `validate_manifest.py inputs/incomplete`
   finds Segment D absent, prints `HARD STOP`, names D, produces nothing, and exits 3.
   This is the enforcement mechanism the lesson prescribes: a deterministic check in
   code, not an instruction to the model.
3. **The delivered rule is measured, not assumed.** The repository's real
   verification harness, `verify_delivery.py`, judges four recorded transcripts:
   three test arms with the rule delivered and one control with it withheld. All
   three arms stop and name D; the control builds the workpaper from A-C and
   reports success. Verdict: **EFFECTIVE** - the rule is doing the work, because
   the run without it failed.

The recorded transcripts carry the fingerprint of the exact case and rule text they
were judged against. Change a prompt, the pass criterion or the rule and the judge
refuses them: a stored verdict must not outlive the text it judged. Step 3 then
fails, which is the harness working as designed.

## How this maps to the architecture

| Stage | File |
|---|---|
| The failure is recorded as an incident | `incident.md` |
| A reusable rule is extracted, in the corpus format the harness reads | `lesson.md` |
| A deterministic validator becomes the control | `validate_manifest.py`, `inputs/` |
| Three prompts invite the mistake; a control prompt withholds the rule | `verification-case.json` |
| The four arms are judged against a control | `recorded-runs.json` -> `verify_delivery.py judge` |
| The whole loop is checked on every push | `run.py --check`, called by `scripts/release_check.py` and CI |

## Why this matters in public accounting

A complete-looking workpaper with incomplete inputs is more dangerous than a visible
failure. The correct agent behavior is not to do its best with what is there; it is
to stop, identify the missing evidence, and preserve an audit record. The
demonstration shows that behavior being enforced by code and then verified against
a control rather than asserted.
