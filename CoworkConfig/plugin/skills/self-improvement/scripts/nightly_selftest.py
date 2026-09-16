#!/usr/bin/env python3
"""
nightly_selftest.py - break the nightly harness before trusting it.

Positive control FIRST, then negatives that each assert WHY they failed.
A checker nobody has tried to fool is an assumption.

The cases that matter most are the ones separating THREE outcomes a naive
runner collapses into two:

    CLEAN            every checker ran, nothing to report
    FINDINGS         every checker ran, something needs a human
    DID NOT RUN      a checker never executed at all

The third is the one that hurts. On an exit code alone it is identical to the
second, and that confusion produced a false "restore from backup" instruction
on 2026-08-31.

Run:  python nightly_selftest.py
Exit: 0 all cases passed, 1 otherwise
"""

import datetime
import hashlib
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MEASURE = os.path.join(HERE, "nightly_measure.py")
HEARTBEAT = os.path.join(HERE, "heartbeat_check.py")

results = []


def record(name, ok, detail=""):
    results.append((name, ok))
    print("%-58s %s%s" % (name, "PASS" if ok else "FAIL",
                          "" if ok else "  <- " + str(detail)[:250]))


LESSONS = """# Lessons

## Failures

### A bridge probe is a timestamp
- **Pattern-Key:** bridge-probe-is-a-timestamp
- **Date:** 2026-08-28
- **Trigger:** failure
- **Failed:** called it down after one drop.
- **Why:** the drop is the tunnel hop.
- **Worked:** waited and probed again.
- **Evidence:** measured
- **Hits:** 1
- **Rule:** Re-probe later before calling a bridge down.

### Stage and commit at close
- **Pattern-Key:** git-commit-before-close
- **Date:** 2026-08-24
- **Trigger:** failure
- **Failed:** left the tree dirty.
- **Why:** no bookend.
- **Worked:** ran the bookend.
- **Evidence:** measured
- **Hits:** 1
- **Rule:** Stage and commit at session close.

## Contradictions - stored memories that proved wrong

## Open questions
"""

INSTRUCTIONS = """# Instructions

<!-- LESSON-DIGEST:BEGIN - generated -->
### Rules already paid for
- Re-probe later before calling a bridge down.
- Stage and commit at session close.
<!-- LESSON-DIGEST:END - 2 rules from 2 entries -->
"""


def build(tmp):
    scripts = os.path.join(tmp, "scripts")
    os.makedirs(scripts, exist_ok=True)
    real = os.path.dirname(os.path.abspath(__file__))
    for f in ("lesson_check.py", "lesson_gate.py", "dream_analyze.py",
              "lesson_brief.py"):
        src = os.path.join(real, f)
        if os.path.isfile(src):
            with open(src, "rb") as a, open(os.path.join(scripts, f), "wb") as b:
                b.write(a.read())
    lp = os.path.join(tmp, "cowork-lessons.md")
    ip = os.path.join(tmp, "copilot-instructions.md")
    open(lp, "w", encoding="utf-8").write(LESSONS)
    open(ip, "w", encoding="utf-8").write(INSTRUCTIONS)
    md = os.path.join(tmp, "cowork-memory")
    os.makedirs(md, exist_ok=True)
    open(os.path.join(md, "MEMORY-INDEX.md"), "w", encoding="utf-8").write(
        "# Index\n\n- cowork-bridge-infrastructure.md - bridges\n")
    open(os.path.join(md, "cowork-bridge-infrastructure.md"), "w",
         encoding="utf-8").write("# Bridges\n")
    # A healthy fixture is an APPROVED fixture. Before the integrity gate
    # existed this did not matter; now an unapproved analyser is refused, and
    # leaving it out would make every unrelated case fail for the same reason -
    # which reads as the gate being broken rather than the fixture being stale.
    analyser = os.path.join(scripts, "dream_analyze.py")
    if os.path.isfile(analyser):
        h = hashlib.sha256(open(analyser, "rb").read()).hexdigest()
        with open(os.path.join(scripts, "analyser.approved"), "w",
                  encoding="utf-8", newline="") as fh:
            fh.write(h + "\n")
    out = os.path.join(tmp, "out")
    hb = os.path.join(tmp, "heartbeat.json")
    return scripts, lp, ip, md, out, hb


def measure(tmp, scripts, lp, ip, md, out, hb):
    return subprocess.run(
        [sys.executable, MEASURE, "--scripts", scripts, "--lessons", lp,
         "--instructions", ip, "--memory-dir", md, "--out-dir", out,
         "--heartbeat", hb],
        cwd=tmp, capture_output=True, text=True)


def case_positive_control():
    """A healthy corpus must exit 0 and write both artifacts."""
    with tempfile.TemporaryDirectory() as tmp:
        args = build(tmp)
        r = measure(tmp, *args)
        out, hb = args[4], args[5]
        files = os.listdir(out) if os.path.isdir(out) else []
        record("POSITIVE CONTROL: healthy corpus exits 0",
               r.returncode == 0, r.stdout[-400:] + r.stderr[-300:])
        record("POSITIVE CONTROL: writes measurements-<date>.json",
               any(f.startswith("measurements-") for f in files), files)
        record("POSITIVE CONTROL: writes the heartbeat",
               os.path.isfile(hb), hb)


def case_report_is_valid_json_with_every_step():
    with tempfile.TemporaryDirectory() as tmp:
        args = build(tmp)
        measure(tmp, *args)
        out = args[4]
        path = os.path.join(out, sorted(os.listdir(out))[0])
        data = json.load(open(path, encoding="utf-8"))
        names = [s["name"] for s in data["steps"]]
        record("report records all three checkers",
               names == ["lesson_check", "lesson_gate_audit", "dream_analyze"],
               names)
        record("report carries the duplicate ceiling actually observed",
               "dup_max_observed" in data["measurements"],
               list(data["measurements"]))


def case_missing_checker_is_did_not_run_not_a_finding():
    """THE CASE THAT MATTERS. A checker that never executed must be
    distinguishable from one that found something."""
    with tempfile.TemporaryDirectory() as tmp:
        scripts, lp, ip, md, out, hb = build(tmp)
        os.remove(os.path.join(scripts, "dream_analyze.py"))
        r = measure(tmp, scripts, lp, ip, md, out, hb)
        path = os.path.join(out, sorted(os.listdir(out))[0])
        data = json.load(open(path, encoding="utf-8"))
        record("a missing checker exits 2, NOT 1",
               r.returncode == 2, "exit=%s\n%s" % (r.returncode, r.stdout[-300:]))
        record("a missing checker is named in did_not_run",
               data["did_not_run"] == ["dream_analyze"], data["did_not_run"])
        record("verdict says HARNESS FAILURE, not findings",
               data["verdict"] == "HARNESS FAILURE", data["verdict"])


def case_real_finding_exits_1():
    """A corpus with a genuine defect must exit 1 - and the run must still
    have happened, so this is not the same as the case above."""
    with tempfile.TemporaryDirectory() as tmp:
        scripts, lp, ip, md, out, hb = build(tmp)
        # A twice-hit entry with no Rule line is a lesson_check FAIL.
        open(lp, "a", encoding="utf-8").write("""
### A repeat with no rule
- **Pattern-Key:** bridge-repeat-no-rule
- **Date:** 2026-08-30
- **Trigger:** failure
- **Failed:** did the thing twice.
- **Why:** nobody read the entry.
- **Worked:** unknown for now.
- **Evidence:** measured
- **Hits:** 2
""")
        r = measure(tmp, scripts, lp, ip, md, out, hb)
        path = os.path.join(out, sorted(os.listdir(out))[0])
        data = json.load(open(path, encoding="utf-8"))
        record("a real finding exits 1, not 2",
               r.returncode == 1, "exit=%s\n%s" % (r.returncode, r.stdout[-300:]))
        record("a real finding leaves did_not_run EMPTY",
               data["did_not_run"] == [], data["did_not_run"])


def case_heartbeat_written_even_on_failure():
    """A heartbeat proves the JOB ran. Writing it only on success would make a
    broken run look like a machine that never woke."""
    with tempfile.TemporaryDirectory() as tmp:
        scripts, lp, ip, md, out, hb = build(tmp)
        os.remove(os.path.join(scripts, "lesson_check.py"))
        r = measure(tmp, scripts, lp, ip, md, out, hb)
        record("heartbeat is written even when the harness fails",
               os.path.isfile(hb) and r.returncode == 2,
               "exit=%s hb=%s" % (r.returncode, os.path.isfile(hb)))


# ---------------------------------------------------------------------------
# THE ANALYSER INTEGRITY GATE
#
# Five cases, and the FIRST one is the positive control. A gate that refuses
# everything passes every negative test ever written, so "it fired" proves
# nothing on its own - the pass case has to be proven in the same breath.
# ---------------------------------------------------------------------------

def _approve(scripts):
    """Write a genuinely correct analyser.approved for the fixture."""
    h = hashlib.sha256(
        open(os.path.join(scripts, "dream_analyze.py"), "rb").read()).hexdigest()
    with open(os.path.join(scripts, "analyser.approved"), "w",
              encoding="utf-8", newline="") as fh:
        fh.write(h + "\n")
    return h


def _read_report(out):
    return json.load(open(os.path.join(out, sorted(os.listdir(out))[0]),
                          encoding="utf-8"))


def case_integrity_positive_control():
    """A VALID marker must let the analyser run. Proven before any refusal."""
    with tempfile.TemporaryDirectory() as tmp:
        scripts, lp, ip, md, out, hb = build(tmp)
        _approve(scripts)
        r = measure(tmp, scripts, lp, ip, md, out, hb)
        data = _read_report(out)
        record("INTEGRITY positive control: valid marker -> analyser RUNS",
               data["analyser_integrity"] == "OK" and data["analysis_ran"] is True,
               "%s / %s" % (data["analyser_integrity"], data["analysis_ran"]))
        record("INTEGRITY positive control: exit is not 3",
               r.returncode != 3, "exit=%s" % r.returncode)


def case_integrity_missing_marker():
    """A missing marker is what a FAILED selftest leaves behind."""
    with tempfile.TemporaryDirectory() as tmp:
        scripts, lp, ip, md, out, hb = build(tmp)
        mk = os.path.join(scripts, "analyser.approved")
        if os.path.exists(mk):
            os.remove(mk)
        r = measure(tmp, scripts, lp, ip, md, out, hb)
        data = _read_report(out)
        record("INTEGRITY missing marker -> exit 3, not 2",
               r.returncode == 3, "exit=%s" % r.returncode)
        record("INTEGRITY missing marker -> state MISSING",
               data["analyser_integrity"] == "MISSING", data["analyser_integrity"])
        record("INTEGRITY missing marker -> analyser did NOT run",
               data["analysis_ran"] is False, data["analysis_ran"])


def case_integrity_malformed_marker():
    """Uppercase hex, wrong length and junk must all be refused."""
    bad = {"uppercase": "A" * 64, "short": "abc123", "junk": "not a hash at all",
           "too_long": "a" * 65}
    for label, content in bad.items():
        with tempfile.TemporaryDirectory() as tmp:
            scripts, lp, ip, md, out, hb = build(tmp)
            with open(os.path.join(scripts, "analyser.approved"), "w",
                      encoding="utf-8") as fh:
                fh.write(content)
            r = measure(tmp, scripts, lp, ip, md, out, hb)
            data = _read_report(out)
            record("INTEGRITY malformed marker (%s) -> MALFORMED, exit 3" % label,
                   r.returncode == 3 and data["analyser_integrity"] == "MALFORMED",
                   "exit=%s state=%s" % (r.returncode, data["analyser_integrity"]))


def case_integrity_crlf_marker_is_accepted():
    """TOLERANT ABOUT WHITESPACE, STRICT ABOUT CONTENT.

    Measured 2026-08-30: the selftest wrote the marker in text mode on Windows,
    producing CRLF, and a byte-length check rejected a valid marker. Strip
    first. This case exists so that fix cannot be undone silently.
    """
    with tempfile.TemporaryDirectory() as tmp:
        scripts, lp, ip, md, out, hb = build(tmp)
        h = hashlib.sha256(
            open(os.path.join(scripts, "dream_analyze.py"), "rb").read()).hexdigest()
        with open(os.path.join(scripts, "analyser.approved"), "wb") as fh:
            fh.write((h + "\r\n").encode("ascii"))
        r = measure(tmp, scripts, lp, ip, md, out, hb)
        data = _read_report(out)
        record("INTEGRITY a CRLF marker is still ACCEPTED",
               data["analyser_integrity"] == "OK",
               "%s (exit %s)" % (data["analyser_integrity"], r.returncode))


def case_integrity_mismatch_after_edit():
    """Editing the analyser after approval must be caught."""
    with tempfile.TemporaryDirectory() as tmp:
        scripts, lp, ip, md, out, hb = build(tmp)
        _approve(scripts)
        with open(os.path.join(scripts, "dream_analyze.py"), "a",
                  encoding="utf-8") as fh:
            fh.write("\n# an edit made after approval\n")
        r = measure(tmp, scripts, lp, ip, md, out, hb)
        data = _read_report(out)
        record("INTEGRITY edited analyser -> MISMATCH, exit 3",
               r.returncode == 3 and data["analyser_integrity"] == "MISMATCH",
               "exit=%s state=%s" % (r.returncode, data["analyser_integrity"]))


def case_integrity_findings_are_null_never_zero():
    """THE CASE THAT MATTERS MOST.

    "0 findings" and "findings not measured" are opposite claims. A skipped
    analyser that reports 0 reads, next morning, as a clean night.
    """
    with tempfile.TemporaryDirectory() as tmp:
        scripts, lp, ip, md, out, hb = build(tmp)
        mk = os.path.join(scripts, "analyser.approved")
        if os.path.exists(mk):
            os.remove(mk)
        measure(tmp, scripts, lp, ip, md, out, hb)
        data = _read_report(out)
        m = data["measurements"]
        record("INTEGRITY skipped analyser -> findings is NULL, not 0",
               m["findings"] is None, repr(m["findings"]))
        record("INTEGRITY skipped analyser -> duplicate figures are NULL too",
               m["dup_max_observed"] is None and m["dup_pairs"] is None,
               "%r / %r" % (m["dup_max_observed"], m["dup_pairs"]))
        # The case that used to sit here asserted proposals_emitted == 0. It
        # could not fail: the field was a literal 0 on every path, so it passed
        # whether or not it carried meaning - a check scoped away from the risk
        # it named. Schema 3 removes the field because `findings` already counts
        # the proposals; this case now fails if it is ever reintroduced.
        record("proposals_emitted is GONE, not reported as a constant zero",
               "proposals_emitted" not in data, sorted(data.keys()))
        record("schema_version reports 3",
               data.get("schema_version") == 3, data.get("schema_version"))
        record("INTEGRITY skipped analyser -> heartbeat still written",
               os.path.isfile(hb), hb)


def hbcheck(path, hours=None):
    argv = [sys.executable, HEARTBEAT, "--heartbeat", path]
    if hours is not None:
        argv += ["--max-age-hours", str(hours)]
    return subprocess.run(argv, capture_output=True, text=True)


def write_hb(path, age_hours):
    when = (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(hours=age_hours))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"schema_version": 2,
                   "last_run_utc": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "verdict": "CLEAN", "exit_code": 0}, fh)


def case_heartbeat_fresh_passes():
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "hb.json")
        write_hb(p, 1.0)
        r = hbcheck(p)
        record("HEARTBEAT: a fresh heartbeat exits 0",
               r.returncode == 0 and "HEARTBEAT OK" in r.stdout, r.stdout)


def case_heartbeat_stale_fires():
    """NEGATIVE CONTROL: the dead-man's switch must be able to fire."""
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "hb.json")
        write_hb(p, 40.0)
        r = hbcheck(p)
        record("HEARTBEAT: a 40h-old heartbeat exits 1",
               r.returncode == 1 and "STALE" in r.stdout, r.stdout)


def case_heartbeat_missing_fires():
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "nope.json")
        r = hbcheck(p)
        record("HEARTBEAT: a missing heartbeat exits 1",
               r.returncode == 1 and "MISSING" in r.stdout, r.stdout)


def case_heartbeat_corrupt_fires():
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "hb.json")
        open(p, "w", encoding="utf-8").write("{not json")
        r = hbcheck(p)
        record("HEARTBEAT: an unreadable heartbeat exits 1",
               r.returncode == 1 and "UNREADABLE" in r.stdout, r.stdout)


def case_heartbeat_always_prints_the_age():
    """The observed value must print on BOTH branches, so a threshold that is
    never in reach cannot masquerade as a clean result."""
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "hb.json")
        write_hb(p, 1.0)
        fresh = hbcheck(p)
        write_hb(p, 40.0)
        stale = hbcheck(p)
        record("HEARTBEAT: prints observed age on the clean branch",
               "age" in fresh.stdout and "threshold" in fresh.stdout,
               fresh.stdout)
        record("HEARTBEAT: prints observed age on the failing branch",
               "age" in stale.stdout and "threshold" in stale.stdout,
               stale.stdout)


def main():
    for fn in (case_positive_control,
               case_report_is_valid_json_with_every_step,
               case_missing_checker_is_did_not_run_not_a_finding,
               case_real_finding_exits_1,
               case_heartbeat_written_even_on_failure,
               case_integrity_positive_control,
               case_integrity_missing_marker,
               case_integrity_malformed_marker,
               case_integrity_crlf_marker_is_accepted,
               case_integrity_mismatch_after_edit,
               case_integrity_findings_are_null_never_zero,
               case_heartbeat_fresh_passes,
               case_heartbeat_stale_fires,
               case_heartbeat_missing_fires,
               case_heartbeat_corrupt_fires,
               case_heartbeat_always_prints_the_age):
        fn()
    failed = [r for r in results if not r[1]]
    print("\n%d/%d cases passed" % (len(results) - len(failed), len(results)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
