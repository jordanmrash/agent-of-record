#!/usr/bin/env python3
"""Negative-controlled self-test for the build_plugin.py --strict matcher.

Every pattern in WINDOWS_ONLY must fire on a sentence that means what the label says,
and none may fire on a lesson key, a route id, a route prefix or a near-miss. The
expected counts are hand-authored from the fixture text, not derived from the patterns
(lesson count-assertion-must-use-independent-control). Exit 0 on pass, 1 on any failure,
2 if the module under test cannot be loaded - a crash is not a pass.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load():
    spec = importlib.util.spec_from_file_location("build_plugin_under_test", HERE / "build_plugin.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    try:
        bp = load()
    except Exception as exc:  # noqa: BLE001 - the point is to report, not to pass
        print(f"BUILD_PLUGIN_SELFTEST: FAIL could not load build_plugin.py: {exc}")
        return 2
    labels = {label: pattern for pattern, label in bp.WINDOWS_ONLY}
    ran = 0
    bad = 0

    def case(ok: bool, msg: str) -> None:
        nonlocal ran, bad
        ran += 1
        bad += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'}  {msg}")

    expected_labels = {"cd /d", "reg query", "C:\\Users", ".bat", "devtunnel", "bridge port", "Copilot connector id"}
    case(set(labels) == expected_labels, f"the pattern set is exactly the seven named labels ({sorted(labels)})")

    # POSITIVE controls: one sentence per label that means what the label says. Counts are
    # authored from the text, not computed by the pattern under test.
    positives = [
        ("cd /d", "Start every job with cd /d into the repository root.", 1),
        ("reg query", "Read the user PATH with reg query HKCU\\Environment before guessing.", 1),
        ("C:\\Users", "Jobs live under C:\\Users\\YOURUSER\\Documents\\COPILOT_COWORK\\CommandJobs.", 1),
        (".bat", "Author a .bat file, then run bridge-health.bat before the job itself.", 2),
        ("devtunnel", "Drops are the devtunnel hop; DevTunnel never reaches the bridge process.", 2),
        ("bridge port", "Port 8933 runs the executor; ports 8931/8932 launch from npx.", 3),
        ("bridge port", "The executor (8933) and the browser bridge (8931) both listen locally.", 2),
        ("bridge port", "Ports 8931, 8932, 8933 and 8934 must be set to PUBLIC after every restart.", 4),
        ("bridge port", "If 8933 is unavailable, stop. Run it on 8933, then read the file back.", 2),
        ("Copilot connector id", "Call jordan-approved-batch-8933-v1-run_batch_file, never jordan-local-filesystem-8932-v1.", 2),
    ]
    def count(label: str, text: str) -> int:
        pattern = labels.get(label)
        return -1 if pattern is None else len(pattern.findall(text))

    for label, text, want in positives:
        got = count(label, text)
        case(got == want, f"{label!r} fires {want}x on: {text!r} (got {got})")

    # NEGATIVE controls: identifiers and near-misses that must NOT read as platform text.
    negatives = [
        ("bridge port", "See `bridge-8933-arg-name` and `bridge-8932-writes-lf` before writing a job."),
        ("bridge port", '"command-bridge-8933": { "title": "the executor" }, "power-automate-8934": {}'),
        ("bridge port", 'route prefixes: "bridge-8931-", "bridge-8932-", "bridge-8933-"'),
        ("bridge port", "the connector jordan-approved-batch-8933-v1 is named by its own pattern, not this one"),
        ("bridge port", "tasks.json has .pre-8933-stateful-backup siblings"),
        ("bridge port", "unrelated numbers: 89315, 18933, v8933, x8933y, 893"),
        (".bat", "combat boots, a .batch file, acrobat, and wombat"),
        ("cd /d", "the cd /dev/null idiom, and cd /data"),
        ("devtunnel", "a devtunnels plural does not count; nor does mydevtunnel"),
        ("Copilot connector id", "jordan-approved-batch-v1 has no port; jordan-8933-v1 has no service name"),
    ]
    for label, text in negatives:
        got = count(label, text)
        case(got == 0, f"{label!r} stays silent on: {text!r} (got {got})")

    # PAIRING: a Windows token is acceptable where the same unit names its macOS counterpart.
    has_pairing = all(hasattr(bp, n) for n in ("unpaired_units", "strip_lessons_block", "MAC_COUNTERPART"))
    case(has_pairing, "build_plugin exposes unpaired_units, strip_lessons_block and MAC_COUNTERPART")
    if not has_pairing:
        print(f"BUILD_PLUGIN_SELFTEST: FAIL {bad} of {ran} cases - the pairing rule is absent, remaining pairing cases skipped")
        return 1
    paired = [
        "the job script - `.bat`/`.cmd` on Windows, `.sh` on macOS",
        "| Executor | `Startup\\exec-server.cmd` on Windows, `Startup/posix/exec-server.sh` on macOS |",
        "Start every job by changing into the tooling root:\n`cd /d <root>` on Windows, `cd <root>` in a POSIX shell.",
        "the browser profile lives under C:\\Users\\YOURUSER on Windows and under ~/ on a Mac",
        "Read the user PATH with reg query on Windows; on macOS the launcher reads ~/.zshrc via zsh.",
    ]
    for text in paired:
        case(bp.unpaired_units(text) == [], f"paired unit is accepted: {text[:60]!r}")
    unpaired = [
        "Author a .bat file containing the exact git commands.",
        "| Tool | `run_batch_file` (relative path to an existing .bat under CommandJobs) |",
        "Start every job with cd /d into the repository root.\nThe environment is complete.",
    ]
    for text in unpaired:
        case(bp.unpaired_units(text) == [text], f"unpaired unit is kept for scanning: {text[:60]!r}")
    # a table pairs PER ROW: one macOS row does not excuse its neighbours
    table = "| a | .bat on Windows, .sh on macOS |\n| b | run the .bat |"
    case(bp.unpaired_units(table) == ["| b | run the .bat |"], "a table pairs per row, not per table")
    # prose pairs PER PARAGRAPH: a wrapped sentence counts as one unit
    prose = "The job script is .bat on\nWindows and .sh on macOS.\n\nAnother paragraph runs the .bat."
    case(bp.unpaired_units(prose) == ["Another paragraph runs the .bat."], "prose pairs per paragraph; the unpaired one is kept")
    # macOS counterpart vocabulary, and the words that must NOT count as one
    for good in ["on macOS", "a POSIX shell", "run install.sh", "under ~/agent-of-record", "the Mac", "bash -n"]:
        case(bp.MAC_COUNTERPART.search(good) is not None, f"counterpart vocabulary: {good!r}")
    for miss in ["macros are fine", "the machine", "a .shx file", "posixly", "nomac"]:
        case(bp.MAC_COUNTERPART.search(miss) is None, f"not a counterpart: {miss!r}")
    # the generated block is a record, not instructions, and is not scanned
    with tempfile.TemporaryDirectory() as td:
        rec = Path(td) / "rec-skill"
        rec.mkdir()
        (rec / "SKILL.md").write_text(
            "# skill\n\n<!-- SKILL-LESSONS:start -->\n| `bridge-8932-writes-lf` | files written through 8932 arrive LF-only; run the .bat fix |\n<!-- SKILL-LESSONS:end -->\n\nPortable body.\n",
            encoding="utf-8")
        case(bp.scan_windows_text(rec) == [], "a Windows-flavoured lessons block does not fail a portable body")
        (rec / "SKILL.md").write_text(
            "# skill\n\n<!-- SKILL-LESSONS:start -->\n| k | r |\n<!-- SKILL-LESSONS:end -->\n\nRun the .bat.\n",
            encoding="utf-8")
        case(bp.scan_windows_text(rec) == ["SKILL.md: 1x .bat"], "the body outside the block is still scanned")
        (rec / "notes.md").write_text("<!-- SKILL-LESSONS:start -->\nrun the .bat\n<!-- SKILL-LESSONS:end -->\n", encoding="utf-8")
        # sorted(): rglob order is case-sensitive on POSIX and case-insensitive on Windows
        case(sorted(bp.scan_windows_text(rec)) == ["SKILL.md: 1x .bat", "notes.md: 1x .bat"], "only SKILL.md's block is exempt; the same markers in another file are not")
    # devtunnel: identifier guard
    case(count("devtunnel", "see `bridge-devtunnel-declared-dead-without-reprobe` first") == 0, "'devtunnel' silent inside a lesson key")
    case(count("devtunnel", "drops are the devtunnel hop") == 1, "'devtunnel' fires in prose")

    # MANIFEST DEFAULT: once every skill is portable, an entry with no platforms field means both.
    manifest_fixture = {"skills": [{"name": "portable"}, {"name": "windows-only", "platforms": ["windows"]}]}
    case([e["name"] for e in bp.select(manifest_fixture, "macos")] == ["portable"], "a manifest entry with no platforms field defaults to both")
    case([e["name"] for e in bp.select(manifest_fixture, "windows")] == ["portable", "windows-only"], "the default-both entry also ships on Windows")

    # THE REAL TREE: all five manifest skills exist, carry no temporary platforms field, and scan clean.
    repo_root = HERE.parent
    manifest_real = json.loads((repo_root / "CoworkConfig" / "plugin" / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    # 2026-09-15: the Claude route narrowed to the executor, so five skills ship to Claude.
    # The five that only duplicate first-party Claude capability - persistent-memory (host
    # memory), local-file-bridge (connected folders), playwright-skill (the built-in browser),
    # git-bridge (the host runs git directly) and skill-menu (Customize lists skills) - stay
    # in the repository declared products: [copilot], because Copilot Cowork has none of it.
    case(len(manifest_real["skills"]) == 10, f"real manifest names ten skills ({len(manifest_real['skills'])})")
    claude_skills = bp.select(manifest_real, None, "claude")
    copilot_skills = bp.select(manifest_real, None, "copilot")
    case(len(claude_skills) == 5, f"five skills ship to claude ({len(claude_skills)})")
    case(len(copilot_skills) == 10, f"ten skills ship to copilot ({len(copilot_skills)})")
    case({s["name"] for s in copilot_skills} - {s["name"] for s in claude_skills}
         == {"persistent-memory", "local-file-bridge", "playwright-skill", "git-bridge", "skill-menu"},
         "the five copilot-only skills are exactly the ones Claude covers first-party")
    case(bp.select({"skills": [{"name": "x"}]}, None, "claude")[0]["name"] == "x",
         "a manifest entry with no products field defaults to both")
    case(all("platforms" not in e for e in manifest_real["skills"]), "the temporary per-skill platforms field is gone")
    dirty_real = {e["name"]: bp.scan_windows_text(repo_root / "CoworkConfig" / "Skills" / e["name"]) for e in manifest_real["skills"]}
    dirty_real = {k: v for k, v in dirty_real.items() if v}
    case(dirty_real == {}, f"all ten real skills have zero unpaired units ({dirty_real})")

    # END TO END through scan_windows_text, the function --strict actually calls: a skill
    # directory whose SKILL.md is all lesson keys is CLEAN; one line of prose is not.
    with tempfile.TemporaryDirectory() as td:
        clean = Path(td) / "clean-skill"
        clean.mkdir()
        (clean / "SKILL.md").write_text(
            "| `bridge-8933-arg-name` | rule |\n| `bridge-8932-writes-lf` | rule |\n"
            '{"command-bridge-8933": 1}\n', encoding="utf-8")
        (clean / "routes.json").write_text('["bridge-8931-", "power-automate-8934"]\n', encoding="utf-8")
        (clean / "notes.py").write_text("port 8933  # code files are not scanned\n", encoding="utf-8")
        hits = bp.scan_windows_text(clean)
        case(hits == [], f"a skill of lesson keys and route ids is CLEAN under scan_windows_text ({hits})")
        dirty = Path(td) / "dirty-skill"
        dirty.mkdir()
        (dirty / "SKILL.md").write_text("| `bridge-8933-arg-name` | run it on 8933 through the .bat |\n", encoding="utf-8")
        hits = bp.scan_windows_text(dirty)
        case(sorted(hits) == sorted(["SKILL.md: 1x .bat", "SKILL.md: 1x bridge port"]),
             f"one prose line yields exactly one .bat and one bridge-port hit ({hits})")

    if bad:
        print(f"BUILD_PLUGIN_SELFTEST: FAIL {bad} of {ran} cases")
        return 1
    print(f"BUILD_PLUGIN_SELFTEST: OK - {ran} of {ran} cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
