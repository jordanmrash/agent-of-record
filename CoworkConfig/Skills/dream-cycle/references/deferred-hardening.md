# Deferred hardening - build these AFTER real runs, not before

From the 2026-08-31 review. Every item is sound. None is built, deliberately.

**Why deferred:** dream-cycle reached v1.5.0 across five review rounds in one
evening and had executed **zero** scheduled sweeps. The review's strongest item
is a fail-closed state validator - proposed 90 minutes before the first run. A
gate that fails closed INCORRECTLY blocks the run that would have produced the
evidence it needs. The review's own ordering says two of its five items belong
"after observing several natural runs", its regression suite needs runs to
regress against, and its acceptance criteria are all measurements.

Recorded here so deferral is a decision, not loss. See lesson
`review-rounds-outpaced-the-first-real-run`.

---

## 1. Machine-readable run-state artifact + transition validator
**Build after: 3-5 real runs. Highest value of the five.**

Today State and Outcome are prose fields; the model decides whether it may
proceed. A deterministic validator would make that impassable:

```json
{"schema_version":1,"run_id":"DC-2026-08-31-CLOUD-001","mode":"CLOUD",
 "phase":"integrity","inputs_complete":true,"memory_enumeration_complete":true,
 "analyser_approved":true,"lesson_check_passed":true,"digest_audit_passed":true,
 "pointers_executed":true,"report_verified":false,"proposals_allowed":true,
 "state":"COMPLETE_EXPECTED_LIMITS","outcome":null,"next_phase":"analysis"}
```

Analysis may not begin unless `inputs_complete`, `memory_enumeration_complete`,
`analyser_approved`, `lesson_check_passed`, `digest_audit_passed` and
`pointers_executed` are all true.

Acceptance: 0 proposals when `proposals_allowed=false`; 0 invalid transitions
accepted; 100% agreement between report State and machine state; 100% of runs
reach an allowed terminal state.

**Wait for runs because** the phase boundaries should match what a real sweep
actually does, and a wrong boundary here blocks everything.

## 2. Regression suite
**Build after: the first run. Fixtures already exist - they are today's defects.**

Each becomes a permanent fixture: missing `lesson_gate.py`; missing
`analyser.approved`; missing determinism reference; valid marker with CRLF;
malformed marker; stale digest; incomplete memory pagination; missing memory
file; POINTERS not executed; report write succeeds but read-back fails; report
succeeds but notification fails; declined fingerprint reappears under a new ID;
latest report failed while an older one remains actionable.

Several are already covered piecemeal - `manifest_check.py` covers the first
three, `dream_analyze_selftest.py` covers detector behaviour. The gap is one
harness that runs them together against a candidate version.

## 3. Failure taxonomy with fixture linkage
**Build after: the first FAILED run. There is nothing to classify yet.**

```yaml
failure:
  stage: acquisition           # routing|acquisition|context|state|tool_transport|
  class: undeclared_dependency #  permissions|execution|integrity|judgment|
  earliest_cause:              #  report_write|notification|handoff|approval|application
  downstream_symptom:
  affected_artifacts: []
  retry_safe: false
  regression_fixture:
```

The value is preventing one root cause being counted as four defects: the marker
not acquired -> marker missing -> FAILED INTEGRITY -> no proposals -> failure
email is ONE acquisition defect, not five.

## 4. Proposal-quality scorecard
**Build after: enough completed cycles that dispositions exist. Explicitly
deferred by the review itself.**

Headline metric: `accepted, nonrecurring proposals / total proposals generated`.
Plus decline reason codes: not actually duplicate; evidence insufficient; target
incorrect; already resolved; change too broad; right observation wrong action;
no longer relevant; conflicts with owning skill; false detector match.

This is the only measure that answers whether the JUDGED half earns its cost.
Counting proposals does not - eight weak proposals are worse than two good ones.

## 5. Checkpoint and resume workspace
**Build only if interruptions actually happen. Do not pre-build.**

An ephemeral `dream-work/<run_id>/` holding state, checkpoint, integrity
results, findings and a report draft, checkpointed after each verified stage.
Revalidate input hashes before resuming; never resend a notification without
checking recorded delivery status; never reuse judged findings if the corpus
checkpoint moved.

**Caution from the review, worth keeping:** this must stay ephemeral execution
state with a retention rule. It must not become another durable memory store.

---

## Explicitly NOT to add

The review's own do-not-add list, recorded because a future session will be
tempted: generic thinking-hats analysis; unrestricted multi-agent debate;
another output contract; larger inline reference sections; more trigger phrases;
autonomous application of findings; model-generated self-modification without
regression evaluation and approval.
