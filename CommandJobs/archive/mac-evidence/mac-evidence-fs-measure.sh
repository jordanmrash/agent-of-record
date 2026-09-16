#!/bin/bash
# COWORK_OUTPUT: ../Outputs/Mac Evidence 2026-09-15
# Measure the PINNED filesystem server's actual tools/list shape.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
OUT="$COWORK_JOB_OUTPUT/fs-tools-list-$(date +%Y%m%d-%H%M%S).json"

python3 - "$OUT" <<'PY'
import json, os, subprocess, sys, time
out_path = sys.argv[1]
root = os.getcwd()
env = dict(os.environ); env["COWORK_ROOT"] = root
p = subprocess.Popen(["Startup/posix/fs-server.sh"], stdin=subprocess.PIPE,
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                     bufsize=1, env=env)
def send(o): p.stdin.write(json.dumps(o)+"\n"); p.stdin.flush()
send({"jsonrpc":"2.0","id":1,"method":"initialize","params":{
      "protocolVersion":"2025-06-18","capabilities":{},
      "clientInfo":{"name":"measure","version":"1"}}})
tools=None; info=None; deadline=time.time()+60
while time.time()<deadline:
    line=p.stdout.readline()
    if not line: break
    try: m=json.loads(line.strip())
    except Exception: continue
    if m.get("id")==1:
        info=m.get("result",{}).get("serverInfo",{})
        send({"jsonrpc":"2.0","id":2,"method":"tools/list"})
    elif m.get("id")==2:
        tools=m.get("result",{}).get("tools",[]); break
p.stdin.close(); p.kill()

print("serverInfo:", json.dumps(info))
print("tool count:", len(tools or []))
if tools:
    t0=tools[0]
    print("\n--- tools[0] name:", t0.get("name"))
    print("--- tools[0].inputSchema (verbatim) ---")
    print(json.dumps(t0.get("inputSchema"), indent=2)[:1200])
    print("\n--- per-tool: does inputSchema have type=='object'? ---")
    for t in tools:
        s=t.get("inputSchema") or {}
        print(f"  {t.get('name'):<28} type={s.get('type')!r:<12} $schema={s.get('$schema')}")
        print(f"  {'':<28} outputSchema={'yes' if t.get('outputSchema') else 'no'}")
    json.dump(tools, open(out_path,"w"), indent=2)
    print("\nwrote", out_path)
PY
