#!/usr/bin/env python3
"""Package CoworkConfig/Skills into an installable Claude Cowork .plugin.

Why this exists
---------------
The repo's only skill-install mechanism was syncing CoworkConfig/Skills into
$COWORK_CONFIG_ROOT/skills, which is a Copilot Cowork location. Nothing
installed a skill into Claude Cowork on either platform. Copying skills into
~/.claude/skills/ looks right and does nothing -- a directory drop is not an
install. The mechanism that works is a plugin: a directory holding
.claude-plugin/plugin.json plus skills/<name>/SKILL.md, zipped to a .plugin
file the user accepts in-app.

This script makes that artifact reproducible instead of hand-assembled.

Usage
-----
    python3 scripts/build_plugin.py                     # build for both platforms
    python3 scripts/build_plugin.py --platform macos    # only macOS-declared skills
    python3 scripts/build_plugin.py --strict            # fail on Windows-only text
    python3 scripts/build_plugin.py --list              # show what would ship

Exit codes: 0 ok, 2 usage/manifest error, 3 validation failure.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_SRC = ROOT / "CoworkConfig" / "Skills"
MANIFEST = ROOT / "CoworkConfig" / "plugin" / ".claude-plugin" / "plugin.json"
OUT_DIR = ROOT / "Outputs" / "Skills Plugin"

# The same signals the acceptance test greps for. A skill declared as
# macos-supported must not contain any of these.
WINDOWS_ONLY = [
    (re.compile(r"\bcd /d\b"), "cd /d"),
    (re.compile(r"\breg query\b", re.I), "reg query"),
    (re.compile(r"C:\\\\Users|C:\\Users"), r"C:\Users"),
    (re.compile(r"\.bat\b"), ".bat"),
    (re.compile(r"\bdevtunnel\b", re.I), "devtunnel"),
    # A port number standing in prose ("port 8933", "(8933)", "8931/8932/8933"), not a
    # digit run inside a hyphenated identifier. `bridge-8933-arg-name` is a lesson key,
    # `command-bridge-8933` a route id, `bridge-8931-` a route prefix: names, not claims
    # about a platform, and a key may never be renamed to satisfy a gate. Measured
    # 2026-09-14: 71 of 141 port hits across the ten skills were identifiers.
    (re.compile(r"(?<![\w-])893[1-4](?![\w-])"), "bridge port"),
    # The Copilot connector ids exist only on the Windows hosted route. They carry a port
    # digit the rule above now ignores, so they are named on their own.
    (re.compile(r"\bjordan-[a-z]+(?:-[a-z]+)*-893[1-4]-v\d+\b"), "Copilot connector id"),
]

FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def fail(msg: str, code: int = 3) -> None:
    print(f"FAIL  {msg}", file=sys.stderr)
    sys.exit(code)


def load_manifest() -> dict:
    if not MANIFEST.exists():
        fail(f"manifest not found: {MANIFEST.relative_to(ROOT)}", 2)
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"manifest is not valid JSON: {exc}", 2)
    return {}


def read_frontmatter(skill_md: Path) -> dict:
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    match = FRONTMATTER.match(text)
    if not match:
        return {}
    fields: dict[str, str] = {}
    key = None
    for line in match.group(1).splitlines():
        if re.match(r"^\s", line) and key:
            fields[key] += " " + line.strip()
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            fields[key] = value.strip()
    return fields


def scan_windows_text(skill_dir: Path) -> list[str]:
    hits: list[str] = []
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".md", ".txt", ".json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern, label in WINDOWS_ONLY:
            count = len(pattern.findall(text))
            if count:
                hits.append(f"{path.relative_to(skill_dir)}: {count}x {label}")
    return hits


def select(manifest: dict, platform: str | None) -> list[dict]:
    entries = manifest.get("skills")
    if not isinstance(entries, list) or not entries:
        fail("manifest has no 'skills' array -- nothing to package", 2)
    if platform is None:
        return entries
    chosen = [e for e in entries if platform in e.get("platforms", [])]
    if not chosen:
        fail(f"no skills declared for platform '{platform}'", 2)
    return chosen


def packaged_manifest(manifest: dict) -> dict:
    """Strip build-time keys so the shipped plugin.json carries only plugin metadata."""
    return {k: v for k, v in manifest.items() if not k.startswith("_") and k != "skills"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--platform", choices=["windows", "macos"], default=None,
                        help="package only skills declared for this platform (default: all)")
    parser.add_argument("--strict", action="store_true",
                        help="fail the build if a macos-declared skill contains Windows-only text")
    parser.add_argument("--list", action="store_true", help="report what would ship and exit")
    parser.add_argument("--out", type=Path, default=None, help="output .plugin path")
    args = parser.parse_args()

    if not SKILLS_SRC.is_dir():
        fail(f"skills source not found: {SKILLS_SRC.relative_to(ROOT)}", 2)

    manifest = load_manifest()
    entries = select(manifest, args.platform)

    problems: list[str] = []
    warnings: list[str] = []
    staged: list[tuple[str, Path]] = []

    for entry in entries:
        name = entry.get("name")
        if not name:
            problems.append("manifest entry with no 'name'")
            continue
        skill_dir = SKILLS_SRC / name
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            problems.append(f"{name}: SKILL.md not found at {skill_md.relative_to(ROOT)}")
            continue
        front = read_frontmatter(skill_md)
        for required in ("name", "description"):
            if not front.get(required):
                problems.append(f"{name}: SKILL.md frontmatter missing '{required}'")
        if front.get("name") and front["name"] != name:
            problems.append(f"{name}: frontmatter name is '{front['name']}' -- must match the directory")

        hits = scan_windows_text(skill_dir)
        if hits and "macos" in entry.get("platforms", []):
            message = f"{name}: declared macos but carries Windows-only text -> " + "; ".join(hits[:4])
            (problems if args.strict else warnings).append(message)

        staged.append((name, skill_dir))

    if args.list:
        for name, skill_dir in staged:
            files = sum(1 for p in skill_dir.rglob("*") if p.is_file())
            print(f"  {name:<20} {files:>3} file(s)")
        print(f"\n{len(staged)} skill(s) selected"
              + (f" for {args.platform}" if args.platform else ""))
        for warning in warnings:
            print(f"WARN  {warning}")
        # "What would ship" has to include what would STOP the build. A --list that
        # printed a clean roster over a manifest naming a missing skill was wrong.
        for problem in problems:
            print(f"FAIL  {problem}", file=sys.stderr)
        if problems:
            print(f"\n{len(problems)} problem(s) -- a build would refuse.", file=sys.stderr)
            return 3
        return 0

    for warning in warnings:
        print(f"WARN  {warning}")
    if problems:
        for problem in problems:
            print(f"FAIL  {problem}", file=sys.stderr)
        print(f"\n{len(problems)} problem(s) -- nothing was written.", file=sys.stderr)
        return 3

    suffix = f"-{args.platform}" if args.platform else ""
    out_path = args.out or (OUT_DIR / f"{manifest.get('name', 'skills')}{suffix}.plugin")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    file_count = 0
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "plugin"
        (stage / ".claude-plugin").mkdir(parents=True)
        (stage / ".claude-plugin" / "plugin.json").write_text(
            json.dumps(packaged_manifest(manifest), indent=2) + "\n", encoding="utf-8"
        )
        for name, skill_dir in staged:
            shutil.copytree(skill_dir, stage / "skills" / name,
                            ignore=shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc"))
        if out_path.exists():
            out_path.unlink()
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    bundle.write(path, path.relative_to(stage).as_posix())
                    file_count += 1

    size_kb = out_path.stat().st_size / 1024
    print(f"OK    {len(staged)} skill(s), {file_count} file(s), {size_kb:.0f} KB")
    # --out may point anywhere; relative_to() raises for a path outside the repo, and
    # a traceback after the bundle is written reads as a failed build that succeeded.
    try:
        shown = out_path.relative_to(ROOT)
    except ValueError:
        shown = out_path
    print(f"OK    {shown}")
    print("\nInstall: open the .plugin file and accept it in Claude, restart the app,")
    print("then confirm with ListSkills. A directory copy into ~/.claude/skills/ does nothing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
