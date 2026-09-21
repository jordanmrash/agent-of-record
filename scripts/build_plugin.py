#!/usr/bin/env python3
"""Package CoworkConfig/Skills into an installable Claude Cowork .plugin.

Why this exists
---------------
The repo's only skill-install mechanism was syncing CoworkConfig/Skills into
$COWORK_CONFIG_ROOT/skills, which is a Copilot Cowork location. Nothing
installed a skill into Claude Cowork on either platform. Copying skills into
~/.claude/skills/ does not do it either: Claude Code reads that directory,
Cowork does not. The mechanism that works is a plugin: a directory holding
.claude-plugin/plugin.json plus skills/<name>/SKILL.md, zipped to a .plugin
file and uploaded through Customize -> Plugins -> Add -> Upload plugin.

The upload picker is the only install path. Claude registers no document type
for the .plugin extension, so double-clicking the file fails with
kLSApplicationNotFoundErr on macOS and does nothing on Windows -- measured
2026-09-15 against Claude 1.52386.3, whose CFBundleDocumentTypes declare
.dxt/.mcpb and .skill but no .plugin.

This script makes that artifact reproducible instead of hand-assembled.

Usage
-----
    python3 scripts/build_plugin.py                     # build for both platforms
    python3 scripts/build_plugin.py --platform macos    # only macOS-declared skills
    python3 scripts/build_plugin.py --strict            # fail on Windows-only text
    python3 scripts/build_plugin.py --list              # show what would ship
    python3 scripts/build_plugin.py --tree              # regenerate CoworkConfig/plugin/skills
    python3 scripts/build_plugin.py --check-tree        # exit 3 if that tree is stale; the gate runs this

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
# The plugin root a marketplace installs: the manifest above plus a skills/ tree generated from
# SKILLS_SRC. Claude Code copies this directory into its cache and refuses component paths that
# leave it, so the tree is a copy, not a reference. --tree writes it; --check-tree fails when it
# differs from the source by one byte. Never edit it by hand.
PLUGIN_ROOT = ROOT / "CoworkConfig" / "plugin"
TREE = PLUGIN_ROOT / "skills"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
COPY_IGNORE = shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc")
OUT_DIR = ROOT / "Outputs" / "Skills Plugin"

# The same signals the acceptance test greps for. A skill declared as
# macos-supported must not contain any of these.
WINDOWS_ONLY = [
    (re.compile(r"\bcd /d\b"), "cd /d"),
    (re.compile(r"\breg query\b", re.I), "reg query"),
    (re.compile(r"C:\\\\Users|C:\\Users"), r"C:\Users"),
    (re.compile(r"\.bat\b"), ".bat"),
    # Same identifier guard as the port pattern below: the lesson key
    # `bridge-devtunnel-declared-dead-without-reprobe` is a name, not a claim.
    (re.compile(r"(?<![\w-])devtunnel(?![\w-])", re.I), "devtunnel"),
    # A port number standing in prose ("port 8933", "(8933)", "8931/8932/8933"), not a
    # digit run inside a hyphenated identifier. `bridge-8933-arg-name` is a lesson key,
    # `command-bridge-8933` a route id, `bridge-8931-` a route prefix: names, not claims
    # about a platform, and a key may never be renamed to satisfy a gate. Measured
    # 2026-09-14: 71 of 141 port hits across the then-ten skills were identifiers.
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


# A Windows-specific token is acceptable where the same unit of text names the macOS
# counterpart: "the job script - .bat/.cmd on Windows, .sh on macOS" is CORRECT on both
# platforms and must not read as Windows-only. The unit is one line for a table row
# (each row stands alone) and one paragraph for prose (a sentence may wrap).
MAC_COUNTERPART = re.compile(r"\bmac(?:os)?\b|\bposix\b|\bdarwin\b|\.sh\b|\bbash\b|\bzsh\b|(?<![\w])~/", re.I)

# The generated lessons block is the operator's record, regenerated from the corpus by
# skill_lessons.py; its entries name the route they were learned on, and a new install
# starts with an empty corpus, which empties the block. It is a record, not the skill's
# instructions, so it is not scanned. The markers are skill_lessons.py's START/END.
LESSONS_START = "<!-- SKILL-LESSONS:start -->"
LESSONS_END = "<!-- SKILL-LESSONS:end -->"


def strip_lessons_block(text: str) -> str:
    if LESSONS_START in text and LESSONS_END in text:
        pre, rest = text.split(LESSONS_START, 1)
        _block, post = rest.split(LESSONS_END, 1)
        return pre + post
    return text


def unpaired_units(text: str) -> list[str]:
    """The lines/paragraphs that carry a Windows token and name no macOS counterpart."""
    units: list[str] = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            units.append("\n".join(paragraph))
            paragraph.clear()

    for line in text.splitlines():
        if line.lstrip().startswith("|"):
            flush()
            units.append(line)
        elif line.strip() == "":
            flush()
        else:
            paragraph.append(line)
    flush()
    return [u for u in units if not MAC_COUNTERPART.search(u)]


def scan_windows_text(skill_dir: Path) -> list[str]:
    hits: list[str] = []
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".md", ".txt", ".json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if path.name == "SKILL.md":
            text = strip_lessons_block(text)
        scope = "\n".join(unpaired_units(text))
        for pattern, label in WINDOWS_ONLY:
            count = len(pattern.findall(scope))
            if count:
                hits.append(f"{path.relative_to(skill_dir)}: {count}x {label}")
    return hits


# This script builds the CLAUDE delivery: a .plugin uploaded through Customize ->
# Plugins -> Add -> Upload plugin. Copilot Cowork gets the same skills a different
# way -- CoworkConfig/Skills is synced into $COWORK_CONFIG_ROOT/skills -- so a skill
# that exists only for one product is declared here rather than kept in two trees.
# Same two-axis shape docs/bridge-facts.json uses for bridges: absent means both.
PRODUCTS = ["claude", "copilot"]
PLATFORMS = ["windows", "macos"]


def select(manifest: dict, platform: str | None,
           product: str = "claude") -> list[dict]:
    # The shipping list lives under metadata, never at the top level. Claude Code reads a
    # top-level `skills` as component PATHS and fails to load a manifest whose `skills` is a list
    # of objects - measured against the plugins reference 2026-09-16 - while `metadata` is the
    # free-form object the schema reserves for a plugin's own data.
    if isinstance(manifest.get("skills"), list) and any(isinstance(e, dict) for e in manifest["skills"]):
        fail("manifest carries the shipping list at top-level 'skills'; Claude Code reads that field as "
             "component paths and would refuse to load the plugin. Move the list to metadata.skills.", 2)
    entries = (manifest.get("metadata") or {}).get("skills")
    if not isinstance(entries, list) or not entries:
        fail("manifest has no metadata.skills array -- nothing to package", 2)
    entries = [e for e in entries if product in e.get("products", PRODUCTS)]
    if not entries:
        fail(f"no skills declared for product '{product}'", 2)
    if platform is None:
        return entries
    chosen = [e for e in entries if platform in e.get("platforms", PLATFORMS)]
    if not chosen:
        fail(f"no skills declared for platform '{platform}'", 2)
    return chosen


def packaged_manifest(manifest: dict) -> dict:
    """The shipped plugin.json: the manifest without the build-time metadata object."""
    return {k: v for k, v in manifest.items() if not k.startswith("_") and k != "metadata"}


def tree_files(base: Path) -> dict[str, bytes]:
    """Every file under base as posix-relative path -> bytes, ignoring what the copy ignores."""
    out: dict[str, bytes] = {}
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(base)
        if any(part in {"__pycache__", ".DS_Store"} for part in rel.parts) or path.suffix == ".pyc":
            continue
        out[rel.as_posix()] = path.read_bytes()
    return out


def expected_tree(staged: list[tuple[str, Path]]) -> dict[str, bytes]:
    want: dict[str, bytes] = {}
    for name, skill_dir in staged:
        for rel, data in tree_files(skill_dir).items():
            want[f"{name}/{rel}"] = data
    return want


def tree_drift(staged: list[tuple[str, Path]]) -> list[str]:
    """What differs between the generated skills/ tree and its source. Empty means current."""
    want = expected_tree(staged)
    have = tree_files(TREE) if TREE.is_dir() else {}
    drift = [f"missing: skills/{rel}" for rel in sorted(set(want) - set(have))]
    drift += [f"extra: skills/{rel}" for rel in sorted(set(have) - set(want))]
    drift += [f"differs: skills/{rel}" for rel in sorted(set(want) & set(have)) if want[rel] != have[rel]]
    return drift


def write_tree(staged: list[tuple[str, Path]]) -> int:
    """Rewrite the generated tree from the source. Whatever was there is removed first, so a
    file the source no longer has cannot survive in the copy; a tree that is already gone, or
    goes while being removed, is not an error - the goal is its absence."""
    shutil.rmtree(TREE, ignore_errors=True)
    TREE.mkdir(parents=True, exist_ok=True)
    for name, skill_dir in staged:
        shutil.copytree(skill_dir, TREE / name, ignore=COPY_IGNORE)
    return len(expected_tree(staged))


def catalog_problems(manifest: dict) -> list[str]:
    """The marketplace catalog names this plugin root, and the manifest is a shape Claude Code loads."""
    problems: list[str] = []
    if not re.fullmatch(r"[a-z][a-z0-9]*(-[a-z0-9]+)*", str(manifest.get("name", ""))):
        problems.append(f"plugin.json name {manifest.get('name')!r} is not kebab-case")
    for key, kind in (("keywords", list), ("author", dict), ("metadata", dict)):
        if key in manifest and not isinstance(manifest[key], kind):
            problems.append(f"plugin.json {key} must be a {kind.__name__}")
    if not MARKETPLACE.is_file():
        problems.append(f"{MARKETPLACE.relative_to(ROOT).as_posix()} is missing")
        return problems
    try:
        catalog = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return problems + [f"marketplace.json is not valid JSON: {exc}"]
    if not catalog.get("name") or not isinstance(catalog.get("owner"), dict) or not catalog["owner"].get("name"):
        problems.append("marketplace.json needs a name and an owner with a name")
    entries = [e for e in catalog.get("plugins", []) if isinstance(e, dict)]
    mine = [e for e in entries if e.get("name") == manifest.get("name")]
    if len(mine) != 1:
        problems.append(f"marketplace.json must list {manifest.get('name')!r} exactly once, found {len(mine)}")
        return problems
    source = str(mine[0].get("source", ""))
    if not source.startswith("./"):
        problems.append(f"marketplace entry source {source!r} must be a relative path starting with ./")
    elif (ROOT / source[2:]).resolve() != PLUGIN_ROOT.resolve():
        problems.append(f"marketplace entry source {source!r} does not point at {PLUGIN_ROOT.relative_to(ROOT).as_posix()}")
    if not mine[0].get("description"):
        problems.append("marketplace entry has no description")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--platform", choices=["windows", "macos"], default=None,
                        help="package only skills declared for this platform (default: all)")
    parser.add_argument("--product", choices=["claude", "copilot"], default="claude",
                        help="package only skills declared for this product (default: claude, "
                             "which is the product this .plugin installs into)")
    parser.add_argument("--strict", action="store_true",
                        help="fail the build if a macos-declared skill contains Windows-only text")
    parser.add_argument("--list", action="store_true", help="report what would ship and exit")
    parser.add_argument("--tree", action="store_true",
                        help="regenerate CoworkConfig/plugin/skills from CoworkConfig/Skills and exit")
    parser.add_argument("--check-tree", action="store_true",
                        help="exit 3 if CoworkConfig/plugin/skills, the manifest or the marketplace catalog would not install")
    parser.add_argument("--out", type=Path, default=None, help="output .plugin path")
    args = parser.parse_args()

    if not SKILLS_SRC.is_dir():
        fail(f"skills source not found: {SKILLS_SRC.relative_to(ROOT)}", 2)

    manifest = load_manifest()
    entries = select(manifest, args.platform, args.product)

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
        if hits and "macos" in entry.get("platforms", ["windows", "macos"]):
            message = f"{name}: declared macos but carries unpaired Windows-only text -> " + "; ".join(hits[:4])
            (problems if args.strict else warnings).append(message)
        elif hits:
            # Declared for Windows only: not a failure, but the residue is what stands
            # between this skill and both platforms, so say how much is left.
            warnings.append(f"{name}: windows-only, {sum(int(h.split(': ')[1].split('x')[0]) for h in hits)} unpaired token(s) remain")

        staged.append((name, skill_dir))

    if args.tree or args.check_tree:
        if problems:
            for problem in problems:
                print(f"FAIL  {problem}", file=sys.stderr)
            print(f"\n{len(problems)} problem(s) -- the tree was not touched.", file=sys.stderr)
            return 3
        if args.tree:
            count = write_tree(staged)
            print(f"PLUGIN_TREE: WRITTEN ({len(staged)} skill(s), {count} file(s) under {TREE.relative_to(ROOT).as_posix()})")
            return 0
        drift = tree_drift(staged) + catalog_problems(manifest)
        for line in drift:
            print(f"FAIL  {line}", file=sys.stderr)
        if drift:
            print(f"PLUGIN_TREE: STALE ({len(drift)} finding(s)) -- run scripts/build_plugin.py --tree", file=sys.stderr)
            return 3
        print(f"PLUGIN_TREE: CURRENT ({len(staged)} skill(s), {len(expected_tree(staged))} file(s); manifest and catalog install)")
        return 0

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
            shutil.copytree(skill_dir, stage / "skills" / name, ignore=COPY_IGNORE)
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
    print("\nInstall: in Claude, Customize -> Plugins -> Add -> Upload plugin, select this")
    print("file, then restart the app and confirm with ListSkills. Double-clicking the")
    print("file does not work; Claude registers no document type for .plugin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
