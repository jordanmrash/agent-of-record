# Synthetic Control-Loop Demonstration

## Scenario

A fictional month-end workpaper workflow receives a source file with a required segment missing.

The agent's first design continues processing and produces a complete-looking result. A reviewer detects the omission.

No real client, firm, tax calculation, or production system is represented here.

## What the example demonstrates

1. The failure is recorded as an incident.
2. A reusable rule is extracted: missing required segments cause a hard stop.
3. The rule is routed to the owning workpaper skill.
4. A deterministic input validator becomes the enforcement mechanism.
5. Three test prompts invite the same mistake in different ways.
6. A control prompt removes the rule.
7. The evidence determines whether the intervention is effective, inert, or unreliable.

## Files

- `incident.md` — the original failure and evidence.
- `lesson.md` — the reusable lesson and control rule.
- `verification-case.json` — the behavioral test design.

## Why this matters in public accounting

A complete-looking workpaper with incomplete inputs is more dangerous than a visible failure. The correct agent behavior is not to “do its best”; it is to stop, identify the missing evidence, and preserve an audit record.
