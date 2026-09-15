#!/usr/bin/env python3
"""Negative controls for facts_check.py.

A checker nobody has tried to fool is an assumption. This runs the check on a
pristine copy of the repository (positive control - must pass), then on copies
with one fact broken at a time, asserting each break is caught and named.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join("scripts", "facts_check.py")
COPY_DIRS = ["Startup", "docs", "scripts", "GitHubSetup", "CommandJobs", "CoworkConfig"]
COPY_FILES = ["README.md", "SECURITY.md"]


def make_copy():
    tmp = tempfile.mkdtemp(prefix="facts-selftest-")
    for d in COPY_DIRS:
        shutil.copytree(os.path.join(ROOT, d), os.path.join(tmp, d),
                        ignore=shutil.ignore_patterns("__pycache__"))
    for f in COPY_FILES:
        shutil.copy2(os.path.join(ROOT, f), os.path.join(tmp, f))
    return tmp


def run(tree):
    proc = subprocess.run([sys.executable, os.path.join(tree, CHECK)],
                          capture_output=True, text=True, cwd=tree)
    return proc.returncode, proc.stdout + proc.stderr


def edit(tree, rel, old, new):
    path = os.path.join(tree, rel)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    assert text.count(old) >= 1, "fixture anchor missing in %s: %r" % (rel, old)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text.replace(old, new, 1))


CASES = [
    ("watchdog drops a port",
     lambda t: edit(t, "Startup/_bridge-watchdog.ps1", "Port = 8934;", "Port = 8944;"),
     r"port 8934 has no entry"),
    ("tasks.json flips 8932 to stateful",
     lambda t: edit(t, "Startup/.vscode/tasks.json", '"--port", "8932",', '"--port", "8932", "--stateful",'),
     r"8932 is stateless in the manifest but stateful"),
    ("known-good snapshot drifts from live",
     lambda t: edit(t, "Startup/KnownGood/tasks.json", '"--port", "8933"', '"--port", "8933" '),
     r"KnownGood/tasks.json differ"),
    ("README row understates the tool count",
     lambda t: edit(t, "README.md", "Own code, 29 tools", "Own code, 28 tools"),
     r"says 28 tools, server registers 29"),
    ("README row calls 8931 stateless",
     lambda t: edit(t, "README.md", "Upstream `@playwright/mcp`, stateful", "Upstream `@playwright/mcp`, stateless"),
     r"port 8931 row does not say stateful"),
    ("stale phrase returns to a skill",
     lambda t: edit(t, "CoworkConfig/Skills/command-bridge/SKILL.md", "## Guardrails", "## Guardrails\n\n- Port 8934 does not exist."),
     r"stale phrase present: 'port 8934 does not exist'"),
    # Anchored on the command line that starts the server: the variable is also
    # named in the `if defined` guard above it, and a root that survives only
    # there was never handed to the server.
    ("launcher loses a filesystem root",
     lambda t: edit(t, "Startup/fs-server.cmd", ' "%COWORK_CONFIG_ROOT%"', ""),
     r"does not pass root %COWORK_CONFIG_ROOT%"),
    # --- the Windows half of the derivation rule. Each of these is a launcher
    # that works only for a clone at one exact path after personalize.py. ---
    ("a Windows launcher hard-codes a C:\\Users root instead of deriving it",
     lambda t: edit(t, "Startup/exec-server.cmd",
                    'cd /d "%COWORK_ROOT%\\CommandJobs"',
                    'cd /d "C:\\Users\\YOURUSER\\Documents\\COPILOT_COWORK\\CommandJobs"'),
     r"exec-server\.cmd carries a C:\\Users\\ path"),
    ("a Windows launcher never sets COWORK_ROOT",
     lambda t: edit(t, "Startup/pw-server.cmd",
                    'set "COWORK_ROOT=%%~fI"',
                    'set "COWORK_ROOT_UNUSED=%%~fI"'),
     r"pw-server\.cmd does not derive COWORK_ROOT from %~dp0"),
    ("Startup README drops a port line",
     lambda t: edit(t, "Startup/README.txt", "  8934  Power Automate  flow-server.cmd", "  8935  Power Automate  flow-server.cmd"),
     r"no port-table line for 8934"),
    ("connector package points at the wrong port",
     lambda t: edit(t, "Startup/Plugins/command-8933/manifest.json", "YOUR-TUNNEL-HOST-8933.", "YOUR-TUNNEL-HOST-8932."),
     r"does not point at port 8933"),
    ("connector id drifts from the name the skills address",
     lambda t: edit(t, "Startup/Plugins/filesystem-8932/manifest.json", '"jordan-local-filesystem-8932-v1"', '"jordan-local-filesystem-8932-v2"'),
     r"skills address 'jordan-local-filesystem-8932-v1'"),
    ("two personalized packages share one app id",
     lambda t: (edit(t, "Startup/Plugins/playwright-8931/manifest.json", "00000000-0000-4000-8000-000000000000", "5b1c9d2e-7f3a-4c8b-9e1d-2a3b4c5d6e7f"),
                edit(t, "Startup/Plugins/command-8933/manifest.json", "00000000-0000-4000-8000-000000000000", "5b1c9d2e-7f3a-4c8b-9e1d-2a3b4c5d6e7f")),
     r"reused by another package"),
    # --- the portable half. Each of these is a way the macOS claim rots. ---
    ("a POSIX launcher is missing",
     lambda t: os.remove(os.path.join(t, "Startup", "posix", "exec-server.sh")),
     r"posix[\\/]exec-server\.sh is missing"),
    # Anchored on the executable line, not the header comment: the check reads
    # only live lines, so a fixture that edits a comment proves nothing.
    ("a POSIX launcher starts the wrong server",
     lambda t: edit(t, "Startup/posix/exec-server.sh",
                    'exec "$NODE_BIN" "$COWORK_ROOT/Startup/CommandBridge/batch-exec-server.js"',
                    'exec "$NODE_BIN" "$COWORK_ROOT/Startup/CommandBridge/some-other-server.js"'),
     r"does not start Startup/CommandBridge/batch-exec-server\.js"),
    ("a POSIX launcher hard-codes a root instead of deriving it",
     lambda t: edit(t, "Startup/posix/exec-server.sh",
                    'COWORK_ROOT="$(cd "$HERE/../.." && pwd)"',
                    'COWORK_ROOT="/opt/cowork"'),
     r"does not derive COWORK_ROOT from its own location"),
    ("the manifest loses a POSIX launcher entry",
     lambda t: edit(t, "docs/bridge-facts.json",
                    '"stdio_posix": "posix/exec-server.sh"',
                    '"stdio_posix_removed": "posix/exec-server.sh"'),
     r"port 8933 has no stdio_posix"),
    ("tasks.json loses its macOS override, so a Mac runs the .cmd launchers",
     lambda t: edit(t, "Startup/.vscode/tasks.json", '"osx"', '"osx_disabled"'),
     r"no osx override"),
    # --- the two axes. A bridge that exists for one product on one platform must not
    # grow a launcher, a task variant or a paragraph on a surface where it does not. ---
    ("a Windows-only bridge names a POSIX launcher again",
     lambda t: edit(t, "docs/bridge-facts.json",
                    '"watchdog_name": "FlowAuto"',
                    '"watchdog_name": "FlowAuto",\n      "stdio_posix": "posix/flow-server.sh"'),
     r"port 8934 is not a macOS bridge but names a POSIX launcher"),
    ("a Claude page describes the Copilot-only bridge",
     lambda t: edit(t, "docs/install/claude-cowork-mac.md", "## 1. Prerequisites",
                    "## 1. Prerequisites\n\nRegister port 8934 as well.\n"),
     r"stale phrase present: '8934'"),
    ("tasks.json gives the Windows-only bridge a macOS variant",
     lambda t: (edit(t, "Startup/.vscode/tasks.json", '"label": "Cowork Power Automate Bridge (8934)",',
                     '"label": "Cowork Power Automate Bridge (8934)", "osx": {},'),
                edit(t, "Startup/KnownGood/tasks.json", '"label": "Cowork Power Automate Bridge (8934)",',
                     '"label": "Cowork Power Automate Bridge (8934)", "osx": {},')),
     r"port 8934 is Windows-only but tasks.json gives it a macOS/Linux variant"),
]


def main():
    tree = make_copy()
    try:
        rc, out = run(tree)
        if rc != 0:
            print("POSITIVE CONTROL FAILED - the pristine tree does not pass:\n" + out)
            return 1
        print("positive control: pristine copy passes")
    finally:
        shutil.rmtree(tree, ignore_errors=True)

    failures = 0
    for name, mutate, expect in CASES:
        tree = make_copy()
        try:
            mutate(tree)
            rc, out = run(tree)
            caught = rc == 1 and re.search(expect, out) is not None
            print("  %s  %s" % ("ok  " if caught else "MISS", name))
            if not caught:
                failures += 1
                print("        expected rc=1 and /%s/, got rc=%d\n%s" % (expect, rc, out))
        finally:
            shutil.rmtree(tree, ignore_errors=True)

    total = len(CASES)
    print("%d/%d negative controls caught" % (total - failures, total))
    if failures:
        print("FACTS_SELFTEST: FAIL")
        return 1
    print("FACTS_SELFTEST: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
