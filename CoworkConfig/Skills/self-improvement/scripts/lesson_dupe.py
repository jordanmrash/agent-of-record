#!/usr/bin/env python3
"""
lesson_dupe.py - catch a "new" lesson that is really another hit on an old one.

WHY
---
The tiered digest ranks by hit count. A repeat logged as a fresh key with
Hits: 1 understates recurrence, so the rules that recur most get filtered OUT
of always-on - the exact inversion of what the ranking is for. On 2026-08-31
that happened once in five entries, which makes the hit count an unreliable
input to a decision that now depends on it.

Nothing here relies on remembering to be careful. It measures.

METHOD
------
TF-IDF cosine over each entry's title + Rule + Failed + Why + Worked, stdlib
only - no embeddings, no network, no install. Rare words carry more weight
than common ones, so "quarantine" separates entries and "the" does not.

The flag threshold is NOT a magic constant. It is a percentile of the corpus's
own pairwise-similarity distribution, so it self-calibrates as the corpus
grows. --pair prints a score and its percentile so any claim here is checkable.

A `See also` reference does NOT suppress a finding. In the case this was built
for, the duplicate DID cite the original in See also - citing a neighbour is
evidence the relationship was noticed and then filed as new anyway.

To dispose of a true finding, add to the entry:
    - **Distinct-from:** <other-key> - <why this is a different mechanism>
That is an auditable sentence, not a silent override.

NOTE ON PARSING: this reads fields through lesson_check.parse, NOT
lesson_brief.load. load() returns flat keys and exposes no Failed/Why, so
building vectors from it would have silently produced title-only similarity.

MEASURED LIMIT - READ THIS BEFORE TRUSTING A CLEAN RESULT
---------------------------------------------------------
Calibrated 2026-08-31 against the case it was built for. It MISSED it.

    artifact-deadness-needs-consumer-grep
    agent-recommends-edit-without-reading-file
    score 0.0405, percentile 57.70 - below the p99.5 floor, and barely
    above the corpus MEDIAN of 0.0355. It did not even reach its own top-3.

Why: the two entries share almost no vocabulary. One says "deadness is a
property of the reference graph", the other says "read the file before
proposing a change to it". The shared MECHANISM - acting on something
without reading the thing that would have contradicted you - is nowhere in
the words. TF-IDF finds LEXICAL twins, not MECHANISTIC ones.

So this tool is an AUDITOR, not a guarantee. A CLEAN result means "no
vocabulary twin found", never "this is genuinely a new lesson". Do not wire
it into a close as a blocking gate on that basis; it would pass the case it
was meant to stop while failing on same-surface neighbours, which trains the
reader to ignore it.

What it IS good at: same-surface lexical clusters that are genuine merge
candidates - onedrive-read-mount-locally/onedrive-user-surface-not-live at
0.4241, memory-tiering-pointer-vs-deep/memory-two-stores-drift at 0.3402.
Use --audit for that.

The real fix is a closed-vocabulary `Mode:` field naming the failure
mechanism, so collision detection is an exact match rather than a guess.

Exit codes:
    0  no finding (or --audit / --pair, which only report)
    1  a recent entry looks like a repeat and is not dispositioned
    2  input could not be read
"""

import argparse
import math
import os
import re
import sys
from collections import Counter
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from lesson_check import parse
except ImportError:
    sys.stderr.write("FATAL: lesson_check.py must sit beside lesson_dupe.py\n")
    sys.exit(2)

STOP = set("""a an the and or but if then than that this these those of to in on at by for with
from as is are was were be been being it its into over under about after before during not no
does do did done can could should would may might must will shall have has had having you he
she they we them him her his their our your my me us so such only just also very more most less
when while where which who whom what how why all any both each few other some own same too
one two three first second next last new old because between against through was not""".split())

WORD = re.compile(r"[a-z][a-z0-9_\-]{2,}")
WEIGHTED_FIELDS = ("Rule", "Failed", "Why", "Worked")


def norm(text):
    text = text.lower()
    text = re.sub(r"`+", " ", text)
    text = re.sub(r"\*+", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    return [w for w in WORD.findall(text) if w not in STOP]


def entry_text(e):
    parts = [e.get("title", "")]
    f = e.get("fields", {})
    for k in WEIGHTED_FIELDS:
        if f.get(k):
            parts.append(f[k])
    return " ".join(parts)


def build_vectors(entries):
    docs = [Counter(norm(entry_text(e))) for e in entries]
    n = len(docs)
    df = Counter()
    for d in docs:
        for t in d:
            df[t] += 1
    vecs = []
    for d in docs:
        v = {}
        for t, c in d.items():
            idf = math.log((n + 1) / (df[t] + 1)) + 1.0
            v[t] = (1.0 + math.log(c)) * idf
        mag = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append({t: x / mag for t, x in v.items()})
    return vecs


def cosine(a, b):
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(t, 0.0) for t, x in a.items())


def all_pairs(vecs):
    return [(cosine(vecs[i], vecs[j]), i, j)
            for i in range(len(vecs)) for j in range(i + 1, len(vecs))]


def percentile_of(sorted_scores, value):
    lo, hi = 0, len(sorted_scores)
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_scores[mid] < value:
            lo = mid + 1
        else:
            hi = mid
    return 100.0 * lo / max(1, len(sorted_scores))


def score_at_percentile(sorted_scores, pct):
    if not sorted_scores:
        return 1.0
    idx = min(len(sorted_scores) - 1,
              int(round(pct / 100.0 * (len(sorted_scores) - 1))))
    return sorted_scores[idx]


def neighbours(vecs, idx, k):
    scored = sorted(((cosine(vecs[idx], vecs[j]), j)
                     for j in range(len(vecs)) if j != idx), reverse=True)
    return scored[:k]


def parse_date(s):
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s or "")
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def load_entries(path):
    with open(path, encoding="utf-8") as fh:
        _, raw = parse(fh.read())
    out = []
    for e in raw:
        key = e["fields"].get("Pattern-Key")
        if key:
            e["key"] = key
            out.append(e)
    return out


DISTINCT_RE = re.compile(r"^- \*\*Distinct-from:\*\*\s?(.*)$", re.M)


def distinct_from(e):
    """EVERY Distinct-from line on the entry, joined into one string.

    `lesson_check.parse` builds `fields` with setdefault, so an entry carrying
    two Distinct-from lines exposes only the FIRST one through `fields`. The
    gate then blocked on a neighbour the SECOND line had already addressed,
    and its message named the neighbour without ever saying that the line
    disposing of it had not been read. Read the body, which holds them all.
    """
    return " ".join(m.group(1).strip()
                    for m in DISTINCT_RE.finditer(e.get("body", "")))


def names_key(df, key):
    """True when `df` names `key` as a whole token.

    A bare substring test let a longer key satisfy a shorter one that is its
    prefix: a line naming bridge-drops-are-tunnel-not-bridge would silently
    dispose of bridge-drops as well. Keys are [a-z0-9-], so the boundary is
    "not another key character on either side".
    """
    if not key:
        return False
    return re.search(r"(?<![a-z0-9-])%s(?![a-z0-9-])" % re.escape(key),
                     df, re.I) is not None


def disposed(e, other_key):
    return names_key(distinct_from(e), other_key)


def read_known(path):
    """None means the snapshot does not exist yet - caller should bootstrap."""
    try:
        with open(path, encoding="utf-8") as fh:
            return {l.strip() for l in fh if l.strip() and not l.startswith("#")}
    except OSError:
        return None


def write_known(path, keys):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# Lesson keys present at the last successful close.\n")
        fh.write("# Managed by lesson_dupe.py --gate. Do not hand-edit to skip a block:\n")
        fh.write("# add a Distinct-from line to the entry instead, which leaves a record.\n")
        for k in sorted(keys):
            fh.write(k + "\n")


def run_gate(entries, keys, vecs, scores, floor, known_path):
    """Force a written disposition for every key that did not exist last close.

    This is the block-then-require-an-answer pattern. The detector is NOT
    deciding whether an entry is a duplicate - it is measured at doing that
    badly. It only has to make the question unavoidable and put the nearest
    candidates on screen while it is asked.
    """
    keyset = set(keys)
    known = read_known(known_path)
    if known is None:
        write_known(known_path, keyset)
        print("bootstrapped: %d existing key(s) recorded as known." % len(keyset))
        print("Disposition is required for every key added after this point.")
        print("LESSON_DUPE: CLEAN")
        return 0

    new = [i for i, k in enumerate(keys) if k not in known]
    if not new:
        write_known(known_path, keyset)
        print("no new lesson keys since the last close.")
        print("LESSON_DUPE: CLEAN")
        return 0

    problems = 0
    for i in new:
        print("NEW KEY  %s" % keys[i])
        nb = neighbours(vecs, i, 3)
        for s, j in nb:
            print("   %.4f p%.2f  %s" % (s, percentile_of(scores, s), keys[j]))
        df = distinct_from(entries[i]).strip()
        if not df:
            print("   BLOCKED: no Distinct-from line. Name the existing lesson this is")
            print("            NOT another hit on, and say why the mechanism differs.")
            problems += 1
        else:
            named = sorted(k for k in keyset if k != keys[i] and names_key(df, k))
            if not named:
                print("   BLOCKED: Distinct-from names no key that exists in the corpus.")
                print("            Given: %s" % df[:110])
                problems += 1
            else:
                print("   dispositioned against: %s" % ", ".join(named[:3]))
            unaddressed = [keys[j] for s, j in nb
                           if s >= floor and not names_key(df, keys[j])]
            if unaddressed:
                print("   BLOCKED: above-floor neighbour(s) not addressed: %s"
                      % ", ".join(unaddressed))
                problems += 1
        print()

    if problems:
        print("%d new key(s) are not dispositioned." % problems)
        print("Either increment Hits on the existing lesson instead of adding a key,")
        print("or add to the entry:")
        print("  - **Distinct-from:** <existing-key> - <why the mechanism differs>")
        print("The snapshot is NOT advanced, so this blocks again until it is answered.")
        print("LESSON_DUPE: FAIL")
        return 1

    write_known(known_path, keyset)
    print("all new key(s) dispositioned.")
    print("LESSON_DUPE: CLEAN")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Detect a repeat logged as a new key.")
    ap.add_argument("lessons")
    ap.add_argument("--since-days", type=int, default=1)
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--pair", nargs=2, metavar=("KEY_A", "KEY_B"))
    ap.add_argument("--pct", type=float, default=99.5)
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--gate", action="store_true",
                    help="block until every NEW key carries a Distinct-from line")
    ap.add_argument("--known",
                    help="file of keys present at the last successful close")
    a = ap.parse_args()

    if not os.path.isfile(a.lessons):
        sys.stderr.write("FATAL: lessons file not found: %s\n" % a.lessons)
        return 2

    entries = load_entries(a.lessons)
    if len(entries) < 3:
        sys.stderr.write("FATAL: too few entries to calibrate\n")
        return 2

    vecs = build_vectors(entries)
    keys = [e["key"] for e in entries]
    pairs = all_pairs(vecs)
    scores = sorted(s for s, _, _ in pairs)
    floor = score_at_percentile(scores, a.pct)

    print("corpus: %d entries, %d pairs" % (len(entries), len(pairs)))
    print("floor p%.1f = %.4f   (median %.4f, p95 %.4f, max %.4f)"
          % (a.pct, floor, score_at_percentile(scores, 50),
             score_at_percentile(scores, 95), scores[-1]))
    print()

    if a.pair:
        idx = {k: i for i, k in enumerate(keys)}
        missing = [k for k in a.pair if k not in idx]
        if missing:
            sys.stderr.write("FATAL: key(s) not found: %s\n" % ", ".join(missing))
            return 2
        s = cosine(vecs[idx[a.pair[0]]], vecs[idx[a.pair[1]]])
        print("PAIR  %s\n      %s" % (a.pair[0], a.pair[1]))
        print("score %.4f   percentile %.2f   %s the p%.1f floor"
              % (s, percentile_of(scores, s),
                 "ABOVE" if s >= floor else "BELOW", a.pct))
        return 0

    if a.gate:
        if not a.known:
            sys.stderr.write("FATAL: --gate requires --known <snapshot file>\n")
            return 2
        return run_gate(entries, keys, vecs, scores, floor, a.known)

    if a.audit:
        pairs.sort(reverse=True)
        print("top %d most similar pairs:" % a.top)
        for s, i, j in pairs[:a.top]:
            print("  %s %.4f  %s" % ("FLAG" if s >= floor else "    ", s, keys[i]))
            print("              %s" % keys[j])
        return 0

    cutoff = date.today() - timedelta(days=a.since_days)
    recent = [i for i, e in enumerate(entries)
              if (parse_date(e["fields"].get("Date", "")) or date.min) >= cutoff]
    if not recent:
        print("no entries dated on or after %s - nothing to check" % cutoff)
        print("LESSON_DUPE: CLEAN")
        return 0

    findings = 0
    for i in recent:
        print("NEW  %s" % keys[i])
        for s, j in neighbours(vecs, i, 3):
            flag = ""
            if s >= floor:
                if disposed(entries[i], keys[j]):
                    flag = "  (dispositioned via Distinct-from)"
                else:
                    flag = "  <== LOOKS LIKE A REPEAT"
                    findings += 1
            print("     %.4f p%.2f  %s%s"
                  % (s, percentile_of(scores, s), keys[j], flag))
        print()

    if findings:
        print("%d recent entr(ies) resemble an existing lesson above the p%.1f floor."
              % (findings, a.pct))
        print("Either increment Hits on the existing entry instead, or add")
        print("  - **Distinct-from:** <key> - <why the mechanism differs>")
        print("LESSON_DUPE: FAIL")
        return 1

    print("LESSON_DUPE: CLEAN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
