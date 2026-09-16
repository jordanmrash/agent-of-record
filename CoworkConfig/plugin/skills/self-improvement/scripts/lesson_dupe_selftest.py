#!/usr/bin/env python3
"""lesson_dupe_selftest.py - prove the Distinct-from disposal actually reads
every Distinct-from line, and that the check can still say no.

Run it against the UNPATCHED lesson_dupe.py and cases 1 and 4 must FAIL. That
is the point: a test that passes on the broken code proves nothing about the
fix. `--expect-broken` asserts exactly that, so the negative control is itself
checked rather than described.
"""

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = []


def record(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print("%-4s %s%s" % ("PASS" if ok else "FAIL", name,
                         ("   [%s]" % detail) if detail and not ok else ""))
    return ok


def entry(key, title, rule, failed, why, worked, extra=""):
    return (
        "### %s\n"
        "- **Pattern-Key:** %s\n"
        "- **Date:** 2026-09-01\n"
        "- **Trigger:** failure\n"
        "- **Rule:** %s\n"
        "- **Failed:** %s\n"
        "- **Why:** %s\n"
        "- **Worked:** %s\n"
        "- **Evidence:** measured\n"
        "- **Hits:** 1\n"
        "%s\n" % (title, key, rule, failed, why, worked, extra)
    )


# The new key is deliberately a lexical twin of TWO existing keys, so both
# land at or above the floor and BOTH must be dispositioned for the gate to
# pass. That is the shape of the case that cost a session 20 minutes.
#
# On a fixture this small the p99.5 floor collapses to the maximum observed
# score (lesson_dupe's own MIN_PAIRS note says a percentile below 200 pairs is
# "just the maximum, renamed"). So the two twins carry IDENTICAL weighted text
# AND title as the new entry: that ties all three at the maximum and puts both
# neighbours at the floor, which is the only arrangement in which the second
# Distinct-from line is load-bearing. An earlier draft of this fixture varied
# the titles, the two neighbours landed just BELOW a floor set by an unrelated
# pair, and the case passed on the broken code - a fixture too small to reach
# the threshold it guards.
TWIN_A = ("retry the devtunnel hop once after a dropped bridge call, then "
          "verify the write landed before retrying it a second time")
TWIN_B = TWIN_A
TWIN_TITLE = "Retry a dropped tunnel call once"

BASE = [
    entry("bridge-tunnel-retry-once", TWIN_TITLE,
          TWIN_A, TWIN_A, TWIN_A, TWIN_A),
    entry("bridge-tunnel-drop-verify", TWIN_TITLE,
          TWIN_B, TWIN_B, TWIN_B, TWIN_B),
    entry("memory-cap-rejects", "Keep a memory under the cap",
          "keep a saved memory under 512 characters or it stores nothing",
          "saved an over-length memory", "the cap rejects silently",
          "read the success field of every save"),
    entry("git-status-before-narrating", "Read git status before describing",
          "read the actual working tree before describing repo state",
          "narrated the repo from memory", "memory drifts from the tree",
          "ran git status and read it"),
    entry("skill-description-cap", "Watch the description cap",
          "a description over 1024 units silently fails to load the skill",
          "shipped an over-cap description", "the loader drops it without error",
          "trimmed to under 900 units"),
    entry("onedrive-mount-read-lag", "Wait before calling a file lost",
          "wait and hash before concluding a mounted file was lost",
          "declared a file lost from one stale read",
          "the mount can serve a partly-flushed file", "waited and re-hashed"),
]


def corpus(new_entry):
    return ("# Lessons\n\n## Failures\n\n" + "".join(BASE) + "\n" + new_entry
            + "\n## Contradictions - stored memories that proved wrong\n\n"
              "## Open questions\n\n")


def run_gate(tmp, text, known_keys):
    lessons = os.path.join(tmp, "lessons.md")
    known = os.path.join(tmp, "known.txt")
    with open(lessons, "w", encoding="utf-8") as fh:
        fh.write(text)
    with open(known, "w", encoding="utf-8") as fh:
        fh.write("# known\n")
        for k in known_keys:
            fh.write(k + "\n")
    p = subprocess.run(
        [sys.executable, os.path.join(HERE, "lesson_dupe.py"), lessons,
         "--gate", "--known", known],
        capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


BASE_KEYS = ["bridge-tunnel-retry-once", "bridge-tunnel-drop-verify",
             "memory-cap-rejects", "git-status-before-narrating",
             "skill-description-cap", "onedrive-mount-read-lag"]

NEW = "bridge-tunnel-retry-window"


def main():
    expect_broken = "--expect-broken" in sys.argv
    with tempfile.TemporaryDirectory() as tmp:

        # 1  THE DEFECT. Two Distinct-from lines, one per above-floor
        #    neighbour. Only the first is visible through `fields`, so the
        #    unpatched gate blocks on a neighbour that WAS addressed.
        two_lines = entry(
            NEW, TWIN_TITLE, TWIN_A, TWIN_A,
            TWIN_A, TWIN_A,
            "- **Distinct-from:** bridge-tunnel-retry-once - that one is about "
            "how many times, this is about how long to wait\n"
            "- **Distinct-from:** bridge-tunnel-drop-verify - that one is "
            "about verifying a write, this is about the wait")
        rc, out = run_gate(tmp, corpus(two_lines), BASE_KEYS)
        c1 = record("second Distinct-from line disposes its neighbour",
                    rc == 0 and "LESSON_DUPE: CLEAN" in out,
                    "rc=%d %s" % (rc, [l for l in out.splitlines()
                                       if "BLOCKED" in l]))

        # 2  REGRESSION CONTROL. Both neighbours named on a SINGLE line - the
        #    shape that already worked before the fix. It must still pass, on
        #    the old code and the new, or the fix has broken the common case.
        one_line = entry(
            NEW, TWIN_TITLE, TWIN_A, TWIN_A,
            TWIN_A, TWIN_A,
            "- **Distinct-from:** bridge-tunnel-retry-once and "
            "bridge-tunnel-drop-verify - both differ in mechanism")
        rc, out = run_gate(tmp, corpus(one_line), BASE_KEYS)
        record("regression control: one line naming both -> CLEAN", rc == 0,
               "rc=%d" % rc)

        # 3  THE CHECK MUST STILL SAY NO. No Distinct-from at all -> blocked.
        none_line = entry(NEW, TWIN_TITLE,
                          TWIN_A, TWIN_A, TWIN_A, TWIN_A)
        rc, out = run_gate(tmp, corpus(none_line), BASE_KEYS)
        record("no Distinct-from still BLOCKS", rc == 1 and "BLOCKED" in out,
               "rc=%d" % rc)

        # 4  PREFIX HAZARD. A line naming only the LONGER key must not
        #    silently dispose of a shorter key that is its prefix.
        sys.path.insert(0, HERE)
        import lesson_dupe
        # Carries BOTH shapes so the case is readable by the old field-based
        # implementation and the new body-based one, and the difference in
        # verdict is the fix rather than a missing key.
        e = {"body": "- **Distinct-from:** bridge-tunnel-drop-verify - x\n",
             "fields": {"Distinct-from": "bridge-tunnel-drop-verify - x"}}
        c4 = record("a longer key does not dispose of its own prefix",
                    lesson_dupe.disposed(e, "bridge-tunnel-drop-verify")
                    and not lesson_dupe.disposed(e, "bridge-tunnel"),
                    "prefix matched")

        # 5  Unrelated key is not disposed.
        record("an unnamed key is not disposed",
               not lesson_dupe.disposed(e, "memory-cap-rejects"))

    bad = [n for n, ok, _ in RESULTS if not ok]
    print("\n%d/%d passed" % (len(RESULTS) - len(bad), len(RESULTS)))

    if expect_broken:
        # The negative control, asserted rather than asserted-about: on the
        # unpatched script cases 1 and 4 are exactly the ones that must fail.
        ok = (not c1) and (not c4)
        print("negative control (expect 1 and 4 to FAIL): %s"
              % ("as expected" if ok else "NOT REPRODUCED"))
        return 0 if ok else 1

    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
