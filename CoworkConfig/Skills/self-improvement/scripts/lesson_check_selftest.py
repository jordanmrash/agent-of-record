#!/usr/bin/env python3
"""
lesson_check_selftest.py - negative controls for lesson_check.py.

Discipline this suite follows, learned the hard way and recorded in
`verifier-ignores-structural-diff`:
  1. The POSITIVE control runs FIRST and gates the rest. A suite that cannot
     demonstrate a pass proves nothing when everything comes back red.
  2. Every negative control asserts WHY the checker failed - the specific code -
     not merely THAT it failed. A defect caught for the wrong reason is a miss
     that reports as a hit.

Exit 0 only when the positive control passes and every negative control is
caught for its own stated reason.
"""

import sys

from lesson_check import check

GOOD = """# Lessons

## Failures

### A good entry that should pass every check
- **Pattern-Key:** good-entry-passes-clean
- **Date:** 2026-08-28
- **Trigger:** failure
- **Hits:** 1
- **Failed:** Something specific went wrong and this states it plainly.
- **Why:** The mechanism, named.
- **Worked:** Run `thing_check.py` and require exit code 0 before reporting.
- **Evidence:** measured - the run was observed
- **See also:** second-entry-also-clean

### A second entry so cluster and duplicate logic has something to chew on
- **Pattern-Key:** second-entry-also-clean
- **Date:** 2026-08-28
- **Trigger:** better-approach
- **Hits:** 1
- **Failed:** A worse approach was used first.
- **Why:** It skipped a step.
- **Worked:** Assert the count matches before publishing.
- **Evidence:** measured - both runs compared

## Contradictions - stored memories that proved wrong

### A contradiction filed where contradictions go
- **Pattern-Key:** contradiction-filed-correctly
- **Date:** 2026-08-28
- **Trigger:** contradiction
- **Hits:** 1
- **Failed:** A stored belief was acted on and proved wrong.
- **Why:** It was never re-checked.
- **Worked:** Re-read the source file, assert the value still holds.
- **Evidence:** measured - the stored value and the file disagreed

## Open questions

### An unresolved one, correctly parked
- **Pattern-Key:** unresolved-parked-correctly
- **Date:** 2026-08-28
- **Trigger:** failure
- **Hits:** 1
- **Failed:** Nothing fixed it.
- **Why:** Not established.
- **Worked:** UNKNOWN - no fix was found and none should be assumed.
- **Evidence:** measured - the failure was observed, the cause is unprobed
"""


def mutate(base, old, new):
    assert base.count(old) == 1, f"anchor not unique: {old[:50]}"
    return base.replace(old, new)


NEGATIVES = [
    ("missing_field", "drop the Evidence line",
     lambda t: mutate(t, "- **Evidence:** measured - the run was observed\n", "")),

    ("missing_field", "drop the Why line",
     lambda t: mutate(t, "- **Why:** The mechanism, named.\n", "")),

    ("duplicate_key", "reuse a Pattern-Key",
     lambda t: mutate(t, "- **Pattern-Key:** second-entry-also-clean",
                      "- **Pattern-Key:** good-entry-passes-clean")),

    ("misfiled_contradiction", "put a contradiction under Failures",
     lambda t: mutate(t, "- **Trigger:** better-approach", "- **Trigger:** contradiction")),

    ("misfiled_unknown", "put an UNKNOWN entry under Failures",
     lambda t: mutate(t, "- **Worked:** Run `thing_check.py` and require exit code 0 before reporting.",
                      "- **Worked:** UNKNOWN - nothing fixed it.")),

    ("promotion_due", "let a 2-hit entry sit unpromoted",
     lambda t: mutate(t, "- **Pattern-Key:** good-entry-passes-clean\n- **Date:** 2026-08-28\n- **Trigger:** failure\n- **Hits:** 1",
                      "- **Pattern-Key:** good-entry-passes-clean\n- **Date:** 2026-08-28\n- **Trigger:** failure\n- **Hits:** 2")),

    ("promotion_stale", "leave a promotion flag open",
     lambda t: mutate(t, "- **Hits:** 1\n- **Failed:** Something specific went wrong",
                      "- **Hits:** 1\n- **Promotion:** DUE at 2 hits, awaiting a yes\n- **Failed:** Something specific went wrong")),

    ("section_order", "put Contradictions before Failures",
     lambda t: t.replace("## Failures", "## TEMP", 1)
                .replace("## Contradictions - stored memories that proved wrong", "## Failures", 1)
                .replace("## TEMP", "## Contradictions - stored memories that proved wrong", 1)),

    ("unknown_trigger", "use a trigger outside the vocabulary",
     lambda t: mutate(t, "- **Trigger:** failure\n- **Hits:** 1\n- **Failed:** Something specific",
                      "- **Trigger:** vibes\n- **Hits:** 1\n- **Failed:** Something specific")),

    ("evidence_unlabelled", "drop the measured/inferred label",
     lambda t: mutate(t, "- **Evidence:** measured - the run was observed",
                      "- **Evidence:** it seemed to work")),

    ("prose_only", "write a Worked line with no mechanism",
     lambda t: mutate(t, "- **Worked:** Run `thing_check.py` and require exit code 0 before reporting.",
                      "- **Worked:** Be more careful next time and remember to check.")),

    ("dangling_see_also", "point See also at a key that does not exist",
     lambda t: mutate(t, "- **See also:** second-entry-also-clean",
                      "- **See also:** this-key-does-not-exist-anywhere")),

    ("no_rule_line", "let a 2-hit entry have no one-line Rule",
     lambda t: mutate(t, "- **Trigger:** better-approach\n- **Hits:** 1",
                      "- **Trigger:** better-approach\n- **Hits:** 2\n- **Promoted-to:** somewhere")),

    ("no_entries", "hand it a file with no entries",
     lambda t: "# Lessons\n\n## Failures\n\nNothing here.\n"),

    # The cluster check had NO negative control until 2026-08-28, and it was
    # warning on size alone. The fixture must clear the 6-key threshold AND
    # carry an unpromoted repeat, or a broken check still passes.
    ("topic_cluster", "a big cluster hiding a repeat nobody promoted",
     lambda t: t + "".join(
         "\n### Cluster entry {i}\n"
         "- **Pattern-Key:** widget-thing-{i}\n"
         "- **Date:** 2026-01-01\n"
         "- **Trigger:** failure\n"
         "- **Rule:** Rule {i}.\n"
         "- **Hits:** {h}\n"
         "- **Failed:** x\n- **Why:** y\n"
         "- **Worked:** run check.py and assert exit code\n"
         "- **Evidence:** measured\n".format(i=i, h=2 if i == 0 else 1)
         for i in range(7))),
]


def main():
    print("=" * 62)
    print("POSITIVE CONTROL (must pass, or the suite proves nothing)")
    print("=" * 62)
    findings, entries = check(GOOD)
    blocking = [f for f in findings if f["level"] in ("FAIL", "WARN")]
    if blocking:
        print("  POSITIVE CONTROL FAILED - suite aborted.")
        for f in blocking:
            print(f"    {f['level']} {f['code']}: {f['message']}")
        return 1
    print(f"  clean on {len(entries)} entries, 0 FAIL, 0 WARN\n")

    print("=" * 62)
    print(f"NEGATIVE CONTROLS ({len(NEGATIVES)})")
    print("=" * 62)
    caught = 0
    for code, label, mut in NEGATIVES:
        try:
            broken = mut(GOOD)
        except AssertionError as exc:
            print(f"  MISS  {code:26} mutation could not be applied: {exc}")
            continue
        found, _ = check(broken)
        codes = {f["code"] for f in found}
        if code in codes:
            caught += 1
            print(f"  OK    {code:26} {label}")
        else:
            print(f"  MISS  {code:26} {label}")
            print(f"        expected '{code}', got {sorted(codes) or 'nothing'}")

    print()
    print("=" * 62)
    print(f"RESULT: {caught}/{len(NEGATIVES)} caught for the right reason")
    print("=" * 62)
    return 0 if caught == len(NEGATIVES) else 1


if __name__ == "__main__":
    sys.exit(main())
