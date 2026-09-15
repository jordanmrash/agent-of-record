#!/bin/bash
# COWORK_OUTPUT: ../Outputs/Mac Evidence 2026-09-15
# Why does 2025.8.21 emit an inputSchema with no "type"? Look at what npx resolved.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

NPX="$(command -v npx || echo "$HOME/.local/bin/npx")"
echo "npx: $NPX"
echo
echo "=== resolved dependency tree for the pinned server ==="
DIR="$(mktemp -d)"
cd "$DIR"
npm init -y >/dev/null 2>&1
npm install --silent "@modelcontextprotocol/server-filesystem@2025.8.21" >/dev/null 2>&1
echo "server-filesystem: $(node -p "require('./node_modules/@modelcontextprotocol/server-filesystem/package.json').version" 2>/dev/null)"
for pkg in zod zod-to-json-schema @modelcontextprotocol/sdk; do
  v=$(node -p "require('./node_modules/$pkg/package.json').version" 2>/dev/null || echo "not present")
  echo "$pkg: $v"
done
echo
echo "=== what the server package DECLARES it wants ==="
node -p "JSON.stringify(require('./node_modules/@modelcontextprotocol/server-filesystem/package.json').dependencies, null, 2)" 2>/dev/null
cd "$REPO"; rm -rf "$DIR" 2>/dev/null || true
