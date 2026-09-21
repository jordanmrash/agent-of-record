#!/usr/bin/env python3
"""
digest_preview.py - show what a TIERED always-on digest would contain.

READ-ONLY. Writes nothing, changes nothing. It exists so the decision to
shrink the always-on rule set is made against real names, not an estimate.

WHY THIS IS A PREVIEW AND NOT AN APPLY
--------------------------------------
lesson_gate G2 compares the digest's advertised rule count against EVERY
ruled entry in the lessons file:

    if (claimed_rules, claimed_entries) != (actual_rules, actual_entries):
        "G2 digest is STALE ... The difference is not loading."

So emitting fewer rules than the file holds makes the gate report STALE
forever and every close fails. Actually shrinking the digest therefore needs
a coordinated change to the marker format across lesson_brief.cmd_digest,
lesson_gate G2, digest_apply.END_RE, and the gate's own selftest. That is a
four-file contract change and it is not safe to do casually.

Usage:
    python digest_preview.py --lessons <path> --tiers <path> [--json]

Exit codes:
    0  preview produced
    2  an input file could not be read     <- never confuse with a finding
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from lesson_brief import load
except ImportError:
    sys.stderr.write("FATAL: lesson_brief.py must sit beside digest_preview.py\n")
    sys.exit(2)


def read_tiers(path):
    pins, enforced = {}, {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split("|")]
                head = parts[0].split(None, 1)
                if len(head) != 2:
                    continue
                kind, key = head[0].upper(), head[1].strip()
                if kind == "PIN":
                    pins[key] = parts[1] if len(parts) > 1 else ""
                elif kind in ("ENFORCED", "PARTIAL"):
                    # PARTIAL added 2026-09-01 alongside ENFORCED. This is the
                    # SECOND parser of digest-tiers.txt - lesson_brief.read_tiers
                    # is the first - and it was missed when PARTIAL was
                    # introduced, which would have reported all six tiered rules
                    # as TIERS FILE DRIFT. Exactly the trap named by
                    # config-contradiction-survives-in-second-file: a format has
                    # as many readers as it has readers, and the one that is not
                    # updated is the one that raises the false alarm.
                    enforced[key] = (parts[1] if len(parts) > 1 else "",
                                     parts[2] if len(parts) > 2 else "")
    except OSError as exc:
        sys.stderr.write("FATAL: cannot read tiers file: %s\n" % exc)
        sys.exit(2)
    return pins, enforced


def main():
    ap = argparse.ArgumentParser(description="Preview a tiered always-on digest.")
    ap.add_argument("--lessons", required=True)
    ap.add_argument("--tiers", required=True)
    ap.add_argument("--min-hits", type=int, default=2)
    a = ap.parse_args()

    if not os.path.isfile(a.lessons):
        sys.stderr.write("FATAL: lessons file not found: %s\n" % a.lessons)
        return 2
    pins, enforced = read_tiers(a.tiers)

    entries = load(a.lessons)
    ruled = [e for e in entries if e["rule"]]
    by_key = {e["key"]: e for e in ruled}

    # every key named in the tiers file must exist, or the file is drifting
    unknown = [k for k in list(pins) + list(enforced) if k not in by_key]

    keep_repeat = [e for e in ruled
                   if e["hits"] >= a.min_hits and e["key"] not in enforced]
    keep_pin = [e for e in ruled
                if e["key"] in pins and e["hits"] < a.min_hits
                and e["key"] not in enforced]
    drop_enforced = [e for e in ruled if e["key"] in enforced]
    keep_keys = {e["key"] for e in keep_repeat + keep_pin}
    drop_surface = [e for e in ruled
                    if e["key"] not in keep_keys and e["key"] not in enforced]

    total = len(ruled)
    keep = len(keep_repeat) + len(keep_pin)

    print("=" * 72)
    print("TIERED DIGEST PREVIEW - nothing has been changed")
    print("=" * 72)
    print("lessons: %s" % a.lessons)
    print("entries: %d   ruled: %d" % (len(entries), total))
    print()
    print("ALWAYS-ON would be %d of %d rules  (%d%% reduction)"
          % (keep, total, round(100 * (total - keep) / max(1, total))))
    print()

    print("-- KEEP: repeated (hits >= %d) : %d" % (a.min_hits, len(keep_repeat)))
    for e in sorted(keep_repeat, key=lambda x: (-x["hits"], x["key"])):
        print("   %dx  %-46s [%s]" % (e["hits"], e["key"], e["surface"]))
    print()

    print("-- KEEP: pinned as irreversible : %d" % len(keep_pin))
    for e in sorted(keep_pin, key=lambda x: x["key"]):
        print("   PIN  %-46s [%s]" % (e["key"], e["surface"]))
        print("        %s" % pins[e["key"]][:96])
    print()

    print("-- DROP: an automated check now refuses this : %d" % len(drop_enforced))
    for e in sorted(drop_enforced, key=lambda x: x["key"]):
        who, what = enforced[e["key"]]
        print("   ->   %-46s enforced by %s" % (e["key"], who))
    print()

    print("-- DROP to surface-loading (still reachable via preflight) : %d"
          % len(drop_surface))
    bysurf = {}
    for e in drop_surface:
        bysurf.setdefault(e["surface"], []).append(e["key"])
    for s in sorted(bysurf):
        print("   %-8s %d: %s" % (s, len(bysurf[s]), ", ".join(sorted(bysurf[s])[:3])
                                  + (" ..." if len(bysurf[s]) > 3 else "")))
    print()

    if unknown:
        print("!! TIERS FILE DRIFT - these keys are named in digest-tiers.txt but")
        print("!! no longer exist in the lessons file. Fix before applying:")
        for k in unknown:
            print("   - %s" % k)
        print()

    print("NOT APPLIED. lesson_gate G2 compares the digest's advertised count")
    print("against every ruled entry, so shrinking the block without changing")
    print("the marker contract would make every close report STALE.")
    print("Four files must change together: lesson_brief.cmd_digest,")
    print("lesson_gate G2, digest_apply.END_RE, lesson_gate_selftest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
