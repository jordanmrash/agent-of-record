#!/usr/bin/env python3
"""
plugin_lessons.py - move a lesson from the general log INTO the PLUGIN TOOL
that owns it.

Sibling of skill_lessons.py. Same contract, different surface, and the
difference in surface is the reason it is a separate script rather than a flag.

WHY THIS EXISTS
A tool description is in context for every session where the plugin is
connected, with no skill load required. That is the highest-reach surface in
the system - strictly better than a skill block, which reaches only sessions
that load that skill.

It is also the most expensive. A skill block costs nothing until the skill
loads; a description costs every session forever. So this script REPORTS the
byte cost of every segment it writes and REFUSES a route that exceeds its
declared max_bytes. A budget nobody is shown is a budget nobody keeps.

WHAT IT DOES NOT CLAIM
Splicing prose into a description is DELIVERY, not enforcement. It puts the
rule in front of a model about to call the tool; it cannot stop a caller that
ignores it, and it cannot reach a session that never calls the tool at all.
The 8933 server already states that limit in its own reminderBlock() and it is
worth restating: an ABSENT bridge cannot be taught by a tool description,
because nobody is calling the tool. Those rules belong in the always-on
instructions, not here.

WHY IT REFUSES TO PLACE ITS OWN MARKERS
skill_lessons.py inserts a first block automatically because a markdown file
has an unambiguous insertion point - before the first H2. JavaScript does not.
A description is an arbitrary `+` concatenation and guessing where a generated
segment belongs is how you produce a file that parses but says something you
did not intend. So: markers are placed ONCE, BY HAND, and reviewed. If they
are absent this script reports MARKERS-ABSENT and changes nothing.

SAFETY, same contract as skill_lessons.py / digest_apply.py
  - writes ONLY between the markers
  - refuses if anything outside the markers would change
  - refuses a segment that exceeds the route's declared max_bytes
  - re-reads from disk after writing, so a partial write cannot report success
  - --check exits 1 on drift and writes nothing
  - exit 2 means it REFUSED rather than ran - never confuse that with a finding

WHAT IT DOES NOT VERIFY
It does NOT parse the resulting JavaScript. Escaping is handled in js_string()
and covered by the selftest, which runs `node --check` on real output - but the
applier itself has no node dependency and makes no syntax claim. Run
plugin_lessons_selftest.py after changing js_string() or render().

Worth knowing why that suite has a dedicated escaping assertion rather than
leaning on the parse check: measured 2026-09-03, removing the backslash escape
produced 'C:\\Cowork\\CommandJobs', which is VALID JavaScript that silently
evaluates to 'C:CoworkCommandJobs'. node --check passed. Only the explicit
assertion caught it.
"""

import argparse, json, os, re, sys

START_RE = re.compile(r'/\*\s*PLUGIN-LESSONS:start\s+(\S+)\s*\*/')
END_TOK  = '/* PLUGIN-LESSONS:end */'

FIELD = lambda name: re.compile(r'^\s*-\s*\*\*' + name + r':\*\*\s*(.+?)\s*$', re.M)

WRAP = 84


def parse_lessons(path):
    """Identical field shape to skill_lessons.py. One corpus, one parser."""
    txt = open(path, encoding='utf-8').read()
    entries = []
    for chunk in re.split(r'\n(?=### )', txt):
        if not chunk.startswith('### '):
            continue

        def f(name):
            m = FIELD(name).search(chunk)
            return m.group(1).strip() if m else None

        key = f('Pattern-Key')
        if not key:
            continue
        entries.append({
            'key': key,
            'rule': f('Rule'),
            'hits': f('Hits'),
        })
    return entries


def select(entries, route):
    prefixes = tuple(route.get('prefix', []))
    exact = set(route.get('exact', []))
    hit = [e for e in entries
           if e['key'] in exact or (prefixes and e['key'].startswith(prefixes))]

    # An entry with no authored Rule cannot be rendered into a description
    # without inventing prose. Skip it here and let the companion skill carry
    # the pointer - a description is the wrong place for "go read the entry".
    hit = [e for e in hit if e['rule']]

    def hits_of(e):
        m = re.match(r'\s*(\d+)', str(e['hits'] or '1'))
        return int(m.group(1)) if m else 1

    # Most-repeated first: if the budget truncates, it truncates the rules that
    # have bitten least.
    hit.sort(key=lambda e: (-hits_of(e), e['key']))
    return hit


def js_string(s):
    """Escape a rule into a single-quoted JS string literal body."""
    s = s.replace('\\', '\\\\').replace("'", "\\'")
    s = s.replace('\r', ' ').replace('\n', ' ')
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def wrap_words(text, width):
    out, line = [], ''
    for w in text.split(' '):
        if line and len(line) + 1 + len(w) > width:
            out.append(line)
            line = w
        else:
            line = (line + ' ' + w).strip()
    if line:
        out.append(line)
    return out


def render(route, rows, indent='    '):
    """A self-contained JS concatenation segment, every line beginning with +.

    Leading `+` rather than trailing means the segment can sit anywhere after
    the first string literal in the expression without the line above it
    needing to know the segment exists.
    """
    cap = int(route.get('max_rules', 6))
    kept = rows[:cap]

    lines = [indent + '/* PLUGIN-LESSONS:start ' + route['tool'] + ' */']

    if not kept:
        lines.append(indent + "+ ''")
        lines.append(indent + END_TOK)
        return '\n'.join(lines), 0, kept

    body = ('OPERATING RULES, each learned from a real failure and regenerated '
            'from cowork-lessons.md - do not hand-edit: ')
    for r in kept:
        rule = r['rule'].strip()
        if not rule.endswith('.'):
            rule += '.'
        body += rule + ' '
    body = body.strip()

    for seg in wrap_words(js_string(body), WRAP):
        lines.append(indent + "+ '" + seg + " '")

    lines.append(indent + END_TOK)
    return '\n'.join(lines), len(body), kept


def find_block(txt, tool):
    """Locate the marker pair for one tool. Returns (start_idx, end_idx)."""
    for m in START_RE.finditer(txt):
        if m.group(1) != tool:
            continue
        line_start = txt.rfind('\n', 0, m.start()) + 1
        end = txt.find(END_TOK, m.end())
        if end == -1:
            return None
        end_line_end = txt.find('\n', end)
        if end_line_end == -1:
            end_line_end = len(txt)
        return (line_start, end_line_end)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lessons', required=True)
    ap.add_argument('--servers-dir', required=True,
                    help='COPILOT_COWORK/Startup')
    ap.add_argument('--routes', required=True)
    ap.add_argument('--check', action='store_true',
                    help='report only, write nothing')
    ap.add_argument('--only', help='one plugin name')
    args = ap.parse_args()

    entries = parse_lessons(args.lessons)
    routes = {k: v for k, v in json.load(open(args.routes)).items()
              if not k.startswith('_')}

    print("lessons parsed : %d" % len(entries))
    print("plugins routed : %d" % len(routes))
    print()

    routed_keys = set()
    changed = 0
    refused = False

    for plugin in sorted(routes):
        route = routes[plugin]
        if args.only and plugin != args.only:
            continue

        src = os.path.join(args.servers_dir, *route['server'].split('/'))
        if not os.path.isfile(src):
            print("  SKIP  %-22s server not found: %s" % (plugin, route['server']))
            continue

        txt = open(src, encoding='utf-8').read()
        span = find_block(txt, route['tool'])
        if span is None:
            print("  MARKERS-ABSENT  %-14s place the pair by hand inside the" % plugin)
            print("        description for tool '%s', then re-run." % route['tool'])
            refused = True
            continue

        rows = select(entries, route)
        routed_keys.update(r['key'] for r in rows)
        block, nbytes, kept = render(route, rows)

        budget = int(route.get('max_bytes', 1200))
        if nbytes > budget:
            print("  FAIL  %-22s segment %d bytes over the %d budget - refusing"
                  % (plugin, nbytes, budget))
            print("        Raise max_bytes deliberately or route a rule to the skill.")
            refused = True
            continue

        new = txt[:span[0]] + block + txt[span[1]:]

        outside_old = txt[:span[0]] + txt[span[1]:]
        outside_new = new[:span[0]] + new[span[0] + len(block):]
        if outside_old != outside_new:
            print("  FAIL  %-22s content outside the markers would change - refusing"
                  % plugin)
            return 2

        pct = (100.0 * nbytes / budget) if budget else 0
        if new == txt:
            print("  ok    %-22s %d rule(s), %d bytes (%.0f%% of budget), current"
                  % (plugin, len(kept), nbytes, pct))
        else:
            print("  UPD   %-22s %d rule(s), %d bytes (%.0f%% of budget)"
                  % (plugin, len(kept), nbytes, pct))
            for r in kept:
                print("          - %s" % r['key'])
            changed += 1
            if not args.check:
                open(src, 'w', encoding='utf-8', newline='').write(new)
                back = open(src, encoding='utf-8').read()
                if find_block(back, route['tool']) is None:
                    print("  FAIL  %s: markers absent after write" % plugin)
                    return 2

    print()
    print("routed to at least one tool : %d" % len(routed_keys))

    if refused:
        print("\nREFUSED: at least one route could not be processed")
        return 2
    if args.check and changed:
        print("\nSTALE: %d plugin(s) would change" % changed)
        return 1
    print("\n%s: %d" % ('would update' if args.check else 'updated', changed))
    return 0


if __name__ == '__main__':
    sys.exit(main())
