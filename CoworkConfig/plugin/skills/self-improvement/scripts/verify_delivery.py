#!/usr/bin/env python3
"""
verify_delivery.py - does a DELIVERED lesson actually change behaviour?

skill_lessons.py and plugin_lessons.py prove a rule is PRESENT on a surface.
--check compares bytes. Neither says whether an agent carrying that rule
actually avoids the trap. This is the difference between shipping a rule and
the rule working, and only the second one was ever the point.

THE MEASUREMENT PROBLEM THIS EXISTS TO AVOID
Running a test three times and passing three times proves nothing on its own.
The model may simply have known the answer already, in which case the rule is
occupying context and buying nothing. A pass rate with no control is a number
that looks like a measurement and is not one - the failure recorded in
nightly-constant-reported-as-a-measurement and metrics-that-do-not-measure.

So every verification has FOUR arms, not three:
  - three TEST runs, each in a fresh isolated context that carries the rule
  - one CONTROL run that does not carry it

The control is what makes a pass attributable. Three passes with a failing
control means the rule is doing the work. Three passes with a PASSING control
means the model already knew and the rule is inert on that surface - which is
a finding worth having, because inert bytes on an always-on surface are pure
cost and can be reclaimed.

WHAT THE CONTROL CAN AND CANNOT BE
A true ablation would remove the rule from the surface and re-run. This
harness does NOT do that: the surfaces are live servers and a live skill tree,
and reverting one to run a test is a worse idea than accepting a weaker
control. The control here is a PROXY - a run denied access to the delivering
surface. Recorded as `control_kind: proxy` in the ledger so nobody later reads
it as an ablation. Where a real ablation is run by hand, record `ablation`.

TWO WAYS TO WRITE A CONTROL THAT MEASURES NOTHING
Both were made on this harness's FIRST real run, 2026-09-03, and both produce
a confident verdict from an invalid comparison:

  1. ASKING INSTEAD OF WATCHING. The three test arms measure BEHAVIOUR - does
     the agent avoid the trap while doing a real task. The first control asked
     the model to PREDICT whether the trap existed. A model can predict a
     limitation it would not have avoided in practice, and can avoid one it
     could not articulate. Different quantities. A control must run the SAME
     TASK as the test arms, judged by the SAME pass criterion, and differ only
     in whether the rule is reachable.

  2. LEAKING THE ANSWER IN THE FRAMING. That control asked about "a local
     Workflow Definition Language evaluator". The word `local` is the whole
     clue: the model reasoned that locally reimplemented evaluators usually
     omit the optional accessor, and answered correctly from the framing
     rather than from knowledge of this bridge. A control prompt must not
     contain a word the test arms did not.

So: a control differs from a test arm in ONE variable - reachability of the
rule. If it differs in the question asked or the wording of the setup, the
comparison is void and the verdict must be withheld rather than reported.

WHY THREE
One run cannot distinguish a working rule from a lucky sample. Three is the
smallest number that shows a split, and a split is itself the finding:
1-of-3 and 3-of-3 are different states and must not be averaged into "it
mostly works".

DIVISION OF LABOUR
This script owns everything deterministic: resolving where a rule is actually
delivered, validating the case, adjudicating results against a fixed table,
and appending to the ledger. It NEVER decides whether a run passed - that
judgement comes from the agent running the case and is fed in as JSON. A
script that both ran the test and graded it would be marking its own homework.

  verify_delivery.py plan  --key <pattern-key>       -> the test plan to run
  verify_delivery.py judge --key <key> --results <f> -> verdict + ledger entry
  verify_delivery.py explain                         -> the adjudication table
"""

import argparse, hashlib, json, os, re, sys
from datetime import datetime, timezone

FIELD = lambda name: re.compile(r'^\s*-\s*\*\*' + name + r':\*\*\s*(.+?)\s*$', re.M)

# The adjudication table. Fixed, total, and printed by `explain` so nobody has
# to read the source to know how a verdict was reached.
VERDICTS = {
    ('3', 'fail'): ('EFFECTIVE',
                    'All three carried runs avoided the trap and the control '
                    'did not. The rule is doing the work.'),
    ('3', 'pass'): ('INERT',
                    'All three passed but so did the control - the model '
                    'already knew. The rule buys nothing on this surface and '
                    'its bytes can be reclaimed.'),
    ('2', 'fail'): ('UNRELIABLE', 'Two of three. A split is the finding: the '
                    'rule fires sometimes, which is not the same as working.'),
    ('1', 'fail'): ('UNRELIABLE', 'One of three. Closer to noise than to '
                    'delivery.'),
    ('0', 'fail'): ('INEFFECTIVE',
                    'Delivered and ignored in every run. The rule is present '
                    'on the surface and is not changing behaviour - sharpen '
                    'the wording or move it to a surface that loads earlier.'),
    ('2', 'pass'): ('INVALID', 'Control passed while carried runs did not all '
                    'pass. The case does not isolate the trap.'),
    ('1', 'pass'): ('INVALID', 'Control passed while carried runs did not all '
                    'pass. The case does not isolate the trap.'),
    ('0', 'pass'): ('INVALID', 'The control outperformed every carried run. '
                    'The case is broken, not the rule.'),
}


def parse_lessons(path):
    txt = open(path, encoding='utf-8').read()
    out = {}
    for chunk in re.split(r'\n(?=### )', txt):
        if not chunk.startswith('### '):
            continue

        def f(name):
            m = FIELD(name).search(chunk)
            return m.group(1).strip() if m else None

        key = f('Pattern-Key')
        if key:
            out[key] = {
                'key': key,
                'title': chunk.split('\n')[0][4:].strip(),
                'rule': f('Rule'),
                'delivered_to': f('Delivered-to'),
                'promoted_to': f('Promoted-to'),
            }
    return out


def matches(key, route):
    prefixes = tuple(route.get('prefix') or [])
    if key in set(route.get('exact') or []):
        return True
    return bool(prefixes) and key.startswith(prefixes)


def delivery_sites(key, skill_routes, plugin_routes):
    """Where this rule is ACTUALLY routed. Read from the route files, never
    from the lesson's own Delivered-to line - that line is written by a
    different script and a stale one would silently redirect the test."""
    sites = []
    for name, route in skill_routes.items():
        if name.startswith('_'):
            continue
        if matches(key, route):
            sites.append({'kind': 'skill', 'name': name,
                          'surface': name + '/SKILL.md'})
    for name, route in plugin_routes.items():
        if name.startswith('_'):
            continue
        if matches(key, route):
            sites.append({'kind': 'plugin', 'name': name,
                          'surface': route.get('server'),
                          'tool': route.get('tool')})
    return sites


def case_fingerprint(case, rule_text):
    """Results are only valid for the case AND the rule that produced them.

    Changing a prompt or the pass criterion must invalidate a stored verdict
    rather than silently inheriting it. So must changing the RULE - measured
    2026-09-03, when the first verified rule turned out to be incomplete and
    had to be amended. A fingerprint over the case alone would have let the
    old verdict survive the correction, which is a stored judgement about
    text that no longer exists: exactly enforcer-encodes-the-superseded-rule,
    one tier up.
    """
    payload = json.dumps({
        'prompts': case.get('prompts'),
        'control_prompt': case.get('control_prompt'),
        'pass_criterion': case.get('pass_criterion'),
        'rule': rule_text,
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]


def load(path, what):
    if not os.path.isfile(path):
        print("REFUSED: %s not found: %s" % (what, path))
        sys.exit(2)
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def cmd_plan(args):
    lessons = parse_lessons(args.lessons)
    cases = load(args.cases, 'case file')
    skill_routes = load(args.skill_routes, 'skill routes')
    plugin_routes = load(args.plugin_routes, 'plugin routes')

    if args.key not in lessons:
        print("REFUSED: no lesson entry with Pattern-Key %s" % args.key)
        return 2
    if args.key not in cases:
        print("REFUSED: no verification case authored for %s" % args.key)
        print("         A case cannot be generated from the rule text - it has")
        print("         to name a task where the trap is available and where")
        print("         avoiding it is observable. Author one first.")
        return 2

    lesson = lessons[args.key]
    case = cases[args.key]
    sites = delivery_sites(args.key, skill_routes, plugin_routes)

    if not sites:
        print("REFUSED: %s is not routed to any surface." % args.key)
        print("         Nothing is delivered, so there is nothing to verify.")
        return 2

    prompts = case.get('prompts') or []
    if len(prompts) != 3:
        print("REFUSED: case must define exactly 3 prompts, found %d"
              % len(prompts))
        return 2
    if not case.get('control_prompt'):
        print("REFUSED: case has no control_prompt.")
        print("         Without a control a pass rate is not attributable to")
        print("         the rule and the whole run is decoration.")
        return 2

    print("VERIFICATION PLAN  %s" % args.key)
    print("=" * 68)
    print("title      : %s" % lesson['title'])
    print("rule       : %s" % (lesson['rule'] or '(no Rule field)'))
    print("fingerprint: %s" % case_fingerprint(case, lesson['rule']))
    print()
    print("delivered to %d surface(s):" % len(sites))
    for s in sites:
        if s['kind'] == 'plugin':
            print("  plugin  %-22s %s :: %s" % (s['name'], s['surface'], s['tool']))
        else:
            print("  skill   %-22s %s" % (s['name'], s['surface']))
    print()
    print("pass criterion (judged by the running agent, not by this script):")
    print("  %s" % case['pass_criterion'])
    print()
    print("side effects: %s" % case.get('side_effects', 'UNDECLARED'))
    if case.get('side_effects') != 'none':
        print("  WARNING: a case with side effects will be run three times.")
    print()
    for i, p in enumerate(prompts, 1):
        print("--- TEST %d (isolated context, carries the rule) ---" % i)
        print(p)
        print()
    print("--- CONTROL (must NOT carry the rule) ---")
    print(case['control_prompt'])
    print()
    print("Record each outcome as pass/fail and feed them to `judge`.")
    return 0


def cmd_judge(args):
    cases = load(args.cases, 'case file')
    results = load(args.results, 'results file')
    lessons = parse_lessons(args.lessons)

    if args.key not in cases:
        print("REFUSED: no case for %s" % args.key)
        return 2
    if args.key not in lessons:
        print("REFUSED: no lesson entry for %s - cannot fingerprint the rule"
              % args.key)
        return 2

    case = cases[args.key]
    fp = case_fingerprint(case, lessons[args.key]['rule'])

    if results.get('case_fingerprint') != fp:
        print("REFUSED: results were produced against a different version of")
        print("         the case or the rule. expected %s, got %s"
              % (fp, results.get('case_fingerprint')))
        print("         Re-run the plan. A changed prompt OR a changed rule")
        print("         invalidates a stored verdict - the old result judged")
        print("         text that no longer exists.")
        return 2

    runs = results.get('runs') or []
    if len(runs) != 3:
        print("REFUSED: expected exactly 3 test runs, got %d" % len(runs))
        return 2

    for i, r in enumerate(runs, 1):
        if r.get('passed') not in (True, False):
            print("REFUSED: run %d has no boolean 'passed'" % i)
            return 2
        if not (r.get('evidence') or '').strip():
            print("REFUSED: run %d has no evidence. A verdict with no quoted"
                  % i)
            print("         observation cannot be re-checked later.")
            return 2

    control = results.get('control')
    if not control or control.get('passed') not in (True, False):
        print("REFUSED: no control result. See the module docstring - a run")
        print("         without a control is not a measurement.")
        return 2
    if not (control.get('evidence') or '').strip():
        print("REFUSED: the control has no evidence.")
        return 2

    kind = results.get('control_kind')
    if kind not in ('proxy', 'ablation'):
        print("REFUSED: control_kind must be 'proxy' or 'ablation', got %r"
              % kind)
        return 2

    n_pass = sum(1 for r in runs if r['passed'])
    ctrl = 'pass' if control['passed'] else 'fail'
    verdict, why = VERDICTS[(str(n_pass), ctrl)]

    print("VERDICT  %s" % args.key)
    print("=" * 68)
    print("carried runs : %d of 3 passed" % n_pass)
    print("control      : %s  (%s)" % (ctrl.upper(), kind))
    print()
    print("%s" % verdict)
    print("  %s" % why)
    print()
    for i, r in enumerate(runs, 1):
        print("  run %d  %-4s  %s" % (i, 'PASS' if r['passed'] else 'FAIL',
                                      r['evidence'][:110]))
    print("  ctrl   %-4s  %s" % ('PASS' if control['passed'] else 'FAIL',
                                 control['evidence'][:110]))
    print()

    if verdict == 'INERT':
        print("ACTION: this rule is a removal candidate on the surfaces it is")
        print("        delivered to. It is NOT a candidate for removal from")
        print("        cowork-lessons.md - the corpus is the audit trail and")
        print("        keeps every entry regardless of verdict.")
    elif verdict == 'INVALID':
        print("ACTION: fix the case, not the rule. Nothing is concluded here.")

    entry = {
        'key': args.key,
        'date': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'case_fingerprint': fp,
        'passes': n_pass,
        'control_passed': control['passed'],
        'control_kind': kind,
        'verdict': verdict,
        'runs': [{'passed': r['passed'], 'evidence': r['evidence']} for r in runs],
        'control': {'passed': control['passed'], 'evidence': control['evidence']},
    }

    if args.ledger:
        led = []
        if os.path.isfile(args.ledger):
            with open(args.ledger, encoding='utf-8') as fh:
                led = json.load(fh)
        led = [e for e in led if not (e['key'] == args.key
                                      and e['case_fingerprint'] == fp)]
        led.append(entry)
        if not args.dry_run:
            with open(args.ledger, 'w', encoding='utf-8') as fh:
                json.dump(led, fh, indent=2, ensure_ascii=False)
            print("ledger: %d entries -> %s" % (len(led), args.ledger))
        else:
            print("ledger: DRY RUN, nothing written")

    # INVALID is the only verdict that means the run itself failed. Every other
    # verdict is a real finding, including the unflattering ones.
    return 1 if verdict == 'INVALID' else 0


def cmd_explain(args):
    print("ADJUDICATION TABLE - passes of 3 x control outcome")
    print("=" * 68)
    for (n, ctrl), (verdict, why) in sorted(VERDICTS.items()):
        print("%s of 3, control %-5s -> %-12s %s" % (n, ctrl, verdict, why))
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('plan')
    p.add_argument('--key', required=True)
    p.add_argument('--lessons', required=True)
    p.add_argument('--cases', required=True)
    p.add_argument('--skill-routes', required=True)
    p.add_argument('--plugin-routes', required=True)
    p.set_defaults(fn=cmd_plan)

    j = sub.add_parser('judge')
    j.add_argument('--key', required=True)
    j.add_argument('--cases', required=True)
    j.add_argument('--lessons', required=True)
    j.add_argument('--results', required=True)
    j.add_argument('--ledger')
    j.add_argument('--dry-run', action='store_true')
    j.set_defaults(fn=cmd_judge)

    e = sub.add_parser('explain')
    e.set_defaults(fn=cmd_explain)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == '__main__':
    sys.exit(main())
