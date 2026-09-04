#!/usr/bin/env python3
"""
verify_delivery_selftest.py - break the harness before trusting a verdict.

The positive control runs FIRST: a harness that refuses everything would pass
a suite made only of negatives, and every refusal below would mean nothing.

The verdict table is exercised at every cell that matters, because the whole
value of this harness is that 3-of-3-with-a-passing-control is reported as
INERT rather than as success. A suite that only checked the happy path would
let that distinction rot silently.

Mutation-verified 2026-09-03: flipping the ('3','pass') cell from INERT to
EFFECTIVE drops this suite from 29 to 27, caught by the INERT cases. A suite
that survives that mutation is not testing the thing that matters.
"""

import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DRIVER = os.path.join(HERE, 'verify_delivery.py')

RESULTS = []


def record(name, passed, detail=''):
    RESULTS.append((name, passed, detail))


LESSONS = """# Lessons

### evaluate_expression cannot parse the ?[] operator
- **Pattern-Key:** bridge-8934-evaluate-rejects-safe-navigation
- **Date:** 2026-09-03
- **Trigger:** failure
- **Rule:** The evaluator does not implement the optional-property accessor.
- **Hits:** 1

### Something routed nowhere
- **Pattern-Key:** orphan-key-routed-nowhere
- **Date:** 2026-09-03
- **Rule:** This rule is delivered to no surface at all.
- **Hits:** 1
"""

CASES = {
    "bridge-8934-evaluate-rejects-safe-navigation": {
        "side_effects": "none",
        "prompts": ["p one", "p two", "p three"],
        "pass_criterion": "agent avoids ?[]",
        "control_prompt": "control question"
    },
    "orphan-key-routed-nowhere": {
        "side_effects": "none",
        "prompts": ["a", "b", "c"],
        "pass_criterion": "x",
        "control_prompt": "y"
    },
    "case-with-two-prompts": {
        "side_effects": "none",
        "prompts": ["a", "b"],
        "pass_criterion": "x",
        "control_prompt": "y"
    },
    "case-with-no-control": {
        "side_effects": "none",
        "prompts": ["a", "b", "c"],
        "pass_criterion": "x"
    }
}

SKILL_ROUTES = {"_c": ["x"], "command-bridge": {"prefix": ["bridge-8933-"], "exact": []}}
PLUGIN_ROUTES = {
    "_c": ["x"],
    "power-automate-8934": {
        "server": "FlowBridge/flow-mcp-server.js",
        "tool": "evaluate_expression",
        "prefix": ["bridge-8934-evaluate-"],
        "exact": []
    }
}


def build(tmp):
    paths = {}
    paths['lessons'] = os.path.join(tmp, 'lessons.md')
    open(paths['lessons'], 'w', encoding='utf-8').write(LESSONS)
    for name, obj in (('cases', CASES), ('skill', SKILL_ROUTES),
                      ('plugin', PLUGIN_ROUTES)):
        p = os.path.join(tmp, name + '.json')
        json.dump(obj, open(p, 'w', encoding='utf-8'))
        paths[name] = p
    return paths


def plan(tmp, key):
    p = build(tmp)
    return subprocess.run(
        [sys.executable, DRIVER, 'plan', '--key', key,
         '--lessons', p['lessons'], '--cases', p['cases'],
         '--skill-routes', p['skill'], '--plugin-routes', p['plugin']],
        capture_output=True, text=True)


def judge(tmp, key, results_obj, ledger=None):
    p = build(tmp)
    rp = os.path.join(tmp, 'results.json')
    json.dump(results_obj, open(rp, 'w', encoding='utf-8'))
    cmd = [sys.executable, DRIVER, 'judge', '--key', key,
           '--cases', p['cases'], '--lessons', p['lessons'], '--results', rp]
    if ledger:
        cmd += ['--ledger', ledger]
    return subprocess.run(cmd, capture_output=True, text=True)


def fingerprint(tmp, key):
    r = plan(tmp, key)
    for line in r.stdout.split('\n'):
        if line.startswith('fingerprint:'):
            return line.split(':', 1)[1].strip()
    return None


def mk(passes, control_passed, fp, kind='proxy'):
    return {
        'case_fingerprint': fp,
        'control_kind': kind,
        'runs': [{'passed': i < passes, 'evidence': 'observed run %d' % i}
                 for i in range(3)],
        'control': {'passed': control_passed, 'evidence': 'observed control'}
    }


# ---------------------------------------------------------------- positive --

def case_positive_plan():
    with tempfile.TemporaryDirectory() as tmp:
        r = plan(tmp, 'bridge-8934-evaluate-rejects-safe-navigation')
        record("POSITIVE plan exits 0 for a routed key with a case",
               r.returncode == 0, "exit %d / %s" % (r.returncode, r.stdout[-160:]))
        record("POSITIVE plan resolves the real delivery site",
               'power-automate-8934' in r.stdout and 'evaluate_expression' in r.stdout,
               r.stdout[:300])
        record("POSITIVE plan prints all three prompts",
               all(s in r.stdout for s in ('p one', 'p two', 'p three')))
        record("POSITIVE plan prints the control",
               'control question' in r.stdout)


def case_positive_judge():
    with tempfile.TemporaryDirectory() as tmp:
        fp = fingerprint(tmp, 'bridge-8934-evaluate-rejects-safe-navigation')
        r = judge(tmp, 'bridge-8934-evaluate-rejects-safe-navigation',
                  mk(3, False, fp))
        record("POSITIVE 3 passes + failing control = EFFECTIVE",
               r.returncode == 0 and 'EFFECTIVE' in r.stdout,
               "exit %d / %s" % (r.returncode, r.stdout[-200:]))


# ------------------------------------------------------- the whole point ----

def case_inert_is_distinguished():
    """3-of-3 must NOT read as success when the control also passed."""
    with tempfile.TemporaryDirectory() as tmp:
        fp = fingerprint(tmp, 'bridge-8934-evaluate-rejects-safe-navigation')
        r = judge(tmp, 'bridge-8934-evaluate-rejects-safe-navigation',
                  mk(3, True, fp))
        record("INERT 3 passes + PASSING control is INERT, not EFFECTIVE",
               'INERT' in r.stdout and 'EFFECTIVE' not in r.stdout,
               r.stdout[-250:])
        record("INERT names the reclaim action",
               'reclaim' in r.stdout.lower(), r.stdout[-250:])
        record("INERT does NOT propose removing it from the corpus",
               'audit trail' in r.stdout, r.stdout[-250:])


def case_split_is_not_averaged():
    with tempfile.TemporaryDirectory() as tmp:
        fp = fingerprint(tmp, 'bridge-8934-evaluate-rejects-safe-navigation')
        for n in (1, 2):
            r = judge(tmp, 'bridge-8934-evaluate-rejects-safe-navigation',
                      mk(n, False, fp))
            record("SPLIT %d of 3 reports UNRELIABLE" % n,
                   'UNRELIABLE' in r.stdout, r.stdout[-160:])


def case_zero_is_ineffective():
    with tempfile.TemporaryDirectory() as tmp:
        fp = fingerprint(tmp, 'bridge-8934-evaluate-rejects-safe-navigation')
        r = judge(tmp, 'bridge-8934-evaluate-rejects-safe-navigation',
                  mk(0, False, fp))
        record("ZERO 0 of 3 reports INEFFECTIVE, exit 0 (a real finding)",
               'INEFFECTIVE' in r.stdout and r.returncode == 0,
               "exit %d / %s" % (r.returncode, r.stdout[-160:]))


def case_control_outperforming_is_invalid():
    with tempfile.TemporaryDirectory() as tmp:
        fp = fingerprint(tmp, 'bridge-8934-evaluate-rejects-safe-navigation')
        r = judge(tmp, 'bridge-8934-evaluate-rejects-safe-navigation',
                  mk(0, True, fp))
        record("INVALID control passing while all runs fail is INVALID",
               'INVALID' in r.stdout, r.stdout[-200:])
        record("INVALID exits 1 - the run failed, nothing is concluded",
               r.returncode == 1, "exit %d" % r.returncode)
        record("INVALID blames the case, not the rule",
               'fix the case' in r.stdout.lower(), r.stdout[-200:])


# ---------------------------------------------------------------- negative --

def case_unrouted_key_refused():
    with tempfile.TemporaryDirectory() as tmp:
        r = plan(tmp, 'orphan-key-routed-nowhere')
        record("NEGATIVE a key routed nowhere is refused", r.returncode == 2,
               "exit %d" % r.returncode)
        record("NEGATIVE it says nothing is delivered",
               'not routed to any surface' in r.stdout, r.stdout[-200:])


def case_missing_case_refused():
    with tempfile.TemporaryDirectory() as tmp:
        r = plan(tmp, 'bridge-8933-arg-name')
        record("NEGATIVE a key with no authored case is refused",
               r.returncode == 2, "exit %d" % r.returncode)


def case_two_prompts_refused():
    with tempfile.TemporaryDirectory() as tmp:
        p = build(tmp)
        open(p['lessons'], 'a', encoding='utf-8').write(
            "\n### two prompt case\n"
            "- **Pattern-Key:** case-with-two-prompts\n"
            "- **Rule:** x\n")
        r = subprocess.run(
            [sys.executable, DRIVER, 'plan', '--key', 'case-with-two-prompts',
             '--lessons', p['lessons'], '--cases', p['cases'],
             '--skill-routes', p['skill'], '--plugin-routes', p['plugin']],
            capture_output=True, text=True)
        record("NEGATIVE a case with 2 prompts is refused", r.returncode == 2,
               "exit %d / %s" % (r.returncode, r.stdout[-160:]))


def case_missing_control_refused():
    with tempfile.TemporaryDirectory() as tmp:
        fp = fingerprint(tmp, 'bridge-8934-evaluate-rejects-safe-navigation')
        res = mk(3, False, fp)
        del res['control']
        r = judge(tmp, 'bridge-8934-evaluate-rejects-safe-navigation', res)
        record("NEGATIVE judging with no control is refused",
               r.returncode == 2, "exit %d" % r.returncode)
        record("NEGATIVE it says why a control is required",
               'not a measurement' in r.stdout, r.stdout[-200:])


def case_no_evidence_refused():
    with tempfile.TemporaryDirectory() as tmp:
        fp = fingerprint(tmp, 'bridge-8934-evaluate-rejects-safe-navigation')
        res = mk(3, False, fp)
        res['runs'][1]['evidence'] = '   '
        r = judge(tmp, 'bridge-8934-evaluate-rejects-safe-navigation', res)
        record("NEGATIVE a run with no evidence is refused",
               r.returncode == 2, "exit %d / %s" % (r.returncode, r.stdout[-160:]))


def case_bad_control_kind_refused():
    with tempfile.TemporaryDirectory() as tmp:
        fp = fingerprint(tmp, 'bridge-8934-evaluate-rejects-safe-navigation')
        r = judge(tmp, 'bridge-8934-evaluate-rejects-safe-navigation',
                  mk(3, False, fp, kind='whatever'))
        record("NEGATIVE control_kind must be proxy or ablation",
               r.returncode == 2, "exit %d" % r.returncode)


def case_stale_fingerprint_refused():
    with tempfile.TemporaryDirectory() as tmp:
        r = judge(tmp, 'bridge-8934-evaluate-rejects-safe-navigation',
                  mk(3, False, 'deadbeefdeadbeef'))
        record("NEGATIVE results from a changed case are refused",
               r.returncode == 2, "exit %d" % r.returncode)
        record("NEGATIVE it names the fingerprint mismatch",
               'different version' in r.stdout, r.stdout[-200:])


def case_ledger_replaces_not_appends():
    with tempfile.TemporaryDirectory() as tmp:
        led = os.path.join(tmp, 'ledger.json')
        fp = fingerprint(tmp, 'bridge-8934-evaluate-rejects-safe-navigation')
        judge(tmp, 'bridge-8934-evaluate-rejects-safe-navigation',
              mk(3, False, fp), ledger=led)
        judge(tmp, 'bridge-8934-evaluate-rejects-safe-navigation',
              mk(1, False, fp), ledger=led)
        data = json.load(open(led, encoding='utf-8'))
        record("LEDGER a re-run replaces the stale verdict for the same case",
               len(data) == 1, "%d entries" % len(data))
        record("LEDGER the surviving entry is the newer one",
               data and data[0]['passes'] == 1,
               str(data[0]['passes']) if data else 'empty')


def case_amended_rule_invalidates_verdict():
    """The gap found 2026-09-03: a fingerprint over the case alone would let
    a verdict survive an amendment to the very rule it judged."""
    with tempfile.TemporaryDirectory() as tmp:
        key = 'bridge-8934-evaluate-rejects-safe-navigation'
        fp_before = fingerprint(tmp, key)
        p = build(tmp)
        txt = open(p['lessons'], encoding='utf-8').read().replace(
            '- **Rule:** The evaluator does not implement the optional-property accessor.',
            '- **Rule:** The evaluator needs an @ prefix AND rejects the optional-property accessor.')
        open(p['lessons'], 'w', encoding='utf-8').write(txt)
        r = subprocess.run(
            [sys.executable, DRIVER, 'plan', '--key', key,
             '--lessons', p['lessons'], '--cases', p['cases'],
             '--skill-routes', p['skill'], '--plugin-routes', p['plugin']],
            capture_output=True, text=True)
        fp_after = None
        for line in r.stdout.split('\n'):
            if line.startswith('fingerprint:'):
                fp_after = line.split(':', 1)[1].strip()
        record("AMEND changing the rule changes the fingerprint",
               fp_before and fp_after and fp_before != fp_after,
               "before %s after %s" % (fp_before, fp_after))

        rp = os.path.join(tmp, 'stale.json')
        json.dump(mk(3, False, fp_before), open(rp, 'w', encoding='utf-8'))
        r2 = subprocess.run(
            [sys.executable, DRIVER, 'judge', '--key', key,
             '--cases', p['cases'], '--lessons', p['lessons'], '--results', rp],
            capture_output=True, text=True)
        record("AMEND a verdict for the OLD rule text is refused",
               r2.returncode == 2 and 'no longer exists' in r2.stdout,
               "exit %d / %s" % (r2.returncode, r2.stdout[-200:]))


def case_explain_covers_every_cell():
    r = subprocess.run([sys.executable, DRIVER, 'explain'],
                       capture_output=True, text=True)
    record("EXPLAIN the table is printable without reading source",
           r.returncode == 0 and r.stdout.count('->') == 8,
           "%d rows" % r.stdout.count('->'))


def main():
    for fn in (case_positive_plan,
               case_positive_judge,
               case_inert_is_distinguished,
               case_split_is_not_averaged,
               case_zero_is_ineffective,
               case_control_outperforming_is_invalid,
               case_unrouted_key_refused,
               case_missing_case_refused,
               case_two_prompts_refused,
               case_missing_control_refused,
               case_no_evidence_refused,
               case_bad_control_kind_refused,
               case_stale_fingerprint_refused,
               case_ledger_replaces_not_appends,
               case_amended_rule_invalidates_verdict,
               case_explain_covers_every_cell):
        try:
            fn()
        except Exception as exc:
            record(fn.__name__ + ' (raised)', False, repr(exc))

    width = max(len(n) for n, _, _ in RESULTS)
    failed = 0
    for name, passed, detail in RESULTS:
        print("%-4s %-*s %s" % ('PASS' if passed else 'FAIL', width, name,
                               '' if passed else detail))
        if not passed:
            failed += 1
    print()
    print("%d of %d passed" % (len(RESULTS) - failed, len(RESULTS)))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
