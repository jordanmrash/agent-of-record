# Memory: Cowork Bridge Infrastructure

- **Slug:** cowork-bridge-infrastructure
- **Created:** 2026-08-18
- **Last Updated:** 2026-09-02
- **Sessions captured:** 7

## Summary
The local MCP bridges (8931 Playwright, 8932 filesystem, 8933 command) are working and
hardened. A FOURTH - 8934 Power Automate - went live 2026-09-02 and is deliberately INERT
until an identity exists for it; see the 2026-09-02 section. A watchdog restarts dead ports automatically, supergateway is pinned locally,
8932/8933 run STATELESS, long synchronous jobs no longer kill 8933, and the COPILOT_COWORK
folder is under git.
The 2026-07-27 npx/quoting failure is long resolved. The unexplained ~5-minute terminal
flash was RETIRED 2026-08-24 at Jordan's direction — deprioritised, not diagnosed.

## 2026-09-02 (later session) - the tunnel question settled, and a stale copy found

**Dev Tunnels: there is nothing to switch to.** Asked whether moving from VS Code to MS
Dev Tunnels would make the bridges drop less - VS Code port forwarding IS Microsoft dev
tunnels. Same relay, same `*.devtunnels.ms` host, same 1-2% hop loss. The standalone
`devtunnel` CLI would change only the CONTROL surface: `devtunnel create -a` plus
`devtunnel access create TUNNELID --anonymous` makes anonymous access a persistent
property, which is the one thing that would end the manual four-port Public step. Moot -
Dev Tunnels is not approved software at the firm (see `tooling-install-researched-before-approval-checked`)
and the CLI is public preview with no SLA. Do not re-open this.

**Merging the four bridges behind one port was proposed and is REJECTED.** 8931 runs
`--stateful --sessionTimeout 1800000` for the Playwright Edge SSO profile lock; 8932, 8933
and 8934 must run stateless. One supergateway process carries ONE flag set, so a merge
forces a choice between breaking SSO and reintroducing the idle-expiry drop. It would also
collapse the watchdog's per-port restart and the whole `bridge_policy` table, which depends
on 8933 being separately addressable. Independent per-port failure is a FEATURE, not a defect.

**The watchdog DOES cover 8934.** `_bridge-watchdog.ps1` `$Bridges` lists all four ports
with correct per-port flags, and `watchdog\status.txt` showed all four UP. The header
comment in `tasks.json` still claimed the watchdog "was written for three ports"; that
comment was stale, was believed over the code, and produced a false report to Jordan of a
live availability gap. Comment corrected in commit 29bda90.

**KnownGood was stale by an entire bridge.** `Startup\KnownGood\tasks.json` had not been
touched since 784dc9f (2026-08-21) - before c2d1e37 brought 8934 online. Running
`bridge-restore-tasksjson.bat` would have restored a THREE-bridge `tasks.json`, silently
deleting the Power Automate bridge while reporting success. Resynced and proven
byte-identical in 29bda90. Second hit on `bridge-recovery-scripts-revert-config`, which now
carries a Rule line.

**A CONCURRENT SESSION was committing to this repo the whole time - that is the answer.**
First it looked unexplained: commit 29bda90 contained only the KnownGood copy even though
`git add` named both files, and `git log -- Startup/.vscode/tasks.json` reported 2307cd6 as
that file's last commit, yet `git show HEAD:` proved the correction WAS committed and the
tree clean for it. Then HEAD moved on its own - 29bda90 -> 83454f5 "Finish the three
untested claims, and clean up the one that bit back", a message this session did not author
- and that commit had swept up this session's untracked `.bat` files and the modified
`Startup/FlowBridge/flow-mcp-server.js`. The mechanism: another Cowork session running
`git add -A` picked up the live `tasks.json` edit and committed it inside 2307cd6 BEFORE
this session's job reached its own `git add`, which is why that `git add` found nothing to
stage for that path. Evidence: measured for the HEAD move and the file-state changes;
INFERENCE UNVERIFIED for attributing 2307cd6's contents to the other session's `add -A`.

**Operational consequence:** COPILOT_COWORK has no concurrency control, and `cowork-close` runs
`git add -A`. Two sessions closing at once will cross-commit each other's working files
with no warning and no conflict. Check `git log -1` immediately before proposing a close
commit, and treat a HEAD that moved since the session's own last commit as a signal that
another session is live.

## 2026-09-02 - a FOURTH bridge (8934, Power Automate) is live, and inert on purpose

The Power Automate bridge was installed as a Cowork plugin from the `PLUGINS` folder,
switched on beside the other three, and answered `bridge_status` from a FRESH chat. That
single answer proves the whole chain end to end: PC -> devtunnel -> new bridge -> Cowork.

- Namespace `jordan-power-automate-8934-v1`; server `Startup\FlowBridge\flow-mcp-server.js`;
  config `flow-bridge.config.json`; audit log under `CommandJobs\Logs\`.
- `bridge_status` reports config loaded, `auth_strategy: none`, `auth_configured: false`,
  `read_only: true`, `allow_delete: false`, and ZERO allowed environments or prod
  environments. **That is the SUCCESS state, not a failure** - the bridge is alive and
  correctly refusing every flow tool until an identity is wired up.
- ~~The watchdog does NOT cover 8934.~~ **CORRECTED 2026-09-02** - it does, and it did at
  the time this line was written. See "The watchdog DOES cover 8934" earlier in this file:
  `_bridge-watchdog.ps1` lists all four ports. This line survived the correction and stood
  as a second, contradicting copy inside the SAME file for several hours
  (`config-contradiction-survives-in-second-file`).

### The auth wall - what actually blocks flow CRUD
- The bridge holds no identity of its own, so every flow tool refuses up front.
- PAC CLI cannot lend it one: `pac auth token` works in the stripped job env, but its
  audience is FIXED at `api.powerplatform.com` - the ADMIN plane. Dataverse and
  `api.flow.microsoft.com` both answer 401, and the command takes no resource argument.
- **MEASURED 2026-09-02: the tenant's Conditional Access blocks device-code sign-in.** Signing in to
  the Microsoft Graph Command Line Tools client returned "Your sign-in was successful but
  does not meet the criteria to access this resource... restricted by your admin." The
  credentials were fine; the ROUTE was refused. **The implication drawn here - "any 8934
  design in which a local script acquires a token on Jordan's behalf is likely dead at this
  tenant" - was DISPROVEN 2026-09-02.** Conditional Access blocks the DEVICE-CODE grant
  specifically, not delegated sign-in as a class. Authorization-code + PKCE on a loopback
  redirect passes cleanly and is what the bridge runs on today. A measured block on one
  grant type was generalised into a verdict on all of them.
- Do NOT read the follow-on Graph `401 InvalidAuthenticationToken / ArgumentNull` as a
  permissions verdict. No token was ever issued, so the request carried an empty `Bearer`.

## 2026-09-02 evening - 8934 reaches v0.4.0: it can now RUN flows, not just describe them

The bridge went 7 tools -> 17. The gap was never permissions; it was one missing token.

**Two APIs, one sign-in.** Flow DEFINITIONS live in Dataverse; RUNS, triggers and
connectors live on the Flow service. Both are reachable on the same delegated PKCE auth:

    definitions   Dataverse Web API, <org_url>          list/get/create/update/delete/state
    runs          https://api.flow.microsoft.com        run/history/actions/cancel
    connections   https://api.powerapps.com             which connectors are authorised

**AAD refresh tokens are NOT resource-bound.** The token cached for the Dataverse org URL
was exchanged silently for both `service.powerapps.com` and `service.flow.microsoft.com`.
So a three-audience bridge needs ONE interactive sign-in, ever. `getToken` now tries every
other cached refresh token before it will open a browser.

**Three address traps, each of which reads as a permissions or support failure:**

- The AUDIENCE `service.flow.microsoft.com` has no DNS record. The HOST is
  `api.flow.microsoft.com`. Aiming at the audience gives `ENOTFOUND`, which is what
  produced the wrong "unsupported API" verdict recorded earlier in this file
  (`api-audience-is-not-a-hostname`).
- The Flow service calls the default environment `Default-<guid>`. The bare guid returns
  `403 EnvironmentAccessDenied` - a permissions error for an addressing mistake.
- Connections are NOT nested under an environment path on either host. They are a flat
  collection filtered by environment, on api.powerapps.com, and the `$filter` is required
  on EVERY verb including DELETE - omitting it returns 400 rather than deleting nothing
  loudly, which silently left a probe connection behind.

**Proven end to end, no manual step:** create -> start -> run -> read history -> read
per-action detail -> cancel a run in flight -> delete, each verified by re-reading rather
than by trusting the call's own success report. A connection CAN be created by API for a
connector needing no credentials (RSS, 201 Connected); OAuth connectors still need a
browser consent no API can mint.

**Against Flow Studio's live tier: roughly 9 of 16 tools matched, 2 partial, 5 missing.**
Missing that matter: per-action INPUTS and OUTPUTS (mine reports which step failed, not
with what data) and dynamic option resolution for authoring against Teams/SharePoint. 8934
is ahead on delete (they deliberately have none) and on governance - explicit production
flags, per-environment read_only, full audit of every mutating attempt including refusals.

### Non-admin paths that already work - do not assume admin is required
Delegated access can never exceed Jordan's own rights, so the question is not "is he an
admin" but "which surface reaches those rights most cheaply". Admin is strictly needed only
for the bridge to act UNATTENDED, as itself.
1. **PAC CLI plus solutions - proven, zero admin, zero consent.** No `pac flow` group, so no
   list/run/enable/disable; but flows ARE solution components - export and unpack reads,
   pack and import writes. Ceiling: export is all-or-nothing (one unreadable flow kills the
   whole export) and a production environment denies solution listing outright.
2. **App registration** - two gates that get conflated: CREATING the registration (a tenant
   setting, often left open to all users) and CONSENTING to its permissions (usually admin,
   and near-certain to be admin at a tenant that blocks device code). Even with both open,
   the ceiling is the same as path 1.
3. **Browser automation in Jordan's own signed-in session** via the 8931 bridge - no
   registration, no consent, and it reaches what the token paths cannot: the maker UI,
   flow on/off, run history. Brittle, and worth a firm-policy check first.

Rejected on purpose: piggybacking on Microsoft's pre-consented first-party client IDs to
obtain a token that was never granted. It sometimes works, and it ends badly with IT.

## 2026-08-28 - the bridge now carries its own operating rules

`batch-exec-server.js` is v1.2.0. Two additions, both additive, neither touching
validation or execution.

1. `TOOL.description` carries the four rules about USING the bridge: the parameter
   is `file` not `path`, a .bat written through 8932 arrives LF-only, check whether
   a job already ran before retrying after a transport error, and drops are the
   devtunnel hop rather than this server.
2. The `tools/call` response appends an OPERATING RULES block, read LIVE from
   `cowork-lessons.md` (all `bridge-` and `git-` keys carrying a one-line `Rule:`,
   ranked by Hits, top 8). No digest to regenerate and it cannot go stale.

**When it fires.** Any job that does not exit clean ALWAYS gets the rules, because
that is when a bridge failure is about to be misdiagnosed. A clean job gets them
once per 45 minutes. Verified live in all three states.

**Two things measured during the build, both of which corrected a belief.**

- **Stateless defeats in-process state.** supergateway spawns a FRESH node process
  per request, so the first throttle (a module-level boolean) did nothing at all -
  two consecutive jobs both reported "first job of this session". State now lives in
  `CommandJobs\Logs\_last-operating-rules.txt`.
- **A server edit goes live on the NEXT call, with no restart.** The same statelessness
  re-reads the file every request. Deployment costs nothing and disturbs no session,
  but there is no staging step between editing and production, so gate any change
  behind `node --check`, a `.bak`, and a throwaway-instance handshake test.

**Scope limit, stated inside the reminder itself.** These rules cover USING the
bridge. A bridge that appears ABSENT cannot be addressed this way, because in that
failure the tool is never called. That rule lives in `copilot-instructions.md`.

Rollback: `batch-exec-server.js.pre-rules-20260828.bak`. The file is tracked in git;
the change is commit `e45c4c0`.

8932 and 8931 got nothing. They are npm packages, so their server code is not worth
editing. The connector-level plugin description is the lever there, and it is unused.

## Key Facts

### Bridges
- Ports: 8931 Playwright, 8932 filesystem, 8933 command (`run_batch_file`), 8934 Power
  Automate (`bridge_status` plus six flow tools, all refusing until an identity is wired
  up; the watchdog does NOT cover this port).
- A healthy bridge returns HTTP 400 to a plain probe. 400 is the GOOD baseline, not an error.
- The 8933 bridge runs only an existing `.bat`/`.cmd` under `CommandJobs`, by relative path.
  No command string, arguments, interpreter, working directory, or elevation.
- Bridge-allowed directories (THREE since 2026-08-24, commit `a6297b6`):
  `C:\Users\YOURUSER\Documents\COPILOT_COWORK`, `...\Downloads`, and
  `C:\Users\YOURUSER\OneDrive\Documents\Cowork`.
- **The third root does NOT remove the OneDrive sync wait.** It changes what the bridge may
  REACH, not how OneDrive replicates. Cloud-side writes still take many minutes to reach the
  PC; only a write made DIRECTLY to the local path is visible to the repo in the same session.
  Write memory and lessons files there, not cloud-side.
- **Job environment (refined 2026-08-20):** PARTIALLY stripped, not empty. User-profile vars
  (`%LOCALAPPDATA%`, `%APPDATA%`, `%USERPROFILE%`) expand to nothing — hard-code absolute
  paths for anything under a profile. But **PATH is intact**: System32, PowerShell, Git,
  node and Python all resolve, so bare interpreter names are fine. What is NOT inherited is
  the WORKING DIRECTORY — `cd /d <repo>` stays mandatory at the top of every job.

### Watchdog (built 2026-08-18)
- Scheduled task `CoworkBridgeWatchdog` runs `Startup\_bridge-watchdog.ps1` every 2 minutes.
- It TCP-probes each port with a 1s timeout and restarts ONLY refused ports. It never kills.
- **Per-port flags (2026-08-21, commit 9f55bda):** the watchdog restarts each bridge with the
  flags that bridge's tasks.json entry declares - 8931 stateful, 8932/8933 stateless. It used
  to hard-code --stateful for all three, so any restart of 8932/8933 silently reverted the
  stateless fix. It now logs STATEFUL/STATELESS on every restart so drift is visible.
- 300-second cooldown per port prevents flapping. Status: `Outputs\2026-08-18 - Bridge
  Hardening\watchdog\status.txt`; history in `watchdog.log`.
- Registered with `-AllowStartIfOnBatteries` — schtasks defaults make a task a silent no-op
  on this laptop when unplugged (reports Last Result 0 with zero output).
- An `-AtLogOn` trigger requires elevation and cannot be registered; the repeating trigger
  plus `-StartWhenAvailable` survives reboots instead.

### Recovery behaviour (verified end to end)
- A bridge death costs only the CURRENT chat. The MCP session is bound to the dead PID and
  cannot re-initialize mid-conversation.
- A NEW chat connects straight to the watchdog-restarted process — no GO.bat, no re-setting
  ports to Public. Confirmed after the deliberate kill test.
- **A DISABLED PLUGIN is a third cause class — check it FIRST (2026-08-26).** A session opened
  specifically to pick the bridges back up probed three ways — broad regex, tool-name regex,
  and the exact names `list_allowed_directories` and `run_batch_file` — found no bridge
  namespace, and concluded the PC side was down (VS Code / GO.bat / Ports panel). **That was
  wrong.** The Cowork PLUGINS had simply been switched off. Jordan turned them back on and all
  fourteen 8932 tools plus `run_batch_file` registered inside the already-running chat, both
  answering on the first call. Nothing was ever wrong with the machine.
- **The tool surface is not immutably fixed at session start.** Re-enabling a connector
  registers its namespace MID-SESSION, exactly as disabling one removes it. The absolute
  wording "a bridge absent at start will not appear later in that same chat" is too strong —
  it holds for a bridge PROCESS started mid-session, not for a connector toggled back on.
- **Diagnostic order when a bridge tool is missing:** is the plugin enabled in Cowork? → are
  the listeners up and the Ports panel rows Public? → has the tunnel re-established? Only
  after all three should a session characterise the PC as the fault.
- A "couldn't be reached" error is often a transient drop, not a dead process. Check
  `status.txt` before assuming the worst — on 2026-08-18 a session declared all three
  bridges dead while all three were in fact UP.

### The LF/CRLF constraint (important)
- Files written through the 8932 bridge arrive LF-only. cmd mis-parses LF-only `.bat` files
  — not just `call :label`, but silent early exits that write nothing and look like success.
- Fix: run `CommandJobs\2026-08-18-fix-crlf-all.bat` after ANY batch of writes. It covers
  `CommandJobs\*.bat` plus `Startup\*.ps1` and skips itself.
- PowerShell is immune to LF. Prefer `.ps1` with a thin `.bat` wrapper.
- Confirmed again 2026-08-18: a freshly written `.bat` needed normalizing before it would run.

### Session statefulness (2026-08-21 - current config)
- Only **8931** runs `--stateful --sessionTimeout 1800000`; it needs a persistent child to hold
  the Playwright Edge SSO profile lock, and must never get `--isolated` or SSO is lost.
- **8932 and 8933 run STATELESS.** The 30-minute idle expiry silently dropped all three tool
  surfaces mid-session while every process stayed alive, and stateful measured a 16% call-drop
  rate on 8932.
- **The 16% is HISTORICAL — it describes the OLD stateful config and is not the current rate.**
  Post-stateless measurement is **0% local / 1-2% tunnel** (see Transport reliability below).
  Never quote 16% as a live figure; quoting it has already led to diagnosing a bridge fault
  where the real layer is the devtunnel hop.
- A tasks.json edit does NOT go live on a plain VS Code restart - GO.bat does not kill existing
  listeners. Kill the listener PIDs, close VS Code, relaunch, and prove it by PID turnover.
- Three files must agree: `Startup\.vscode\tasks.json`, `Startup\KnownGood\tasks.json` (what
  `bridge-restore-tasksjson.bat` restores from) and `Startup\_bridge-watchdog.ps1`. A stale
  recovery copy silently undoes the fix at the worst moment. Verify with a printed flag matrix.

### Long-running jobs (revised 2026-08-21)
- **The long-job kill is FIXED by running 8933 stateless.** Measured: a 137.5s job and a 93.1s
  job both ran SYNCHRONOUSLY to exit 0 with full stdout, and 8933 survived on the same PID.
  The earlier belief that jobs over ~60s inherently kill the bridge was a stateful artefact.
- `_async-launch.ps1` + Task Scheduler still works and is still preferable for genuinely long
  or unattended work, but it is **no longer mandatory** above ~60s.
- The 8933 executor waits on the whole PROCESS TREE, not a stdout pipe. Redirecting handles
  does NOT let a long job return early - a 15s worker still reported ~15.9s.
- Exit-code contract verified: a worker emitting `COWORK_RESULT: FAIL` writes `STATUS=DONE
  EXIT=1`; re-running a job whose `_job-state.txt` reads `STATUS=RUNNING` is refused with
  exit code 3.

### Transport reliability (measured 2026-08-21)
- 400 requests, 100 per endpoint: local loopback dropped **0%** on both 8932 and 8933
  (avg 1ms / 0ms). The devtunnel public URL dropped **2%** on 8932 and **1%** on 8933, every
  failure an operation timeout (avg 125ms / 134ms).
- So the bridge processes drop nothing - the tunnel hop loses 1-2%. A "couldn't be reached"
  is a transport hiccup. Check `status.txt`, then a single informed retry.
- Do not read a handful of failures on one port as that port being faulty; 2-vs-1 at n=100
  is noise. Probe and CSV: `CommandJobs\2026-08-21-droprate-8932.ps1`, commit 1e983e5.

### Verified live state (2026-08-21 20:51Z - bridge-health + real round-trips)
- Listeners: **8931 = PID 31784, 8932 = 34812, 8933 = 51816**. 8931/8932 are the PIDs from
  the 23:04 clean restart; 8933's is NEW because its VS Code task found the port free and
  bound it. Local probe 400 / 400 / 405.
- **The devtunnel URLs now ALL answer** (400 / 400 / 405). This CORRECTS the standing
  "8932 devtunnel is dead" open item, which was repeated twice this session from stale
  memory before anything was probed. Re-probe a stored "X is broken" item before repeating it.
- Verified by USE, not just probes: 8932 did a write-then-read round trip, 8933 ran two jobs
  exit 0, 8931 returned its tab list. 8931's first call failed "couldn't be reached" and
  succeeded on one retry — the expected 1-2% tunnel loss, not a sick bridge.
- 8931 `--stateful` present, `--isolated` absent, no stale SingletonLock, all 7 key files OK.

### Red VS Code task terminals are duplicates, not dead bridges
- On folder open, VS Code re-runs the bridge tasks. Any port already served loses with
  `EADDRINUSE`, that task exits 1, and it shows **red with an error badge** in the terminal list.
- **Red = the duplicate died; the bridge is fine.** Do not click the ⊗, do not re-run the task,
  and above all do not kill the port holder — that drops a live bridge mid-session.
- Diagnostic: the task that starts CLEANLY is the one whose bridge was actually down.

### Fallback path - THERE IS NONE (authoritative)
- **If 8933 is unreachable, STOP and report the connection failure.** Do not write to
  `COPILOT_COWORK\autorun\queue`, do not invoke `AUTORUN.ps1`, and do not substitute any other
  execution runtime. This is Jordan's settled ruling and overrides any earlier note describing
  autorun as a fallback.
- The Autorun watcher task was REMOVED from tasks.json on 2026-08-21 (commit 784dc9f) so the
  path is no longer armed on folder open. `AUTORUN.ps1` remains on disk and can be run by hand.
- Capability note only: AUTORUN.ps1 picks a `.ps1` from the queue in ~2s and logs to
  `autorun\logs`. This is documentation, not permission.

### Port visibility (confirmed 2026-08-21)
- Ports 8931/8932/8933 revert to **Private** on every VS Code restart and must be set Public
  in the Ports panel by hand. This cannot currently be automated.
- `devtunnel.exe` is genuinely ABSENT - re-probed with hard-coded paths plus a full AppData
  sweep. The original probe searched `%LOCALAPPDATA%`/`%USERPROFILE%`, which are blank in the
  8933 job environment, so its NOT FOUND proved nothing. Same answer, now actually evidenced.
### Version control (added 2026-08-18)
- Git 2.55.0.windows.3 was ALREADY installed at `C:\Program Files\Git\cmd\git.exe`.
  No install and no elevation were needed.
- Repo initialized at `COPILOT_COWORK`. Baseline commit `ff2e36e`, 75 files.
- Identity set LOCALLY in this repo only, never global. Nothing is ever pushed; local only.
- `.gitignore` excludes node_modules, `Outputs/`, autorun logs/queue, `*.log`, hand-made
  backups (`*.bak`, `*-backup`, `*.pre-*`), archives, and anything credential-shaped.
- Git does NOT track anything automatically. Only 14 stock `.sample` hooks exist, which git
  ignores. Every commit must be invoked. Watchdog and autorun activity is gitignored, so the
  repo is deliberately blind to it.
- **CORRECTED 2026-08-18 17:30** — the git-bridge skill no longer references port 8934.
  That server never existed. The skill was rewritten (6,593 → 10,396 bytes) so git runs as
  `.bat` jobs through the 8933 command bridge: author the batch, write it via 8932, run the
  CRLF normalizer, then `run_batch_file`. It carries an explicit "never call an 8934 tool"
  guardrail.
- **Remote: NONE, and the skill's strongest guardrail forbids adding one.** Repo is local
  only — no `git remote add`, no `push`, no `clone`. This means the repo is version control,
  NOT backup: history lives on the same disk with nothing to restore from. The skills
  themselves are separately protected because they live in OneDrive, which does sync.
- **2026-08-24 commits:** `a6297b6` (third bridge root; standing `cowork-close.bat` and
  `bridge-restart-8932.bat` added to the repo) and `50a425f` (the 8/24 memory and lessons
  updates, plus `git rm --cached` and a `.gitignore` entry for `CommandJobs/_commit-msg.txt`).
  `git status --short` empty after both.
- **Scan for client entity names before staging — the sync filter is inclusive by default.**
  `b08ad5b` (2026-08-20) widened the skills pass from `SKILL.md` to
  `*.md *.py *.js /S /XF *conflicted*`, taking the synced set from 24 files/446 KB to
  102 files/1.64 MB. That pulls engagement-flavoured content into `CoworkConfig\` —
  `je-builder` history and its mapping files, state-apportionment and
  <client>-apportionment scripts. `0d72b12` added `/XD` exclusions and `0c80eb1` deleted three
  client-identifying SKILL.md files, but because the filter admits by pattern rather than by
  allowlist, any future widening can re-introduce them silently. Read the staged file list
  before every commit. Deleting later does not undo it: the path is already in history and
  every clone still surfaces the client name (lesson `git-deletion-does-not-sanitize-history`).

## Decisions Made
- 2026-08-24 — A self-committing job must stage its PERMANENT self but never its EPHEMERAL
  inputs. `cowork-close.bat` was committing its own `_commit-msg.txt`; fixed by untracking and
  gitignoring the message file, NOT by editing the standing job — which preserves its
  never-rewritten property, so it never needs the CRLF pass.
- 2026-08-24 — Memory and lessons files are written to the LOCAL OneDrive path through the
  8932 bridge from now on, never cloud-side, so the repo sees them in the same session.
- 2026-08-21 — Close-out commit jobs must stage THEMSELVES as well as their targets, or each
  close leaves a new untracked job behind and the chain never ends. Proven by `8e096a3`.
- 2026-08-18 — Built the watchdog rather than relying on being physically present to re-run
  GO.bat, after 8933 died twice and blocked all work.
- 2026-08-18 — Pinned supergateway 3.4.3 into `Startup\node_modules` and pointed tasks.json
  at the local copy instead of `npx -y`, removing a registry dependency at startup.
- 2026-08-18 — Moved long jobs to Task Scheduler after the stdout-pipe theory was disproven.
- 2026-08-18 — Initialized git for the COPILOT_COWORK folder with a 400-file staging guard,
  so a bad `.gitignore` aborts before it can bake thousands of files into history.
- 2026-08-18 — Chose commit-around-edits discipline over an auto-commit scheduled task, to
  avoid adding machinery to a machine with an unexplained recurring process.

- 2026-08-20 — Approved GitHub for a PERSONAL account, PRIVATE repo, **tooling only**
  (`Startup\`, `CommandJobs\`, `CoworkConfig\`). `Outputs\` is excluded — deliverables are
  never pushed. Jordan did not confirm the approval covers firm work product, so the scope
  stays narrow deliberately. It must be a NEW repo with clean history: gitignoring `Outputs\`
  does not remove it from the existing COPILOT_COWORK commits, so pushing that repo would
  upload every deliverable ever committed. Pre-push requires a secret/client scan of
  `cowork-memory` and `tasks.json` (dev tunnel URLs are effectively access paths).

## Open Threads / Next Steps

- [ ] Explain why commit 29bda90 captured only `Startup/KnownGood/tasks.json` when `git add` named the live `.vscode/tasks.json` as well, and identify what else was writing to COPILOT_COWORK in that window. `cowork-close` runs `git add -A` and would sweep an unattributed change into the next commit.
- [ ] `Startup/FlowBridge/flow-mcp-server.js` is sitting modified and unstaged, from no known session. Decide whether it is wanted before the next close.
- [x] ~~OPEN 2026-08-26 — bridges DOWN, memory-folder writes uncommitted~~ — RESOLVED the same
      session. The bridges were not down: the Cowork plugins had been switched off, and
      re-enabling them registered both namespaces mid-chat. The commit ran normally after
      that. Two mechanics worth keeping: (1) the OneDrive DOWN-leg was fast this time — three
      cloud writes were on local disk within about six minutes, so the "tens of minutes"
      figure is a worst case, not a constant; verify with a `dir` rather than assuming either
      way. (2) `CoworkConfig\` was still a full day stale, and `git status` listed no memory
      file at all until `CommandJobs\2026-08-18-sync-cowork-config.bat` had run — the sync job
      is what makes a memory edit committable, and it is never optional.
- [x] ~~Commit the 8/24 memory and lessons files stranded cloud-side by `1d60874`~~ — DONE
      2026-08-24 in `50a425f`. The OneDrive client caught up on its own; no hand-placement
      was needed, matching the 2026-08-20 precedent.
- [x] ~~Two write-path instructions are STALE~~ — FIXED 2026-08-24 on Jordan's approval, and
      it was FOUR surfaces rather than two: `copilot-instructions.md` (the "exactly two
      directories" claim and the "NOT reachable by the bridges" paragraph),
      `self-improvement` SKILL.md (environment block + Write row), `persistent-memory`
      SKILL.md (write path, confirm step, guardrail), and `git-bridge` SKILL.md (the
      `add -A` disagreement, plus a new ephemeral-inputs guardrail).
- [x] ~~Promotion candidate — `onedrive-cloud-to-laptop-lag` reached Hits 2~~ — PROMOTED
      2026-08-24 to `copilot-instructions.md` § "Writing config, memory and lessons files",
      which loads unconditionally regardless of routing. `git-commit-job-must-stage-itself`
      was promoted in the same pass to `git-bridge` SKILL.md § Guardrails.
- [x] ~~Identify the terminal window that flashes roughly every 5 minutes~~ — DROPPED
      2026-08-24 at Jordan's direction. Deprioritised, NOT diagnosed: the cause is still
      unknown and no scheduler dump was run. Do not reopen it unprompted.
- [x] ~~Get the git bridge (port 8934) connected~~ — CLOSED 2026-08-18: no such server exists;
      the skill was rewritten to run git through the 8933 command bridge instead.
- [x] ~~Commit deck-builder v3.1 (2026-08-20)~~ — DONE, commit `2d962f5` (six files,
      +327/-30). Preceded by `b08ad5b` (widen sync filter — without it `review_strip.py`
      would have been silently skipped), `0d72b12` (/XD exclusions), `0c80eb1` (delete
      engagement skills). Original blocker was a stalled laptop OneDrive client, which
      caught up ~35 min after the cloud-side upload. Superseded detail: Bridges were started mid-session so 8932/8933
      never registered — must run from a FRESH chat. Sequence: run
      `CommandJobs\2026-08-18-sync-cowork-config.bat`, then a status/diff job, then stage
      `CoworkConfig\Skills\deck-builder\SKILL.md` and `...\reference\review_strip.py`
      by name. Subject: "Fix deck-builder slide review: renders are files, not inline images".
- [ ] GitHub push (see Decisions 2026-08-20). Phase 1 is a read-only pre-flight scan, not a
      remote. Do not add a remote until the git-bridge guardrail is deliberately rewritten.
- [ ] **The COPILOT_COWORK repo can NEVER be the one pushed.** Confirmed 2026-08-20: the
      three engagement skills were committed in `5ff400d` and remain in every commit since;
      commit `0c80eb1` deletes them going forward but does not sanitize history. A GitHub
      repo must be NEW, populated by copying named folders in, never by cloning and
      filtering. Define the scope as an ALLOWLIST — a blocklist fails open on the next
      client skill added.
- [ ] Scrub `state-apportionment`: `SAMPLE_DATA_NOTES.md` and `make_sample_data.py` carry
      client-derived sample data and are currently excluded BY FILENAME, which protects two
      names rather than the category. Regenerate them as genuinely synthetic so the skill
      becomes fully generic and needs no exclusion.
- [x] ~~Run a `git status` check to confirm the repo is clean since the baseline commit.~~ —
      DONE 2026-08-21: `git status --short` returned EMPTY after commit `8e096a3`. Tree clean.
- [x] ~~8932 devtunnel dead~~ — CLOSED 2026-08-21: it was never dead at the time it was being
      reported; all three tunnel URLs answer. See "Verified live state".
- [ ] Decide whether the scattered `*.bak` / `*-backup` / `*.pre-*` files can be deleted now
      that git holds history. Leave them until the repo has proven itself.

## Preferences & Constraints
- Approved 8933 workflow: Jordan describes a task; Cowork proposes the EXACT commands and the
  exact output folder; Jordan approves once; Cowork writes the `.bat` via the 8932 bridge and
  immediately runs it with NO second approval; Cowork reports stdout, stderr, exit code,
  affected files, and output locations. No allowlist — a new `.bat` is authored per task.
- Do not blindly retry a failed 8933 call. Diagnose first.
- Do not over-verify. Act on the most likely path and batch checks.
- Separate facts from inferences and flag anything needing review.
- Report exact absolute Windows paths after writing.

## Key Exchanges
- 2026-08-18 — Jordan asked whether the monitoring fixes were themselves breaking the
  bridges. They were not: the log showed only 3 restarts all day (00:23 kill test, 07:36
  x2) and nothing during the reported outage. Check evidence before blaming new machinery.
- 2026-08-18 — Jordan corrected a claim that persistent memory is capped at 512 characters.
  That cap belongs to the built-in memory tool; the persistent-memory skill writes uncapped
  `.md` files. Keep the two systems distinct.

## Watchdog — consolidated record (2026-08-18 → 2026-08-21)

Absorbed from six memory-tool entries so the detail survives in the file store.

- **What it is (2026-08-18, built + verified).** Scheduled task `CoworkBridgeWatchdog` runs
  `Startup\_bridge-watchdog.ps1` every 2 minutes, probes 8931/8932/8933, and restarts ONLY
  dead ports (5-minute cooldown). It never kills a live process; it acts only when a TCP
  connect is refused. Cheap status file:
  `Outputs\2026-08-18 - Bridge Hardening\watchdog\status.txt`. Same work pinned
  supergateway 3.4.3 into `Startup\node_modules`, so `tasks.json` runs
  `node ...\supergateway\dist\index.js` rather than `npx -y` (verified on spare port 8939;
  backup `tasks.json.pre-local-supergateway-backup`).
- **Recovery is proven at the process level (2026-08-18 kill test).** The 8933 node PID was
  killed via the autorun queue. Watchdog saw it DOWN at 00:23:35 and listening again at
  00:23:43 — about 24 seconds unattended, no `GO.bat`. Local and tunnel probes both returned
  400, matching the untouched 8931/8932 controls, so process + tunnel recovery works.
- **But recovery does not rescue the current chat.** In that same test `run_batch_file`
  failed three times: the MCP session is bound to the dead PID and cannot re-initialize
  inside an existing conversation.
- **A new chat picks up the recovered bridge (2026-08-18 00:34 CDT, confirmed end to end).**
  `run_batch_file("command-bridge-test.bat")` returned exit 0 in 268 ms with stdout
  `COMMAND_BRIDGE_TEST_OK` against the watchdog-restarted process — no `GO.bat`, no
  re-setting ports to Public. A bridge death costs only the chat it happened in.
- **Watchdog exonerated for the midday outage (2026-08-18 11:45 CDT).** `watchdog.log` shows
  only three restarts all day: 8933 at 00:23 (the deliberate kill test) and 8931+8932 at
  07:36. Nothing between 07:36 and 11:45. `status.txt` at 11:45:33 reported all three UP and
  8932 reads worked in-chat. The roughly 5-minute terminal flash does not match its 2-minute
  trigger — that was a separate, unidentified scheduled item.
- **Console flash fixed (2026-08-18 16:52 CDT).** `powershell.exe -WindowStyle Hidden` applies
  only after the host window exists, so Windows draws the console and then hides it. The task
  action is now
  `conhost.exe --headless powershell.exe -NoProfile -ExecutionPolicy Bypass -File _bridge-watchdog.ps1`
  (build 22631), with a `wscript` shim fallback below build 22000. `_watchdog-install.ps1`
  was rewritten so re-running preserves it. Never revert to `-WindowStyle Hidden`.
- **The real cause of vanishing tools, solved 2026-08-21 — bridges never died.** All three
  PIDs (8931/1492, 8932/17248, 8933/2792) were created 8/19 between 08:24:44 and 08:25:03 in
  one batch and were still LISTENING. Tools disappeared because supergateway runs
  `--stateful --sessionTimeout 1800000`, a 30-minute IDLE expiry: chat idle at 23:39Z, drop
  noticed 02:03Z. The session expired server-side and all three went at once. An `EADDRINUSE`
  seen at that time was a restart attempt correctly failing against a healthy bridge. The fix
  is a NEW CHAT — kill nothing. PID magnitude does not indicate generation.

## Reference Links & Files
- Watchdog script — `...\COPILOT_COWORK\Startup\_bridge-watchdog.ps1`
- Watchdog installer — `...\Startup\_watchdog-install.ps1`
- Status + history — `...\Outputs\2026-08-18 - Bridge Hardening\watchdog\status.txt`, `watchdog.log`
- CRLF fixer — `...\CommandJobs\2026-08-18-fix-crlf-all.bat`
- Async launcher — `...\CommandJobs\_async-launch.ps1`
- Git init job — `...\CommandJobs\git-init.ps1` and `git-init.bat`
- Job logs — `...\CommandJobs\Logs\<job>_<stamp>.log`
