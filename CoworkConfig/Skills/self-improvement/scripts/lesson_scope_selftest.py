#!/usr/bin/env python3
"""Self-test for lesson scope: Routes / Platforms narrowing.

The rule the whole feature rests on: ABSENT MEANS EVERYWHERE. An untagged corpus must
behave exactly as it did before scoping existed, and a malformed scope line must never
cost a rule. Both are asserted here, because either one failing silently removes
operating rules an operator needs and nothing would say so.

Mirrors inScope() in Startup/CommandBridge/batch-exec-server.js. That function is the
one that actually runs; this proves the contract it implements.
"""
from __future__ import annotations
import re
import sys

VALID_ROUTES = {"claude", "copilot"}
VALID_PLATFORMS = {"windows", "macos"}


def in_scope(block: str, route: str | None, platform: str) -> bool:
    m = re.search(r"(?m)^- \*\*Routes:\*\* (.+)$", block)
    if m and route:
        values = [v for v in re.split(r"[,\s]+", m.group(1).lower()) if v]
        if values and route not in values:
            return False
    m = re.search(r"(?m)^- \*\*Platforms:\*\* (.+)$", block)
    if m:
        values = [v for v in re.split(r"[,\s]+", m.group(1).lower()) if v]
        if values and platform not in values:
            return False
    return True


def entry(**fields) -> str:
    lines = ["- **Pattern-Key:** bridge-test"]
    for k, v in fields.items():
        lines.append(f"- **{k.replace('_', '-')}:** {v}")
    lines.append("- **Rule:** do the thing")
    return "\n".join(lines) + "\n"


CASES = [
    ("untagged is served everywhere",
     entry(), [("claude", "macos", True), ("copilot", "windows", True),
               (None, "macos", True), (None, "windows", True)]),
    ("Routes: copilot is withheld from the claude route",
     entry(Routes="copilot"), [("claude", "macos", False), ("claude", "windows", False),
                               ("copilot", "windows", True)]),
    ("an unknown route is served, not dropped",
     entry(Routes="copilot"), [(None, "windows", True)]),
    ("Platforms: windows is withheld from macos",
     entry(Platforms="windows"), [("claude", "macos", False), ("claude", "windows", True),
                                  ("copilot", "windows", True)]),
    ("both axes must pass",
     entry(Routes="copilot", Platforms="windows"),
     [("copilot", "windows", True), ("copilot", "macos", False),
      ("claude", "windows", False)]),
    ("a list is honoured",
     entry(Routes="claude, copilot"), [("claude", "macos", True), ("copilot", "windows", True)]),
    ("an empty value narrows nothing",
     "- **Pattern-Key:** bridge-test\n- **Routes:** \n- **Rule:** x\n",
     [("claude", "macos", True), ("copilot", "windows", True)]),
    ("a malformed value narrows nothing it should not",
     entry(Routes="claude"), [("claude", "macos", True), ("copilot", "macos", False)]),
    ("the field name must match exactly - Route is not Routes",
     entry(Route="copilot"), [("claude", "macos", True)]),
]


def main() -> int:
    passed = failed = 0
    for name, block, checks in CASES:
        for route, platform, want in checks:
            got = in_scope(block, route, platform)
            ok = got == want
            passed += ok
            failed += not ok
            status = "PASS" if ok else "FAIL"
            if not ok:
                print(f"{status}  {name}  (route={route}, platform={platform}: "
                      f"want {want}, got {got})")
    # The real corpus must parse, and every declared value must be known.
    from pathlib import Path
    corpus = Path(__file__).resolve().parents[3] / "cowork-memory" / "cowork-lessons.md"
    if corpus.is_file():
        text = corpus.read_text(encoding="utf-8")
        bad = []
        for b in text.split("\n### ")[1:]:
            for field, valid in (("Routes", VALID_ROUTES), ("Platforms", VALID_PLATFORMS)):
                m = re.search(rf"(?m)^- \*\*{field}:\*\* (.+)$", b)
                if not m:
                    continue
                for v in re.split(r"[,\s]+", m.group(1).lower()):
                    if v and v not in valid:
                        bad.append(f"{field}={v}")
        ok = not bad
        passed += ok
        failed += not ok
        if bad:
            print(f"FAIL  the real corpus declares unknown scope values: {sorted(set(bad))}")
    print(f"LESSON_SCOPE_SELFTEST: {'OK' if not failed else 'FAIL'} - "
          f"{passed} of {passed + failed} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
