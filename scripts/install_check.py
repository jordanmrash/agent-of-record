#!/usr/bin/env python3
"""Verify an installation of this repository, on Windows or macOS or Linux.

`release_check.py` answers "is this snapshot intact?" and runs anywhere. This
script answers a different and harder question - "does this machine actually
have a working agent foundation?" - and can only be answered where the thing is
installed. It is the definition of done for the install contract in AGENTS.md:
an agent that has finished installing this repository can run this and get a
verdict rather than an impression.

It checks four layers, and reports each independently:

    runtime   node, python, git, and the pinned supergateway
    servers   a REAL stdio MCP handshake against each bridge's own server,
              started the way its launcher starts it - not a port probe, not
              a file-exists test
    config    the skills, instructions and lessons corpus Cowork loads, with
              the 1024-character description cap enforced, because a skill
              over it is dropped silently by the loader with no error
    corpus    lesson integrity and digest currency on the installed corpus

Nothing here contacts a tunnel or a tenant. A dev tunnel that is private, a
connector that has not been registered, and an administrator who has not
allowed custom apps are all real installation failures, and all three are
invisible from this machine - so this script deliberately does not pretend to
observe them. What it can prove, it proves by doing.

    python scripts/install_check.py
    python scripts/install_check.py --json install-results.json
    python scripts/install_check.py --config-root "/path/to/Cowork"
    python scripts/install_check.py --route local

`--route` names how the agent host reaches the bridges. `hosted` (the default) is
a cloud client behind a dev tunnel, which needs the pinned supergateway; `local`
is a client on the machine that starts each launcher itself as a stdio server,
where supergateway is never used and is reported as skipped rather than required.

Exit 0 when every check passes, 1 when any fails.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "docs" / "bridge-facts.json"
IS_WINDOWS = os.name == "nt"

# A skill whose frontmatter description exceeds this is dropped by the Cowork
# loader with no error at all. Measured, and it cost a day to find.
DESCRIPTION_CAP = 1024

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"


class Report:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, layer: str, name: str, status: str, detail: str = "") -> None:
        self.rows.append({"layer": layer, "check": name, "status": status,
                          "detail": detail})

    @property
    def failures(self) -> list[dict]:
        return [r for r in self.rows if r["status"] == FAIL]


def run(cmd: list[str], timeout: int = 30) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           cwd=str(ROOT))
    except FileNotFoundError:
        return 127, "not found"
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    return p.returncode, (p.stdout + p.stderr).strip()


# ----------------------------------------------------------------- runtime --

def check_runtime(rep: Report, route: str = "hosted") -> None:
    for name, cmd, needed in (
        ("node", ["node", "--version"], True),
        ("python", [sys.executable, "--version"], True),
        ("git", ["git", "--version"], True),
        ("npx", ["npx.cmd" if IS_WINDOWS else "npx", "--version"], False),
    ):
        exe = cmd[0]
        if exe != sys.executable and shutil.which(exe) is None:
            rep.add("runtime", name, FAIL if needed else SKIP, "not on PATH")
            continue
        code, out = run(cmd)
        first = out.splitlines()[0] if out else ""
        rep.add("runtime", name, PASS if code == 0 else FAIL, first)

    # Node 20+ is what the servers are written against.
    code, out = run(["node", "--version"]) if shutil.which("node") else (127, "")
    m = re.match(r"v(\d+)", out or "")
    if m:
        major = int(m.group(1))
        rep.add("runtime", "node is 20 or newer",
                PASS if major >= 20 else FAIL, out.strip())

    if route == "local":
        rep.add("runtime", "supergateway", SKIP,
                "not used on the local route - the host starts each launcher as a stdio server")
        return

    pinned = ROOT / "Startup" / "package.json"
    installed = ROOT / "Startup" / "node_modules" / "supergateway"
    want = ""
    if pinned.is_file():
        try:
            want = json.loads(pinned.read_text()).get("dependencies", {}).get(
                "supergateway", "")
        except json.JSONDecodeError:
            want = ""
    if not installed.is_dir():
        rep.add("runtime", "supergateway installed", FAIL,
                "Startup/node_modules is absent - run: cd Startup && npm install")
    else:
        got = ""
        pkg = installed / "package.json"
        if pkg.is_file():
            try:
                got = json.loads(pkg.read_text()).get("version", "")
            except json.JSONDecodeError:
                got = ""
        ok = bool(want) and got == want.lstrip("^~")
        rep.add("runtime", "supergateway matches the pinned version",
                PASS if ok else FAIL, f"pinned {want or '?'}, installed {got or '?'}")


# ----------------------------------------------------------------- servers --

def launcher_for(bridge: dict) -> Path:
    key = "stdio" if IS_WINDOWS else "stdio_posix"
    rel = bridge.get(key)
    if not rel:
        return ROOT / "Startup" / bridge.get("stdio", "")
    return ROOT / "Startup" / rel


# Claude Cowork validates tool schemas against JSON Schema 2020-12 only. A server
# that declares draft-07 handshakes, advertises its tools, and then fails EVERY
# call -- which is what made the 2026-09-14 aor-filesystem outage invisible to a
# CLEAN install check. An absent $schema is fine; a wrong one is not.
SUPPORTED_DIALECT = "2020-12"

# npx fetches the upstream servers on first run, so the first handshake on a cold
# machine is a download. Long enough to clear a normal fetch, short enough that an
# offline machine skips rather than hangs.
UPSTREAM_TIMEOUT = int(os.environ.get("COWORK_UPSTREAM_HANDSHAKE_TIMEOUT", "60"))


def schema_findings(tools: list) -> list[str]:
    """Tool schemas Cowork cannot use.

    Two distinct faults, both measured on this repo's own bridges:

    1. A structurally empty inputSchema -- `{"$schema": ...}` and nothing else.
       Cowork rejects tools/list outright ("expected object" at
       tools[N].inputSchema.type) and the whole server drops out. Measured
       2026-09-15: server-filesystem 2025.8.21 does this on 13 of 14 tools,
       because zod-to-json-schema@3 cannot read the zod 4 internals that
       @modelcontextprotocol/sdk now pulls in.

    2. A declared $schema dialect other than 2020-12, which Cowork does not
       validate against.

    Fault 1 is fatal on its own, so it is reported first and separately: a
    dialect complaint about an empty schema hides the real problem.
    """
    findings = []
    for tool in tools or []:
        name = tool.get("name", "?")
        schema = tool.get("inputSchema")
        if isinstance(schema, dict) and schema.get("type") != "object":
            findings.append(f"{name}.inputSchema has no type:object (empty schema)")
            continue
        for field in ("inputSchema", "outputSchema"):
            s = tool.get(field)
            if not isinstance(s, dict):
                continue
            dialect = s.get("$schema")
            if dialect and SUPPORTED_DIALECT not in dialect:
                findings.append(f"{name}.{field}={dialect}")
    return findings


def mcp_handshake(command: list, timeout: int = 25,
                  cwd: Path | None = None) -> tuple[bool, str, list]:
    """Start the server on stdio and complete a real MCP initialize.

    Returns (ok, detail, tools). `command` is argv, so this works for both the
    repository's own node servers and the POSIX/Windows launcher scripts that
    exec an upstream server through npx.
    """
    env = dict(os.environ)
    env["COWORK_ROOT"] = str(ROOT)
    tools_seen: list = []
    try:
        proc = subprocess.Popen(
            [str(c) for c in command],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, env=env,
            cwd=str(cwd) if cwd else None,
        )
    except OSError as exc:
        return False, f"could not start: {exc}", tools_seen

    req = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
           "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                      "clientInfo": {"name": "install-check", "version": "1"}}}
    try:
        proc.stdin.write(json.dumps(req) + "\n")
        proc.stdin.flush()
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == 1:
                info = msg.get("result", {}).get("serverInfo", {})
                name = info.get("name", "")
                ver = info.get("version", "")
                if name:
                    # A server that answers initialize should also list tools.
                    proc.stdin.write(json.dumps(
                        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}) + "\n")
                    proc.stdin.flush()
                    tools = "?"
                    while time.time() < deadline:
                        l2 = proc.stdout.readline()
                        if not l2:
                            break
                        try:
                            m2 = json.loads(l2.strip())
                        except json.JSONDecodeError:
                            continue
                        if m2.get("id") == 2:
                            tools_seen = m2.get("result", {}).get("tools", []) or []
                            tools = str(len(tools_seen))
                            break
                    return True, f"{name} {ver}, {tools} tool(s)", tools_seen
                return False, "initialize returned no serverInfo", tools_seen
        return False, "no initialize response", tools_seen
    except (BrokenPipeError, OSError) as exc:
        return False, f"transport error: {exc}", tools_seen
    finally:
        try:
            proc.stdin.close()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


ROUTE_PRODUCT = {"hosted": "copilot", "local": "claude"}
THIS_PLATFORM = "windows" if IS_WINDOWS else "macos"


def bridges_in_scope(facts: dict, route: str) -> tuple[list[dict], list[dict]]:
    """The bridges that exist for this route's product on this platform, per the two
    axes the manifest declares. No port is named here: a bridge leaves a route by a
    manifest edit, and this check follows."""
    product = ROUTE_PRODUCT[route]
    inside, outside = [], []
    for bridge in facts.get("bridges", []):
        products = bridge.get("products") or sorted(ROUTE_PRODUCT.values())
        platforms = bridge.get("platforms") or ["windows", "macos"]
        (inside if product in products and THIS_PLATFORM in platforms else outside).append(bridge)
    return inside, outside


def check_servers(rep: Report, facts: dict, route: str = "hosted") -> None:
    if shutil.which("node") is None:
        rep.add("servers", "all bridges", SKIP, "node is not installed")
        return

    inside, _outside = bridges_in_scope(facts, route)
    total = len(facts.get("bridges", []))
    rep.add("servers", "bridges in scope", PASS,
            f"{len(inside)} of {total} for {ROUTE_PRODUCT[route]} on {THIS_PLATFORM}: "
            + ", ".join(str(b.get("port")) for b in inside))

    for bridge in inside:
        port = bridge.get("port")
        label = f"{port} {bridge.get('name', '')}".strip()

        launcher = launcher_for(bridge)
        rep.add("servers", f"{label}: launcher present",
                PASS if launcher.is_file() else FAIL, str(launcher.name))

        if not IS_WINDOWS and launcher.is_file():
            mode = launcher.stat().st_mode
            rep.add("servers", f"{label}: launcher is executable",
                    PASS if mode & 0o111 else FAIL,
                    "chmod +x " + str(launcher.relative_to(ROOT)))

        # The upstream servers are started by npx, which downloads on first run,
        # so this used to be skipped outright. That skip is what let the
        # 2026-09-14 aor-filesystem outage pass a CLEAN check: the launcher was
        # present and executable, and every tool call still failed. So the
        # handshake is attempted; only an unresponsive server is skipped, and a
        # server that answers with the wrong schema dialect is a hard failure.
        server_rel = bridge.get("server")
        if not server_rel:
            if not launcher.is_file():
                rep.add("servers", f"{label}: stdio handshake", SKIP,
                        "launcher missing; nothing to start")
                continue
            command = ([str(launcher)] if not IS_WINDOWS
                       else ["cmd", "/c", str(launcher)])
            ok, detail, tools = mcp_handshake(command, timeout=UPSTREAM_TIMEOUT,
                                              cwd=launcher.parent)
            if not ok:
                rep.add("servers", f"{label}: stdio handshake", SKIP,
                        f"{detail} (npx may still be fetching it; re-run once cached)")
                continue
            rep.add("servers", f"{label}: stdio handshake", PASS, detail)

            findings = schema_findings(tools)
            rep.add("servers", f"{label}: tool schemas",
                    FAIL if findings else PASS,
                    "; ".join(findings[:3]) + (f" (+{len(findings) - 3} more)"
                                               if len(findings) > 3 else "")
                    if findings
                    else f"{len(tools)} tool(s), no unsupported $schema")
            continue

        server_js = ROOT / server_rel
        if not server_js.is_file():
            rep.add("servers", f"{label}: stdio handshake", FAIL,
                    f"missing {server_rel}")
            continue

        code, _ = run(["node", "--check", str(server_js)])
        rep.add("servers", f"{label}: server parses",
                PASS if code == 0 else FAIL, server_js.name)

        ok, detail, tools = mcp_handshake(["node", str(server_js)],
                                          cwd=server_js.parent)
        rep.add("servers", f"{label}: stdio handshake",
                PASS if ok else FAIL, detail)

        findings = schema_findings(tools)
        rep.add("servers", f"{label}: tool schemas",
                FAIL if findings else PASS,
                "; ".join(findings[:3]) if findings
                else f"{len(tools)} tool(s), no unsupported $schema")


# ------------------------------------------------------------------ config --

def resolve_config_root(explicit: str | None) -> Path | None:
    if explicit:
        return Path(explicit).expanduser()
    env = os.environ.get("COWORK_CONFIG_ROOT")
    if env:
        return Path(env).expanduser()
    return None


def frontmatter_description(text: str) -> str | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end]
    m = re.search(r"^description:\s*(.*?)(?=^\w+:|\Z)", block,
                  re.S | re.M)
    if not m:
        return None
    raw = m.group(1).strip()
    if raw.startswith(("|", ">")):
        raw = "\n".join(l.strip() for l in raw.splitlines()[1:])
    return raw.strip().strip("'\"")


PLUGIN_MANIFEST = ROOT / "CoworkConfig" / "plugin" / ".claude-plugin" / "plugin.json"


def skills_for_product(product: str) -> int | None:
    """How many manifest skills are declared for this product. None if unreadable."""
    try:
        entries = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))["skills"]
    except (OSError, ValueError, KeyError):
        return None
    return sum(1 for e in entries
               if product in e.get("products", list(ROUTE_PRODUCT.values())))


def check_config(rep: Report, config_root: Path | None, route: str = "hosted") -> None:
    # The skills that ship in the repository are always checkable.
    for label, skills_dir in (("repository", ROOT / "CoworkConfig" / "Skills"),
                              ("installed", (config_root / "skills")
                               if config_root else None)):
        if skills_dir is None:
            rep.add("config", "installed skills", SKIP,
                    "no config root given; pass --config-root or set "
                    "COWORK_CONFIG_ROOT")
            continue
        if not skills_dir.is_dir():
            rep.add("config", f"{label} skills present",
                    SKIP if label == "installed" else FAIL, str(skills_dir))
            continue

        files = sorted(skills_dir.glob("*/SKILL.md"))
        detail = f"{len(files)} skill(s)"
        if label == "repository":
            # The repository holds every skill; a route ships the subset declared
            # for its product. Both numbers are true and reporting only the first
            # makes a correct install look wrong.
            shipped = skills_for_product(ROUTE_PRODUCT[route])
            if shipped is not None and shipped != len(files):
                detail = (f"{len(files)} in the repository, "
                          f"{shipped} ship to {ROUTE_PRODUCT[route]}")
        rep.add("config", f"{label} skills present",
                PASS if files else FAIL, detail)

        over = []
        missing = []
        for f in files:
            text = f.read_text(encoding="utf-8", errors="replace")
            desc = frontmatter_description(text)
            if desc is None:
                missing.append(f.parent.name)
            elif len(desc) > DESCRIPTION_CAP:
                over.append(f"{f.parent.name} ({len(desc)})")
        rep.add("config", f"{label} skills under the {DESCRIPTION_CAP}-char cap",
                PASS if not over else FAIL,
                ", ".join(over) if over else f"{len(files)} checked")
        if missing:
            rep.add("config", f"{label} skills have a description", FAIL,
                    ", ".join(missing))

    if config_root is None:
        return

    rep.add("config", "config root exists",
            PASS if config_root.is_dir() else FAIL, str(config_root))
    if not config_root.is_dir():
        return

    for name, rel in (("copilot-instructions.md", "copilot-instructions.md"),
                      ("cowork-memory corpus", "cowork-memory")):
        target = config_root / rel
        rep.add("config", f"installed {name}",
                PASS if target.exists() else FAIL, str(target))


# ------------------------------------------------------------------ corpus --

def check_corpus(rep: Report, config_root: Path | None) -> None:
    scripts = ROOT / "CoworkConfig" / "Skills" / "self-improvement" / "scripts"
    lessons = None
    if config_root and (config_root / "cowork-memory" / "cowork-lessons.md").is_file():
        lessons = config_root / "cowork-memory" / "cowork-lessons.md"
    elif (ROOT / "CoworkConfig" / "cowork-memory" / "cowork-lessons.md").is_file():
        lessons = ROOT / "CoworkConfig" / "cowork-memory" / "cowork-lessons.md"

    if lessons is None:
        rep.add("corpus", "lessons corpus", FAIL, "cowork-lessons.md not found")
        return

    where = "installed" if config_root and str(lessons).startswith(
        str(config_root)) else "repository"
    checker = scripts / "lesson_check.py"
    if not checker.is_file():
        rep.add("corpus", "lesson integrity", FAIL, "lesson_check.py missing")
        return
    code, out = run([sys.executable, str(checker), str(lessons)], timeout=120)
    last = out.splitlines()[-1] if out else ""
    rep.add("corpus", f"lesson integrity ({where} corpus)",
            PASS if code == 0 else FAIL, last)

    instructions = None
    if config_root and (config_root / "copilot-instructions.md").is_file():
        instructions = config_root / "copilot-instructions.md"
    elif (ROOT / "CoworkConfig" / "copilot-instructions.md").is_file():
        instructions = ROOT / "CoworkConfig" / "copilot-instructions.md"
    if instructions is None:
        rep.add("corpus", "digest currency", SKIP, "no instructions file")
        return
    digest = scripts / "digest_apply.py"
    if not digest.is_file():
        rep.add("corpus", "digest currency", FAIL, "digest_apply.py missing")
        return
    code, out = run([sys.executable, str(digest), "--lessons", str(lessons),
                     "--instructions", str(instructions), "--check"], timeout=120)
    last = out.splitlines()[-1] if out else ""
    rep.add("corpus", "digest currency", PASS if code == 0 else FAIL, last)


# -------------------------------------------------------------------- main --

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Verify an installation of this repository on this machine.")
    ap.add_argument("--config-root", default=None,
                    help="the Cowork folder that holds skills, "
                         "copilot-instructions.md and cowork-memory "
                         "(default: $COWORK_CONFIG_ROOT)")
    ap.add_argument("--json", default=None, metavar="FILE",
                    help="also write machine-readable results")
    ap.add_argument("--route", choices=("hosted", "local"), default="hosted",
                    help="hosted: a cloud client reaches the bridges through "
                         "supergateway and a dev tunnel (Copilot Cowork); "
                         "local: the client starts the launchers itself as stdio "
                         "servers (Claude Cowork) - supergateway is not checked")
    args = ap.parse_args(argv)

    if not FACTS.is_file():
        print(f"INSTALL_CHECK: {FACTS} not found - is this the repository root?")
        return 1
    facts = json.loads(FACTS.read_text(encoding="utf-8"))
    config_root = resolve_config_root(args.config_root)

    rep = Report()
    check_runtime(rep, args.route)
    check_servers(rep, facts, args.route)
    check_config(rep, config_root, args.route)
    check_corpus(rep, config_root)

    width = max(len(r["check"]) for r in rep.rows)
    current = None
    for row in rep.rows:
        if row["layer"] != current:
            current = row["layer"]
            print(f"\n[{current}]")
        print(f"  {row['status']:4s}  {row['check']:<{width}}  {row['detail']}")

    passed = sum(1 for r in rep.rows if r["status"] == PASS)
    skipped = sum(1 for r in rep.rows if r["status"] == SKIP)
    failed = len(rep.failures)

    print()
    print(f"host: {platform.system()} {platform.release()}  "
          f"python {platform.python_version()}  route {args.route}")
    print(f"config root: {config_root or '(not given)'}")

    if args.json:
        # The results file is meant to be committed as evidence, so it must not
        # carry the operator's home directory. The config root is reduced to a
        # placeholder and every check detail has the home path redacted; the
        # disclosure scan would refuse the file otherwise, and rightly.
        home = str(Path.home())
        cfg = str(config_root) if config_root else ""
        def scrub(text: str) -> str:
            # config root first: it usually lives under home, and replacing home
            # first would leave "<home>/Library/.../Cowork" - still a real layout.
            if cfg and cfg in text:
                text = text.replace(cfg, "<config-root>")
            if home and home in text:
                text = text.replace(home, "<home>")
            return text
        payload = {
            "repository": "agent-of-record",
            "host": {"system": platform.system(), "release": platform.release(),
                     "machine": platform.machine(),
                     "python": platform.python_version()},
            "config_root": "<config-root>" if config_root else None,
            "route": args.route,
            "checks": [{**r, "detail": scrub(r["detail"])} for r in rep.rows],
            "passed": passed, "failed": failed, "skipped": skipped,
            "clean": failed == 0,
        }
        Path(args.json).write_text(json.dumps(payload, indent=2) + "\n",
                                   encoding="utf-8")
        print(f"results written to {args.json}")

    if failed:
        print(f"INSTALL_CHECK: {failed} FAILURE(S)  "
              f"({passed} passed, {skipped} skipped)")
        return 1
    print(f"INSTALL_CHECK: CLEAN ({passed} passed, {skipped} skipped)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
