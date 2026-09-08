#!/usr/bin/env bash
# ============================================================
#  Install the bridge watchdog as a launchd agent (macOS).
#  POSIX sibling of ../../_watchdog-install.ps1
#
#      bash install-launchd.sh              install and start
#      bash install-launchd.sh --uninstall  stop and remove
#
#  Registers a per-user LaunchAgent that runs bridge-watchdog.sh
#  at login and every two minutes. Nothing here needs sudo: it is
#  a user agent, not a system daemon, and it runs with exactly the
#  authority you already have.
#
#  On Linux there is no launchd. Use cron instead:
#      */2 * * * * /bin/bash <this dir>/bridge-watchdog.sh
# ============================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WATCHDOG="$HERE/bridge-watchdog.sh"
LABEL="com.agentofrecord.bridgewatchdog"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
INTERVAL=120

if [ "$(uname -s)" != "Darwin" ]; then
  echo "This installer is for macOS. On Linux, add a cron entry instead:"
  echo "  */2 * * * * /bin/bash $WATCHDOG"
  exit 2
fi

if [ "${1:-}" = "--uninstall" ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || \
    launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "Removed $LABEL"
  exit 0
fi

if [ ! -f "$WATCHDOG" ]; then
  echo "watchdog script not found: $WATCHDOG" >&2
  exit 1
fi
chmod +x "$WATCHDOG"

mkdir -p "$HOME/Library/LaunchAgents" "$HERE/logs"

cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$WATCHDOG</string>
    </array>
    <key>StartInterval</key>
    <integer>$INTERVAL</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HERE/logs/launchd.out.log</string>
    <key>StandardErrorPath</key>
    <string>$HERE/logs/launchd.err.log</string>
    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>
PLIST_EOF

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null || launchctl load "$PLIST"

echo "Installed $LABEL"
echo "  runs every ${INTERVAL}s and at login"
echo "  status:  $HERE/status.txt"
echo "  logs:    $HERE/logs/"
echo
echo "It restarts a dead listener. It cannot set a dev tunnel port back to"
echo "Public - only you can do that, in the VS Code Ports panel."
