#!/usr/bin/env python3
"""
lesson_gate_selftest.py - prove every gate in lesson_gate.py can FAIL.

A gate that has never been observed failing is decoration. Each case below
either (a) builds a clean fixture and asserts exit 0, or (b) sabotages exactly
one thing and asserts the specific gate fires. If a sabotage case passes, the
gate is not wired to anything and the suite says so.

Run:  python lesson_gate_selftest.py
Exit: 0 all cases passed, 1 otherwise
"""

import io
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "lesson_gate.py")
BRIEF = os.path.join(HERE, "lesson_brief.py")

LESSONS = """# Lessons

### A bridge probe is a timestamp
- **Pattern-Key:** bridge-probe-is-a-timestamp
- **Date:** 2026-08-28
- **Hits:** 2
- **Rule:** Re-probe later before calling a bridge down.
- **Worked:** waited 90s and probed again.

### Batch files need CRLF
- **Pattern-Key:** bridge-lf-breaks-label
- **Date:** 2026-08-20
- **Hits:** 1
- **Rule:** Write .bat with CRLF or GOTO labels break.
- **Worked:** converted line endings.

### Commit before closing
- **Pattern-Key:** git-commit-before-close
- **Date:** 2026-08-24
- **Hits:** 1
- **Rule:** Stage and commit at session close.
- **Worked:** ran the bookend.
"""

# Same content, plus one bridge entry hit twice with NO Rule line.
LESSONS_REPEAT_UNRULED = LESSONS + """
### Tunnel drops look like bridge failure
- **Pattern-Key:** bridge-tunnel-drop-misread
- **Date:** 2026-08-21
- **Hits:** 3
- **Worked:** measured the local leg separately and it was clean.
"""

results = []


def record(name, ok, detail=""):
    results.append((name, ok, detail))
    print("%-52s %s%s" % (name, "PASS" if ok else "FAIL",
                          "" if ok else "  <- " + detail))


def build(tmp, lessons_text, digest=True, mangle=None):
    """Create a fixture dir with lessons + instructions. Returns paths."""
    shutil.copy(BRIEF, tmp)
    shutil.copy(GATE, tmp)
    lp = os.path.join(tmp, "cowork-lessons.md")
    ip = os.path.join(tmp, "copilot-instructions.md")
    with open(lp, "w", encoding="utf-8") as fh:
        fh.write(lessons_text)

    body = "# Instructions\n\nSome preamble.\n\n"
    if digest:
        out = subprocess.run([sys.executable, "lesson_brief.py",
                              "cowork-lessons.md", "--digest"],
                             cwd=tmp, capture_output=True, text=True)
        block = out.stdout
        if mangle:
            block = mangle(block)
        body += block
    with open(ip, "w", encoding="utf-8") as fh:
        fh.write(body)
    return lp, ip


def run(tmp, *args):
    return subprocess.run([sys.executable, "lesson_gate.py"] + list(args),
                          cwd=tmp, capture_output=True, text=True)


def case_clean_passes():
    with tempfile.TemporaryDirectory() as tmp:
        build(tmp, LESSONS)
        r = run(tmp, "preflight", "--surface", "bridge", "--session", "s1")
        record("clean fixture -> exit 0", r.returncode == 0,
               r.stdout + r.stderr)
        record("clean fixture prints the bridge rules",
               "Re-probe later" in r.stdout, r.stdout)
        record("clean fixture does NOT leak git rules",
               "session close" not in r.stdout, r.stdout)


def case_g1_missing_block():
    with tempfile.TemporaryDirectory() as tmp:
        build(tmp, LESSONS, digest=False)
        r = run(tmp, "preflight", "--surface", "bridge", "--session", "s1")
        record("G1 missing digest block -> exit 1", r.returncode == 1, r.stdout)
        record("G1 names the right gate", "G1" in r.stdout, r.stdout)


def case_g2_stale_counts():
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip = build(tmp, LESSONS)
        # Sabotage: add a lesson AFTER the digest was generated.
        with open(lp, "a", encoding="utf-8") as fh:
            fh.write("\n### New finding\n- **Pattern-Key:** bridge-new-thing\n"
                     "- **Date:** 2026-08-29\n- **Hits:** 1\n"
                     "- **Rule:** Something new and unloaded.\n"
                     "- **Worked:** n/a\n")
        r = run(tmp, "preflight", "--surface", "bridge", "--session", "s1")
        record("G2 stale digest -> exit 1", r.returncode == 1, r.stdout)
        record("G2 names the right gate", "G2" in r.stdout, r.stdout)
        record("G2 reports both counts",
               "advertises" in r.stdout and "now holds" in r.stdout
               or "lessons file now holds" in r.stdout, r.stdout)


def case_g3_body_edited():
    def mangle(block):
        return block.replace("Re-probe later before calling a bridge down.",
                             "Re-probe whenever, honestly.")
    with tempfile.TemporaryDirectory() as tmp:
        build(tmp, LESSONS, mangle=mangle)
        r = run(tmp, "preflight", "--surface", "bridge", "--session", "s1")
        record("G3 hand-edited digest body -> exit 1", r.returncode == 1, r.stdout)
        record("G3 names the right gate", "G3" in r.stdout, r.stdout)


def case_g4_repeat_offender_unruled():
    with tempfile.TemporaryDirectory() as tmp:
        build(tmp, LESSONS_REPEAT_UNRULED)
        r = run(tmp, "preflight", "--surface", "bridge", "--session", "s1")
        record("G4 repeat offender with no Rule -> exit 1",
               r.returncode == 1, r.stdout)
        record("G4 names the offending key",
               "bridge-tunnel-drop-misread" in r.stdout, r.stdout)
        # Same fixture, different surface: git is clean, must NOT fail.
        r2 = run(tmp, "preflight", "--surface", "git", "--session", "s1")
        record("G4 does not punish an unrelated surface",
               r2.returncode == 0, r2.stdout)


def case_g5_warns_only():
    lessons = LESSONS.replace(
        "- **Rule:** Write .bat with CRLF or GOTO labels break.\n", "")
    with tempfile.TemporaryDirectory() as tmp:
        build(tmp, lessons)
        r = run(tmp, "preflight", "--surface", "bridge", "--session", "s1")
        record("G5 single-hit unruled warns but exits 0",
               r.returncode == 0, r.stdout)
        record("G5 emits a WARN line", "WARN" in r.stdout, r.stdout)


def case_verify_requires_receipt():
    with tempfile.TemporaryDirectory() as tmp:
        build(tmp, LESSONS)
        r = run(tmp, "verify", "--surface", "bridge", "--session", "s1")
        record("verify without preflight -> exit 1", r.returncode == 1, r.stdout)
        run(tmp, "preflight", "--surface", "bridge", "--session", "s1")
        r2 = run(tmp, "verify", "--surface", "bridge", "--session", "s1")
        record("verify after preflight -> exit 0", r2.returncode == 0, r2.stdout)
        r3 = run(tmp, "verify", "--surface", "git", "--session", "s1")
        record("receipt does not cover a different surface",
               r3.returncode == 1, r3.stdout)
        r4 = run(tmp, "verify", "--surface", "bridge", "--session", "s2")
        record("receipt does not cover a different session",
               r4.returncode == 1, r4.stdout)


def case_verify_detects_digest_change():
    with tempfile.TemporaryDirectory() as tmp:
        lp, ip = build(tmp, LESSONS)
        run(tmp, "preflight", "--surface", "bridge", "--session", "s1")
        with open(ip, "a", encoding="utf-8") as fh:
            fh.write("\n")  # outside the block: must NOT trip
        r_ok = run(tmp, "verify", "--surface", "bridge", "--session", "s1")
        record("verify ignores edits outside the digest block",
               r_ok.returncode == 0, r_ok.stdout)
        text = open(ip, encoding="utf-8").read().replace(
            "Re-probe later before calling a bridge down.", "Ignore this rule.")
        open(ip, "w", encoding="utf-8").write(text)
        r = run(tmp, "verify", "--surface", "bridge", "--session", "s1")
        record("verify catches a digest edited after the receipt",
               r.returncode == 1, r.stdout)


def case_unknown_surface():
    with tempfile.TemporaryDirectory() as tmp:
        build(tmp, LESSONS)
        r = run(tmp, "preflight", "--surface", "nonsense", "--session", "s1")
        record("unknown surface -> exit 1 (no silent pass)",
               r.returncode == 1, r.stdout)


def case_missing_file():
    with tempfile.TemporaryDirectory() as tmp:
        build(tmp, LESSONS)
        os.remove(os.path.join(tmp, "copilot-instructions.md"))
        r = run(tmp, "preflight", "--surface", "bridge", "--session", "s1")
        record("unreadable input -> exit 2, not 0", r.returncode == 2,
               "%s / %s" % (r.returncode, r.stderr))


def case_audit_runs():
    with tempfile.TemporaryDirectory() as tmp:
        build(tmp, LESSONS_REPEAT_UNRULED)
        r = run(tmp, "audit")
        record("audit reports a blocked surface",
               r.returncode == 0 and "GATE FAILS" in r.stdout, r.stdout)


def case_receipt_dir_unwritable():
    """An unwritable receipt dir is an ENVIRONMENT fault, not a rule failure.

    Before 2026-09-01 this raised OSError Errno 30 and exited 1, and exit 1 is
    defined as "stop". A read-only mount therefore read as a lessons failure
    and would have halted a close.

    The sabotage is portable on purpose: point --receipt-dir at a path whose
    parent is a regular FILE, so os.makedirs raises on Windows and POSIX alike.
    chmod would NOT do it - on Windows the owner keeps write access to a
    read-only directory, so the case would pass for the wrong reason on the
    very machine that runs the nightly job.
    """
    with tempfile.TemporaryDirectory() as tmp:
        build(tmp, LESSONS)
        blocker = os.path.join(tmp, "notadir")
        with open(blocker, "w", encoding="utf-8") as fh:
            fh.write("I am a file, not a directory.")
        r = run(tmp, "preflight", "--surface", "bridge", "--session", "s1",
                "--receipt-dir", os.path.join(blocker, "sub"))
        record("unwritable receipt dir -> exit 2, not 1",
               r.returncode == 2, "%s / %s" % (r.returncode, r.stdout))
        record("unwritable receipt dir still printed the rules",
               "Rules in force" in r.stdout, r.stdout)
        record("unwritable receipt dir is NOT reported as GATE FAILED",
               "GATE FAILED" not in r.stdout, r.stdout)


def case_default_receipt_dir_is_cwd_local():
    """The default must stay per-cwd, or the sabotage cases stop firing.

    If the default ever becomes one shared absolute directory, the receipt
    case_clean_passes writes would satisfy case_verify_requires_receipt, which
    asserts verify FAILS when nothing was loaded. That case would then pass on
    known-broken code. This asserts the isolation property directly rather than
    leaving it as an assumption.
    """
    with tempfile.TemporaryDirectory() as tmp:
        build(tmp, LESSONS)
        r = run(tmp, "preflight", "--surface", "bridge", "--session", "s1")
        local = os.path.join(tmp, ".lesson-receipts")
        record("default receipt dir resolves under the current directory",
               r.returncode == 0 and os.path.isdir(local)
               and len(os.listdir(local)) == 1,
               "%s / %s" % (r.returncode, r.stdout))


def main():
    for fn in (case_clean_passes, case_g1_missing_block, case_g2_stale_counts,
               case_g3_body_edited, case_g4_repeat_offender_unruled,
               case_g5_warns_only, case_verify_requires_receipt,
               case_verify_detects_digest_change, case_unknown_surface,
               case_missing_file, case_audit_runs,
               case_receipt_dir_unwritable,
               case_default_receipt_dir_is_cwd_local):
        fn()
    failed = [r for r in results if not r[1]]
    print("\n%d/%d cases passed" % (len(results) - len(failed), len(results)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
