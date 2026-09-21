#!/usr/bin/env python3
"""
dream_analyze.py - the deterministic half of the nightly consolidation pass.

WHAT THIS IS FOR
----------------
The lessons log and the memory files grow by appending. Nothing ever merges two
entries that say the same thing, retires one a later entry contradicted, or asks
whether a finding is reachable at all. Done by hand that is slow and easy to skip;
done by an LLM alone at 2am with no user present it is a fabrication risk.

So the split is the same one the rest of this skill uses: MECHANICAL findings
here, AUTHORED judgement by a human (or by an agent writing a proposal a human
approves). This script computes what can be counted and NEVER decides.

HARD RULE: THIS SCRIPT IS READ-ONLY.
It opens files for reading only and writes nothing but its own report on stdout.
It cannot delete, merge, rewrite or reorder a lesson or a memory file. A nightly
job that mutates the knowledge base unattended can destroy it in one bad run, and
"superseded" is a judgement no counter should make. Proposals go to a human.

SECTIONS
--------
  REACHABILITY  what fraction of findings can actually reach a session, per
                surface. An entry with no `Rule:` line never enters the digest,
                so it is inert until somebody opens the archive.
  DUPLICATES    entry pairs whose Rule or title are near-identical. Candidates
                for a merge + Hits bump, which is what turns two invisible
                single-hit lessons into one ranked repeat offender.
  SUPERSEDED    entries carrying their own contradiction markers (SUPERSEDED,
                CORRECTED, WRONG, RETIRED, Promoted-to, Fixed) - these are the
                ones most likely to be stale or already resolved.
  OPEN          entries with a `Still open:` field, so open work cannot quietly
                become permanent.
  POINTERS      every deep memory file has an index entry and vice versa.
  GROWTH        file sizes and digest share, so bloat is visible before it makes
                the digest too long to be read.

Exit codes:
    0  analysis completed (findings are REPORTED, not failed on)
    1  --strict was given AND at least one finding was reported
    2  an input could not be read
"""

import argparse
import difflib
import os
import re
import sys

# Duplicate-detection calibration. See duplicate_floor() for why each exists.
DUP_PCT = 99.5      # percentile of the corpus's own pairwise distribution
DUP_MIN = 0.50      # absolute meaningfulness bar; keeps the check able to say no
MIN_PAIRS = 200     # below this a percentile is just the maximum, renamed

ENTRY_RE = re.compile(r"^### (.+)$", re.M)
FIELD_RE = re.compile(r"^- \*\*([\w\s-]+):\*\*\s?(.*)$", re.M)
# CASE-SENSITIVE, WHOLE-WORD. The first version of this matched against
# body.upper(), so the ordinary prose word "wrong" matched the marker WRONG and
# the section flagged 40 of 87 entries - a warning that is always on, which is
# training to skip warnings. The convention in the log is that a retirement
# marker is SHOUTED, so only uppercase counts. Same defect family as
# classifier-substring-match-silently-misfiles.
SUPERSEDE_RE = re.compile(
    r"\b(SUPERSEDED|RETIRED|DISPROVEN|OBSOLETE|NO LONGER TRUE|WRONG)\b")

# Kept identical in spirit to lesson_brief.surface_of: prefix decides, content
# is only the fallback. Duplicated rather than imported so this script still
# runs if lesson_brief is absent, but the prefix table is the same idea.
PREFIX_SURFACE = {
    'bridge': 'bridge', 'git': 'git', 'gt': 'git',
    'skill': 'skills', 'voice': 'skills', 'myvoice': 'skills',
    'onedrive': 'files', 'artifact': 'files', 'delivery': 'files',
    'docx': 'files', 'upload': 'files', 'grepc': 'files',
    'memory': 'memory', 'savememory': 'memory', 'lessons': 'memory',
    'promotion': 'memory',
    'verifier': 'claims', 'prestage': 'claims', 'agent': 'claims',
    'recommend': 'claims', 'guard': 'claims', 'diagnosis': 'claims',
    'quarantine': 'git', 'cowork': 'git',
}
CONTENT_SURFACE = [
    ("bridge", r"\bbridge|\bprobe\b|tunnel|893[123]"),
    ("git",    r"\bgit\b|\bcommit\b|\brepo\b"),
    ("skills", r"\bskill|\bvoice\b|myvoice"),
    ("memory", r"\bmemory\b|\blesson"),
    ("files",  r"artifact|onedrive|\bfile\b|\bfiles\b|upload|download"),
    ("claims", r"\bclaim|verif|false[- ]success"),
]


def norm(s):
    """Lowercase, strip punctuation and collapse space, for comparison only."""
    s = re.sub(r"`[^`]*`", " ", s.lower())
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def surface_of(key, title):
    head = key.split("-")[0].lower()
    if head in PREFIX_SURFACE:
        return PREFIX_SURFACE[head]
    blob = f"{key} {title}".lower()
    for name, pat in CONTENT_SURFACE:
        if re.search(pat, blob):
            return name
    return "other"


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError as exc:
        sys.stderr.write("FATAL: cannot read %s: %s\n" % (path, exc))
        sys.exit(2)


def load_entries(path):
    text = read(path)
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
            "hits": int(hits_m.group(1)) if hits_m else 1,
            "date": fields.get("Date", ""),
            "promoted": "Promoted-to" in fields,
            "fixed": "Fixed" in fields,
            "still_open": fields.get("Still open", "").strip(),
            "body": body,
            "surface": surface_of(key, m.group(1)),
        })
    return entries


def section(title):
    print()
    print("=" * 68)
    print(title)
    print("=" * 68)


def do_reachability(entries):
    section("REACHABILITY - can a finding actually reach a session?")
    total = len(entries)
    ruled = [e for e in entries if e["rule"]]
    print("%d of %d entries (%.0f%%) carry a Rule line and reach the digest."
          % (len(ruled), total, 100.0 * len(ruled) / total if total else 0))
    print("The rest are inert until somebody opens the archive.")
    print()
    print("%-10s %6s %6s %8s  %s" % ("surface", "total", "ruled", "inert", "reach"))
    findings = 0
    by = {}
    for e in entries:
        by.setdefault(e["surface"], []).append(e)
    for name in sorted(by):
        grp = by[name]
        r = sum(1 for e in grp if e["rule"])
        pct = 100.0 * r / len(grp)
        flag = "  <- under half" if pct < 50 else ""
        if pct < 50:
            findings += 1
        print("%-10s %6d %6d %8d  %3.0f%%%s"
              % (name, len(grp), r, len(grp) - r, pct, flag))
    hi = [e for e in entries if e["hits"] >= 2 and not e["rule"]]
    if hi:
        findings += len(hi)
        print()
        print("REPEAT OFFENDERS WITH NO RULE (these already cost you twice):")
        for e in hi:
            print("  %-52s %d hits" % (e["key"], e["hits"]))
    return findings


def score_at_percentile(sorted_scores, pct):
    """Percentile of the corpus's own distribution. Same method as lesson_dupe.py."""
    if not sorted_scores:
        return 0.0
    idx = min(len(sorted_scores) - 1,
              int(round(pct / 100.0 * (len(sorted_scores) - 1))))
    return sorted_scores[idx]


def duplicate_floor(scores, pct, min_floor, fixed=None, min_pairs=MIN_PAIRS):
    """Return (floor, p_floor, binding_reason).

    WHY THIS IS NOT A CONSTANT
    --------------------------
    It was 0.72. Measured 2026-08-31 over the real corpus: 3081 unpromoted
    pairs, median 0.2963, p99.5 0.4643, MAX 0.5655. Nothing could ever reach
    0.72, so the section printed "none at or above 0.72" every night and read
    as a clean result. A check that cannot return one of its two answers is
    not a check.

    WHY IT IS NOT A BARE PERCENTILE EITHER
    --------------------------------------
    Swapping the constant for p99.5 alone inverts the same defect: a
    percentile over all pairs is a fixed-COUNT selector, so it flags ~0.5% of
    pairs no matter how unrelated they are - 16 nightly findings on this
    corpus, mostly title-string coincidences across different surfaces. An
    always-on warning trains the reader to skip warnings.

    So BOTH must hold: unusually similar FOR THIS CORPUS (the percentile,
    which self-calibrates as the corpus grows) AND similar enough to be worth
    a human's time at all (min_floor). The floor is the higher of the two.

    Below min_pairs the percentile is NOT trusted: over a handful of pairs
    p99.5 collapses onto the maximum, so it would flag the top pair of any
    corpus by construction. There, min_floor governs alone.
    """
    p_floor = score_at_percentile(scores, pct)
    if fixed is not None:
        return fixed, p_floor, "fixed --similarity"
    if len(scores) < min_pairs:
        return min_floor, p_floor, ("--similarity-min; %d pairs is below the "
                                    "%d needed for a percentile to mean "
                                    "anything" % (len(scores), min_pairs))
    if p_floor >= min_floor:
        return p_floor, p_floor, "p%.1f of this corpus" % pct
    return min_floor, p_floor, "--similarity-min (above p%.1f = %.4f)" % (pct, p_floor)


def do_duplicates(entries, pct=DUP_PCT, min_floor=DUP_MIN, fixed=None):
    section("DUPLICATES - merge candidates (PROPOSAL ONLY, never auto-merged)")
    print("Two entries saying the same thing stay two single-hit lessons and")
    print("rank below a real repeat. Merging them is what makes the count honest.")
    print()
    pairs = []
    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            a, b = entries[i], entries[j]
            if a["promoted"] or b["promoted"]:
                continue
            ra, rb = norm(a["rule"]), norm(b["rule"])
            score = 0.0
            basis = ""
            if ra and rb:
                score = difflib.SequenceMatcher(None, ra, rb).ratio()
                basis = "Rule"
            ta, tb = norm(a["title"]), norm(b["title"])
            tscore = difflib.SequenceMatcher(None, ta, tb).ratio()
            if tscore > score:
                score, basis = tscore, "title"
            pairs.append((score, basis, a, b))

    if not pairs:
        print("highest similarity observed: none - fewer than two unpromoted entries")
        return 0

    scores = sorted(p[0] for p in pairs)
    floor, p_floor, binding = duplicate_floor(scores, pct, min_floor, fixed)

    # PRINTED ON EVERY RUN, on both branches. The unreachable 0.72 survived
    # because the one number that would have exposed it - the highest score
    # actually observed - was never shown next to it.
    print("%d pairs   median %.4f   p95 %.4f   p%.1f %.4f   MAX OBSERVED %.4f"
          % (len(scores), score_at_percentile(scores, 50),
             score_at_percentile(scores, 95), pct, p_floor, scores[-1]))
    print("floor %.4f  (%s)" % (floor, binding))
    if floor > scores[-1]:
        print("WARNING: the floor sits ABOVE every observed score, so this check")
        print("         could not have reported a finding on this run. That is the")
        print("         defect the fixed 0.72 threshold had. Lower the floor or")
        print("         accept that this section is decoration.")
    print()

    hits = [p for p in pairs if p[0] >= floor]
    if not hits:
        print("none at or above %.4f similarity" % floor)
        return 0
    for score, basis, a, b in sorted(hits, reverse=True, key=lambda p: p[0]):
        same = "same surface" if a["surface"] == b["surface"] else \
               "DIFFERENT surfaces (%s / %s)" % (a["surface"], b["surface"])
        print("  %.2f on %-5s  %s" % (score, basis, same))
        print("      %s  [%dh]" % (a["key"], a["hits"]))
        print("      %s  [%dh]" % (b["key"], b["hits"]))
        print("      -> if genuinely the same failure: keep the older key, set")
        print("         Hits to %d, mark the other Promoted-to it."
              % (a["hits"] + b["hits"]))
        print()
    return len(hits)


def do_superseded(entries):
    section("RETIREMENT CANDIDATES - flagged by the entry's OWN shouted marker")
    print("Uppercase markers only. Lowercase prose - 'that turned out wrong' -")
    print("is NOT a marker; matching it flagged half the log and meant nothing.")
    print("Nothing is retired automatically. A human decides whether an entry")
    print("still teaches something even after its claim was corrected.")
    print()
    found = 0
    for e in entries:
        marks = sorted(set(SUPERSEDE_RE.findall(e["body"])))
        if not marks:
            continue
        found += 1
        print("  %-52s %s" % (e["key"], ", ".join(marks)))
    if not found:
        print("none")

    merged = [e for e in entries if e["promoted"]]
    print()
    print("MERGED (Promoted-to) - %d entr(ies). This is a HEALTHY state, not a"
          % len(merged))
    print("finding: the lesson was folded into another key and kept as evidence.")
    print("Listed so the count is visible, not counted as work to do.")

    live_fixed = [e for e in entries if e["fixed"] and e["rule"]]
    if live_fixed:
        print()
        print("FIXED BUT STILL CARRYING A LIVE RULE - decide one way or the other:")
        for e in live_fixed:
            found += 1
            print("  %s" % e["key"])
            print("      The defect is fixed, but the Rule still loads every")
            print("      session. Keep it if the discipline still applies; retire")
            print("      it if it now only describes history.")
    return found


# Relative time anchors that become UNRECOVERABLE once the session ends.
# Deliberately NARROW. The first draft of the retirement detector matched
# case-insensitively and flagged 40 of 87 entries; the same trap applies here.
# Measured on the real corpus 2026-08-30: a broad pattern hit 43 times, but 40
# of those were durable usages -
#   "now"          = "in the current version" (structural, not temporal)
#   "earlier"      = "earlier in the file"
#   "this session" = mostly inside QUOTED advice about what to say
# Only 3 were genuine. So this matches an anchor that names a DAY and cannot be
# resolved later. Every entry carries a Date field, which is exactly what the
# fix uses: "today" -> that entry's own date.
RELATIVE_DATE_RE = re.compile(
    r"\b(today|yesterday|tomorrow|last (?:night|week|month)|"
    r"a (?:few|couple of) (?:days|weeks) ago|(?:this|next) week)\b", re.I)


def do_relative_dates(entries):
    section("RELATIVE DATES - anchors that stop meaning anything")
    print("A relative anchor is readable the day it is written and ambiguous")
    print("forever after. Each entry carries a Date field, so the fix is")
    print("deterministic: replace the phrase with that entry's own date.")
    print()
    print("NOT flagged, deliberately: 'now' (means 'in the current version'),")
    print("'earlier' (means 'earlier in the file') and 'this session' (mostly")
    print("appears inside quoted advice). A broad pattern hit 43 times on this")
    print("corpus and 40 were durable usages - that is a warning nobody reads.")
    print()
    found = 0
    for e in entries:
        for m in RELATIVE_DATE_RE.finditer(e["body"]):
            found += 1
            s = max(0, m.start() - 55)
            snippet = " ".join(e["body"][s:m.end() + 45].split())
            print("  %s  (Date: %s)" % (e["key"], e["date"] or "MISSING"))
            print("      '%s' in: ...%s..." % (m.group(0), snippet))
            if e["date"]:
                print("      -> resolve to %s" % e["date"])
            else:
                print("      -> NO Date field, so this cannot be resolved at all")
    if not found:
        print("none")
    return found


def do_open(entries):
    section("STILL OPEN - work recorded but not finished")
    found = 0
    for e in entries:
        if e["still_open"]:
            found += 1
            print("  %s" % e["key"])
            print("      %s" % e["still_open"][:160])
    if not found:
        print("none")
    return found


def do_pointers(memory_dir):
    section("POINTERS - deep memory files vs the index")
    if not memory_dir or not os.path.isdir(memory_dir):
        print("memory dir not supplied or not readable - skipped")
        return 0
    files = [f for f in os.listdir(memory_dir)
             if f.endswith(".md") and not f.endswith(".bak")
             and f != "MEMORY-INDEX.md"]
    idx_path = os.path.join(memory_dir, "MEMORY-INDEX.md")
    findings = 0
    if not os.path.exists(idx_path):
        print("MEMORY-INDEX.md missing - every deep file is unreachable by index")
        return 1
    idx = read(idx_path)
    for f in sorted(files):
        stem = f[:-3]
        if stem not in idx:
            findings += 1
            print("  NOT IN INDEX: %s" % f)
    for m in re.finditer(r"([a-z0-9][a-z0-9-]{4,})\.md", idx):
        name = m.group(1) + ".md"
        if name not in files and name != "MEMORY-INDEX.md":
            findings += 1
            print("  INDEX POINTS AT A MISSING FILE: %s" % name)
    stale = [f for f in os.listdir(memory_dir) if ".bak" in f or ".pre-" in f]
    if stale:
        print()
        print("  backup copies present (git already versions these):")
        for f in sorted(stale):
            print("    %s" % f)
    if not findings:
        print("index and files agree")
    return findings


# A JUDGEMENT, not a measurement. Nobody chose the previous value of 80 either,
# and worse, it was compared against the count of AUTHORED rules in the lessons
# file rather than the always-on block - two numbers that measured the same
# thing until the digest was TIERED on 2026-08-31 and have diverged since.
# Override with --always-on-max. Raise it deliberately; do not silence it.
ALWAYS_ON_MAX = 40


def count_always_on(instructions_text):
    """Rules ACTUALLY in the always-on digest block, counted from the block.

    Returns (count, block_bytes), or (None, 0) when the block is absent.

    Counting authored Rule lines in the lessons file instead is what made the
    old growth check wrong: since the tiering only a subset loads every
    session, and only this number answers "how much is read every time".
    """
    start = instructions_text.find("<!-- LESSON-DIGEST:BEGIN")
    end = instructions_text.find("LESSON-DIGEST:END")
    if start == -1 or end == -1 or end < start:
        return None, 0
    block = instructions_text[start:end]
    n = sum(1 for ln in block.split("\n") if ln.strip().startswith("- "))
    return n, end - start


def do_growth(lessons_path, instructions_path, entries, always_on_max=ALWAYS_ON_MAX):
    section("GROWTH - is the ALWAYS-ON digest still short enough to be read?")

    ls = os.path.getsize(lessons_path)
    authored = sum(1 for e in entries if e["rule"])
    print("cowork-lessons.md      %8d bytes, %d entries, %d authored rule(s)"
          % (ls, len(entries), authored))

    if not (instructions_path and os.path.exists(instructions_path)):
        return 0

    ins = read(instructions_path)
    size = os.path.getsize(instructions_path)
    always_on, share = count_always_on(ins)

    if always_on is None:
        print("copilot-instructions.md %8d bytes - NO DIGEST BLOCK FOUND" % size)
        print("  <- the always-on block is missing entirely. `lesson_gate audit`")
        print("     is the authoritative check for that; this is a pointer to it.")
        return 1

    print("copilot-instructions.md %8d bytes, digest block %d bytes (%.0f%%)"
          % (size, share, 100.0 * share / size if size else 0))
    print("digest is TIERED: %d rule(s) always-on, %d authored in total."
          % (always_on, authored))
    print("The other %d load PER-SURFACE via `lesson_gate preflight`, so they are"
          % max(authored - always_on, 0))
    print("NOT read every session and do not count against this check.")

    if always_on > always_on_max:
        print("  <- %d always-on rules, over the --always-on-max of %d. These ARE"
              % (always_on, always_on_max))
        print("     read every session. Consider promoting the settled ones into")
        print("     copilot-instructions.md prose and retiring them from the block.")
        return 1
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--lessons", default="cowork-lessons.md")
    ap.add_argument("--instructions", default="copilot-instructions.md")
    ap.add_argument("--memory-dir", default="")
    ap.add_argument("--similarity", type=float, default=None,
                    help="fixed duplicate floor 0-1; overrides the percentile. "
                         "Default is unset - the floor is derived from the "
                         "corpus (see --similarity-pct / --similarity-min)")
    ap.add_argument("--similarity-pct", type=float, default=DUP_PCT,
                    help="percentile of the corpus's own pairwise distribution "
                         "used as the floor (default %.1f)" % DUP_PCT)
    ap.add_argument("--similarity-min", type=float, default=DUP_MIN,
                    help="absolute floor the percentile may not fall below "
                         "(default %.2f)" % DUP_MIN)
    ap.add_argument("--always-on-max", type=int, default=ALWAYS_ON_MAX,
                    help="warn when the ALWAYS-ON digest block exceeds this many "
                         "rules (default %d); a judgement, not a measurement" % ALWAYS_ON_MAX)
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any finding was reported")
    a = ap.parse_args()

    entries = load_entries(a.lessons)
    if not entries:
        sys.stderr.write("FATAL: no entries parsed from %s\n" % a.lessons)
        return 2

    print("DREAM ANALYSIS - read-only. Proposes; never edits.")
    print("source: %s (%d entries)" % (os.path.basename(a.lessons), len(entries)))

    n = 0
    n += do_reachability(entries)
    n += do_duplicates(entries, a.similarity_pct, a.similarity_min,
                       a.similarity)
    n += do_superseded(entries)
    n += do_relative_dates(entries)
    n += do_open(entries)
    n += do_pointers(a.memory_dir)
    n += do_growth(a.lessons, a.instructions, entries, a.always_on_max)

    section("SUMMARY")
    print("%d finding(s) to review. Nothing was changed by this script." % n)
    print("Every merge, retirement or deletion needs a human decision.")
    return 1 if (a.strict and n) else 0


if __name__ == "__main__":
    sys.exit(main())
