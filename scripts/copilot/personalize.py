#!/usr/bin/env python3
"""Replace the repository placeholders with one operator's real values.

The published tree is sanitized: every path that names an account says
``C:\\Users\\YOURUSER``, every connector manifest points at
``YOUR-TUNNEL-HOST-<port>.use.devtunnels.ms`` and all four manifests share one
placeholder app id. Running the hosted (Copilot Cowork) route needs the real
account name, the real OneDrive folder name, the real tunnel host and a
distinct app id per connector package - in dozens of files. This script does
that substitution, reports it file by file, and is a dry run unless ``--apply``
is passed.

Scope is deliberately narrow. Only the operating trees are touched:

    Startup/          watchdog, connector packages, FlowBridge config
    CommandJobs/      approved batch jobs and their PowerShell bodies
    CoworkConfig/     skills, instructions, memory - the paths they cite
    docs/bridge-facts.json   kept in scope; its roots are launcher variables now

The bridge launchers (``Startup/*.cmd``, ``Startup/posix/*.sh``), the VS Code
task file and the roots in ``docs/bridge-facts.json`` carry no placeholder: each
launcher derives ``COWORK_ROOT`` from its own location, and machine-specific
values such as ``COWORK_CONFIG_ROOT`` live in the gitignored
``Startup/cowork-env.cmd`` (Windows) or ``Startup/posix/cowork-env.sh`` (POSIX).
This script finds nothing to rewrite in them, by design.

Everything that *documents* the placeholders - README.md, AGENTS.md,
CONTRIBUTING.md, docs/*.md, GitHubSetup/ (the publishing tooling) and
scripts/ - is left alone, so the explanation of what was replaced survives the
replacement. The attribution ``author-email`` lines in the skills are never
rewritten: they name the author of the skill, not the operator.

A personalized tree is an installation, not a publication. ``scripts/public_scan.py``
will (correctly) refuse it; do not push it to a public remote.

Exit codes: 0 ran (or nothing to do), 2 bad arguments or refused.
"""
import argparse
import json
import os
import re
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

USER_PLACEHOLDER = "YOURUSER"
TUNNEL_PLACEHOLDER = "YOUR-TUNNEL-HOST"
TUNNEL_DOMAIN_DEFAULT = "use.devtunnels.ms"
EMAIL_PLACEHOLDER = "you@example.com"
APP_ID_PLACEHOLDER = "00000000-0000-4000-8000-000000000000"

SCOPE_DIRS = ["Startup", "CommandJobs", "CoworkConfig"]
SCOPE_FILES = [os.path.join("docs", "bridge-facts.json")]
PLUGIN_DIR = os.path.join("Startup", "Plugins")
# the operator's email belongs in git identity and job headers, never in a
# skill's attribution block
EMAIL_DIRS = ["Startup", "CommandJobs"]
SKIP_SUFFIXES = (".png", ".ico", ".jpg", ".gif", ".zip", ".pyc")

# C:\Users\YOURUSER\OneDrive\... in .cmd/.ps1/.md (single backslash) and in JSON
# (doubled). The folder name after the account is what a business tenant renames.
ONEDRIVE_RE = re.compile(r"(C:\\+Users\\+)" + USER_PLACEHOLDER + r"(\\+)OneDrive(?=\\)")


def iter_files(root):
    for d in SCOPE_DIRS:
        base = os.path.join(root, d)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(n for n in dirnames if n not in ("__pycache__", "node_modules", ".git"))
            for name in sorted(filenames):
                if name.lower().endswith(SKIP_SUFFIXES):
                    continue
                yield os.path.join(dirpath, name)
    for rel in SCOPE_FILES:
        path = os.path.join(root, rel)
        if os.path.isfile(path):
            yield path


def load_text(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def save_text(path, text):
    # newline="" keeps CRLF files CRLF; git attributes decide the rest
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def valid_user(name):
    return bool(name) and name != USER_PLACEHOLDER and not re.search(r'[\\/:*?"<>|]', name)


def valid_tunnel_host(host):
    # the leading label of https://<host>-<port>.<region>.devtunnels.ms
    return bool(re.fullmatch(r"[a-z0-9]([a-z0-9-]*[a-z0-9])?", host))


def personalize_text(text, rel, args):
    counts = {}

    def bump(key, n):
        if n:
            counts[key] = counts.get(key, 0) + n

    if args.onedrive_folder != "OneDrive":
        text, n = ONEDRIVE_RE.subn(lambda m: m.group(1) + args.user + m.group(2) + args.onedrive_folder, text)
        bump("onedrive-folder", n)
    n = text.count(USER_PLACEHOLDER)
    text = text.replace(USER_PLACEHOLDER, args.user)
    bump(USER_PLACEHOLDER, n)

    if args.tunnel_host:
        n = text.count(TUNNEL_PLACEHOLDER)
        text = text.replace(TUNNEL_PLACEHOLDER, args.tunnel_host)
        bump(TUNNEL_PLACEHOLDER, n)
        if args.tunnel_domain != TUNNEL_DOMAIN_DEFAULT:
            n = text.count(TUNNEL_DOMAIN_DEFAULT)
            text = text.replace(TUNNEL_DOMAIN_DEFAULT, args.tunnel_domain)
            bump("tunnel-domain", n)

    if args.email and rel.split(os.sep)[0] in EMAIL_DIRS:
        n = text.count(EMAIL_PLACEHOLDER)
        text = text.replace(EMAIL_PLACEHOLDER, args.email)
        bump(EMAIL_PLACEHOLDER, n)

    if rel.startswith(PLUGIN_DIR + os.sep) and rel.endswith("manifest.json") and APP_ID_PLACEHOLDER in text:
        text = text.replace(APP_ID_PLACEHOLDER, str(uuid.uuid4()), 1)
        bump("app-id", 1)
    return text, counts


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--user", required=True, help="Windows account name, the folder under C:\\Users")
    ap.add_argument("--onedrive-folder", default="OneDrive",
                    help='OneDrive folder name under the profile, e.g. "OneDrive - Contoso" (default: OneDrive)')
    ap.add_argument("--tunnel-host", default="",
                    help="dev tunnel host label, the part before -<port> in the forwarded address; "
                         "omit on the first pass and re-run once the Ports panel shows it")
    ap.add_argument("--tunnel-domain", default=TUNNEL_DOMAIN_DEFAULT,
                    help="tunnel domain after the port, if your region is not %s" % TUNNEL_DOMAIN_DEFAULT)
    ap.add_argument("--email", default="", help="git identity email for the job headers (optional)")
    ap.add_argument("--apply", action="store_true", help="write the changes; without it nothing is modified")
    ap.add_argument("--root", default=ROOT, help="repository root (default: the checkout this script is in)")
    args = ap.parse_args(argv)

    if not valid_user(args.user):
        print("PERSONALIZE: refused - --user must be a plain account name, not %r" % args.user)
        return 2
    if args.tunnel_host and not valid_tunnel_host(args.tunnel_host):
        print("PERSONALIZE: refused - --tunnel-host is the host label only (letters, digits, hyphens), not %r"
              % args.tunnel_host)
        return 2
    root = os.path.abspath(args.root)
    for d in SCOPE_DIRS:
        if not os.path.isdir(os.path.join(root, d)):
            print("PERSONALIZE: refused - %s has no %s folder; point --root at the repository" % (root, d))
            return 2

    changed = []
    totals = {}
    skipped_binary = 0
    for path in iter_files(root):
        rel = os.path.relpath(path, root)
        text = load_text(path)
        if text is None:
            skipped_binary += 1
            continue
        new_text, counts = personalize_text(text, rel, args)
        if not counts:
            continue
        changed.append((rel, counts))
        for k, v in counts.items():
            totals[k] = totals.get(k, 0) + v
        if args.apply:
            save_text(path, new_text)

    mode = "applied" if args.apply else "dry run - nothing written; add --apply"
    print("PERSONALIZE: %s" % mode)
    print("  user            %s" % args.user)
    print("  OneDrive folder %s" % args.onedrive_folder)
    print("  tunnel host     %s" % (args.tunnel_host or "(not given - YOUR-TUNNEL-HOST left in place)"))
    if args.email:
        print("  email           %s" % args.email)
    print()
    for rel, counts in changed:
        print("  %-64s %s" % (rel.replace(os.sep, "/"),
                              ", ".join("%s x%d" % (k, v) for k, v in sorted(counts.items()))))
    print()
    print("files changed: %d   replacements: %s" % (
        len(changed), ", ".join("%s=%d" % (k, v) for k, v in sorted(totals.items())) or "none"))
    if skipped_binary:
        print("skipped %d non-text files" % skipped_binary)

    left = [rel for rel, _ in changed] if not args.apply else []
    if args.apply:
        for path in iter_files(root):
            text = load_text(path)
            if text and (USER_PLACEHOLDER in text or (args.tunnel_host and TUNNEL_PLACEHOLDER in text)):
                left.append(os.path.relpath(path, root))
        if left:
            print("WARNING: placeholders remain in %d file(s): %s" % (len(left), ", ".join(left[:8])))

    print()
    print("Not touched, by design: docs that explain the placeholders, GitHubSetup/, scripts/,")
    print("skill attribution lines, and the Power Automate config (copy")
    print("Startup/FlowBridge/flow-bridge.config.example.json and fill in your own environment).")
    print("Nothing to rewrite, by design: the bridge launchers, the VS Code task file and the")
    print("roots in docs/bridge-facts.json derive from the clone location. Your config root goes")
    print("in Startup/cowork-env.cmd (copy cowork-env.example.cmd), not in a tracked file.")
    if not args.tunnel_host:
        print("Re-run with --tunnel-host once VS Code shows the forwarded address, then package")
        print("the connector manifests under Startup/Plugins/.")
    if " " in args.onedrive_folder and args.apply:
        print("Your OneDrive folder name contains spaces: the shipped launchers quote every path,")
        print("but check any job you write by hand.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
