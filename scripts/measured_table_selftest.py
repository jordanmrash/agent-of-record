#!/usr/bin/env python3
"""Break scripts/measured_table.py on purpose and prove it notices.

Cases: the published tree is current; a changed digit in README's block is STALE and --check writes
nothing; --write repairs it; a moved count in the digest end marker makes the table STALE, so the
numbers come from the tree and not from the table; a README without markers fails instead of writing.
Prints MEASURED_TABLE_SELFTEST: OK - n of n cases passed, or FAIL with exit 1.
"""
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "measured_table.py"
IGNORE = shutil.ignore_patterns(".git", "Outputs", "node_modules", "__pycache__", "playwright-output", "*.plugin", "*.log")


def run(root: Path, *flags: str):
    proc = subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *flags],
                          text=True, capture_output=True, encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout + proc.stderr


def put(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def finish(results) -> int:
    passed = sum(1 for r in results if r)
    if passed == len(results):
        print(f"MEASURED_TABLE_SELFTEST: OK - {passed} of {len(results)} cases passed")
        return 0
    print(f"MEASURED_TABLE_SELFTEST: FAIL - {passed} of {len(results)} cases passed")
    return 1


def main() -> int:
    results = []

    def case(name: str, ok: bool, detail: str = "") -> None:
        results.append(ok)
        line = f"{'PASS' if ok else 'FAIL'}  {name}"
        if detail and not ok:
            line += f"  ({detail.strip()[-160:]})"
        print(line)

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "tree"
        shutil.copytree(ROOT, work, ignore=IGNORE)

        code, out = run(work, "--check")
        case("the published tree is current", code == 0 and "MEASURED_TABLE: CURRENT" in out, out)

        readme = work / "README.md"
        original = readme.read_text(encoding="utf-8")
        row = re.search(r"\| Recorded lesson entries \| (\d+) \|", original)
        case("README carries a generated entries row", row is not None)
        if row is None:
            return finish(results)
        put(readme, original.replace(row.group(0), f"| Recorded lesson entries | {int(row.group(1)) + 1} |"))
        before = tree_hash(work)
        code, out = run(work, "--check")
        case("a changed digit is STALE", code == 1 and "STALE  README.md" in out, out)
        case("--check writes nothing", tree_hash(work) == before)

        code, out = run(work, "--write")
        code2, out2 = run(work, "--check")
        case("--write repairs and --check passes", code == 0 and code2 == 0 and "CURRENT" in out2, out + out2)

        instructions = work / "CoworkConfig" / "copilot-instructions.md"
        itext = instructions.read_text(encoding="utf-8")
        marker = re.search(r"from (\d+) entries -->", itext)
        case("digest end marker present", marker is not None)
        if marker is not None:
            put(instructions, itext.replace(marker.group(0), f"from {int(marker.group(1)) + 7} entries -->"))
            code, out = run(work, "--check")
            case("a moved source count makes the table STALE", code == 1 and "STALE" in out, out)
            put(instructions, itext)

        put(readme, readme.read_text(encoding="utf-8").replace("<!-- MEASURED:start -->", "").replace("<!-- MEASURED:end -->", ""))
        code, out = run(work, "--write")
        case("missing markers fail instead of writing", code == 1 and "markers missing" in out, out)

    return finish(results)


if __name__ == "__main__":
    raise SystemExit(main())
