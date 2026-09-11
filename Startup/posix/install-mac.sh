#!/usr/bin/env bash
# ============================================================
#  agent-of-record  --  Mac installer for the Claude Cowork route
#
#  Run this from the macOS Terminal, not from a Cowork chat:
#
#      bash <where you unzipped or cloned>/Startup/posix/install-mac.sh
#
#  It does every step the Mac can do on its own:
#    1. puts the tree at ~/Documents/agent-of-record (or --root <dir>)
#    2. checks git, python3 and node, and installs node without sudo
#       if the Mac has none
#    3. creates CommandJobs/, CommandJobs/Logs/ and Outputs/, sets the
#       execute bits, clears the download quarantine flag
#    4. writes Startup/posix/cowork-env.sh with COWORK_NODE pinned
#    5. runs release_check.py and install_check.py in THIS terminal,
#       so the result is about the Mac and not about a sandbox
#    6. starts the executor the way the desktop app will (a minimal
#       PATH) and completes a real MCP handshake with it
#    7. registers the executor in Claude Desktop's own config file,
#       keeping a dated backup of that file
#    8. drops a first job, hello-mac.sh, into CommandJobs/
#    9. prints the short list of things only you can do, and saves it
#
#  What it never does: sudo, curl | bash, or write anywhere outside the
#  tooling root except Claude Desktop's config file, which it backs up first.
#
#  Modes:
#      install-mac.sh                 full run (safe to repeat)
#      install-mac.sh --verify        after you reopen Claude: read its MCP
#                                     logs and say whether the executor connected
#      install-mac.sh --register      only rewrite the Claude Desktop entry
#      install-mac.sh --root DIR      use DIR as the tooling root
#      install-mac.sh --replace       refresh an existing tooling root from
#                                     this download (keeps jobs, outputs, env)
# ============================================================
set -euo pipefail

SERVER_KEY="cowork-batch-exec"
NODE_LINE_DEFAULT="v24.x"        # nodejs.org release line to fetch if the Mac has no node
MIN_NODE_MAJOR=20
MIN_PY_MINOR=10                  # 3.10

MODE="install"
TARGET_ROOT="${HOME}/Documents/agent-of-record"
REPLACE="no"
while [ $# -gt 0 ]; do
  case "$1" in
    --verify)   MODE="verify" ;;
    --register) MODE="register" ;;
    --root)     shift; TARGET_ROOT="${1:?--root needs a directory}" ;;
    --replace)  REPLACE="yes" ;;
    -h|--help)  sed -n '2,40p' "$0"; exit 0 ;;
    *) echo "unknown option: $1 (try --help)" >&2; exit 64 ;;
  esac
  shift
done

# ---------- output helpers ------------------------------------------------
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG=""
MANUAL=()          # steps only the person can do, printed at the end
say()  { printf '%s\n' "$*"; [ -n "$LOG" ] && printf '%s\n' "$*" >>"$LOG" || true; }
pass() { say "PASS  $*"; }
info() { say "      $*"; }
warn() { say "WARN  $*"; }
die()  { say "STOP  $*"; print_manual; exit 1; }
manual() { MANUAL+=("$*"); }

print_manual() {
  if [ ${#MANUAL[@]} -eq 0 ]; then return; fi
  say ""
  say "=================  THINGS ONLY YOU CAN DO  ================="
  local n=1
  for step in "${MANUAL[@]}"; do
    say "  $n. $step"
    n=$((n+1))
  done
  say "============================================================"
}

# ---------- platform guards ----------------------------------------------
if [ "$(uname -s)" != "Darwin" ] && [ "${AOR_ALLOW_NON_DARWIN:-}" != "1" ]; then
  echo "This installer is for macOS. On Windows use the hosted route in docs/install/." >&2
  exit 65
fi
if [ "$(id -u)" -eq 0 ]; then
  echo "Do not run this with sudo. Nothing here needs root, and a root-owned tree will not work for your user." >&2
  exit 66
fi

# ---------- where the files are, and where they should be -----------------
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_ROOT="$(cd "$HERE/../.." && pwd)"

looks_like_repo() {
  [ -f "$1/Startup/posix/exec-server.sh" ] &&
  [ -f "$1/Startup/CommandBridge/batch-exec-server.js" ] &&
  [ -f "$1/scripts/install_check.py" ]
}
looks_like_repo "$SRC_ROOT" || {
  echo "This script must stay inside the agent-of-record tree (Startup/posix/). Found no repo above: $SRC_ROOT" >&2
  exit 67
}

canon() { (cd "$1" 2>/dev/null && pwd -P) || printf '%s' "$1"; }

ROOT="$SRC_ROOT"
if [ "$MODE" = "install" ]; then
  mkdir -p "$(dirname "$TARGET_ROOT")"
  if [ "$(canon "$SRC_ROOT")" != "$(canon "$TARGET_ROOT")" ]; then
    if [ -e "$TARGET_ROOT" ] && [ -n "$(ls -A "$TARGET_ROOT" 2>/dev/null)" ]; then
      if looks_like_repo "$TARGET_ROOT" && [ "$REPLACE" = "yes" ]; then
        echo "Refreshing $TARGET_ROOT from $SRC_ROOT (jobs, outputs and cowork-env.sh are kept)"
        rsync -a --exclude 'CommandJobs/' --exclude 'Outputs/' \
              --exclude 'Startup/posix/cowork-env.sh' --exclude 'install-results.json' \
              "$SRC_ROOT/" "$TARGET_ROOT/"
      elif looks_like_repo "$TARGET_ROOT"; then
        echo "There is already an agent-of-record tree at $TARGET_ROOT."
        echo "Either run the installer from that copy:"
        echo "    bash \"$TARGET_ROOT/Startup/posix/install-mac.sh\""
        echo "or refresh it from this download:"
        echo "    bash \"$0\" --replace"
        exit 68
      else
        echo "$TARGET_ROOT exists and is not an agent-of-record tree. Pick another place with --root." >&2
        exit 69
      fi
    else
      echo "Placing the tree at $TARGET_ROOT"
      rsync -a "$SRC_ROOT/" "$TARGET_ROOT/"
    fi
  fi
  ROOT="$(canon "$TARGET_ROOT")"
else
  # --verify / --register act on the tree this script lives in
  ROOT="$(canon "$SRC_ROOT")"
fi

mkdir -p "$ROOT/CommandJobs/Logs" "$ROOT/Outputs"
LOG="$ROOT/CommandJobs/Logs/install-mac-$STAMP.log"
: >"$LOG"
say "agent-of-record Mac installer, mode: $MODE"
say "Tooling root: $ROOT"
say "Log: $LOG"

# ---------- prerequisites -------------------------------------------------
need_clt() {
  if xcode-select -p >/dev/null 2>&1 || [ "$(uname -s)" != "Darwin" ]; then
    return 0
  fi
  warn "Apple's Command Line Tools are not installed. git and python3 come from them."
  xcode-select --install >/dev/null 2>&1 || true
  manual "A macOS dialog is asking to install the Command Line Tools. Click Install, wait for it to finish, then run this installer again the same way."
  die "waiting for the Command Line Tools"
}

node_major() { "$1" -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0; }

find_node() {
  # 1. an explicit pin in cowork-env.sh
  if [ -f "$ROOT/Startup/posix/cowork-env.sh" ]; then
    local pinned
    pinned="$(sh -c '. "$1"; printf "%s" "${COWORK_NODE:-}"' sh "$ROOT/Startup/posix/cowork-env.sh" 2>/dev/null || true)"
    if [ -n "$pinned" ] && [ -x "$pinned" ] && [ "$(node_major "$pinned")" -ge "$MIN_NODE_MAJOR" ]; then
      printf '%s' "$pinned"; return 0
    fi
  fi
  # 2. whatever this terminal already sees
  local c
  c="$(command -v node 2>/dev/null || true)"
  if [ -n "$c" ] && [ "$(node_major "$c")" -ge "$MIN_NODE_MAJOR" ]; then printf '%s' "$c"; return 0; fi
  # 3. the usual macOS locations, newest nvm version last
  for c in /opt/homebrew/bin/node /usr/local/bin/node "$HOME/.local/node/bin/node" "$HOME/.volta/bin/node" \
           $(ls -d "$HOME"/.nvm/versions/node/*/bin/node 2>/dev/null | (sort -V 2>/dev/null || sort) | tail -1); do
    if [ -x "$c" ] && [ "$(node_major "$c")" -ge "$MIN_NODE_MAJOR" ]; then printf '%s' "$c"; return 0; fi
  done
  return 1
}

install_node_userlocal() {
  # No sudo: unpack the official nodejs.org build under ~/.local/node,
  # verified against the SHASUMS256.txt published beside it.
  local line="${COWORK_NODE_LINE:-$NODE_LINE_DEFAULT}" arch tarball url tmp sums
  case "$(uname -m)" in
    arm64)  arch="darwin-arm64" ;;
    x86_64) arch="darwin-x64" ;;
    *) return 1 ;;
  esac
  tmp="$(mktemp -d)"
  sums="$(curl -fsSL "https://nodejs.org/dist/latest-${line}/SHASUMS256.txt" 2>>"$LOG")" || return 1
  tarball="$(printf '%s\n' "$sums" | awk -v a="$arch" '$2 ~ ("node-v[0-9.]+-" a "\\.tar\\.gz$") {print $2; exit}')"
  [ -n "$tarball" ] || return 1
  url="https://nodejs.org/dist/latest-${line}/${tarball}"
  info "downloading $url"
  curl -fsSL "$url" -o "$tmp/$tarball" 2>>"$LOG" || return 1
  local want got
  want="$(printf '%s\n' "$sums" | awk -v t="$tarball" '$2==t {print $1}')"
  got="$(shasum -a 256 "$tmp/$tarball" | awk '{print $1}')"
  [ "$want" = "$got" ] || { warn "checksum mismatch for $tarball, not installing it"; return 1; }
  rm -rf "$HOME/.local/node"
  mkdir -p "$HOME/.local/node" "$HOME/.local/bin"
  tar -xzf "$tmp/$tarball" -C "$HOME/.local/node" --strip-components=1
  ln -sf "$HOME/.local/node/bin/node" "$HOME/.local/bin/node"
  ln -sf "$HOME/.local/node/bin/npm"  "$HOME/.local/bin/npm"
  ln -sf "$HOME/.local/node/bin/npx"  "$HOME/.local/bin/npx"
  rm -rf "$tmp"
  return 0
}

py_ok() { "$1" -c "import sys; sys.exit(0 if sys.version_info >= (3, $MIN_PY_MINOR) else 1)" 2>/dev/null; }

find_python() {
  local c
  for c in "$(command -v python3 2>/dev/null || true)" /opt/homebrew/bin/python3 /usr/local/bin/python3 \
           "$HOME/.local/bin/python3" /usr/bin/python3; do
    [ -n "$c" ] && [ -x "$c" ] && py_ok "$c" && { printf '%s' "$c"; return 0; }
  done
  return 1
}

# ---------- Claude Desktop registration ----------------------------------
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/Library/Application Support/Claude}"
CLAUDE_CFG="$CLAUDE_DIR/claude_desktop_config.json"

register_claude() {
  local node_bin="$1" node_dir
  node_dir="$(dirname "$node_bin")"
  if [ ! -d "$CLAUDE_DIR" ]; then
    warn "Claude Desktop does not seem to be installed (no $CLAUDE_DIR)."
    manual "Install the Claude desktop app from claude.ai/download, open it once and sign in, then run:  bash \"$ROOT/Startup/posix/install-mac.sh\" --register"
    return 1
  fi
  if [ -f "$CLAUDE_CFG" ]; then
    cp -p "$CLAUDE_CFG" "$CLAUDE_CFG.bak-$STAMP"
    info "backed up the existing config to $(basename "$CLAUDE_CFG").bak-$STAMP"
  fi
  AOR_ROOT="$ROOT" AOR_KEY="$SERVER_KEY" AOR_NODE="$node_bin" AOR_NODE_DIR="$node_dir" AOR_CFG="$CLAUDE_CFG" \
  "$PY" - <<'PYEOF'
import json, os, sys
cfg_path = os.environ["AOR_CFG"]
root, key, node, node_dir = (os.environ[k] for k in ("AOR_ROOT", "AOR_KEY", "AOR_NODE", "AOR_NODE_DIR"))
data = {}
if os.path.exists(cfg_path) and os.path.getsize(cfg_path) > 0:
    with open(cfg_path, encoding="utf-8") as f:
        raw = f.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"claude_desktop_config.json is not valid JSON ({e}); not touching it. Fix it in a text editor and rerun with --register.\n")
        sys.exit(3)
    if not isinstance(data, dict):
        sys.stderr.write("claude_desktop_config.json is not a JSON object; not touching it.\n")
        sys.exit(3)
servers = data.setdefault("mcpServers", {})
entry = {
    "command": "/bin/bash",
    "args": [os.path.join(root, "Startup", "posix", "exec-server.sh")],
    "env": {
        "PATH": f"{node_dir}:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "COWORK_NODE": node,
        "HOME": os.environ.get("HOME", ""),
    },
}
if servers.get(key) == entry:
    print(f"      mcpServers.{key} already points at /bin/bash {entry['args'][0]} (unchanged)")
    sys.exit(10)
servers[key] = entry
with open(cfg_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
print(f"      wrote mcpServers.{key} -> /bin/bash {entry['args'][0]}")
PYEOF
  local rc=$?
  if [ $rc -eq 10 ]; then
    # nothing changed, so the backup taken above is noise
    rm -f "$CLAUDE_CFG.bak-$STAMP"
  elif [ $rc -ne 0 ]; then
    die "could not update $CLAUDE_CFG"
  fi
  pass "Claude Desktop config: $CLAUDE_CFG"
  if pgrep -x "Claude" >/dev/null 2>&1; then
    manual "Quit Claude completely (Claude menu > Quit Claude, or Cmd+Q) and open it again. It reads this config only at launch."
  else
    manual "Open the Claude desktop app."
  fi
  return 0
}

# ---------- a real MCP handshake, under the PATH the desktop app will pass --
handshake() {
  # $1 = PATH to hand the launcher, $2 = label. Prints the server line on success.
  local path_val="$1" label="$2"
  AOR_LAUNCHER="$ROOT/Startup/posix/exec-server.sh" AOR_PATH="$path_val" AOR_NODE_PIN="${3:-}" \
  "$PY" - <<'PYEOF'
import json, os, subprocess, sys, threading
launcher, path_val, node_pin = os.environ["AOR_LAUNCHER"], os.environ["AOR_PATH"], os.environ["AOR_NODE_PIN"]
env = {"HOME": os.environ.get("HOME", ""), "USER": os.environ.get("USER", ""), "PATH": path_val}
if node_pin:
    env["COWORK_NODE"] = node_pin
p = subprocess.Popen(["/bin/bash", launcher], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE, env=env, text=True, bufsize=1)
def send(obj):
    p.stdin.write(json.dumps(obj) + "\n"); p.stdin.flush()
result = {}
def reader():
    for line in p.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "id" in msg and msg.get("id") in (1, 2):
            result[msg["id"]] = msg
        if 2 in result:
            break
t = threading.Thread(target=reader, daemon=True)
t.start()
try:
    send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {},
        "clientInfo": {"name": "install-mac.sh", "version": "1"}}})
    t.join(15)
    if 1 in result:
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        t.join(15)
finally:
    try:
        p.stdin.close()
    except Exception:
        pass
    p.terminate()
    try:
        p.wait(5)
    except Exception:
        p.kill()
err = p.stderr.read().strip()
if 1 not in result or "result" not in result[1]:
    print("no initialize response" + (f"; launcher stderr: {err}" if err else f"; exit code {p.returncode}"))
    sys.exit(1)
info = result[1]["result"].get("serverInfo", {})
tools = [t.get("name") for t in result.get(2, {}).get("result", {}).get("tools", [])]
print(f"{info.get('name','?')} {info.get('version','?')}, tools: {', '.join(tools) or 'none listed'}")
sys.exit(0 if "run_batch_file" in tools else 2)
PYEOF
}

# ---------- verify mode: read what the desktop app logged ------------------
verify_logs() {
  local logdir="$HOME/Library/Logs/Claude"
  say ""
  say "What Claude Desktop logged about $SERVER_KEY:"
  if [ ! -d "$logdir" ]; then
    warn "no $logdir yet. Open the Claude desktop app, start a Cowork chat in it, then run --verify again."
    return 1
  fi
  local hits
  # files that mention the server by name, plus the per-server log the app names after it
  hits="$( { grep -il "$SERVER_KEY" "$logdir"/mcp*.log 2>/dev/null; ls "$logdir"/mcp-server-*"$SERVER_KEY"*.log 2>/dev/null; } | sort -u || true)"
  if [ -z "$hits" ]; then
    warn "no MCP log mentions $SERVER_KEY. The app has not tried to start it."
    info "Check: is the entry in $CLAUDE_CFG (run --register), did you fully quit and reopen Claude,"
    info "and was the Cowork chat started in the desktop app itself, not on the web."
    return 1
  fi
  local f
  for f in $hits; do
    say "--- $f (last 30 lines mentioning the server or an error)"
    grep -inE "$SERVER_KEY|error|ENOENT|spawn|exit|not found|connected|initializ" "$f" | tail -30 | tee -a "$LOG"
  done
  if grep -qiE "ENOENT|not found|exit code [1-9]|exited|spawn .* failed|exiting early" $hits 2>/dev/null; then
    warn "the launcher was started and died. The lines above say why (usually node or a wrong path)."
    return 1
  fi
  if grep -qiE "connected|initialized|tools/list" $hits 2>/dev/null; then
    pass "the desktop app started the executor and talked to it"
    return 0
  fi
  warn "the app mentions the server but neither a clean connection nor a spawn error is visible. Read the lines above."
  return 1
}

# =============================== MAIN ======================================
need_clt

PY="$(find_python || true)"
if [ -z "$PY" ]; then
  if command -v brew >/dev/null 2>&1; then
    info "python3 3.$MIN_PY_MINOR+ not found, installing it with Homebrew (no sudo)"
    brew install python@3.12 >>"$LOG" 2>&1 || true
    PY="$(find_python || true)"
  fi
fi
[ -n "$PY" ] || { manual "Install Python 3 (3.$MIN_PY_MINOR or later) from python.org, one download and a double-click, then run this installer again."; die "python3 3.$MIN_PY_MINOR+ is missing"; }
pass "python3: $PY ($("$PY" --version 2>&1))"

if [ "$MODE" = "verify" ]; then
  NODE_BIN="$(find_node || true)"
  if [ -n "$NODE_BIN" ]; then
    if out="$(handshake "$(dirname "$NODE_BIN"):/usr/bin:/bin:/usr/sbin:/sbin" "config PATH" "$NODE_BIN")"; then
      pass "executor handshake under the config's PATH: $out"
    else
      warn "executor handshake under the config's PATH: $out"
    fi
  fi
  verify_logs && exit 0 || exit 1
fi

if command -v git >/dev/null 2>&1; then
  pass "git: $(git --version 2>&1)"
else
  warn "git not found; the release gate's tracked-file scan needs it"
fi

NODE_BIN="$(find_node || true)"
if [ -z "$NODE_BIN" ]; then
  if command -v brew >/dev/null 2>&1; then
    info "node $MIN_NODE_MAJOR+ not found, installing it with Homebrew (no sudo)"
    brew install node >>"$LOG" 2>&1 || warn "brew install node did not finish cleanly, see the log"
    NODE_BIN="$(find_node || true)"
  fi
fi
if [ -z "$NODE_BIN" ]; then
  info "node $MIN_NODE_MAJOR+ not found, fetching the official build into ~/.local/node (no sudo)"
  if install_node_userlocal; then
    NODE_BIN="$(find_node || true)"
  fi
fi
[ -n "$NODE_BIN" ] || { manual "Install Node.js (LTS) from nodejs.org, one download and a double-click, then run this installer again."; die "node $MIN_NODE_MAJOR+ is missing and could not be fetched"; }
pass "node: $NODE_BIN ($("$NODE_BIN" --version))"

if [ "$MODE" = "register" ]; then
  register_claude "$NODE_BIN" || true
  print_manual
  exit 0
fi

# ---------- folders, bits, quarantine, env --------------------------------
chmod +x "$ROOT"/Startup/posix/*.sh 2>/dev/null || true
xattr -dr com.apple.quarantine "$ROOT" 2>/dev/null || true
pass "folders: CommandJobs/, CommandJobs/Logs/, Outputs/; execute bits set; quarantine flag cleared"

if [ ! -d "$ROOT/.git" ] && command -v git >/dev/null 2>&1; then
  # A release zip has no .git. The gate's tracked-file scan asks git, so give it a
  # local-only history to answer from. Nothing is pushed anywhere.
  (cd "$ROOT" && git init -q && git add -A && git -c user.name=installer -c user.email=installer@example.com \
     commit -q -m "local import of the downloaded tree" ) >>"$LOG" 2>&1 && pass "git: local history created for the downloaded tree (no remote)" || warn "git init of the downloaded tree failed, see the log"
fi

ENV_FILE="$ROOT/Startup/posix/cowork-env.sh"
if [ ! -f "$ENV_FILE" ]; then
  if [ -f "$ROOT/Startup/posix/cowork-env.example.sh" ]; then
    cp "$ROOT/Startup/posix/cowork-env.example.sh" "$ENV_FILE"
  else
    printf '# machine-specific settings, gitignored\n' >"$ENV_FILE"
  fi
fi
# pin node for the launcher; replace an earlier pin rather than stacking them
grep -v '^export COWORK_NODE=' "$ENV_FILE" >"$ENV_FILE.tmp" || true
printf 'export COWORK_NODE="%s"\n' "$NODE_BIN" >>"$ENV_FILE.tmp"
mv "$ENV_FILE.tmp" "$ENV_FILE"
pass "cowork-env.sh: COWORK_NODE pinned to $NODE_BIN"

# ---------- first job -----------------------------------------------------
if [ -f "$ROOT/Startup/posix/hello-mac.example.sh" ] && [ ! -f "$ROOT/CommandJobs/hello-mac.sh" ]; then
  cp "$ROOT/Startup/posix/hello-mac.example.sh" "$ROOT/CommandJobs/hello-mac.sh"
  chmod +x "$ROOT/CommandJobs/hello-mac.sh"
fi
[ -f "$ROOT/CommandJobs/hello-mac.sh" ] && pass "first job in place: CommandJobs/hello-mac.sh"

# ---------- the repo's own checks, run on the Mac itself -------------------
say ""
say "Running the release gate in this terminal (this is the Mac, not a sandbox)..."
if (cd "$ROOT" && PATH="$(dirname "$NODE_BIN"):$PATH" "$PY" scripts/release_check.py) >>"$LOG" 2>&1; then
  pass "$(grep -E 'RELEASE_CHECK:' "$LOG" | tail -1)"
else
  grep -E 'FAIL|RELEASE_CHECK:' "$LOG" | tail -20 | sed 's/^/      /'
  die "release_check.py did not come back CLEAN. Do not adjust a check to make it pass; open an issue with the log."
fi

say "Running the install check..."
if (cd "$ROOT" && PATH="$(dirname "$NODE_BIN"):$PATH" "$PY" scripts/install_check.py --route local --json install-results.json) >>"$LOG" 2>&1; then
  pass "$(grep -E 'INSTALL_CHECK:' "$LOG" | tail -1)"
else
  grep -E 'FAIL|INSTALL_CHECK:' "$LOG" | tail -20 | sed 's/^/      /'
  die "install_check.py did not come back CLEAN. Each FAIL line names its remedy."
fi

# ---------- the test that the sandbox could never run ----------------------
say ""
say "Starting the executor the way the desktop app will, and shaking hands with it..."
LAUNCHD_PATH="${AOR_BARE_PATH:-/usr/bin:/bin:/usr/sbin:/sbin}"   # what launchd hands a GUI app's children
if out="$(handshake "$LAUNCHD_PATH" "bare launchd PATH" "")"; then
  pass "with only the bare system PATH (the launcher found node by itself): $out"
else
  info "with only the bare system PATH the launcher does not start: $out"
  info "That is the failure a desktop app produces when nothing tells the launcher where node is."
  info "The config written below pins it, so this is informational."
fi
CFG_PATH="$(dirname "$NODE_BIN"):/opt/homebrew/bin:/usr/local/bin:$LAUNCHD_PATH"
if out="$(handshake "$CFG_PATH" "config PATH" "$NODE_BIN")"; then
  pass "with the PATH the config will pass: $out"
else
  die "the executor did not answer even with node on PATH: $out"
fi

# ---------- register with Claude Desktop ----------------------------------
say ""
register_claude "$NODE_BIN" || true

# ---------- what only the person can do -----------------------------------
manual "In Claude, start a NEW Cowork chat on this Mac (choose Cowork in the message box). It has to be started in the desktop app, not on the web."
manual "Click the + at the bottom of the message box, then Connectors. You should see $SERVER_KEY with one tool, run_batch_file. If you do not, run:  bash \"$ROOT/Startup/posix/install-mac.sh\" --verify"
manual "Ask Claude: \"Use run_batch_file to run hello-mac.sh\" and approve it. The result should list $ROOT/Outputs/Executor Test/result.txt"
manual "The first time a job controls another app (AppleScript), macOS will ask for permission once. Click OK."
manual "Send back what happened, pass or fail: the INSTALL_CHECK line from this log and the --verify output, as a pull request or an issue on the repository."

say ""
say "Everything the Mac could do on its own is done."
print_manual
NEXT="$ROOT/Outputs/agent-of-record-next-steps.txt"
{
  echo "agent-of-record on this Mac: what is left to do ($(date))"
  echo "Tooling root: $ROOT"
  echo "Log: $LOG"
  echo
  n=1; for step in "${MANUAL[@]}"; do echo "$n. $step"; n=$((n+1)); done
} >"$NEXT"
say "This list is saved at: $NEXT"
