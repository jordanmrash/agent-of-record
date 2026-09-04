#!/usr/bin/env python3
"""
lesson_brief.py - make the lessons usable BEFORE acting, not after.

The pre-task scan in copilot-instructions.md fails because it asks for an
action: go read a 115 KB file. Measured across 2026-08-24, -25 and -28, that
action does not happen. This script attacks the problem from both ends.

  --for <keyword>   Targeted lookup. One call, returns only the one-line Rule
                    of entries whose key, title or Rule matches. Sub-second,
                    so the "too expensive to check" excuse disappears.

  --digest          Emits EVERY authored rule, ranked, as a compact block
                    for pasting into copilot-instructions.md between the
                    LESSON-DIGEST markers. That file loads unconditionally
                    every session, so a rule living there needs NO action to
                    be read. This is the only path measured to work.

  --missing-rules   Lists entries that earn a place in the digest but have no
                    one-line `Rule:` field yet.

The `Rule:` field is authored, never auto-summarised. A script cannot compress
a Worked paragraph into an imperative without inventing, and an invented rule
is worse than no rule.

Exit codes:
    0  ran fine
    2  could not read the file
"""

import argparse
import os
import re
import sys

ENTRY_RE = re.compile(r"^### (.+)$", re.M)
FIELD_RE = re.compile(r"^- \*\*([\w\s-]+):\*\*\s?(.*)$", re.M)

# Which trigger surface a key belongs to.
#
# PREFIX FIRST, content second. Measured 2026-08-28: a first-match content regex
# put `skill-voiceprofile-calibrate-from-user-diff` under "files", because the word
# "profile" contains "file". `--for skills` therefore MISSED it and `--for files`
# returned something irrelevant. That is a silent false negative in the one tool
# built to stop silent false negatives.
#
# The Pattern-Key prefix is authored deliberately, so it decides. Content matching
# is only the fallback for keys whose prefix is not a known surface. Word boundaries
# throughout, because substring matching is what caused the defect.
PREFIX_SURFACE = {
    'bridge': 'bridge',
    'git': 'git', 'gt': 'git',
    'skill': 'skills', 'voice': 'skills', 'myvoice': 'skills',
    'onedrive': 'files', 'artifact': 'files', 'delivery': 'files',
    'docx': 'files', 'upload': 'files',
    'memory': 'memory', 'savememory': 'memory', 'lessons': 'memory',
    'promotion': 'memory',
    'verifier': 'claims', 'prestage': 'claims', 'agent': 'claims',
    'recommend': 'claims',
}

SURFACES = [
    ("bridge", r"\bbridge|\bprobe\b|tunnel|893[123]"),
    ("git",    r"\bgit\b|\bcommit\b|\brepo\b"),
    ("skills", r"\bskill|\bvoice\b|myvoice"),
    ("memory", r"\bmemory\b|\blesson"),
    ("files",  r"artifact|onedrive|\bfile\b|\bfiles\b|upload|download"),
    ("claims", r"\bclaim|verif|false[- ]success"),
]


def surface_of(key, text):
    """Prefix decides; content is the fallback. See PREFIX_SURFACE for why."""
    head = key.split("-")[0].lower()
    if head in PREFIX_SURFACE:
        return PREFIX_SURFACE[head]
    blob = f"{key} {text}".lower()
    for name, pat in SURFACES:
        if re.search(pat, blob):
            return name
    return "other"


def load(path):
    text = open(path, encoding="utf-8").read()
    entries = []
    for m in ENTRY_RE.finditer(text):
        nxt = ENTRY_RE.search(text, m.end())
        body = text[m.end():nxt.start() if nxt else len(text)]
        fields = {}
        for fm in FIELD_RE.finditer(body):
            fields.setdefault(fm.group(1).strip(), fm.group(2).strip())
        key = fields.get("Pattern-Key")
        if not key:
            continue
        hits_m = re.match(r"\s*(\d+)", fields.get("Hits", ""))
        entries.append({
            "key": key,
            "title": m.group(1).strip(),
            "rule": fields.get("Rule", "").strip(),
            "worked": fields.get("Worked", "").strip(),
            "hits": int(hits_m.group(1)) if hits_m else 1,
            "date": fields.get("Date", ""),
            "promoted": "Promoted-to" in fields,
            "surface": surface_of(key, m.group(1)),
        })
    return entries


def rank(e):
    """Highest value first: repeat offenders, then promoted, then recency."""
    return (-e["hits"], not e["promoted"], e["date"])


def cmd_for(entries, kw):
    kw = kw.lower()
    hits = [e for e in entries
            if kw in e["key"].lower()
            or kw in e["title"].lower()
            or kw in e["rule"].lower()
            or kw in e["surface"]]
    if not hits:
        print(f"no lessons matching '{kw}'")
        return
    print(f"{len(hits)} lesson(s) matching '{kw}':\n")
    for e in sorted(hits, key=rank):
        line = e["rule"] or (e["worked"][:150] + ("..." if len(e["worked"]) > 150 else ""))
        flag = f" [{e['hits']} hits]" if e["hits"] > 1 else ""
        print(f"  - {line}")
        print(f"      ({e['key']}{flag})")


# ---------------------------------------------------------------------------
# TIERED ALWAYS-ON SELECTION
#
# The digest carried every authored Rule - 60 of them by 2026-08-31. That is
# not a control surface: instruction-following decays multiplicatively with
# the number of simultaneous instructions, so the 60th rule dilutes the first.
#
# The axis is THREE-way, not "keep the frequent ones":
#   ENFORCED  a check now refuses the mistake on EVERY surface the mistake can
#             be made on, so the prose is redundant. The strongest kind of drop.
#   PARTIAL   a check refuses it on some surfaces and is blind on others. Also
#             dropped from always-on - the per-surface preflight still delivers
#             it - but the blind surfaces are declared so the claim can be
#             audited by scope_check.py rather than assumed. Added 2026-09-01
#             after an ENFORCED rule was missed on a surface its enforcer
#             cannot read (digest-enforced-demotion-outruns-the-enforcer).
#   PIN       one violation is irreversible or invisible and no check exists
#             yet. Always-on regardless of hit count. git-deletion-does-not-
#             sanitize-history has fired ONCE and is unrecoverable.
#   repeat    hits >= 2, computed from the lessons file, never hand-listed.
#
# NOTHING IS DELETED. Everything else stays in cowork-lessons.md and loads
# through `lesson_gate.py preflight --surface <x>` at the moment of the action,
# which is when it is useful anyway.
# ---------------------------------------------------------------------------

DEFAULT_TIERS = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "digest-tiers.txt")


def read_tiers(path):
    """Parse digest-tiers.txt into (pins, enforced). Missing file -> ({}, {}).

    PARTIAL is read as ENFORCED here, deliberately (added 2026-09-01). A PARTIAL
    rule is one whose enforcer covers some surfaces and not others; it is still
    excluded from the always-on block, because the per-surface preflight
    delivers it at the moment of the action, which is when it applies. The
    distinction exists so the CLAIM is honest and auditable in digest-tiers.txt,
    not to change what loads at turn 1 - the always-on set is identical either
    way, and that was verified by regenerating the block after the rename.

    A missing tiers file is NOT silently equivalent to an untiered digest:
    with no PIN/ENFORCED data the block becomes repeats-only, which is a
    DIFFERENT set, not the old full set. cmd_digest warns loudly on stderr
    rather than emitting a block that looks authoritative.
    """
    pins, enforced = {}, {}
    if not path or not os.path.isfile(path):
        return pins, enforced
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [x.strip() for x in line.split("|")]
            head = parts[0].split(None, 1)
            if len(head) != 2:
                continue
            kind, key = head[0].upper(), head[1].strip()
            if kind == "PIN":
                pins[key] = parts[1] if len(parts) > 1 else ""
            elif kind in ("ENFORCED", "PARTIAL"):
                enforced[key] = parts[1] if len(parts) > 1 else ""
    return pins, enforced


def select_alwayson(entries, pins, enforced, min_hits=2):
    """The always-on set. ENFORCED wins over hits: a rule a check refuses is
    dropped even at 3 hits, because the check cannot be skipped and the prose
    can."""
    ruled = [e for e in entries if e["rule"]]
    keep = [e for e in ruled
            if e["key"] not in enforced
            and (e["hits"] >= min_hits or e["key"] in pins)]
    return ruled, keep


def cmd_digest(entries, limit, tiers_path=None):
    """The block that goes into copilot-instructions.md.

    Emits the ALWAYS-ON tier only - repeats plus pins, minus anything an
    automated check already enforces. The rest stay in the lessons file and
    load per surface through lesson_gate preflight.

    `limit` remains available for inspection but is NOT how the block is
    trimmed: --limit caps a ranked list and silently drops its tail, which is
    the lowest-ranked and therefore NEWEST rules. Tiering drops by a stated
    reason instead, and the reason is auditable in digest-tiers.txt.
    """
    if tiers_path is None:
        tiers_path = DEFAULT_TIERS
    pins, enforced = read_tiers(tiers_path)
    withrule, kept = select_alwayson(entries, pins, enforced)

    if not pins and not enforced:
        # Loud, and on stderr so it cannot be mistaken for block content.
        print("WARNING: no tiers file at %s - no PIN or ENFORCED tier is in "
              "effect, so this block is repeats-only (hits >= 2). Pinned "
              "single-hit rules are NOT in it and enforced rules are NOT "
              "excluded. Do not compare it against a tiered digest."
              % tiers_path, file=sys.stderr)

    ranked = sorted(kept, key=rank)
    chosen = ranked[:limit] if limit else ranked
    cut = ranked[len(chosen):]
    if cut:
        print("WARNING: --limit %d drops %d authored rule(s) that will NOT load "
              "next session: %s" % (limit, len(cut), ", ".join(e["key"] for e in cut)),
              file=sys.stderr)

    by_surface = {}
    for e in chosen:
        by_surface.setdefault(e["surface"], []).append(e)

    print("<!-- LESSON-DIGEST:BEGIN - generated by "
          "self-improvement/scripts/lesson_brief.py --digest. Do not hand-edit. -->")
    print("### Rules already paid for")
    print()
    print("Each line below was learned by getting it wrong at least once. They live here,")
    print("not in the lessons file, because this file loads every session and the lessons")
    print("file only loads if I remember to open it. Three sessions proved I do not.")
    print()
    print("This is the ALWAYS-ON tier: rules that recurred, plus rules whose first")
    print("violation is irreversible. Rules an automated check now refuses were dropped")
    print("from here BECAUSE the check cannot be skipped. Nothing was deleted - every")
    print("other rule is in cowork-lessons.md and loads with")
    print("`lesson_gate.py preflight --surface <bridge|files|memory|skills|git|claims>`")
    print("at the moment it applies.")
    print()
    for name, _ in SURFACES + [("other", "")]:
        group = by_surface.get(name)
        if not group:
            continue
        print(f"**{name}**")
        for e in group:
            flag = f" _({e['hits']}x)_" if e["hits"] > 1 else ""
            print(f"- {e['rule']}{flag}")
        print()
    # MARKER CONTRACT - all three numbers, because two cannot express tiering.
    # G2 recomputes each and fails on any mismatch, so a hand-edit or a stale
    # regeneration is caught rather than assumed.
    print(f"<!-- LESSON-DIGEST:END - {len(chosen)} always-on of "
          f"{len(withrule)} rules from {len(entries)} entries -->")


def cmd_missing(entries, limit):
    candidates = [e for e in sorted(entries, key=rank)[:limit] if not e["rule"]]
    if not candidates:
        print("every digest-eligible entry has a Rule line")
        return
    print(f"{len(candidates)} entr(ies) rank high enough for the digest but have no "
          f"one-line **Rule:** field.\nAuthor one for each (never auto-summarise):\n")
    for e in candidates:
        print(f"  {e['key']}  [{e['hits']} hits]")
        print(f"    title:  {e['title'][:80]}")
        print(f"    worked: {e['worked'][:110]}...")
        print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--for", dest="kw", help="targeted lookup by keyword or surface")
    ap.add_argument("--digest", action="store_true", help="emit the instructions block")
    ap.add_argument("--missing-rules", action="store_true")
    # --tiers added 2026-09-01 so that "does a tiering edit move the always-on
    # set?" is a RUNNABLE comparison rather than a claim: generate the block
    # under two tier files and diff them. Without it that question could only
    # be answered by hand, which is how the ENFORCED labels went four days
    # without anyone checking what they asserted.
    ap.add_argument("--tiers", default=None, help="override the tiering file")
    ap.add_argument("--limit", type=int, default=None,
                    help="cap the digest at N rules "
                         "(default: emit every authored Rule)")
    a = ap.parse_args()

    try:
        entries = load(a.path)
    except OSError as exc:
        print(f"FATAL: cannot read {a.path}: {exc}", file=sys.stderr)
        return 2

    if a.kw:
        cmd_for(entries, a.kw)
    elif a.digest:
        cmd_digest(entries, a.limit, a.tiers)
    elif a.missing_rules:
        cmd_missing(entries, a.limit or 24)
    else:
        surfaces = {}
        for e in entries:
            surfaces[e["surface"]] = surfaces.get(e["surface"], 0) + 1
        withrule = sum(1 for e in entries if e["rule"])
        print(f"{len(entries)} entries, {withrule} with a one-line Rule")
        print("surfaces: " + ", ".join(f"{k} {v}" for k, v in sorted(surfaces.items())))
        print("\nuse --for <keyword> before acting, or --digest to refresh the "
              "instructions block")
    return 0


if __name__ == "__main__":
    sys.exit(main())
