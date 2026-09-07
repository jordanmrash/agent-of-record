#!/usr/bin/env python3
"""
skill_lessons_backlink.py - write the return pointer into cowork-lessons.md.

skill_lessons.py pushes rules OUT to the skills that own them. Without a
pointer back, the lessons file cannot tell you where a rule now ships, and a
future session editing an entry has no idea a skill carries a copy.

Adds `- **Delivered-to:** <skill>, <skill>` under an entry's Rule line.

Delivered-to is DELIBERATELY a different field from Promoted-to:
  Promoted-to  = the rule was moved to a surface that ALWAYS loads
                 (copilot-instructions.md, the digest, an enforcing check)
  Delivered-to = the rule is ALSO rendered inside these skills, and reaches a
                 session only when one of them loads

Conflating them would let a skill-scoped delivery be mistaken for unconditional
coverage, which is exactly the failure recorded in
digest-enforced-demotion-outruns-the-enforcer (2026-09-01).

NON-DESTRUCTIVE BY CONSTRUCTION
  - never deletes an entry, a field, or a Promoted-to line
  - only inserts or replaces the single Delivered-to line it owns
  - re-parses after writing and REFUSES if the entry count changed
  - --check writes nothing
"""

import argparse, json, re, sys

FIELD = lambda n: re.compile(r'^\s*-\s*\*\*' + n + r':\*\*\s*(.+?)\s*$', re.M)
DELIV = re.compile(r'^\s*-\s*\*\*Delivered-to:\*\*.*$\n?', re.M)


def entry_keys(txt):
    keys = []
    for chunk in re.split(r'\n(?=### )', txt):
        if not chunk.startswith('### '):
            continue
        m = FIELD('Pattern-Key').search(chunk)
        if m:
            keys.append(m.group(1).strip())
    return keys


def build_map(routes, keys):
    out = {}
    for skill, r in routes.items():
        if skill.startswith('_'):
            continue
        prefixes = tuple(r.get('prefix', []))
        exact = set(r.get('exact', []))
        for k in keys:
            if k in exact or (prefixes and k.startswith(prefixes)):
                out.setdefault(k, []).append(skill)
    return {k: sorted(v) for k, v in out.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lessons', required=True)
    ap.add_argument('--routes', required=True)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    txt = open(args.lessons, encoding='utf-8').read()
    before_keys = entry_keys(txt)
    routes = json.load(open(args.routes))
    mapping = build_map(routes, before_keys)

    print("entries        : %d" % len(before_keys))
    print("entries routed : %d" % len(mapping))
    print()

    chunks = re.split(r'(?=\n### )', txt)
    added = updated = 0

    for i, chunk in enumerate(chunks):
        m = FIELD('Pattern-Key').search(chunk)
        if not m:
            continue
        key = m.group(1).strip()
        if key not in mapping:
            # not routed - remove any stale Delivered-to we previously wrote
            if DELIV.search(chunk):
                chunks[i] = DELIV.sub('', chunk)
                updated += 1
            continue

        want = "- **Delivered-to:** " + ", ".join(mapping[key])
        existing = DELIV.search(chunk)
        if existing:
            if existing.group(0).strip() == want:
                continue
            chunks[i] = DELIV.sub(want + "\n", chunk, count=1)
            updated += 1
            continue

        # Insert after Rule if present, else after Pattern-Key.
        anchor = FIELD('Rule').search(chunk) or FIELD('Pattern-Key').search(chunk)
        end = anchor.end()
        nl = chunk.find('\n', end)
        if nl < 0:
            nl = len(chunk)
        chunks[i] = chunk[:nl + 1] + want + "\n" + chunk[nl + 1:]
        added += 1

    new = "".join(chunks)
    after_keys = entry_keys(new)

    if after_keys != before_keys:
        print("FAIL entry list changed (%d -> %d) - refusing to write"
              % (len(before_keys), len(after_keys)))
        return 2

    # Every original line must survive except the Delivered-to lines we own.
    def skeleton(s):
        return DELIV.sub('', s)
    if skeleton(new) != skeleton(txt):
        print("FAIL content outside the Delivered-to lines would change - refusing")
        return 2

    print("would add    : %d" % added)
    print("would update : %d" % updated)

    if args.check:
        print("\ncheck only, nothing written")
        return 1 if (added or updated) else 0

    if added or updated:
        open(args.lessons, 'w', encoding='utf-8', newline='').write(new)
        back = open(args.lessons, encoding='utf-8').read()
        if entry_keys(back) != before_keys:
            print("FAIL re-read after write shows a different entry list")
            return 2
        print("\nwritten and re-verified: %d entries intact" % len(before_keys))
    else:
        print("\nalready current")
    return 0


if __name__ == '__main__':
    sys.exit(main())
