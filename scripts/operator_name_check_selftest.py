#!/usr/bin/env python3
"""Break scripts/operator_name_check.py on purpose and prove it notices.

A synthetic tree with its own author (Avery Example): rule text, skill prose, a verified lesson, an
attribution block, a docs page, a CRLF file. Cases: hits are found and the verified rule is KEPT;
--fix rewrites hits with the right role and capitalisation, leaves attribution and the verified rule
alone, and preserves CRLF; the fixed tree is CLEAN; a tree with no hits is CLEAN.
Prints OPERATOR_NAME_SELFTEST: OK - n of n cases passed, or FAIL with exit 1.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "operator_name_check.py"


def run(root: Path, *flags: str):
    proc = subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *flags],
                          text=True, capture_output=True, encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout + proc.stderr


def put(root: Path, rel: str, text: str, newline: str = "\n") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.replace("\n", newline).encode("utf-8"))
    return path


def build(root: Path, with_hits: bool) -> None:
    put(root, "CITATION.cff", "cff-version: 1.2.0\nauthors:\n  - family-names: Example\n    given-names: Avery\n")
    put(root, "CoworkConfig/cowork-memory/verification-ledger.json",
        '[{"key": "verified-one", "verdict": "EFFECTIVE"}]')
    skill = (
        "---\nname: demo\ndescription: Demo skill.\nmetadata:\n  author: \"Avery Example\"\n  owner: \"Avery Example\"\n---\n"
        "# Demo\n\n> **Created by Avery Example**, original author and maintainer.\n\n"
    )
    corpus = "# Lessons\n\n### One\n- **Pattern-Key:** verified-one\n- **Rule:** Ask Avery first.\n\n### Two\n- **Pattern-Key:** plain-two\n"
    docs = "# Vision\n\nThis page states Avery Example's view.\n"
    if with_hits:
        skill += "| Key | Rule |\n|---|---|\n| `k1` | When Avery says the bridge is up, wait. |\n\nTell Avery before deleting anything.\n"
        corpus += "- **Rule:** Never tell Avery a bridge is down.\n- **Failed:** Avery asked for the file twice.\n"
        docs += "Avery's perspective is the author's.\n"
    put(root, "CoworkConfig/Skills/demo/SKILL.md", skill, newline="\r\n")
    put(root, "CoworkConfig/cowork-memory/cowork-lessons.md", corpus)
    put(root, "docs/vision.md", docs)


def main() -> int:
    results = []

    def case(name: str, ok: bool, detail: str = "") -> None:
        results.append(ok)
        line = f"{'PASS' if ok else 'FAIL'}  {name}"
        if detail and not ok:
            line += f"  ({detail.strip()[-160:]})"
        print(line)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "hits"
        build(root, with_hits=True)
        code, out = run(root)
        case("hits are reported and the check fails", code == 1 and "OPERATOR_NAME_CHECK: 5 line(s)" in out, out)
        case("the verified rule is KEPT, not counted", "KEEP  CoworkConfig/cowork-memory/cowork-lessons.md:5" in out, out)
        case("attribution lines are not hits", "SKILL.md:5" not in out and "SKILL.md:9" not in out, out)

        code, out = run(root, "--fix")
        case("--fix runs", code == 0 and "OPERATOR_NAME_FIX: rewrote 5 line(s)" in out, out)
        skill = (root / "CoworkConfig/Skills/demo/SKILL.md").read_bytes().decode("utf-8")
        case("rule text uses the operator", "When the operator says the bridge is up" in skill and "Tell the operator before" in skill)
        case("attribution survives", "Created by Avery Example" in skill and "author: \"Avery Example\"" in skill)
        case("CRLF preserved", "\r\n" in skill and "\n" not in skill.replace("\r\n", ""))
        corpus = (root / "CoworkConfig/cowork-memory/cowork-lessons.md").read_text(encoding="utf-8")
        case("verified rule text untouched", "- **Rule:** Ask Avery first." in corpus)
        case("field openers are capitalised", "- **Failed:** The operator asked for the file twice." in corpus
             and "Never tell the operator a bridge is down." in corpus)
        docs = (root / "docs/vision.md").read_text(encoding="utf-8")
        case("docs pages say the author", "The author's perspective is the author's." in docs and "Avery Example's view" in docs)

        code, out = run(root)
        case("the fixed tree is CLEAN", code == 0 and "OPERATOR_NAME_CHECK: CLEAN" in out and "1 verified rule line(s) kept" in out, out)

        clean = Path(tmp) / "clean"
        build(clean, with_hits=False)
        code, out = run(clean)
        case("a tree without hits is CLEAN", code == 0 and "CLEAN" in out, out)

    passed = sum(1 for r in results if r)
    if passed == len(results):
        print(f"OPERATOR_NAME_SELFTEST: OK - {passed} of {len(results)} cases passed")
        return 0
    print(f"OPERATOR_NAME_SELFTEST: FAIL - {passed} of {len(results)} cases passed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
