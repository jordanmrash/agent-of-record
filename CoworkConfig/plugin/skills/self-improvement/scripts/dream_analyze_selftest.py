#!/usr/bin/env python3
"""
dream_analyze_selftest.py - prove every detector fires, and prove the script
cannot write.

The read-only guarantee is the ONLY thing making an unattended 2am run safe.
It is therefore tested first and hardest: every input file is hashed before and
after a full run and must be byte-identical, and the directory listing must not
gain or lose a file. If that case ever fails, the nightly job must be disabled
before anything else is investigated.

Every other case sabotages exactly one thing and asserts the matching detector
reports it. A detector that has never been seen firing is decoration.

Run:  python dream_analyze_selftest.py
Exit: 0 all cases passed, 1 otherwise
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "dream_analyze.py")
APPROVED = os.path.join(HERE, "analyser.approved")

BASE = """# Lessons

### A bridge probe is a timestamp
- **Pattern-Key:** bridge-probe-is-a-timestamp
- **Date:** 2026-08-28
- **Hits:** 2
- **Rule:** Re-probe later before calling a bridge down.
- **Worked:** waited and probed again.

### Stage and commit at close
- **Pattern-Key:** git-commit-before-close
- **Date:** 2026-08-24
- **Hits:** 1
- **Rule:** Stage and commit at session close.
- **Worked:** ran the bookend.

### Keep a memory short
- **Pattern-Key:** memory-512-cap
- **Date:** 2026-08-20
- **Hits:** 1
- **Rule:** Keep a memory under 512 characters and read the success field.
- **Worked:** shortened it.
"""

INSTRUCTIONS = """# Instructions

Some preamble.

<!-- LESSON-DIGEST:BEGIN - generated -->
### Rules already paid for
- Re-probe later before calling a bridge down.
<!-- LESSON-DIGEST:END - 3 rules from 3 entries -->
"""

results = []


def record(name, ok, detail=""):
    results.append((name, ok))
    print("%-56s %s%s" % (name, "PASS" if ok else "FAIL",
                          "" if ok else "  <- " + str(detail)[:200]))


def build(tmp, lessons=BASE, instructions=INSTRUCTIONS, memory=True):
    lp = os.path.join(tmp, "cowork-lessons.md")
    ip = os.path.join(tmp, "copilot-instructions.md")
    open(lp, "w", encoding="utf-8").write(lessons)
    open(ip, "w", encoding="utf-8").write(instructions)
    md = os.path.join(tmp, "cowork-memory")
    if memory:
        os.makedirs(md, exist_ok=True)
        open(os.path.join(md, "MEMORY-INDEX.md"), "w", encoding="utf-8").write(
            "# Index\n\n- cowork-bridge-infrastructure.md - bridges\n")
        open(os.path.join(md, "cowork-bridge-infrastructure.md"), "w",
             encoding="utf-8").write("# Bridges\n")
    return lp, ip, md


def run(tmp, *args):
    return subprocess.run([sys.executable, SCRIPT] + list(args),
                          cwd=tmp, capture_output=True, text=True)


def digest_tree(root):
    """hash of (relative path -> content hash) for the whole tree"""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for f in sorted(filenames):
            p = os.path.join(dirpath, f)
            h = hashlib.sha256(open(p, "rb").read()).hexdigest()
            out.append((os.path.relpath(p, root), h))
    return out


def case_read_only():
    """THE safety case. If this fails, disable the nightly job."""
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp)
        before = digest_tree(tmp)
        r = run(tmp, "--lessons", lp, "--instructions", ip, "--memory-dir", md)
        after = digest_tree(tmp)
        record("READ-ONLY: no file added, removed or modified",
               before == after,
               "before=%d files after=%d files" % (len(before), len(after)))
        record("READ-ONLY: run completed successfully", r.returncode == 0,
               r.stderr)


def case_reachability():
    lessons = BASE.replace("- **Rule:** Stage and commit at session close.\n", "")
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp, lessons=lessons)
        r = run(tmp, "--lessons", lp, "--instructions", ip)
        record("REACHABILITY reports an inert entry",
               "inert" in r.stdout and "REACHABILITY" in r.stdout, r.stdout[:200])


def case_repeat_offender_no_rule():
    lessons = BASE + """
### Tunnel drops misread as bridge failure
- **Pattern-Key:** bridge-tunnel-drop-misread
- **Date:** 2026-08-21
- **Hits:** 3
- **Worked:** measured the local leg separately.
"""
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp, lessons=lessons)
        r = run(tmp, "--lessons", lp, "--instructions", ip)
        record("REPEAT OFFENDER with no Rule is named",
               "bridge-tunnel-drop-misread" in r.stdout
               and "REPEAT OFFENDERS" in r.stdout, r.stdout[:300])


def case_duplicates_fire():
    lessons = BASE + """
### Re-probe before declaring a bridge down
- **Pattern-Key:** bridge-declared-down-too-early
- **Date:** 2026-08-29
- **Hits:** 1
- **Rule:** Re-probe later before calling a bridge down.
- **Worked:** waited and probed again.
"""
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp, lessons=lessons)
        r = run(tmp, "--lessons", lp, "--instructions", ip)
        record("DUPLICATES detects an identical Rule",
               "bridge-declared-down-too-early" in r.stdout
               and "DUPLICATES" in r.stdout, r.stdout[:400])
        record("DUPLICATES proposes the combined Hits count",
               "Hits to 3" in r.stdout, r.stdout[:600])


def case_duplicates_negative_control():
    """Unrelated entries must NOT be reported - or the section is noise."""
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp)
        r = run(tmp, "--lessons", lp, "--instructions", ip)
        idx = r.stdout.find("DUPLICATES")
        nxt = r.stdout.find("RETIREMENT CANDIDATES")
        body = r.stdout[idx:nxt]
        record("DUPLICATES stays silent on unrelated entries",
               "none at or above" in body, body[:300])


def case_promoted_pair_not_reported():
    """An already-merged pair must not be re-proposed every night."""
    lessons = BASE + """
### Re-probe before declaring a bridge down
- **Pattern-Key:** bridge-declared-down-too-early
- **Date:** 2026-08-29
- **Hits:** 1
- **Rule:** Re-probe later before calling a bridge down.
- **Promoted-to:** bridge-probe-is-a-timestamp
- **Worked:** waited and probed again.
"""
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp, lessons=lessons)
        r = run(tmp, "--lessons", lp, "--instructions", ip)
        idx = r.stdout.find("DUPLICATES")
        nxt = r.stdout.find("RETIREMENT CANDIDATES")
        body = r.stdout[idx:nxt]
        record("DUPLICATES skips a pair already marked Promoted-to",
               "none at or above" in body, body[:300])


def _wide_corpus():
    """21 entries with genuinely disjoint wording -> 210 pairs.

    Purpose: get ABOVE MIN_PAIRS so the PERCENTILE branch is the one under
    test. With fewer pairs duplicate_floor() falls back to the absolute floor
    and the percentile path is never exercised - the hole this case closes.

    The first attempt at this fixture generated titles programmatically with a
    padding string and words sharing an "-ation" suffix. difflib is character
    based, so "Elimination xxxxxx" scored 0.7692 against "Reconciliation
    xxxxxx" and the corpus was not unrelated at all - p99.5 came out at 0.7222
    and the case failed. Hand-written disjoint sentences, no shared padding,
    no shared suffixes. If this case ever fails, suspect the fixture before
    the analyser.
    """
    lines = [
        ("Confirm printer tray size before queueing a long job", "tray-size-before-queue"),
        ("Never trust a cached exchange rate older than one hour", "stale-fx-rate"),
        ("Photograph the serial plate while the unit is still open", "serial-plate-photo"),
        ("Warm the sensor for ninety seconds or readings drift low", "sensor-warmup-drift"),
        ("Label every archive box with its destruction date", "archive-box-label"),
        ("Two people must witness a vault opening, always", "vault-two-witness"),
        ("Check tyre pressure when the rubber is cold, not hot", "tyre-cold-pressure"),
        ("A soldering iron left face down burns through the mat", "iron-face-down"),
        ("Rotate backup tapes each Friday and log the barcode", "tape-rotation-day"),
        ("Measure twice against the datum edge, then cut", "datum-edge-measure"),
        ("Salt the walkway before the frost, not after", "walkway-salt-timing"),
        ("Log the kilowatt reading at the meter, not the panel", "kilowatt-at-meter"),
        ("Quarantine any parcel whose seal is broken on arrival", "broken-seal-parcel"),
        ("Feed the starter culture at the same hour each day", "culture-feed-hour"),
        ("Bleed the radiator from the highest room downward", "radiator-bleed-order"),
        ("Prime the pump with clean water or the impeller scores", "pump-prime-water"),
        ("Ship lithium cells at thirty percent charge", "lithium-ship-charge"),
        ("Anneal the glass slowly or it shatters on the bench", "glass-anneal-slow"),
        ("Weigh reagent only on a levelled granite slab", "reagent-level-bench"),
        ("Trim the wick to six millimetres before each burn", "wick-trim-length"),
        ("Stack the timber with spacers so air moves through it", "timber-stack-spacers"),
    ]
    out = ["# Lessons\n"]
    for n, (text, key) in enumerate(lines):
        out.append(
            "### %s\n"
            "- **Pattern-Key:** %s\n"
            "- **Date:** 2026-08-%02d\n"
            "- **Hits:** 1\n"
            "- **Rule:** %s.\n"
            "- **Worked:** did exactly that.\n" % (text, key, (n % 27) + 1, text))
    return "\n".join(out)


def case_duplicates_reports_observed_max():
    """The number that would have exposed the dead 0.72 floor must always print.

    The old empty branch printed only "none at or above 0.72". The highest
    score actually observed was never shown beside it, so a floor above the
    corpus ceiling was indistinguishable from a genuinely clean corpus.
    """
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp)
        r = run(tmp, "--lessons", lp, "--instructions", ip)
        idx = r.stdout.find("DUPLICATES")
        nxt = r.stdout.find("RETIREMENT CANDIDATES")
        body = r.stdout[idx:nxt]
        record("DUPLICATES prints MAX OBSERVED even when reporting none",
               "MAX OBSERVED" in body and "none at or above" in body,
               body[:400])


def case_duplicates_unreachable_floor_warns():
    """A floor above the corpus ceiling must announce itself, not read as clean.

    This is the 2026-08-31 defect reproduced deliberately: a fixed floor no
    pair can reach. Before this case, that state printed the same words as a
    real clean result.
    """
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp)
        r = run(tmp, "--lessons", lp, "--instructions", ip, "--similarity", "0.99")
        idx = r.stdout.find("DUPLICATES")
        nxt = r.stdout.find("RETIREMENT CANDIDATES")
        body = r.stdout[idx:nxt]
        record("DUPLICATES warns when the floor is above every observed score",
               "WARNING" in body and "could not have reported a finding" in body,
               body[:400])


def case_duplicates_percentile_cannot_manufacture_a_finding():
    """THE CHECK MUST STILL BE ABLE TO SAY NO.

    A percentile over all pairs is a fixed-COUNT selector: p99.5 flags the top
    0.5% of pairs however unrelated they are. Swapping 0.72 for a bare
    percentile would replace "never fires" with "always fires" - the same
    defect wearing the opposite sign.

    This corpus is large enough that the percentile branch is live (>= 200
    pairs) and its entries share no vocabulary, so a correct implementation
    reports nothing.
    """
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp, lessons=_wide_corpus())
        r = run(tmp, "--lessons", lp, "--instructions", ip)
        idx = r.stdout.find("DUPLICATES")
        nxt = r.stdout.find("RETIREMENT CANDIDATES")
        body = r.stdout[idx:nxt]
        enough_pairs = False
        for line in body.splitlines():
            if "pairs" in line and "MAX OBSERVED" in line:
                enough_pairs = int(line.split()[0]) >= 200
        record("DUPLICATES exercises the percentile path (>=200 pairs)",
               enough_pairs, body[:400])
        record("DUPLICATES still says none on an unrelated corpus",
               "none at or above" in body, body[:400])


def case_superseded():
    lessons = BASE + """
### The old theory about the executor
- **Pattern-Key:** bridge-old-theory
- **Date:** 2026-08-18
- **Hits:** 1
- **Rule:** SUPERSEDED - the stdout pipe theory was disproven.
- **Worked:** measured it again.
"""
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp, lessons=lessons)
        r = run(tmp, "--lessons", lp, "--instructions", ip)
        body = r.stdout.split("RETIREMENT CANDIDATES")[1]
        record("RETIREMENT flags an entry carrying a SHOUTED marker",
               "bridge-old-theory" in body, body[:400])


def case_fixed_but_live_rule():
    lessons = BASE + """
### The close job could not fail
- **Pattern-Key:** git-close-could-not-fail
- **Date:** 2026-08-29
- **Hits:** 1
- **Rule:** Do not trust the close job to report a commit.
- **Fixed:** 2026-08-30 every exit code is now tested.
- **Worked:** rewrote it.
"""
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp, lessons=lessons)
        r = run(tmp, "--lessons", lp, "--instructions", ip)
        record("FIXED entries that still carry a live Rule are surfaced",
               "FIXED BUT STILL CARRYING A LIVE RULE" in r.stdout
               and "git-close-could-not-fail" in r.stdout, r.stdout[-900:])


def case_lowercase_prose_is_not_a_marker():
    """THE control this detector shipped without, and immediately needed.

    First version matched against body.upper(), so ordinary prose - 'the
    theory turned out wrong', 'corrected the memory' - matched the marker
    WRONG and the section flagged 40 of 87 real entries. A warning that is
    always on is training to skip warnings.
    """
    lessons = BASE + """
### An entry whose prose merely uses the words
- **Pattern-Key:** bridge-prose-only-mention
- **Date:** 2026-08-30
- **Hits:** 1
- **Rule:** Read the actual state before describing it.
- **Why:** the earlier guess turned out wrong and was corrected later, and the
  old note is no longer accurate, but nothing here is retired.
- **Worked:** re-read it.
"""
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp, lessons=lessons)
        r = run(tmp, "--lessons", lp, "--instructions", ip)
        body = r.stdout.split("RETIREMENT CANDIDATES")[1].split("STILL OPEN")[0]
        record("lowercase 'wrong'/'corrected' in prose is NOT a marker",
               "bridge-prose-only-mention" not in body, body[:400])


def case_relative_date_flagged():
    lessons = BASE + """
### Something that happened on an unnameable day
- **Pattern-Key:** bridge-relative-anchor
- **Date:** 2026-08-30
- **Hits:** 1
- **Rule:** Anchor a claim to a date.
- **Why:** yesterday the probe returned a different answer, so the note is
  no longer resolvable.
- **Worked:** n/a
"""
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp, lessons=lessons)
        r = run(tmp, "--lessons", lp, "--instructions", ip)
        body = r.stdout.split("RELATIVE DATES")[1].split("STILL OPEN")[0]
        record("RELATIVE DATES flags 'yesterday'",
               "bridge-relative-anchor" in body, body[:400])
        record("RELATIVE DATES offers the entry's own Date as the fix",
               "resolve to 2026-08-30" in body, body[:400])


def case_relative_date_negative_controls():
    """The control the retirement detector shipped WITHOUT and needed.

    Measured on the real corpus: a broad relative-time pattern hit 43 times
    and 40 were durable usages. 'now' means 'in the current version',
    'earlier' means 'earlier in the file', and 'this session' mostly appears
    inside quoted advice. Flagging those makes the section unreadable.
    """
    lessons = BASE + """
### Durable phrasing that must NOT be flagged
- **Pattern-Key:** bridge-durable-phrasing
- **Date:** 2026-08-30
- **Hits:** 1
- **Rule:** The job now tests every exit code.
- **Why:** as noted earlier in this file, the checker is now correct, and
  the advice to say "not on the surface as of now" rather than "down this
  session" still holds.
- **Worked:** n/a
"""
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp, lessons=lessons)
        r = run(tmp, "--lessons", lp, "--instructions", ip)
        body = r.stdout.split("RELATIVE DATES")[1].split("STILL OPEN")[0]
        record("'now' / 'earlier' / 'this session' are NOT flagged",
               "bridge-durable-phrasing" not in body, body[:400])


def case_relative_date_no_date_field():
    lessons = BASE + """
### An anchor with no Date to resolve against
- **Pattern-Key:** bridge-anchor-no-date
- **Hits:** 1
- **Rule:** Anchor a claim to a date.
- **Why:** today the probe answered differently.
- **Worked:** n/a
"""
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp, lessons=lessons)
        r = run(tmp, "--lessons", lp, "--instructions", ip)
        record("an anchor with no Date field says so rather than inventing one",
               "cannot be resolved at all" in r.stdout, r.stdout[-700:])


def case_still_open():
    lessons = BASE + """
### Archive the spent one-offs
- **Pattern-Key:** git-archive-oneoffs
- **Date:** 2026-08-30
- **Hits:** 1
- **Rule:** Archive spent one-off jobs.
- **Still open:** 80 one-off .bat files are still in CommandJobs.
- **Worked:** nothing yet.
"""
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp, lessons=lessons)
        r = run(tmp, "--lessons", lp, "--instructions", ip)
        record("STILL OPEN surfaces unfinished work",
               "git-archive-oneoffs" in r.stdout.split("STILL OPEN")[1],
               r.stdout[-600:])


def case_pointer_missing_from_index():
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp)
        open(os.path.join(md, "cowork-orphan-file.md"), "w",
             encoding="utf-8").write("# Orphan\n")
        r = run(tmp, "--lessons", lp, "--instructions", ip, "--memory-dir", md)
        record("POINTERS catches a deep file missing from the index",
               "NOT IN INDEX: cowork-orphan-file.md" in r.stdout,
               r.stdout[-600:])


def case_pointer_dangling():
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp)
        open(os.path.join(md, "MEMORY-INDEX.md"), "a",
             encoding="utf-8").write("- cowork-does-not-exist.md - ghost\n")
        r = run(tmp, "--lessons", lp, "--instructions", ip, "--memory-dir", md)
        record("POINTERS catches an index entry with no file",
               "MISSING FILE: cowork-does-not-exist.md" in r.stdout,
               r.stdout[-600:])


def case_strict_exit():
    lessons = BASE + """
### Tunnel drops misread
- **Pattern-Key:** bridge-tunnel-drop-misread
- **Date:** 2026-08-21
- **Hits:** 3
- **Worked:** measured it.
"""
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp, lessons=lessons)
        r = run(tmp, "--lessons", lp, "--instructions", ip, "--strict")
        record("--strict exits 1 when there are findings", r.returncode == 1,
               r.returncode)
        r2 = run(tmp, "--lessons", lp, "--instructions", ip)
        record("without --strict the same input exits 0", r2.returncode == 0,
               r2.returncode)


def case_unreadable():
    with tempfile.TemporaryDirectory() as tmp:
        r = run(tmp, "--lessons", os.path.join(tmp, "nope.md"))
        record("unreadable input exits 2, never 0", r.returncode == 2,
               r.returncode)


def case_empty_parse():
    with tempfile.TemporaryDirectory() as tmp:
        lp = os.path.join(tmp, "cowork-lessons.md")
        open(lp, "w", encoding="utf-8").write("# Lessons\n\nno entries here\n")
        r = run(tmp, "--lessons", lp)
        record("a file that parses to zero entries exits 2, not a clean 0",
               r.returncode == 2, r.returncode)


def _instructions_with_always_on(n):
    """An instructions file whose always-on digest block holds exactly n rules."""
    body = "\n".join("- rule number %d" % i for i in range(n))
    return ("# Instructions\n\nSome prose.\n\n"
            "<!-- LESSON-DIGEST:BEGIN - generated. Do not hand-edit. -->\n"
            + body +
            "\n<!-- LESSON-DIGEST:END -->\n\nMore prose.\n")


def _lessons_with_authored_rules(n):
    """A lessons file carrying exactly n entries that each have a Rule line."""
    out = [BASE]
    for i in range(n):
        out.append("""
### Growth fixture entry %d
- **Pattern-Key:** growthfixture-entry-%03d
- **Date:** 2026-09-03
- **Trigger:** failure
- **Rule:** fixture rule %d, present only to inflate the authored count.
- **Failed:** n/a
- **Why:** n/a
- **Worked:** n/a
- **Evidence:** measured
- **Hits:** 1
""" % (i, i, i))
    return "".join(out)


def case_growth_counts_the_block_not_the_corpus():
    """THE regression case for the defect this check shipped with.

    Until 2026-09-03 do_growth compared the count of AUTHORED Rule lines in the
    lessons file against a hardcoded 80. After the digest was tiered those are
    different populations, so the check warned about a block of 30 because the
    CORPUS held 90. Here the corpus is deliberately huge and the block small:
    a check that counts the right thing stays silent.
    """
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp,
                           lessons=_lessons_with_authored_rules(95),
                           instructions=_instructions_with_always_on(5))
        r = run(tmp, "--lessons", lp, "--instructions", ip)
        body = r.stdout[r.stdout.find("GROWTH"):]
        record("GROWTH: a large corpus with a SMALL always-on block does not warn",
               "over the --always-on-max" not in body,
               body[:400])
        # Derive the authored count from the RUN's own output rather than
        # asserting a literal: BASE already carries entries with Rule lines, so
        # a pasted number is wrong the moment the fixture changes. That is the
        # frozen-baseline defect this suite exists to catch, and the first
        # version of this case had it.
        m = re.search(r"(\d+) authored rule", body)
        authored = int(m.group(1)) if m else -1
        record("GROWTH: reports the always-on count, not the authored count",
               "5 rule(s) always-on" in body and authored >= 95,
               "always-on line present=%s authored=%d\n%s"
               % ("5 rule(s) always-on" in body, authored, body[:300]))


def case_growth_fires_on_a_large_always_on_block():
    """Positive control - the check must still be able to fire."""
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp,
                           lessons=_lessons_with_authored_rules(2),
                           instructions=_instructions_with_always_on(45))
        r = run(tmp, "--lessons", lp, "--instructions", ip)
        body = r.stdout[r.stdout.find("GROWTH"):]
        record("GROWTH: fires when the ALWAYS-ON block exceeds the max",
               "over the --always-on-max" in body, body[:400])


def case_growth_threshold_is_overridable():
    """The threshold is a judgement, so it must be settable - and settable
    BOTH ways. Raising it silences a warning; lowering it must reinstate one,
    or the flag is decoration that only ever hides findings."""
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp,
                           lessons=_lessons_with_authored_rules(2),
                           instructions=_instructions_with_always_on(45))
        raised = run(tmp, "--lessons", lp, "--instructions", ip,
                     "--always-on-max", "50")
        rb = raised.stdout[raised.stdout.find("GROWTH"):]
        record("GROWTH: raising --always-on-max silences the warning",
               "over the --always-on-max" not in rb, rb[:300])

        lowered = run(tmp, "--lessons", lp, "--instructions", ip,
                      "--always-on-max", "10")
        lb = lowered.stdout[lowered.stdout.find("GROWTH"):]
        record("GROWTH: lowering --always-on-max reinstates it",
               "over the --always-on-max" in lb, lb[:300])


def case_growth_missing_block_is_a_finding():
    """No digest block at all must not read as a small, healthy one."""
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip, md = build(tmp,
                           lessons=_lessons_with_authored_rules(2),
                           instructions="# Instructions\n\nNo digest here.\n")
        r = run(tmp, "--lessons", lp, "--instructions", ip)
        body = r.stdout[r.stdout.find("GROWTH"):]
        record("GROWTH: an absent digest block is reported, not treated as clean",
               "NO DIGEST BLOCK FOUND" in body, body[:300])


def main():
    for fn in (case_read_only, case_reachability, case_repeat_offender_no_rule,
               case_duplicates_fire, case_duplicates_negative_control,
               case_promoted_pair_not_reported,
               case_duplicates_reports_observed_max,
               case_duplicates_unreachable_floor_warns,
               case_duplicates_percentile_cannot_manufacture_a_finding,
               case_superseded,
               case_lowercase_prose_is_not_a_marker,
               case_fixed_but_live_rule,
               case_relative_date_flagged,
               case_relative_date_negative_controls,
               case_relative_date_no_date_field, case_still_open,
               case_pointer_missing_from_index, case_pointer_dangling,
               case_growth_counts_the_block_not_the_corpus,
               case_growth_fires_on_a_large_always_on_block,
               case_growth_threshold_is_overridable,
               case_growth_missing_block_is_a_finding,
               case_strict_exit, case_unreadable, case_empty_parse):
        fn()
    failed = [r for r in results if not r[1]]
    print("\n%d/%d cases passed" % (len(results) - len(failed), len(results)))

    # RELEASE GATE. The nightly run refuses to execute an analyser whose hash
    # does not match analyser.approved, which proves the analyser being run is
    # the one that passed these tests.
    #
    # The hash is written HERE, by a passing run, rather than recorded by hand.
    # A manually maintained approved-hash has a failure mode worse than the one
    # it prevents: a legitimate edit with a forgotten hash update blocks every
    # subsequent nightly run, and whoever hits that at 2am learns to disable the
    # gate. Self-updating keeps the guarantee without the footgun.
    #
    # On FAILURE the file is REMOVED, not left stale - a missing
    # analyser.approved is FAILED INTEGRITY nightly, which is the correct
    # outcome for an analyser whose tests do not pass.
    if failed:
        if os.path.exists(APPROVED):
            os.remove(APPROVED)
            print("tests failed - removed analyser.approved; "
                  "the nightly run will now refuse to execute this analyser")
        return 1

    # newline="" so the marker is LF on every platform. Without it Python's
    # text mode writes CRLF on Windows, giving a 66-byte file where the reader
    # expected 65 - measured 2026-08-30, and it made the nightly gate reject its
    # own marker as malformed. The reader also strips whitespace, so this is
    # belt and braces: the artifact is canonical AND the check is tolerant.
    digest = hashlib.sha256(open(SCRIPT, "rb").read()).hexdigest()
    with open(APPROVED, "w", encoding="utf-8", newline="") as fh:
        fh.write(digest + "\n")
    print("approved analyser sha256: %s" % digest)
    print("written to %s" % os.path.basename(APPROVED))
    return 0


if __name__ == "__main__":
    sys.exit(main())
