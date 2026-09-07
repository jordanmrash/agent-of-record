#!/usr/bin/env python3
"""
nightly_measure.py - the half of the dream cycle that needs no LLM.

WHY THIS EXISTS
---------------
Measured 2026-08-31: a hosted scheduler reported SUCCESS four times while one
of those runs produced nothing for 5h 43m. The "success" described the TRIGGER
firing, not the work happening. A trigger that fires into a dormant session is
indistinguishable, from the scheduler's side, from one that did the job.

So the measured half is moved onto the machine, where an exit code means the
work ran. lesson_check.py, lesson_gate.py audit and dream_analyze.py are all
plain Python over local files - no model, no network, no approval. They run at
02:00 whether or not anybody is logged on, write one JSON file, and stop.

The JUDGING half - deciding what to merge, retire or rewrite - stays with
Jordan in the morning. This script never proposes and never edits.

WHAT IT REFUSES TO CONFUSE
--------------------------
Three different outcomes that a naive runner collapses into one:

  exit 0  every checker RAN and reported nothing that needs a human
  exit 1  every checker RAN and at least one has a FINDING for the morning
  exit 2  a checker did NOT RUN - usage error, missing file, bad interpreter
  exit 3  a guard REFUSED to run the analyser - failed integrity

2 and 3 are both "do not trust the numbers", and they are still kept apart.
2 is an ACCIDENT: something broke that nobody chose. 3 is a DECISION: a guard
looked at the analyser, did not recognise it, and declined. Reporting a
deliberate refusal as a breakage sends the next person hunting for a fault
that does not exist, which is the same confusion as exit 1 versus exit 2 one
level up.

2 is the subtle one. A checker that never executed exits non-zero just like a
checker that found a problem, and on that signal alone they are identical.
Every step therefore asserts a marker string that only appears in real output;
a checker whose marker is missing is reported as DID NOT RUN, whatever its exit
code was. See lesson verifier-usage-error-reads-as-finding.

THE INTEGRITY GATE, AND WHAT IT REFUSES TO CONFLATE
---------------------------------------------------
`dream_analyze.py` is only trustworthy if it is the build that passed
`dream_analyze_selftest.py`, which writes the approved SHA-256 to
`analyser.approved` on a pass and REMOVES it on a failure. Until now this job
ran the analyser without ever reading that marker - the deploy gate existed and
the nightly consumer ignored it, so a failed selftest would have deleted the
marker and the nightly would have carried on regardless.

On any integrity failure the analyser is NOT RUN, and every figure derived from
it is recorded as null - NEVER as zero. "0 findings" and "findings not measured"
are opposite claims that a naive encoding renders identically, and the first one
reads as a clean night.

Checkers are invoked as argument lists through subprocess - never a shell
pipeline. A pipe reports the pipe's exit status, not the checker's, which
returned a false clean twice on 2026-08-29.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

SCHEMA_VERSION = 3


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def run_checker(name, argv, marker, cwd):
    """Run one checker bare. Returns a step dict; never raises."""
    started = utc_now()
    step = {
        "name": name,
        "argv": [os.path.basename(argv[1]) if len(argv) > 1 else argv[0]] + argv[2:],
        "started_at": stamp(started),
    }
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                           timeout=600)
        out, err, code = p.stdout, p.stderr, p.returncode
    except Exception as exc:                      # noqa: BLE001 - reported, not raised
        step.update({"ran": False, "exit": None, "error": str(exc)[:300],
                     "verdict": "DID NOT RUN"})
        return step, "", ""

    ran = marker in out
    step.update({
        "ran": ran,
        "exit": code,
        "elapsed_s": round((utc_now() - started).total_seconds(), 2),
        "stdout_bytes": len(out),
        "stderr_first_line": (err.strip().splitlines() or [""])[0][:200],
    })
    if not ran:
        # The marker is the proof of execution. Without it the exit code is
        # unreadable: argparse's 2 and a genuine finding's 1 look the same.
        step["verdict"] = "DID NOT RUN"
        step["expected_marker"] = marker
    elif code == 0:
        step["verdict"] = "CLEAN"
    else:
        step["verdict"] = "FINDINGS"
    return step, out, err


APPROVED_RE = re.compile(r"^[0-9a-f]{64}$")


def check_analyser_integrity(scripts_dir):
    """Is dream_analyze.py the build that passed its selftest?

    Returns (ok, state, detail). state is one of OK / MISSING / MALFORMED /
    MISMATCH - distinct because they need distinct responses: MISSING and
    MISMATCH mean "run the selftest", MALFORMED means "the marker file itself
    is damaged".

    STRIP-THEN-MATCH, never a literal byte comparison. Measured 2026-08-30: the
    selftest wrote the marker in Python text mode on Windows, producing CRLF and
    a 66-byte file where a reader expecting 65 rejected its own valid marker.
    Stripping first makes the check tolerant of LF, CRLF or no trailing newline
    while still requiring exactly 64 lowercase hex characters - tolerant about
    whitespace, strict about content.
    """
    analyser = os.path.join(scripts_dir, "dream_analyze.py")
    marker = os.path.join(scripts_dir, "analyser.approved")

    # Callers must not reach here with the analyser absent - see main(). An
    # absent analyser is a broken deployment, not a guard declining to trust
    # something, and routing it here would report a DECISION where there was
    # only an ACCIDENT.
    if not os.path.isfile(marker):
        return False, "MISSING", (
            "analyser.approved is absent. The selftest REMOVES it on failure, so "
            "this is what a failed analyser looks like - run "
            "dream_analyze_selftest.py and read the result.")

    with open(marker, encoding="utf-8") as fh:
        claimed = fh.read().strip()
    if not APPROVED_RE.match(claimed):
        return False, "MALFORMED", (
            "analyser.approved does not hold exactly 64 lowercase hex characters "
            "after stripping (got %d chars)." % len(claimed))

    actual = hashlib.sha256(open(analyser, "rb").read()).hexdigest()
    if actual != claimed:
        return False, "MISMATCH", (
            "dream_analyze.py hashes to %s but analyser.approved holds %s. The "
            "analyser has been edited since it was approved." % (actual, claimed))
    return True, "OK", actual


def num(pattern, text, cast=int, default=None):
    # re.M matters: the floor line is anchored with ^ and without it the value
    # silently came back None on the first real run, which would have written a
    # null into the measurement record and read as "not measured".
    m = re.search(pattern, text, re.M)
    if not m:
        return default
    try:
        return cast(m.group(1))
    except (TypeError, ValueError):
        return default


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--scripts", required=True)
    ap.add_argument("--lessons", required=True)
    ap.add_argument("--instructions", required=True)
    ap.add_argument("--memory-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--heartbeat", required=True)
    a = ap.parse_args()

    started = utc_now()
    py = sys.executable
    S = a.scripts

    steps = []

    st, out_check, _ = run_checker(
        "lesson_check",
        [py, os.path.join(S, "lesson_check.py"), a.lessons],
        "lesson_check:", S)
    steps.append(st)

    st, out_audit, _ = run_checker(
        "lesson_gate_audit",
        [py, os.path.join(S, "lesson_gate.py"), "audit",
         "--lessons", a.lessons, "--instructions", a.instructions],
        "digest block:", S)
    steps.append(st)

    # THE GATE RUNS BEFORE THE ANALYSER, not after. A check that reports on
    # something already executed is a post-mortem, not a guard.
    #
    # An ABSENT analyser is deliberately NOT sent through the gate. There is
    # nothing to refuse: the deployment is broken, which is exit 2's territory,
    # and the normal run_checker path reports it as DID NOT RUN. Sending it
    # here would dress an accident up as a decision.
    if not os.path.isfile(os.path.join(S, "dream_analyze.py")):
        integrity_ok = True
        integrity_state = "NOT_CHECKED"
        integrity_detail = ("dream_analyze.py is absent, so there was nothing to "
                            "verify; the DID NOT RUN path owns this failure.")
    else:
        integrity_ok, integrity_state, integrity_detail = check_analyser_integrity(S)

    integrity_refused = (integrity_state not in ("OK", "NOT_CHECKED"))

    if integrity_ok:
        st, out_dream, _ = run_checker(
            "dream_analyze",
            [py, os.path.join(S, "dream_analyze.py"),
             "--lessons", a.lessons, "--instructions", a.instructions,
             "--memory-dir", a.memory_dir],
            "DREAM ANALYSIS", S)
    else:
        # SKIPPED, deliberately - NOT "DID NOT RUN". The distinction is the
        # whole point of the exit-code split above.
        out_dream = ""
        st = {"name": "dream_analyze", "argv": ["dream_analyze.py"],
              "started_at": stamp(utc_now()), "ran": False, "exit": None,
              "verdict": "SKIPPED (failed integrity)",
              "integrity_state": integrity_state,
              "integrity_detail": integrity_detail}
    steps.append(st)

    measurements = {
        "entries": num(r"lesson_check: (\d+) entries", out_check),
        "unique_keys": num(r"(\d+) unique keys", out_check),
        "fail": num(r"FAIL (\d+)", out_check),
        "warn": num(r"WARN (\d+)", out_check),
        "prose_only": num(r"prose-only (\d+)", out_check),
        # Tiered marker: "<N> always-on of <M> rules from <K> entries".
        # Compare LIKE WITH LIKE. Before tiering the digest advertised every
        # ruled entry, so advertised-vs-held was the staleness test. After
        # tiering, 26 always-on of 60 rules is CORRECT and comparing those two
        # numbers would report a stale digest every single night.
        "digest_alwayson_advertised": num(
            r"advertises (\d+) always-on", out_audit),
        "digest_alwayson_actual": num(
            r"lessons file holds (\d+) always-on", out_audit),
        "digest_advertises": num(
            r"advertises \d+ always-on of (\d+) rules", out_audit),
        "digest_holds": num(
            r"lessons file holds \d+ always-on of (\d+) rules", out_audit),
        "blocked_surfaces": len(re.findall(r"^\s*\w+\s+\d+\s+\d+\s+[1-9]\d*\s",
                                           out_audit, re.M)),
        "reachability_pct": num(r"\((\d+)%\) carry a Rule line", out_dream),
        "findings": num(r"(\d+) finding\(s\) to review", out_dream),
        "dup_pairs": num(r"(\d+) pairs\s+median", out_dream),
        "dup_max_observed": num(r"MAX OBSERVED ([\d.]+)", out_dream, float),
        "dup_floor": num(r"^floor ([\d.]+)", out_dream, float),
    }

    # The digest contract, checked mechanically rather than eyeballed.
    # BOTH pairs must agree: the always-on count and the underlying rule count.
    adv, held = measurements["digest_advertises"], measurements["digest_holds"]
    aadv, aheld = (measurements["digest_alwayson_advertised"],
                   measurements["digest_alwayson_actual"])
    digest_stale = any(
        x is not None and y is not None and x != y
        for x, y in ((adv, held), (aadv, aheld)))

    did_not_run = [s["name"] for s in steps if s["verdict"] == "DID NOT RUN"]
    findings = [s["name"] for s in steps if s["verdict"] == "FINDINGS"]

    # Order matters. Integrity outranks everything: if the analyser was refused,
    # the corpus was not fully examined and no verdict about it is available -
    # including "clean".
    if integrity_refused:
        verdict, code = "FAILED INTEGRITY", 3
    elif did_not_run:
        verdict, code = "HARNESS FAILURE", 2
    elif findings or digest_stale:
        verdict, code = "FINDINGS FOR THE MORNING", 1
    else:
        verdict, code = "CLEAN", 0

    # THE INVARIANT, asserted rather than assumed. When the analyser did not
    # run - refused OR absent - every figure derived from it must be null,
    # never 0. A zero would be read next morning as "the analyser looked and
    # found nothing".
    analysis_ran = any(s["name"] == "dream_analyze" and s.get("ran")
                       for s in steps)
    if not analysis_ran:
        for k in ("findings", "dup_pairs", "dup_max_observed", "dup_floor",
                  "reachability_pct"):
            measurements[k] = None
        assert measurements["findings"] is None, (
            "findings must be null, not zero, when the analyser did not run")
    # proposals_emitted was REMOVED at schema 3. It was a literal 0 with no
    # code path anywhere that could change it, reported next to a real parsed
    # findings count - so two nights running the file read "findings: 15,
    # proposals_emitted: 0", which invites the conclusion that the analyser
    # looked and proposed nothing. It had in fact proposed every one of those
    # 15: merge candidates, retirement candidates and relative-date fixes are
    # all proposals, and `findings` is their count. The invariant directly
    # above forbids exactly this reading for the figures it covers; this field
    # sat one line below it doing the thing it forbids. Do not reintroduce a
    # second name for findings.

    ended = utc_now()
    report = {
        "schema_version": SCHEMA_VERSION,
        "run_started_at": stamp(started),
        "run_ended_at": stamp(ended),
        "elapsed_s": round((ended - started).total_seconds(), 2),
        "local_date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "verdict": verdict,
        "exit_code": code,
        "did_not_run": did_not_run,
        "with_findings": findings,
        "digest_stale": digest_stale,
        "analyser_integrity": integrity_state,
        "analyser_integrity_detail": integrity_detail,
        "analysis_ran": analysis_ran,
        "steps": steps,
        "measurements": measurements,
        "note": ("Measured only. No lesson, memory, digest or instruction file "
                 "was read for editing or written by this run."),
    }

    if not os.path.isdir(a.out_dir):
        os.makedirs(a.out_dir)
    path = os.path.join(a.out_dir, "measurements-%s.json"
                        % datetime.datetime.now().strftime("%Y-%m-%d"))
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")

    # HEARTBEAT. Written LAST and on every path, including a failed one: its
    # job is to prove the JOB executed, which is a different question from
    # whether the corpus is healthy. A heartbeat written only on success would
    # make a broken run look like a machine that never woke - the exact
    # ambiguity this whole job exists to remove.
    with open(a.heartbeat, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({
            "schema_version": SCHEMA_VERSION,
            "last_run_utc": stamp(ended),
            "last_run_local": datetime.datetime.now().strftime(
                "%Y-%m-%dT%H:%M:%S"),
            "verdict": verdict,
            "exit_code": code,
            "report": os.path.basename(path),
        }, fh, indent=2)
        fh.write("\n")

    print("nightly_measure: %s" % verdict)
    print("  analyser integrity: %s" % integrity_state)
    if integrity_refused:
        print("    %s" % integrity_detail)
        print("    The analyser was NOT run. Every figure it would have produced")
        print("    is recorded as null, not zero - nothing was examined.")
    for s in steps:
        print("  %-18s %-12s exit=%s" % (s["name"], s["verdict"], s["exit"]))
    print("  entries=%s FAIL=%s WARN=%s findings=%s dup_max=%s floor=%s"
          % (measurements["entries"], measurements["fail"],
             measurements["warn"], measurements["findings"],
             measurements["dup_max_observed"], measurements["dup_floor"]))
    if digest_stale:
        print("  DIGEST STALE: advertises %s always-on of %s rules; "
              "file gives %s always-on of %s" % (aadv, adv, aheld, held))
    print("  report:    %s" % path)
    print("  heartbeat: %s" % a.heartbeat)
    return code


if __name__ == "__main__":
    sys.exit(main())
