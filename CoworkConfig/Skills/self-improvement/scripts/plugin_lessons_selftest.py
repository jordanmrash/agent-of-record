#!/usr/bin/env python3
"""
plugin_lessons_selftest.py - break the applier before trusting it.

Every negative case asserts WHY it failed, not merely that it did. A test that
only checks a non-zero exit cannot tell a refusal from a crash, which is the
failure recorded in verifier-usage-error-reads-as-finding.

The positive control runs FIRST. If the applier cannot do the ordinary thing,
every negative below it is meaningless - a script that refuses everything
passes a suite made only of negatives.

Where node is available the rendered output is also PARSED. But note what the
parse check CANNOT do: measured 2026-09-03, deleting the backslash escape in
js_string() produced 'C:\\Cowork\\CommandJobs' - valid JavaScript that silently
evaluates to 'C:CoworkCommandJobs'. node --check passed it. Only the explicit
ESCAPE assertion caught the corruption, which is why that assertion exists
separately rather than being folded into the parse case.

Adjudicates ONCE, at the end, after every case has been collected.
"""

import json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
APPLIER = os.path.join(HERE, 'plugin_lessons.py')

RESULTS = []


def record(name, passed, detail=''):
    RESULTS.append((name, passed, detail))


LESSONS = """# Lessons

### The parameter is file, never path
- **Pattern-Key:** bridge-8933-arg-name
- **Date:** 2026-08-17
- **Rule:** The run_batch_file parameter is `file`, never `path`. A wrong name is rejected before the job runs.
- **Hits:** 3

### Files written through the bridge arrive LF-only
- **Pattern-Key:** bridge-8932-writes-lf
- **Date:** 2026-08-18
- **Rule:** A .bat written through the filesystem bridge arrives LF-only and cmd mis-parses it. Run the CRLF fix on any newly written job under C:\\Cowork\\CommandJobs before executing it.
- **Hits:** 2

### After a transport error, check whether the job ran
- **Pattern-Key:** bridge-8933-transport-drop-verify-first
- **Date:** 2026-08-18
- **Rule:** After a transport error, check whether the job already ran before retrying. Never blind-retry a state-changing job.
- **Hits:** 5

### An entry with no authored rule
- **Pattern-Key:** bridge-8933-no-rule-yet
- **Date:** 2026-08-20
- **Hits:** 1

### A rule belonging to a different surface
- **Pattern-Key:** memory-two-stores-drift
- **Date:** 2026-08-25
- **Rule:** A fact gets ONE home. On conflict the file wins.
- **Hits:** 4
"""

SERVER_WITH_MARKERS = """'use strict';
const TOOL = {
  name: 'run_batch_file',
  description:
    'Execute an existing .bat under CommandJobs. ' +
    'The only input is the filename.'
    /* PLUGIN-LESSONS:start run_batch_file */
    + ''
    /* PLUGIN-LESSONS:end */
  ,
  inputSchema: { type: 'object' }
};
module.exports = { TOOL };
"""

SERVER_NO_MARKERS = """'use strict';
const TOOL = {
  name: 'run_batch_file',
  description:
    'Execute an existing .bat under CommandJobs.'
  ,
  inputSchema: { type: 'object' }
};
module.exports = { TOOL };
"""

ROUTES = {
    "command-bridge-8933": {
        "title": "the approved batch executor (8933)",
        "server": "CommandBridge/batch-exec-server.js",
        "tool": "run_batch_file",
        "max_rules": 6,
        "max_bytes": 1400,
        "prefix": ["bridge-8933-"],
        "exact": ["bridge-8932-writes-lf"]
    }
}


def build(tmp, server_src=SERVER_WITH_MARKERS, routes=None):
    os.makedirs(os.path.join(tmp, 'CommandBridge'), exist_ok=True)
    with open(os.path.join(tmp, 'CommandBridge', 'batch-exec-server.js'),
              'w', encoding='utf-8') as fh:
        fh.write(server_src)
    lessons = os.path.join(tmp, 'lessons.md')
    with open(lessons, 'w', encoding='utf-8') as fh:
        fh.write(LESSONS)
    rpath = os.path.join(tmp, 'routes.json')
    with open(rpath, 'w', encoding='utf-8') as fh:
        json.dump(routes or ROUTES, fh)
    return lessons, rpath


def run(tmp, lessons, routes, *extra):
    cmd = [sys.executable, APPLIER, '--lessons', lessons,
           '--servers-dir', tmp, '--routes', routes] + list(extra)
    return subprocess.run(cmd, capture_output=True, text=True)


def server_text(tmp):
    return open(os.path.join(tmp, 'CommandBridge', 'batch-exec-server.js'),
                encoding='utf-8').read()


def node_parses(js):
    """(ok, stderr) if node checked it; None if node is unavailable."""
    exe = shutil.which('node')
    if not exe:
        return None
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False,
                                     encoding='utf-8') as fh:
        fh.write(js)
        p = fh.name
    try:
        r = subprocess.run([exe, '--check', p], capture_output=True, text=True)
        return r.returncode == 0, r.stderr.strip()
    finally:
        os.unlink(p)


# ---------------------------------------------------------------- positive --

def case_positive_control():
    """The ordinary path must work before any refusal below it means anything."""
    with tempfile.TemporaryDirectory() as tmp:
        lessons, routes = build(tmp)
        r = run(tmp, lessons, routes)
        txt = server_text(tmp)
        record("POSITIVE applier exits 0 on the ordinary path",
               r.returncode == 0,
               "exit %d / %s" % (r.returncode, r.stdout[-200:]))
        record("POSITIVE the routed rule text reaches the description",
               'never `path`' in txt or "never \\'path\\'" in txt or 'never' in txt,
               "segment: %s" % txt[txt.find('start run_batch_file'):][:160])
        record("POSITIVE the out-of-scope rule is NOT pulled in",
               'ONE home' not in txt,
               "memory-two-stores-drift must not route to this tool")
        record("POSITIVE the rule with no Rule field is skipped",
               'no-rule-yet' not in txt)


def case_output_parses_as_js():
    with tempfile.TemporaryDirectory() as tmp:
        lessons, routes = build(tmp)
        run(tmp, lessons, routes)
        txt = server_text(tmp)
        res = node_parses(txt)
        if res is None:
            record("PARSE node unavailable - parse claim NOT made", True,
                   "reported honestly rather than assumed")
        else:
            good, err = res
            record("PARSE the rewritten server is valid JavaScript", good, err)


def case_escaping_survives():
    """Backslashes and quotes in a rule must not break the string literal."""
    with tempfile.TemporaryDirectory() as tmp:
        lessons, routes = build(tmp)
        run(tmp, lessons, routes)
        txt = server_text(tmp)
        seg = txt.split('PLUGIN-LESSONS:start')[1].split('PLUGIN-LESSONS:end')[0]
        record("ESCAPE a Windows path is backslash-escaped",
               'C:\\\\Cowork' in seg,
               "found: %s" % [l for l in seg.split('\n') if 'Cowork' in l])
        record("ESCAPE a backquoted term keeps its quote escaped",
               "\\'" in seg or '`file`' in seg,
               "segment must not contain a bare unescaped single quote")
        res = node_parses(txt)
        if res is not None:
            record("ESCAPE the escaped output still parses", res[0], res[1])


def case_idempotent():
    with tempfile.TemporaryDirectory() as tmp:
        lessons, routes = build(tmp)
        run(tmp, lessons, routes)
        once = server_text(tmp)
        r2 = run(tmp, lessons, routes)
        twice = server_text(tmp)
        record("IDEMPOTENT a second run changes nothing", once == twice)
        record("IDEMPOTENT the second run reports 'current'",
               'current' in r2.stdout, r2.stdout[-200:])


# ---------------------------------------------------------------- negative --

def case_markers_absent_refuses():
    with tempfile.TemporaryDirectory() as tmp:
        lessons, routes = build(tmp, server_src=SERVER_NO_MARKERS)
        before = server_text(tmp)
        r = run(tmp, lessons, routes)
        after = server_text(tmp)
        record("NEGATIVE markers absent exits 2, not 1",
               r.returncode == 2,
               "exit %d - 2 is REFUSED, 1 would mean a finding" % r.returncode)
        record("NEGATIVE markers absent says MARKERS-ABSENT",
               'MARKERS-ABSENT' in r.stdout,
               "must name the cause, not just fail: %s" % r.stdout[-200:])
        record("NEGATIVE markers absent writes nothing", before == after)


def case_budget_exceeded_refuses():
    routes = json.loads(json.dumps(ROUTES))
    routes['command-bridge-8933']['max_bytes'] = 40
    with tempfile.TemporaryDirectory() as tmp:
        lessons, rp = build(tmp, routes=routes)
        before = server_text(tmp)
        r = run(tmp, lessons, rp)
        after = server_text(tmp)
        record("NEGATIVE over-budget exits 2", r.returncode == 2,
               "exit %d" % r.returncode)
        record("NEGATIVE over-budget names the budget in the message",
               'budget' in r.stdout and '40' in r.stdout,
               r.stdout[-200:])
        record("NEGATIVE over-budget writes nothing", before == after)


def case_check_writes_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        lessons, routes = build(tmp)
        before = server_text(tmp)
        r = run(tmp, lessons, routes, '--check')
        after = server_text(tmp)
        record("NEGATIVE --check writes nothing", before == after)
        record("NEGATIVE --check exits 1 on drift", r.returncode == 1,
               "exit %d - 1 means STALE" % r.returncode)
        record("NEGATIVE --check says STALE", 'STALE' in r.stdout,
               r.stdout[-200:])


def case_check_clean_exits_zero():
    """The control the --check case needs: clean must be distinguishable."""
    with tempfile.TemporaryDirectory() as tmp:
        lessons, routes = build(tmp)
        run(tmp, lessons, routes)           # bring it current
        r = run(tmp, lessons, routes, '--check')
        record("CONTROL --check on a current file exits 0",
               r.returncode == 0,
               "exit %d - if this were also 1, the STALE signal would be noise"
               % r.returncode)


def case_outside_markers_preserved():
    with tempfile.TemporaryDirectory() as tmp:
        lessons, routes = build(tmp)
        run(tmp, lessons, routes)
        txt = server_text(tmp)
        record("GUARD hand-written description text survives",
               'Execute an existing .bat under CommandJobs.' in txt)
        record("GUARD the trailing schema survives",
               "inputSchema: { type: 'object' }" in txt)
        record("GUARD module tail survives",
               'module.exports' in txt)


def case_empty_route_is_not_a_crash():
    routes = json.loads(json.dumps(ROUTES))
    routes['command-bridge-8933']['prefix'] = ['nothing-matches-this-']
    routes['command-bridge-8933']['exact'] = []
    with tempfile.TemporaryDirectory() as tmp:
        lessons, rp = build(tmp, routes=routes)
        r = run(tmp, lessons, rp)
        txt = server_text(tmp)
        record("EMPTY a route matching nothing exits 0", r.returncode == 0,
               "exit %d / %s" % (r.returncode, r.stdout[-160:]))
        res = node_parses(txt)
        if res is not None:
            record("EMPTY the empty segment still parses", res[0], res[1])


def main():
    for fn in (case_positive_control,
               case_output_parses_as_js,
               case_escaping_survives,
               case_idempotent,
               case_markers_absent_refuses,
               case_budget_exceeded_refuses,
               case_check_writes_nothing,
               case_check_clean_exits_zero,
               case_outside_markers_preserved,
               case_empty_route_is_not_a_crash):
        try:
            fn()
        except Exception as exc:
            record(fn.__name__ + " (raised)", False, repr(exc))

    # Adjudicate ONCE, at the end, after every case has been collected.
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
