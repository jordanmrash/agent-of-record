#!/usr/bin/env python3
"""
heartbeat_check.py - a local dead-man's switch for the 2am job.

WHAT IT ANSWERS
---------------
"Did the nightly job actually run?" - which is a different question from
"is the corpus healthy?". The scheduler answers neither: measured 2026-08-31,
a hosted scheduler reported success on a run that produced nothing for 5h 43m.
A trigger firing is not work happening.

So the job writes a heartbeat when it finishes, and this reads the AGE of that
heartbeat. Silence stops being ambiguous: a missing or stale heartbeat is a
positive finding, not an absence of one.

Nothing leaves the machine. No mail, no webhook, no telemetry - it exits
non-zero and prints why, and a human or a job reads that.

  exit 0  heartbeat present and fresh
  exit 1  heartbeat MISSING, STALE, or unreadable   <- a real finding
  exit 2  usage error                                <- NOT a finding

EXIT 1 vs 2 IS DELIBERATE, as in every other checker here: a checker that
could not run must never be mistaken for a checker that found something.

THE FAILURE MODE THIS WAS BUILT AGAINST
---------------------------------------
A staleness check with a threshold nothing can reach is decoration that reads
as reassurance. The dead 0.72 duplicate floor in dream_analyze.py was exactly
that shape - it printed "no duplicates" every night from below an unreachable
ceiling. So this prints the OBSERVED AGE on every run, clean or not, and
nightly_selftest.py drives it with an old heartbeat to prove it can fail.
"""

import argparse
import datetime
import json
import os
import sys


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--heartbeat", required=True)
    ap.add_argument("--max-age-hours", type=float, default=26.0,
                    help="a daily job is late once a full day plus slack has "
                         "passed; 26h tolerates a DST shift and a slow run "
                         "without tolerating a missed night (default 26)")
    a = ap.parse_args()

    if not os.path.isfile(a.heartbeat):
        print("HEARTBEAT MISSING: %s" % a.heartbeat)
        print("The 2am job has never completed, or its output was removed.")
        return 1

    try:
        with open(a.heartbeat, encoding="utf-8") as fh:
            hb = json.load(fh)
        last = datetime.datetime.strptime(
            hb["last_run_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=datetime.timezone.utc)
    except Exception as exc:                      # noqa: BLE001
        print("HEARTBEAT UNREADABLE: %s" % str(exc)[:200])
        print("Treated as a finding: an unparseable heartbeat proves nothing.")
        return 1

    age_h = (datetime.datetime.now(datetime.timezone.utc) - last
             ).total_seconds() / 3600.0

    # Printed on BOTH branches, on purpose. A check that reports only its
    # verdict hides whether the threshold was ever in reach.
    print("heartbeat    %s  (age %.2f h, threshold %.2f h)"
          % (hb.get("last_run_utc"), age_h, a.max_age_hours))
    print("last verdict %s (exit %s)"
          % (hb.get("verdict"), hb.get("exit_code")))

    if age_h > a.max_age_hours:
        print("HEARTBEAT STALE: the nightly job has not completed in %.1f hours."
              % age_h)
        print("Check Task Scheduler history for 'Cowork Nightly Measure'.")
        return 1

    print("HEARTBEAT OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
