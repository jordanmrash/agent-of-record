#!/bin/bash
# COWORK_OUTPUT: ../Outputs/Mac Evidence 2026-09-15
# Read-only: does Claude declare a document type for .plugin, and is there a CLI?
set -uo pipefail

APP="/Applications/Claude.app"
PL="$APP/Contents/Info.plist"

echo "Claude.app present: $([ -d "$APP" ] && echo yes || echo no)"
[ -f "$PL" ] && echo "version: $(/usr/bin/defaults read "$PL" CFBundleShortVersionString 2>/dev/null)"

echo
echo "=== declared document types ==="
/usr/bin/plutil -extract CFBundleDocumentTypes json -o - "$PL" 2>/dev/null \
  | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    print("  (none declared)"); raise SystemExit
for t in d:
    print(" ", t.get("CFBundleTypeName"), "exts:", t.get("CFBundleTypeExtensions"), "utis:", t.get("LSItemContentTypes"))
' 2>/dev/null || echo "  (none declared)"

echo
echo "=== exported/imported UTIs mentioning plugin ==="
/usr/bin/plutil -p "$PL" 2>/dev/null | grep -i -A3 "UTExported\|UTImported\|plugin" | head -20 || echo "  (none)"

echo
echo "=== URL schemes Claude registers ==="
/usr/bin/plutil -extract CFBundleURLTypes json -o - "$PL" 2>/dev/null \
  | python3 -c 'import json,sys
d=json.load(sys.stdin)
for t in d: print(" ", t.get("CFBundleURLName"), t.get("CFBundleURLSchemes"))' 2>/dev/null || echo "  (none)"

echo
echo "=== any claude CLI on this Mac ==="
for c in claude claude-code; do
  echo "  $c: $(command -v $c || echo 'not installed')"
done
ls -1 "$APP/Contents/Resources" 2>/dev/null | head -20
