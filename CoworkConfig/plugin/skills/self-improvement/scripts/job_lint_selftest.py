#!/usr/bin/env python3
"""
job_lint_selftest.py - sabotage test for job_lint.py.

Every check is tested in BOTH directions:
  - a deliberately broken sample that MUST be caught
  - a correct sample that MUST NOT be caught

The second half is the point. A check that fires on everything proves nothing,
and a passing lint run only means something if the check can still say no.
That is the same negative-control discipline the close job uses on lesson_gate.

Exit 0 = every case behaved. Exit 1 = at least one case did not.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import job_lint  # noqa: E402

HEAD = "@echo off\nREM COWORK_OUTPUT: C:\\out\n"
VERDICT = "echo COWORK_RESULT: OK\n"


def codes(text, lang="bat"):
    try:
        found = job_lint.lint_text(text, lang)
    except TypeError:
        # The pre-2026-09-01 linter had no language scope: every check ran
        # against every file. Fall back instead of crashing, so this selftest
        # can be pointed at the OLD version and report the difference as failed
        # assertions. A stack trace would only prove the signature moved - and
        # "could not run" reading as "found something" is the exact confusion
        # lesson verifier-usage-error-reads-as-finding is about.
        found = job_lint.lint_text(text)
    return {f["code"] for f in found}


# Samples that must NOT be flagged, beyond the paired negative in CASES.
# (code that must stay silent, sample, language)
EXTRA_NEGATIVES = [
    # A variable assignment is not an invocation. This exact line refused a
    # real job on 2026-09-01 before the check was scoped to skip assignments.
    ("checker-no-args",
     HEAD + 'set "SI=C:\\Users\\u\\Cowork\\Skills\\self-improvement\\scripts\\'
            'job_lint.py"\n' + VERDICT, "bat"),
    ("checker-no-args",
     HEAD + '$LINT = "C:\\s\\lesson_check.py"\n' + VERDICT, "ps1"),
]

# The scope matrix itself, asserted rather than described.
# (code, sample, language, must_fire)
LANG_CASES = [
    # A .ps1 sidecar carries no verdict because its WRAPPER emits one. Linting
    # it for COWORK_RESULT flagged 9 of 17 real files for a defect none had.
    ("no-verdict", 'Write-Output "hello"\n', "ps1", False),
    ("no-verdict", 'echo hello\n', "bat", True),
    # PowerShell has no errorlevel; the pattern cannot apply to it.
    ("untested-exit", 'git commit -F $msg\nWrite-Output "done"\n', "ps1", False),
    ("untested-exit", 'git commit -F "%MSG%"\necho done\n', "bat", True),
    # These two DO read PowerShell, and are the reason the sweep was widened.
    ("onedrive-recursive",
     "Get-ChildItem -LiteralPath 'C:\\Users\\u\\OneDrive\\Cowork' -Recurse "
     "| Select-String 'x'\n", "ps1", True),
    ("quarantine-in-repo",
     '$q = "C:\\Users\\u\\Documents\\COPILOT_COWORK\\Quarantine\\x"\n', "ps1", True),
]


# (check code, sample that MUST trip it, sample that MUST NOT)
CASES = [
    (
        "no-verdict",
        HEAD + "echo hello\n",
        HEAD + "echo hello\n" + VERDICT,
    ),
    (
        "untested-exit",
        HEAD + 'git commit -F "%MSG%"\necho done\n' + VERDICT,
        HEAD + 'git commit -F "%MSG%"\nif errorlevel 1 goto failed\n' + VERDICT,
    ),
    (
        "verifier-piped",
        HEAD + 'python "C:\\s\\lesson_check.py" "C:\\m\\l.md" | find "FAIL"\n' + VERDICT,
        HEAD + 'python "C:\\s\\lesson_check.py" "C:\\m\\l.md"\n' + VERDICT,
    ),
    (
        "checker-no-args",
        HEAD + 'python "C:\\s\\lesson_check.py"\n' + VERDICT,
        HEAD + 'python "C:\\s\\lesson_check.py" "C:\\m\\lessons.md"\n' + VERDICT,
    ),
    (
        # UPDATED 2026-09-01 to the SHARPENED rule. The old bad-sample was a
        # bare -Recurse, which the 09-01 measurement showed is harmless: walking
        # metadata across the whole tree hydrates nothing. What costs is READING
        # the files walked, so the bad sample now reads and the good sample
        # walks. If this case is ever reverted to flagging a bare enumeration,
        # the check has drifted back to the superseded wording.
        "onedrive-recursive",
        HEAD + 'powershell -Command "Get-ChildItem -LiteralPath '
               "'C:\\Users\\u\\OneDrive\\Documents\\Cowork' -Recurse "
               "| Select-String 'term'\"\n" + VERDICT,
        HEAD + 'powershell -Command "Get-ChildItem -LiteralPath '
               "'C:\\Users\\u\\OneDrive\\Documents\\Cowork' -Recurse -File "
               '| Select-Object Name,Attributes"\n' + VERDICT,
    ),
    (
        "quarantine-in-repo",
        HEAD + 'set "Q=C:\\Users\\u\\Documents\\COPILOT_COWORK\\Quarantine\\x"\n' + VERDICT,
        # Hard negative control: the LEGITIMATE move puts the repo path and the
        # word quarantine on the SAME line. Naive co-occurrence flagged this.
        HEAD + 'move "C:\\Users\\u\\Documents\\COPILOT_COWORK\\CommandJobs\\p.bat" '
               '"C:\\Users\\u\\Downloads\\COWORK_QUARANTINE\\p.bat"\n'
               'if errorlevel 1 goto failed\n' + VERDICT,
    ),
    (
        "unguarded-snapshot",
        HEAD + 'powershell -Command "Copy-Item -LiteralPath $p -Destination '
               '(Join-Path $pre \'pre-edit\') -Force"\n' + VERDICT,
        HEAD + 'if not exist "%PRE%" powershell -Command "Copy-Item -LiteralPath $p '
               '-Destination (Join-Path $pre \'pre-edit\')"\n' + VERDICT,
    ),
    (
        "errorlevel-in-parens",
        HEAD + 'if exist foo.txt (\n  echo %ERRORLEVEL%\n)\n' + VERDICT,
        HEAD + 'call other.bat\nif errorlevel 1 goto failed\necho %ERRORLEVEL%\n' + VERDICT,
    ),
    (
        "no-output-decl",
        '@echo off\nset "OUT=%COWORK_JOB_OUTPUT%"\n' + VERDICT,
        HEAD + 'set "OUT=%COWORK_JOB_OUTPUT%"\n' + VERDICT,
    ),
]


def main():
    passed = failed = 0

    for code, bad, good in CASES:
        got_bad = codes(bad)
        if code in got_bad:
            passed += 1
        else:
            failed += 1
            print(f"MISS  [{code}] broken sample was NOT caught. got={sorted(got_bad)}")

        got_good = codes(good)
        if code not in got_good:
            passed += 1
        else:
            failed += 1
            print(f"FALSE [{code}] correct sample WAS flagged. got={sorted(got_good)}")

    for code, sample, lang in EXTRA_NEGATIVES:
        if code in codes(sample, lang):
            failed += 1
            print(f"FALSE [{code}] ({lang}) a correct sample WAS flagged")
        else:
            passed += 1

    for code, sample, lang, must_fire in LANG_CASES:
        fired = code in codes(sample, lang)
        if fired == must_fire:
            passed += 1
        else:
            failed += 1
            want = "fire" if must_fire else "stay silent"
            print(f"SCOPE [{code}] on .{lang} should {want} and did not")

    # every check must DECLARE the languages it reads - an undeclared scope is
    # how a rule got called ENFORCED on a surface its enforcer cannot read
    for c in job_lint.CHECKS:
        if not c.get("langs"):
            failed += 1
            print(f"NO SCOPE [{c['code']}] declares no languages")
            break
        if any(l not in getattr(job_lint, "ALL_LANGS", ()) for l in c["langs"]):
            failed += 1
            print(f"BAD SCOPE [{c['code']}] declares an unknown language")
            break
    else:
        passed += 1

    # the .ps1 sweep must actually collect .ps1, or the scope work is inert
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        for name in ("a.bat", "b.ps1", "c.txt"):
            open(os.path.join(d, name), "w").close()
        swept, _ = job_lint.collect([d])
        got = sorted(os.path.basename(f) for f in swept)
        if got == ["a.bat", "b.ps1"]:
            passed += 1
        else:
            failed += 1
            print(f"SWEEP collect() returned {got}, expected ['a.bat', 'b.ps1']")

    # every registered check must be covered by a case
    registered = {c["code"] for c in job_lint.CHECKS}
    covered = {c[0] for c in CASES}
    if registered - covered:
        failed += 1
        print(f"UNTESTED checks with no case: {sorted(registered - covered)}")
    else:
        passed += 1

    # every check must name where it came from
    for c in job_lint.CHECKS:
        if not c["source"].strip():
            failed += 1
            print(f"NO SOURCE [{c['code']}] does not name the lesson it enforces")
            break
    else:
        passed += 1

    # a missing path is a usage error (exit 2), never a finding (exit 1)
    _, missing = job_lint.collect(["C:\\no\\such\\path\\xyz"])
    if missing:
        passed += 1
    else:
        failed += 1
        print("MISS  a nonexistent path was not reported as unreadable")

    total = passed + failed
    print(f"\njob_lint_selftest: {passed}/{total} passed")
    if failed:
        print("SELFTEST: FAIL")
        return 1
    print("SELFTEST: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
