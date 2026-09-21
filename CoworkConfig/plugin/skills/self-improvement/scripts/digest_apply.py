#!/usr/bin/env python3
"""
digest_apply.py - splice a freshly generated digest into the instructions file.

The missing link. `lesson_brief.py --digest` PRINTS the block and
`lesson_gate.py` DETECTS when the copy in copilot-instructions.md has gone
stale, but nothing ever wrote the new block into the file. That splice was a
manual copy-paste, which is precisely why a digest goes stale: the detection
was automated and the fix was not.

Refuses to write unless the result verifies. Specifically:
  * the BEGIN and END markers must both exist, exactly once each
  * everything outside the markers must be byte-identical afterwards
  * the new block must re-extract to exactly what was generated
  * a .bak of the previous instructions file is written first

--check exits 1 when the file is stale without changing anything, so it can be
used as a gate in its own right.

Exit codes:
    0  applied (or --check found it already current)
    1  --check found it stale, or a verification refused the write
    2  an input file could not be read / markers missing
"""

import argparse
import io
import os
import re
import shutil
import sys
from contextlib import redirect_stdout

try:
    from lesson_brief import load, cmd_digest
except ImportError:
    sys.stderr.write("FATAL: lesson_brief.py must sit beside digest_apply.py\n")
    sys.exit(2)

BEGIN = "<!-- LESSON-DIGEST:BEGIN"
# LOCATOR, deliberately liberal: it must match the marker ALREADY ON DISK,
# including the pre-tiering two-number form, or this script cannot migrate the
# very block it exists to replace. Measured 2026-08-31: a strict tiered-only
# pattern made digest_apply refuse with "expected exactly one END marker,
# found 0" against the live file, and the flip could not proceed.
#
# Liberal in what it ACCEPTS when finding the old block; strict in what it
# WRITES - the emitted marker always comes from lesson_brief.cmd_digest and is
# always the three-number tiered form. lesson_gate's END_RE stays strict on
# purpose: the GATE must fail an out-of-date marker, the MIGRATOR must not.
END_RE = re.compile(
    r"<!-- LESSON-DIGEST:END - \d+ (?:always-on of \d+ )?rules from "
    r"\d+ entries -->")


def generate(lessons_path):
    entries = load(lessons_path)
    buf = io.StringIO()
    with redirect_stdout(buf):
        cmd_digest(entries, None)
    return buf.getvalue().rstrip("\n"), entries


def locate(text):
    """Return (start, end) of the digest block, or exit 2 if unusable."""
    if text.count(BEGIN) != 1:
        sys.stderr.write("FATAL: expected exactly one BEGIN marker, found %d\n"
                         % text.count(BEGIN))
        sys.exit(2)
    ends = END_RE.findall(text)
    if len(ends) != 1:
        sys.stderr.write("FATAL: expected exactly one END marker, found %d\n"
                         % len(ends))
        sys.exit(2)
    start = text.find(BEGIN)
    m = END_RE.search(text, start)
    if not m:
        sys.stderr.write("FATAL: END marker precedes BEGIN marker\n")
        sys.exit(2)
    return start, m.end()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lessons", default="cowork-lessons.md")
    ap.add_argument("--instructions", default="copilot-instructions.md")
    ap.add_argument("--check", action="store_true",
                    help="report staleness and exit 1; change nothing")
    ap.add_argument("--no-backup", action="store_true")
    a = ap.parse_args()

    try:
        old = open(a.instructions, encoding="utf-8").read()
    except OSError as exc:
        sys.stderr.write("FATAL: cannot read %s: %s\n" % (a.instructions, exc))
        return 2

    fresh, entries = generate(a.lessons)
    start, end = locate(old)
    current = old[start:end]

    rules = sum(1 for e in entries if e["rule"])
    if current.strip() == fresh.strip():
        print("already current: %d rules from %d entries" % (rules, len(entries)))
        return 0

    if a.check:
        print("STALE: the digest block does not match a fresh regeneration.")
        print("       lessons file holds %d rules from %d entries" % (rules, len(entries)))
        print("       run without --check to apply")
        return 1

    new = old[:start] + fresh + old[end:]

    # Verify BEFORE writing: everything outside the block must be untouched.
    if new[:start] != old[:start] or new[len(new) - (len(old) - end):] != old[end:]:
        sys.stderr.write("REFUSED: content outside the digest block would change\n")
        return 1
    ns, ne = locate(new)
    if new[ns:ne].strip() != fresh.strip():
        sys.stderr.write("REFUSED: the spliced block does not re-extract cleanly\n")
        return 1

    if not a.no_backup:
        bak = a.instructions + ".pre-digest.bak"
        shutil.copyfile(a.instructions, bak)
        print("backup: %s" % os.path.basename(bak))

    with open(a.instructions, "w", encoding="utf-8", newline="") as fh:
        fh.write(new)

    # Read back from disk - never report success from the buffer we just built.
    back = open(a.instructions, encoding="utf-8").read()
    rs, re_ = locate(back)
    if back[rs:re_].strip() != fresh.strip():
        sys.stderr.write("FATAL: file on disk does not match what was written\n")
        return 1

    print("applied: %d rules from %d entries" % (rules, len(entries)))
    print("bytes: %d -> %d" % (len(old), len(back)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
