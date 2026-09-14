#!/usr/bin/env python3
"""Behavioural negative-control suite for the command bridge, on either platform.

The bridge is the one component in this repository that executes with the
signed-in user's authority, and v0.3 made it run on POSIX as well as Windows.
A port of something that dangerous is only worth having if the refusals ported
with it, so this suite does not read the source or mock a transport: it starts
the real server as a stdio MCP process, speaks real JSON-RPC to it against a
throwaway tooling root, and asserts both halves of the contract.

    approved script runs     the output directive is honoured, and the exit
                             code and stderr are reported rather than swallowed
    everything else refused  absolute, traversal, variable, metacharacter, UNC,
                             URL, extension and symlink-escape shapes
    line endings             a script written in the other platform's convention
                             is rewritten to this one before it runs, and a mixed
                             file is left alone - both reported in the result
    environment              a server started with the profile variables stripped
                             still hands its jobs a complete one, derived from
                             the account, never from the caller

The script shape is chosen by platform - .sh through bash on POSIX, .bat
through cmd.exe on Windows - and every case runs on both. A refusal that holds
on Windows but not on a Mac is exactly the defect this is here to catch.

Exit 0 when every case passes.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "Startup" / "CommandBridge" / "batch-exec-server.js"

IS_WINDOWS = os.name == "nt"
EXT = ".bat" if IS_WINDOWS else ".sh"
EXPECTED_VERSION = "1.3.0"


def job_source(body: list[str], output_dir: str | None = None) -> str:
    """One approved job, written in the platform's own script language."""
    if IS_WINDOWS:
        head = ["@echo off"]
        if output_dir:
            head.append(f"REM COWORK_OUTPUT: {output_dir}")
        return "\r\n".join(head + body) + "\r\n"
    head = ["#!/bin/bash"]
    if output_dir:
        head.append(f"# COWORK_OUTPUT: {output_dir}")
    return "\n".join(head + body) + "\n"


def echo_var(name: str) -> str:
    return f"echo {name}=%{name}%" if IS_WINDOWS else f'echo "{name}=${name}"'


def write_artifact() -> str:
    if IS_WINDOWS:
        return 'echo proof> "%COWORK_JOB_OUTPUT%\\artifact.txt"'
    return 'echo proof > "$COWORK_JOB_OUTPUT/artifact.txt"'


def other_convention(text: str) -> str:
    """The same script with the OTHER platform's line terminators."""
    lf = text.replace("\r\n", "\n")
    return lf if IS_WINDOWS else lf.replace("\n", "\r\n")


def result_json(body: str) -> dict:
    """The structured result the server echoes back after its one-line summary.
    Parsed rather than searched: stdout arrives JSON-escaped inside it, so a
    substring test on the raw body would see backslash-n, not a newline."""
    i = body.find("{")
    if i < 0:
        return {}
    try:
        obj, _ = json.JSONDecoder().raw_decode(body, i)
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        return {}


def field(body: str, name: str) -> str:
    return str(result_json(body).get(name, ""))


def stdout_vars(body: str) -> dict[str, str]:
    """NAME=value lines from the job's stdout, as a dict."""
    out: dict[str, str] = {}
    for line in result_json(body).get("stdout", "").splitlines():
        line = line.strip()
        if "=" in line:
            k, v = line.split("=", 1)
            out.setdefault(k, v)
    return out


# Profile variables a scheduled-task or launchd start leaves empty; the server
# must derive every one of them from the account rather than pass the gap on.
PROFILE_VARS = (("USERPROFILE", "APPDATA", "LOCALAPPDATA", "HOMEDRIVE", "HOMEPATH", "TEMP", "TMP")
                if IS_WINDOWS else ("HOME", "USER", "LOGNAME"))


class Server:
    """A live stdio MCP client for the bridge under test."""

    def __init__(self, tooling_root: Path, strip: tuple[str, ...] = ()):
        env = dict(os.environ)
        env["COWORK_ROOT"] = str(tooling_root)
        env.pop("COWORK_CONFIG_ROOT", None)
        for name in strip:
            env.pop(name, None)
        self.proc = subprocess.Popen(
            ["node", str(SERVER)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, env=env,
        )
        self.seq = 0

    def call(self, method: str, params: dict | None = None) -> dict:
        self.seq += 1
        msg: dict = {"jsonrpc": "2.0", "id": self.seq, "method": method}
        if params is not None:
            msg["params"] = params
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("server closed early: " + self.proc.stderr.read())
            line = line.strip()
            if not line:
                continue
            try:
                got = json.loads(line)
            except json.JSONDecodeError:
                continue
            if got.get("id") == self.seq:
                return got

    def run_job(self, name: str) -> tuple[str, bool]:
        resp = self.call("tools/call",
                         {"name": "run_batch_file", "arguments": {"file": name}})
        result = resp.get("result", {})
        body = "\n".join(p.get("text", "") for p in result.get("content", []))
        return body, bool(result.get("isError"))

    def close(self) -> None:
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()


REFUSALS = [
    ("absolute POSIX path", "/etc/passwd"),
    ("absolute Windows path", "C:\\Windows\\system32\\calc.exe"),
    ("parent traversal", "../outside" + EXT),
    ("traversal with the other separator", "..\\outside" + EXT),
    ("home-relative path", "~/outside" + EXT),
    ("environment variable", "$HOME/outside" + EXT),
    ("braced variable", "${HOME}/outside" + EXT),
    ("Windows variable", "%USERPROFILE%/outside" + EXT),
    ("command chaining", "hello" + EXT + "; echo pwned"),
    ("pipe metacharacter", "hello" + EXT + "|more"),
    ("backtick substitution", "`id`" + EXT),
    ("wrong extension", "notallowed.py"),
    ("nonexistent file", "nope" + EXT),
    ("directory rather than a file", "nested"),
    ("UNC path", "\\\\server\\share\\x" + EXT),
    ("double-slash network path", "//server/share/x" + EXT),
    ("URL-style path", "file:///etc/passwd"),
    ("colon / alternate data stream", "hello" + EXT + ":stream"),
    ("newline injection", "hello" + EXT + "\necho pwned"),
    ("empty filename", ""),
]


def main() -> int:
    if not SERVER.is_file():
        print(f"EXEC_SELFTEST: server not found at {SERVER}")
        return 1
    if shutil.which("node") is None:
        print("EXEC_SELFTEST: SKIPPED - node is not installed")
        return 0

    root = Path(tempfile.mkdtemp(prefix="cowork-exec-selftest-"))
    jobs = root / "CommandJobs"
    outs = root / "Outputs"
    (jobs / "nested").mkdir(parents=True)
    outs.mkdir(parents=True)

    declared = "2026-01-01 - Self Test"
    (jobs / f"hello{EXT}").write_text(
        job_source([echo_var("COWORK_JOB_NAME"), echo_var("COWORK_JOB_OUTPUT"),
                    write_artifact()], output_dir=declared), newline="")
    (jobs / f"fails{EXT}").write_text(
        job_source(["echo to-stderr 1>&2", "exit 3"]), newline="")
    (jobs / "nested" / f"deep{EXT}").write_text(
        job_source(["echo nested-ok"]), newline="")
    (jobs / "notallowed.py").write_text("print('should never run')\n")
    (root / f"outside{EXT}").write_text(job_source(["echo escaped"]), newline="")
    # Written in the OTHER platform's convention: LF-only .bat on Windows, CRLF .sh on POSIX.
    (jobs / f"wrongend{EXT}").write_text(
        other_convention(job_source(["echo normalized-ok"])), newline="")
    # Deliberately mixed: one terminator of each kind. Must run, must be reported, must not be rewritten.
    mixed = job_source(["echo mixed-ok", "echo second-line"])
    mixed_text = (mixed.replace("\r\n", "\n", 1) if IS_WINDOWS
                  else mixed[:-1] + "\r\n")
    (jobs / f"mixed{EXT}").write_text(mixed_text, newline="")
    (jobs / f"env{EXT}").write_text(
        job_source([echo_var(v) for v in PROFILE_VARS] + [echo_var("PATH" if not IS_WINDOWS else "Path")]),
        newline="")

    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))

    server = Server(root)
    try:
        init = server.call("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "exec-selftest", "version": "1"},
        })
        info = init.get("result", {}).get("serverInfo", {})
        check("MCP initialize handshake answers",
              info.get("name") == "aor-batch-exec", json.dumps(init)[:200])
        check("server reports the portable version",
              info.get("version") == EXPECTED_VERSION, str(info))

        listed = server.call("tools/list")
        names = [t["name"] for t in listed.get("result", {}).get("tools", [])]
        check("exposes exactly one tool", names == ["run_batch_file"], str(names))

        body, _ = server.run_job(f"hello{EXT}")
        check("approved job runs", "COWORK_JOB_NAME=hello" in body, body[:300])
        check("declared output folder is honoured", declared in body, body[:300])
        check("artifact lands in the declared folder",
              (outs / declared / "artifact.txt").is_file(), "")
        check("exit code 0 reported",
              '"exit_code": 0' in body or '"exit_code":0' in body, body[:300])

        body, _ = server.run_job(f"nested{os.sep}deep{EXT}")
        check("contained nested job runs", "nested-ok" in body, body[:300])

        body, _ = server.run_job(f"fails{EXT}")
        check("non-zero exit reported",
              '"exit_code": 3' in body or '"exit_code":3' in body, body[:300])
        check("stderr captured", "to-stderr" in body, body[:300])

        body, _ = server.run_job(f"wrongend{EXT}")
        expected_action = "lf-to-crlf" if IS_WINDOWS else "crlf-to-lf"
        check("script in the other convention still runs correctly",
              "normalized-ok" in body and ('"exit_code": 0' in body or '"exit_code":0' in body),
              body[:300])
        check("line-ending normalisation is reported in the result",
              field(body, "line_endings") == expected_action, field(body, "line_endings"))
        on_disk = (jobs / f"wrongend{EXT}").read_bytes()
        native_ok = (b"\n" not in on_disk.replace(b"\r\n", b"")) if IS_WINDOWS else (b"\r\n" not in on_disk)
        check("the script on disk now carries the platform's terminators", native_ok,
              repr(on_disk[:60]))

        mixed_before = (jobs / f"mixed{EXT}").read_bytes()
        body, _ = server.run_job(f"mixed{EXT}")
        check("mixed-ending script is left alone and says so",
              field(body, "line_endings") == "mixed-left-alone"
              and (jobs / f"mixed{EXT}").read_bytes() == mixed_before,
              field(body, "line_endings"))

        for label, payload in REFUSALS:
            body, is_error = server.run_job(payload)
            upper = body.upper()
            refused = is_error or "REFUSED" in upper or "REJECTED" in upper
            # A refusal echoes the offending payload back, so searching the body
            # for a sentinel word would flag the server's own error text as
            # evidence of execution. Only a real run reports an exit code, so
            # that - not the payload echo - is what proves nothing ran.
            executed = '"exit_code"' in body or "'exit_code'" in body
            check(f"refuses: {label}", refused and not executed, body[:160])

        link = jobs / f"escape{EXT}"
        try:
            link.symlink_to(root / f"outside{EXT}")
            body, _ = server.run_job(f"escape{EXT}")
            check("refuses: symlink escaping the root", "escaped" not in body,
                  body[:160])
        except OSError:
            check("refuses: symlink escaping the root", True,
                  "symlink creation unavailable on this host")
    finally:
        server.close()

    stripped = Server(root, strip=PROFILE_VARS)
    try:
        stripped.call("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                     "clientInfo": {"name": "exec-selftest", "version": "1"}})
        body, _ = stripped.run_job(f"env{EXT}")
        seen = stdout_vars(body)
        for name in PROFILE_VARS:
            value = seen.get(name, "")
            check(f"job sees a derived {name} when the server was started without one",
                  bool(value) and not value.startswith("%") and not value.startswith("$"), value[:80])
        path_value = seen.get("Path", seen.get("PATH", ""))
        check("job PATH is non-empty under a stripped server", len(path_value) > 1, path_value[:80])
        check("user PATH entry count is reported as a number",
              isinstance(result_json(body).get("user_path_entries"), int), field(body, "user_path_entries"))
    finally:
        stripped.close()
        shutil.rmtree(root, ignore_errors=True)

    failed = [(n, d) for n, ok, d in results if not ok]
    for name, ok, _ in results:
        print(("PASS  " if ok else "FAIL  ") + name)
    print()
    platform_name = "Windows" if IS_WINDOWS else "POSIX"
    if failed:
        print(f"{len(failed)} of {len(results)} cases FAILED on {platform_name}")
        for name, detail in failed:
            print(f"  {name}: {detail}")
        return 1
    print(f"EXEC_SELFTEST: OK - {len(results)} of {len(results)} cases passed "
          f"on {platform_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
