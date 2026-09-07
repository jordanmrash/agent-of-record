# Memory: Cowork Configuration & Setup

- **Slug:** cowork-config-setup
- **Created:** 2026-07-27
- **Last Updated:** 2026-09-02
- **Sessions captured:** 6

## Summary
Configuring Cowork so it applies Jordan's standing preferences automatically instead of
requiring explicit instruction each session. Personal instructions are broken at the platform
level on this tenant; the working substitute is encoding standing rules as skills, which do
load. The 2026-07-27 bridge outage is RESOLVED — see the `cowork-bridge-infrastructure`
memory for all bridge operations, hardening, and version control.

## Key Facts

### Platform findings (still current as of 2026-08-18)
- `copilot-instructions.md` does NOT take effect on this tenant. Cowork loads instructions
  from `/mnt/workspace/copilot-instructions.md`, which holds ~70 bytes of unrelated
  boilerplate ("Use these tools to access SharePoint and other Power Platform services").
  Jordan's real file reaches OneDrive correctly but never reaches the loader.
  **Re-confirmed 2026-08-18** — that same boilerplate string was live in the session.
- Skills DO load reliably and register in the live session immediately.
- Skill **descriptions** are injected into context at session start whether or not the skill
  fires — so standing directives belong in the description field, not only the body.
  This is the ONLY reliable mechanism for "do X every session" on this tenant.
- The tool surface is fixed at session start. A connector that is absent cannot be added
  mid-conversation; start a new chat instead.
- OneDrive replication of new skills/memory runs slower than the documented ~35s.

### The two "Cowork" folders — keep straight
- **`C:\Users\YOURUSER\Documents\COPILOT_COWORK`** (local PC, bridge-reachable) — renamed from
  `Cowork` on 2026-07-27. Now holds Startup, CommandJobs, autorun, Outputs, staged skills,
  and a git repo. Does not sync to OneDrive.
- **OneDrive `Documents/Cowork`** (Cowork's config store, NOT bridge-reachable) — holds
  Skills, `cowork-memory/`, `copilot-instructions.md`. Reach via the OneDrive tools or the
  `/mnt/user-config/` mount.

### The two memory stores — keep straight (added 2026-08-20)
- **Built-in memory tools** (`save_memory` / `list_memories`) — a separate store, ~59
  entries. Fast recall inside Cowork. NOT files, NOT in OneDrive, NOT under git.
- **OneDrive `Documents/Cowork/cowork-memory/*.md`** — `MEMORY-INDEX.md`,
  `cowork-lessons.md`, `cowork-bridge-infrastructure.md`, `cowork-config-setup.md`. This is
  what the `persistent-memory` skill reads and what `CoworkConfig\` puts under git.
- **They do not sync.** On 2026-08-20 the built-in store held three same-day entries while
  every `cowork-memory` file still read 2026-08-18.
- **SUPERSEDED 2026-08-25** — the write-to-BOTH rule that stood here was the cause of the
  drift, not the cure. See "Memory architecture — two tiers" below: one home per fact, and on
  conflict the file wins.

### Skills live in OneDrive, so they are backed up; the repo is not (added 2026-08-20)
- `Documents/Cowork` syncs to the cloud — skills, memory and instructions survive a dead
  laptop. `COPILOT_COWORK` and its git history are local only and do not.
- Consequence: a skill edit is protected the moment it uploads; the git commit adds history
  and revertibility, not durability. Do not describe committing as "backing up".

### The 1024-character description cap silently unloads a skill (added 2026-08-21)

The CLI skill loader drops any skill whose frontmatter `description` exceeds 1024 UTF-16
units. No error is shown; the skill simply never appears in the session's skill list and
never triggers. Measured 2026-08-21: `persistent-memory` was at 1257 units and
`self-improvement` at 1519 — **both had been silently unloaded**, and the always-on
behaviour that appeared to work was coming from `copilot-instructions.md`, which duplicates
the same rules. Trimmed to 747 and 861 units; scores 93 to 96 and 63 to 68. Target 800,
never exceed 1024, and re-run `validate_skill.py` after any edit that adds trigger phrases.

Corollary: instructions are NOT broken on this tenant the way the 2026-07-27 summary
assumed — `copilot-instructions.md` loads and is doing real work. It is the oversized
skills that were not loading.

## Memory architecture — two tiers (decided 2026-08-25)

Cowork has its own built-in persistent memory, separate from the `cowork-memory` files. Both
are real, neither replaces the other, and duplicating content across them is what caused the
drift recorded in `memory-two-stores-drift`.

| | Built-in store (POINTER tier) | `cowork-memory/*.md` (DEEP tier) |
|---|---|---|
| Loads | automatically, before the first turn | only if a skill fires and OneDrive has replicated |
| Needs a bridge | no | yes, for a same-session write |
| Unit | keyed facts, hard cap 512 chars | long-form Markdown, no cap |
| Versioned in git | no | yes, via `CoworkConfig\` |
| Editable by hand | no — chat only | yes |
| Searchable | yes, scored recall | via `MEMORY-INDEX.md` |

**The rule:** one home per fact. A durable finding lives in the deep tier and gets at most a
short `ptr-<slug>` pointer in the built-in store naming the file and when to read it. On
conflict the file wins, because it is dated and versioned; update the pointer, never the reverse.

**Why the pointer tier matters:** it is the only tier that survives a session where the bridges
did not register. On 2026-08-25 the bridges were absent at session start, and the pointer tier
was written successfully while all four file edits had to be deferred.

**Pointers in place as of 2026-08-25:** `ptr-cowork-config-setup`,
`ptr-cowork-bridge-infrastructure`, `ptr-cowork-lessons`, `ptr-cowork-skill-design`, governed by
`instruction-memory-tiering`.

## Decisions Made
- ~~2026-07-27 — Abandoned `copilot-instructions.md` as the mechanism for standing rules; the
  load path is broken platform-side.~~ **SUPERSEDED 2026-08-25** — the premise was wrong. The
  instructions file loads and does real work (see the corollary above); it was the oversized
  skill descriptions that were not loading.
- ~~2026-07-27 — Created the `local-file-bridge` skill to carry the bridge routing rules, with
  the directive in the description field so it loads at session start.~~ **SUPERSEDED
  2026-08-25 as a general pattern** — a directive in a description does not survive routing
  (measured 2026-08-18, commit 3292cf1). The bridge routing rules now also live in
  `copilot-instructions.md` § "Local MCP bridges". `local-file-bridge` itself was not edited.
- 2026-07-27 — Renamed the PC folder `Cowork` → `COPILOT_COWORK` to end the name collision.
- ~~2026-08-18 — Put the persistent-memory auto-load directive in that skill's description
  field rather than in `copilot-instructions.md`, for the same reason.~~ **REVERSED
  2026-08-25** — both the memory and the lessons obligations now live in
  `copilot-instructions.md`, which loads unconditionally. The ALWAYS-ON preambles were removed
  from the `persistent-memory` and `self-improvement` descriptions and that budget returned to
  trigger phrases (840→791 and 726→792 UTF-16 units, both under the 800 target).

## Resolved — do not re-investigate
- 2026-07-27's blocking bug (npx resolving npm relative to CWD, caused by nested cmd quoting
  of `--stdio`) is FIXED. The launcher now uses per-bridge `.cmd` helpers
  (`pw-server.cmd`, `fs-server.cmd`, `exec-server.cmd`) invoked from tasks.json, which was
  option (b)/(c) of the three proposed fixes. All three bridges run normally.
- Supergateway is no longer fetched with `npx -y`; version 3.4.3 is pinned locally.
- Dev tunnels, port forwarding, and Public visibility were never the fault and remain fine.

- **2026-08-21 — `gamma-tango` skill created.** One typed phrase, `gamma tango`, bookends a
  work session by running three skills in a fixed order. OPEN: persistent-memory loads the
  matching memory file, self-improvement scans lessons Pattern-Keys, git-bridge reports the
  repo baseline. CLOSE: lessons logged first, memory updated second, git commit proposed and
  run last. Mode is inferred when no mode word is given. It delegates only — no hand-rolled
  git, memory or lesson logic. Scored 84 (Good), clears its floor.
- **2026-08-21 — autorun fallback struck from every surface.** `copilot-instructions.md` and
  the `local-file-bridge` skill now both say there is NO fallback when 8933 is down: retry
  once, then stop and report. `AUTORUN.ps1` is manual-use-only; the watcher task was already
  removed from `tasks.json` (commit 784dc9f). Stored memory `pref-8933-down-use-autorun-queue`
  deleted.

- **2026-08-21 — `self-improvement` rebuilt against external references, 63 to 94 (Excellent).**
  Added: a mid-session review cadence (~every 15 tool calls and at each phase boundary), a
  promotion ladder that moves a recurring lesson out of the log into instructions / the owning
  SKILL.md / memory with a `Promoted-to:` back-pointer, capability gaps split into a build list,
  a periodic audit that downgrades or deletes unconfirmed `reported` entries, a failure-handling
  table, a `Guardrails` section, and a `Hits:` counter that drives promotion at 2. Sources:
  Hermes GEPA loop (root-cause capture, review cadence, human review of self-modification) and
  the OpenClaw self-improvement skills (promotion targets, "logging is not fixing", lessons can
  encode a coincidence). Clears its 80 high-risk floor for the first time.
- **2026-08-21 — `Better-Faster-Stronger` skill built for the Cowork POC group.** Portable
  self-improvement loop: reads lessons at task start, checkpoints periodically, records at task
  end, bootstraps its own `lessons/LESSONS.md` in the user's Cowork folder, zero setup, no
  bridges or scripts. 93 Excellent, under the 15KB size gate, security scan clean. Delivered as
  `Better-Faster-Stronger-skill.zip` with a README carrying the `copilot-instructions.md` lines
  that make it fire reliably — routing alone is best-effort, and that caveat travels with it.
- **Decision: do NOT merge memory / git / self-improvement into one skill.** A merged
  description would be roughly 2,500 units against the 1,024 cap, it would couple ambient
  always-on work to an approval-gated shell bridge, and one broken file would take out all
  three. `gamma-tango` is the composition layer instead.

- **2026-08-21 — `myvoice` recalibrated from a hand-rewritten article, 9 rules to 21, score 100.**
  Jordan rewrote a full AI-drafted LinkedIn article by hand; the diff was measured rather than
  read. Headline finding: **zero em dashes and zero semicolons across 2,542 words**, every em
  dash in the draft removed by hand — now rule 1 plus a mechanical strip-pass and a guardrail.
  Other additions: humour lives in short parentheticals ("(read smug)"), escalate a beat to a
  third instance, thrown-away pop-culture reference, orient the reader with an appositive before
  naming a third party, coach directly ("Try to remember,"), headings as spoken questions,
  conversational openers ("Well," "So,"). Two corrections: cut extended confessional asides but
  keep one-sentence factual candour, and the wry rhetorical-question close is for SHORT posts
  only — long technical pieces end on practical advice. Capped at one or two markers per
  paragraph; restraint is part of the voice.
- **2026-08-21 — LinkedIn article drafted on the self-improvement build.** Long technical version
  covering the six architecture decisions, the description-cap failure, four defects found in
  testing, and the Hermes / Nous / OpenClaw / sentrux landscape. Deliberately no firm or client
  detail and no drop-in files — shape only. Banner image generated
  (`self-improving-agent-banner.png`): ledger, terminal, one loop arrow, no text.

## 2026-09-01 - measurement honesty pass on the nightly tooling

Three figures in the self-improvement tooling were found to say something other than
what they appeared to say. The shared shape is worth naming: a number that READS as a
measurement without being one.

- `proposals_emitted` in the nightly report was a hardcoded `0` - one assignment, no
  update site anywhere in the tree, and a selftest asserting it equalled 0 which
  therefore could never fail. Printed beside a genuinely parsed `findings: 15`, it
  invited the reading that the analyser had proposed nothing, when in fact all 15
  findings WERE its proposals. DECIDED: delete the field (schema 2 -> 3) rather than
  compute it, since `findings` already counts them. The selftest now fails if it is
  reintroduced. 33/33 on the PC.
- `prose_only` counts entries whose Worked line names no runnable check. It does NOT
  measure reachability, so reading it as drift overstates the problem by more than
  half: of 64 prose-only entries, 36 carry a `Rule:` and reach every session through
  the digest. Only 28 were genuinely inert. Three of those were converted this session
  and the digest went 70 -> 77 rules.
- The dupe gate was blocking for a reason it never stated. Root cause is upstream of
  lesson_dupe: `lesson_check.parse` builds fields with `setdefault`, so only the FIRST
  `Distinct-from` line on an entry survives parsing. Now reads every line from the
  entry body, with whole-token key matching so a longer key cannot dispose of a
  shorter one that is its prefix.

**OneDrive conflict copies - settled.** The 15:27:27 client restart did NOT create
them. 67 of 88 were created locally at 15:27:59-15:28:00, a two-second burst that is a
download; but all 88 carry content stamped 08:02-08:09 that morning and 21 were already
on disk from 08-31. The creating event was the morning burst, not the restart. All 88
are quarantined to `C:\Users\YOURUSER\CoworkQuarantine\2026-09-01-conflicted` with a
manifest - OUTSIDE the repo AND outside OneDrive. The 2026-08-21 precedent quarantined
into `COPILOT_COWORK\Outputs`, which is inside the repository and is exactly the
mistake `quarantine-destination-inside-the-repo` names; do not reuse that script's
destination.

**Job hygiene.** Eight spent 2026-09-01 one-offs archived as tracked git renames.
`restart-onedrive` was KEPT deliberately, against the original list of four to keep,
because the standing rule on `onedrive-placeholder-cannot-hydrate` now tells a session
to restart the client first - archiving it would leave that rule with nothing to call.

## 2026-09-02 - the close gate deadlocked on its own repair

`gamma tango close` step 0 failed on ALL FOUR surfaces with `G3 digest counts match but the
body does not`. The diagnosis and the way through are worth keeping, because the shape will
recur every time a lessons entry is touched.

- **The drift was ONE line.** A hit counter had been bumped on a lessons entry without
  regenerating, so the digest copy in `copilot-instructions.md` still carried the old count
  and sorted that rule two positions low. G3 compares the block against a fresh
  regeneration, so a single stale counter fails EVERY surface at once. A global-looking
  failure with a one-line cause invites a far bigger diagnosis than the evidence supports -
  read the diff before theorising.
- **The deadlock.** The fix the failure itself names, `digest_apply.py`, cannot write
  `/mnt/user-config/` - it is a read-only mount. The write path that CAN reach the file is
  the 8932 bridge, and step 0 forbids a bridge call until the bridge preflight SUCCEEDS.
  The repair sits behind the door its own failure locks.
- **The way through.** Compute the repair on a WRITABLE scratch copy under `working/`; diff
  old against new to prove nothing was dropped; re-run `preflight` against the repaired copy
  into a SEPARATE receipt directory - all four exit 0 proves the repair WITHOUT minting a
  receipt that would falsely attest to the real file; then apply the difference to the PC
  through 8932 `edit_file`, `dryRun: true` first to confirm the anchor matches.
- **Afterwards the mount keeps serving the OLD file for minutes.** Hash it against the
  pre-repair copy - identical means sync lag, not a failed write. Do not read that second
  exit 1 as a fresh failure.
- **Editing a lessons entry that carries a `Rule:` line changes the digest again**, so the
  regenerate-and-push step runs TWICE in any close that logs a new rule. Budget for it.
- The guardrail override was put to Jordan as an explicit choice rather than taken
  unilaterally; he chose "fix it, then close".

## 2026-09-03 - lessons now ship INSIDE the skill that owns them, generated not copied

Jordan's framing: bake the lesson into the application rather than expecting a session to
adhere to it. Measured position before the change: 87 of 117 entries carried a Rule and
reached the always-on digest; the `skills` surface reached only 46%. `command-bridge` was
the ONLY skill carrying any lessons at all - four, hand-written.

**Why a generator and not a migration.** Hand-copying rules into eleven SKILL.md files is
the version that rots - four surfaces once stated the same OneDrive rule and all four were
wrong together (`config-contradiction-survives-in-second-file`). So each skill now carries
a marker-delimited block REGENERATED from `cowork-lessons.md`:

    skill_lessons.py           regenerates the block in each SKILL.md   (--check = read-only)
    skill_lesson_routes.json   which Pattern-Key belongs to which skill
    skill_lessons_backlink.py  writes the Delivered-to pointer back into the entry

A key MAY route to several skills - a rule about writing .bat files matters to the skill
that writes them and the one that runs them. That duplication is safe here and only here,
because the copies are generated from one source and cannot disagree.

**80 of 117 entries now route to 11 skills.** command-bridge 4 -> 24 rules;
local-file-bridge 0 -> 19; dream-cycle 0 -> 12; git-bridge 0 -> 10. The other 37 stay
general - they are not subsystem-specific.

**`Delivered-to` is deliberately NOT `Promoted-to`.** Promotion means a rule reached a
surface that ALWAYS loads. Delivery means it reaches a session only if that skill loads.
Collapsing the two is exactly the 2026-09-01 failure where ENFORCED rules were dropped
from context while `job_lint` read only `.bat` and `.cmd`. The generated block says
DELIVERED, not enforced, in its own text.

**Wired into the nightly pass.** `dream-cycle` now runs `skill_lessons.py --check` beside
`lesson_gate audit` - the same currency question, one tier down. A stale block is a
FINDING, not FAILED INTEGRITY: the data is sound, a generated copy has just not caught up.
Exit 2 (could not run) IS FAILED INTEGRITY. The check opens the 11 named SKILL.md files,
one path each, and must never become a tree walk - that would hydrate the OneDrive tree.

**The nightly pass had stopped running.** Found while wiring this up: no dream report
existed for 2026-09-01, and `GetScheduledPrompts` returned none. The mechanical half (the
Windows task) does run, but fires ~6.5h late on battery because "Allow wake timers" is
disabled on DC and vetoes `WakeToRun`. A scheduled prompt now exists for 02:30 daily; its
first run produced `dream-reports/2026-09-03.md` and found four real memory
contradictions, all applied the same evening.

## Open Threads / Next Steps
- [ ] Inert lesson entries - no `Rule:`, not promoted, no runnable check. Two of the
      highest-value ones were converted 2026-09-01 evening:
      `config-contradiction-survives-in-second-file` (the meta-rule governing every
      multi-surface fix, and it was itself unreachable) and
      `file-edit-reencodes-existing-characters`. Digest 77 -> 79.
      NOTE ON THE COUNT: an ad-hoc parse of "no Rule and not promoted" returns 32, not
      25. The difference is definitional, not drift - the report also requires "no
      runnable check". Do not quote either number as authoritative without saying which
      definition produced it.
- [ ] MEASURED 2026-09-01 at the close, NOT fixed - the section discipline is only
      half-enforced. Five entries sit under `## Contradictions` carrying
      non-contradiction triggers: `git-renaming-is-not-sanitizing`,
      `onedrive-recursive-scan-hydrates-tree`, `verifier-usage-error-reads-as-finding`,
      `artifact-rollback-overwritten-on-rerun`, `artifact-deadness-needs-consumer-grep`.
      `lesson_check`'s misfiled_contradiction test runs ONE WAY only - it found 0
      contradiction entries sitting outside the section and cannot see the 5
      non-contradiction entries sitting inside it. Same shape as the ENFORCED finding
      logged the same evening: the guard is narrower than the rule it stands for.
      Three of the five also use the trigger value `near-miss`, which is not in the
      self-improvement trigger table, and nothing validates trigger values at all.
      Decide three things: move the five, add the reverse direction to the checker,
      and either adopt `near-miss` into the table or remap it as `better-method` and
      `false-failure` were remapped.
- [ ] Decide the remaining dream-cycle proposals: 4 cross-surface merge candidates (all
      low confidence - judge, do not merge on the score), 4 relative-date "today" anchors
      to resolve to each entry's own Date, and 3 `.bak` files in cowork-memory that git
      already versions.
- [ ] `2026-08-21-quarantine-conflicted.ps1` went to `CommandJobs\Archive` while its
      `.bat` wrapper was retired on 08-31 to `Downloads\COWORK_QUARANTINE`. Neither can
      run, so the safety property holds either way, but the PAIR is split across two
      locations. Decide one convention for retiring a job rather than leaving two.
- [ ] Consider raising the broken instructions load path with IT/tenant admin.
- [ ] For GO.bat auto-start: add `"task.allowAutomaticTasks": "on"` to **User** settings
      (VS Code ignores it in workspace settings).
- [ ] Change both tasks from `"reveal": "silent"` to `"reveal": "always"` — silent hid a
      failed server start and cost about an hour.
- [ ] Deferred: build the billing skill.
- [ ] Not started: Power Automate workflows.

### Closed 2026-09-01 (evening)
- **DONE - the lesson gate's read-only receipt path.** Fixed at the source, not worked
  around: the receipt write is guarded and returns **2 (could not run)** instead of 1
  (stop), so an environment fault can no longer read as a rule failure and halt a close.
  `--receipt-dir` defaults through `default_receipt_dir()`, which preflight and verify
  BOTH call, so the two cannot resolve differently. The cwd-relative branch is FIRST
  among the automatic choices deliberately - a shared absolute default would let one
  selftest case's receipt satisfy the next case's "no receipt" assertion, and the
  sabotage cases would stop firing while still printing PASS. All three surfaces that
  state the path now agree. Selftest 28/28, and the new case fails ALONE at rc=1 against
  the pre-fix script. Commit 66c13b6.
- **DONE - 8932 `search_files` semantics, previously "mechanism not established".** It
  glob-matches against the path RELATIVE to the search root; it is not a substring
  search. Two independent silent-empty modes: a pattern with no wildcard never matches a
  longer filename, and `*` does not cross a directory separator. Use `**/*term*`. Proved
  against a known ground truth - the exact literal basename of a file that demonstrably
  exists returned "No matches found", and `**/<name>` found it. The lesson's Why is no
  longer marked inference-unverified.
- **DONE - the 2026-08-21 quarantine script that targeted inside the repo.** Archived to
  `CommandJobs\Archive` as a tracked rename rather than fixed, because the 2026-09-01
  successor already does the job correctly. Its consumer grep found that the 08-31
  retirement had moved the `.bat` wrapper and left this `.ps1` behind - a half-finished
  retirement, which is why the file was still there to be flagged.
- **VERIFIED at the close, by re-running rather than by reading the write-up.** Gate
  selftest 28/28 including the exit-2 case and the `default_receipt_dir()` case;
  `lesson_check` exit 0 across 110 entries, 0 FAIL 0 WARN; `digest_apply --check` reported
  `already current: 79 rules from 110 entries`; and a scoped grep of the three files that
  state the receipt path confirmed none still names the read-only mount. All four close
  preflights - bridge, git, memory, files - exited 0 and wrote receipts.
- **NEW, and it happened DURING this verification: `onedrive-recursive-scan-hydrates-tree`
  took hit 2.** The rule was live in the digest and had just been printed by the `files`
  preflight minutes earlier, and was missed anyway - it said "inside a job", so a
  session-side `grep -rn --include=*.md` over `/mnt/user-config` read as a different act.
  It hung and was killed unfinished; the same question, asked of the three named files,
  answered at once. Widened rather than re-promoted: when a rule is READ and still missed,
  the defect is the scope of the sentence, not its delivery path. That is now the second
  rule in two days to fail that way - `deferred-tools-read-as-absent-bridge` took hit 3 on
  2026-09-01 for the same reason, its wording unfollowable in the case it targeted. Worth
  watching as a pattern: the digest solves reach, and reach was never the whole problem.

## Preferences & Constraints
- Every SKILL.md must include `Created by: Jordan Rash` in its frontmatter `metadata:` block.
  No exceptions.
- Separate facts from inferences, and flag anything that needs Jordan's review.
- Be direct and concise; lead with the answer, then the detail.
- Confirm before any irreversible action (sending email, posting to Teams, deleting).
- Prefer the local bridge whenever a request references a `C:\` path, "my PC", "locally", or
  the COPILOT_COWORK / Downloads folders. Never silently fall back to the cloud workspace.
- Report the exact absolute Windows path after writing.
- Prefer `edit_file` over `write_file` for existing files — it fails safe; `write_file`
  overwrites silently and there is no delete tool.
- **Do not over-verify.** Long tool-call chains are frustrating. Act on the most likely path;
  batch checks; do not re-confirm what is already known.

## Key Exchanges
- 2026-07-27 — Goal: stop having to name tools every session; make bridge routing the default.
- 2026-07-27 — Two wrong diagnoses were given during bridge troubleshooting (`--stateful`,
  then the `BACK UP` folder) before the real cause was identified. Verify against evidence
  before asserting a cause.
- 2026-08-18 — Same lesson recurred: the monitoring was blamed for an outage the logs showed
  it did not cause, and the bridges were declared dead while they were up.

## 2026-09-03 — Lesson delivery reached the PLUGIN tier, and got a verification arm

**Third delivery surface.** Lessons already routed to skills (`skill_lessons.py`).
They now also route to PLUGIN TOOL DESCRIPTIONS via `plugin_lessons.py` +
`plugin_lesson_routes.json`, same safety contract: writes only between markers,
refuses if anything outside changes, `--check` exits 1 on drift, exit 2 = refused.
Wired into `dream-cycle` (manifest + Routine step 2 + a `Plugin blocks:` report
line); `manifest_check` passes.

- Live on `run_batch_file` (5 rules, 972 b, 81% of budget) and `evaluate_expression`
  (1 rule, 568 b, 63%). Both proven by a stdio handshake against the running server,
  not by `node --check` — parsing and serving are different claims.
- **Only 8933 and 8934 are eligible.** 8931/8932 launch from `npx`, so an edit lands
  in `node_modules` and is overwritten on next start. Their rules stay in the
  companion skills.
- **Budget matters here in a way it does not for skills.** A skill block costs
  context only when the skill loads; a description costs EVERY session with the
  plugin connected. Prefix routing (fine for skills) filled 95% of the 8933 budget
  with rules about BUILDING a bridge. That route is now exact-only and curated.
- Markers are placed BY HAND once, reviewed. The applier refuses to insert them —
  guessing an insertion point in arbitrary JavaScript is not a safe auto-operation.

**Verification arm** — `verify_delivery.py` (plan / judge / explain) +
`verification_cases.json` + selftest (29/29, mutation-verified). Ledger lives in
`cowork-memory/verification-ledger.json`. FOUR arms, not three: three carried runs
plus a CONTROL, because a pass rate with no control is not a measurement. Verdicts:
`EFFECTIVE`, `INERT` (model already knew — reclaim the bytes), `UNRELIABLE`,
`INEFFECTIVE`, `INVALID`. Fingerprint covers case AND rule text, so amending a rule
invalidates its stored verdict. **It never proposes removing anything from the
corpus** — Jordan settled that: delivery is not promotion.

First verified lesson: `bridge-8934-evaluate-rejects-safe-navigation` = EFFECTIVE,
3/3, control failed. But the harness's FIRST act was to prove the rule WRONG — it
named only the `?[]` refusal and missed the `@`-prefix gate, where unprefixed input
is echoed back with `evaluated_locally: true`. Following the rule as written led
from a loud refusal to a silent wrong answer. No `--check` could ever find that.

**Three verifier failures in one session, same class.** A gate asserted a literal
copied from the rule — first a phrase from the TITLE, then wording that was amended
20 minutes later, then a Pattern-Key against a digest that carries rule TEXT and no
keys at all. Each failed confidently and two reverted correct installs. Fix in all
three: DERIVE the expectation from the corpus at check time. See
`verifier-asserts-a-literal-copied-from-the-rule` (promoted, verified present in
both destinations).

**The close-gate digest deadlock recurred, with a new cause.** Adding a lesson made
the digest stale, so `preflight` failed all four surfaces — but this time the
authoritative file was already correct and the READ-ONLY MOUNT was 19 hours behind
(21187 bytes, mtime 01:47Z, still advertising 120 entries while the corpus showed
121). The lessons file had synced; `copilot-instructions.md` had not. Repair is the
documented one: stage a fresh copy of the live file into `/mnt/workspace/` and point
`--instructions` at it. Measure the mount before blaming the digest.

## Reference Links & Files
- `plugin_lessons.py`, `verify_delivery.py` — `Documents/Cowork/Skills/self-improvement/scripts/`
- Verification ledger — `Documents/Cowork/cowork-memory/verification-ledger.json`
- `local-file-bridge` skill — `/mnt/user-config/skills/local-file-bridge/SKILL.md`
- `persistent-memory` skill — `/mnt/user-config/skills/persistent-memory/SKILL.md`
- Personal instructions (correct but never loaded) — `Documents/Cowork/copilot-instructions.md`
- Bridge launcher + task config — `...\COPILOT_COWORK\Startup\GO.bat`, `Startup\.vscode\tasks.json`
- Related memory — `cowork-bridge-infrastructure.md`
