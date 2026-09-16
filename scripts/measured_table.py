#!/usr/bin/env python3
"""Generate or check the measured-results table that README.md and docs/measured-results.md share.

Every figure is computed from the tree. Nothing in the table is typed by hand, so it cannot drift
from the corpus the way the hand-maintained one did - 123 entries against 120, 93 rules against 94,
13 self-test suites against the 15 the gate ran, measured on the published tree on 2026-09-15.

    python scripts/measured_table.py --check    # exit 1 if either block is stale; the gate runs this
    python scripts/measured_table.py --write    # regenerate both blocks in place
    python scripts/measured_table.py            # print the table

Sources
  entries / rules / always-on   the LESSON-DIGEST end marker in CoworkConfig/copilot-instructions.md,
                                which digest_apply.py --check already proves current against the corpus
  routed keys / routed skills   the Pattern-Keys in the corpus matched against the prefix and exact
                                routes in skill_lesson_routes.json and plugin_lesson_routes.json
  self-tests / gate checks      the lists release_check.py itself runs
  behavioral verdicts           CoworkConfig/cowork-memory/verification-ledger.json, superseded records excluded
  enforcement tiers             ENFORCED and PARTIAL lines in digest-tiers.txt

Exit codes: 0 current (or written), 1 stale or a marker is missing, 2 a source could not be read.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

START = "<!-- MEASURED:start -->"
END = "<!-- MEASURED:end -->"
TARGETS = ("README.md", "docs/measured-results.md")

DIGEST_END = re.compile(r"<!-- LESSON-DIGEST:END - (\d+) always-on of (\d+) rules from (\d+) entries -->")
PATTERN_KEY = re.compile(r"^- \*\*Pattern-Key:\*\*\s*(\S+)", re.M)


def fail(msg: str, code: int = 2) -> None:
    print(f"FAIL  {msg}")
    sys.exit(code)


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"cannot read {path}: {exc}")
    return ""


def route_targets(node, out: list) -> None:
    """Every dict carrying a prefix or exact list is one routing target, wherever it sits."""
    if isinstance(node, dict):
        if isinstance(node.get("prefix"), list) or isinstance(node.get("exact"), list):
            out.append(node)
        for key, value in node.items():
            if not str(key).startswith("_"):
                route_targets(value, out)
    elif isinstance(node, list):
        for item in node:
            route_targets(item, out)


def matched(target: dict, keys: set) -> set:
    prefixes = tuple(target.get("prefix") or [])
    exact = set(target.get("exact") or [])
    return {k for k in keys if k in exact or (prefixes and k.startswith(prefixes))}


def load_release_check(root: Path):
    path = root / "scripts" / "release_check.py"
    spec = importlib.util.spec_from_file_location("aor_release_check", path)
    if spec is None or spec.loader is None:
        fail(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve the class's module through sys.modules
    spec.loader.exec_module(module)
    return module


def measure(root: Path) -> list:
    config = root / "CoworkConfig"
    scripts = config / "Skills" / "self-improvement" / "scripts"

    digest = DIGEST_END.search(read(config / "copilot-instructions.md"))
    if not digest:
        fail("no LESSON-DIGEST end marker in CoworkConfig/copilot-instructions.md")
    always_on, rules, entries = (int(digest.group(i)) for i in (1, 2, 3))

    keys = set(PATTERN_KEY.findall(read(config / "cowork-memory" / "cowork-lessons.md")))

    skill_targets: list = []
    route_targets(json.loads(read(scripts / "skill_lesson_routes.json")), skill_targets)
    skill_hits = [matched(t, keys) for t in skill_targets]
    skill_keys = set().union(*skill_hits) if skill_hits else set()
    routed_skills = sum(1 for hit in skill_hits if hit)

    plugin_targets: list = []
    route_targets(json.loads(read(scripts / "plugin_lesson_routes.json")), plugin_targets)
    plugin_hits = [matched(t, keys) for t in plugin_targets]
    plugin_keys = set().union(*plugin_hits) if plugin_hits else set()

    gate = load_release_check(root)
    selftests = len(gate.SELFTESTS) + len(gate.ROOT_SELFTESTS)
    checks = len(gate.CHECKS) + selftests

    ledger = json.loads(read(config / "cowork-memory" / "verification-ledger.json"))
    live = [r for r in ledger if isinstance(r, dict) and "_superseded" not in r]
    effective = len({r.get("key") for r in live if r.get("verdict") == "EFFECTIVE"})
    inert = len({r.get("key") for r in live if r.get("verdict") == "INERT"})

    tiers = read(config / "Skills" / "self-improvement" / "digest-tiers.txt").splitlines()
    enforced = sum(1 for line in tiers if line.startswith("ENFORCED "))
    partial = sum(1 for line in tiers if line.startswith("PARTIAL "))

    return [
        ("Recorded lesson entries", entries),
        ("Entries with an authored rule", rules),
        ("Rules in the always-on tier", always_on),
        ("Lesson keys routed into skills", len(skill_keys)),
        ("Lesson keys routed into plugin tools", len(plugin_keys)),
        ("Routed skills", routed_skills),
        ("Self-test suites run by the gate", selftests),
        ("Checks in the release gate", checks),
        ("Behaviorally verified effective rules", effective),
        ("Behaviorally verified inert rules", inert),
        ("Rules a checker enforces on some surfaces and is blind on others", partial),
        ("Rules proven fully enforced across every behavior surface", enforced),
    ]


def render(rows: list) -> str:
    lines = [START, "| Measure | Result |", "|---|---:|"]
    lines += [f"| {name} | {value} |" for name, value in rows]
    lines += ["", "<sub>Generated by `scripts/measured_table.py`; the release gate fails when this table is stale.</sub>", END]
    return "\n".join(lines)


def splice(text: str, block: str, name: str) -> str:
    start = text.find(START)
    end = text.find(END)
    if start < 0 or end < 0 or end < start:
        fail(f"{name}: MEASURED markers missing or out of order", 1)
    return text[:start] + block + text[end + len(END):]


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    rows = measure(root)
    block = render(rows)
    if not (args.check or args.write):
        print(block)
        return 0

    stale = []
    for rel in TARGETS:
        path = root / rel
        text = read(path)
        current = splice(text, block, rel)
        if current != text:
            stale.append(rel)
            if args.write:
                with open(path, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(current)
                print(f"wrote  {rel}")
    if args.write:
        print(f"MEASURED_TABLE: WRITTEN ({len(stale)} file(s) changed)")
        return 0
    for rel in stale:
        print(f"STALE  {rel}")
    if stale:
        print(f"MEASURED_TABLE: STALE ({len(stale)} of {len(TARGETS)} blocks) - run scripts/measured_table.py --write")
        return 1
    print(f"MEASURED_TABLE: CURRENT ({len(TARGETS)} blocks, {len(rows)} measures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
