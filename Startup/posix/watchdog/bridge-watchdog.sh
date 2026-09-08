#!/usr/bin/env bash
# ============================================================
#  Cowork bridge watchdog (macOS / Linux)
#  POSIX sibling of ../../_bridge-watchdog.ps1
#
#  Probes the four ports and starts a listener ONLY on a port
#  that refuses connections. It never kills anything, and it
#  will not restart the same port twice inside the cooldown
#  window - a port that dies repeatedly is a fault to read
#  about, not one to paper over with a restart loop.
#
#  WHAT IT CANNOT DO, and neither can its Windows counterpart:
#    - restore dev tunnel visibility. A port reset to Private
#      still answers locally, so this sees a healthy listener
#      while Cowork sees nothing. Only a person can set it
#      Public again in the VS Code Ports panel.
#    - help when VS Code is closed. It starts the stdio server
#      behind supergateway, not the editor session.
#
#  Writes status.txt beside itself on every run. Trust that file
#  over any note in this header.
# ============================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POSIX_DIR="$(cd "$HERE/.." && pwd)"
STARTUP="$(cd "$POSIX_DIR/.." && pwd)"
COWORK_ROOT="$(cd "$STARTUP/.." && pwd)"
export COWORK_ROOT

LOG_DIR="$HERE/logs"
STATUS_FILE="$HERE/status.txt"
COOLDOWN_SECONDS=300
SUPERGATEWAY="$STARTUP/node_modules/supergateway/dist/index.js"

mkdir -p "$LOG_DIR"

# port:name:launcher:stateful  -- kept in the same order as bridge-facts.json
BRIDGES=(
  "8931:Playwright:pw-server.sh:true"
  "8932:Filesystem:fs-server.sh:false"
  "8933:Command:exec-server.sh:false"
  "8934:FlowAuto:flow-server.sh:false"
)

now() { date +%s; }
stamp() { date "+%Y-%m-%d %H:%M:%S"; }

port_is_listening() {
  local port="$1"
  if command -v nc >/dev/null 2>&1; then
    nc -z -w 2 127.0.0.1 "$port" >/dev/null 2>&1 && return 0
    return 1
  fi
  # Fall back to bash's own /dev/tcp if netcat is absent.
  (exec 3<>"/dev/tcp/127.0.0.1/$port") >/dev/null 2>&1 && { exec 3>&- ; return 0; }
  return 1
}

start_bridge() {
  local port="$1" launcher="$2" stateful="$3"
  local args=("$SUPERGATEWAY" --port "$port"
              --outputTransport streamableHttp)
  if [ "$stateful" = "true" ]; then
    args+=(--stateful --sessionTimeout 1800000)
  fi
  args+=(--stdio "$POSIX_DIR/$launcher")

  nohup node "${args[@]}" \
    >>"$LOG_DIR/$port.log" 2>&1 &
  disown 2>/dev/null || true
}

STATUS=("Cowork bridge watchdog - $(stamp)")

if [ ! -f "$SUPERGATEWAY" ]; then
  STATUS+=("ABORT  supergateway not installed at $SUPERGATEWAY")
  STATUS+=("       run: cd '$STARTUP' && npm install")
  printf '%s\n' "${STATUS[@]}" > "$STATUS_FILE"
  exit 1
fi

for entry in "${BRIDGES[@]}"; do
  IFS=':' read -r port name launcher stateful <<< "$entry"
  flag="$LOG_DIR/.last-restart-$port"

  if port_is_listening "$port"; then
    STATUS+=("OK      $port $name listening")
    continue
  fi

  last=0
  [ -f "$flag" ] && last="$(cat "$flag" 2>/dev/null || echo 0)"
  elapsed=$(( $(now) - last ))

  if [ "$elapsed" -lt "$COOLDOWN_SECONDS" ]; then
    STATUS+=("HOLD    $port $name down, restarted ${elapsed}s ago - inside the ${COOLDOWN_SECONDS}s cooldown")
    continue
  fi

  if [ ! -f "$POSIX_DIR/$launcher" ]; then
    STATUS+=("FAIL    $port $name down, launcher missing: $launcher")
    continue
  fi

  start_bridge "$port" "$launcher" "$stateful"
  date +%s > "$flag"
  STATUS+=("RESTART $port $name was down, listener started")
done

STATUS+=("")
STATUS+=("Visibility is not observable from here: a port set back to Private")
STATUS+=("still answers locally. Check the VS Code Ports panel if Cowork cannot")
STATUS+=("reach a bridge this file reports as OK.")

printf '%s\n' "${STATUS[@]}" > "$STATUS_FILE"
