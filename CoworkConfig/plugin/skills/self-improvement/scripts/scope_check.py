#!/usr/bin/env python3
"""
scope_check.py - refuse a tiering claim that outruns the thing enforcing it.

WHY THIS EXISTS
---------------
digest-tiers.txt drops a rule out of always-on context whenever an automated
check "already refuses the mistake". That reasoning is sound only if the check
reads every surface the mistake can be made on. Nothing recorded which surfaces
those were, so the claim could not be wrong - it could only be unexamined.

On 2026-09-01 it was examined. onedrive-recursive-scan-hydrates-tree was ENFORCED
by job_lint/onedrive-recursive; job_lint swept .bat and .cmd only, the rule was
therefore silent on 17 .ps1 sidecars and on anything the agent does directly, and
the rule was missed in the one place its prose had been quietened. See lesson
digest-enforced-demotion-outruns-the-enforcer.

WHAT IT CHECKS
--------------
The declared scope in digest-tiers.txt is compared against the scope job_lint
ACTUALLY declares in code. The two cannot drift, because one is read from the
other. A hand-written claim that no longer matches the enforcer is a FAIL.

  covers:  surfaces the enforcer reads
  blind:   surfaces it does not - these stay unenforced and must still be
           delivered as prose on the per-surface lookup

  ENFORCED  is only legitimate when blind is empty
  PARTIAL   is the honest classification when it is not

EXIT CODES
----------
  0  every claim matches its enforcer
  1  at least one claim overruns its enforcer   <- a real finding
  2  usage error / unreadable input             <- NOT a finding

1 and 2 are distinct on purpose. A checker that never ran must never be mistaken
for one that found something (verifier-usage-error-reads-as-finding).

ITS OWN BLIND SPOTS, stated because that is the entire subject of this file:
  - It verifies job_lint-backed claims only. An enforcer named anything else is
    reported UNVERIFIED, not clean - it is a claim this script cannot audit.
  - It checks that a blind surface is DECLARED, not that the rule's prose
    actually covers it. Wording is still a human judgement.
  - 'session' - the agent acting directly through tools rather than through a
    script - is a surface job_lint structurally cannot read, so it is blind for
    every file-linting enforcer by construction.
"""

import argparse
import os
import re
import sys

ALL_SURFACES = ("bat", "cmd", "ps1", "session")

TIER_LINE = re.compile(r"^(ENFORCED|PARTIAL)\s+(\S+)\s*\|(.*)$")


def parse_tiers(path):
    rows, errors = [], []
    with open(path, "r", encoding="utf-8") as fh:
        for n, raw in enumerate(fh, 1):
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            m = TIER_LINE.match(line.strip())
            if not m:
                continue
            tier, key, rest = m.group(1), m.group(2), m.group(3)
            fields = [f.strip() for f in rest.split("|")]
            enforcer = fields[0] if fields else ""
            covers = blind = None
            for f in fields:
                low = f.lower()
                if low.startswith("covers:"):
                    covers = _surfaces(f.split(":", 1)[1])
                elif low.startswith("blind:"):
                    blind = _surfaces(f.split(":", 1)[1])
            rows.append({"line": n, "tier": tier, "key": key, "enforcer": enforcer,
                         "covers": covers, "blind": blind})
    return rows, errors


def _surfaces(text):
    text = text.strip()
    if text in ("-", "none", ""):
        return frozenset()
    return frozenset(s.strip().lower() for s in text.replace(",", " ").split() if s.strip())


def enforcer_scope(enforcer, checks_by_code):
    """Resolve 'job_lint/code1,code2' to the surfaces those checks actually read.

    A rule needing several checks is enforced only where ALL of them apply, so
    the intersection is taken. Returns (covers, unknown_codes) or None when the
    enforcer is not job_lint-backed and therefore cannot be audited here.
    """
    if not enforcer.lower().startswith("job_lint/"):
        return None, []
    codes = [c.strip() for c in enforcer.split("/", 1)[1].split(",") if c.strip()]
    unknown = [c for c in codes if c not in checks_by_code]
    known = [c for c in codes if c in checks_by_code]
    if not known:
        return frozenset(), unknown
    covers = None
    for c in known:
        langs = frozenset(checks_by_code[c]["langs"])
        covers = langs if covers is None else (covers & langs)
    return covers, unknown


def main():
    ap = argparse.ArgumentParser(
        description="Refuse a tiering claim that outruns its enforcer.")
    ap.add_argument("tiers", nargs="?", help="path to digest-tiers.txt")
    ap.add_argument("--scripts", help="folder holding job_lint.py "
                                      "(defaults to this script's folder)")
    ap.add_argument("--scope", action="store_true",
                    help="print what this checker can and cannot audit, and exit")
    a = ap.parse_args()

    if a.scope:
        print(__doc__.split("ITS OWN BLIND SPOTS")[1].strip())
        return 0
    if not a.tiers:
        ap.error("no tiers file given (use --scope to inspect this checker's reach)")
    if not os.path.isfile(a.tiers):
        print(f"scope_check: cannot read {a.tiers}", file=sys.stderr)
        return 2

    sys.path.insert(0, a.scripts or os.path.dirname(os.path.abspath(__file__)))
    try:
        import job_lint
    except ImportError as exc:
        print(f"scope_check: cannot import job_lint ({exc})", file=sys.stderr)
        return 2
    if not hasattr(job_lint, "CHECKS") or not job_lint.CHECKS:
        print("scope_check: job_lint exposes no CHECKS", file=sys.stderr)
        return 2
    if any("langs" not in c for c in job_lint.CHECKS):
        print("scope_check: this job_lint predates per-check language scope, so "
              "there is nothing to compare a claim against", file=sys.stderr)
        return 2

    by_code = {c["code"]: c for c in job_lint.CHECKS}
    rows, _ = parse_tiers(a.tiers)
    if not rows:
        print("scope_check: no ENFORCED or PARTIAL lines found", file=sys.stderr)
        return 2

    findings = []
    unverified = 0
    for r in rows:
        actual, unknown = enforcer_scope(r["enforcer"], by_code)
        if actual is None:
            unverified += 1
            print(f"  UNVERIFIED [{r['key']}] enforcer '{r['enforcer']}' is not "
                  f"job_lint-backed; this checker cannot audit it")
            continue
        if unknown:
            findings.append((r, f"names check(s) {unknown} that job_lint does not "
                                f"register - the claim points at nothing"))
            continue
        if r["covers"] is None or r["blind"] is None:
            findings.append((r, "declares no covers:/blind: scope, so the claim "
                                "cannot be checked against the enforcer"))
            continue
        expected_blind = frozenset(ALL_SURFACES) - actual
        if r["covers"] != actual:
            findings.append((r, f"claims covers: {_fmt(r['covers'])} but the checks "
                                f"actually read {_fmt(actual)}"))
        elif r["blind"] != expected_blind:
            findings.append((r, f"claims blind: {_fmt(r['blind'])} but the unread "
                                f"surfaces are {_fmt(expected_blind)}"))
        elif r["tier"] == "ENFORCED" and expected_blind:
            findings.append((r, f"is ENFORCED while blind on {_fmt(expected_blind)}; "
                                f"a rule unenforced anywhere must be PARTIAL, so its "
                                f"prose is kept rather than dropped"))

    for r, msg in findings:
        print(f"  FAIL [{r['key']}] line {r['line']}")
        print(f"       {msg}")

    print(f"\nscope_check: {len(rows)} tiering claim(s), {len(findings)} FAIL, "
          f"{unverified} unverifiable")
    if findings:
        print("SCOPE_CHECK: FAIL")
        return 1
    print("SCOPE_CHECK: CLEAN")
    return 0


def _fmt(s):
    return ",".join(sorted(s)) if s else "-"


if __name__ == "__main__":
    sys.exit(main())
