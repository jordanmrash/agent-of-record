#!/usr/bin/env python3
"""Proof that personalize.py does what its docstring says, on a throwaway copy.

Asserts, in order: a dry run writes nothing; --apply removes every YOURUSER and
YOUR-TUNNEL-HOST from the operating trees; the OneDrive folder rename lands in
the launcher that passes it as a root; each connector package gets its own app
id and the right port; the documentation and the skill attribution lines are
untouched; the two tasks.json copies still match; scripts/facts_check.py is
CLEAN on the personalized tree; and scripts/public_scan.py refuses it - a
personalized tree must never pass the publication gate.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPY_DIRS = ["Startup", "docs", "scripts", "GitHubSetup", "CommandJobs", "CoworkConfig"]
COPY_FILES = ["README.md", "SECURITY.md", "AGENTS.md", "CONTRIBUTING.md"]
USER, HOST, ONEDRIVE = "jsmith", "abc123xy", "OneDrive - Contoso"


def make_copy():
    tmp = tempfile.mkdtemp(prefix="personalize-selftest-")
    for d in COPY_DIRS:
        shutil.copytree(os.path.join(ROOT, d), os.path.join(tmp, d),
                        ignore=shutil.ignore_patterns("__pycache__"))
    for f in COPY_FILES:
        shutil.copy2(os.path.join(ROOT, f), os.path.join(tmp, f))
    return tmp


def tree_hashes(tree):
    out = {}
    for dirpath, _, files in os.walk(tree):
        for name in files:
            p = os.path.join(dirpath, name)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, tree)] = hashlib.sha256(fh.read()).hexdigest()
    return out


def run(tree, *argv):
    proc = subprocess.run([sys.executable] + list(argv), capture_output=True, text=True, cwd=tree)
    return proc.returncode, proc.stdout + proc.stderr


def grep_tree(tree, needle, subdirs):
    hits = []
    for d in subdirs:
        for dirpath, _, files in os.walk(os.path.join(tree, d)):
            for name in files:
                if name.lower().endswith((".png", ".ico")):
                    continue
                p = os.path.join(dirpath, name)
                with open(p, "rb") as fh:
                    if needle.encode() in fh.read():
                        hits.append(os.path.relpath(p, tree))
    return hits


def read(tree, rel):
    with open(os.path.join(tree, rel), encoding="utf-8") as fh:
        return fh.read()


def main():
    failures = []

    def check(cond, name):
        print("  %s  %s" % ("ok  " if cond else "FAIL", name))
        if not cond:
            failures.append(name)

    tree = make_copy()
    try:
        script = os.path.join(tree, "scripts", "personalize.py")
        before = tree_hashes(tree)
        rc, out = run(tree, script, "--user", USER, "--tunnel-host", HOST, "--onedrive-folder", ONEDRIVE)
        check(rc == 0 and "dry run" in out, "dry run exits 0 and says so")
        check(tree_hashes(tree) == before, "dry run writes nothing")

        rc, out = run(tree, script, "--user", "YOURUSER", "--apply")
        check(rc == 2 and tree_hashes(tree) == before, "the placeholder itself is refused as a user name")

        rc, out = run(tree, script, "--user", USER, "--tunnel-host", HOST,
                      "--onedrive-folder", ONEDRIVE, "--apply")
        check(rc == 0 and "applied" in out, "apply exits 0")
        check("WARNING" not in out, "apply reports no leftover placeholders")

        scope = ["Startup", "CommandJobs", "CoworkConfig"]
        check(not grep_tree(tree, "YOURUSER", scope), "no YOURUSER remains in the operating trees")
        check(not grep_tree(tree, "YOUR-TUNNEL-HOST", scope), "no YOUR-TUNNEL-HOST remains in the operating trees")

        fs = read(tree, "Startup/fs-server.cmd")
        check("C:\\Users\\%s\\%s\\Documents\\Cowork" % (USER, ONEDRIVE) in fs,
              "filesystem launcher passes the renamed OneDrive root")
        check("C:\\Users\\%s\\Documents\\COPILOT_COWORK" % USER in fs, "filesystem launcher passes the tooling root")

        tasks = read(tree, "Startup/.vscode/tasks.json")
        check(tasks == read(tree, "Startup/KnownGood/tasks.json"), "live and known-good tasks.json still identical")
        check("C:\\\\Users\\\\%s\\\\" % USER in tasks, "tasks.json keeps JSON-escaped backslashes")

        ids = set()
        manifests_ok = True
        for name in ("playwright-8931", "filesystem-8932", "command-8933", "power-automate-8934"):
            m = json.loads(read(tree, "Startup/Plugins/%s/manifest.json" % name))
            port = name.rsplit("-", 1)[1]
            url = m["agentConnectors"][0]["toolSource"]["remoteMcpServer"]["mcpServerUrl"]
            manifests_ok &= url == "https://%s-%s.use.devtunnels.ms/mcp" % (HOST, port)
            manifests_ok &= bool(re.fullmatch(r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}", m["id"]))
            manifests_ok &= m["id"] != "00000000-0000-4000-8000-000000000000"
            ids.add(m["id"])
        check(manifests_ok, "each connector package points at its port on the given host with a real app id")
        check(len(ids) == 4, "the four app ids are distinct")

        check("YOURUSER" in read(tree, "AGENTS.md") and "YOURUSER" in read(tree, "docs/quickstart.md"),
              "documentation that explains the placeholders is untouched")
        check('author-email: "you@example.com"' in read(tree, "CoworkConfig/Skills/dream-cycle/SKILL.md"),
              "skill attribution email is untouched")
        check("YOURUSER" in read(tree, "scripts/public_scan.py"), "the sanitizer's own patterns are untouched")

        rc, out = run(tree, os.path.join(tree, "scripts", "facts_check.py"))
        check(rc == 0, "facts_check is CLEAN on the personalized tree")
        rc, out = run(tree, os.path.join(tree, "scripts", "public_scan.py"))
        check(rc != 0 and "non-placeholder Windows user path" in out, "public_scan refuses the personalized tree")

        rc, out = run(tree, script, "--user", USER, "--tunnel-host", HOST, "--onedrive-folder", ONEDRIVE, "--apply")
        check(rc == 0 and "files changed: 0" in out, "a second apply finds nothing left to do")
    finally:
        shutil.rmtree(tree, ignore_errors=True)

    if failures:
        print("PERSONALIZE_SELFTEST: FAIL (%d)" % len(failures))
        return 1
    print("PERSONALIZE_SELFTEST: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
