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
