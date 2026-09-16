#!/usr/bin/env python3
"""
manifest_check.py - fail when a skill reads a file its manifest does not fetch.

THE DEFECT THIS EXISTS FOR
--------------------------
Three times in one session (2026-08-30) the dream-cycle skill told a scheduled
run to read a file that its acquisition manifest never retrieved:

  lesson_gate.py       the routine called lesson_gate audit; the manifest listed
                       three other scripts. The run would have died at the
                       digest step, after doing the whole analysis.
  analyser.approved    the routine required the marker and treated a missing one
                       as FAILED INTEGRITY. Never fetched. The gate would have
                       deadlocked on its own first run and every run after.
  determinism.md       the routine says to load it for the checkpoint and
                       fingerprint specs. Only listed after a fourth review.

Every one was found by a human reading carefully. None was a logic error - all
three were INTEGRATION defects, a dependency named in one section and absent
from another. That is exactly the class a machine should catch, because a
reviewer who misses it once ships it.

HOW IT WORKS
------------
The skill declares its dependencies in a fenced block tagged `manifest`, holding
an acquires: list and a not_acquired: list. The checker scans the whole SKILL.md
for backticked filenames that look like dependencies and FAILS on any appearing
in neither list.

not_acquired is deliberately explicit: a file the skill mentions but must NOT
fetch is a real decision, and writing it down is how the next editor knows it
was a decision rather than an omission.

Run it against any skill, not just dream-cycle.

Exit codes:
    0  every referenced file is accounted for
    1  a referenced file is in neither list, or the manifest block is malformed
    2  the skill file could not be read
"""

import argparse
import re
import sys

MANIFEST_RE = re.compile(r"```manifest\n(.*?)```", re.S)

# Extensions that denote a runtime dependency. Deliberately narrow: .bat and
# .cmd are excluded because a skill legitimately names jobs it does not read,
# and widening this to every filename produces a checker nobody trusts.
#
# KNOWN LIMITATION, stated rather than hidden: .md is NOT scanned. All three
# defects this was built for were .py or .approved, so this covers the measured
# class - but a .md dependency listed in acquires: will show as "declared but
# never referenced", which is the WARN, not a FAIL. Adding md here would also
# match every incidental prose mention of a document, including SKILL.md itself,
# and a checker that cries wolf on prose is one people stop reading. If a .md
# dependency is ever MISSED rather than merely unmatched, that is the case to
# revisit this - not before.
DEP_RE = re.compile(r"`([A-Za-z0-9_.-]+\.(?:py|approved|json))`")


def parse_manifest(text):
    """Returns (acquires, not_acquired) or exits 1 if malformed."""
    m = MANIFEST_RE.search(text)
    if not m:
        sys.stderr.write(
            "FAIL: no manifest block. A skill that reads files must declare\n"
            "      them. Add acquires: and not_acquired: lists.\n")
        sys.exit(1)

    acquires, not_acquired, current = [], [], None
    for raw in m.group(1).splitlines():
        line = raw.split("#")[0].rstrip()
        if not line.strip():
            continue
        if re.match(r"^acquires:\s*$", line):
            current = acquires
        elif re.match(r"^not_acquired:\s*$", line):
            current = not_acquired
        elif line.lstrip().startswith("- "):
            if current is None:
                sys.stderr.write("FAIL: list item before any section header\n")
                sys.exit(1)
            current.append(line.lstrip()[2:].strip())
        else:
            sys.stderr.write("FAIL: unparseable manifest line: %r\n" % raw)
            sys.exit(1)

    if not acquires:
        sys.stderr.write("FAIL: acquires: is empty. A manifest that fetches\n"
                         "      nothing cannot be satisfied by any run.\n")
        sys.exit(1)
    return acquires, not_acquired


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("skill", help="path to SKILL.md")
    ap.add_argument("--extra", action="append", default=[],
                    help="another file whose references also count")
    a = ap.parse_args()

    try:
        text = open(a.skill, encoding="utf-8").read()
    except OSError as exc:
        sys.stderr.write("FATAL: cannot read %s: %s\n" % (a.skill, exc))
        return 2

    acquires, not_acquired = parse_manifest(text)

    scan = text
    for path in a.extra:
        try:
            scan += "\n" + open(path, encoding="utf-8").read()
        except OSError as exc:
            sys.stderr.write("FATAL: cannot read %s: %s\n" % (path, exc))
            return 2

    referenced = sorted(set(DEP_RE.findall(scan)))
    declared = set(acquires) | set(not_acquired)
    missing = [f for f in referenced if f not in declared]

    print("manifest_check: %s" % a.skill)
    print("  acquires:     %d" % len(acquires))
    print("  not_acquired: %d" % len(not_acquired))
    print("  referenced:   %d" % len(referenced))

    unused = [f for f in acquires if f not in referenced]
    if unused:
        print()
        print("  WARN: declared in acquires but not matched by the scanner.")
        print("        Either the skill stopped using it, a reference was")
        print("        renamed, or it is a .md dependency (see the KNOWN")
        print("        LIMITATION note - .md is deliberately not scanned):")
        for f in unused:
            print("    %s" % f)
        print("        This is informational. Over-declaring is safe; the")
        print("        failure this tool exists for is UNDER-declaring.")

    if missing:
        print()
        print("FAIL: %d file(s) referenced but in NEITHER list." % len(missing))
        print("      A scheduled run would reach them without having fetched")
        print("      them. Add each to acquires:, or to not_acquired: with a")
        print("      comment saying why it must not be fetched.")
        for f in missing:
            print("    %s" % f)
        return 1

    print()
    print("PASS: every referenced dependency is declared.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
