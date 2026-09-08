#!/usr/bin/env python3
"""Cross-surface bridge facts check.

Every bridge fact - port, name, stateful or not, roots, tool count - is stated in
several places: the VS Code tasks, the watchdog, the .cmd launchers, two READMEs,
the architecture diagram, the Cowork connector packages and the skills that
drive the bridges. Each restatement
is a place for drift to hide. The published v0.1.0 tree carried two: a skill that
counted three bridges after a fourth had been added, and a skill that said port
8934 did not exist after it had become the Power Automate bridge.

`docs/bridge-facts.json` is the one home. This check reads it and verifies every
surface it names. It never edits anything.

Exit codes: 0 all surfaces agree, 1 at least one finding, 2 could not run.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "docs", "bridge-facts.json")

STATEFUL_WORDS = {True: "stateful", False: "stateless"}
PLACEHOLDER_APP_ID = "00000000-0000-4000-8000-000000000000"


class Findings:
    def __init__(self):
        self.items = []
        self.checked = 0

    def fail(self, surface, message):
        self.items.append((surface, message))

    def ok(self):
        self.checked += 1


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def strip_json_comments(text):
    # tasks.json is JSON with // comments; the values we need are on their own lines
    return "\n".join(l for l in text.splitlines() if not l.strip().startswith("//"))


def check_tasks(m, f):
    live = read(m["surfaces"]["tasks"])
    good = read(m["surfaces"]["tasks_known_good"])
    if live != good:
        f.fail("tasks", "Startup/.vscode/tasks.json and Startup/KnownGood/tasks.json differ - "
                        "the restore job would revert the live configuration")
    else:
        f.ok()
    text = strip_json_comments(live)
    # One task now declares its port once per platform: the default args plus
    # the osx and linux overrides. What must match the manifest is the set of
    # ports served and the number of TASKS, not the number of times a port is
    # written down - so ports are counted per task block, not per occurrence.
    ports = []
    for seg in _task_blocks(text):
        found = re.findall(r'"--port",\s*"(\d+)"', seg)
        if not found:
            continue
        if len(set(found)) != 1:
            f.fail("tasks", "one task block declares more than one port: %s"
                   % sorted(set(found)))
            continue
        ports.append(found[0])
    expected = [str(b["port"]) for b in m["bridges"]]
    if sorted(ports) != sorted(expected):
        f.fail("tasks", "tasks.json declares ports %s, manifest has %s" % (ports, expected))
    else:
        f.ok()
    for b in m["bridges"]:
        seg = _task_segment(text, str(b["port"]))
        if seg is None:
            f.fail("tasks", "no task block for port %s" % b["port"])
            continue
        if b["task_label"] not in seg:
            f.fail("tasks", "port %s task label is not %r" % (b["port"], b["task_label"]))
        if not seg.rstrip().endswith(b["stdio"]) and b["stdio"] not in seg:
            f.fail("tasks", "port %s does not point --stdio at %s" % (b["port"], b["stdio"]))
        has_stateful = '"--stateful"' in seg
        if has_stateful != b["stateful"]:
            f.fail("tasks", "port %s is %s in the manifest but %s in tasks.json"
                   % (b["port"], STATEFUL_WORDS[b["stateful"]], STATEFUL_WORDS[has_stateful]))
        f.ok()


def _task_blocks(text):
    """Each task block, from its "label" line to the next one."""
    labels = [mm.start() for mm in re.finditer(r'"label"\s*:', text)]
    for i, start in enumerate(labels):
        end = labels[i + 1] if i + 1 < len(labels) else len(text)
        yield text[start:end]


def _task_segment(text, port):
    for seg in _task_blocks(text):
        if re.search(r'"--port",\s*"%s"' % port, seg):
            return seg
    return None


def check_watchdog(m, f):
    text = read(m["surfaces"]["watchdog"])
    rows = re.findall(r'Port\s*=\s*(\d+);\s*Name\s*=\s*"([^"]+)";\s*Stdio\s*=\s*"\$Startup\\([^"]+)";\s*Stateful\s*=\s*\$(true|false)', text)
    found = {int(p): (n, s, st == "true") for p, n, s, st in rows}
    for b in m["bridges"]:
        if b["port"] not in found:
            f.fail("watchdog", "port %s has no entry in the watchdog table" % b["port"])
            continue
        n, s, st = found[b["port"]]
        if n != b["watchdog_name"]:
            f.fail("watchdog", "port %s named %r, manifest says %r" % (b["port"], n, b["watchdog_name"]))
        if s != b["stdio"]:
            f.fail("watchdog", "port %s stdio %r, manifest says %r" % (b["port"], s, b["stdio"]))
        if st != b["stateful"]:
            f.fail("watchdog", "port %s %s in watchdog, %s in manifest"
                   % (b["port"], STATEFUL_WORDS[st], STATEFUL_WORDS[b["stateful"]]))
        f.ok()
    extra = set(found) - {b["port"] for b in m["bridges"]}
    if extra:
        f.fail("watchdog", "watchdog covers ports not in the manifest: %s" % sorted(extra))


def check_launchers(m, f):
    for b in m["bridges"]:
        path = os.path.join("Startup", b["stdio"])
        if not os.path.isfile(os.path.join(ROOT, path)):
            f.fail("launchers", "%s is missing" % path)
            continue
        text = read(path)
        live = "\n".join(l for l in text.splitlines() if not l.upper().startswith("REM"))
        if b["implementation"] == "upstream":
            if b["package"] not in live:
                f.fail("launchers", "%s does not start %s" % (path, b["package"]))
            for root in b.get("roots", []):
                if root not in live:
                    f.fail("launchers", "%s does not pass root %s" % (path, root))
        else:
            server = b["server"].replace("/", "\\")
            if server.split("\\")[-1] not in live:
                f.fail("launchers", "%s does not start %s" % (path, b["server"]))
            if not os.path.isfile(os.path.join(ROOT, b["server"])):
                f.fail("launchers", "%s named in the manifest does not exist" % b["server"])
        f.ok()


def check_posix_launchers(m, f):
    """Every Windows launcher has a POSIX sibling that starts the same server.

    The claim v0.3 makes is that this runs on a Mac. The way that claim rots is
    a bridge gaining a Windows launcher and never gaining the other one, so the
    manifest names both and this refuses a pair that has drifted apart.
    """
    for b in m["bridges"]:
        rel = b.get("stdio_posix")
        if not rel:
            f.fail("posix launchers", "port %s has no stdio_posix in the manifest"
                   % b["port"])
            continue
        path = os.path.join("Startup", rel.replace("/", os.sep))
        if not os.path.isfile(os.path.join(ROOT, path)):
            f.fail("posix launchers", "%s is missing" % path)
            continue
        text = read(path)
        live = "\n".join(l for l in text.splitlines()
                         if not l.lstrip().startswith("#"))
        if b["implementation"] == "upstream":
            if b["package"] not in live:
                f.fail("posix launchers", "%s does not start %s"
                       % (path, b["package"]))
        else:
            leaf = b["server"].split("/")[-1]
            if leaf not in live:
                f.fail("posix launchers", "%s does not start %s"
                       % (path, b["server"]))
        # A POSIX launcher that hard-codes a home directory would defeat both
        # the disclosure scan and the point of shipping it. It must COMPUTE the
        # tooling root from its own location - merely mentioning COWORK_ROOT is
        # not the property being asserted, so the pattern is the derivation.
        if not re.search(r'COWORK_ROOT="\$\(cd\s+"\$HERE', text):
            f.fail("posix launchers",
                   "%s does not derive COWORK_ROOT from its own location" % path)
            continue
        f.ok()

    # The task file must actually START them, per task. A launcher that exists
    # but is wired to nothing is the same outage as a launcher that is missing,
    # and one task keeping its override while another loses it is exactly the
    # drift a whole-file check would miss.
    tasks = strip_json_comments(read(m["surfaces"]["tasks"]))
    for b in m["bridges"]:
        rel = b.get("stdio_posix")
        if not rel:
            continue
        seg = _task_segment(tasks, str(b["port"]))
        if seg is None:
            continue          # already reported by check_tasks
        missing = [k for k in ("osx", "linux") if '"%s"' % k not in seg]
        if missing:
            f.fail("posix launchers",
                   "port %s has no %s override in tasks.json; that platform "
                   "would run the Windows launcher"
                   % (b["port"], " or ".join(missing)))
            continue
        if rel not in seg:
            f.fail("posix launchers",
                   "port %s platform override does not point --stdio at %s"
                   % (b["port"], rel))
            continue
        f.ok()


def check_tool_count(m, f):
    for b in m["bridges"]:
        if "tool_count" not in b:
            continue
        src = read(b["server"])
        names = set(re.findall(r"^\s+name:\s*'([a-z_]+)'", src, re.M))
        if len(names) != b["tool_count"]:
            f.fail("tool_count", "%s registers %d tools, manifest says %d"
                   % (b["server"], len(names), b["tool_count"]))
        else:
            f.ok()
        for path in (m["surfaces"]["readme"], m["surfaces"]["readme_template"]):
            row = _readme_row(read(path), b["port"])
            if row is None:
                continue
            mm = re.search(r"(\d+)\s+tools", row)
            if mm and int(mm.group(1)) != b["tool_count"]:
                f.fail(path, "8934 row says %s tools, server registers %d" % (mm.group(1), len(names)))


def _readme_row(text, port):
    for line in text.splitlines():
        if line.startswith("| %d |" % port):
            return line
    return None


def check_readmes(m, f):
    for path in (m["surfaces"]["readme"], m["surfaces"]["readme_template"]):
        text = read(path)
        for b in m["bridges"]:
            row = _readme_row(text, b["port"])
            if row is None:
                f.fail(path, "no bridge table row for port %s" % b["port"])
                continue
            cells = [c.strip() for c in row.strip("|").split("|")]
            if cells[1] != b["readme_name"]:
                f.fail(path, "port %s row names it %r, manifest says %r" % (b["port"], cells[1], b["readme_name"]))
            word = STATEFUL_WORDS[b["stateful"]]
            other = STATEFUL_WORDS[not b["stateful"]]
            impl = cells[-1].lower()
            if word not in impl or other in impl:
                f.fail(path, "port %s row does not say %s" % (b["port"], word))
            f.ok()
        heading = re.search(r"^## The (\w+) bridges", text, re.M)
        if heading and _number(heading.group(1)) != m["bridge_count"]:
            f.fail(path, "heading counts %s bridges, manifest has %d" % (heading.group(1), m["bridge_count"]))

    text = read(m["surfaces"]["startup_readme"])
    for b in m["bridges"]:
        line = next((l for l in text.splitlines() if re.match(r"\s*%d\s" % b["port"], l)), None)
        if line is None:
            f.fail("Startup/README.txt", "no port-table line for %s" % b["port"])
            continue
        if b["stdio"] not in line:
            f.fail("Startup/README.txt", "port %s line does not name %s" % (b["port"], b["stdio"]))
        for root in b.get("roots", []):
            leaf = root.rstrip("\\").split("\\")[-1]
            if leaf not in line:
                f.fail("Startup/README.txt", "port %s line does not mention root %s" % (b["port"], leaf))
        f.ok()
    ports_line = re.search(r"Confirm ([\d, and]+) are listed", text)
    if ports_line:
        listed = sorted(int(p) for p in re.findall(r"\d{4}", ports_line.group(1)))
        if listed != sorted(b["port"] for b in m["bridges"]):
            f.fail("Startup/README.txt", "Ports panel instruction lists %s" % listed)


def check_plugins(m, f):
    """Each bridge ships a Cowork connector package; its id and URL port must match."""
    seen = set()
    for b in m["bridges"]:
        path = b["plugin_manifest"]
        try:
            manifest = json.loads(read(path))
        except FileNotFoundError:
            f.fail(path, "connector manifest missing for port %d" % b["port"])
            continue
        except ValueError as exc:
            f.fail(path, "connector manifest is not valid JSON: %s" % exc)
            continue
        connectors = manifest.get("agentConnectors") or []
        if len(connectors) != 1:
            f.fail(path, "expected exactly one agentConnectors entry, found %d" % len(connectors))
            continue
        c = connectors[0]
        if c.get("id") != b["connector_id"]:
            f.fail(path, "connector id is %r, skills address %r" % (c.get("id"), b["connector_id"]))
        else:
            f.ok()
        url = ((c.get("toolSource") or {}).get("remoteMcpServer") or {}).get("mcpServerUrl", "")
        port = re.search(r"-(\d{4})\.[a-z0-9]+\.devtunnels\.ms/mcp$", url)
        if not port or int(port.group(1)) != b["port"]:
            f.fail(path, "mcpServerUrl %r does not point at port %d" % (url, b["port"]))
        else:
            f.ok()
        if str(b["port"]) not in c.get("displayName", ""):
            f.fail(path, "connector displayName does not carry the port")
        else:
            f.ok()
        app_id = manifest.get("id", "")
        if not re.fullmatch(r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}", app_id):
            f.fail(path, "app id %r is not a GUID" % app_id)
        elif app_id != PLACEHOLDER_APP_ID and app_id in seen:
            # the published template shares one placeholder; personalize.py mints a
            # distinct id per package, and two real packages must never share one
            f.fail(path, "app id %s reused by another package - each upload needs its own" % app_id)
        seen.add(app_id)
        for icon in (manifest.get("icons") or {}).values():
            if not os.path.isfile(os.path.join(ROOT, os.path.dirname(path), icon)):
                f.fail(path, "icon %s referenced but missing" % icon)


def _number(word):
    return {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}.get(word.lower(), -1)


def check_architecture(m, f):
    text = read(m["surfaces"]["architecture"])
    for b in m["bridges"]:
        if not re.search(r"G\d\[%d\]" % b["port"], text):
            f.fail("docs/architecture.md", "system diagram has no tunnel node for %s" % b["port"])
        else:
            f.ok()
    count = m["bridge_count"]
    if "## Why %s bridges remain separate" % {4: "four", 3: "three"}.get(count, count) not in text:
        f.fail("docs/architecture.md", "separation heading does not count %d bridges" % count)


def check_prose(m, f):
    phrases = [p.lower() for p in m["stale_phrases"]]
    for path in m["surfaces"]["prose"]:
        if not os.path.isfile(os.path.join(ROOT, path)):
            f.fail("prose", "%s listed as a surface but missing" % path)
            continue
        text = read(path)
        # generated blocks are regenerated from the corpus and audited there, not here
        text = re.sub(r"<!-- SKILL-LESSONS:start -->.*?<!-- SKILL-LESSONS:end -->", "", text, flags=re.S)
        text = re.sub(r"<!-- LESSON-DIGEST:BEGIN.*?<!-- LESSON-DIGEST:END[^\n]*-->", "", text, flags=re.S)
        low = text.lower()
        for p in phrases:
            if p in low:
                f.fail(path, "stale phrase present: %r" % p)
        f.ok()


def main(argv):
    try:
        with open(MANIFEST, encoding="utf-8") as fh:
            m = json.load(fh)
    except Exception as exc:  # noqa: BLE001
        print("FACTS_CHECK: COULD NOT RUN - %s" % exc)
        return 2
    f = Findings()
    for check in (check_tasks, check_watchdog, check_launchers, check_posix_launchers, check_tool_count,
                  check_readmes, check_architecture, check_prose, check_plugins):
        try:
            check(m, f)
        except FileNotFoundError as exc:
            f.fail(check.__name__, "missing surface: %s" % exc.filename)
        except Exception as exc:  # noqa: BLE001
            print("FACTS_CHECK: COULD NOT RUN - %s raised %r" % (check.__name__, exc))
            return 2
    for surface, message in f.items:
        print("  FAIL %-40s %s" % (surface, message))
    print("bridges: %d, assertions passed: %d, findings: %d"
          % (len(m["bridges"]), f.checked, len(f.items)))
    if f.items:
        print("FACTS_CHECK: FAIL")
        return 1
    print("FACTS_CHECK: CLEAN")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
