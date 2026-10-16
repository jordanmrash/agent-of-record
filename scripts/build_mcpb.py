#!/usr/bin/env python3
"""Build, check and describe the approved executor as an MCP Bundle (.mcpb).

The bundle is DELIVERY, never source. `Startup/CommandBridge/batch-exec-server.js`
stays the one implementation the launchers start; this script copies it into a
zip beside a manifest (`Startup/CommandBridge/mcpb-manifest.json`) so a desktop host
that understands MCP Bundles can install
the executor with its own picker instead of a hand-edited config file. The same
rule the skills plugin follows applies here: the artifact is regenerated, never
edited, and `--check` fails the release gate when the manifest has drifted from
the server it packages.

What the packaged copy differs in, deliberately:

  * The generated PLUGIN-LESSONS block inside the tool description is removed.
    That block is the operator's own record, regenerated from their corpus, and
    a new install starts with an empty corpus. Shipping one operator's Windows
    rules inside a stranger's Mac tool description was measured as noise on the
    2026-09-15 macOS run, so the bundle carries the generic description only.
    The live reminder (read from cowork-lessons.md at run time) is unaffected.
  * Line terminators are normalized to LF so the bundle hashes identically on a
    Windows and a macOS builder. (0.3.4 shipped a gate failure that was nothing
    but a CRLF checkout; this script does not get to repeat it.)

Nothing else changes. `node --check` runs on the packaged file before it is
zipped. The zip is deterministic: fixed timestamps, sorted entries, one
compression level, so the SHA-256 in the sidecar is reproducible.

Usage
  python scripts/build_mcpb.py                       build to Outputs/MCP Bundle/
  python scripts/build_mcpb.py --out <dir>           build somewhere else
  python scripts/build_mcpb.py --check               gate mode: build to a temp dir, verify, print one line
  python scripts/build_mcpb.py --server-json --tag v0.3.5 --sha <hex> [--out <dir>]
                                                     write server.json for the MCP Registry

Exit codes: 0 ok, 1 check failed, 2 usage or missing input.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SERVER_SRC = REPO / "Startup" / "CommandBridge" / "batch-exec-server.js"
MANIFEST_SRC = REPO / "Startup" / "CommandBridge" / "mcpb-manifest.json"
README_SRC = REPO / "Startup" / "CommandBridge" / "mcpb-README.md"
LICENSE_SRC = REPO / "LICENSE"
DEFAULT_OUT = REPO / "Outputs" / "MCP Bundle"

BUNDLE_BASENAME = "aor-batch-exec"
REGISTRY_NAME = "io.github.jordanmrash/aor-batch-exec"
# The registry entry's one-line description. server.schema.json (2025-12-11) caps `description`
# at 100 characters and mcp-publisher validates against the schema before publishing; the first
# entry carried 150 and would have been refused. The check below holds the line at the source.
REGISTRY_DESCRIPTION = "Runs one existing person-approved script by relative name under one folder. No command or arguments."
REGISTRY_DESCRIPTION_MAX = 100
RELEASE_URL = "https://github.com/jordanmrash/agent-of-record/releases/download/{tag}/{file}"
SCHEMA_URL = "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json"

# The bundle carries exactly these entries and no others.
EXPECTED_ENTRIES = ("manifest.json", "server/index.js", "README.md", "LICENSE")

VERSION_RE = re.compile(r"const SERVER_VERSION\s*=\s*'(\d+\.\d+\.\d+)'")
NAME_RE = re.compile(r"const SERVER_NAME\s*=\s*'([^']+)'")
# The generated block sits inside a string concatenation: `... 'text ' /* start */ + '...' /* end */ , inputSchema`.
# Removing from the start marker through the end marker (inclusive) leaves `'text '  , inputSchema`, valid JS.
LESSONS_BLOCK_RE = re.compile(
    r"/\*\s*PLUGIN-LESSONS:start run_batch_file\s*\*/.*?/\*\s*PLUGIN-LESSONS:end\s*\*/",
    re.DOTALL,
)
LESSONS_REPLACEMENT = (
    "/* PLUGIN-LESSONS: omitted from the packaged bundle. The block is the operator's "
    "own record, regenerated from their corpus; a new install starts with an empty corpus. */"
)

REQUIRED_MANIFEST_FIELDS = ("manifest_version", "name", "version", "description", "author", "server")
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


class BuildError(Exception):
    pass


def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise BuildError(f"missing input: {p.relative_to(REPO) if p.is_relative_to(REPO) else p}")


def server_identity(src_text: str) -> tuple[str, str]:
    m_v = VERSION_RE.search(src_text)
    m_n = NAME_RE.search(src_text)
    if not m_v or not m_n:
        raise BuildError("could not read SERVER_NAME / SERVER_VERSION from the server source")
    return m_n.group(1), m_v.group(1)


def packaged_server(src_text: str) -> str:
    """The server as shipped: lessons block removed, LF terminators, trailing newline."""
    text, n = LESSONS_BLOCK_RE.subn(LESSONS_REPLACEMENT, src_text)
    if n != 1:
        raise BuildError(f"expected exactly one PLUGIN-LESSONS block in the server source, found {n}")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.endswith("\n"):
        text += "\n"
    return text


def node_check(js_text: str) -> None:
    node = shutil.which("node")
    if not node:
        raise BuildError("node is not on PATH; the packaged server cannot be syntax-checked")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "index.js"
        p.write_text(js_text, encoding="utf-8", newline="\n")
        r = subprocess.run([node, "--check", str(p)], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise BuildError("node --check failed on the packaged server:\n" + (r.stderr or r.stdout))


def validate_manifest(manifest: dict, name: str, version: str) -> None:
    for f in REQUIRED_MANIFEST_FIELDS:
        if f not in manifest:
            raise BuildError(f"manifest.json lacks required field '{f}'")
    if manifest["name"] != name:
        raise BuildError(f"manifest name '{manifest['name']}' differs from SERVER_NAME '{name}'")
    if manifest["version"] != version:
        raise BuildError(
            f"manifest version '{manifest['version']}' differs from SERVER_VERSION '{version}'; "
            "bump the manifest when the server version moves"
        )
    server = manifest["server"]
    if server.get("type") != "node":
        raise BuildError("manifest server.type must be 'node'")
    if server.get("entry_point") != "server/index.js":
        raise BuildError("manifest server.entry_point must be 'server/index.js'")
    args = server.get("mcp_config", {}).get("args", [])
    if "${__dirname}/server/index.js" not in args:
        raise BuildError("manifest mcp_config.args must start the packaged server by ${__dirname}/server/index.js")
    env = server.get("mcp_config", {}).get("env", {})
    if env.get("COWORK_ROOT") != "${user_config.tooling_root}":
        raise BuildError("manifest must pass the chosen tooling root to the server as COWORK_ROOT")
    if "tooling_root" not in manifest.get("user_config", {}):
        raise BuildError("manifest user_config must offer tooling_root")
    if not isinstance(manifest.get("author"), dict) or not manifest["author"].get("name"):
        raise BuildError("manifest author.name is required")


def bundle_bytes(manifest_text: str, server_text: str, readme_text: str, license_text: str) -> bytes:
    """A deterministic zip: fixed timestamps, sorted names, one compression level."""
    files = {
        "manifest.json": manifest_text,
        "server/index.js": server_text,
        "README.md": readme_text,
        "LICENSE": license_text,
    }
    assert tuple(sorted(files)) == tuple(sorted(EXPECTED_ENTRIES))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name in sorted(files):
            data = files[name].replace("\r\n", "\n").encode("utf-8")
            info = zipfile.ZipInfo(name, date_time=FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o644 & 0xFFFF) << 16
            zf.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return buf.getvalue()


def verify_bundle(data: bytes, expected_server: str, manifest: dict) -> None:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = tuple(sorted(zf.namelist()))
        if names != tuple(sorted(EXPECTED_ENTRIES)):
            raise BuildError(f"bundle entries {names} differ from expected {tuple(sorted(EXPECTED_ENTRIES))}")
        shipped = zf.read("server/index.js").decode("utf-8")
        if shipped != expected_server:
            raise BuildError("packaged server/index.js differs from the stripped, LF-normalized source")
        if "PLUGIN-LESSONS:start" in shipped or "OPERATING RULES, each learned" in shipped:
            raise BuildError("packaged server still carries the PLUGIN-LESSONS block")
        if json.loads(zf.read("manifest.json").decode("utf-8")) != manifest:
            raise BuildError("packaged manifest.json differs from the source manifest")


def build(out_dir: Path | None, quiet: bool = False) -> tuple[Path | None, str, str, bytes]:
    src_text = read_text(SERVER_SRC)
    name, version = server_identity(src_text)
    manifest_text = read_text(MANIFEST_SRC)
    try:
        manifest = json.loads(manifest_text)
    except json.JSONDecodeError as e:
        raise BuildError(f"manifest.json is not valid JSON: {e}")
    validate_manifest(manifest, name, version)
    shipped = packaged_server(src_text)
    node_check(shipped)
    readme = read_text(README_SRC)
    lic = read_text(LICENSE_SRC)
    data = bundle_bytes(manifest_text, shipped, readme, lic)
    verify_bundle(data, shipped, manifest)
    sha = hashlib.sha256(data).hexdigest()
    filename = f"{BUNDLE_BASENAME}-{version}.mcpb"
    written = None
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        written = out_dir / filename
        written.write_bytes(data)
        (out_dir / (filename + ".sha256")).write_text(f"{sha}  {filename}\n", encoding="utf-8", newline="\n")
        if not quiet:
            print(f"OK    {written}")
            print(f"OK    sha256 {sha}")
            print(f"OK    {len(data)} bytes, {len(EXPECTED_ENTRIES)} entries, server {name} {version}")
    return written, version, sha, data


def check_registry_description() -> None:
    """The server.json description must fit the registry schema: 1 to 100 characters."""
    n = len(REGISTRY_DESCRIPTION)
    if not 1 <= n <= REGISTRY_DESCRIPTION_MAX:
        raise BuildError(
            f"registry description is {n} characters; server.schema.json allows 1-{REGISTRY_DESCRIPTION_MAX}"
        )


def server_json(tag: str, version: str, sha: str, out_dir: Path) -> Path:
    check_registry_description()
    filename = f"{BUNDLE_BASENAME}-{version}.mcpb"
    doc = {
        "$schema": SCHEMA_URL,
        "name": REGISTRY_NAME,
        "title": "Agent of Record: approved batch executor",
        "description": REGISTRY_DESCRIPTION,
        "repository": {"url": "https://github.com/jordanmrash/agent-of-record", "source": "github"},
        "websiteUrl": "https://github.com/jordanmrash/agent-of-record/blob/main/docs/install/claude-cowork.md",
        "version": version,
        "packages": [
            {
                "registryType": "mcpb",
                "identifier": RELEASE_URL.format(tag=tag, file=filename),
                "fileSha256": sha,
                "transport": {"type": "stdio"},
                "environmentVariables": [
                    {
                        "name": "COWORK_ROOT",
                        "description": "The one folder the executor is confined to: scripts under <root>/CommandJobs, deliverables under <root>/Outputs.",
                        "isRequired": True,
                    },
                    {
                        "name": "COWORK_CONFIG_ROOT",
                        "description": "Optional folder holding cowork-memory/cowork-lessons.md for the operating-rules reminder.",
                        "isRequired": False,
                    },
                ],
            }
        ],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / "server.json"
    p.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    return p


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=None, help=f"output folder (default: {DEFAULT_OUT})")
    ap.add_argument("--check", action="store_true", help="gate mode: build to a temp dir, verify, print one line")
    ap.add_argument("--server-json", action="store_true", help="write server.json for the MCP Registry")
    ap.add_argument("--tag", help="release tag the bundle is attached to, e.g. v0.3.5 (with --server-json)")
    ap.add_argument("--sha", help="sha256 of the released bundle (with --server-json); computed if omitted")
    a = ap.parse_args(argv)

    try:
        if a.check:
            with tempfile.TemporaryDirectory() as td:
                _, version, sha, data = build(Path(td), quiet=True)
            check_registry_description()
            print(f"MCPB_CHECK: CLEAN - {BUNDLE_BASENAME} {version}, {len(data)} bytes, sha256 {sha[:12]}...")
            return 0
        if a.server_json:
            if not a.tag:
                print("--server-json needs --tag", file=sys.stderr)
                return 2
            out = a.out or DEFAULT_OUT
            _, version, sha, _ = build(None, quiet=True)
            p = server_json(a.tag, version, a.sha or sha, out)
            print(f"OK    {p}")
            if a.sha and a.sha != sha:
                print("NOTE  --sha differs from a fresh local build; make sure it is the digest of the RELEASED asset")
            return 0
        build(a.out or DEFAULT_OUT)
        return 0
    except BuildError as e:
        print(f"MCPB_CHECK: FAIL - {e}" if a.check else f"FAIL  {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
