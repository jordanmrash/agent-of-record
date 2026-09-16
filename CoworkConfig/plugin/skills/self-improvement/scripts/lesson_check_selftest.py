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

import os
import tempfile

from lesson_check import check, digest_findings

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

    ("misfiled_failure", "park a RESOLVED entry under Open questions",
     lambda t: mutate(t, "- **Worked:** UNKNOWN - no fix was found and none should be assumed.",
                      "- **Worked:** Run `fix_it.py` and assert exit code 0.")),

    ("misfiled_failure", "file a plain failure under Contradictions",
     lambda t: mutate(t, "- **Trigger:** contradiction", "- **Trigger:** failure")),

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


# ---------------------------------------------------------------------------
# DIGEST TIER CASES, added 2026-09-11.
#
# The digest check lived inline in main() and check() never saw it, so it had
# no control of any kind while it was quietly reporting the pre-tiering
# population. These drive digest_findings directly.
#
# Fixture: two entries carry a Rule. `repeat-rule-two-hits` is a repeat and so
# belongs to the always-on tier. `single-hit-rule` has one hit and belongs in
# the per-surface tier, so its ABSENCE from the block must not be a finding -
# that absence is the whole design.
# ---------------------------------------------------------------------------

DIGEST_LESSONS = """# Lessons

## Failures

### A repeat that must load every session
- **Pattern-Key:** repeat-rule-two-hits
- **Date:** 2026-09-11
- **Trigger:** failure
- **Rule:** Always assert the exit code before reporting a result.
- **Hits:** 2
- **Promoted-to:** the always-on digest tier
- **Failed:** A result was reported without reading the exit code.
- **Why:** The wrapper swallowed it.
- **Worked:** Run check.py and assert exit code 0.
- **Evidence:** measured - the run was observed

### A single-hit rule that belongs in the per-surface tier
- **Pattern-Key:** single-hit-rule
- **Date:** 2026-09-11
- **Trigger:** failure
- **Rule:** Pass the folder in paths and keep the pattern relative.
- **Hits:** 1
- **Failed:** An absolute pattern matched nothing.
- **Why:** The tool anchors every pattern under its root.
- **Worked:** Run glob with a relative pattern and assert a non-zero count.
- **Evidence:** measured - both forms were run
"""

BLOCK_TIERED = ("<!-- LESSON-DIGEST:BEGIN -->\\n"
                "- Always assert the exit code before reporting a result.\\n"
                "<!-- LESSON-DIGEST:END - 1 always-on of 2 rules from 2 entries -->")

BLOCK_MISSING_ALWAYSON = ("<!-- LESSON-DIGEST:BEGIN -->\\n"
                          "- Pass the folder in paths and keep the pattern relative.\\n"
                          "<!-- LESSON-DIGEST:END - 1 always-on of 2 rules from 2 entries -->")


def digest_cases():
    """Returns (passed, total) and prints each case."""
    from lesson_check import parse
    _, entries = parse(DIGEST_LESSONS)
    tiers = os.path.join(tempfile.mkdtemp(prefix="tiers-"), "digest-tiers.txt")
    with open(tiers, "w", encoding="utf-8") as fh:
        fh.write("# test tiers - no PIN, no ENFORCED\\n")

    cases = []

    # POSITIVE CONTROL. A correctly tiered block omits the single-hit rule.
    # Before the fix this case FAILED, which is the defect in one line.
    codes = {f["code"] for f in digest_findings(entries, BLOCK_TIERED, tiers)}
    cases.append((not codes, "positive: a tiered block with only the always-on "
                             "rule is clean", codes))

    # NEGATIVE: an always-on rule genuinely missing must still FAIL.
    codes = {f["code"] for f in digest_findings(entries, BLOCK_MISSING_ALWAYSON, tiers)}
    cases.append(("digest_stale" in codes,
                  "negative: a repeat rule absent from the block is digest_stale",
                  codes))

    # NEGATIVE: no block at all.
    codes = {f["code"] for f in digest_findings(entries, "nothing here", tiers)}
    cases.append(("digest_missing" in codes,
                  "negative: no LESSON-DIGEST block is digest_missing", codes))

    # NEGATIVE: the tiers file is gone, so the always-on set cannot be computed.
    # This must be its own finding and never a silent pass.
    codes = {f["code"] for f in digest_findings(entries, BLOCK_TIERED,
                                                tiers + ".does-not-exist")}
    cases.append(("digest_tiers_missing" in codes,
                  "negative: a missing tiers file refuses rather than passing",
                  codes))

    passed = 0
    for ok, label, codes in cases:
        if ok:
            passed += 1
            print(f"  OK    {'digest':26} {label}")
        else:
            print(f"  MISS  {'digest':26} {label}")
            print(f"        got {sorted(codes) or 'nothing'}")
    return passed, len(cases)


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
    print("DIGEST TIER CONTROLS")
    print("=" * 62)
    dpassed, dtotal = digest_cases()

    print()
    print("=" * 62)
    print(f"RESULT: {caught}/{len(NEGATIVES)} negative controls caught for the "
          f"right reason; {dpassed}/{dtotal} digest tier controls")
    print("=" * 62)
    return 0 if (caught == len(NEGATIVES) and dpassed == dtotal) else 1


if __name__ == "__main__":
    sys.exit(main())
