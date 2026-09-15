#!/bin/bash
# COWORK_OUTPUT: ../Outputs/Mac Evidence 2026-09-15
# Hypothesis: 2025.8.21 emits empty schemas because zod-to-json-schema@3 is fed
# zod 4 internals (pulled in by @modelcontextprotocol/sdk). Force zod 3 and re-measure.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"

DIR="$(mktemp -d)"
cd "$DIR"
cat > package.json <<'JSON'
{
  "name": "fs-server-probe",
  "private": true,
  "dependencies": { "@modelcontextprotocol/server-filesystem": "2025.8.21" },
  "overrides": { "zod": "^3.25.0" }
}
JSON
npm install --silent >/dev/null 2>&1
echo "server-filesystem: $(node -p "require('./node_modules/@modelcontextprotocol/server-filesystem/package.json').version")"
echo "zod:               $(node -p "require('./node_modules/zod/package.json').version")"
echo "zod-to-json-schema:$(node -p "require('./node_modules/zod-to-json-schema/package.json').version")"
echo

BIN="$DIR/node_modules/.bin/mcp-server-filesystem"
[ -x "$BIN" ] || BIN="$(ls -1 "$DIR"/node_modules/@modelcontextprotocol/server-filesystem/dist/*.js 2>/dev/null | head -1)"
echo "launching: $BIN"

python3 - "$BIN" "$REPO" <<'PY'
import json, subprocess, sys, time, os
bin_path, root = sys.argv[1], sys.argv[2]
cmd = [bin_path, root] if not bin_path.endswith(".js") else ["node", bin_path, root]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE, text=True, bufsize=1)
def send(o): p.stdin.write(json.dumps(o)+"\n"); p.stdin.flush()
send({"jsonrpc":"2.0","id":1,"method":"initialize","params":{
      "protocolVersion":"2025-06-18","capabilities":{},
      "clientInfo":{"name":"probe","version":"1"}}})
tools=None; deadline=time.time()+60
while time.time()<deadline:
    line=p.stdout.readline()
    if not line: break
    try: m=json.loads(line.strip())
    except Exception: continue
    if m.get("id")==1: send({"jsonrpc":"2.0","id":2,"method":"tools/list"})
    elif m.get("id")==2: tools=m.get("result",{}).get("tools",[]); break
p.stdin.close(); p.kill()
if tools is None:
    print("NO RESPONSE"); raise SystemExit
bad=[t["name"] for t in tools if (t.get("inputSchema") or {}).get("type")!="object"]
d7=[t["name"] for t in tools if "draft-07" in str((t.get("inputSchema") or {}).get("$schema"))]
print(f"tools={len(tools)}  missing-type={len(bad)}  input-draft07={len(d7)}")
print("\ntools[0] inputSchema:")
print(json.dumps(tools[0].get("inputSchema"), indent=2)[:700])
PY
cd "$REPO"; rm -rf "$DIR" 2>/dev/null || true
