# Measured Results and Honest Boundaries

## Snapshot

| Measure | Result |
|---|---:|
| Lesson entries | 123 |
| Authored rules | 93 |
| Always-on rules | 32 |
| Keys delivered to at least one skill | 80 |
| Keys delivered to plugin tool descriptions | 5 |
| Routed skills | 9 |
| Self-test suites | 10 |
| Effective behavioral verdicts | 1 |
| Inert behavioral verdicts | 1 |
| Fully enforced rules across every declared surface | 0 |

## What the figures mean

### Recorded is not enforced

A lesson can exist in the corpus and still be unavailable at the moment it matters.

### Delivered is not promoted

A generated rule inside a skill loads only when the skill loads. It is not equivalent to an always-on instruction.

### Checked is not fully enforced

A file linter can refuse a mistake in `.bat`, `.cmd`, or `.ps1` while remaining unable to observe an agent taking the same action directly in the session.

### Passing is not effective

If three agents carrying a rule pass, but the control agent without the rule also passes, the rule is inert on that surface. The correct action is to reclaim the prompt budget rather than congratulate the intervention.

## Negative results preserved

The verification ledger retains superseded and failed verdicts. That history shows:

- A first version of a rule was unreliable.
- A sharpened version became effective.
- A different rule restated a machine-enforced input schema and was measured inert.
- Hard-coded verification expectations can fail when the system is correct.

Preserving these results is part of the evidence. A learning system that deletes its failed experiments cannot explain why its current design exists.

## Current limitations of the evidence

- Behavioral verification covers only a small portion of routed rules.
- Most lesson entries are advice rather than machine-enforced checks.
- No automated control observes every direct action an agent can take in a session.
- The figures describe this snapshot, not a benchmark against other agent systems.
- The tests show internal consistency and specific behavior; they do not establish suitability for a particular professional engagement.

## Near-term measurement targets

1. Behavioral verdicts for at least ten high-cost or high-risk rules.
2. A shared cross-surface facts check for bridge ports, roots, and fallback policy.
3. One consolidated self-test runner with published CI results.
4. A common control contract for applied accounting skills.
5. Synthetic demonstrations that expose normal, boundary, and failure behavior.
