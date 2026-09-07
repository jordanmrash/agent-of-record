#!/usr/bin/env python3
"""Cross-surface bridge facts check.

Every bridge fact - port, name, stateful or not, roots, tool count - is stated in
several places: the VS Code tasks, the watchdog, the .cmd launchers, two READMEs,
the architecture diagram and the skills that drive the bridges. Each restatement
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
    ports = re.findall(r'"--port",\s*"(\d+)"', text)
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


def _task_segment(text, port):
    # the block for a port runs from its "label" line to the next "label" line
    labels = [mm.start() for mm in re.finditer(r'"label"\s*:', text)]
    for i, start in enumerate(labels):
        end = labels[i + 1] if i + 1 < len(labels) else len(text)
        seg = text[start:end]
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
    for check in (check_tasks, check_watchdog, check_launchers, check_tool_count,
                  check_readmes, check_architecture, check_prose):
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
