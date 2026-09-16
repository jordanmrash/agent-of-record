#!/bin/bash
# COWORK_OUTPUT: ../Outputs/Mac Evidence 2026-09-15
# Measure which server-filesystem releases emit a USABLE inputSchema.
# Versions come from VERSIONS.txt beside this script, one per line.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

python3 - <<'PY'
import json, os, subprocess, time, pathlib
vers = [v.strip() for v in pathlib.Path("CommandJobs/VERSIONS.txt").read_text().split() if v.strip()]
root = os.getcwd()
for v in vers:
    env = dict(os.environ); env["COWORK_ROOT"] = root; env["COWORK_FS_SERVER_VERSION"] = v
    try:
        p = subprocess.Popen(["Startup/posix/fs-server.sh"], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                             bufsize=1, env=env)
        def send(o): p.stdin.write(json.dumps(o)+"\n"); p.stdin.flush()
        send({"jsonrpc":"2.0","id":1,"method":"initialize","params":{
              "protocolVersion":"2025-06-18","capabilities":{},
              "clientInfo":{"name":"measure","version":"1"}}})
        tools=None; deadline=time.time()+75
        while time.time()<deadline:
            line=p.stdout.readline()
            if not line: break
            try: m=json.loads(line.strip())
            except Exception: continue
            if m.get("id")==1: send({"jsonrpc":"2.0","id":2,"method":"tools/list"})
            elif m.get("id")==2: tools=m.get("result",{}).get("tools",[]); break
        p.stdin.close(); p.kill()
    except Exception as e:
        print(f"{v:<14} ERROR {e}"); continue
    if tools is None:
        print(f"{v:<14} no tools/list response"); continue
    bad_in  = [t["name"] for t in tools if (t.get("inputSchema") or {}).get("type") != "object"]
    d7      = [t["name"] for t in tools if "draft-07" in str((t.get("inputSchema") or {}).get("$schema"))]
    out_d7  = [t["name"] for t in tools if "draft-07" in str((t.get("outputSchema") or {}).get("$schema"))]
    verdict = "USABLE" if not bad_in and not out_d7 else "BROKEN"
    print(f"{v:<14} {verdict:<7} tools={len(tools):<3} inputSchema-missing-type={len(bad_in):<3} input-draft07={len(d7):<3} output-draft07={len(out_d7)}")
PY
