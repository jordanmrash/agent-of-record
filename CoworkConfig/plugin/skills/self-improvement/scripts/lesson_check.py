#!/usr/bin/env python3
"""
lesson_check.py - make the self-improvement skill fail-able.

Reads cowork-lessons.md and cross-examines it against its own stated rules.
Exits non-zero when the log has drifted. This is the standalone skill's
equivalent of gate_check.py in alteryx-to-python: the prose says what a good
entry looks like, this decides whether the file actually contains them.

Usage:
    python lesson_check.py <path-to-cowork-lessons.md> [--json] [--strict]

Exit codes:
    0  clean
    1  one or more FAIL findings
    2  could not read or parse the file at all
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict

# lesson_brief lives beside this file and owns the tier predicate. Importing it
# is deliberate: see digest_findings below.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REQUIRED = ["Pattern-Key", "Date", "Trigger", "Failed", "Why", "Worked", "Evidence"]

# Optional scope fields. Absent means everywhere, so an untagged corpus is valid and
# behaves exactly as it did before scoping existed.
VALID_ROUTES = {"claude", "copilot"}
VALID_PLATFORMS = {"windows", "macos"}
VALID_TRIGGERS = {"failure", "correction", "better-approach", "contradiction", "pattern", "open",
                  "false-success", "near-miss", "missing-capability"}

# A Worked line naming one of these is enforceable rather than advisory.
MECHANISM = re.compile(
    r"\.py\b|\.bat\b|\.ps1\b|\bassert|\bexit code\b|\bcertutil\b|\bhash\b|"
    r"\bgrep\b|\bregex\b|\bcount ==|\bnon-zero\b|\bvalidate_\w+|"
    r"\bscore_\w+|\bmd5\b|\bsha-?256\b", re.I)

SECTION_RE = re.compile(r"^## (.+)$", re.M)
ENTRY_RE = re.compile(r"^### (.+)$", re.M)


def parse(text):
    sections = [(m.start(), m.group(1).strip()) for m in SECTION_RE.finditer(text)]
    sections.append((len(text), None))

    entries = []
    for m in ENTRY_RE.finditer(text):
        start = m.start()
        section = None
        for i in range(len(sections) - 1):
            if sections[i][0] < start < sections[i + 1][0]:
                section = sections[i][1]
                break
        nxt = ENTRY_RE.search(text, m.end())
        end = nxt.start() if nxt else len(text)
        body = text[m.end():end]
        fields = {}
        for fm in re.finditer(r"^- \*\*([\w\s-]+):\*\*\s?(.*)$", body, re.M):
            fields.setdefault(fm.group(1).strip(), fm.group(2).strip())
        entries.append({
            "title": m.group(1).strip(),
            "section": section,
            "line": text[:start].count("\n") + 1,
            "fields": fields,
            "body": body,
        })
    return [s[1] for s in sections[:-1]], entries


def check(text):
    findings = []

    def add(level, code, msg, entry=None):
        findings.append({
            "level": level, "code": code, "message": msg,
            "key": (entry or {}).get("fields", {}).get("Pattern-Key"),
            "line": (entry or {}).get("line"),
        })

    section_names, entries = parse(text)

    if not entries:
        add("FAIL", "no_entries", "No '### ' entries found. Wrong file or a broken parse.")
        return findings, entries

    def first_index(prefix):
        for i, s in enumerate(section_names):
            if s and s.lower().startswith(prefix):
                return i
        return None

    fi = first_index("failures")
    ci = first_index("contradictions")
    if fi is None:
        add("FAIL", "missing_section", "No '## Failures' section.")
    if ci is not None and fi is not None and ci < fi:
        add("FAIL", "section_order",
            "'Contradictions' precedes 'Failures', so appending at the end of the "
            "file misfiles entries.")

    keys = defaultdict(list)
    for e in entries:
        f = e["fields"]
        key = f.get("Pattern-Key")

        for req in REQUIRED:
            if req not in f or not f[req]:
                add("FAIL", "missing_field",
                    f"'{e['title'][:55]}' is missing **{req}**.", e)

        if key:
            keys[key].append(e)

        trig = (f.get("Trigger") or "").lower().strip()
        if trig and trig not in VALID_TRIGGERS:
            add("WARN", "unknown_trigger", f"Trigger '{trig}' is not a known value.", e)

        # Routes / Platforms narrow WHERE a rule is served. Both optional; absent means
        # everywhere. A typo must fail loudly: a misspelled value silently narrows a rule
        # to nothing, which is the one failure mode worse than not scoping at all.
        for field, valid in (("Routes", VALID_ROUTES), ("Platforms", VALID_PLATFORMS)):
            raw = (f.get(field) or "").strip()
            if not raw:
                continue
            values = [v for v in re.split(r"[,\s]+", raw.lower()) if v]
            unknown = [v for v in values if v not in valid]
            if unknown:
                add("FAIL", f"unknown_{field.lower()}",
                    f"{field} value(s) {', '.join(unknown)} not in "
                    f"{', '.join(sorted(valid))}.", e)
            elif len(values) == len(valid):
                add("WARN", f"redundant_{field.lower()}",
                    f"{field} lists every value, which is the same as omitting it.", e)

        sec = (e["section"] or "").lower()
        if trig == "contradiction" and not sec.startswith("contradictions"):
            add("FAIL", "misfiled_contradiction",
                f"Trigger is 'contradiction' but it sits under '{e['section']}'.", e)

        worked = f.get("Worked", "")
        if re.match(r"\s*\**UNKNOWN\b", worked, re.I) and not sec.startswith("open questions"):
            add("FAIL", "misfiled_unknown",
                f"Worked is UNKNOWN but it sits under '{e['section']}'.", e)

        # The complement of the two checks above: a RESOLVED entry parked under Open
        # questions, or a non-contradiction filed under Contradictions. Both are what
        # "append at the end of the file" produces. Added 2026-09-08 after 4 + 7 such
        # entries were found in a corpus this checker had passed clean.
        if sec.startswith("open questions") and worked and not re.match(r"\s*\**UNKNOWN\b", worked, re.I):
            add("FAIL", "misfiled_failure",
                f"Worked is a real fix but it sits under '{e['section']}'. "
                "Open questions holds only unresolved entries - move it to Failures.", e)
        if sec.startswith("contradictions") and trig and trig != "contradiction":
            add("FAIL", "misfiled_failure",
                f"Trigger is '{trig}' but it sits under '{e['section']}'. "
                "Only contradiction entries belong there - move it to Failures.", e)

        ev = f.get("Evidence", "")
        if ev and not re.search(r"measured|inferred|mixed|unverified|reported", ev, re.I):
            add("WARN", "evidence_unlabelled",
                "Evidence does not say whether it is measured or inferred.", e)

        if worked and not MECHANISM.search(worked):
            add("INFO", "prose_only",
                "Worked names no runnable check, so it is advice.", e)

        # a repeat lesson with no one-line Rule cannot reach the digest, and the
        # digest is the only delivery path measured to actually fire
        hits_raw = f.get("Hits", "")
        m = re.match(r"\s*(\d+)", hits_raw)
        hits = int(m.group(1)) if m else 0
        promoted = "Promoted-to" in f
        promo_flag = f.get("Promotion", "")
        if hits >= 2 and not promoted and not promo_flag:
            add("FAIL", "promotion_due",
                f"Hits={hits} with no **Promoted-to** and no **Promotion** line. "
                "A twice-hit lesson left in the log gets hit a third time.", e)
        if promo_flag and re.search(r"awaiting|DUE", promo_flag, re.I) and not promoted:
            add("WARN", "promotion_stale",
                f"Promotion still open: '{promo_flag[:60]}'.", e)
        if hits >= 2 and not f.get("Rule"):
            add("FAIL", "no_rule_line",
                f"Hits={hits} but no one-line **Rule:** field, so it cannot reach the "
                "instructions digest. A repeat lesson that only lives in this file "
                "relies on someone opening this file.", e)

    for k, es in keys.items():
        if len(es) > 1:
            add("FAIL", "duplicate_key",
                f"Pattern-Key '{k}' appears {len(es)} times (lines "
                f"{', '.join(str(x['line']) for x in es)}).")

    known = set(keys)
    for e in entries:
        seealso = e["fields"].get("See also", "")
        for ref in re.findall(r"`?([a-z0-9]+(?:-[a-z0-9]+){2,})`?", seealso):
            if ref not in known:
                add("WARN", "dangling_see_also",
                    f"See also points at '{ref}', not a Pattern-Key in this file.", e)

    clusters = defaultdict(list)
    for k in known:
        clusters[k.split("-")[0]].append(k)
    # Size alone is not a defect. The failure this was written to catch - a repeat
    # re-logged under a new key instead of promoted - is exactly `promotion_due`,
    # so a cluster only earns a WARN when it actually contains one. Warning on
    # size alone fired on three healthy clusters and taught the reader to skim
    # past warnings, which is how eight promotion_due FAILs survived unread.
    by_key = {e["fields"].get("Pattern-Key"): e for e in entries}
    for prefix, ks in sorted(clusters.items()):
        if len(ks) < 6:
            continue
        unpromoted = []
        for k in sorted(ks):
            e = by_key.get(k)
            if not e:
                continue
            f = e["fields"]
            m = re.match(r"\s*(\d+)", f.get("Hits", ""))
            # Must use the SAME definition of resolved as promotion_due above:
            # Promoted-to (folded into another key) OR Promotion (carried into
            # the digest as a loaded rule). Both genuinely resolve a repeat.
            # 2026-08-30: this re-implemented the test and accepted only
            # Promoted-to, so an entry resolved by Promotion cleared the FAIL
            # and then warned forever - a warning that can never be satisfied,
            # which is the always-on warning this check was rewritten to stop.
            if m and int(m.group(1)) >= 2 and "Promoted-to" not in f \
                    and not f.get("Promotion", ""):
                unpromoted.append(k)
        if unpromoted:
            add("WARN", "topic_cluster",
                f"{len(ks)} keys share the prefix '{prefix}-' and {len(unpromoted)} "
                f"is a repeat that was never promoted: {', '.join(unpromoted)}. "
                "That is the re-logging this check exists to catch.")
        else:
            add("INFO", "topic_cluster_size",
                f"{len(ks)} keys share the prefix '{prefix}-'. Every repeat in it is "
                "promoted, so this is a size reading, not a defect.")

    return findings, entries


# ---------------------------------------------------------------------------
# Digest freshness - TIER-AWARE since 2026-09-11.
#
# The block carries the ALWAYS-ON tier only: repeats plus pins, minus anything
# an automated check already enforces. The original check required EVERY
# authored Rule to appear in it, which was correct until the 2026-08-31
# tiering and reports `authored - always-on` missing every run afterwards - 71
# of 109 on the corpus the day this was fixed, arithmetic that does not change
# however current the digest is. Bare lesson_check exited 0 on the same bytes.
#
# The tier predicate is CALLED from lesson_brief.select_alwayson, never copied
# here, so a future change to the tiering cannot leave this check behind. That
# is the whole point: see lesson enforcer-encodes-the-superseded-rule, whose
# third hit is this defect.
# ---------------------------------------------------------------------------

def digest_findings(entries, dtext, tiers_path=None):
    """FAIL findings about the digest block. Separated from main() so the
    selftest can drive it - it had no negative control for three weeks because
    it lived inline and check() never saw it."""
    out = []

    def fail(code, message):
        out.append({"level": "FAIL", "code": code, "message": message,
                    "key": None, "line": None})

    m = re.search(r"LESSON-DIGEST:BEGIN(.*?)LESSON-DIGEST:END", dtext, re.S)
    if not m:
        fail("digest_missing",
             "No LESSON-DIGEST block found in the instructions file. "
             "Regenerate it with digest_apply.py.")
        return out
    block = m.group(1)

    try:
        import lesson_brief
    except ImportError as exc:
        fail("digest_tiers_unavailable",
             f"cannot import lesson_brief, which owns the tier predicate: {exc}. "
             "This check cannot run - that is not the same as the digest being "
             "clean.")
        return out

    path = tiers_path or lesson_brief.DEFAULT_TIERS
    if not os.path.isfile(path):
        fail("digest_tiers_missing",
             f"no tiers file at {path}, so the always-on set cannot be "
             "computed. Refusing to guess: with no PIN/ENFORCED data the set "
             "is repeats-only, which is a DIFFERENT set, not the full one.")
        return out

    pins, enforced = lesson_brief.read_tiers(path)
    adapted = []
    for e in entries:
        f = e["fields"]
        hm = re.match(r"\s*(\d+)", f.get("Hits", ""))
        adapted.append({"key": f.get("Pattern-Key"),
                        "rule": f.get("Rule", "").strip(),
                        "hits": int(hm.group(1)) if hm else 1})
    ruled, keep = lesson_brief.select_alwayson(adapted, pins, enforced)

    missing = [a["key"] for a in keep
               if a["rule"][:60].rstrip() and a["rule"][:60].rstrip() not in block]
    if missing:
        fail("digest_stale",
             f"{len(missing)} ALWAYS-ON Rule(s) are not in the instructions "
             f"digest, so a rule that recurred or was pinned is not loading: "
             f"{', '.join(m for m in missing[:5])}"
             + (" ..." if len(missing) > 5 else "")
             + f". {len(keep)} always-on of {len(ruled)} authored. "
               "Regenerate with digest_apply.py.")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="treat WARN as failing too")
    ap.add_argument("--digest", metavar="PATH",
                    help="path to copilot-instructions.md; FAILS if its LESSON-DIGEST "
                         "block is missing any Rule that ranks high enough to be in it")
    a = ap.parse_args()

    try:
        text = open(a.path, encoding="utf-8").read()
    except OSError as exc:
        print(f"FATAL: cannot read {a.path}: {exc}", file=sys.stderr)
        return 2

    findings, entries = check(text)

    # Digest freshness. A Rule that never reaches the instructions block depends on
    # somebody opening the archive, which is the dependency this whole skill exists
    # to remove. Added 2026-08-28 after the block went stale within the hour.
    if a.digest:
        try:
            dtext = open(a.digest, encoding="utf-8").read()
        except OSError as exc:
            findings.append({"level": "FAIL", "code": "digest_unreadable",
                             "message": f"cannot read {a.digest}: {exc}",
                             "key": None, "line": None})
        else:
            import re as _re
            findings.extend(digest_findings(entries, dtext))
    fails = [f for f in findings if f["level"] == "FAIL"]
    warns = [f for f in findings if f["level"] == "WARN"]
    infos = [f for f in findings if f["level"] == "INFO"]
    prose = [f for f in infos if f["code"] == "prose_only"]
    notes = [f for f in infos if f["code"] != "prose_only"]

    result = {
        "path": a.path,
        "entries": len(entries),
        "unique_keys": len({e["fields"].get("Pattern-Key") for e in entries} - {None}),
        "fail": len(fails), "warn": len(warns), "prose_only": len(prose),
        "findings": findings,
        "passed": not fails and (not warns if a.strict else True),
    }

    if a.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"lesson_check: {result['entries']} entries, {result['unique_keys']} unique keys")
        print(f"  FAIL {len(fails)}   WARN {len(warns)}   prose-only {len(prose)}")
        for f in fails + warns:
            loc = f" (line {f['line']})" if f.get("line") else ""
            key = f" [{f['key']}]" if f.get("key") else ""
            print(f"  {f['level']:4} {f['code']}{key}{loc}: {f['message']}")
        for f in notes:
            key = f" [{f['key']}]" if f.get("key") else ""
            print(f"  INFO {f['code']}{key}: {f['message']}")
        if prose:
            pct = round(100 * len(prose) / max(1, result["entries"]))
            print(f"  INFO {len(prose)} entries ({pct}%) are advice with no runnable check.")

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
