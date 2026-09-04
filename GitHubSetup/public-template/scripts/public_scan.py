#!/usr/bin/env python3
"""Generic disclosure scan for the published tree.

Client, employer, colleague, and environment names belong in the local
denylist used by GitHubSetup. This script deliberately contains none of them;
it catches shapes that can be checked safely in public CI.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_EXTENSIONS = {
    ".bat", ".cfg", ".cmd", ".html", ".ini", ".js", ".json", ".md",
    ".ps1", ".py", ".txt", ".xml", ".yaml", ".yml",
}

PATTERNS = {
    "non-placeholder Windows user path": re.compile(
        r"C:\\Users\\(?!YOURUSER\b)[A-Za-z0-9._-]+", re.I
    ),
    "live dev-tunnel hostname": re.compile(
        r"(?<!YOUR-TUNNEL-HOST-)[A-Za-z0-9]{6,}-\d{2,5}\."
        r"[a-z0-9.-]+\.devtunnels\.ms", re.I
    ),
    "bearer token": re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{40,}"),
    "JWT": re.compile(
        r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\."
        r"[A-Za-z0-9_-]{10,}"
    ),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "assigned client secret": re.compile(
        r"(?i)client[_-]?secret\s*[:=]\s*['\"]?[A-Za-z0-9._~-]{8,}"
    ),
    "refresh token value": re.compile(
        r'(?i)refresh[_-]?token["\']?\s*[:=]\s*["\'][^"\']{20,}'
    ),
    "non-example email": re.compile(
        r"\b(?![A-Za-z0-9._%+-]+@(?:example\.com|test\.com|users\.noreply\.github\.com)\b)"
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    ),
    "non-example Dataverse host": re.compile(
        r"https://(?!(?:your(?:test|prod)?org\d*|orgX+)\.crm\.dynamics\.com)"
        r"[A-Za-z0-9.-]+\.crm\.dynamics\.com", re.I
    ),
}

PROHIBITED_NAMES = {
    "denylist.local.txt",
    "sanitize.local.txt",
    "allow.local.txt",
    "excludes.local.txt",
    "flow-bridge.config.json",
    "token-cache.json",
    "_commit-msg.txt",
}


def iter_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        files.append(path)
    return files


def main() -> int:
    findings: list[str] = []
    files = iter_files()

    for path in files:
        rel = path.relative_to(ROOT)
        if path.name.lower() in PROHIBITED_NAMES:
            findings.append(f"prohibited local filename: {rel}")
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{label}: {rel}:{line}")

    print(f"scanned {len(files)} files")
    if findings:
        print(f"{len(findings)} finding(s):")
        for finding in findings:
            print(f"  {finding}")
        return 1

    print("PUBLIC_SCAN: CLEAN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
