#!/usr/bin/env python3
"""
job_lint.py - refuse a CommandJobs .bat that repeats a mistake already paid for.

WHY THIS EXISTS
---------------
Every check below encodes a lesson that was written down, promoted to a Rule,
loaded into context, and then violated anyway. Research on instruction-following
is blunt about the reason: compliance decays multiplicatively with the number of
simultaneous instructions, so a 60-rule preamble is not a control surface. The
only version of a rule that cannot be skipped is one that FAILS.

Prose asks. A check refuses.

TWO MODES
---------
  gate   (file arguments)      exit 1 on any FAIL. Use before running a new job.
  survey (directory argument)  report only, exit 0. Use to measure the backlog.
                               Add --strict to make survey fail too.

EXIT CODES
----------
  0  no FAIL findings
  1  at least one FAIL             <- a real finding
  2  usage error / unreadable input <- NOT a finding

  1 and 2 are deliberately distinct. A checker that never ran must not be
  mistaken for a checker that found something; that confusion cost a false
  "restore from backup" instruction on 2026-08-31.
  See lesson verifier-usage-error-reads-as-finding.
"""

import argparse
import json
import os
import re
import sys

CHECKS = []


ALL_LANGS = ("bat", "cmd", "ps1")


def check(code, source, severity="FAIL", langs=("bat", "cmd")):
    """Register a check.

    `source` is the lesson key or file this rule came from.
    `langs`  is the SCOPE: which file languages this check can actually read.

    The scope is mandatory and explicit because of what it cost to leave it
    implicit. digest-tiers.txt drops a rule out of always-on context whenever a
    check "already refuses the mistake" - but a check only refuses it on the
    surfaces it reads, and nothing recorded which those were. A rule enforced on
    .bat and silent on .ps1 was demoted as though it were enforced everywhere.
    See lesson digest-enforced-demotion-outruns-the-enforcer.

    Default is ("bat", "cmd") - the narrow, cmd-shaped assumption - so a new
    check has to claim PowerShell deliberately rather than inherit it.
    """
    unknown = [l for l in langs if l not in ALL_LANGS]
    if unknown:
        raise ValueError(f"check {code}: unknown language(s) {unknown}")

    def deco(fn):
        CHECKS.append({"code": code, "source": source, "severity": severity,
                       "langs": tuple(langs), "fn": fn})
        return fn
    return deco


def _is_comment(line):
    s = line.strip().upper()
    return s.startswith("REM") or s.startswith("::")


# --------------------------------------------------------------------------
# The checks. Each one is a lesson that prose failed to enforce.
# --------------------------------------------------------------------------

@check("no-verdict", "cowork-close-reports-ok-on-failed-commit", langs=("bat", "cmd"))
def c_no_verdict(text, lines):
    # BLIND on .ps1 deliberately: a sidecar script is invoked by a .bat and the
    # WRAPPER emits the verdict. Linting the sidecar for it flags 9 of 17
    # existing .ps1 files for a defect none of them has.
    if "COWORK_RESULT:" not in text:
        yield 0, ("emits no COWORK_RESULT line, so no caller - human or agent - can "
                  "tell a successful run from a failed one")


STATE_CMD = re.compile(
    r"^\s*(git\s+(commit|add|push|reset|checkout)|robocopy|move\b|del\b|xcopy|rmdir)",
    re.M | re.I)


@check("untested-exit", "cowork-close-reports-ok-on-failed-commit", langs=("bat", "cmd"))
def c_untested_exit(text, lines):
    # BLIND on .ps1: the pattern looks for `errorlevel`, which PowerShell does
    # not have - it uses $LASTEXITCODE / $?. Run against a .ps1 this reports a
    # defect on every script that touches git. A PowerShell-shaped sibling
    # check is the fix; until one exists this scope is the honest statement.
    body = "\n".join(l for l in lines if not _is_comment(l))
    if STATE_CMD.search(body) and not re.search(r"errorlevel", body, re.I):
        yield 0, ("runs a state-changing command but never tests errorlevel; a failure "
                  "will look identical to success")


@check("verifier-piped", "verifier-pipe-masks-the-exit-code", langs=ALL_LANGS)
def c_verifier_piped(text, lines):
    for i, ln in enumerate(lines, 1):
        if _is_comment(ln):
            continue
        if re.search(r"\bpython\b[^|>\n]*\|", ln, re.I):
            yield i, ("a checker's output is piped, so the PIPE's exit code is reported "
                      "and the checker's is discarded - run it bare")


ASSIGNMENT = re.compile(r"^\s*(set\s|\$\w+\s*=|[A-Za-z_]\w*\s*=)", re.I)


@check("checker-no-args", "verifier-usage-error-reads-as-finding", langs=ALL_LANGS)
def c_checker_no_args(text, lines):
    # FIXED 2026-09-01: this matched any line ENDING in <checker>.py, which
    # includes `set "SI=...\scripts\job_lint.py"`. A variable assignment is not
    # an invocation. It refused a job that never called the checker at all -
    # a false positive in the same family as the false negatives it guards.
    pat = re.compile(r"(lesson_check|lesson_gate|digest_apply|manifest_check|"
                     r"dream_analyze|job_lint)\.py\"?\s*$", re.I)
    for i, ln in enumerate(lines, 1):
        if _is_comment(ln) or ASSIGNMENT.match(ln):
            continue
        m = pat.search(ln.rstrip())
        if m:
            yield i, (f"{m.group(1)}.py is invoked with no arguments; argparse exits 2 "
                      f"and the job will report a corpus failure that did not happen")


CONTENT_READ = re.compile(
    r"select-string|get-content|readalltext|readallbytes|readalllines|"
    r"\bfindstr\b|\btype\s|\.readbyte|-raw\b|\bgrep\b", re.I)


@check("onedrive-recursive", "onedrive-recursive-scan-hydrates-tree", langs=ALL_LANGS)
def c_onedrive_recursive(text, lines):
    # SHARPENED 2026-09-01, and the sharpening is the whole point of this edit.
    # The rule as first written refused any -Recurse near a OneDrive path. The
    # lessons entry was then corrected by measurement: walking metadata across
    # the whole tree took about a second and hydrated NOTHING. It is reading
    # CONTENT that forces a fetch. The check was never updated to match, so it
    # went on enforcing the superseded wording - and because the rule is
    # dropped from always-on, that stale version is the one least likely to be
    # read. A bare enumeration is no longer a finding. A recursion whose output
    # is READ still is.
    for i, ln in enumerate(lines, 1):
        if _is_comment(ln):
            continue
        low = ln.lower()
        onedrive = ("onedrive" in low) or ("\\cowork" in low) or ("/cowork" in low)
        if not onedrive:
            continue
        window = " ".join(lines[i - 1:i + 3]).lower()
        walks = ("-recurse" in low) or bool(re.search(r"\bdir\b[^\n]*\s/s\b", low))
        if walks and CONTENT_READ.search(window):
            yield i, ("recurses a OneDrive tree AND reads the files it walks; the "
                      "READ is what hydrates cloud-only placeholders, and the job "
                      "blows the 300s cap. Enumerating metadata alone is fine")
        elif re.search(r"\bfindstr\b[^\n]*\s/s\b", low) and "skills\\" not in low:
            yield i, ("findstr /s over a OneDrive root reads every file it walks; "
                      "scope it to named files or one folder")


@check("quarantine-in-repo", "quarantine-destination-inside-the-repo", langs=ALL_LANGS)
def c_quarantine_in_repo(text, lines):
    for i, ln in enumerate(lines, 1):
        if _is_comment(ln):
            continue
        low = ln.lower()
        # The quarantine path must sit UNDER the repo to be a defect. Naive
        # co-occurrence flagged the legitimate case - moving a file OUT of the
        # repo INTO Downloads\COWORK_QUARANTINE puts both strings on one line.
        if re.search(r"copilot_cowork[\\/][^\"\s]*quarantine", low):
            yield i, ("a quarantine destination sits INSIDE the git repo; the next "
                      "git add -A commits exactly what the move was meant to remove")


@check("unguarded-snapshot", "artifact-rollback-overwritten-on-rerun", langs=ALL_LANGS)
def c_unguarded_snapshot(text, lines):
    for i, ln in enumerate(lines, 1):
        if _is_comment(ln):
            continue
        low = ln.lower()
        copies = re.search(r"(copy-item|\bcopy\b|xcopy)", low)
        aside = re.search(r"pre-edit|pre_edit|backup|\.bak|snapshot|original", low)
        if not (copies and aside):
            continue
        window = " ".join(lines[max(0, i - 5):i + 1]).lower()
        if "if not exist" not in window and "test-path" not in window:
            yield i, ("copies originals aside with no 'if not exist' / Test-Path guard; "
                      "a re-run overwrites the rollback with mutated content")


@check("errorlevel-in-parens", "cowork-close.bat header note, 2026-08-30", "WARN",
       langs=("bat", "cmd"))
def c_errorlevel_in_parens(text, lines):
    depth = 0
    for i, ln in enumerate(lines, 1):
        if _is_comment(ln):
            continue
        if depth > 0 and re.search(r"%ERRORLEVEL%", ln, re.I):
            yield i, ("%ERRORLEVEL% is read inside a parenthesised block, where it is "
                      "expanded at parse time and is stale - use labels")
        depth += ln.count("(") - ln.count(")")
        depth = max(depth, 0)


@check("no-output-decl", "cowork-job-standard", "WARN", langs=("bat", "cmd"))
def c_no_output_decl(text, lines):
    writes = re.search(r"COWORK_JOB_OUTPUT|>\s*\"%OUT%", text, re.I)
    if writes and "COWORK_OUTPUT:" not in text:
        yield 0, "writes output but declares no COWORK_OUTPUT directory"


# --------------------------------------------------------------------------

def lang_of(path):
    """Which language a file is linted as. Anything not .ps1 is treated as cmd,
    which keeps the default narrow rather than assuming coverage."""
    return "ps1" if path.lower().endswith(".ps1") else "bat"


def lint_text(text, lang="bat"):
    lines = text.splitlines()
    findings = []
    for c in CHECKS:
        if lang not in c["langs"]:
            continue
        for line_no, msg in c["fn"](text, lines):
            findings.append({
                "severity": c["severity"],
                "code": c["code"],
                "source": c["source"],
                "line": line_no,
                "message": msg,
            })
    findings.sort(key=lambda f: (f["line"], f["code"]))
    return findings


def lint_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return lint_text(fh.read(), lang_of(path)), None
    except OSError as exc:
        return [], str(exc)


def collect(paths):
    files, missing = [], []
    for p in paths:
        if os.path.isdir(p):
            for name in sorted(os.listdir(p)):
                # .ps1 added 2026-09-01. The sweep used to stop at .bat/.cmd
                # while several checks were already PowerShell-shaped, so 17
                # sidecar scripts were never handed to a check that could read
                # them. Widening the sweep is only safe now that each check
                # declares its own languages - without that, the same widening
                # produces a FAIL on 12 of those 17 for defects they do not have.
                if name.lower().endswith((".bat", ".cmd", ".ps1")):
                    files.append(os.path.join(p, name))
        elif os.path.isfile(p):
            files.append(p)
        else:
            missing.append(p)
    return files, missing


def main():
    ap = argparse.ArgumentParser(
        description="Refuse a job that repeats a mistake already written down.")
    ap.add_argument("paths", nargs="*",
                    help="one or more .bat/.cmd/.ps1 files, or a directory")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--strict", action="store_true",
                    help="in survey mode, exit 1 on FAIL as well")
    ap.add_argument("--only", help="report only this check code")
    ap.add_argument("--scope", action="store_true",
                    help="print which languages each check reads, and exit")
    a = ap.parse_args()

    if a.scope:
        print("job_lint scope - what each check CAN read, and what it cannot.\n")
        width = max(len(c["code"]) for c in CHECKS)
        for c in sorted(CHECKS, key=lambda x: x["code"]):
            blind = [l for l in ALL_LANGS if l not in c["langs"]]
            print(f"  {c['code']:<{width}}  reads: {','.join(c['langs']):<12} "
                  f"blind: {','.join(blind) if blind else '-'}")
        print("\nA rule may only be called ENFORCED for the languages listed under")
        print("'reads'. Anything under 'blind' is unenforced and must still be")
        print("delivered as prose. See digest-enforced-demotion-outruns-the-enforcer.")
        return 0

    if not a.paths:
        ap.error("no paths given (use --scope to inspect coverage without linting)")

    survey = any(os.path.isdir(p) for p in a.paths)
    files, missing = collect(a.paths)

    if missing:
        for m in missing:
            print(f"job_lint: cannot read {m}", file=sys.stderr)
        return 2
    if not files:
        print("job_lint: no .bat, .cmd or .ps1 files found", file=sys.stderr)
        return 2

    results, fails, warns, unreadable = {}, 0, 0, 0
    for f in files:
        found, err = lint_file(f)
        if err:
            unreadable += 1
            continue
        if a.only:
            found = [x for x in found if x["code"] == a.only]
        if found:
            results[f] = found
            fails += sum(1 for x in found if x["severity"] == "FAIL")
            warns += sum(1 for x in found if x["severity"] == "WARN")

    if unreadable:
        print(f"job_lint: {unreadable} file(s) unreadable", file=sys.stderr)
        return 2

    if a.json:
        print(json.dumps({"files": len(files), "fail": fails, "warn": warns,
                          "findings": results}, indent=2))
    else:
        for f in sorted(results):
            print(f"\n{os.path.basename(f)}")
            for x in results[f]:
                where = f"line {x['line']}" if x["line"] else "file"
                print(f"  {x['severity']:<4} [{x['code']}] {where}")
                print(f"       {x['message']}")
                print(f"       rule: {x['source']}")
        print()
        if survey:
            by_code = {}
            for fnd in results.values():
                for x in fnd:
                    by_code[x["code"]] = by_code.get(x["code"], 0) + 1
            print(f"SURVEY of {len(files)} job(s): {fails} FAIL, {warns} WARN, "
                  f"{len(files) - len(results)} clean")
            for code, n in sorted(by_code.items(), key=lambda kv: -kv[1]):
                print(f"   {n:>4}  {code}")
        else:
            print(f"job_lint: {len(files)} file(s), {fails} FAIL, {warns} WARN")
        n_ps1 = sum(1 for f in files if lang_of(f) == "ps1")
        if n_ps1:
            applied = sum(1 for c in CHECKS if "ps1" in c["langs"])
            print(f"   scope: {n_ps1} PowerShell file(s) linted against "
                  f"{applied} of {len(CHECKS)} checks - run --scope for the rest")

    if fails and (not survey or a.strict):
        print("JOB_LINT: FAIL")
        return 1
    print("JOB_LINT: CLEAN" if not fails else "JOB_LINT: FAIL (survey, not gating)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
