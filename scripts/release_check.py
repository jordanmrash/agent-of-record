#!/usr/bin/env python3
"""Run the repository's integrity checks and negative-control self-tests."""

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "CoworkConfig" / "Skills" / "self-improvement" / "scripts"
LESSONS = ROOT / "CoworkConfig" / "cowork-memory" / "cowork-lessons.md"
INSTRUCTIONS = ROOT / "CoworkConfig" / "copilot-instructions.md"
SKILLS = ROOT / "CoworkConfig" / "Skills"
TIERS = SKILLS / "self-improvement" / "digest-tiers.txt"
STARTUP = ROOT / "Startup"


@dataclass(frozen=True)
class Check:
    name: str
    command: list[str]
    timeout: int = 180


def py(script: str, *args: str) -> list[str]:
    return [sys.executable, str(SCRIPTS / script), *map(str, args)]


CHECKS = [
    Check("public disclosure scan", [sys.executable, str(ROOT / "scripts" / "public_scan.py")]),
    Check("lesson integrity", py("lesson_check.py", LESSONS)),
    Check(
        "digest currency",
        py(
            "digest_apply.py",
            "--lessons", LESSONS,
            "--instructions", INSTRUCTIONS,
            "--check",
        ),
    ),
    Check(
        "skill delivery currency",
        py(
            "skill_lessons.py",
            "--lessons", LESSONS,
            "--skills-dir", SKILLS,
            "--routes", SCRIPTS / "skill_lesson_routes.json",
            "--check",
        ),
    ),
    Check(
        "plugin delivery currency",
        py(
            "plugin_lessons.py",
            "--lessons", LESSONS,
            "--servers-dir", STARTUP,
            "--routes", SCRIPTS / "plugin_lesson_routes.json",
            "--check",
        ),
    ),
    Check(
        "scope claims",
        py("scope_check.py", TIERS, "--scripts", SCRIPTS),
    ),
    Check(
        "surface audit",
        py(
            "lesson_gate.py",
            "audit",
            "--lessons", LESSONS,
            "--instructions", INSTRUCTIONS,
        ),
    ),
]

SELFTESTS = [
    "lesson_check_selftest.py",
    "lesson_gate_selftest.py",
    "job_lint_selftest.py",
    "scope_check_selftest.py",
    "plugin_lessons_selftest.py",
    "verify_delivery_selftest.py",
    "dream_analyze_selftest.py",
    "nightly_selftest.py",
    "lesson_dupe_selftest.py",
    "lesson_brief_selftest.py",
]


def run(check: Check) -> tuple[bool, float, str]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            check.command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=check.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, time.monotonic() - started, "timed out"

    output = (result.stdout + "\n" + result.stderr).strip()
    last = output.splitlines()[-1] if output else "(no output)"
    return result.returncode == 0, time.monotonic() - started, last


def main() -> int:
    results: list[tuple[str, bool, float, str]] = []
    for check in CHECKS:
        ok, seconds, last = run(check)
        results.append((check.name, ok, seconds, last))

    for script in SELFTESTS:
        check = Check(f"self-test: {script}", py(script))
        ok, seconds, last = run(check)
        results.append((check.name, ok, seconds, last))

    width = max(len(name) for name, *_ in results)
    failures = 0
    for name, ok, seconds, last in results:
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"{status:4s}  {name:<{width}}  {seconds:6.1f}s  {last}")

    if failures:
        print(f"RELEASE_CHECK: {failures} FAILURE(S)")
        return 1
    print(f"RELEASE_CHECK: CLEAN ({len(results)} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
