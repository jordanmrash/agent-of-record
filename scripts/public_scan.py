#!/usr/bin/env python3
"""Generic disclosure scan for the published tree.

Client, employer, colleague, and environment names belong in the local
denylist used by GitHubSetup. This script deliberately contains none of them;
it catches shapes that can be checked safely in public CI.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_EXTENSIONS = {
    ".bash", ".bat", ".cfg", ".cmd", ".html", ".ini", ".js", ".json", ".md",
    ".ps1", ".py", ".sh", ".txt", ".xml", ".yaml", ".yml", ".zsh",
}

PATTERNS = {
    "non-placeholder Windows user path": re.compile(
        r"C:\\Users\\(?!YOURUSER\b)[A-Za-z0-9._-]+", re.I
    ),
    # macOS and Linux homes leak the same way a Windows profile path does, and
    # the POSIX launchers made that reachable. Angle-bracket and shell-variable
    # forms are how the documentation refers to a home directory it cannot know,
    # so those are the placeholders here.
    "non-placeholder POSIX home path": re.compile(
        r"/(?:Users|home)/(?!YOURUSER\b|<|\$|\{|\.\.)[A-Za-z0-9._-]+"
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
    "cowork-env.cmd",         # the operator's real Windows paths; example is committed
    "cowork-env.sh",          # the operator's real POSIX paths; example is committed
    "denylist.local.txt",
    "sanitize.local.txt",
    "allow.local.txt",
    "excludes.local.txt",
    "flow-bridge.config.json",
    "token-cache.json",
    "_commit-msg.txt",
}


def git_listed(root: Path) -> list[Path] | None:
    """Every file git would let into a commit: tracked, plus untracked and not
    ignored. None when git is unavailable or this is not a repository (a release
    zip), in which case the caller walks the tree instead."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            capture_output=True, check=False,
        )
    except OSError:
        return None
    if out.returncode != 0:
        return None
    return [root / p for p in out.stdout.decode("utf-8", "replace").split("\0") if p]


def iter_files(targets: list[Path]) -> tuple[list[Path], str]:
    """The files to scan and how they were chosen.

    Before this the scan walked the whole tree, gitignored paths included, so a
    run was refused on hits inside CommandJobs/Logs/*.json - files no commit
    could carry - and the positional arguments were read by nobody. Now: the
    git-listed set when git answers, else a walk; then narrowed to any paths
    given on the command line."""
    listed = git_listed(ROOT)
    if listed is None:
        mode = "walked (git unavailable)"
        candidates = list(ROOT.rglob("*"))
    else:
        mode = "git-listed (ignored paths skipped)"
        candidates = listed
    files: list[Path] = []
    wanted = [t.resolve() for t in targets]
    for path in candidates:
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if wanted:
            resolved = path.resolve()
            if not any(resolved == w or w in resolved.parents for w in wanted):
                continue
        files.append(path)
    return files, mode


def main() -> int:
    findings: list[str] = []
    targets = [ROOT / a if not Path(a).is_absolute() else Path(a) for a in sys.argv[1:]]
    for t in targets:
        if not t.exists():
            print(f"PUBLIC_SCAN: path not found: {t}")
            return 2
    files, mode = iter_files(targets)

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

    print(f"scanned {len(files)} files, {mode}"
          + (f", under {', '.join(str(t.relative_to(ROOT)) if t.is_relative_to(ROOT) else str(t) for t in targets)}" if targets else ""))
    if findings:
        print(f"{len(findings)} finding(s):")
        for finding in findings:
            print(f"  {finding}")
        return 1

    print("PUBLIC_SCAN: CLEAN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
