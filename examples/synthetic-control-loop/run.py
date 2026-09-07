#!/usr/bin/env python3
"""Run the synthetic control loop end to end, with no host, tunnel or network.

Three steps, each of which must come out the way the lesson predicts:

  1. The deterministic gate accepts the complete input set (exit 0).
  2. The same gate refuses the set with Segment D missing, names D, and produces
     nothing (exit 3). This is the enforcement mechanism the lesson prescribes.
  3. The real verification harness (CoworkConfig/Skills/self-improvement/scripts/
     verify_delivery.py) judges the recorded three-arm-plus-control transcripts
     for this case and returns EFFECTIVE - the rule is doing the work, because
     the control without it failed.

The judge writes its ledger entry to a temporary file, so running this never
changes the repository. `--check` prints one line per step and is what the
release check and CI call.

Exit codes: 0 every step behaved as predicted, 1 a step did not, 2 could not run.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
HARNESS = os.path.join(ROOT, "CoworkConfig", "Skills", "self-improvement", "scripts", "verify_delivery.py")
KEY = "workpaper-required-segment-missing"


def run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=HERE)
    return proc.returncode, (proc.stdout + proc.stderr)


def step(quiet, label, ok, detail):
    mark = "ok  " if ok else "FAIL"
    print("  %s  %s" % (mark, label))
    if not quiet and detail:
        print("\n".join("        " + l for l in detail.rstrip().splitlines()))
        print()
    return ok


def main(argv):
    quiet = "--check" in argv
    py = sys.executable
    gate = os.path.join(HERE, "validate_manifest.py")
    if not os.path.isfile(HARNESS):
        print("COULD NOT RUN: harness not found at %s" % HARNESS)
        return 2

    print("Synthetic control loop - %s" % KEY)
    results = []

    rc, out = run([py, gate, os.path.join(HERE, "inputs", "complete")])
    results.append(step(quiet, "gate accepts the complete input set (exit 0)", rc == 0, out))

    rc, out = run([py, gate, os.path.join(HERE, "inputs", "incomplete")])
    ok = rc == 3 and "HARD STOP" in out and " D " in out and "No workpaper was produced" in out
    results.append(step(quiet, "gate refuses the set missing Segment D, names it, produces nothing (exit 3)", ok, out))

    with tempfile.TemporaryDirectory(prefix="control-loop-") as tmp:
        ledger = os.path.join(tmp, "ledger.json")
        rc, out = run([py, HARNESS, "judge", "--key", KEY,
                       "--cases", os.path.join(HERE, "verification-case.json"),
                       "--lessons", os.path.join(HERE, "lesson.md"),
                       "--results", os.path.join(HERE, "recorded-runs.json"),
                       "--ledger", ledger])
        ok = rc == 0 and "\nEFFECTIVE\n" in out and "3 of 3 passed" in out and "control      : FAIL" in out
        if "REFUSED" in out:
            out += ("\nThe judge refused the recorded runs. The case or the rule text has changed since they were\n"
                    "recorded, so the stored verdict no longer applies - that refusal is the harness working as\n"
                    "designed. Re-record the runs against the current text.")
        results.append(step(quiet, "harness judges the recorded arms EFFECTIVE (3 carried pass, control fails)", ok, out))

    if all(results):
        print("CONTROL_LOOP: OK - a missing input became a hard stop, and the delivered rule is measured, not assumed.")
        return 0
    print("CONTROL_LOOP: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
