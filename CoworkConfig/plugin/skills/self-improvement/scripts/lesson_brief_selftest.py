#!/usr/bin/env python3
"""
lesson_brief_selftest.py - regression tests for the surface classifier.

Exists because of a real defect shipped 2026-08-28: the classifier matched
content substrings, so "profile" matched "file" and the voice-calibration rule
was filed under `files`. `--for skills` silently missed it. A lookup tool that
returns the wrong set is worse than no lookup tool, because it reads as an
answer.

Positive control runs FIRST. Every case asserts the expected surface by name,
not merely that something was returned.
"""

import sys

from lesson_brief import surface_of

# (key, title, expected surface)
CASES = [
    # the defect that prompted this suite
    ("skill-voiceprofile-calibrate-from-user-diff",
     "Calibrate a voice profile from a real user rewrite", "skills"),
    # prefix must beat misleading title words
    ("onedrive-cloud-to-laptop-lag",
     "Commit waits on the repo copy", "files"),
    ("onedrive-pick-the-leg-that-does-not-block",
     "Choose the leg that does not block the commit", "files"),
    ("git-deletion-does-not-sanitize-history",
     "A deleted file remains in every earlier commit", "git"),
    ("lessons-file-section-anchor-must-be-exact",
     "Anchor a section insert on the FULL heading", "memory"),
    ("savememory-512-cap-rejects-silently",
     "The memory store caps content", "memory"),
    ("artifact-delete-recursive-skips-file-paths",
     "Reconcile every requested path", "files"),
    ("bridge-8933-stateless-defeats-in-process-state",
     "A stateless bridge spawns a fresh process per call", "bridge"),
    ("voice-us-register-sweep",
     "Sweep for US spelling and contractions", "skills"),
    ("verifier-ignores-structural-diff",
     "A renamed column reported PASS", "claims"),
    ("prestage-verify-by-hash-not-credential-grep",
     "Verify a staged diff by hash", "claims"),
    # no known prefix, must fall through to content
    ("alteryx-static-audits-miss-runtime-defects",
     "A clean compile passes on code that never ran", "other"),
]

NEGATIVE = [
    # substrings that must NOT drag a key into the wrong surface
    ("skill-profile-tuning", "tuning a profile", "skills",
     "'profile' must not match the files pattern"),
    ("memory-two-stores-drift", "two stores disagree", "memory",
     "'stores' must not match anything in files"),
    ("git-repo-clean-not-dirty", "read the actual status", "git",
     "'clean' must not pull it elsewhere"),
]



def _fixture(n=30):
    """n entries, every one carrying an authored Rule.

    MUST exceed the old default of 24, or a default-limit regression cannot
    make this test fail - which is precisely what happened the first time
    this guard was written with a 2-rule fixture.
    """
    head = "# Lessons\n\n## Failures\n"
    body = "".join(
        "\n### Entry {i}\n"
        "- **Pattern-Key:** bridge-entry-{i}\n"
        "- **Date:** 2026-01-01\n"
        "- **Trigger:** failure\n"
        "- **Rule:** Rule number {i}.\n"
        "- **Hits:** {h}\n"
        "- **Failed:** x\n- **Why:** y\n- **Worked:** z\n"
        "- **Evidence:** measured\n".format(i=i, h=3 if i == 0 else 2)
        for i in range(n))
    return head + body


def _fixture_singlehit(n=4):
    """Entries at Hits: 1 with no PIN. The always-on tier must exclude these."""
    head = "# Lessons\n\n## Failures\n"
    body = "".join(
        "\n### Single {i}\n"
        "- **Pattern-Key:** bridge-single-{i}\n"
        "- **Date:** 2026-01-01\n"
        "- **Trigger:** failure\n"
        "- **Rule:** Single rule {i}.\n"
        "- **Hits:** 1\n"
        "- **Failed:** x\n- **Why:** y\n- **Worked:** z\n"
        "- **Evidence:** measured\n".format(i=i)
        for i in range(n))
    return head + body


FIXTURE = _fixture()
FIXTURE_N = 30


def digest_cases():
    """The default must never SILENTLY drop a rule that belongs always-on.

    Regression guard for lessons-digest-default-limit-truncates: --limit
    defaulted to 24 while the live block held 30, so running the command
    exactly as SKILL.md documents it would have deleted 8 live rules.

    Tiering (2026-08-31) changed WHICH rules the default emits - the
    always-on tier rather than every authored Rule - but not this guard's
    point: a drop must be stated, never silent. So every fixture entry is a
    repeat, which puts the whole fixture in the tier and keeps this suite
    measuring --limit truncation rather than tier selection. Tier selection
    is covered by the case below and by lesson_gate_selftest.
    """
    import subprocess, tempfile, os
    here = os.path.dirname(os.path.abspath(__file__))
    fd, path = tempfile.mkstemp(suffix=".md")
    os.write(fd, FIXTURE.encode()); os.close(fd)
    out = []
    try:
        def run(*extra):
            return subprocess.run(
                [sys.executable, os.path.join(here, "lesson_brief.py"), path,
                 "--digest", *extra],
                capture_output=True, text=True)

        r = run()
        n = len([l for l in r.stdout.splitlines() if l.startswith("- ")])
        out.append((n == FIXTURE_N, "default emits every always-on rule",
                    f"{n} of {FIXTURE_N}"))

        # NEGATIVE CONTROL for tiering: single-hit, unpinned rules must NOT
        # reach the always-on block. Without this, a tier selection that
        # quietly kept everything would pass the whole suite.
        fd2, path2 = tempfile.mkstemp(suffix=".md")
        os.write(fd2, _fixture_singlehit().encode()); os.close(fd2)
        try:
            r2 = subprocess.run(
                [sys.executable, os.path.join(here, "lesson_brief.py"), path2,
                 "--digest"], capture_output=True, text=True)
            n2 = len([l for l in r2.stdout.splitlines() if l.startswith("- ")])
            out.append((n2 == 0,
                        "single-hit unpinned rules stay OUT of always-on",
                        f"{n2} emitted, expected 0"))
        finally:
            os.unlink(path2)

        r = run("--limit", "1")
        n = len([l for l in r.stdout.splitlines() if l.startswith("- ")])
        out.append((n == 1, "--limit still caps when asked", f"{n} of 1"))
        out.append(("WARNING" in r.stderr and "bridge-entry-" in r.stderr,
                    "truncation warns and names the dropped key",
                    r.stderr.strip()[:60] or "no warning"))
    finally:
        os.unlink(path)
    return out


def main():
    print("=" * 60)
    print("POSITIVE CONTROL")
    print("=" * 60)
    ok = surface_of("bridge-anything", "a bridge thing") == "bridge"
    if not ok:
        print("  POSITIVE CONTROL FAILED - suite aborted")
        return 1
    print("  classifier resolves a known prefix\n")

    print("=" * 60)
    print(f"CASES ({len(CASES) + len(NEGATIVE)})")
    print("=" * 60)
    passed = 0
    total = 0
    for key, title, want in CASES:
        total += 1
        got = surface_of(key, title)
        if got == want:
            passed += 1
            print(f"  OK    {key[:46]:48} -> {got}")
        else:
            print(f"  FAIL  {key[:46]:48} -> {got}, wanted {want}")

    for key, title, want, why in NEGATIVE:
        total += 1
        got = surface_of(key, title)
        if got == want:
            passed += 1
            print(f"  OK    {key[:46]:48} -> {got}   ({why})")
        else:
            print(f"  FAIL  {key[:46]:48} -> {got}, wanted {want}   ({why})")

    print()
    print("DIGEST TRUNCATION GUARD")
    print("-" * 60)
    for ok, what, detail in digest_cases():
        total += 1
        passed += 1 if ok else 0
        print(f"  {'OK  ' if ok else 'FAIL'}  {what:52} {detail}")

    print()
    print("=" * 60)
    print(f"RESULT: {passed}/{total}")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
