#!/usr/bin/env python3
"""
bridge_policy.py - decide whether an automatic bridge restart is ALLOWED.

Jordan authorised Cowork to start/restart bridges automatically on 2026-08-30.
This module is where that authorisation is bounded, so the decision is a table
that can be tested rather than a judgement made in the moment.

WHY THE BOUNDS EXIST (all measured, none hypothetical)

  * A restart cannot register a connector. The tool surface is fixed at session
    start. On 2026-08-18 all three bridges were LISTENING the whole time and the
    tools vanished because supergateway's 30-minute idle session expired
    server-side; the fix was a NEW CHAT. "The tool is missing from my surface"
    is therefore NEVER a reason to restart anything.

  * bridge-restart-all.bat kills the bridge running it and leaves the tunnel
    ports PRIVATE. devtunnel.exe is not installed (confirmed 2026-08-21), so
    setting them Public again is a manual step in the VS Code Ports panel that
    Cowork cannot perform. An unnecessary full restart takes working bridges off
    the air until Jordan is physically present - worse than doing nothing.

  * 8933 cannot restart itself. The restart job runs ON 8933; killing 8933 kills
    the job mid-execution and nothing survives to verify the result.

  * EADDRINUSE means a port is ALREADY HELD, i.e. healthy. Seen 2026-08-18 and
    again 2026-08-30. It is evidence against restarting, not for it.

DECISION TABLE (the whole authorisation)

  every port healthy .................. NOACTION
  8933 down ........................... REFUSE  (cannot restart the executor
                                                 from the executor)
  all three down ...................... REFUSE  (needs the manual Public-port
                                                 step; only Jordan can do it)
  8931 down, 8933 up .................. RESTART bridge-restart-8931.bat
  8932 down, 8933 up .................. RESTART bridge-restart-8932.bat
  8931 and 8932 down, 8933 up ......... RESTART both, one at a time

A port is DOWN only if it is not LISTENING, or it is listening but does not
answer a local HTTP probe (the hung case). Both are measurements, not opinions.

Usage:
    bridge_policy.py --state 8931=up,8932=down,8933=up
    bridge_policy.py --state ... --json

Exit codes:
    0  NOACTION - everything healthy, do nothing
    1  RESTART  - an automatic restart is authorised (script names on stdout)
    2  REFUSE   - a restart is needed but NOT authorised automatically
    3  bad input
"""

import argparse
import json
import sys

PORTS = ("8931", "8932", "8933")
RESTART_SCRIPT = {
    "8931": "bridge-restart-8931.bat",
    "8932": "bridge-restart-8932.bat",
}


def decide(state):
    """state: {'8931': True/False, ...} True = healthy. Returns dict."""
    for p in PORTS:
        if p not in state:
            return {"action": "ERROR", "reason": "no measurement for %s" % p,
                    "scripts": []}

    down = [p for p in PORTS if not state[p]]

    if not down:
        return {"action": "NOACTION",
                "reason": "all three bridges are listening and answering",
                "scripts": []}

    if len(down) == 3:
        return {"action": "REFUSE",
                "reason": ("all three bridges are down. A full restart leaves the "
                           "tunnel ports PRIVATE and devtunnel.exe is not installed, "
                           "so only Jordan can set them Public again. Report and "
                           "stop; do not run bridge-restart-all.bat automatically."),
                "scripts": []}

    if "8933" in down:
        return {"action": "REFUSE",
                "reason": ("8933 is down. The restart job would run ON 8933, so it "
                           "cannot restart itself and nothing would survive to "
                           "verify the result. Needs a new chat or Jordan."),
                "scripts": []}

    return {"action": "RESTART",
            "reason": ("%s down, 8933 healthy - a surgical single-port restart is "
                       "authorised and 8933 stays up to verify PID turnover."
                       % " and ".join(down)),
            "scripts": [RESTART_SCRIPT[p] for p in down]}


def parse_state(s):
    state = {}
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError("expected port=up|down, got %r" % part)
        k, v = part.split("=", 1)
        k, v = k.strip(), v.strip().lower()
        if k not in PORTS:
            raise ValueError("unknown port %r" % k)
        if v not in ("up", "down"):
            raise ValueError("expected up|down for %s, got %r" % (k, v))
        state[k] = (v == "up")
    return state


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True,
                    help="e.g. 8931=up,8932=down,8933=up")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    try:
        state = parse_state(a.state)
    except ValueError as exc:
        sys.stderr.write("FATAL: %s\n" % exc)
        return 3

    d = decide(state)
    if a.json:
        print(json.dumps(d))
    else:
        print("ACTION: %s" % d["action"])
        print("REASON: %s" % d["reason"])
        for s in d["scripts"]:
            print("SCRIPT: %s" % s)

    return {"NOACTION": 0, "RESTART": 1, "REFUSE": 2, "ERROR": 3}[d["action"]]


if __name__ == "__main__":
    sys.exit(main())
