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
    single flight (1.4.0)    a second request while a job holds the lock gets
                             EXECUTOR_BUSY and starts nothing; a stale lock whose
                             processes are gone is reclaimed; every run leaves an
                             operation record with a terminal status
    bounded replies (1.5/1.8) a clean run answers concisely, a failure answers
                             with the full bounded result, and a stream over the
                             budget is truncated in the reply but not on disk
    run_job (1.7.0)          save-and-run accepts a plain filename and refuses
                             folders, foreign extensions, reserved names, empty
                             or oversized content, extra parameters, and a script
                             that is running right now
    targeted lessons (1.6.0) attached only on a REPEATED failure of the same
                             script, and only rules in scope for this platform

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
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "Startup" / "CommandBridge" / "batch-exec-server.js"

IS_WINDOWS = os.name == "nt"
EXT = ".bat" if IS_WINDOWS else ".sh"
EXPECTED_VERSION = "1.9.0"


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

# A lessons corpus the targeted-lesson path can read: one rule everywhere, one
# scoped to the platform this suite is NOT running on. The server must serve the
# first and never the second. The shared phrase is what the failing job prints.
OTHER_PLATFORM = "linux" if IS_WINDOWS else "windows"
LESSONS_TEXT = (
    "### A\n- **Pattern-Key:** bridge-selftest-everywhere\n"
    "- **Rule:** Rule for everywhere about zebra quartz failures.\n- **Hits:** 3\n"
    "### B\n- **Pattern-Key:** bridge-selftest-other-platform\n"
    f"- **Platforms:** {OTHER_PLATFORM}\n"
    "- **Rule:** Rule for the other platform about zebra quartz failures.\n- **Hits:** 5\n"
)


class Server:
    """A live stdio MCP client for the bridge under test."""

    def __init__(self, tooling_root: Path, strip: tuple[str, ...] = ()):
        env = dict(os.environ)
        env["COWORK_ROOT"] = str(tooling_root)
        env.pop("COWORK_CONFIG_ROOT", None)
        env.pop("COWORK_ROUTE", None)
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

    def run_tool(self, tool: str, args: dict) -> tuple[str, bool, list[str]]:
        resp = self.call("tools/call", {"name": tool, "arguments": args})
        result = resp.get("result", {})
        parts = [p.get("text", "") for p in result.get("content", [])]
        return "\n".join(parts), bool(result.get("isError")), parts

    def run_job(self, name: str) -> tuple[str, bool]:
        body, is_error, _ = self.run_tool("run_batch_file", {"file": name})
        return body, is_error

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

# run_job must refuse every shape that is not "a plain filename with the
# platform extension plus non-empty content under 64 KB", and nothing else.
RUN_JOB_REFUSALS = [
    ("folder in the name", {"file": "sub" + os.sep + "x" + EXT, "content": "x"}),
    ("traversal in the name", {"file": ".." + os.sep + "x" + EXT, "content": "x"}),
    ("foreign extension", {"file": "x.py", "content": "x"}),
    ("other platform's extension", {"file": "x" + (".sh" if IS_WINDOWS else ".bat"), "content": "x"}),
    ("reserved device name", {"file": "con" + EXT, "content": "x"}),
    ("empty content", {"file": "x" + EXT, "content": ""}),
    ("content with a NUL byte", {"file": "x" + EXT, "content": "a\x00b"}),
    ("oversized content", {"file": "x" + EXT, "content": "a" * (64 * 1024 + 1)}),
    ("extra parameter", {"file": "x" + EXT, "content": "x", "timeout": 5}),
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
    lessons_dir = root / "CoworkConfig" / "cowork-memory"
    lessons_dir.mkdir(parents=True)
    (lessons_dir / "cowork-lessons.md").write_text(LESSONS_TEXT, newline="\n")
    ops = jobs / "Logs" / "ops"
    lock = jobs / "Logs" / "_executor.lock"

    declared = "2026-01-01 - Self Test"
    (jobs / f"hello{EXT}").write_text(
        job_source([echo_var("COWORK_JOB_NAME"), echo_var("COWORK_JOB_OUTPUT"),
                    write_artifact()], output_dir=declared), newline="")
    (jobs / f"fails{EXT}").write_text(
        job_source(["echo to-stderr 1>&2", "exit 3"]), newline="")
    (jobs / f"zebra{EXT}").write_text(
        job_source(["echo zebra quartz failure 1>&2", "exit 4"]), newline="")
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
    # Prints well over the 4,000-character reply budget, then fails so the full
    # bounded result (not the concise one) is what carries the stream.
    loud_line = "echo " + ("x" * 200)
    (jobs / f"loud{EXT}").write_text(job_source([loud_line] * 40 + ["exit 2"]), newline="")

    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))

    def latest_op(script: str) -> dict:
        try:
            return json.loads((ops / f"{script}.latest.json").read_text())
        except Exception:
            return {}

    def hold_lock(script_name: str, server_pid: int, job_pid: int | None, op_id: str) -> None:
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text(json.dumps({
            "op_id": op_id, "script_name": script_name, "server_pid": server_pid,
            "job_pid": job_pid, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())}))

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
        tools = listed.get("result", {}).get("tools", [])
        names = [t["name"] for t in tools]
        check("exposes exactly the two tools", names == ["run_batch_file", "run_job"], str(names))
        descs = " ".join(t.get("description", "") for t in tools)
        wrong_hint = "cd /d" if not IS_WINDOWS else "$COWORK_JOB_OUTPUT"
        check("tool text describes this platform, not the other one",
              wrong_hint not in descs.split("OPERATING RULES")[0], descs[:200])

        body, _ = server.run_job(f"hello{EXT}")
        check("approved job runs", "COWORK_JOB_NAME=hello" in body, body[:300])
        check("declared output folder is honoured", declared in body, body[:300])
        check("artifact lands in the declared folder",
              (outs / declared / "artifact.txt").is_file(), "")
        check("exit code 0 reported",
              '"exit_code": 0' in body or '"exit_code":0' in body, body[:300])
        concise = result_json(body)
        check("clean run answers concisely (no file-list fields, has op_id)",
              "op_id" in concise and "files_created" not in concise, str(sorted(concise))[:200])
        op = latest_op(f"hello{EXT}")
        check("operation record is written with a terminal status",
              op.get("status") == "COMPLETED" and op.get("exit_code") == 0
              and op.get("tool") == "run_batch_file", str(op)[:200])
        check("operation record pins the script hash",
              isinstance(op.get("sha256_run"), str) and len(op["sha256_run"]) == 64, str(op.get("sha256_run")))
        check("operation record path in the reply exists", Path(concise.get("op_record", "")).is_file(),
              concise.get("op_record", ""))
        check("lock is released after the run", not lock.exists(), "")

        body, _ = server.run_job(f"nested{os.sep}deep{EXT}")
        check("contained nested job runs", "nested-ok" in body, body[:300])

        body, is_error = server.run_job(f"fails{EXT}")
        check("non-zero exit reported",
              '"exit_code": 3' in body or '"exit_code":3' in body, body[:300])
        check("stderr captured", "to-stderr" in body, body[:300])
        bounded = result_json(body)
        check("failure answers with the full bounded result",
              is_error and "files_created" in bounded and "stdout_chars_total" in bounded,
              str(sorted(bounded))[:200])
        check("operation record of a failure says FAILED",
              latest_op(f"fails{EXT}").get("status") == "FAILED", str(latest_op(f"fails{EXT}"))[:120])

        body, _ = server.run_job(f"loud{EXT}")
        loud = result_json(body)
        check("a stream over the budget is truncated in the reply, not on disk",
              loud.get("stdout_reply_truncated") is True
              and loud.get("stdout_chars_total", 0) > len(loud.get("stdout", ""))
              and Path(loud.get("result_file", "")).is_file()
              and len(json.loads(Path(loud["result_file"]).read_text()).get("stdout", "")) == loud["stdout_chars_total"],
              str({k: loud.get(k) for k in ("stdout_reply_truncated", "stdout_chars_total")}))

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

        # ---- run_job (1.7.0) ---------------------------------------------------------
        body, is_error, _ = server.run_tool("run_job", {
            "file": f"saved{EXT}", "content": job_source(["echo saved-and-ran"])})
        check("run_job saves a new script and runs it",
              not is_error and "saved-and-ran" in body and (jobs / f"saved{EXT}").is_file(), body[:200])
        check("run_job is recorded as run_job in the operation record",
              latest_op(f"saved{EXT}").get("tool") == "run_job", str(latest_op(f"saved{EXT}"))[:120])
        for label, args in RUN_JOB_REFUSALS:
            body, is_error, _ = server.run_tool("run_job", dict(args))
            executed = '"exit_code"' in body
            check(f"run_job refuses: {label}", is_error and "REJECTED" in body.upper() and not executed, body[:160])
        check("run_job refusals saved nothing",
              not (jobs / f"x{EXT}").exists() and not (jobs / "x.py").exists(), "")

        # ---- single flight (1.4.0) ---------------------------------------------------
        before_op = latest_op(f"hello{EXT}").get("op_id")
        hold_lock(f"other{EXT}", os.getpid(), None, "held-by-selftest")
        body, is_error = server.run_job(f"hello{EXT}")
        check("a held lock answers EXECUTOR_BUSY and names the holder",
              is_error and "EXECUTOR_BUSY" in body and f"other{EXT}" in body, body[:200])
        check("a busy refusal starts nothing",
              latest_op(f"hello{EXT}").get("op_id") == before_op and '"exit_code"' not in body, "")
        check("a different script is not called the same script", "THIS SAME script" not in body, "")
        hold_lock(f"hello{EXT}", os.getpid(), None, "held-by-selftest-2")
        body, _ = server.run_job(f"hello{EXT}")
        check("the same script held is flagged so it is not rerun", "THIS SAME script" in body, body[:200])
        saved_before = (jobs / f"hello{EXT}").read_bytes()
        body, is_error, _ = server.run_tool("run_job", {"file": f"hello{EXT}", "content": "x"})
        check("run_job will not overwrite a script that is running",
              is_error and "EXECUTOR_BUSY" in body and (jobs / f"hello{EXT}").read_bytes() == saved_before, body[:160])
        hold_lock(f"other{EXT}", 999999, 999998, "stale-selftest")
        body, is_error = server.run_job(f"hello{EXT}")
        check("a stale lock (both processes gone) is reclaimed and the job runs",
              not is_error and not lock.exists() and "COWORK_JOB_NAME=hello" in body, body[:160])

        # ---- targeted lessons (1.6.0) -------------------------------------------------
        body, _, parts = server.run_tool("run_batch_file", {"file": f"zebra{EXT}"})
        check("first failure of a script carries no lessons", len(parts) == 2 and "RELEVANT LESSONS" not in body,
              str(len(parts)))
        body, _, parts = server.run_tool("run_batch_file", {"file": f"zebra{EXT}"})
        check("a repeated failure attaches matching lessons",
              len(parts) == 3 and "RELEVANT LESSONS" in parts[2] and "bridge-selftest-everywhere" in parts[2],
              body[-300:])
        check("a lesson scoped to the other platform is not served",
              "bridge-selftest-other-platform" not in body, body[-300:])
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
