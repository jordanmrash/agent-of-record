#!/usr/bin/env python3
"""Run the repository's integrity checks, the demonstration, and the negative-control self-tests.

    python scripts/release_check.py                 # human-readable table
    python scripts/release_check.py --json out.json # also write machine-readable results

Exit 0 means every check passed. The JSON file carries one record per check with
its name, result, duration and last output line, plus the git commit when one is
available, so a release can be tied to the exact run that validated it.
"""

from __future__ import annotations

import json
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
    Check("bridge facts", [sys.executable, str(ROOT / "scripts" / "facts_check.py")]),
    # The measured table in README.md and docs/measured-results.md is generated from the tree;
    # a stale block fails here instead of drifting for a release (123 vs 120 entries, 2026-09-15).
    Check("measured table currency", [sys.executable, str(ROOT / "scripts" / "measured_table.py"), "--check"]),
    # Operating text addresses "the operator", never the author by name; attribution is exempt.
    Check("operator name scan", [sys.executable, str(ROOT / "scripts" / "operator_name_check.py")]),
    # The plugin manifest's own validation, without writing a bundle: --list exits 3 when a
    # manifest entry has no skill directory or, under --strict, when a skill declared for
    # macOS carries Windows-only text. Item 6 asked for this to be wired into CI; CI runs
    # this file, so this is the wire.
    Check(
        "skill plugin manifest",
        [sys.executable, str(ROOT / "scripts" / "build_plugin.py"), "--strict", "--list"],
    ),
    Check(
        "synthetic control loop",
        [sys.executable, str(ROOT / "examples" / "synthetic-control-loop" / "run.py"), "--check"],
    ),
]

# Self-tests that live beside the public scripts rather than under the skill.
ROOT_SELFTESTS = [
    ROOT / "scripts" / "facts_check_selftest.py",
    ROOT / "scripts" / "personalize_selftest.py",
    # Starts the command bridge as a real stdio MCP server and tries to escape
    # it. Runs the platform's own script shape, so the same suite covers the
    # Windows machine that publishes and the Mac that contributes.
    ROOT / "scripts" / "exec_bridge_selftest.py",
    # Positive and negative controls for the --strict matcher: every Windows-only
    # pattern fires on a sentence that means it, and none fires on a lesson key,
    # a route id or a near-miss. The gate that guards the plugin is itself gated.
    ROOT / "scripts" / "build_plugin_selftest.py",
    ROOT / "scripts" / "measured_table_selftest.py",
    ROOT / "scripts" / "operator_name_check_selftest.py",
]

SELFTESTS = [
    "lesson_check_selftest.py",
    "lesson_scope_selftest.py",
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


def git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False
        )
    except OSError:
        return None
    return out.stdout.strip() or None if out.returncode == 0 else None


def write_json(path: str, results: list[tuple[str, bool, float, str]], failures: int) -> None:
    payload = {
        "repository": "agent-of-record",
        "commit": git_commit(),
        "checks": [
            {"name": name, "passed": ok, "seconds": round(seconds, 2), "last_line": last}
            for name, ok, seconds, last in results
        ],
        "total": len(results),
        "failures": failures,
        "clean": failures == 0,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")


def main(argv: list[str]) -> int:
    json_path = None
    if "--json" in argv:
        i = argv.index("--json")
        if i + 1 >= len(argv):
            print("usage: release_check.py [--json <file>]")
            return 2
        json_path = argv[i + 1]

    results: list[tuple[str, bool, float, str]] = []
    for check in CHECKS:
        ok, seconds, last = run(check)
        results.append((check.name, ok, seconds, last))

    for script in SELFTESTS:
        check = Check(f"self-test: {script}", py(script))
        ok, seconds, last = run(check)
        results.append((check.name, ok, seconds, last))

    for path in ROOT_SELFTESTS:
        check = Check(f"self-test: {path.name}", [sys.executable, str(path)])
        ok, seconds, last = run(check)
        results.append((check.name, ok, seconds, last))

    width = max(len(name) for name, *_ in results)
    failures = 0
    for name, ok, seconds, last in results:
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"{status:4s}  {name:<{width}}  {seconds:6.1f}s  {last}")

    if json_path:
        write_json(json_path, results, failures)
        print(f"results written to {json_path}")

    if failures:
        print(f"RELEASE_CHECK: {failures} FAILURE(S)")
        return 1
    print(f"RELEASE_CHECK: CLEAN ({len(results)} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
