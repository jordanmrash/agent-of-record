# Dream cycle - deterministic specifications

Load this when writing a report, computing a fingerprint, or deciding whether a
run is a no-op. `SKILL.md` carries the rules; this file carries the exact shapes
so two runs over the same corpus produce the same answer.

---

## 1. Corpus checkpoint - what "nothing changed" actually means

The no-op gate originally compared the lessons file's modified date. That is a
proxy, and a bad one: a built-in memory can change, a pointer can break, or a
proposal can be declined, all while `cowork-lessons.md` sits untouched. The
cycle would have stopped and reported NO-OP over a corpus that had moved.

Compute every component available in the current mode:

```yaml
checkpoint:
  lessons_sha256:              # file bytes
  instructions_sha256:         # file bytes
  memory_index_sha256:         # file bytes
  cowork_memory_tree_sha256:   # see below
  built_in_memory_signature:   # see below
  digest_sha256:               # the LESSON-DIGEST block only, not the whole file
  proposal_disposition_sha256: # see below
  git_head:                    # FULL mode only; omit in CLOUD, do not fake it
  completed_at:                # ISO-8601, absolute, never relative
```

**Determinism rules** - without these, two runs over an identical corpus
disagree and every night looks like a change:

- Hash file BYTES, never rendered or re-encoded text.
- `cowork_memory_tree_sha256`: sort paths, then hash `path + "\n" + sha256(bytes)`
  for each in order. Sorting matters - directory listing order is not stable.
- `built_in_memory_signature`: sort by key, then hash `key + "\u0000" + content`
  for each. EXCLUDE `created_at`, `updated_at`, `last_used_at` and any paging
  token - `last_used_at` changes on every read, so including it would make the
  corpus look modified every single night.
- `proposal_disposition_sha256`: over `id + status + fingerprint_sha256` for
  every proposal in every retained report, sorted by id. Report prose and
  whitespace are excluded - only dispositions count.
- The digest hash covers the block between the LESSON-DIGEST markers, not the
  whole instructions file, so unrelated edits to instructions do not read as a
  digest change.

**Comparison:** read the checkpoint from the newest VERIFIED report. If every
component present in both is identical, the run is `NO-OP`. If any differs, run
the full analysis. A component present in one and absent in the other (e.g.
`git_head` when comparing a FULL report to a CLOUD run) is NOT a difference -
skip it and say so.

Enumerating built-in memory fully is required before its signature can be
computed. That is not wasted work; it is the minimum needed to answer the
question honestly.

---

## 2. Proposal fingerprint - canonical form

The ID identifies the instance and carries a date. The fingerprint identifies
the SUBSTANCE and must be stable across runs, or a declined proposal returns
tomorrow wearing a new ID.

Serialize exactly this, then SHA-256 it:

```json
{
  "schema_version": 1,
  "type": "merge",
  "targets": ["bridge-x", "bridge-y"],
  "operation": "merge bridge-x into bridge-y"
}
```

Canonicalization, in order:

1. Unicode-normalize (NFC) every string.
2. Trim leading and trailing whitespace.
3. Collapse internal whitespace runs to one space.
4. Lowercase `type` and every entry in `targets`.
5. **Sort `targets`** - a merge of A+B and of B+A are the same proposal.
6. Keep `operation` normalized but specific enough to distinguish two different
   changes to the same targets.
7. Serialize with sorted keys, no incidental whitespace.
8. SHA-256 the serialized string.

Store BOTH `fingerprint_material` (the serialized JSON) and
`fingerprint_sha256`. The material is what makes a mismatch debuggable; a bare
hash tells you two things differ and nothing about why.

**Reopening a declined fingerprint** requires all four fields - anything less is
prose judgement wearing a schema:

```yaml
reopens:
  prior_proposal_id:
  prior_fingerprint:
  new_evidence:            # what was measured that was not known before
  substantive_difference:  # why this is not simply the same proposal again
```

---

## 3. State and Outcome - the only valid combinations

State describes DATA QUALITY. Outcome describes FINDINGS. They are independent
but not freely combinable:

| State | Outcome | Valid |
|---|---|---|
| `COMPLETE` | `PROPOSALS` | yes |
| `COMPLETE` | `NO-OP` | yes |
| `COMPLETE (expected limits)` | `PROPOSALS` | yes |
| `COMPLETE (expected limits)` | `NO-OP` | yes |
| `INCOMPLETE` | `FAILED` | yes |
| `FAILED INTEGRITY` | `FAILED` | yes |

**Invariant:** if State is `INCOMPLETE` or `FAILED INTEGRITY`, Outcome MUST be
`FAILED` and the proposal count MUST be zero. Any other pairing is a defect in
the run, not a finding - say so rather than emitting it.

---

## 4. Run evidence block - goes in every report

Enough to establish which corpus and which scripts produced the findings,
without the report becoming a second lessons file:

```yaml
run_evidence:
  mode:                        # CLOUD | FULL
  state:
  outcome:
  lessons_sha256:
  instructions_sha256:
  memory_index_sha256:
  cowork_memory_tree_sha256:
  analyzer_sha256:             # of dream_analyze.py AS RETRIEVED
  approved_analyzer_sha256:    # from analyser.approved
  memories_enumerated:         # "81 of 81" or "50 of 81 - INCOMPLETE"
  memory_pages:
  lesson_check_exit:
  lesson_gate_exit:
  report_readback_verified:    # true | false
  report_byte_count:
```

This is what makes a later "the same corpus produced different findings"
question answerable instead of speculative.

---

## 5. Same-date reruns - never overwrite

`dream-reports/YYYY-MM-DD.md` is one filename per date, and a FULL rerun on the
same day would silently destroy the scheduled run's report - including its
disposition history, which is the suppression mechanism.

Reruns get their own file:

```
2026-08-31.md              the scheduled run
2026-08-31-rerun-01.md     an interactive rerun the same day
2026-08-31-rerun-02.md
```

Each rerun carries:

```yaml
supersedes_report:    # the filename it supersedes
trigger:              # scheduled | interactive
mode:                 # CLOUD | FULL
reason_for_rerun:
```

The superseded report is NOT deleted and NOT edited except for its disposition
fields. "Newest report" for the morning handoff means newest by filename order,
reruns included.

---

## 6. Analyser release gate

`dream_analyze_selftest.py` is a DEPLOYMENT gate, not a nightly step. Running 22
unchanged tests every night costs credits and proves nothing new; what matters
is that the analyser being executed is the one that passed them.

**The security invariant is an ORDERING, and it only holds in this order:**

```
test the exact candidate bytes
  -> the complete current suite passes
    -> hash THOSE EXACT BYTES and write the marker
      -> nightly run hashes the retrieved bytes
        -> execute only on an exact match
```

The selftest MUST NOT modify `dream_analyze.py` between testing it and hashing
it - every case copies the analyser into a temporary directory and works there,
never writing to the file under test. If a future case ever needs to modify the
analyser, it must do so on a copy, or the marker stops meaning "these bytes
passed".

The gate requires the COMPLETE CURRENT SUITE to pass, not a fixed case count. A
hard-coded number goes stale the moment a test is added, and a stale count in a
safety claim is worse than no count.

**On any change to `dream_analyze.py`:**

1. Run `dream_analyze_selftest.py`. Every case must pass.
2. On a pass it writes the SHA-256 of the tested bytes to `analyser.approved`
   beside the scripts. On a FAILURE it REMOVES any existing marker, so an
   earlier approval cannot survive a failed candidate test.

**Format - validate by STRIP-THEN-MATCH, not by a literal byte pattern:**

```python
content = open("analyser.approved", encoding="utf-8").read().strip()
valid   = re.fullmatch(r"[0-9a-f]{64}", content)
```

Strip first, then require exactly 64 lowercase hex characters. This tolerates
LF, CRLF, or no trailing newline - the file is written on Windows and crosses
OneDrive, so a line-ending assumption is not a safety property - while still
rejecting what actually matters: extra lines (an interior newline survives the
strip and fails the hex match), uppercase, and whitespace-only content. Anything
that fails is `FAILED INTEGRITY`, never a value to salvage.

MEASURED 2026-08-30, in the first literal dry run of this manifest: the writer
used Python text mode, which translated `\n` to `\r\n` on Windows, producing a
66-byte marker where a validator matching `[0-9a-f]{64}\n?` expected 65. The
gate rejected its OWN marker and the nightly run would have been `FAILED
INTEGRITY` every night. The writer now passes `newline=""` so the artifact is
canonical LF, and the reader strips - the artifact is exact and the check is
tolerant, which is the right way round.

**Location:** `/Documents/Cowork/Skills/self-improvement/scripts/analyser.approved`.
The CLOUD manifest must retrieve it explicitly - it is not implied by the
selftest writing it beside the analyser, because in CLOUD mode nothing runs the
selftest.

**Deliberate deviation from the reviewed design:** the approved hash is written
BY the selftest on a passing run, not recorded by hand. A manually maintained
hash has a failure mode worse than the one it prevents - a legitimate edit with
a forgotten hash update blocks every subsequent nightly run, which trains
whoever hits it to disable the gate. Self-updating keeps the guarantee (the
executed analyser passed its tests) without the footgun.

**Nightly:** hash the retrieved `dream_analyze.py` and compare to
`analyser.approved`. On mismatch the run is `FAILED INTEGRITY` - do not execute
the analyser and generate no proposals. If `analyser.approved` is missing
entirely, that is also `FAILED INTEGRITY`: an ungated analyser is exactly the
case this exists to catch, and treating a missing file as "no gate configured,
proceed" would defeat it.

---

## 7. Report write failure - the edge case where nothing can be trusted

An `INCOMPLETE` run may normally write a diagnostic report. But if the failed
surface IS the report write, no report of any kind can be claimed:

- State `INCOMPLETE`, Outcome `FAILED`.
- Claim NO report exists - neither a normal one nor a diagnostic.
- Include no report link and no report path as a completed artifact.
- Send a failure notification ONLY if the email surface was resolved
  independently of the write surface.
- The notification must state plainly that no verified report was created, and
  name the write or read-back step that failed.

The rule underneath: never let a notification imply an artifact exists that was
not read back and verified.
