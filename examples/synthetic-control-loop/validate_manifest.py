#!/usr/bin/env python3
"""Deterministic input gate for the synthetic workpaper.

This is the enforcement mechanism the lesson prescribes: the manifest names the
required segments, and nothing downstream runs until every one of them is present
and non-empty. A missing segment is a hard stop that names what is missing. The
gate produces no partial output, so a complete-looking workpaper cannot be built
from incomplete inputs by accident.

Exit codes: 0 complete, 3 a required segment is missing or empty, 2 could not run.
"""
import csv
import json
import os
import sys


def main(argv):
    if len(argv) != 1:
        print("usage: validate_manifest.py <input-folder>")
        return 2
    folder = argv[0]
    manifest_path = os.path.join(folder, "manifest.json")
    try:
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, ValueError) as exc:
        print("COULD NOT RUN: %s" % exc)
        return 2

    missing, present = [], []
    for seg in manifest["required_segments"]:
        path = os.path.join(folder, seg["file"])
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            missing.append(seg)
            continue
        with open(path, encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        present.append((seg, len(rows)))

    print("workpaper : %s" % manifest["workpaper"])
    for seg, n in present:
        print("  present  %s  %-16s %d rows  %s" % (seg["id"], seg["file"], n, seg["description"]))
    for seg in missing:
        print("  MISSING  %s  %-16s         %s" % (seg["id"], seg["file"], seg["description"]))

    if missing:
        ids = ", ".join(s["id"] for s in missing)
        print("HARD STOP: required segment(s) %s absent. No workpaper was produced." % ids)
        return 3

    print("complete  : %d of %d required segments present; downstream steps may run"
          % (len(present), len(manifest["required_segments"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
