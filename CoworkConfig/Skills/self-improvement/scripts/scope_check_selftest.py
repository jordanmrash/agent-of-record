#!/usr/bin/env python3
"""
scope_check_selftest.py - sabotage test for scope_check.py.

A checker nobody has tried to fool is an assumption. Each case below breaks the
tiering file in ONE specific way and asserts the specific outcome, not merely
that something failed - and the positive control runs FIRST, so a scope_check
that refuses everything cannot pass this file.

The exit-code cases matter as much as the findings: 2 (could not run) must never
be reachable by a broken CLAIM, and 1 (a real finding) must never be produced by
a broken INVOCATION. Conflating those is verifier-usage-error-reads-as-finding.

Exit 0 = every case behaved. Exit 1 = at least one did not.
"""

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCOPE_CHECK = os.path.join(HERE, "scope_check.py")
REAL_TIERS = os.path.join(os.path.dirname(HERE), "digest-tiers.txt")
if not os.path.isfile(REAL_TIERS):
    REAL_TIERS = os.path.join(HERE, "digest-tiers.txt")

HEAD = "# test tiers file\n"
GOOD = ("PARTIAL onedrive-recursive-scan-hydrates-tree | job_lint/onedrive-recursive "
        "| refuses a read-backed recursive walk | covers: bat,cmd,ps1 | blind: session\n")


def run(tiers_text=None, path=None, extra=None):
    args = [sys.executable, SCOPE_CHECK]
    tmp = None
    if tiers_text is not None:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                          encoding="utf-8")
        tmp.write(tiers_text)
        tmp.close()
        args.append(tmp.name)
    elif path is not None:
        args.append(path)
    if extra:
        args.extend(extra)
    args.extend(["--scripts", HERE])
    p = subprocess.run(args, capture_output=True, text=True)
    if tmp:
        os.unlink(tmp.name)
    return p.returncode, p.stdout + p.stderr


CASES = [
    # (name, tiers text, expected exit, substring that must appear)
    ("a correct claim passes",
     HEAD + GOOD, 0, "CLEAN"),
    ("no covers/blind declared at all",
     HEAD + "PARTIAL onedrive-recursive-scan-hydrates-tree | "
            "job_lint/onedrive-recursive | refuses it\n", 1, "declares no covers"),
    ("covers overstates what the check reads",
     HEAD + "PARTIAL cowork-close-reports-ok-on-failed-commit | "
            "job_lint/no-verdict,untested-exit | x | covers: bat,cmd,ps1 "
            "| blind: session\n", 1, "actually read"),
    ("blind understates the unread surfaces",
     HEAD + "PARTIAL onedrive-recursive-scan-hydrates-tree | "
            "job_lint/onedrive-recursive | x | covers: bat,cmd,ps1 | blind: -\n",
     1, "unread"),
    ("ENFORCED while blind somewhere",
     HEAD + "ENFORCED onedrive-recursive-scan-hydrates-tree | "
            "job_lint/onedrive-recursive | x | covers: bat,cmd,ps1 "
            "| blind: session\n", 1, "must be PARTIAL"),
    ("names a check job_lint does not register",
     HEAD + "PARTIAL some-key | job_lint/no-such-check | x | covers: bat "
            "| blind: cmd,ps1,session\n", 1, "does not register"),
    ("a non-job_lint enforcer is UNVERIFIED, not silently clean",
     HEAD + "PARTIAL some-key | human-review | x | covers: bat | blind: session\n",
     0, "UNVERIFIED"),
    ("a file with no tiering lines is a usage error, not a finding",
     HEAD + "# nothing here\n", 2, "no ENFORCED or PARTIAL"),
]


def main():
    passed = failed = 0

    for name, text, want_rc, want_sub in CASES:
        rc, out = run(tiers_text=text)
        ok_rc = (rc == want_rc)
        ok_sub = (want_sub.lower() in out.lower())
        if ok_rc and ok_sub:
            passed += 1
            print(f"{name:<52} PASS")
        else:
            failed += 1
            print(f"{name:<52} FAIL (rc={rc}, wanted {want_rc}; "
                  f"substring {'found' if ok_sub else 'MISSING'})")

    # an unreadable path is exit 2, never exit 1
    rc, _ = run(path=os.path.join(HERE, "definitely-not-here-9f2a.txt"))
    if rc == 2:
        passed += 1
        print(f"{'unreadable input exits 2, not 1':<52} PASS")
    else:
        failed += 1
        print(f"{'unreadable input exits 2, not 1':<52} FAIL (rc={rc})")

    # --scope must work with no tiers file at all
    rc, out = run(extra=["--scope"])
    if rc == 0 and "blind" in out.lower():
        passed += 1
        print(f"{'--scope states its own blind spots':<52} PASS")
    else:
        failed += 1
        print(f"{'--scope states its own blind spots':<52} FAIL (rc={rc})")

    # the real tiers file shipped alongside must itself be clean
    if os.path.isfile(REAL_TIERS):
        rc, out = run(path=REAL_TIERS)
        if rc == 0:
            passed += 1
            print(f"{'the shipped digest-tiers.txt is clean':<52} PASS")
        else:
            failed += 1
            print(f"{'the shipped digest-tiers.txt is clean':<52} FAIL (rc={rc})")
            print(out)
    else:
        failed += 1
        print(f"{'the shipped digest-tiers.txt is readable':<52} FAIL (not found)")

    total = passed + failed
    print(f"\nscope_check_selftest: {passed}/{total} passed")
    if failed:
        print("SELFTEST: FAIL")
        return 1
    print("SELFTEST: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
