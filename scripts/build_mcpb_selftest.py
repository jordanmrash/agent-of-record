#!/usr/bin/env python3
"""Self-test for build_mcpb.py: one positive run and the negative controls.

A gate check that has never been seen to fail has not been seen to work, so each
control below breaks the input in one specific way and asserts the build refuses
with the expected reason. The positive control builds the real bundle to a temp
folder, extracts it, starts the packaged server with COWORK_ROOT pointing at a
throwaway root, completes an MCP handshake, and reads the tool description back
to prove the PLUGIN-LESSONS block is gone.

Run:  python scripts/build_mcpb_selftest.py
Exit: 0 all cases passed, 1 otherwise. Prints BUILD_MCPB_SELFTEST: OK|FAIL.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_mcpb as bm  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def case(name: str, ok: bool, note: str = "") -> None:
    RESULTS.append((name, ok, note))
    print(f"{'PASS' if ok else 'FAIL'}  {name}{('  ' + note) if note else ''}")


def expect_fail(name: str, fn, needle: str) -> None:
    try:
        fn()
    except bm.BuildError as e:
        case(name, needle in str(e), f"refused: {e}" if needle in str(e) else f"refused for the wrong reason: {e}")
        return
    case(name, False, "was accepted")


def with_source(mutator):
    """Run a build against a copy of the tree whose server source was altered by `mutator`."""
    def run():
        src = bm.SERVER_SRC.read_text(encoding="utf-8")
        man = bm.MANIFEST_SRC.read_text(encoding="utf-8")
        new_src, new_man = mutator(src, man)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "Startup" / "CommandBridge").mkdir(parents=True)
            (root / "Startup" / "CommandBridge" / "batch-exec-server.js").write_text(new_src, encoding="utf-8", newline="\n")
            (root / "Startup" / "CommandBridge" / "mcpb-manifest.json").write_text(new_man, encoding="utf-8", newline="\n")
            (root / "Startup" / "CommandBridge" / "mcpb-README.md").write_text(bm.README_SRC.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
            (root / "LICENSE").write_text(bm.LICENSE_SRC.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
            saved = (bm.SERVER_SRC, bm.MANIFEST_SRC, bm.README_SRC, bm.LICENSE_SRC)
            bm.SERVER_SRC = root / "Startup" / "CommandBridge" / "batch-exec-server.js"
            bm.MANIFEST_SRC = root / "Startup" / "CommandBridge" / "mcpb-manifest.json"
            bm.README_SRC = root / "Startup" / "CommandBridge" / "mcpb-README.md"
            bm.LICENSE_SRC = root / "LICENSE"
            try:
                bm.build(None, quiet=True)
            finally:
                bm.SERVER_SRC, bm.MANIFEST_SRC, bm.README_SRC, bm.LICENSE_SRC = saved
    return run


def handshake(index_js: Path, tooling_root: Path) -> dict:
    node = shutil.which("node")
    env = dict(os.environ)
    env["COWORK_ROOT"] = str(tooling_root)
    env.pop("COWORK_CONFIG_ROOT", None)
    proc = subprocess.Popen(
        [node, str(index_js)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=env, text=True, encoding="utf-8",
    )
    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "selftest", "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    out, _ = proc.communicate("".join(json.dumps(m) + "\n" for m in msgs), timeout=60)
    replies = {}
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if "id" in obj:
            replies[obj["id"]] = obj
    return replies


def main() -> int:
    # ---- positive control -----------------------------------------------------------
    try:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            written, version, sha, data = bm.build(out, quiet=True)
            case("bundle builds", written is not None and written.exists(), f"{written.name if written else ''} {len(data)} bytes")
            sidecar = out / (written.name + ".sha256")
            case("sha256 sidecar matches", sidecar.exists() and sidecar.read_text().split()[0] == sha)
            # deterministic: a second build is byte-identical
            _, _, sha2, _ = bm.build(None, quiet=True)
            case("build is deterministic", sha == sha2)
            with zipfile.ZipFile(written) as zf:
                case("bundle carries exactly the expected entries",
                     tuple(sorted(zf.namelist())) == tuple(sorted(bm.EXPECTED_ENTRIES)))
                extract = Path(td) / "x"
                zf.extractall(extract)
            index_js = extract / "server" / "index.js"
            case("packaged server has LF terminators only", b"\r" not in index_js.read_bytes())
            root = Path(td) / "root"
            replies = handshake(index_js, root)
            info = replies.get(1, {}).get("result", {}).get("serverInfo", {})
            case("packaged server completes an MCP handshake",
                 info.get("name") == "aor-batch-exec" and info.get("version") == version, str(info))
            tools = replies.get(2, {}).get("result", {}).get("tools", [])
            desc = tools[0]["description"] if tools else ""
            case("one tool, run_batch_file", len(tools) == 1 and tools[0]["name"] == "run_batch_file")
            case("tool description carries no operator lessons block",
                 "OPERATING RULES, each learned" not in desc and "PLUGIN-LESSONS" not in desc)
            case("server created CommandJobs and Outputs under the chosen root",
                 (root / "CommandJobs").is_dir() and (root / "Outputs").is_dir())
    except Exception as e:  # noqa: BLE001
        case("positive control ran", False, repr(e))

    # ---- negative controls ----------------------------------------------------------
    expect_fail("refuses a manifest version that drifted from SERVER_VERSION",
                with_source(lambda s, m: (s, m.replace('"version": "', '"version": "9.', 1))), "differs from SERVER_VERSION")
    expect_fail("refuses a source with the lessons block missing",
                with_source(lambda s, m: (bm.LESSONS_BLOCK_RE.sub("", s), m)), "exactly one PLUGIN-LESSONS block")
    expect_fail("refuses a manifest that does not pass the tooling root through",
                with_source(lambda s, m: (s, m.replace('"COWORK_ROOT": "${user_config.tooling_root}"', '"COWORK_ROOT": "/tmp/fixed"'))),
                "tooling root")
    expect_fail("refuses a manifest whose name is not the server's",
                with_source(lambda s, m: (s, m.replace('"name": "aor-batch-exec"', '"name": "something-else"', 1))),
                "differs from SERVER_NAME")
    expect_fail("refuses a packaged server that does not parse",
                with_source(lambda s, m: (s + "\nthis is not javascript (\n", m)), "node --check failed")
    expect_fail("refuses a manifest that is not JSON",
                with_source(lambda s, m: (s, m + "\n{")), "not valid JSON")

    # ---- report -----------------------------------------------------------------------
    failed = [r for r in RESULTS if not r[1]]
    total = len(RESULTS)
    if failed:
        print(f"BUILD_MCPB_SELFTEST: FAIL - {len(failed)} of {total} cases failed")
        return 1
    print(f"BUILD_MCPB_SELFTEST: OK - {total} of {total} cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
