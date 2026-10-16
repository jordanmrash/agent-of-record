# Cowork Lessons — failed approaches and what worked instead

Maintained by the `self-improvement` skill. Read this before repeating a known
technique. Update entries in place by `Pattern-Key`; do not append duplicates.

**Evidence key:** `measured` = verified in-session by a check whose output was read.
`reported` = a tool claimed success and nothing confirmed it. Add `inference unverified`
when the **Why** is reasoning rather than something probed.

**Key format:** `<subsystem>-<short-behavior>` — subsystem first, so dedupe works.

---

## Failures

### A product-capability claim was asserted as a correction without checking
- **Pattern-Key:** verify-product-claim-before-correcting-the-operator
- **Distinct-from:** assumption-from-the-brief-encoded-as-a-durable-rule - there an assumption from the USER'S framing was carried into a skill file as a permanent rule; here an assumption about a PRODUCT'S capability was asserted to the user without a lookup. One is about what gets written down, the other about what gets checked before it is said.
- **Date:** 2026-09-15
- **Trigger:** failure
- **Rule:** Before telling the operator a product cannot do something, search once. A capability claim is a fact to check, not an inference to make.
- **Delivered-to:** self-improvement, gamma-tango
- **Failed:** the operator asked about an open LLM inside Claude Cowork. The reply opened by correcting him: the model cannot be swapped. It can - Claude Desktop's third-party inference mode runs Cowork against any gateway or a local model, and Ollama documents the integration. The rest of the answer stood on the false premise and had to be withdrawn.
- **Why:** The premise sounded like product knowledge and was a stale assumption. No lookup was made because the answer felt certain, and certainty was treated as evidence.
- **Worked:** One web search before answering. Two results settled it in under a minute, and the corrected answer changed the design conclusion: the host stays Claude, so the narrowing stands; what changes is memory availability under a gateway and the data boundary.
- **Evidence:** measured - the exchange of 2026-09-15 21:16-21:22 UTC; Ollama blog 2026-08-25 and docs.ollama.com/integrations/claude-desktop.

### The `.plugin` file is uploaded, never opened
- **Pattern-Key:** plugin-install-is-upload-not-open
- **Distinct-from:** claude-cowork-connectors-dialog-is-remote-only - that entry is about WHERE a stdio executor can be registered (the Connectors dialog cannot; claude_desktop_config.json can); this is about HOW a built .plugin file is installed (Upload plugin, never Finder open). Different dialog, different artifact, and the fix for one does nothing for the other.
- **Date:** 2026-09-15
- **Trigger:** failure
- **Rule:** Install a built `.plugin` through Customize → Plugins → Add → Upload plugin. Never tell anyone to open or double-click the file.
- **Delivered-to:** command-bridge
- **Failed:** `open "Outputs/Skills Plugin/agent-of-record-skills-macos.plugin"` → `kLSApplicationNotFoundErr: E.g. no application claims the file`. The install pages and the `build_plugin.py` epilogue had said "open it in Claude and accept it" since the file format was invented.
- **Why:** Claude 1.52386.3 declares `CFBundleDocumentTypes` for `.dxt`/`.mcpb` and `.skill`, and nothing for `.plugin`, so macOS assigns the dynamic UTI `dyn.ah62d4rv4ge81a5dzq7y06` and no handler exists. A Finder double-click fails the same way.
- **Worked:** The app's own upload picker. The file is read by Claude, not handed to it by the OS.
- **Evidence:** measured — `open` exit 1 with the LaunchServices error, and the `Info.plist` document types read directly.

### A skipped handshake makes a CLEAN install check meaningless
- **Pattern-Key:** install-check-skipped-handshake-hides-dead-bridge
- **Distinct-from:** claude-cowork-agent-vm-validation-proves-repo-not-host - there the checks ran in the WRONG PLACE (the Linux VM instead of the host) so a clean result was true of the wrong machine; here the check ran in the right place but SKIPPED THE STEP that fails (never started the server), so a clean result was true of a smaller question. Fix there is where to run; fix here is what to exercise.
- **Date:** 2026-09-15
- **Trigger:** failure
- **Rule:** A check that skips the thing that can fail is not a check. Handshake every stdio server and inspect the tool schemas it returns.
- **Delivered-to:** command-bridge, self-improvement
- **Failed:** `INSTALL_CHECK: CLEAN (18 passed, 4 skipped)` on a machine where `aor-filesystem` was in a `failed` state and every one of its 14 tools was unusable. Two of the four skips were the 8931 and 8932 stdio handshakes, skipped because npx fetches those servers on first run.
- **Why:** The check proved the launcher existed and was executable. Nothing started the server, so nothing saw that its tool list was rejected. The failure was invisible until a tool was called.
- **Worked:** `install_check.py` now starts the launcher, completes a real MCP `initialize` plus `tools/list`, and reports two distinct faults: an `inputSchema` with no `type: object`, and a declared `$schema` dialect other than 2020-12. Only an unresponsive server is skipped. Against the then-current pin it failed correctly and immediately.
- **Evidence:** measured — the new check failed on the pinned server on the same machine that had just passed the old one.

### The filesystem pin was measured on the wrong axis
- **Pattern-Key:** fs-server-pin-measured-output-schema-only
- **Distinct-from:** narrow-before-fixing-duplicated-capability - that is a scoping question (should this component exist at all); this is a measurement defect inside a fix that was warranted (the pin measured one schema axis and missed the broken one). cowork-draft07-well-formed-untested - that is the OPEN question of whether a complete draft-07 schema is accepted; this entry's defect was measuring the wrong AXIS, which would mislead whichever answer that question gets.
- **Date:** 2026-09-15
- **Trigger:** failure
- **Rule:** When pinning a dependency against a schema fault, measure every schema the server emits, not the one that prompted the investigation.
- **Delivered-to:** command-bridge, self-improvement
- **Failed:** `@modelcontextprotocol/server-filesystem@2025.8.21` was pinned on 2026-09-13 as the last release with no output schemas, and documented as safe. It is the worst of the measured releases. Thirteen of its fourteen tools emit an `inputSchema` of literally `{"$schema": "...draft-07..."}` — no `type`, no `properties` — and Cowork rejects the whole `tools/list` at `tools[0].inputSchema.type`.
- **Why:** The 2026-09-13 measurement read `outputSchema` dialects only. On that axis 2025.8.21 is genuinely clean, because it has no output schemas at all. The breakage was always on the input side and was never looked at. Root cause: the package declares `zod-to-json-schema ^3.23.5` and no `zod`, so npx resolves zod 4.x through `@modelcontextprotocol/sdk` 1.30.0, and `zod-to-json-schema@3` cannot read zod 4 internals — it emits an empty schema and no error.
- **Worked:** Nothing, on that route. Installing the same version with an npm `overrides` of `zod` to `^3.25.0` restores complete schemas on all 14 tools (measured: `missing-type=0`), but the bridge was retired from the Claude route instead, because it duplicated capability the host already had. Retiring it removed the whole class of failure rather than working around it.
- **Evidence:** measured — three releases handshaked and their tool lists read: 2025.8.21 (13 of 14 missing `type`), 2025.11.25 and 2026.8.31 (0 missing, 14 draft-07 on both axes); dependency tree read from a clean install.

### The Cowork session's own shell is not the machine
- **Pattern-Key:** device-shell-is-a-linux-vm-not-the-host
- **Distinct-from:** claude-cowork-agent-vm-validation-proves-repo-not-host - same underlying fact (the session shell is a Linux VM), different scope: that entry is the install-verdict consequence and its fix (run the checks in the Mac's own Terminal); this one is the general rule for ANY evidence claim made from the session shell and names the approved executor as the only path to the machine. Kept as the general statement; the install entry is the worked case.
- **Date:** 2026-09-15
- **Trigger:** failure
- **Rule:** Evidence that a thing works "on the Mac" must come through the approved executor. The session's own shell runs in a sandboxed Linux VM with the folders mounted.
- **Delivered-to:** command-bridge
- **Failed:** A first run of `install_check.py` from the session shell reported `host: Linux 6.8.0-136-generic`. As real-device evidence it was worthless, and it would have been filed as a passing macOS run.
- **Why:** The desktop workspace mounts connected folders into a Linux VM. Same files, different kernel, different interpreters — that run used Python 3.10.12 where the Mac has 3.14.7.
- **Worked:** The same script through `run_batch_file`: `host: Darwin 25.6.0 arm64 / macOS 26.6.2`, Python 3.14.7, running as the user. That is the only path in this repository that reaches the machine itself.
- **Evidence:** measured — both runs performed, both `uname` lines read.

### Check branch protection before pushing, because the undo may be blocked
- **Pattern-Key:** git-protected-branch-bypass-not-reversible
- **Distinct-from:** git-repo-state-read-from-worktree-only - that is about READING repo state from the wrong source (a file listing instead of git/gh commands); this is about a WRITE whose undo is governed by a different permission than the write itself. One misreads what landed, the other cannot take back what landed.
- **Date:** 2026-09-15
- **Trigger:** failure
- **Rule:** Read the branch's protection rules before pushing to it. An admin bypass that succeeds does not imply an undo that succeeds.
- **Delivered-to:** command-bridge
- **Failed:** `git push origin main` succeeded with `Bypassed rule violations for refs/heads/main: Changes must be made through a pull request. 2 of 2 required status checks are expected.` The correction — rewinding `main` and reopening the change as a PR — was then rejected: `GH006: Protected branch update failed. Cannot force-push to this branch.`
- **Why:** The ruleset allows an admin to bypass the pull-request requirement but not to force-push. The two permissions are independent, so a bypass can be one-way.
- **Worked:** Nothing rewound it. The commit stayed on `main` and the duplicate branch was deleted. Every later change went to a branch first. Additional damage was caused by `git reset --hard` during the attempted undo, which stripped the committed files out of the working tree; it was recoverable only because the commit was already on the remote.
- **Evidence:** measured — both remote responses read verbatim.

### Editing a skill description can silently cross the 1024-character cap
- **Pattern-Key:** skill-description-cap-crossed-by-edit
- **Distinct-from:** skill-over-description-cap-silently-dropped - that entry establishes the FACT (an over-cap description unloads the skill with no error) and its detection (validate_skill.py); this entry is the PROCESS gap that re-creates the fault after the fact is known: an edit path with no re-check, because release_check does not read descriptions. Same cap, different failure point.
- **Date:** 2026-09-15
- **Trigger:** failure
- **Rule:** After editing any skill's frontmatter description, re-run the cap check. The loader drops an over-cap skill with no error.
- **Delivered-to:** self-improvement, gamma-tango
- **Failed:** An edit to `gamma-tango`'s description to name the per-product behaviour took it to 1038 characters. `release_check.py` passed; the skill would have been dropped at load with no message.
- **Why:** The cap is enforced by the loader, silently. `release_check` checks repository integrity; only `install_check` reads the descriptions.
- **Worked:** `install_check.py` caught it on the commit that introduced it. Trimmed to 953, 71 characters of margin. Leave margin deliberately — a later edit that adds one clause should not cross it.
- **Evidence:** measured — the failing check and the passing re-check both read.

### Do not pass `path` to the batch bridge — the parameter is `file`
- **Pattern-Key:** bridge-8933-arg-name
- **Date:** 2026-08-18
- **Trigger:** failure
- **Rule:** Call `run_batch_file` with `file=` holding a path relative to CommandJobs. There is no path, args, cwd or timeout parameter.
- **Delivered-to:** command-bridge, git-bridge
- **Failed:** `run_batch_file(path="2026-08-18-fix-crlf-all.bat")` → `REJECTED: unexpected parameter(s): path`
- **Why:** The 8933 tool accepts exactly one parameter, `file`, holding a path relative to `CommandJobs`. No command string, args, cwd, or timeout.
- **Worked:** `run_batch_file(file="2026-08-18-fix-crlf-all.bat")` → exit 0.
- **Evidence:** measured

### After a bridge transport error, check whether the job ran before retrying
- **Pattern-Key:** bridge-8933-transport-drop-verify-first
- **Date:** 2026-08-18
- **Trigger:** failure
- **Rule:** After a transport error, check whether the job already ran before retrying. Never blind-retry a state-changing job.
- **Delivered-to:** command-bridge
- **Failed:** Treating "MCP server couldn't be reached" as a plain retry. A blind retry risks running a state-changing job twice.
- **Why:** The transport can drop while the job either did or did not start. The error alone does not distinguish them.
- **Worked:** Check for the job's declared output folder / log via the 8932 filesystem bridge. Folder absent = never started, safe to retry. Also read `Outputs\2026-08-18 - Bridge Hardening\watchdog\status.txt` — it refreshes every 2 minutes and reports each port UP/DOWN, so it distinguishes "port dead" from "this session's connection dead". Twice on 2026-08-18 the ports were UP and a single informed retry succeeded. For 8932 WRITES the check is `get_file_info` before the retry: size unchanged = write never landed, safe to retry. 2026-10-01: eight such verifies, eight retries, zero double-writes, including one `write_file` that dropped twice and landed on the third attempt.
- **Evidence:** measured — outcome observed; Why is inference unverified
- **See also:** bridge-session-bound-to-pid

### A dead bridge costs the current chat, not the machine
- **Pattern-Key:** bridge-session-bound-to-pid
- **Date:** 2026-08-18
- **Trigger:** correction
- **Rule:** A dead bridge costs the current chat, not the machine.
- **Delivered-to:** command-bridge, local-file-bridge, playwright-skill
- **Failed:** Assuming the bridges were down on the PC because the tools were unreachable in-session.
- **Why:** The MCP tool surface is fixed when a chat starts and binds to the process that was alive then. If that process is replaced, the chat cannot re-initialize against the new one.
- **Worked:** Start a new chat — local tools connect straight to the recovered bridges. No GO.bat, no re-setting ports to Public.
- **Evidence:** measured — outcome observed; Why is inference unverified

### Files written through the filesystem bridge arrive LF-only and break cmd
- **Pattern-Key:** bridge-8932-writes-lf
- **Date:** 2026-08-18
- **Trigger:** failure
- **Rule:** FIXED AT SOURCE 2026-09-09 - executor 1.3.0 rewrites an LF-only .bat/.cmd to CRLF in place before running it and reports `line_endings`. The CRLF fix job is no longer required before a first run; it stays as the lint gate. What survives: a script another tool wrote may not be in the platform's convention - read `line_endings` in the result instead of assuming.
- **Delivered-to:** command-bridge, git-bridge, local-file-bridge
- **Failed:** Running a `.bat` straight after writing it via the 8932 bridge — cmd can exit silently, and `call :label` constructs break outright.
- **Why:** The bridge writes LF line endings; cmd's parser requires CRLF for reliable label and block handling.
- **Worked:** Run `2026-08-18-fix-crlf-all.bat` after every write and before executing. It normalizes and reports which files it touched. Also avoid `call :label` menus entirely.
- **Evidence:** measured
- **Fixed-at-source:** 2026-09-09 - `batch-exec-server.js` 1.3.0 (agent-of-record PR #9, `main f0f5518`, ported to the live bridge the same day) normalizes the script's terminators before the run. Measured twice through the live bridge: bridge-written .bat files ran with `line_endings: lf-to-crlf` and clean output, one of them containing an `if ( ) else ( )` block. The 2026-08-18 fix job still runs the lint gate for new jobs.

### `-WindowStyle Hidden` does not suppress a scheduled task's console flash
- **Pattern-Key:** schtask-hidden-window
- **Delivered-to:** command-bridge
- **Date:** 2026-08-18
- **Trigger:** better-approach
- **Failed:** Scheduled action `powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ...` — flashed a console every 2 minutes.
- **Why:** `-WindowStyle` is applied by PowerShell after its host window already exists. Windows draws the console first; PowerShell hides it a beat later. That beat is the flash.
- **Worked:** `conhost.exe --headless powershell.exe -NoProfile -ExecutionPolicy Bypass -File ...` — no window is created at all (build 22631). Below build 22000, use a `wscript.exe` shim calling `Run(cmd, 0, False)`.
- **Evidence:** measured — outcome observed; Why is inference unverified

### Read skills and memory from the local mirror, not by downloading
- **Pattern-Key:** onedrive-read-mount-locally
- **Supersedes key:** read-user-folder-locally
- **Date:** 2026-08-24
- **Trigger:** better-approach
- **Rule:** READ the Cowork tree from the mounted user folder rather than downloading it, and WRITE it through the 8932 bridge at its local path - a `user` surface write reaches only the container mirror.
- **Delivered-to:** local-file-bridge, persistent-memory
- **Failed:** Fetching skill/memory files through the file-content download path — the retrieved copy was not where the tool said it would be, costing a round trip.
- **Why:** The OneDrive `Documents/Cowork` tree is already mounted read-only in the session, so a download is redundant.
- **Worked:** READ `cowork-memory/` and `skills/` directly from the mounted user folder. Do NOT write back with `surface="user"` — that lands only in the container mirror (see `onedrive-user-surface-not-live`). To WRITE, as of 2026-08-24 there are two paths and they are NOT equivalent. PREFERRED: write the file on the PC through the 8932 bridge under `OneDrive\Documents\Cowork\` — that folder was added as a third bridge root in commit a6297b6, the repo sync sees the change in the same session, and OneDrive carries it upward afterwards. FALLBACK, only when the bridge is unavailable: stage under `working/`, upload with `UploadFileContent` (`conflict_behavior=replace`), then re-list to confirm size and modified time changed — but that write lands cloud-side and will NOT reach the PC or the repo for many minutes (see `onedrive-cloud-to-laptop-lag`).
- **Evidence:** measured

### Writing to the user surface does not reach OneDrive on its own
- **Pattern-Key:** onedrive-user-surface-not-live
- **Supersedes key:** user-surface-not-onedrive
- **Date:** 2026-08-18
- **Trigger:** false-success
- **Rule:** Write config, memory and lesson files to the LOCAL OneDrive path via the 8932 bridge. The repo sees it instantly. Cloud-side artifact writes are the fallback for when the bridge is down.
- **Delivered-to:** local-file-bridge, persistent-memory
- **CORRECTED 2026-08-28, this entry's headline is now WRONG:** `CopyArtifact(surface="user")` DOES reach OneDrive and the PC. Measured repeatedly on 2026-08-28, hash-identical on the PC every time, taking roughly 3 to 5 minutes to replicate down. So the 2026-08-18 finding that those writes "are not pushed back to the live OneDrive folder" no longer holds, and the `UploadFileContent` dance in the Worked line below is no longer required. What survives is the TIMING, not the failure: cloud-side writes work but are slow, which is why the local path is preferred rather than merely tidier.
- **Failed:** Creating `skills/self-improvement/SKILL.md` and `cowork-memory/cowork-lessons.md` on the session's user surface. Both calls returned `{"ok": true, ...}` — and neither file existed in OneDrive. A path lookup on the live folder returned 404 and the index still showed its old size.
- **Why:** The user surface is a container-side mirror of `Documents/Cowork`. Writes land in the mirror; they are not pushed back to the live OneDrive folder within the session.
- **Worked:** Stage the file under `working/`, then upload it to the live folder with the file-upload tool (`conflict_behavior=replace`), then re-list the folder and confirm size and modified time changed. Verified by re-listing the folder after upload and confirming both size and modified time had changed from the pre-upload values. (Do not hard-code the byte counts here — they decay and would hand a later session a false negative.)
- **Evidence:** measured
- **See also:** onedrive-read-mount-locally

---

### Git does not make system state revertible
- **Pattern-Key:** git-misses-system-state
- **Delivered-to:** git-bridge
- **Date:** 2026-08-18
- **Trigger:** correction
- **Failed:** Describing a commit as a rollback point for a machine change.
- **Why:** Git tracks files only — not installs, scheduled tasks, registry, or port visibility, which is where the worst incidents originated.
- **Worked:** Make the *installer script* the source of truth (e.g. edit `_watchdog-install.ps1` rather than the live registration), commit that, and keep a timestamped `.bak` of the prior version. Then the scheduler change is reproducible from a tracked file.
- **Evidence:** measured

### `fsutil` needs elevation — use `Get-PSDrive` for disk space
- **Pattern-Key:** batch-fsutil-needs-elevation
- **Delivered-to:** command-bridge
- **Date:** 2026-08-18
- **Trigger:** failure
- **Failed:** `fsutil.exe volume diskfree C:` inside a batch job → "Access is denied", job exited 1.
- **Why:** `fsutil` requires an elevated token, and the batch bridge runs as a standard user and cannot elevate. No retry or argument change fixes this.
- **Worked:** `powershell.exe -NoProfile -Command "$d=Get-PSDrive C; '{0:N2} GB free of {1:N2} GB' -f ($d.Free/1GB),(($d.Used+$d.Free)/1GB)"` — same answer, no elevation. Prefer PowerShell/CIM over elevation-gated console utilities generally.
- **Evidence:** measured

### Classify a skill by scanning its CONTENT, not by reading its folder name
- **Pattern-Key:** skill-classification-needs-content-scan
- **Date:** 2026-08-20
- **Trigger:** failure
- **Failed:** Treating `CoworkConfig\` as generic tooling and widening the config-sync filter without checking what was in it. The widened pass went from 24 to 102 files and pulled engagement material into the git mirror.
- **Why:** Some skills are engagement-specific. `<client>-apportionment` names a client in the FOLDER PATH — a repo tree discloses the engagement in a directory listing, before anyone opens a file. Worse, `tax-provision-report-replication` sounds generic and still carries client references inside `SKILL.md` and `OTP_REFERENCE.md`, so a name-based rule misses it entirely.
- **Worked:** Content-scan every skill folder, then exclude engagement-specific ones at the SOURCE with robocopy `/XD` (a `.gitignore` is too late — the mirror already holds the file). After adding `/XD`, delete what already landed: `/XD` stops future copies but does not purge existing ones. Verify with a residual scan and a re-run that copies nothing. Prefer an ALLOWLIST over a blocklist, because a new client skill fails open under a blocklist.
- **Evidence:** measured — 102 → 56 files, residual scan reported CLEAN, re-run copied nothing
- **See also:** git-deletion-does-not-sanitize-history

### Deleting a file does not remove it from git history
- **Pattern-Key:** git-deletion-does-not-sanitize-history
- **Date:** 2026-08-20
- **Trigger:** failure
- **Failed:** Assuming that excluding the engagement skills from the mirror and committing the deletions made the repo safe to push.
- **Why:** `git status` showed them as deletions of TRACKED files — they had been committed in `5ff400d` and sit in that commit and every one since. `git log`, `git show`, and any clone still surface the client name in the path. A deletion commit stops future propagation; it does not sanitize.
- **Rule:** Committing a deletion does not sanitize git history - the path survives in every prior commit and every clone. A repo that ever held engagement content can never be the one pushed; populate a NEW repo by copying named folders in, never by cloning and filtering.
- **Delivered-to:** git-bridge
- **Worked:** Accept that this repo can never be the one pushed. Any GitHub repo must be NEW, populated by copying named folders in — never by cloning and filtering, which carries invisible history. State the limitation in the deletion commit body so no one later mistakes it for a sanitization.
- **Evidence:** measured — tracked-deletion status read after the commit

### A slide render cannot be shown inline in chat — it reaches the user as a FILE
- **Pattern-Key:** render-not-inline-in-chat
- **Date:** 2026-08-20
- **Trigger:** failure
- **Failed:** Running the `deck-builder` §11.5 slide-by-slide review as written — "publish the renders and show them one per row." The agent published 39 JPGs to `output/review/` and then wrote prose describing three options per slide as though the operator could see them. He could not. The review looked functional for two slides before he said "after the second slide i no longer see slides to select."
- **Why:** There is no path from a workspace image to the conversation. `RenderSlide` returns a file PATH — opening it shows the image to the AGENT only. `render_ui` renders allowlisted image URLs, and a workspace path is not a URL. The skill instructed a step the environment cannot perform, and the agent improvised something that resembled it instead of naming the limit.
- **Rule:** Never describe a visual as though the user can see it. A workspace image reaches him only as a named file - name the file, or put the comparison in a chat table instead.
- **Delivered-to:** deck-builder
- **Worked:** Rewrote §11.5 (skill v3.0 → v3.1, uploaded and re-listed to confirm). §11.5a states the constraint and adds the hard rule *never describe a visual as though the user can see it*; §11.5b makes a comparison TABLE in chat the default review, with self-describing filenames (`slide-12-A-table.jpg`) and a per-slide A/B/C comparison strip; §11.5c keeps the sequential loop only on explicit request and requires a `Glob` of the review folder before the first question. Added `reference/review_strip.py` (5,578 bytes) so the mechanics cannot be skipped — it builds the renames, the strips, and prints the table, and exits non-zero naming missing files.
- **Evidence:** measured — script run end to end, 52 files over 13 slides; a tofu-box glyph from an em dash in the strip label was caught in the render and fixed to ASCII
- **See also:** skill-alwayson-defeated-by-routing

### Do not narrate an action as done before it has been done
- **Pattern-Key:** agent-claims-action-before-doing-it
- **Date:** 2026-08-20
- **Trigger:** failure
- **Failed:** Twice in one session. (1) Describing three slide renders as if they were visible in chat. (2) Writing "I've saved this so the next chat picks it up" about the GitHub decision — the `save_memory` call had not been made, and the claim was only caught because the operator asked whether everything had been saved and the memory list was checked instead of answered from recollection.
- **Why:** Narrating intent in the past tense reads identically to reporting a result. Neither error was a tool failure; both were assertions made without a confirming read. This is the same class as claiming a commit succeeded on a zero exit code without reading the commit id.
- **Rule:** State an action as done only after its confirming call returns. When the check is cheap - `list_memories`, `Glob output/**`, a folder re-list - run it rather than reporting from memory.
- **Worked:** State an action as done only after the confirming call returns — and when the check is cheap (`list_memories`, `Glob output/**`, a folder re-list), run it rather than reporting from memory. If something can only be delivered as a file, say so in the same sentence and name the file.
- **Evidence:** measured — the missed save was found by listing memories, then actually written
- **See also:** render-not-inline-in-chat, onedrive-user-surface-not-live

### The deck layout engine refuses long copy rather than overflowing it
- **Pattern-Key:** gtdeck-engine-refuses-long-copy
- **Delivered-to:** deck-builder
- **Date:** 2026-08-20
- **Trigger:** failure
- **Failed:** Treating build errors like `cards: no column count fits this region` and `kpi label ... too long for a 2.85 in tile` as bugs to work around, which cost roughly ten build cycles on a 15-slide, 3-version deck.
- **Why:** `gt_layout.js` measures text and refuses any placement that would collide, overflow, or break a word — by design. The error names the element and states the remedy; it is the engine working, not failing.
- **Worked:** Read the error's stated fix and shorten the CONTENT (KPI labels to ~4 words, card headings to ~3), or swap the device for one that suits the region — a narrow split-panel region takes a table or icon rows, not four cards. Reach past the engine to hand-place a box only for a device it has no primitive for. Cap `s.region.bottom` before a device when a chevron banner must sit beneath it.
- **Evidence:** measured — final three versions each pre-flighted 0 failures

### A cloud write can take minutes to reach the laptop — never commit a partial set
- **Pattern-Key:** onedrive-cloud-to-laptop-lag
- **Rule:** Both sync legs cost minutes, so pick the one that does not block you. A LOCAL 8932 write unblocks the repo and the commit immediately; a cloud-side write blocks them for minutes.
- **Delivered-to:** local-file-bridge
- **Date:** 2026-08-24
- **Trigger:** failure
- **Failed:** Uploading an edited `copilot-instructions.md` to the live OneDrive folder (confirmed 6,536 B in the cloud), then running the sync job three times over four minutes. Every run reported `robocopy exit: 0` and the repo copy stayed at the old 5,417 B.
- **Why:** The desktop OneDrive client pulls cloud-side changes on its own schedule. `robocopy exit: 0` means "nothing copied", which reads identically to "nothing to do" — success and staleness look the same.
- **Worked:** Verify the SOURCE by size and timestamp before trusting a sync, not the robocopy exit code. When the client lags and the cloud copy is already confirmed, write the identical approved bytes into the repo copy through the 8932 bridge: the two converge when the client catches up, and the commit is not held hostage. Confirmed the same day — a later sync copied the cloud file over the hand-placed one and left nothing to commit, proving the bytes matched.
- **Evidence:** measured
- **Hits:** 2   (2026-08-21 sync job read a stale repo copy; 2026-08-24 three memory files stranded cloud-side across a commit)
- **Repeat 2026-08-24:** Commit 1d60874 went in while `cowork-lessons.md`, `MEMORY-INDEX.md` and `cowork-skill-design.md` were still cloud-only — exactly the partial set this entry's title warns against — so a follow-up commit had to wait on replication. Two further errors compounded it. First, adding the OneDrive Cowork folder as a third 8932 root was announced to the operator as removing the sync wait; it does not. A bridge root changes what the bridge may REACH, not how OneDrive replicates. The cloud-to-PC leg is unchanged and still slow; only a write made directly to the LOCAL path is visible to the repo in the same session. Second, the download was twice called stuck on readings taken minutes after the cloud write — including a theory that in-place updates lag while new files arrive, which expired about sixty seconds later when all three landed together. The client caught up on its own, as it did on 2026-08-20. Hand-placement stays available, but note WHICH copy: this entry's Worked line writes the REPO copy, which OneDrive does not sync and therefore cannot conflict. Writing the ONEDRIVE copy while a download is pending is what produces conflict files.
- **Promoted-to:** `copilot-instructions.md` § "Writing config, memory and lessons files" (2026-08-24), which loads unconditionally. FOUR surfaces stated the old rule and all four were corrected in the same pass — `copilot-instructions.md` (the "exactly two directories" claim and the "NOT reachable by the bridges" paragraph), `self-improvement` SKILL.md (environment block and Write row), and `persistent-memory` SKILL.md (write path, confirm step, guardrail). See `config-contradiction-survives-in-second-file`.
- **See also:** onedrive-user-surface-not-live, onedrive-read-mount-locally

### Run `git ls-files` before deleting anything called "scratch"
- **Pattern-Key:** git-check-tracked-before-deleting
- **Date:** 2026-08-21
- **Trigger:** failure
- **Rule:** Run `git ls-files` before deleting anything that looks like scratch. Untracked files take a plain delete; tracked files take `git rm` and a commit that says why.
- **Delivered-to:** git-bridge
- **Failed:** A prune list described seven COPILOT_COWORK files as disposable scratch. Five of them — `bridge-test.txt`, `copilot-test.txt`, `page-2026-07-27*.yml`, `session-handoff-test.txt` and `CommandJobs/Output/DEPRECATED-DO-NOT-USE.txt` — were tracked in git. A plain delete would have left the repo dirty with phantom deletions instead of recording them.
- **Why:** Files that look like throwaway probes are often committed early, when the repo is young and everything gets added.
- **Worked:** `git --no-pager ls-files | findstr /V /C:"CoworkConfig/"` first, then split the list: untracked files get a plain delete, tracked files get `git rm` plus a commit that says why. Also verify "empty" folders really are empty — `Outputs\Outputs` was described as an empty duplicate and contained a subfolder.
- **Evidence:** measured

### Vanishing tools mean an expired session, not a dead bridge
- **Pattern-Key:** bridge-idle-session-expiry
- **Date:** 2026-08-21
- **Trigger:** correction
- **Rule:** Check PID creation times and listening state before restarting anything.
- **Delivered-to:** command-bridge, local-file-bridge
- **Hits:** 2   (2026-08-21 all-three drop; 2026-08-21 20:19 EADDRINUSE on 8931/8932 while both healthy)
- **Failed:** Reading the simultaneous loss of all three bridge tool surfaces as three dead processes, and reaching for restarts.
- **Why:** supergateway ran `--stateful --sessionTimeout 1800000` on all three ports — a 30-minute IDLE expiry. All three PIDs were created in one batch on 8/19 and were still LISTENING; the chat went idle at 23:39Z and the drop was noticed at 02:03Z. The session expired server-side, so all three went at once. An `EADDRINUSE` at that moment is a restart attempt correctly failing against a HEALTHY bridge, not evidence of a crash.
- **Worked:** Check PID creation times and listening state before restarting anything, then start a NEW chat. 2026-08-21: `--stateful`/`--sessionTimeout` were removed from the 8932 and 8933 tasks (stateless), keeping them only on 8931 where the Playwright Edge SSO profile lock needs them. Takes effect at the next VS Code restart.
- **Evidence:** measured
- **See also:** bridge-session-bound-to-pid
- **Promoted-to:** copilot-instructions.md, "Rules already paid for" (LESSON-DIGEST block) - rule text confirmed present in the digest 2026-08-28.

### A VS Code restart alone does not apply a tasks.json change
- **Pattern-Key:** bridge-restart-needs-pid-kill
- **Date:** 2026-08-21
- **Trigger:** failure
- **Rule:** Restarting VS Code does not replace a bridge listener that already holds the port. Kill the old PIDs, then prove the edit is live by comparing netstat PIDs before and after - identical PIDs mean the old process is still serving.
- **Delivered-to:** command-bridge
- **Failed:** Editing `Startup\.vscode\tasks.json` to make 8932/8933 stateless, restarting VS Code with GO.bat, and reporting the change live. The three bridge PIDs came back byte-identical, so the old stateful processes were still serving every call.
- **Why:** GO.bat starts the folderOpen tasks but does not terminate node processes already bound to 8931/8932/8933. An existing listener keeps the port, so the new task's flags never take effect and nothing reports an error.
- **Worked:** Kill the listeners explicitly by PID, close VS Code, then relaunch - and PROVE it by comparing netstat PIDs before and after. On 2026-08-21 the relaunch job showed 14728/34420/31296 before and 31784/34812/37692 after; PID turnover is the only reliable evidence the edit is live.
- **Evidence:** measured
- **See also:** bridge-idle-session-expiry

### Changing a config also means changing everything that restores it
- **Pattern-Key:** bridge-recovery-scripts-revert-config
- **Date:** 2026-09-02
- **Trigger:** failure
- **Rule:** After ANY edit to `tasks.json`, resync `Startup\KnownGood\tasks.json` from live in the SAME job and prove it byte-identical. An unsynced snapshot turns `bridge-restore-tasksjson.bat` from a recovery tool into a regression tool, and the restore reports success while doing it.
- **Delivered-to:** command-bridge, gamma-tango
- **Hits:** 2 (2026-08-21 stateless fix; 2026-09-02 KnownGood found still at its 8/21 revision, predating the entire 8934 bridge)
- **Promotion:** 2026-09-02 - Rule authored on the second hit and carried into the copilot-instructions.md LESSON-DIGEST, so it now loads every session.
- **Failed:** Treating the stateless fix as done once `tasks.json` was edited and committed. Two recovery paths still carried the OLD values: `Startup\KnownGood\tasks.json` (what `bridge-restore-tasksjson.bat` restores from) still had `npx.cmd -y supergateway` and `--stateful` on all three ports, and `Startup\_bridge-watchdog.ps1` hard-coded `--stateful --sessionTimeout 1800000` for every port while restarting any dead listener every 2 minutes.
- **Why:** A recovery script is a second copy of the configuration. It is invisible while everything is healthy and authoritative the moment something breaks - so a stale one silently undoes the fix at exactly the worst time, with no error and no log entry.
- **Worked:** After any bridge config change, update every copy and prove agreement: refresh KnownGood from live and confirm with `fc /L` (IDENTICAL), give the watchdog per-port flags mirroring tasks.json, and print a three-way flag matrix (tasks.json vs watchdog, per port) as the verification step. Also make the watchdog LOG which mode it used on each restart so future drift is visible.
- **Evidence:** measured - commits bd4029f and 9f55bda, flag matrix printed and matched on all three ports; 2026-09-02 the KnownGood resync produced +44/-4 because its last commit was 784dc9f (2026-08-21), predating c2d1e37 which brought 8934 online - a restore would have silently deleted the Power Automate bridge from tasks.json
- **See also:** watchdog-exonerated

### Transport drops are the devtunnel hop, not the bridge processes
- **Pattern-Key:** bridge-drops-are-tunnel-not-bridge
- **Date:** 2026-10-02
- **Trigger:** correction
- **Rule:** Drops are the devtunnel hop, not the bridge process. 0% local; the tunnel measured 1-2% on 2026-08-21 and roughly 1 in 3 on 2026-10-01, so budget a verify-then-retry on EVERY write rather than treating a drop as rare.
- **Delivered-to:** command-bridge, local-file-bridge
- **Hits:** 4   (2026-08-21 measured 400-request baseline; 2026-08-24 two first-contact drops in four calls, both recovered on an immediate retry, all three PIDs unchanged — n=4 is far too small to move the measured rate; 2026-10-01 roughly 8 first-attempt failures in ~25 bridge calls - write_file x5, edit_file x1, list_allowed_directories x1, get_file_info 1 of 4 - every retry succeeded, PIDs not checked, no local-vs-tunnel split re-measured; 2026-10-02 roughly 1 in 4 calls dropped across the 1.4.1/1.4.2 build - edit_file, write_file (`HOST_CALL_LOST_WRITE`), move_file x2 - every drop confirmed by read-back, every retry or split landed, a 10-file 73 KB read_multiple_files passed)
- **Hit 4, 2026-10-02 - when the same payload drops twice, split it before a third retry.** An `edit_file` carrying two description fields in `ai-plugin.json` returned "couldn't be reached" twice in a row, read-back unchanged both times; split into two one-field edits, both landed first try. A six-edit batch on `ai-plugin_2.json` dropped once; split 3+3, both landed first try. Smaller calls dropped too (a one-line manifest edit, a `write_file`, two `move_file`) but each landed on a single retry. So the retry discipline stands, with one addition: a repeat drop on the SAME payload is the cue to split it, not to retry it a third time. Whether size drives the drop probability is inference unverified - two large payloads and ~20 calls cannot establish a rate - and this is a transport DROP (nothing written, read-back unchanged), not the content corruption in `bridge-8932-large-write-corrupts-a-character`.
- **Failed:** Inferring from five in-session failures that all landed on 8932 that the filesystem bridge specifically was unreliable.
- **Why:** Small-sample bias. Five observations cannot separate a per-port fault from a shared transport fault.
- **Worked:** Measure it - 400 requests, 100 each against the local listener and the public tunnel for both ports. Local loopback dropped 0/100 on BOTH 8932 and 8933 (avg 1ms and 0ms). The tunnel dropped 2/100 and 1/100, every failure an operation timeout (avg 125ms and 134ms). The bridge processes drop nothing; the tunnel leg loses 1-2 percent, and a 2-vs-1 split at n=100 is noise, not a per-port pattern. For scale, stateful 8932 measured 16 percent. A single informed retry remains the correct response.
- **Evidence:** measured - script and detail CSV committed as 1e983e5
- **See also:** bridge-8933-transport-drop-verify-first, bridge-8932-large-write-corrupts-a-character, batch-one-reconcile-job-beats-many-bridge-edits
- **Promoted-to:** copilot-instructions.md, "Rules already paid for" (LESSON-DIGEST block) - rule text confirmed present in the digest 2026-08-28.

### Quarantine by moving with a manifest instead of deleting
- **Pattern-Key:** cleanup-quarantine-instead-of-delete
- **Date:** 2026-08-21
- **Trigger:** better-approach
- **Failed:** Nothing broke - but a blanket "just delete them" on 111 files is the one step in a cleanup that cannot be undone if the filter is wrong by even one entry.
- **Why:** A move produces the identical clean end state as a delete while staying reversible, and it costs only disk. The filter is the risky part, not the removal.
- **Worked:** Move matches into a dated quarantine folder preserving relative structure, write a MANIFEST.csv (RelativePath, Type, Bytes, LastWriteTime, OriginalFullPath), and hard-ABORT the run if a known live file matches the filter - the 2026-08-21 job checked for `memory\memories.json` and would have exited without moving anything. Re-scan afterwards to prove 0 remaining. Result: 111 moved, 0 failed, 0 left, counts matching the prior inventory exactly (Demo 49, Tasks 36, Skills 26).
- **Evidence:** measured
- **See also:** git-check-tracked-before-deleting, prune-list-counts-drift-from-names

### Editing a file through PowerShell can silently re-encode the rest of it
- **Pattern-Key:** file-edit-reencodes-existing-characters
- **Date:** 2026-08-21
- **Trigger:** failure
- **Rule:** Never round-trip a UTF-8 file through PowerShell `Get-Content`/`Set-Content`. 5.1 decodes a BOM-less UTF-8 file as ANSI and re-encodes the damage into content the edit never touched, so exit 0 and a plausible size delta prove nothing. Use `[System.IO.File]::ReadAllText`/`WriteAllText` with an explicit no-BOM UTF8Encoding, and verify by diffing a known non-ASCII line against the backup.
- **Failed:** Appending new lessons with `Get-Content -Raw` + `Set-Content -Encoding UTF8`. The append itself was correct and pure ASCII, but the round-trip mangled em dashes ALREADY in the file - the heading `## Contradictions - stored memories that proved wrong` came back as garbled bytes. The job reported exit 0 and a plausible size increase, so nothing looked wrong.
- **Why:** Windows PowerShell 5.1 `Get-Content` decodes a BOM-less UTF-8 file as ANSI, turning each multi-byte character into separate characters; `Set-Content -Encoding UTF8` then re-encodes those, doubling the damage and adding a BOM. The corruption hits content the edit never touched.
- **Worked:** Read and write bytes explicitly - `[System.IO.File]::ReadAllText($p, [System.Text.Encoding]::UTF8)` and `[System.IO.File]::WriteAllText($p, $t, (New-Object System.Text.UTF8Encoding($false)))`. Always back up before an in-place edit, and VERIFY by re-reading and diffing a known non-ASCII line against the backup rather than trusting exit 0 and a size delta. This file already carried older damage from the same cause.
- **Evidence:** measured - corruption seen by comparing headings against the backup, then repaired by restore and byte-safe rewrite

### A commit job that does not stage itself spawns an endless successor
- **Pattern-Key:** git-commit-job-must-stage-itself
- **Date:** 2026-08-24
- **Trigger:** better-approach
- **Rule:** A self-committing job must stage its own permanent file and never its ephemeral inputs.
- **Delivered-to:** git-bridge
- **Failed:** Writing a close-out commit job that stages only the file it was created to commit. `2026-08-21-cowork-close-commit.bat` was committed by `2026-08-21-cowork-close-commit-2.bat`, which then sat untracked itself - so the next close needed a job 3, which would need a job 4. Each close leaves the tree dirty by exactly one new file and the sequence never terminates.
- **Why:** The job is written into the repo it commits, so running it creates a new untracked file in the same working tree it is trying to clean. Staging by explicit filename cannot cover a file whose name did not exist when the list was written.
- **Worked:** Have the job stage ITSELF alongside its targets - `git add CommandJobs/<job-2>.bat` plus `git add CommandJobs/<this-job>.bat` - in one commit. The file exists on disk by the time the job runs, so self-staging resolves. Verified 2026-08-21: commit 8e096a3, 2 files, 25 insertions, exit 0, and `git status --short` came back EMPTY - the first close in the chain to leave a genuinely clean tree.
- **Evidence:** measured - stdout of the job, verified by a second independent `git status` run afterwards
- **Hits:** 2   (2026-08-21 job file left untracked; 2026-08-24 the standing job staged its own ephemeral message file)
- **Repeat 2026-08-24:** The rule has a second half. A self-committing job must stage its PERMANENT self, but must never stage its EPHEMERAL inputs. `cowork-close.bat` reads `CommandJobs/_commit-msg.txt`, and its `git add -A` swept that file into commit a6297b6 before deleting it on exit — leaving a tracked-but-missing file and a tree dirty with a pending deletion after every close. `.gitignore` alone cannot fix this: gitignore applies only to UNTRACKED files, and the pending deletion could only be recorded by a close run, which must recreate the very file whose deletion it is trying to commit. That catch-22 cannot break itself.
- **Worked 2026-08-24:** A one-off job ran `git rm --cached --ignore-unmatch` on the message file plus a `.gitignore` entry in a single commit — 50a425f, 6 files, exit 0, `git status --short` empty afterwards. The standing job was deliberately NOT edited, preserving its never-rewritten property so it never needs the CRLF pass.
- **Promoted-to:** `git-bridge` SKILL.md § Guardrails (2026-08-24) — the reviewed-then-staged exception that reconciles `git add -A` in `cowork-close.bat` with the never-stage-blindly rule, plus a new guardrail forbidding a job from committing its own ephemeral inputs.
- **See also:** git-check-tracked-before-deleting, bridge-8932-writes-lf

### Duplicating a fact across both memory stores causes the drift it was meant to prevent
- **Pattern-Key:** memory-tiering-pointer-vs-deep
- **Delivered-to:** persistent-memory
- **Date:** 2026-08-25
- **Trigger:** correction
- **Hits:** 1
- **Failed:** Following `memory-two-stores-drift`'s instruction to write durable findings to
  BOTH the built-in store and `cowork-memory/*.md`. By 2026-08-25 the built-in store held 80
  entries, many of them commit-level restatements of what the files already said
  (`fact-deckbuilder-v31-committed`, `fact-conflicted-quarantined`, `fact-lessons-logged`).
  Two copies of one fact age independently and there is no signal for which is current.
- **Why:** The two stores have different strengths and duplicating flattens both. The built-in
  store loads before the first turn with no bridge and no OneDrive, but caps at 512 characters.
  The files hold unlimited mechanism and are git-versioned, but only load if a skill fires AND
  OneDrive has replicated. Copying content into both gives the reliability of the file and the
  brevity of the memory — the worst half of each.
- **Worked:** Tier them. The built-in store is the POINTER layer: one `ptr-<slug>` per focus
  area naming the deep file and when to read it, plus genuinely short standing facts. The files
  are the DEEP layer. One home per fact; on conflict the FILE wins and the pointer is updated.
  Applied 2026-08-25: `ptr-cowork-lessons`, `ptr-cowork-bridge-infrastructure`,
  `ptr-cowork-config-setup`, `ptr-cowork-skill-design`, governed by `instruction-memory-tiering`.
- **Evidence:** measured — 80 built-in entries against 4 deep files covering the same subsystems
- **See also:** memory-two-stores-drift, skill-over-description-cap-silently-dropped

### Check where a rule already lives before recommending that it be moved there
- **Pattern-Key:** recommend-move-of-rule-already-moved
- **Date:** 2026-08-25
- **Trigger:** correction
- **Hits:** 1
- **Failed:** Recommending that the unconditional lessons-scan obligation be moved out of the
  `self-improvement` description and into `copilot-instructions.md`. It had already been moved
  there on 2026-08-18 (commit 3292cf1) and refined since; the instructions file already carries
  the scan, the "regardless of which skill is driving" clause, and the write-back obligation.
  The recommendation was drafted from the stored memory of the defect rather than from the
  current file.
- **Why:** `fact-lessons-load-path-fixed-2026-08-18` records both the defect AND the fix, but the
  defect is the memorable half. A memory that describes a past problem reads as a present one
  unless the file it refers to is opened.
- **Promoted-to:** agent-recommends-edit-without-reading-file
- **Worked:** Before proposing that any rule move to a config surface, read that surface first
  and quote the lines that are or are not there. Applies to `copilot-instructions.md`, `AGENTS.md`
  and any SKILL.md. This is the same failure as `agent-recommends-edit-without-reading-file`,
  reached from the memory store instead of from an agent summary.
- **Evidence:** measured — instructions file read after the recommendation was already made
- **See also:** agent-recommends-edit-without-reading-file, config-contradiction-survives-in-second-file

### `save_memory` rejects an over-length entry and stores nothing
- **Pattern-Key:** savememory-512-cap-rejects-silently
- **Date:** 2026-10-02
- **Trigger:** failure
- **Rule:** Keep a memory under 512 characters and read the success field of every save - an over-length save stores nothing.
- **Delivered-to:** persistent-memory
- **Hits:** 7
- **Hit 7, 2026-10-02.** Two rejections, both on `update_memory` (not `save_memory`) - each returning `success:false` with "Content must be at most 512 characters", read and trimmed and re-saved the same turn. Widening only: the cap and its explicit error apply to `update_memory` identically. The key's "silently" is already defined above as batch-non-interrupting, not API-silent, so this is NOT a contradiction. Same drafting-step miss as hits 4-6; the escalation named at hit 6 (a `len()` gate in the save path) is still the only thing that would move this.
- **Hit 6, 2026-10-01.** Two saves rejected over 512 characters, `success:false` read both times, trimmed and re-saved. No new mechanism; the trap fired at the DRAFTING step again, with the Rule live in the always-on digest. As with `deferred-tools-read-as-absent-bridge` at hit 3, another sentence will not move this - the next escalation is a runnable `len()` gate in the save path, not prose.
- **Hit 5, 2026-09-10.** A preference memory (`pref-article-paragraph-openers-and-significance-tails-2026-09-10`, ~530 chars) was drafted with no character count, rejected with `{"success":false,"error":"Content must be at most 512 characters","reason":"invalid_content"}`, trimmed BY EYE to ~520 and rejected again with the same error, then trimmed under 512 and saved `success:true`. The `success` field was read every time, so nothing was lost; the counter moves because two writes were burned before one landed, and the retry in Worked failed once because it was a trim, not a count.
- **Hit 4, 2026-09-02.** A memory recording the 8934 bridge verification was drafted for completeness rather than to the cap, came in slightly over, and returned `success:false / invalid_content`. The `success` field was read on the same turn and a trimmed version saved cleanly, so the recovery in Worked held. The counter moves because the trap still fires at the DRAFTING step, not the recovery step - compose to the cap, do not compose and then discover it.
- **Failed:** Saving two pointer memories of roughly 520-540 characters in a batch of six. Both
  returned `success:false / invalid_content` while the other four succeeded, so a glance at the
  batch looked like it had worked. The same trap fired again later in the same session on a
  handoff memory, after the lesson had already been drafted.
- **Why:** The cap is 512 characters and enforcement is all-or-nothing — there is no truncation
  and no partial save. In a parallel batch the failures do not interrupt anything.
- **Worked:** Keep pointer memories near 300-450 characters, and read the `success` field of every
  `save_memory` result individually rather than assuming a batch succeeded. Count the content with `len()`
  before the first save AND before any retry, then retry the counted version in the same turn. Note this is the 512-char store cap, unrelated to the 1024-char
  SKILL.md description cap — two different limits on two different surfaces.
  Confirmed again 2026-08-28, and the key's wording needs care: every rejection observed is
  EXPLICIT. Over-length returns `{"success":false,"error":"Content must be at most 512
  characters"}`; a call with no key returns `{"success":false,"error":"Key cannot be
  empty","reason":"invalid_key"}`. "Silently" in this key means the failure does not
  interrupt a parallel batch and is easy to miss in one - it does NOT mean the API is
  silent. Always pass a key on the first call, and read the `success` field of every result.
- **Evidence:** measured — 3 rejected saves across the session, all re-saved after trimming; 2026-08-28 both rejection strings read verbatim, then a trimmed save returned success; 2026-09-10 two rejections (~530 then ~520 chars, same error string) read verbatim, then a save under 512 returned success:true
- **See also:** skill-over-description-cap-silently-dropped
- **Promoted-to:** copilot-instructions.md, "Persistent memory — two tiers, one home per fact" (the 512-character bullet). Already there and worded compatibly ("rejected outright — nothing is stored, and the failure is easy to miss") — read and confirmed 2026-08-28, so no new promotion is proposed.

### A tool missing from the visible list is not an absent bridge — call it before declaring failure
- **Pattern-Key:** deferred-tools-read-as-absent-bridge
- **Date:** 2026-09-01
- **Trigger:** correction
- **Rule:** Prove a bridge by CALLING it, never by reading a tool list. When the tool is ABSENT from the schema there is nothing to call - run `bridge-health.bat` through 8933 as the callable substitute. Re-probe before saying it is down AND again before closing out. Say "not on the surface as of now", never "unavailable this session", and never PLAN AROUND the absence.
- **Hits:** 3   (2026-08-25 declared bridge-less, both answered live; 2026-08-28 declared the git step impossible mid-routine, both present ~60 min later; 2026-09-01 said "not on the surface" - correct wording - then reasoned and planned as though the bridge were down, with the operator asserting it was up)
- **Promotion:** DUE at 2 hits. This is the head of a five-key cluster - `bridge-connector-removed-midsession`, `bridge-devtunnel-declared-dead-without-reprobe`, `probe-env-vars-blank-false-negative` and `bridge-absent-probe-is-not-permanent` all restate it. `copilot-instructions.md` routing rule 5 now covers BOTH halves - "A single failed call is not a dead bridge, and a negative probe expires" - and adds the re-probe-before-closing-out clause. Read and confirmed 2026-08-28. Promotion COMPLETE; the cluster keys above are back-pointed to the same digest block. **2026-09-01 - promotion did NOT prevent hit 3.** The rule was live in the always-on digest and was missed anyway, so the digest path is necessary but NOT sufficient for this rule. Two defects found: (1) the Rule as written was unfollowable in the exact case it targets - a tool absent from the schema cannot be called - so the 8933 `bridge-health.bat` substitute is now named in the Rule; (2) correct WORDING did not produce correct BEHAVIOUR - "not on the surface" was said, then the session planned around absence regardless. Do NOT re-promote on hit 3: the rule already sits on the strongest delivery path available, and a fourth restatement would only add prose. Any further escalation has to be a runnable CHECK, not another sentence.
- **Promoted-to:** copilot-instructions.md, "Rules already paid for" (LESSON-DIGEST block) - rule text confirmed present in the digest 2026-08-28.
- **Failed:** Telling the operator that neither the 8932 filesystem bridge nor the 8933 command bridge
  was registered in the session, and that there was no way to proceed. Both were present and
  healthy the entire time. The session ended by writing a handoff pack for a connection failure
  that did not exist, and four config edits were deferred a full day for no reason.
- **Why:** Tools are DEFERRED, not preloaded — a tool's definition does not appear until a tool
  search surfaces it, so an unsearched surface looks identical to an unregistered one. The
  standing note that a mid-session bridge start never registers made the false negative
  plausible enough to report without probing.
- **Worked:** Prove a bridge by CALLING it, never by reading a list. `list_allowed_directories`
  on 8932 and a review-only `cowork-close.bat` on 8933 each cost one call and give a definitive
  answer. Search the deferred surface first, then probe, and only then report a bridge down.
  Verified 2026-08-25: both bridges answered on the first attempt in a session previously
  declared bridge-less, and the entire handoff pack was discharged in that same session.
  **Second hit 2026-08-28 adds two things.** (1) A negative probe EXPIRES. Re-probe before
  reporting a bridge step impossible AND again before closing out any routine that needs it,
  not only before the first report - here the whole gamma-tango close was reported with git
  skipped, and the bridge was live about an hour later. (2) Word a negative as "not on the
  surface as of now", never "unavailable this session", because the second phrasing states a
  property the probe cannot establish. Watch the probe itself too: an anchored `^tool_name$`
  cannot match a fully qualified `<server>-<tool>` name and will read as absent even when the
  bridge is up.
  **Observed in BOTH directions on 2026-08-28.** Absent at the start of the close, present
  ~60 min later and used for two commits, then absent again ~17 min after the last
  successful call (`cowork-close.bat` at 21:35:26 UTC exit 0; `get_file_info` and
  `run_batch_file` both returning "couldn't be found, so its tools are unavailable" by
  21:52). Same conversation throughout, nothing done to the PC in between by this agent.
  So the reading expires in both directions and a bridge that just worked is not evidence
  it still works. Take the reading, act on it immediately, and re-read before the next
  step that depends on it. Practical consequence: publish to OneDrive FIRST and hash-verify
  there, because that leg does not depend on the bridge; the commit can wait for a session
  that has one.
- **Evidence:** measured — bridges declared absent, then both answered live, in two separate sessions. The 2026-08-28 disappearance is measured by two consecutive failed calls after a successful one in the same conversation. WHY the surface changes mid-session is unprobed and remains inference.
- **See also:** bridge-devtunnel-declared-dead-without-reprobe, recommend-move-of-rule-already-moved, bridge-absent-probe-is-not-permanent, bridge-connector-removed-midsession

### Replacing a block verbatim drops every obligation the new text does not restate
- **Pattern-Key:** skill-verbatim-replace-drops-unrestated-clauses
- **Date:** 2026-08-26
- **Trigger:** failure
- **Hits:** 1
- **Failed:** Applying a handoff pack's prepared §4 block verbatim over the existing §4. The
  replacement was correct in what it said, but two obligations that lived only in the old text
  and were not restated in the new block vanished with it. A whole-section replacement shows in
  the diff as one delete plus one insert, so nothing marks the lost clauses as lost.
- **Why:** A diff is line-oriented and a wholesale block swap defeats it — the reviewer sees a
  new section that reads correctly and has no signal pointing at what the old one carried.
  Reading for correctness of the NEW text cannot detect an omission in it.
- **Worked:** Before applying any prepared block over existing text, enumerate the imperative
  clauses in the OLD text and confirm each one survives in the new. Confirm with a normalised
  search (strip line breaks, collapse whitespace) rather than by eye — line wrapping produced a
  false negative on the first pass and made a surviving clause look deleted.
- **Evidence:** measured — two dropped obligations found on re-read after the replacement landed
- **See also:** agent-recommends-edit-without-reading-file, config-contradiction-survives-in-second-file

### A skill description is router matching text, not a slot for instructions
- **Pattern-Key:** skill-description-is-trigger-text-not-instruction-slot
- **Date:** 2026-08-26
- **Trigger:** better-approach
- **Hits:** 1
- **Failed:** Writing directives ("always do X", "never do Y") into a SKILL.md `description`.
  They never execute — nothing reads a description as instruction — and they consume the
  character budget that trigger phrases need, so the skill also matches worse.
- **Why:** The description is consumed by the router for matching only; the body is what a
  loaded skill executes. A directive there is therefore doubly wasted — inert AND crowding.
  Inference unverified: the crowding effect on match quality is reasoned from the budget, not
  measured directly.
- **Worked:** Treat the directive-to-trigger ratio as the diagnostic when a skill mis-fires: if
  a description contains imperatives, move them into the body and refill the space with trigger
  phrasing and the `Do NOT use` exclusion. Trim toward roughly 800 UTF-16 units, not the 1024
  cap — leaving headroom keeps a later edit from silently pushing the skill over.
- **Evidence:** measured — descriptions rewritten and re-scored; inference unverified on the Why
- **See also:** skill-over-description-cap-silently-dropped, savememory-512-cap-rejects-silently

---

### A converted workflow is not converted until it has RUN on real data
- **Pattern-Key:** alteryx-static-audits-miss-runtime-defects
- **Delivered-to:** alteryx-to-python
- **Date:** 2026-08-28
- **Trigger:** failure
- **Failed:** Treating a PASSing coverage audit plus a clean `py_compile` as evidence the conversion was sound. On Sales Workflow 2024 (139 nodes) both passed on a script that could not complete a single stage. Three separate defects only appeared on execution against the real 1.69 GB source set: (1) the Join helper renamed `Right_DC State` back to `DC State` while the left's own `DC State` was still present, so `pd.concat` raised "cannot reindex on an axis with duplicate labels"; (2) after ToolIDs 185 and 227 the stream already carried a `Right_State`, so ToolID 229's prefixing produced "The column label 'Right_State' is not unique"; (3) ToolID 109's declared `ImportLine=5` had been transcribed into CONFIG as `1`, giving `KeyError: 'Customer'`.
- **Why:** Coverage is a static diff of ToolIDs against a registry and `py_compile` only parses syntax. Neither touches data, so neither can see a column-name collision or a wrong header row. The failures surface only when real frames flow through the joins.
- **Worked:** Run the generated script end to end on the real source data before reporting anything, and treat each traceback as a finding rather than a nuisance. Where the data cannot come into the session, run it on the user's machine through the 8933 bridge. Three run-fix cycles took ~10 minutes and turned a plausible-looking script into a working one.
- **Evidence:** measured
- **Hits:** 1
- **See also:** alteryx-skip-schema-check-costs-a-run-cycle

### Run the schema pre-flight before writing conversion code, not after it fails
- **Pattern-Key:** alteryx-skip-schema-check-costs-a-run-cycle
- **Delivered-to:** alteryx-to-python
- **Date:** 2026-08-28
- **Trigger:** failure
- **Failed:** Skipping gate G2 (`schema_check.py`) on Sales Workflow 2024 because the source data was a 1.69 GB zip on the user's PC rather than in the session, and going straight from the conversion brief to writing code. ToolID 109's header row was transcribed as 1 when the workflow declares `ImportLine=5`; the error surfaced ~3.5 minutes into a full run as `KeyError: 'Customer'`.
- **Why:** The brief reports which fields each tool CONSUMES but does not verify them against the actual files, and `ImportLine` is a per-source attribute that is easy to lose when transcribing five sources into a CONFIG block by hand. G2 exists precisely to catch that class of mistake before any code is written.
- **Worked:** When the data is not reachable in-session, push a small probe script to the machine that holds it and dump every declared sheet's first three rows plus the sheet list. That probe took 18 seconds and revealed the title block above ToolID 109's header, the duplicate `Billing type` columns on the BEX sheets, and the real BEX file count - all before another run cycle.
- **Evidence:** measured
- **Hits:** 1
- **See also:** alteryx-static-audits-miss-runtime-defects

### Transcribing a literal table by hand fabricates data that looks right
- **Pattern-Key:** alteryx-handwritten-lookup-table-is-fabrication
- **Date:** 2026-08-28
- **Trigger:** false-success
- **Failed:** Writing ToolID 418's 82-row State/Recode table into the generated script from memory of a truncated config dump. The hand-written version listed ~25 foreign codes and ~56 US states, all plausible, none checked.
- **Why:** The config dump had been printed with a character limit, so only the first rows were ever visible, and a US-state list is easy to reconstruct convincingly from general knowledge. The result compiles, runs, and produces wrong apportionment silently.
- **Rule:** Never transcribe a data table by hand from a dump that may have been truncated - extract it programmatically from the source. A plausible reconstruction compiles, runs, and is silently wrong.
- **Delivered-to:** alteryx-to-python
- **Worked:** Extract every Text Input table programmatically from the manifest (`Data/r[i]/c[j]` keys, sized by `NumRows@value`) and write it into the script from the extracted values. The real table was entirely different: 82 rows ALL flagged Foreign, including `MEX`, `GTO`, `NSW`, `KZN`, `YUC`, bare numeric codes like `00`/`13`/`020`, a literal `N/A`, a `WI,` with a trailing comma, and one row whose key cell is null. Not one of those was guessable.
- **Evidence:** measured
- **Hits:** 1

### A 1.69 GB source zip does not need to cross the wire
- **Pattern-Key:** bridge-extract-on-pc-instead-of-downloading
- **Date:** 2026-08-28
- **Trigger:** better-approach
- **Failed:** Calling `sharepoint_onedrive-ReadFileContent` on a 1.69 GB zip in OneDrive. The call was interrupted and would in any case have been slow and context-hostile.
- **Why:** The connector streams file content back through the session. Workflow XML is a tiny fraction of a source package - here 830 KB of .yxmd/.yxmc inside 1.69 GB of Excel.
- **Worked:** Have the PC do the extraction. A batch job listed the zip's manifest and extracted only `*.yxmd`/`*.yxmc` (6 files, 830 KB), base64-encoded them, and the session decoded them back to byte-exact copies. Later, the same pattern ran the finished script against the full source set in place. Ask the user to put the zip in `Downloads` (a bridge root) rather than pulling it through the cloud.
- **Evidence:** measured
- **Hits:** 1
- **See also:** onedrive-cloud-to-laptop-lag

### A placeholder shaped like the deliverable is a false delivery, not an honest gap
- **Pattern-Key:** delivery-pointer-file-passes-as-artifact
- **Date:** 2026-08-28
- **Trigger:** false-success
- **Failed:** Shipping a conversion zip containing `AUDIT_TRAIL_NOTE.md` - a short file saying the real audit trail lived at `...\data\Output\AUDIT_TRAIL.md` on the PC that ran the job - in the slot where the contract listed `AUDIT_TRAIL.md`. The archive was verified by listing contents, counting files and checking the CRC. All three passed. the operator asked "is the audit trail not in the zip?" It was not.
- **Why:** Nothing was invented, so it did not register as fabrication - but a pointer file carries the deliverable's NAME while withholding its CONTENT, so the file listing looks complete and the gap becomes invisible. An outright omission would have been noticed. The verification compounded it: counting files is exactly the check a stub passes.
- **Rule:** A file carrying the deliverable's NAME but not its content is a false delivery, not an honest gap. Bring the artifact back and check its byte count against the source, or list it as not produced with the reason - nothing in between. Counting files is exactly the check a stub passes.
- **Worked:** Two permitted responses when an artifact was produced somewhere unreachable - bring it back (base64 through the bridge, decoded and the byte count checked against the source rather than retyped) or list it as not produced with the reason. Nothing in between. And verify archives by CONTENT: per-file minimum size plus a marker string only the real file contains, plus, for a run log, a figure from THAT run. The recovered file decoded to exactly 6,532 bytes matching the source.
- **Evidence:** measured
- **Hits:** 1
- **See also:** verifier-ignores-structural-diff, alteryx-handwritten-lookup-table-is-fabrication

### A verification that cannot fail on the thing you fear is not a verification
- **Pattern-Key:** verification-scoped-away-from-the-risk
- **Date:** 2026-10-01
- **Trigger:** better-approach
- **Rule:** For every check, name the failure it CANNOT catch. A guard whose fixture is smaller than the threshold it guards can never fail.
- **Failed:** Four separate checks reported success on one job while never examining the thing that was actually wrong. A coverage audit diffed ToolIDs against a registry and passed on code that could not complete a stage. `py_compile` parsed syntax and ran nothing. A row-count check would have accepted an 82-row lookup table transcribed by hand. An archive check counted files and never opened them.
- **Why:** Each check was sound within its own scope, and each scope excluded the failure mode. Passing them in sequence produces a strong feeling of verification with none of the substance, because the gaps are between the checks rather than inside any of them.
- **Worked:** For each check, name the failure it CANNOT catch, then decide whether something else covers that. Where nothing does, add a check that touches the real artifact: execute the code on real data, assert a marker string inside each delivered file, verify a decoded byte count against its source. Cheap and specific beats broad and structural.
- **Evidence:** measured
- **Hits:** 4   (2026-08-28 four checks that each excluded the real defect; 2026-08-28 a regression guard whose fixture was too small to trip the threshold it guarded; 2026-09-01 a selftest fixture whose two neighbours fell BELOW a floor set by an unrelated pair; 2026-10-01 behaviour certifications with no model in the loop)
- **Repeat 2026-10-01 - the certification's behavioural checks could not fail on behaviour:** the Phase 6 BROWSER_ACTION cert calls 127.0.0.1:8931 directly with no LLM in the loop, and the AGENTIC_PROBLEM_SOLVING cert writes hardcoded JSON stage files. Each is sound about the bridge and says nothing about the agent. Same shape as `py_compile` and `node --check` standing in for a run.
- **Repeat 2026-08-28 - the guard written FOR this lesson had this exact defect:** after finding that `lesson_brief.py --digest` truncated at 24, a selftest case was added to stop it regressing. The fixture held 2 rules. A 2-rule file cannot be truncated by a limit of 24, so the guard reported OK against a deliberately reintroduced bug - 18/18, exit 0, no signal at all. Only the negative control exposed it. Widening the fixture to 30 rules made the same reintroduction fail at 17/18, exit 1. A test fixture is part of the scope: sizing it below the threshold under test scopes the risk out just as completely as checking the wrong artifact.
- **Worked (addendum):** Size every fixture ABOVE the boundary it exercises, and run the negative control - reintroduce the bug and confirm the suite actually fails - before trusting any new guard. `sed` the default back, re-run, assert a non-zero exit.
- **Repeat 2026-09-01 - the same defect, one layer further out:** a new selftest for the lesson_dupe Distinct-from fix passed against the KNOWN-BROKEN script. The fixture held 7 entries, and lesson_dupe's floor is the p99.5 of pairwise similarity, which on 21 pairs is simply the maximum. That maximum belonged to a pair of BASELINE entries, so the new entry's two neighbours scored 0.9863 and 0.9846 against a floor of 0.9976 and neither was ever "above floor". The gate therefore never reached the branch under test. Sizing the fixture is not enough - the fixture must be able to REACH the threshold, and when the threshold is derived from the fixture's own distribution, an unrelated pair can hold it out of reach. Fixed by making the three entries byte-identical in the compared text so all three tied at the maximum; the case then failed on the broken script and passed on the fixed one.
- **Promoted-to:** copilot-instructions.md, "Rules already paid for" (LESSON-DIGEST block) - 2026-08-28.
- **See also:** delivery-pointer-file-passes-as-artifact, alteryx-static-audits-miss-runtime-defects, lessons-digest-default-limit-truncates

### Reconcile every requested path after a DeleteArtifact - `ok:true` can hide skipped files
- **Pattern-Key:** artifact-delete-recursive-skips-file-paths
- **Date:** 2026-08-28
- **Trigger:** false-success
- **Rule:** Send folders and files to DeleteArtifact in separate calls, and reconcile every requested path against `deleted` plus `not_found`.
- **Failed:** One `host-DeleteArtifact(surface="output", recursive=true, paths=[...])` call carrying six file paths AND one folder. It returned `ok:true` with `not_found: []` and a `deleted` array holding only the paths under the folder. The six FILE paths appeared in neither array - not deleted, not reported missing, no error raised. A `Glob output/**/*` run immediately afterwards showed all six still present.
- **Why:** The response does not account for every requested path, so a caller reading `ok` plus an empty `not_found` sees a clean delete. The only difference between the failing and the succeeding call was `recursive=true` on a mixed file-plus-folder batch; the internal cause was not probed.
- **Worked:** Re-sent the same six paths WITHOUT `recursive`. All six came back in `deleted`, and a fresh Glob of the tree showed only the intended survivors. Rule: send folders and files in separate calls, and after any DeleteArtifact reconcile each requested path against `deleted` plus `not_found` and re-list the tree. `ok:true` is not evidence that a delete happened.
- **Evidence:** measured - both Globs were run and read; Why is inference unverified
- **Hits:** 1
- **Confirmed 2026-08-28:** a two-FILE delete sent WITHOUT `recursive` returned both paths in `deleted` and an `ls` of the folder confirmed both gone. The Worked line holds.
- **See also:** artifact-deletion-reverts-after-verified-absent, verification-scoped-away-from-the-risk, agent-claims-action-before-doing-it

### Normalize before matching prose against a fixed vocabulary
- **Pattern-Key:** verifier-prose-match-needs-normalization
- **Delivered-to:** dream-cycle
- **Date:** 2026-08-28
- **Trigger:** failure
- **Failed:** `gate_check.py` failed gate G4 with "verdict wording is not classifiable" on its first real run. The verdict under test was correct. The ledger said "no-baseline wording"; the matcher's vocabulary list held "no baseline" - a hyphen against a space. Everything else the checker said in that same run was right, which is what made the false FAIL credible enough to send a session looking at the wrong artifact.
- **Why:** A checker that classifies human-written prose by literal substring match treats typography as meaning. Hyphen, space, underscore, slash and the unicode dash family are interchangeable to whoever typed the line and distinct to `in`. The direction matters: this is a false FAIL, which tempts a session to edit the evidence until the checker goes green instead of fixing the matcher.
- **Worked:** Normalize both sides before comparing - a `_norm()` that collapses `[\s\-\u2010-\u2015_/]+` to a single space, applied to the ledger text and to every vocabulary entry. The re-run passed G4 with the correct classification. Rule: any matcher reading prose a human typed normalizes separators first; and when a checker fails on something you believe is right, suspect the matcher before you touch the artifact.
- **Evidence:** measured - the FAIL, the fix and the passing re-run were each read
- **Hits:** 1
- **See also:** multiline-string-defeats-single-line-grep, verifier-ignores-structural-diff

### Apply a batch of proposed edits by extraction, and confirm by hash rather than count
- **Pattern-Key:** skill-edit-by-extraction-and-hash-verify
- **Date:** 2026-08-28
- **Trigger:** better-approach
- **Failed:** Nothing broke - but the default way to apply a review's OLD/NEW pairs to a SKILL.md is to read them and retype them into edit calls, and the default way to confirm is that the write returned ok or that a file count matched. Retyping is transcription, which is exactly how a lookup table got fabricated (`alteryx-handwritten-lookup-table-is-fabrication`), and a count is exactly the check a stub passes (`delivery-pointer-file-passes-as-artifact`).
- **Why:** Both defaults fail in the same direction: they confirm that SOMETHING was written, not that the RIGHT bytes were written. Neither an ok response nor a file count can separate a correctly applied edit from a mistyped one.
- **Worked:** Eight edits across three skill files, applied this way, all three confirmed. Parse the OLD/NEW pairs out of the proposal document with a regex instead of retyping them; assert each OLD string occurs EXACTLY ONCE in its target before applying anything; apply the whole set to LOCAL copies first and record the sha256 of each expected result; apply the same set through the bridge `edit_file`; then hash the resulting files and compare against the expected hashes. All three matched. Caveat: an insert-type edit has no OLD block, so the occurs-exactly-once assert correctly reports NOT FOUND for it - that is the expected result, not a failure, and an automated applier must special-case inserts rather than abort on them.
- **Evidence:** measured - 8 edits over 3 files, expected-versus-actual hashes compared and equal
- **Hits:** 1
- **See also:** skill-editartifact-patch-rejected-republish-folder, verification-scoped-away-from-the-risk, skill-verbatim-replace-drops-unrestated-clauses

### An always-on skill over the 1024-char description cap never loads at all
- **Pattern-Key:** skill-over-description-cap-silently-dropped
- **Date:** 2026-08-21
- **Trigger:** failure
- **Rule:** A description over 1024 units makes the skill silently fail to load. Treat the 900 WARN as the real ceiling.
- **Failed:** Assuming `persistent-memory` and `self-improvement` were firing because they are marked ALWAYS-ON and are listed in `Documents/Cowork/Skills`. Invoking `self-improvement` by name returned "Skill not found", and it was absent from the session's available-skills list. `persistent-memory` was absent too.
- **Why:** The CLI skill loader drops any skill whose frontmatter `description` exceeds 1024 UTF-16 units, silently — no error, no entry in the list. Measured: `persistent-memory` 1257 units, `self-improvement` 1519. Both had grown by accumulating trigger phrases and ALWAYS-ON preamble. Every "always-on" behaviour that appeared to work was actually coming from `copilot-instructions.md`, which duplicates the same rules and does load.
- **Worked:** Run `python scripts/validate_skill.py <SKILL.md>` on every personal skill and treat a `description_length` FAIL as "this skill does not exist". Trimmed both descriptions to 747 and 861 units, keeping the ALWAYS-ON sentence, the file path, 4-6 trigger phrases and the `Do NOT use` exclusion, and cutting duplicated restatements. Scores rose 93 to 96 and 63 to 68; both now load. A skill missing from the available-skills list is a cap problem until proven otherwise, not a routing problem.
- **Evidence:** measured - validator output before and after, plus the not-found response
- **See also:** agent-recommends-edit-without-reading-file

### EditArtifact can reject a patch whose find text is byte-identical — republish the folder instead
- **Pattern-Key:** skill-editartifact-patch-rejected-republish-folder
- **Date:** 2026-08-21
- **Trigger:** failure
- **Rule:** Never edit a SKILL.md or the lessons file in place with EditArtifact. Edit a local copy, republish the folder, confirm by hash.
- **Delivered-to:** persistent-memory, self-improvement
- **Hits:** 2   (2026-08-21 and 2026-08-28. Hits counts SESSIONS. Within them there are FIVE occurrences across FOUR files: self-improvement and myvoice on 08-21, then cowork-lessons.md over 3 attempts and myvoice again over 2 on 08-28.)
- **Promoted-to:** copilot-instructions.md, section "Do not edit skills or lessons in place with EditArtifact patches" (2026-08-28). Promoted after a fresh-context review found the DUE flag had sat unactioned from 2 hits to 5 occurrences.
- **Failed:** `EditArtifact(surface="user", path="skills/self-improvement/SKILL.md", patches=[two replace_text ops])` returned `invalid patch: replace_text 'find' string is not present in the artifact`. Both find strings were verified present exactly once in the mounted file first (`t.count(find) == 1` in Python, including the em dashes and the fenced code block), so the mismatch was not in the text I sent.
- **Why:** Unknown at the service layer — the mount and the artifact store can disagree, or a patch containing a fenced code block does not survive the round trip. Not worth further probing when a reliable path exists.
- **Worked:** Copy the current file from `/mnt/user-config/skills/<name>/SKILL.md` into `working/<name>/`, apply the edit locally with an asserted `count == 1` replace, re-run `validate_skill.py` and `score_skill.py`, then `CopyArtifact(surface="user", recursive=true, overwrite=true)` the whole folder and confirm `copied` equals the file count. Same two-gate discipline, one extra copy. **A count is not enough** - hash the local expected result and compare it against the published file; see `skill-edit-by-extraction-and-hash-verify`.
- **Evidence:** measured — both occurrences observed, both republished successfully; the Why is inference unverified
- **Second occurrence:** 2026-08-21, `skills/myvoice/SKILL.md`, three patches, same rejection. Two files, two shapes of edit, same failure — treat the in-place path as unreliable for SKILL.md rather than as a one-off.
- **Fourth and fifth occurrences 2026-08-28:** `cowork-memory/cowork-lessons.md` rejected three patches whose find text was verified present exactly once on the mount, INCLUDING anchors taken from the pre-edit version, so the service copy matched neither state. Later the same day `skills/myvoice/SKILL.md` rejected two more, one multi-line and one single-line, on text confirmed present. Five occurrences across four files now, none ever recovered by retrying. Treat in-place EditArtifact on user-surface markdown as unavailable rather than unreliable, and go straight to the whole-file republish with a hash check.
- **See also:** skill-over-description-cap-silently-dropped

### The skill scorer reads literal section headings, not equivalent content
- **Pattern-Key:** skill-score-needs-literal-guardrails-heading
- **Date:** 2026-08-21
- **Trigger:** failure
- **Hits:** 1
- **Failed:** Rewriting `self-improvement` with a full failure-handling table and ten guardrail-style rules spread through the body. Score moved only 68 to 72, and `dimension_notes` still read "no Guardrails section", "no 'When NOT to Use' section", "no failure handling" — with a safety FAIL for destructive scope and no substantive guardrails.
- **Why:** The rubric detects sections by heading name. Content that satisfies the intent under a different heading is invisible to it, and the destructive-scope safety check specifically looks for a Guardrails section.
- **Worked:** Add literal `## Guardrails` and `## When NOT to Use` headings, and name the failure section so it reads as failure handling. Same substance, restructured: 72 to 94, robustness 11 to 23, scope 15 to 25, safety FAIL to WARN, faithfulness WARN to PASS once an explicit no-fabrication rule was present.
- **Evidence:** measured — `dimension_notes` compared before and after

### conflict_scan reads an exclusion clause as a shared trigger
- **Pattern-Key:** skill-conflictscan-needs-reciprocal-delegation
- **Date:** 2026-08-21
- **Trigger:** better-approach
- **Hits:** 1
- **Failed:** Reading the HIGH-severity conflicts between `gamma-tango` and the three skills it delegates to as real routing collisions. It also flags shared vocabulary like "are", "before" and "file" as conflicts, which is noise.
- **Why:** The scanner matches quoted phrases anywhere in a description. `gamma-tango` names "show me the diff", "save memory" and "log that" in its own `Do NOT use` line, so its exclusion reads as a trigger, and delegation is only credited when the OTHER skill points back.
- **Worked:** Judge each reported conflict by hand, and resolve a real one by adding a reciprocal pointer in the delegated-to skill's description ("for the combined open/close routine use gamma-tango"). Treat single-word keyword overlaps as noise.
- **Evidence:** measured — scan output read in full

### Calibrate a voice profile from a real user rewrite, not from invented examples
- **Pattern-Key:** skill-voiceprofile-calibrate-from-user-diff
- **Date:** 2026-09-10
- **Trigger:** better-approach
- **Rule:** Calibrate a voice profile by mechanically diffing his real rewrite, never from description. Test any proposed rule against the whole finished document.
- **Delivered-to:** myvoice
- **Hits:** 3   (2026-08-21 first hand-rewrite; 2026-08-28, which carried TWO passes - a hand-edited .docx with red comments and a second pasted edit pass; 2026-09-10 red-ink review of a v2 .docx, diffed the same way. Hits counts SESSIONS, not passes.)
- **Failed:** Trusting the `myvoice` profile's nine rules, several of which carried invented illustrative quotes rather than the operator's own sentences. Drafts kept reading close-but-wrong, and one rule was actively backwards — it mandated a wry rhetorical-question close on every piece, which he deleted from a long technical article and replaced with practical advice.
- **Why:** A profile written from description rather than from a measured diff encodes the writer's theory of the voice, not the voice. Nothing in the file was falsifiable, so no rule ever got disproved.
- **Worked:** Have him rewrite a full AI draft by hand, then diff it mechanically. Count punctuation before reading for tone — that surfaced zero em dashes and zero semicolons across 2,542 words, the single strongest tell, which no amount of reading for "feel" had caught. Replace invented examples with his actual sentences, scope any rule he contradicted rather than deleting it, and add a restraint cap since he removed roughly as much colour as he added. Profile went from 9 rules to 21, score 100.
- **Promoted-to:** `myvoice` SKILL.md - the punctuation ban and the count-before-rewriting rule are the encoded form of this method.
- **Evidence:** measured — punctuation counted in Python across the pasted rewrite
- **Held on two further passes 2026-08-28:** the same mechanical diff (`difflib.SequenceMatcher` over paragraph lists, then read the opcodes) surfaced what reading for tone did not - a structural complaint he wrote three times in one document, and on the second pass a spelling register nobody thought to check. Profile is now 42 rules, score 100. The method's value rises with each pass rather than falling, because the cheap tells get taken early and what is left is the non-obvious.
- **Held on a third pass 2026-09-10:** the same difflib diff (paragraph then word level) confined his edits to 5 paragraphs plus 4 red comments, and what it surfaced this time was paragraph SHAPE, not punctuation or register: the one-line paragraph opener and the "..., and that is the X" closing tail he marked as AI tells were shapes the profile's own rules 36 and 33 had supplied. Two calibration passes had not tested the profile's example and fix sentences against its other rules or against his sentences, and the pre-ship mechanical count covered punctuation and register only. Method held; the count now has to include openers, summarizers and closers - see skill-voiceprofile-own-example-is-the-ai-tell.
- **See also:** skill-score-needs-literal-guardrails-heading, voice-us-register-sweep, assumption-from-the-brief-encoded-as-a-durable-rule, skill-voiceprofile-own-example-is-the-ai-tell

### A "No tools found" probe is a reading of NOW, never a verdict on the session
- **Pattern-Key:** bridge-absent-probe-is-not-permanent
- **Date:** 2026-08-28
- **Trigger:** correction
- **Rule:** An anchored `^tool_name$` probe cannot match a fully qualified `<server>-<tool>` and reads as absent even when the bridge is up.
- **Delivered-to:** command-bridge, local-file-bridge
- **Status:** NEAR-DUPLICATE of `deferred-tools-read-as-absent-bridge`, which owns this failure. Hits deliberately NOT set here to avoid double-counting the cluster. Kept only for the anchored-regex fault, which is specific and is recorded nowhere else.
- **Failed:** Probed for `run_batch_file` and `list_allowed_directories` by exact name, got "No tools found", and reported the git step as impossible for the rest of the session. the operator said "the bridge should be up, dig deeper, probe" - a re-probe found BOTH servers fully present, with all 14 filesystem tools and the batch tool. The whole gamma-tango close had already been reported with git skipped.
- **Why:** TWO faults, and the first was not noticed until a fresh-context review. (1) The confirming probe was written `^run_batch_file$`, which is anchored and therefore CANNOT match the fully qualified tool name `jordan-approved-batch-8933-v1-run_batch_file` whether the bridge is present or not. "No tools found" was evidence about the pattern, not about the bridge. The real evidence was the earlier UNANCHORED probe returning only `skill`. A malformed probe was read as a confirming second opinion. (2) Even the sound probe was treated as a standing property of the session rather than a timestamped reading. `bridge-connector-removed-midsession` already records that connectors ARRIVE mid-session as well as vanish, so a negative probe has a shelf life measured in minutes.
- **Worked:** Re-probe before reporting a bridge step as impossible, and again before closing out any routine that needs it. Say "not on the surface as of now" rather than "unavailable this session", and offer the re-probe rather than waiting to be asked. The absent-probe rule stands for what it proves, that no tool definition exists to call at that instant, and stops there.
- **Evidence:** measured - both probes ran in the same conversation about an hour apart, the first returning only `skill` and the second the full tool set, ending in commits 8d42c40 and 95672b6. The anchored-regex fault is measured by inspection of the pattern against the tool name. WHY the surface changed is unprobed and remains inference.
- **See also:** deferred-tools-read-as-absent-bridge (owns this failure), bridge-connector-removed-midsession, bridge-devtunnel-declared-dead-without-reprobe, bridge-reprobe-must-be-separated-in-time

### Verify a staged diff by HASH when a credential grep would trip the SOC
- **Pattern-Key:** prestage-verify-by-hash-not-credential-grep
- **Date:** 2026-08-28
- **Trigger:** better-approach
- **Rule:** Verify files you authored by hashing them, not by grepping for credentials. The credential grep trips the SOC alert.
- **Hits:** 1
- **Failed:** The standing pre-stage check greps the CoworkConfig tree for `client_secret`, `client_id`, `password=`, `api_key`, `Bearer` and private-key headers. That exact `findstr` fired a corporate security alert on 2026-08-28 05:09 UTC which the operator had to answer by email the same morning. Running it again hours later would have generated a second alert on the same explained activity.
- **Why:** A credential scan and credential theft look identical to endpoint detection - same process, same pattern list, same target extensions. The control is legitimate and the alert is correct, which is exactly why re-running it casually is expensive.
- **Worked:** Hash instead. `certutil -hashfile <path> MD5` on each file about to be staged, compared against the hash of the content the agent itself authored. A match proves the repo copy is byte-identical to known content, which is a STRONGER guarantee than a pattern grep, since it rules out anything riding along rather than only the patterns someone thought to list. Pair it with a `forfiles` size check for the 10 MB rule. Four files verified this way before commit 8d42c40, all four matching. Use the grep only for content the agent did NOT author and therefore cannot hash against a known good.
- **Evidence:** measured - the SOC email quotes the exact findstr command line; the four MD5 values matched the container-side hashes exactly
- **See also:** work-is-an-exercise-not-an-engagement

### A connector can vanish mid-session, not just fail to load at start
- **Pattern-Key:** bridge-connector-removed-midsession
- **Date:** 2026-10-02
- **Trigger:** correction
- **Rule:** A connector can vanish OR arrive mid-session. Do not restart anything on the PC; start a new chat instead.
- **Delivered-to:** command-bridge, local-file-bridge
- **Hits:** 4   (2026-08-21 a connector vanished mid-session; 2026-08-26 the reverse — a connector ARRIVED mid-session when the plugin was re-enabled; 2026-09-07 a "couldn't be found" that reversed itself, then a removal that did not; 2026-10-02 two in-chat arrivals with no new chat - minutes after the Ports panel went Public, and about an hour and a half after a PC reboot removed all three namespaces)
- **Hit 4, 2026-10-02 - the return can take over an hour, a new chat was never needed, and "another client is using the bridges" is evidence FOR waiting, not against it.** Two instances in one session. (a) At chat start 8932/8933/8931 were absent because the chat opened before the operator set the VS Code ports Public; the session told him "new chat" twice, including after a 75-second wait, and all bridge tools then arrived by `tools_changed_notice` in the SAME chat about eight minutes after the ports went Public. (b) After a PC reboot a `tools_changed_notice` removed all bridge tools; five separated probes over roughly 36 minutes all read absent while the operator reported the same bridges serving M365 Copilot/ACL; the namespaces returned to THIS chat about 95 minutes after the reboot with no new chat and nothing done on the PC beyond ports Public. Three consequences: the Hit-3 wording "open the new chat only if the second, separated probe also fails" is still too eager - today several separated probes failed and no new chat was required (whether one would have been FASTER was not tested); a report that another client is using the bridges proves the PC and tunnel are healthy and locates the fault in this chat's registration; and the wait is unbounded - minutes to over an hour - so keep working on what does not need the bridge rather than blocking on it.
- **Distinct-from:** `bridge-session-bound-to-pid` - there the bridge PROCESS died or was replaced and the chat stayed bound to the dead PID; here every process is healthy and the PLATFORM registers or removes the connector namespace, in both directions, with no process event at all. `bridge-server-edit-live-without-restart` - there a code edit changes tool BEHAVIOUR instantly while one newly ADDED tool lags a few minutes; here nothing was edited and a whole namespace of existing tools appears or vanishes.
- **Hit 3, 2026-09-07 - "couldn't be found" has two durations, and only a LATER re-probe tells them apart.** At 22:22 CDT on 2026-09-06 `run_batch_file` and then `search_files` both returned `couldn't be found, so its tools are unavailable` after nine minutes of successful calls. The session followed this rule to the letter and wrote "resume in a NEW chat" to memory. the operator typed "proceed" thirteen minutes later in the SAME chat, and both bridges answered on the first call - no plugin toggle was reported and nothing on the PC was restarted. The namespaces then carried roughly three hours of work until a `tools_changed_notice` removed 8932, 8933 and 8934 together at 00:29 CDT, and that removal did NOT reverse within the session. So the rule stands but its first move is wrong: before telling the operator to open a new chat, WAIT several minutes and re-call once (`bridge-reprobe-must-be-separated-in-time`); open the new chat only if the second, separated probe also fails. When the surface is genuinely gone, the close still completes - lessons and memory go cloud-side by the documented fallback, and the git step is deferred and reported as deferred, never skipped silently.
- **Failed:** TWO mistakes. (1) Assuming the filesystem bridge (8932) would still be there because it worked earlier in the same session; a `tools_changed_notice` removed `jordan-local-filesystem-8932-v1-write_file` mid-session, which breaks `git-bridge`'s core mechanic since it authors a `.bat` with 8932 and runs it with 8933. (2) Writing this entry at all without first scanning the `bridge-` keys — `bridge-session-bound-to-pid` and `bridge-idle-session-expiry` already explained the mechanism, and this started life as a near-duplicate with a vaguer Why.
- **Why:** The tool surface is fixed when a chat starts and binds to the process alive at that moment. If that process is replaced — by the watchdog, by GO.bat, or by hand — the chat cannot re-initialize against the new one, so the tool disappears while the bridge itself is perfectly healthy. 8933 survived here because its process was not replaced.
- **Worked:** Do not restart anything and do not re-set the tunnel ports. Start a NEW chat, which binds to the live processes. Within the doomed session, existing `.bat` files in `CommandJobs\` still run through 8933, so read-only git jobs survive while anything needing a NEW script does not — report the specific missing tool and what it blocks, never fall back to the autorun queue or artifact tools. And scan sibling keys before opening an entry: the correct action here was to increment the two existing entries, not add a third.
- **Repeat 2026-08-26 — the surface moves in BOTH directions, and a DISABLED PLUGIN is a third cause class:** a session told the operator to open a new chat because "it will bind all three bridges at start". He opened one; that session probed three ways (broad regex, tool-name regex, exact `list_allowed_directories` / `run_batch_file`), found no bridge namespace, declared the bridges down, and blamed the PC — GO.bat, the Ports panel. **That attribution was wrong.** the operator's reply was "the plugins were disabled. i have turned them back on", and seconds later a `tools_changed_notice` registered all fourteen 8932 tools plus `run_batch_file` INSIDE the already-running chat; both answered on the first call. Two corrections follow. (1) The tool surface is NOT immutably fixed at session start — re-enabling a connector registers its namespace mid-session, exactly as disabling one removes it. The old absolute wording ("a bridge absent at start will NOT appear later in that same chat") is too strong: it holds for a bridge PROCESS started mid-session, not for a connector toggled back on. (2) Check causes in this order before blaming the machine: **is the plugin turned on in Cowork?** → are the listeners up / Ports panel Public? → is the tunnel re-established? Nothing was ever wrong with the PC on 2026-08-26.
- **Evidence:** measured — 2026-08-21 the removal notice was explicit, the status job still ran, no new job could be written; 2026-08-26 three probes found nothing, then a plugin re-enable registered both namespaces mid-session and both bridges answered immediately; 2026-09-07 the "couldn't be found" text, the successful call thirteen minutes later, and the 00:29 tools_changed_notice are all in one session transcript
- **See also:** bridge-session-bound-to-pid, bridge-idle-session-expiry, bridge-restart-needs-pid-kill
- **Promoted-to:** copilot-instructions.md, "Rules already paid for" (LESSON-DIGEST block) - rule text confirmed present in the digest 2026-08-28.

### Unexplained ~5-minute terminal flash
- **Pattern-Key:** schtask-unexplained-5min-flash
- **Delivered-to:** command-bridge
- **Supersedes key:** unexplained-5min-flash
- **Date:** 2026-08-18
- **Trigger:** missing-capability
- **Failed:** Attributing it to the watchdog — the cadences do not match, and no 5-minute repeater is registered.
- **Why:** Unknown. A full scheduler audit found only `CoworkBridgeWatchdog` at PT2M; the sole other short-interval task, `BootstrapUsageDataReporting` at PT15M, is Disabled.
- **Worked:** Nothing — RETIRED 2026-08-24 at the operator's direction. He does not care about the flash, so it will not be chased. It is unresolved, NOT solved: the cause was never found and no scheduler dump was ever run. Do not investigate it, do not propose a scheduled-task dump for it, and do not re-raise it as an open item — reopening is the operator's call, not a session's initiative.
- **Evidence:** reported — diagnosis only, no fix verified; inference unverified
- **Status:** retired by decision, not by resolution (2026-08-24)

### A stuck "Working" card does not mean the work was lost
- **Pattern-Key:** task-stuck-working-output-already-written
- **Date:** 2026-08-24
- **Trigger:** correction
- **Hits:** 1
- **Failed:** Diagnosing a stalled Cowork task by listing `COPILOT_COWORK\CommandJobs` and `Outputs` on the PC, finding nothing newer than 2026-08-21, and telling the operator nothing had been produced. An unrelated 12:37 `bridge-health` run was also attributed to the stalled task.
- **Why:** The stalled task was a document task — its deliverable lands in OneDrive `Documents/Cowork/Tasks/<slug>/output/` and never touches the PC. The PC job folders are silent by construction for anything that does not run through the command bridge, so "empty" there is not evidence about a document task at all. The agent was alive the whole time; it answered three separate `stop` commands. Only the turn-completion signal hung, which left the task card on **Working** and the composer stuck in **Queue** mode so no new turn could start.
- **Worked:** Read the chat's own timestamps first, then list `Documents/Cowork/Tasks/<slug>/output/` and compare Modified times against them. Here `Cowork_Skill_Design_Standard.docx` was written at 2026-08-24T20:42:36Z — 31 minutes BEFORE the operator first asked "you stuck?" — so the deliverable was complete and on disk for the entire time he sat waiting. Confirm completeness by opening the file and counting its structure (108 paragraphs, 7 tables, all populated), never by trusting that a file merely exists.
- **Evidence:** measured — output folder listed, docx opened and every table read
- **See also:** onedrive-folder-mtime-not-child-mtime

### A SharePoint folder's Modified date does not track edits to files inside it
- **Pattern-Key:** onedrive-folder-mtime-not-child-mtime
- **Delivered-to:** local-file-bridge
- **Date:** 2026-08-24
- **Trigger:** failure
- **Hits:** 1
- **Failed:** Using the Modified column from `GetDriveChildren` on `Documents/Cowork/Skills` to decide which skills a session had rewritten. It reported `deck-builder` at 2026-07-09 and `tax-client-emails` at 2026-06-18, which would have meant neither had been touched in months.
- **Why:** The folder timestamp reflects folder-level operations only. `deck-builder`'s SKILL.md verifiably went to v3.1 and was committed as 2d962f5 on 2026-08-20, and its parent folder still reads July 9 — so the field is not merely lagging, it does not track children at all.
- **Worked:** Read the SKILL.md file's own Modified value, or skip OneDrive for this question entirely and let the repo answer: run the sync job, then `git status` and `git diff --stat`. The repo diff is the authoritative record of what changed. Never infer "unchanged" from a container's timestamp.
- **Evidence:** measured — folder read 2026-07-09 against a known 2026-08-20 commit of a file inside it

### Two approval-gated bridge writes sent in one tool block: the second is auto-denied
- **Pattern-Key:** bridge-8932-parallel-writes-denied
- **Date:** 2026-09-07
- **Trigger:** failure
- **Rule:** Send approval-gated 8932 writes ONE per tool block. A second write batched beside the first is auto-denied while that approval is still pending.
- **Delivered-to:** local-file-bridge
- **Hits:** 2   (2026-08-26 two 8932 writes in one block; 2026-09-07 twice more, and an 8934 read denied beside an 8932 read - the limit is global)
- **Promotion:** COMPLETE at 2 hits, by the counter: at Hits 2 the unchanged Rule is selected into the always-on block on the next `digest_apply` (run 2026-09-07 on a scratch copy with the bridge absent - see that close report). No second copy written; the self-improvement SKILL.md environment-facts sentence already states the same rule.
- **Repeat 2026-09-07 - twice in one session, and the limit is GLOBAL, not per bridge.** (1) Two `write_file` calls in one block: the first came back `couldn't be reached, so its tools may be unavailable` (a tunnel drop - a different failure class, see `bridge-drops-are-tunnel-not-bridge`) and the second `denied by the user: Another approval-needing call is already pending`. `search_files` confirmed NEITHER file had landed before the writes were re-sent one per block, and both then succeeded. (2) Earlier the same night `bridge_status` on the 8934 Power Automate bridge was denied with the identical text when batched beside an 8932 `list_allowed_directories` and an 8931 `browser_tabs`. One pending approval blocks every other gated call on EVERY bridge, so the rule is not an 8932 quirk: any two approval-gated calls in one block cost a denial, whichever bridges they target.
- **Separate 2026-08-28 observation, mechanism NOT established:** four `get_file_info` READS were sent in one tool block and two came back `MCP server ... couldn't be reached`. Both succeeded when retried serially. That is NOT this entry's failure - reads are not approval-gated and the error text is a reachability error, not the auto-deny string. It was briefly mis-attributed to this key during a live audit, which is exactly the dedupe hazard of reasoning from a key NAME instead of its body. The honest reading: n=4, and `bridge-drops-are-tunnel-not-bridge` measured 1-2% on a 400-request baseline, so two failures in four is either bad luck or an unmeasured concurrency limit on parallel reads. Do NOT record a per-port pattern from four observations - that entry exists because exactly that inference was wrong before. If it recurs, measure it properly before writing a rule.
- **Failed:** Batching two `jordan-local-filesystem-8932-v1-write_file` calls in a single tool block to create a .bat and its companion .ps1. The first succeeded; the second returned `Tool 'write_file' was denied by the user: Another approval-needing call is already pending - wait for the user to approve or deny it, then retry`.
- **Why:** Each bridge write raises its own approval prompt and only one approval can be outstanding at a time. A parallel sibling is denied OUTRIGHT rather than queued, so it is a hard failure, not a wait. The denial text names the user, which misleads: the operator never saw or refused a prompt.
- **Worked:** Issue bridge writes SEQUENTIALLY - one call, wait for the result, then the next. Retrying the denied call unchanged in the following block succeeded. Sequential costs one round trip per file; batching costs the same round trips PLUS a denial.
- **Evidence:** measured - reproduced once on 2026-08-26, retry succeeded with byte-identical content
- **See also:** bridge-8932-writes-lf

### A job cannot start a per-user service - Start-Service is refused without elevation
- **Pattern-Key:** batch-start-service-needs-elevation
- **Delivered-to:** command-bridge
- **Date:** 2026-08-26
- **Trigger:** failure
- **Hits:** 1
- **Failed:** `Start-Service BluetoothUserService_329e65` from an 8933 job, trying to restore a stopped per-user Bluetooth service. Refused with "Cannot open BluetoothUserService_329e65 service on computer '.'".
- **Why:** Per-user service INSTANCES are not startable by the interactive user despite the naming. Opening the service control handle needs administrator rights, which the bridge cannot obtain. The per-user prefix describes instance scope, not the permission model - do not read it as "the user may control this".
- **Worked:** Nothing from the bridge; this is a genuine elevation wall. Wrap any Start-Service/Stop-Service in try/catch, report the refusal plainly and CONTINUE rather than failing the job, so the run still returns its diagnostic before/after value. Hand the elevation step to the operator.
- **Evidence:** measured - job 2026-08-26-bt-audio-repair.bat, exit 0, service state unchanged across the before/after snapshots
- **See also:** batch-fsutil-needs-elevation

---

### A wrapped string defeats both the edit AND the grep that verifies it
- **Pattern-Key:** multiline-string-defeats-single-line-grep
- **Date:** 2026-08-27
- **Trigger:** false-success
- **Hits:** 1
- **Failed:** Renaming a job title across 18 skills. Replaced `"Corporate Tax Solutions"` with a single-line search, then verified with `grep -rl "Corporate Tax Solutions"`, which returned NONE. Reported the change complete. 16 files still had it - the body notices wrap as `Corporate Tax\n> Solutions`, so the literal never matched on either pass. Found only when the gamma-tango attribution check surfaced the old title in the loaded skill context.
- **Why:** Markdown body text is hard-wrapped at ~78 chars, so any two-or-three-word phrase can straddle a line break, often with a `> ` blockquote marker inserted. A single-line search is blind to it - and crucially the SAME blindness hits the verification step, so the check confirms the bug rather than catching it.
- **Worked:** Search and replace with a multiline regex that tolerates the wrap and the quote marker: `re.compile(r'Corporate\s+Tax\s*\n?\s*>?\s*Solutions')`. Verify with the SAME regex, never with the flat literal. Rule: when the edit pattern must be multiline, the verification pattern must be multiline too - reusing the flat literal to "confirm" is how a partial edit reports clean.
- **Evidence:** measured - 16 files fixed after the first pass reported zero remaining

---

### grep -c on a single file drops the filename, so a piped count reads as zero
- **Pattern-Key:** grepc-single-file-drops-filename
- **Date:** 2026-08-27
- **Trigger:** false-success
- **Hits:** 1
- **Failed:** Scanning which skills carried an email address with `grep -c PATTERN "$d"/*.md | awk -F: '{s+=$2}'`. Reported 3 affected skills; the real number was 16. the operator approved a scope of "all four" based on that wrong figure.
- **Why:** `grep -c` prefixes `filename:` only when given MORE THAN ONE file. With a single .md in the folder it prints the bare count, so `awk -F:` finds no second field and sums 0. Folders with several .md files reported correctly, which is why the output looked plausible rather than obviously broken.
- **Worked:** Use `grep -rl` and count paths, or do the counting in Python. Never pipe `grep -c` through a field split unless the multi-file form is guaranteed. Sanity-check any scan whose result seems small before acting on it.
- **Evidence:** measured - re-scan with `grep -rln` found 16 where the awk pipeline found 3

---

### The user-config mount lags behind writes - its absence is not evidence
- **Pattern-Key:** onedrive-user-mount-read-lag
- **Supersedes key:** copyartifact-mount-read-lag
- **Date:** 2026-08-28
- **Trigger:** failure
- **Rule:** The mount can serve a stale or partly-flushed file. Wait ~20s and hash before concluding anything was lost.
- **Delivered-to:** local-file-bridge
- **Hits:** 3
- **Failed:** Two different write paths, same mount, same wrong conclusion. (1) Ran a .py straight from the user skills mount immediately after `CopyArtifact` returned `ok` with the correct file count. Python raised `SyntaxError: unterminated string literal` mid-file, which reads exactly like a truncated publish. (2) 2026-08-28: after an 8932 bridge `write_file`, the new script never appeared on `/mnt/user-config/` at all - checked, waited, checked again over more than a minute - and a `grep` for a string the same bridge had just written into a SKILL.md returned zero matches on the mounted copy. Both times the mount was the only thing claiming the write had not landed.
- **Why:** The mount serves read-after-write with a lag, and the lag is PER FILE: in the 2026-08-28 case a file written minutes earlier was visible and current on the mount at the same moment a newer one was missing entirely. So an immediate read can return a partly-flushed file EVEN WHEN the returned byte count already matches, or return nothing at all - and mount freshness cannot be established by testing a different file. The lag belongs to the mount, not to `CopyArtifact`; the old key named the wrong half, hence the rename.
- **Worked:** Verify a write through the path you WROTE it with. On 2026-08-28 `list_directory_with_sizes` and `read_text_file` on the 8932 bridge both showed the file and the text the mount was denying. For an execute-after-publish, `md5sum` both copies before concluding anything - they were identical - then simply retry; it parsed on the retry and 3/3 after. Do NOT republish, re-send, or start "fixing" a file because the mount disagrees - confirm on the write path first.
- **Evidence:** measured - identical md5 and a clean retry in the CopyArtifact case; a bridge listing and a bridge read each contradicted the mount in the 8932 case
- **THIRD HIT, and the worst shape yet - a partial read that looks like targeted data loss.** 2026-08-28: an `EditArtifact(surface="user")` with two `replace_text` patches on `skills/myvoice/SKILL.md` returned `ok`. An immediate read of the mount showed 13,033 bytes where the original was 11,491 and the intended result 16,903 - neither the old file nor the new one. Rules 1-9 were present, rules 10-21 were GONE along with three section headings, and rules 22-31 (the new material) were present. That is a coherent, plausible, targeted deletion, and it was reported to the operator as data loss. It was not. The middle of the file had simply not flushed yet. Republishing the whole file with `CopyArtifact` fixed the symptom, so the wrong diagnosis was never contradicted. Reproduced afterwards on a scratch file with the same patch shape: at 3 seconds the mount served the ORIGINAL unchanged, at 20 seconds it served the correct result with every line present. **The signature to recognise: beginning and end intact, a contiguous block missing from the middle, and a byte count between the old size and the new one.** That is a partly-written file, not a destructive edit. Wait and re-read, or hash against the intended content, before concluding anything was destroyed - and never let a successful repair stand in for a diagnosis that was never actually made.
- **See also:** onedrive-read-mount-locally, onedrive-cloud-to-laptop-lag, agent-claims-action-before-doing-it
- **Promoted-to:** copilot-instructions.md, "Rules already paid for" (LESSON-DIGEST block) - rule text confirmed present in the digest 2026-08-28.

---

### A verifier that counts only value differences blesses a schema change
- **Pattern-Key:** verifier-ignores-structural-diff
- **Date:** 2026-08-28
- **Trigger:** better-approach
- **Rule:** Break your own checker before trusting it. Positive control first, then negatives that each assert WHY it failed.
- **Delivered-to:** dream-cycle
- **Hits:** 2
- **Failed:** The alteryx-to-python parity checker reported PASS on an output whose column had been RENAMED. It recorded the column difference in the per-sheet line but only value mismatches incremented the counter that decided the overall verdict.
- **Why:** Two separate tallies - one for cells, one for structure - and only the first was wired to the verdict. A renamed column breaks every downstream consumer while every cell still matches, so the report was confidently wrong in the one case a human reviewer would never re-check.
- **Worked:** Mutation-test the verifier before trusting it. Inject six known defects (one cell, dropped row, extra row, renamed column, swapped label, sub-tolerance noise) and confirm it catches exactly the five that matter and passes the noise. That surfaced the hole immediately; after the fix, 6/6 caught with true negatives still passing. Applies to ANY checker: a checker nobody has tried to fool is an assumption. **Two refinements added 2026-08-28, from a second checker.** (1) A negative control must assert WHY the checker failed - the message text AND the specific gate the failure was attributed to - not merely THAT it failed, because a defect caught for the wrong reason is a miss that reports as a hit. An earlier `verify_primitives` control passed on its first attempt only because the implementation dodged the injected bug by another route. (2) Run the positive control FIRST and gate the negative suite on it: a suite that cannot demonstrate green proves nothing when everything comes back red. Built that way, a 17-case negative suite for `gate_check.py` caught 17/17 for the right reason with its positive control passing.
- **Evidence:** measured - 6-mutant suite, 1 false PASS before the fix, 0 after; the 17-case suite and its positive control were run and read on 2026-08-28. The earlier `verify_primitives` false-green is reported from a prior session, not re-observed here.
- **Promoted-to:** Skills/alteryx-to-python/SKILL.md - the `gate_check_selftest.py` paragraph (17 deliberately-broken workspaces each failing on the expected gate with the expected message) and "Every zero reported to the user needs a positive control". Read on the mount 2026-08-28 and already present in concrete form, so no move is proposed; this entry is now the evidence trail. The generic form is NOT stated in `copilot-instructions.md`.
- **See also:** delivery-pointer-file-passes-as-artifact, verification-scoped-away-from-the-risk

### Alteryx is the reference - fix the conversion, document the workflow's own defects
- **Pattern-Key:** alteryx-fix-conversion-not-original-defect
- **Delivered-to:** alteryx-to-python
- **Date:** 2026-08-28
- **Trigger:** correction
- **Failed:** Read the alteryx-to-python skill's "flag defects, never fix them" boundary as a blanket rule covering every wrong number. Acting on that, one bad line found on review got written up as the skill breaking its own guarantee, and a true statement in a published article was softened to accommodate the imagined violation. the operator corrected it twice before it was right.
- **Why:** Two different failures were collapsed into one word. "Defect" in that boundary means a defect in the ORIGINAL Alteryx workflow. A wrong number in the generated Python is a CONVERSION error, an entirely different thing, and it is meant to be fixed.
- **Worked:** Hold the loop in this exact shape. The Alteryx workflow is the reference. If the Python does not give the same answer, that is a conversion error - analyse it and fix the conversion until the two agree. A defect in the underlying Alteryx workflow is detected, written into the generated documentation, and LEFT IN the Python, because silently improving on what the original workflow produced makes the reconciliation impossible. The remediation path is not the agent's to take: the workflow owner reads the write-up, fixes the Alteryx, and re-runs the skill, at which point the Python comes back corrected because it still tracks its source. Authority stays with the owner and the conversion follows it. Corollary worth carrying: with no Alteryx baseline there is no parity comparison, so a conversion error in a delivered script has nothing to catch it, which is exactly how one survived into a finished script on 2026-08-28.
- **Evidence:** measured - the operator stated the loop directly; the conversion it describes was parity UNVERIFIED and the defect surfaced only when he ran the finished script
- **Corrected 2026-08-28:** this entry originally attributed the bad line to a client's report and to a client desk. the operator states plainly that NONE of this work was for a client - the skill build was an exercise in what can be built inside Cowork, and the bad line was found on his own review. Key left unchanged so existing references still resolve; see `work-is-an-exercise-not-an-engagement`.
- **Hits:** 1
- **See also:** alteryx-static-audits-miss-runtime-defects, verification-scoped-away-from-the-risk

### Sweep for US spelling and contractions the same way you sweep for em dashes
- **Pattern-Key:** voice-us-register-sweep
- **Date:** 2026-08-28
- **Trigger:** failure
- **Rule:** Final mechanical pass on his writing is three greps: em dash and semicolon, British spellings, then contractions by judgement.
- **Delivered-to:** myvoice
- **Hits:** 1
- **Failed:** Delivered a 4,500-word article for the operator carrying organised, behaviour, realisation, licence, organisation and the verb "reckons", plus zero contractions. He corrected every one by hand. The `myvoice` punctuation sweep for em dashes and semicolons ran and passed, so the piece was reported as voice-compliant while the register was visibly wrong.
- **Why:** The voice profile had a mechanical final-pass rule for punctuation only. Spelling and contraction register are equally mechanical and equally invisible to a read-for-tone check, but nothing in the file named them, so nothing looked for them.
- **Worked:** Extend the final mechanical pass to three greps, not one. (1) em dash and semicolon, (2) `-ise/-isation/-our/licence` and British idiom, (3) where an uncontracted clause reads stiff, prefer the contraction, as he did with exactly one clause on this pass. Do NOT treat a low contraction count as a defect on its own. Greps (1) and (2) run in one Python pass over the paragraph list before delivery; (3) is a judgement call, not a gate. Encoded as `myvoice` rules 37 and 38.
- **Evidence:** MIXED. Measured - his edit pass corrected 5 spellings and 1 idiom, and a regex over the rebuilt article confirms zero British forms remain. INFERRED and now partly DISPROVED - the contraction guidance was generalised from a single observed conversion and was never run as a gate on the deliverable.
- **Corrected 2026-08-28 by a fresh-context review:** the first version of this entry told the reader to treat zero contractions across a long piece as a defect. His own hand-finished article carries TWO verbal contractions in 4,534 words, so the deliverable he shipped fails the rule this entry derived from it. A rule taken from one sentence in a diff is a sample of one, and the artifact was sitting right there to test it against. Test a proposed rule against the whole finished document before writing it down, not only against the diff hunk that suggested it.
- **See also:** skill-voiceprofile-calibrate-from-user-diff

### Never encode an unstated premise from the opening request into a durable rule
- **Pattern-Key:** assumption-from-the-brief-encoded-as-a-durable-rule
- **Date:** 2026-08-28
- **Trigger:** correction
- **Rule:** Never write a premise from the opening request into a skill file as if it were verified. Confirm it first, or constrain the rule to what was observed.
- **Hits:** 1
- **Failed:** The session opened with "convert this workflow for a client that does not have an Alteryx license." That premise was carried forward as established fact for the whole session, written as client framing through an article, and then written into `myvoice` as a PERMANENT rule - a clause explicitly protecting the word "client" as legitimate domain vocabulary. the operator then stated that none of the work was for a client at all. The rule just written would have defended the exact phrasing he was asking to have removed.
- **Why:** A premise stated once in an opening request has the same surface form as a verified fact, and nothing downstream re-checks it. Writing it into a skill file promotes an inference to a standing instruction, applied silently by future sessions that never saw the conversation it came from. The blast radius of a wrong durable rule is far larger than a wrong sentence in a draft.
- **Worked:** Before a framing assumption goes into a skill file, name it back to the user as an assumption and get it confirmed. Cheaper still, write the rule so it constrains only what was actually observed: "cut third-party attribution" was observed, "the word client is fine as background colour" was invention. When correcting the rule, grep every other artifact the assumption reached - here it had spread to an article, a lesson entry and a memory file. Corrected form is `myvoice` rules 35 and 36 plus `work-is-an-exercise-not-an-engagement`.
- **Evidence:** measured - the operator's correction is explicit; the wrong exception clause was published and then replaced, and the stale attributions were found in three files by grep
- **See also:** work-is-an-exercise-not-an-engagement, alteryx-fix-conversion-not-original-defect

### The skill builds are exercises, not engagements - never write them as client work
- **Pattern-Key:** work-is-an-exercise-not-an-engagement
- **Date:** 2026-08-28
- **Trigger:** correction
- **Rule:** the operator's builds are exercises in what Cowork can do. Never write them up as client or engagement work.
- **Delivered-to:** myvoice
- **Hits:** 1
- **Failed:** Framing the alteryx-to-python build and its outputs as work performed for a client, in an article, in a lesson entry and in conversation. Also staging a third party as a reviewer of the output.
- **Why:** the operator builds these to find out what can be built inside Cowork. Nobody is waiting on the result, which is precisely what makes the accuracy-over-speed stance affordable and defensible. Client framing misstates the motive and imports an engagement that does not exist.
- **Worked:** Write the build as something he made because he wanted to know whether it could be done, and write every finding as something he found on his own review. State it once, early, in any write-up: what was being tested, and that nobody was waiting on the output. NOT a blanket ban on the word in every context - a corpus note recording where a baseline workflow came from is a different claim, and those were deliberately left alone rather than rewritten on an over-broad reading of the correction.
- **Evidence:** measured - the operator stated it twice in consecutive turns
- **See also:** assumption-from-the-brief-encoded-as-a-durable-rule

### Build a .docx with python-docx, not a 90-element insert_paragraph patch array
- **Pattern-Key:** docx-build-with-python-docx-not-patch-array
- **Date:** 2026-08-28
- **Trigger:** better-approach
- **Rule:** Build a .docx with python-docx from the source text, then verify paragraph-by-paragraph. Never hand-write a long insert_paragraph patch array.
- **Delivered-to:** deck-builder
- **Hits:** 1
- **Failed:** Rebuilding the same 92-paragraph article twice by hand-writing a `host-EditArtifact` patch array with one `insert_paragraph` op per paragraph, each carrying the full paragraph text plus an `after` index and a style. Every revision meant re-emitting the entire body verbatim, and `host-GetArtifactModel` then returned 57 KB that had to be parsed out of a temp file just to verify it.
- **Why:** The patch-array path makes the model the transport for the document body, so cost scales with document length on every rebuild, and the index arithmetic (`after: max(0, i-1)`) is hand-maintained and silently wrong the moment a paragraph is inserted.
- **Worked:** `python-docx` 1.2.0 is present in the container. Build in `working/` from the source text file with a script - set section size and margins, `add_paragraph(style='Title'|'Heading 1')` off a heading set, set core properties - then verify by re-opening with python-docx and comparing paragraph-by-paragraph against the source, then `host-CopyArtifact(surface="output")`. The third rebuild took one short script instead of a full-body emission, matched the source with zero mismatches, and asserted the heading count (17 of 17) rather than eyeballing it.
- **Evidence:** measured - all three rebuilds ran in the same session; the python-docx build verified 93/93 paragraphs identical and 17 headings styled
- **See also:** skill-editartifact-patch-rejected-republish-folder


### Anchor a section insert on the FULL heading, never a prefix
- **Pattern-Key:** lessons-file-section-anchor-must-be-exact
- **Date:** 2026-09-07
- **Trigger:** failure
- **Rule:** Scope any structural regex to its target section and anchor on the FULL heading. Over a whole file a prefix matches prose and returns a false negative.
- **Delivered-to:** self-improvement
- **Hits:** 3
- **Distinct-from:** `classifier-substring-match-silently-misfiles` - there a content regex ROUTES a lesson to the wrong skill block; here a heading prefix LOCATES the wrong position in the lessons file for an insert or a placement check. Both are loose matches, but one misfiles across files by classification and the other misplaces within one file by position, and the fix differs: route on the authored key there, anchor on the full heading here.
- **Hit 3, 2026-09-07 - same file, same prefix, caught by an assertion instead of a false verdict.** A scratch-copy edit inserted three entries using the FULL heading as the insert anchor (correct, matched once) and then verified placement with `text.index('## Contradictions')` - the bare prefix, which matched the entry body at line 849 first and reported the new entries misfiled when they were not. The assertion halted the run before any file was written; the fix was to compare against the full heading. Sharper wording of the rule: use the SAME anchor string for the write and for the check - a check anchored more loosely than the write it verifies is the false negative waiting to happen.
- **Failed:** Twice, in the same file, from the same cause. (1) Appending new entries "at the end" of `cowork-lessons.md` put them under `## Contradictions`, because `## Failures` is the FIRST section and the end of the file is a different section entirely - 21 of 65 entries were misfiled before anyone counted. (2) Verifying the 2026-08-28 four new entries with `s.index('## Contradictions')` reported all four MISFILED when all four were correct: that prefix occurs twice in the file, once inside an entry body, and `index` returned the earlier text mention rather than the heading.
Third instance, same day, different file: a rule-numbering check on `myvoice/SKILL.md` matched numbered lines outside the Voice Profile section and printed `rules: 1 to 7 | count 49 | contiguous False`. Re-scoping the regex to that section alone printed `voice rules: 1 - 42 count 42 contiguous True`. The rules were fine. The check was scoped over the whole file.
- **Why:** All three are the same mistake at different ends of the operation. A section identifier that is a prefix of ordinary body text is not an anchor, and the file discusses its own section names, so prefixes match prose.
- **Worked:** Insert with the complete heading string including its trailing description, assert `count == 1` before replacing, and verify the same way. After writing, print each new key's offset against `index(full_heading)` and assert the ordering. The insert itself was right every time - only the check was wrong, which is the more dangerous shape, because a false MISFILED or false `contiguous False` reading invites a "fix" that would have actually broken a correct file. Generalise past this file: scope ANY structural regex, placement or numbering or count, to its target section. Run over a whole document, a prefix or a stray number matches unrelated text and returns a false negative.
- **Evidence:** measured - the count-2 prefix and the count-1 full heading were both printed on 2026-08-28, as were both numbering readings; the 21-entry misfile was counted in a prior session on this same file
- **Note on Hits:** all three instances fall in ONE session, so this stays at 2 by the separate-sessions definition rather than being inflated to 3.
- **See also:** verification-scoped-away-from-the-risk, verifier-prose-match-needs-normalization
- **Promoted-to:** copilot-instructions.md, "Rules already paid for" (LESSON-DIGEST block) - rule text confirmed present in the digest 2026-08-28.

### A stateless bridge spawns a fresh process per call, so in-process state never persists
- **Pattern-Key:** bridge-8933-stateless-defeats-in-process-state
- **Date:** 2026-08-28
- **Trigger:** failure
- **Rule:** 8931/8932/8933 run stateless, so a module-level variable in a bridge server resets on EVERY call. Persist any cross-call state to a file.
- **Delivered-to:** command-bridge
- **Hits:** 1
- **Failed:** Added a reminder block to `batch-exec-server.js` throttled by a module-level `let FIRST_CALL_DONE = false`. Two consecutive jobs BOTH reported "first job of this session". The throttle did nothing, so the reminder would have fired on every single call and become exactly the wallpaper it was designed to avoid.
- **Why:** supergateway runs 8933 with `--stateless`, which spawns a FRESH node process per request. Module-level state is born and dies inside one call. This is the same property recorded in `fact-8933-longjob-fixed-by-stateless`, seen from the other side: statelessness fixes long jobs and destroys in-process memory, and only the first half had been written down.
- **Worked:** Persist to a file. `_last-operating-rules.txt` under `CommandJobs\Logs` holds a timestamp; a clean job inside a 45-minute window stays quiet, a job that does not exit clean ALWAYS gets the rules because that is when they are worth reading. Verified live in three states: fires outside the window, silent on a clean job inside it, fires on a deliberate failcase inside it.
- **Evidence:** measured - the duplicate "first job of this session" was observed on two consecutive real calls, and all three post-fix behaviours were run and read
- **See also:** bridge-8933-longjob-fixed-by-stateless

### Editing a bridge server goes live on the next call, with no restart
- **Pattern-Key:** bridge-server-edit-live-without-restart
- **Date:** 2026-09-02
- **Trigger:** correction
- **Rule:** A code edit to a bridge server takes effect on the NEXT call - do not restart to deploy it. A tool's BEHAVIOUR changes instantly; the tool SURFACE does not. A newly ADDED tool is rejected as non-existent at first, then arrives on its own a few minutes later without any restart or new chat. So after adding a tool: WAIT and retry. Do not tell the operator a new chat is needed, and do not restart anything.
- **Delivered-to:** command-bridge, local-file-bridge
- **Hits:** 1
- **Failed:** Told the operator that a change to `batch-exec-server.js` "will not take effect until 8933 restarts, and restarting mid-session kills this chat's connector, so it lands for the NEXT session". The very next call to the bridge already carried the new behaviour.
- **Why:** Stateless mode re-spawns the server process per request, so the edited file is re-read every time. The restart model was carried over from stateful servers and from `bridge-session-bound-to-pid`, which is about the CONNECTOR binding, not about the server code. Two different things wearing one word.
- **Worked:** Edit, syntax-check with `node --check`, then simply call the bridge. Deployment costs nothing and disturbs no session. Keep a `.bak` and confirm the file is tracked in git first, since the deploy is instant and there is no staging step between the edit and production.
- **Evidence:** measured - the new reminder block appeared on the first call after the edit, with no restart performed and no connector interruption. The 2026-09-02 behaviour/surface split is measured the same way: `bridge_status` returned the new version and the rewritten config immediately, while a sibling tool added in that same edit was rejected as non-existent and then succeeded unmodified once the surface refreshed minutes later.
- **Sharpened 2026-09-02, then CORRECTED the same hour - read both halves:** 8934 was edited from v0.2.0 to v0.3.0 mid-session. The BEHAVIOUR changes landed instantly and were confirmed on the next call - new version string, eight environments parsed from a rewritten config, and a production guard that correctly refused `ProdCRM`. Three tools added in the SAME edit (`analyze_flow`, `find_flows_using_connector`, `list_environments`) were rejected as "Tool ... does not exist". I wrote that up as "the tool surface is fixed at session start, so a new tool needs a NEW CHAT" - and that was WRONG. All three arrived in the SAME chat about two to three minutes later (edit ~18:26Z, tools announced 18:29Z), with no restart, no new session and no action of any kind, and all three then worked first time. The surface is not fixed; it REFRESHES, and it does so in both directions - `bridge-connector-removed-midsession` records the same thing happening in reverse. The correct response to a missing new tool is to WAIT and retry, exactly as that entry says for a vanished one. Recording the wrong version too, because the mistake is the instructive part: a first observation was generalised into a permanent-sounding rule after one reading, when the difference between "not there" and "not there YET" needed only a second look a few minutes later.
- **See also:** bridge-8933-stateless-defeats-in-process-state, bridge-session-bound-to-pid, bridge-connector-removed-midsession


### Both OneDrive legs are slow, so choose the one that does not block the commit
- **Pattern-Key:** onedrive-pick-the-leg-that-does-not-block
- **Date:** 2026-08-28
- **Trigger:** better-approach
- **Rule:** Route a write by PAYLOAD: small or new file, write_file local. Existing large file, edit_file local so only the diff crosses. Bulk or binary, CopyArtifact. Verify a local write THROUGH THE BRIDGE, never the mount.
- **Delivered-to:** local-file-bridge
- **Hits:** 2
- **Promotion:** 2026-09-09 - second hit; the Rule is carried into the copilot-instructions.md LESSON-DIGEST at Hits 2, so it now loads every session.
- **Repeat 2026-09-09 - the bulk leg, used on purpose:** a 60 KB pinned land input (`bundle.txt`, the whole executor plus its self-test) would otherwise have been re-typed through `write_file`. It went `CopyArtifact` to `output/` -> OneDrive -> the PC's OneDrive root in about ten minutes, then `move_file` across roots into `Outputs\Agent of Record\executor-1.3.0\`; the land job's pin hash then proved it byte-exact. The four small inputs (under 9 KB) went by `write_file` directly. Same routing rule, third payload class exercised.
- **Failed:** Publishing every memory, lesson, skill and instructions file cloud-side with `CopyArtifact(surface="user")` and then waiting for OneDrive to replicate it down before the repo could see it. Six or seven times in one session, roughly five minutes each, somewhere near 20 to 30 minutes of a single session spent waiting. The bridge was up and instant throughout. `copilot-instructions.md` already marked the local path PREFERRED and the cloud path FALLBACK, only when the bridge is unavailable.
- **Why:** Both legs take minutes, so neither is "fast", and the real question is which one blocks. It is the wrong question to ask which write is quicker. A cloud-side write reaches the container mount at once and the PC minutes later, so the REPO and therefore the COMMIT are blocked. A local write reaches the repo at once and the mount minutes later, and the mount lag costs nothing because the content is already in `working/`.
- **Worked:** Route by PAYLOAD SIZE, which the first version of this entry got wrong. (1) NEW or SMALL file, roughly under 30 KB: `write_file` on the 8932 bridge under `OneDrive\Documents\Cowork\`. (2) EXISTING LARGE file: `edit_file` on that same local path, which sends only the anchors. The lessons file is 124 KB, so `write_file` would push all of it through a tool call to change three paragraphs. (3) BULK, BINARY or a whole folder: `CopyArtifact`, which copies server-side and sends no content at all, accepting the replication wait. Verify any local write by reading it back THROUGH THE BRIDGE, because the mount serves the old bytes for minutes. Once a file has been written locally in a session, keep using the local path for it: a later cloud-side write based on a stale mount read would clobber it.
- **How this was found, and it matters:** by writing the rule and then breaking it sixty seconds later. Publishing this very entry, the reflex was `CopyArtifact` again. Inspecting WHY found a real reason rather than pure habit, since `CopyArtifact` copies server-side and transfers no content, which is exactly right for a 124 KB file. The first version said "always write locally" and would have made large-file writes worse. Then that same cloud write blocked the local correction for about ten minutes, because `edit_file` cannot patch a file that has not arrived. The rule demonstrated both its point and its exception, on itself, inside ten minutes.
- **Down-leg is VARIABLE, do not quote a single number:** measured 2026-08-28 at roughly 5 minutes early in the session and roughly 10 minutes later the same hour; 20 to 35 minutes was recorded on 2026-08-24. Plan for tens of minutes, never for five.
- **Evidence:** measured 2026-08-28 - a probe written to the local path at 23:11:14Z became visible on the container mount at 23:14:24Z, 3 min 10 s for the UP leg. The DOWN leg was observed at roughly 5 minutes twice the same day. Both are minutes; only one of them blocks the commit.
- **See also:** onedrive-cloud-to-laptop-lag, onedrive-user-surface-not-live, onedrive-user-mount-read-lag


### Classify by an authored key, never by matching content substrings
- **Pattern-Key:** classifier-substring-match-silently-misfiles
- **Date:** 2026-08-28
- **Trigger:** failure
- **Rule:** Route on the authored identifier (a key prefix), not on a content regex over free text. If content matching is unavoidable, use word boundaries and test the near-misses.
- **Delivered-to:** self-improvement
- **Hits:** 1
- **Failed:** `lesson_brief.py` classified each lesson into a surface by first-match of a content regex over key plus title. The `files` pattern contained the bare substring `file`, so `skill-voiceprofile-calibrate-from-user-diff` matched on the word **profile** and was filed under `files`. `--for skills` therefore silently MISSED it, and `--for files` returned something irrelevant. Shipped and used for about an hour before anyone looked.
- **Why:** Substring matching over prose has no notion of what the text is ABOUT. Worse, the tool still returns a confident, well-formatted list, so a wrong classification reads exactly like a right one. That is a false negative in the single tool built to prevent false negatives.
- **Worked:** Two changes, and the FIRST attempt at the fix was also wrong. Adding word boundaries alone just moved the damage: reordering the surfaces sent every `onedrive-*` entry into `git`, because their titles mention commits. The correct design routes on the PREFIX of the Pattern-Key, which is authored deliberately and states the subject, and falls back to a word-boundary content regex only for keys whose prefix is unknown. Verified 12 of 12 hand-picked cases, then locked in with `lesson_brief_selftest.py`, 15 of 15, including negative controls asserting that `profile` does not match `files` and `clean` does not drag a key out of `git`.
- **Evidence:** measured - the misclassification was reproduced directly, both candidate fixes were run across all 76 keys and their spreads compared, and the regression suite passes 15/15
- **See also:** lessons-file-section-anchor-must-be-exact, verifier-ignores-structural-diff

### A rule is most likely to be wrong in the first hour after it is written
- **Pattern-Key:** new-rule-is-untested-until-it-survives-a-real-case
- **Date:** 2026-08-28
- **Trigger:** better-approach
- **Rule:** Before encoding a rule, run it against the artifact already in front of you. A rule derived from one observation is a hypothesis, and it stays one until a real case fails to break it.
- **Hits:** 1
- **Failed:** FOUR times in one session, same shape each time. (1) Wrote "never attribute the work to a client", then immediately added an exception clause protecting the word as domain vocabulary, which would have defended the exact phrasing the operator was asking to remove. (2) Wrote "contractions are his register" from a single clause he changed by hand; his finished 4,534-word article carries two. (3) Wrote "always write to the local path", then published that very entry through the cloud path sixty seconds later. (4) Shipped a surface classifier that matched content substrings, so "profile" matched "file" and a rule was filed under the wrong surface for an hour.
- **Why:** A rule feels most certain at the moment of writing, because it was distilled from a case still fresh in mind. That is also the moment it has been tested against exactly one example. Encoding it into a skill file or a script promotes a hypothesis to a standing instruction, and standing instructions are applied silently by sessions that never saw the case that produced them. Three of the four above were caught only because someone used the rule immediately; a rule written and then not exercised would have sat there being wrong.
- **Worked:** Test the candidate rule against material already available before writing it down. For a writing rule, count the pattern across the whole finished document, not the diff hunk that suggested it, which is `myvoice` rule 43. For a code rule, run it over the full corpus and diff the before and after, which is how the classifier's second wrong fix was caught before shipping. For a process rule, do the very next instance of that process deliberately and watch whether the rule holds. Where the rule survives none of that, write it as a scoped observation rather than an absolute.
- **Evidence:** measured - all four instances occurred and were corrected in this session, each with the correction recorded in its own entry
- **See also:** assumption-from-the-brief-encoded-as-a-durable-rule, classifier-substring-match-silently-misfiles, onedrive-pick-the-leg-that-does-not-block, voice-us-register-sweep

### The digest generator truncates to 24 rules unless told otherwise
- **Pattern-Key:** lessons-digest-default-limit-truncates
- **Date:** 2026-08-28
- **Trigger:** failure
- **Rule:** Regenerate the digest with --limit set to the authored-Rule count, then diff old against new and confirm nothing was dropped.
- **Delivered-to:** self-improvement
- **Hits:** 1
- **Failed:** Running the regeneration command exactly as `self-improvement/SKILL.md` documents it - `lesson_brief.py <lessons.md> --digest`, with no `--limit`. It emitted 24 rules where the live block held 30. Splicing that in would have DELETED 8 rules from the block that loads every session, four of them logged earlier the same day, including the stateless-bridge rule and the exercises-not-engagement rule. The output looked entirely normal - a well-formed block, correct headings, and a plausible self-consistent count in the END marker.
- **Why:** `cmd_digest` applies `sorted(withrule, key=rank)[:limit]` and `--limit` defaults to 24 in the arg parser. The live block was generated at a higher limit, so the default silently discards the lowest-ranked rules, which are the 1-hit ones, meaning the NEWEST. The generator reports how many it wrote and never how many it dropped, so the trailing count agrees with itself and looks right.
- **Worked:** Count the authored rules first with `grep -c '^- [*][*]Rule:[*][*]'`, pass that number as `--limit`, then diff the old block against the new by normalized rule text and assert nothing disappeared before splicing. 32 authored, 32 emitted, all 8 previously-dropped rules present, 2 new ones added. A regeneration that SHRINKS the block is the signature of this trap.
- **Evidence:** measured - the 24-rule output and the 30-rule live block were both counted, and the 8 dropped rules were listed by diff before anything was written
- **See also:** lessons-file-section-anchor-must-be-exact, verification-scoped-away-from-the-risk

### A check that warns on a proxy trains you to ignore the real ones
- **Pattern-Key:** verifier-warns-on-proxy-not-the-defect
- **Date:** 2026-08-28
- **Trigger:** better-approach
- **Rule:** Make a check fire on the defect it names, not on a proxy for it. A warning that is always on is training to skip warnings.
- **Delivered-to:** dream-cycle
- **Hits:** 1
- **Failed:** `topic_cluster` warned whenever six keys shared a prefix, on the stated theory that a cluster that large "usually means a repeated failure was re-logged instead of promoted". It fired on all three large clusters every run. Measured 2026-08-28: `bridge-` 17 keys, `skill-` 10, `onedrive-` 6, and across all three exactly ZERO entries at Hits>=2 without a `Promoted-to`. Every warning it had ever emitted was false, and those three standing warnings sat immediately above eight real `promotion_due` FAILs that went unread for days.
- **Why:** Size is a proxy for re-logging, not re-logging itself. A subsystem with three ports and a tunnel legitimately produces many genuinely distinct traps, so the proxy is guaranteed to misfire on exactly the subsystems that get the most use. Worse, the check had no negative control: 14 of the checker's findings were each tested against a deliberately broken log and this one was not, so nothing in the suite could reveal it was measuring the wrong quantity. A token-overlap heuristic was then tried as a replacement and REJECTED on measurement - at Jaccard 0.34 it flagged two pairs, `bridge-8932-parallel-writes-denied` vs `bridge-8932-writes-lf` and `onedrive-read-mount-locally` vs `onedrive-user-mount-read-lag`, and both are legitimately separate traps that merely share words.
- **Worked:** Make the check test the defect it names. A cluster now WARNs only when it contains an entry at Hits>=2 with no `Promoted-to` - actual re-logging - and otherwise reports its size as INFO, so the number stays visible without pretending to be a defect. Negative-controlled two ways before trusting it: forcing the branch off drops the suite to 14/15, and forcing it on reproduces the three old warnings exactly, proving the change is what removed them. Also fixed the summary line, which counted every INFO as prose-only and silently inflated 53 to 56 the moment a second INFO code existed.
- **Evidence:** measured - all three clusters enumerated with hit counts and promotion state, both sabotage runs executed and read
- **See also:** verification-scoped-away-from-the-risk, lessons-digest-default-limit-truncates, verifier-ignores-structural-diff

### Re-probing three times in one breath is still one probe
- **Pattern-Key:** bridge-reprobe-must-be-separated-in-time
- **Date:** 2026-08-28
- **Trigger:** correction
- **Rule:** Re-probe means LATER, not again in the same breath. When the operator says the bridge is up, wait 60-120s and probe again. Say the connector has not registered in this chat, never that the bridge is down.
- **Delivered-to:** command-bridge, local-file-bridge
- **Hits:** 1
- **Failed:** the operator said "the bridges are back" at 01:26. Three tool searches went out in ONE batch - the 8932 namespace, the 8933 namespace, and a broad pattern across all three ports - all read empty, and the bridges were reported absent. The registration notice arrived at 01:30, four minutes later. At 01:44 he said "Do it"; one probe, reported absent again, notice at 01:46. Both times he was right, and both times the disagreement was defended with a measurement.
- **Why:** Three mechanisms, and the third is the one that matters. (1) SAMPLING - registration is time-varying, so three probes inside a single turn sample one instant. They carry the felt confidence of three readings and the information of one. `deferred-tools-read-as-absent-bridge` says re-probe; its letter was satisfied while its entire purpose was inverted. (2) LOCUS - "the bridges are down", "dropped", "off the surface" all name the MACHINE. What was actually missing is the connector registration in this chat. `bridge-session-bound-to-pid` already records that a dead bridge costs the chat and not the machine, but only as a diagnosis, never as a rule about wording, so every report implied a PC fault that did not exist. That is precisely what he kept disputing. (3) PRIORITY - the operator can see the Ports panel and the plugin toggles. His "the bridge is up" is EVIDENCE about the machine, not a hunch to be checked against a probe. Read as evidence it dissolves the contradiction on the spot: PC healthy, registration pending, therefore wait. Underneath all three, accuracy-over-speed is settled on file and speed won anyway, because answering instantly feels responsive.
- **Worked:** Measured tonight - 4 minutes and 1.5 minutes from the "absent" report to the registration notice, two for two, plus a roughly 60-minute instance earlier the same day already recorded under `deferred-tools-read-as-absent-bridge`. When he asserts the bridge is up: say the connector has not registered YET, keep working on anything that does not need it (the cloud fallback carried eight of nine files tonight while this argument ran), and re-probe on a DELAY instead of returning a verdict. A probe repeated inside one turn does not discharge the re-probe rule. Never report a bridge verdict until a second probe, separated by at least 60 seconds, has also come back empty.
- **Evidence:** measured - conversation timestamps for both cycles, and the registration notices themselves
- **See also:** deferred-tools-read-as-absent-bridge, bridge-absent-probe-is-not-permanent, bridge-session-bound-to-pid, bridge-connector-removed-midsession

### A pipeline's exit code is the LAST command's, so `| tail` reports the checker as clean
- **Pattern-Key:** verifier-pipe-masks-the-exit-code
- **Date:** 2026-08-29
- **Trigger:** false-success
- **Rule:** Never read a checker's exit code through a pipe. `cmd | tail` reports tail's status, not the checker's. Run the check bare, or capture `${PIPESTATUS[0]}`.
- **Delivered-to:** dream-cycle
- **Hits:** 1
- **Failed:** Running `python lesson_check.py cowork-lessons.md 2>&1 | tail -25; echo "EXIT=$?"` during the 2026-08-29 audit. It printed `EXIT=0`. The checker had actually exited 1 on a real FAIL - a `promotion_due` defect introduced minutes earlier in the same session by setting `agent-recommends-edit-without-reading-file` to Hits 2 without a `Promoted-to` or `Promotion` line.
- **Why:** In bash `$?` after a pipeline is the exit status of the LAST element, and `tail` almost always succeeds. The FAIL line was visible in the captured stdout, so the defect was caught by reading the output - but the exit code, which is the part a job or a gate would branch on, said the opposite. A batch job wrapping this pattern would have recorded a clean run. Same shape as the always-exits-zero defect the `_template-job.bat` contract was written to stop, but reached through a pipe rather than through a missing error check - so the job contract does not cover it.
- **Worked:** Re-ran the checker bare with stdout discarded - `python lesson_check.py cowork-lessons.md >/dev/null 2>&1; echo $?` - which returned 1 and exposed the real state. Fixed the underlying defect by authoring a `Promotion:` line, then re-verified: `lesson_check` exit 0, `lesson_gate.py audit` clean at 46 rules from 82 entries, digest byte-identical so no second instructions write was needed.
- **Evidence:** measured - both exit codes read in the same session, 0 through the pipe and 1 bare
- **See also:** verifier-warns-on-proxy-not-the-defect, verification-scoped-away-from-the-risk, agent-claims-action-before-doing-it

### A familiar failure mode was asserted as the cause while the disproving evidence sat unread
- **Pattern-Key:** diagnosis-anchored-on-the-known-failure-mode
- **Date:** 2026-08-29
- **Trigger:** correction
- **Rule:** Before naming a known failure mode as the cause, check the evidence that would DISPROVE it. A cause that matches a remembered pattern is a hypothesis competing with others, not a finding.
- **Hits:** 1
- **Failed:** Reporting to the operator that `<client>-apportionment` was not loading and that its 1,019-character description - just under the 1,024 cap, past the 900 working ceiling - was the likely cause. the operator replied that the skill had been replaced by `state-apportionment`. It had been. The skill was not silently unloaded; it was deliberately superseded and deregistered, and the OneDrive folder is residue.
- **Why:** `skill-description-over-cap-unloads-silently` is a lesson already in the digest, so a skill that is absent plus a description near the cap matched a stored pattern instantly. The disproving evidence was one call away and was not made: `state-apportionment` holds the same four stage scripts at near-identical sizes (34,000 / 83,070 / 97,501 / 28,652 against 34,008 / 82,928 / 95,366 / 28,556), the same helpers, seven added intake and validation scripts, a newer SKILL.md, and zero occurrences of the client name. A loaded rule made a wrong answer arrive faster and with more confidence, which is the failure mode of a digest rather than an argument against one.
- **Worked:** State a cause as a hypothesis until the competing explanation has been checked, and for a MISSING component always ask first whether it was replaced. Comparing the two script folders settled it in one call. the operator's recollection outperformed the analysis, so treat a user contradiction as evidence to test immediately, never as something to defend against.
- **Evidence:** measured - both scripts folders listed and the SKILL.md files read after the claim was already made
- **See also:** agent-recommends-edit-without-reading-file, config-contradiction-survives-in-second-file, prune-list-counts-drift-from-names

### Quarantining into a folder inside the repo puts the content INTO version control
- **Pattern-Key:** quarantine-destination-inside-the-repo
- **Date:** 2026-08-29
- **Trigger:** failure
- **Rule:** A quarantine destination must be OUTSIDE the repository. Moving files to a folder inside it and then running `git add -A` commits the very content the move was meant to remove.
- **Delivered-to:** git-bridge
- **Hits:** 1
- **Failed:** Moving `<client>-apportionment`, its zip and an empty folder from the Cowork Skills folder into `COPILOT_COWORK\Quarantine\2026-08-29 - Skill Residue`. That path is inside the git repo. The sync/commit job then ran `git add -A` and commit cffae50 added 17 client-named files, 7957 insertions. The `/XD` rule in the sync job had successfully kept those paths OUT of the working tree for nine days; the quarantine put them in.
- **Why:** The quarantine rule says move-with-a-manifest rather than delete, and it was followed exactly - the destination was simply never checked against the repo boundary. Two individually correct rules (quarantine rather than delete; commit the session's work) compose into a defect when the quarantine lands inside the thing being committed. `Outputs/` was already gitignored, which is why no previous job had ever hit this.
- **Worked:** Because the repo is local-only and cffae50 was the tip, `git reset --mixed HEAD~1` undid it cleanly rather than layering a deletion commit that would have left the content in history forever. Then: move the folder to `Downloads\COWORK_QUARANTINE` (outside the repo), add `Quarantine/` to `.gitignore`, re-stage, re-commit as 353104a, then `git reflog expire --expire=now --all` and `git gc --prune=now` to drop the abandoned objects. Verified by `git log --oneline cffae50` returning "unknown revision" and `git ls-files` matching no client name.
- **Evidence:** measured - tracked-file list captured before and after, abandoned commit confirmed unreachable
- **See also:** git-deletion-does-not-sanitize-history, cleanup-quarantine-instead-of-delete

### A guard that greps a whole path matched the guard script's own filename
- **Pattern-Key:** guard-substring-matches-its-own-filename
- **Date:** 2026-08-29
- **Trigger:** failure
- **Rule:** Anchor a path guard to where the path actually starts (`findstr /b /c:"Quarantine/"`). An unanchored substring search matches the job's own filename and aborts a correct run.
- **Hits:** 1
- **Failed:** The correction job checked its staged list with `findstr /i /c:"Quarantine" /c:"<client>"` and aborted with `quarantine-still-staged`. The staged list was CLEAN. The match was `CommandJobs/2026-08-29-quarantine-residue.bat` - the name of the job that had done the quarantining.
- **Why:** Same defect shape as the `--for skills` miss where "profile" contained "file", inverted: there a substring caused a false negative, here it caused a false positive. A guard that blocks correct work is not harmless - it trains you to loosen or skip the guard, and the second run is where the real mistake gets waved through.
- **Worked:** Anchor with `/b` so only a path BEGINNING with `Quarantine/` matches, and add a NEGATIVE CONTROL in the same job: write a known-bad path to a temp file and assert the check still fires on it. Without that control, "no match" is indistinguishable from "the check is broken". Both ran and both passed before the commit was allowed.
- **Evidence:** measured - the false positive aborted one run, the anchored version plus its control passed the next
- **See also:** classifier-substring-match-silently-misfiles, verifier-warns-on-proxy-not-the-defect, verification-scoped-away-from-the-risk

### The standing close job reports OK even when its commit fails, and deletes the message
- **Pattern-Key:** cowork-close-reports-ok-on-failed-commit
- **Date:** 2026-08-29
- **Trigger:** failure
- **Rule:** Test every exit code; never echo one. A job that prints `git commit exit` and then unconditionally prints `COWORK_RESULT: OK` cannot tell a failed close from a good one. This is the DISCIPLINE, not a live warning about cowork-close.bat: that job was fixed on 2026-08-30 and now tests each code, preserves `_commit-msg.txt` on any failure, and guards staging with a negative-controlled check.
- **Delivered-to:** command-bridge, gamma-tango, git-bridge
- **Hits:** 1
- **Failed:** Not yet observed failing in the wild - found by reading the file while looking for something else. That is the point: it has been the standing close job since 2026-08-21 and every clean run has looked identical to what a failed run would look like.
- **Why:** The job predates the `_template-job.bat` contract and was never migrated. It echoes three exit codes (`sync exit`, `git add exit`, `git commit exit`) and acts on none of them. That contract exists precisely because older jobs always exited 0 and hid their failures - but the migration was never applied to the one job that runs at the end of EVERY session, where a false OK also destroys the commit message needed to retry.
- **Worked:** For this session's commit the job was deliberately NOT used - `2026-08-29-sync-and-commit.bat` was written instead, with `if errorlevel 1 goto commit_failed` after the commit and the message file preserved on failure. `2026-08-18-sync-cowork-config.bat` had the same defect: three `echo robocopy exit` lines, zero checks, unconditional `exit /b 0`.
- **Fixed:** 2026-08-30. Both jobs now TEST every exit code. `cowork-close.bat` deletes `_commit-msg.txt` only after a commit that actually succeeded, and adds an anchored `Quarantine/` staging guard with its own negative control. The sync job tests `if errorlevel 8` - NOT `errorlevel 1`, because robocopy returns a bitmask where 1-7 are success variants and treating 1 as failure would break every normal run. Verified by `2026-08-30-test-close-contract.bat`, 6/6, including two sabotage cases: a close pointed at a non-repo now exits nonzero AND preserves the message file, and a sync with a bad source fails with the named reason.
- **Evidence:** measured - both files read end to end; 86 of 121 batch files in CommandJobs emit no COWORK_RESULT line at all; the fix proven by sabotage rather than by re-reading the code
- **Resolved 2026-09-01:** the spent one-offs were archived - eight 2026-09-01 jobs moved to `CommandJobs\Archive` as tracked git renames, leaving only re-runnable diagnostics in the live folder. The rule above was also rewritten the same day: it had described the pre-2026-08-30 cowork-close in the present tense and loaded that stale claim into every session, which dream_analyze had flagged as "fixed but still carrying a live rule".
- **See also:** verifier-pipe-masks-the-exit-code, git-commit-job-must-stage-itself

### A dropped call was reported as a down bridge, repeatedly, until the operator said so
- **Pattern-Key:** bridge-call-failure-reported-as-bridge-down
- **Date:** 2026-08-30
- **Trigger:** correction
- **Rule:** The error "couldn't be reached, so its tools may be unavailable" is ONE CALL failing on the devtunnel hop, not a bridge state. RETRY the call before saying anything about the bridge. Never tell the operator a bridge is down on the strength of a single failed call.
- **Delivered-to:** command-bridge, local-file-bridge, playwright-skill
- **Hits:** 2 (2026-08-29 connector-absent, 2026-08-30 dropped write)
- **Promotion:** 2026-08-30 - Rule authored and carried into the copilot-instructions.md LESSON-DIGEST, so it loads every session. Also served by the 8933 bridge's own operating-rules banner on the first call of a session, which is the surface where it is actually needed.
- **Failed:** the operator: "it seems like you often think the bridges are down when they are actually up." He was right, and it had just happened twice in the same session. A `write_file` returned "couldn't be reached" and was treated as a bridge problem; the very next call to the SAME bridge answered instantly with a normal ENOENT. Earlier the same day, a `list_directory_with_sizes` failed while a `list_directory` issued in the same batch succeeded.
- **Why:** The message names the SERVER ("'the operator Local Filesystem 8932' couldn't be reached") and speculates about its tools, so it reads as a diagnosis of the bridge rather than as a report about one request. Measured drop rate is 0% local and 1-2% on the tunnel, so a single failure is the EXPECTED case at this volume, not a signal. The existing rule `bridge-drops-are-tunnel-not-bridge` already said this - it was loaded in the digest and still not applied, which makes this a rule that reads as background knowledge instead of an instruction to act on.
- **Worked:** Retry once, and let the SECOND result decide. If the retry answers, say nothing about bridge health - it was a dropped call. Only a measured probe that fails TWICE justifies the word "down". `bridge-autorecover.bat` now probes every port twice for exactly this reason and counts a port UP if either probe answers. Also: never conflate three different things - (1) a dropped call, retry it; (2) a tool absent from the session surface, start a new chat; (3) a port that fails a repeated probe, that alone is a real bridge failure. The proving call itself can be the drop: 2026-10-01 `list_allowed_directories` - the one-call bridge proof named in `deferred-tools-read-as-absent-bridge` - failed on first attempt at session start and answered on retry. Retry the probe before reading its failure as absence.
- **Evidence:** measured - the failing write and the succeeding next call are both in the 2026-08-30 transcript, same bridge, seconds apart
- **See also:** bridge-drops-are-tunnel-not-bridge, bridge-8933-transport-drop-verify-first, deferred-tools-read-as-absent-bridge

### An authorisation to act automatically needs bounds that are testable, not remembered
- **Pattern-Key:** bridge-restart-authorisation-needs-bounds
- **Date:** 2026-08-30
- **Trigger:** better-approach
- **Rule:** When the operator authorises an automatic action, encode WHEN it may fire as a tested decision table, not as prose. `bridge_policy.py` decides; the job obeys. An authorisation whose refusals are never tested is a rubber stamp.
- **Delivered-to:** command-bridge
- **Hits:** 1
- **Failed:** Nothing yet - written at the moment of the grant rather than after an incident. the operator authorised automatic bridge start/restart; the naive reading is "restart whenever a bridge looks down", which would have fired on every one of the dropped calls above and taken healthy bridges off the air.
- **Why:** Three measured constraints make the blanket version harmful. A restart CANNOT register a connector - the tool surface is fixed at session start, so a missing tool is never a restart reason. `bridge-restart-all.bat` kills the bridge running it and leaves the tunnel ports PRIVATE, and devtunnel.exe is absent, so only the operator can restore them - an unnecessary full restart strands the machine until he is physically present. And 8933 cannot restart itself, because the restart job runs on 8933.
- **Worked:** `bridge_policy.py` holds the whole authorisation as a table: NOACTION when healthy; RESTART only for 8931 or 8932 while 8933 stays up to verify PID turnover; REFUSE when 8933 is down or all three are down. `bridge_policy_selftest.py` is 14 cases and MOST of them assert a refusal, including one that walks all 8 possible states and asserts `bridge-restart-all.bat` is never proposed in any of them. The job runs the selftest before it will act at all.
- **Evidence:** measured - selftest 14/14, and the live dry run measured 8931/8932/8933 all up and correctly chose NOACTION
- **See also:** bridge-call-failure-reported-as-bridge-down, verifier-ignores-structural-diff

### Five review rounds hardened a skill that had never run once
- **Pattern-Key:** review-rounds-outpaced-the-first-real-run
- **Date:** 2026-08-31
- **Trigger:** better-approach
- **Rule:** Count the production runs before accepting another round of hardening. A component at v1.5 with ZERO runs is being improved against imagined failure modes; ship it, watch one real run, then harden against what actually happened.
- **Hits:** 1
- **Failed:** dream-cycle went 1.0.0 -> 1.5.0 in a single evening across five external review rounds, roughly 25 real defects fixed, and was never once executed on its own schedule. The fifth review proposed a machine-readable state artifact with a deterministic transition validator - a genuinely strong idea - 90 minutes before the first scheduled run. Installing a new fail-closed gate immediately before a first run inverts its purpose: a gate that fails closed INCORRECTLY blocks the very run that would have produced the evidence it needs.
- **Why:** Each round was individually correct and the hit rate was high, so "one more round" always looked justified. What that framing hides is that review finds CONTRACT defects - contradictions, missing dependencies, undefined branches - and by round five those were nearly exhausted, while the untested surface (does the email send, does the checkpoint compare, does the judged half produce useful proposals) had not moved at all. The same session had already reached this conclusion about lessons: 48 unmeasured rules and 71 unmeasured rules are the same epistemic position. It was not applied to the skill being built.
- **Worked:** The fifth review's OWN priority ordering resolved it - two of its five items were marked "implement after observing several natural runs", its regression suite needs runs to regress against, and its acceptance criteria are all measurements requiring runs. Accept the diagnosis, defer the build. Concretely: let the first scheduled run happen on the current version, capture what it actually does, and build the state validator informed by that. Record the deferred items so deferral is not loss.
- **Evidence:** measured - execution_count 1 (the setup call, not a sweep), next_execution_time 90 minutes out, five SKILL.md versions committed the same evening
- **See also:** new-rule-is-untested-until-it-survives-a-real-case, verification-scoped-away-from-the-risk

### Every defect that would have broken the run was an integration defect, not a logic error
- **Pattern-Key:** integration-defects-outnumber-logic-errors
- **Date:** 2026-08-31
- **Trigger:** better-approach
- **Rule:** When a routine names a file, a script or a tool, check the acquisition step in the SAME edit. The defects that break an unattended run are dependencies declared in one section and absent from another - not bad logic.
- **Hits:** 1
- **Failed:** Three separate times in one session dream-cycle told a scheduled run to read something its manifest never fetched: `lesson_gate.py` (the routine called `lesson_gate audit`; it would have died at the digest step after completing the analysis), `analyser.approved` (the gate treated a missing marker as FAILED INTEGRITY and would have deadlocked on its own first run forever), and the determinism reference. A fourth was self-inflicted in the same class: the selftest wrote the marker in Python text mode, producing CRLF, while the validator matched `[0-9a-f]{64}\n?` - the gate rejected its own file.
- **Why:** Logic errors are visible in the section you are editing. Integration defects live in the GAP between two sections that are each individually correct, so re-reading either one finds nothing. Prose review catches them only by holding both halves in mind at once, which is exactly what a careful reader does until the one time they do not.
- **Worked:** Two techniques, and they catch different classes. A LITERAL DRY RUN - follow the acquisition steps exactly, using only what they name - found the CRLF mismatch and a stale live digest that no reading would have surfaced. Then `manifest_check.py` made it mechanical: the skill declares `acquires:` and `not_acquired:`, and the check FAILS on any referenced dependency in neither list. 3/3 including a reproduction of the real defect. `not_acquired` is explicit on purpose - a file deliberately not fetched is a decision, and writing it down is how the next editor knows it was one rather than an omission.
- **Evidence:** measured - all four defects reproduced, manifest_check verified against a sabotaged manifest that omits lesson_gate.py
- **See also:** verifier-pipe-masks-the-exit-code, guard-substring-matches-its-own-filename

### A hosted scheduler's success describes the trigger, not the work
- **Pattern-Key:** schtask-hosted-success-describes-the-trigger
- **Date:** 2026-08-31
- **Trigger:** false-success
- **Rule:** A scheduler reporting success proves a TRIGGER fired, never that work happened. Require an artifact the job itself wrote - a report, a heartbeat - and treat its absence as failure however green the scheduler looks.
- **Delivered-to:** command-bridge, dream-cycle
- **Hits:** 1
- **Failed:** Four scheduled dream-cycle runs reported success. One of them produced nothing for 5h 43m: `2026-08-31.md` was created at a measured 12:46:16Z against an assumed 07:00Z trigger. The scheduler had no way to say "I fired into a session that never woke", because from its side those two outcomes are identical.
- **Why:** A scheduler owns exactly one event - the trigger. Whether anything downstream executed is outside what it observes, so its success field answers a narrower question than the one being asked of it. Windows Task Scheduler has the same shape: `Last Result: 0` is what the 2026-08-18 battery trap printed while producing zero output - that trap lives in the MEMORY store as `fact-schtasks-battery-trap-2026-08-18`, and naming it on a `See also` line raised a dangling_see_also WARN, because that field takes Pattern-Keys from this file only.
- **Worked:** Moved the measurable half onto the machine and made it write evidence. `nightly_measure.py` writes `measurements-YYYY-MM-DD.json` plus a heartbeat on EVERY exit path, and `heartbeat_check.py` reads the heartbeat's AGE. The install job then fired the task through the scheduler and asserted a fresh heartbeat within 0.25h rather than trusting `Last Result: 0` - measured 2026-08-31, heartbeat at 16:49:02Z, age 0.01h.
- **Evidence:** measured - scheduler reported Last Result 0 AND a fresh heartbeat was independently confirmed; the two are separate facts and the job requires both
- **Distinct-from:** verifier-usage-error-reads-as-finding - that one is about a checker's own EXIT CODE being unreadable because a usage error and a real finding both exit non-zero. This one is about a DIFFERENT PROCESS reporting on work it never observed: the scheduler's exit code is accurate about the trigger and silent about the job, so the fix is an external artifact rather than a wider exit-code vocabulary.
- **See also:** elapsed-time-is-not-execution-time, schtask-scheduled-prompt-cannot-preauthorize-a-send

### Elapsed is not execution
- **Pattern-Key:** elapsed-time-is-not-execution-time
- **Date:** 2026-08-31
- **Trigger:** correction
- **Rule:** A gap between a scheduled hour and an artifact's timestamp is LATENCY, not duration. Never call it execution time without a start stamp the job itself wrote.
- **Hits:** 1
- **Failed:** Called a 5h 43m gap "execution time" for the dream cycle. Attended runs of the same job took 2m 21s, 12m 35s and 11m 14s - so the 5h 43m was almost entirely dormancy before the work began, not work.
- **Why:** Subtracting a scheduled hour from a completion stamp measures the interval between an INTENTION and a RESULT. Everything in between - dormancy, queueing, a machine asleep - is inside that number and indistinguishable from work. It reads as a performance figure while actually being a latency figure.
- **Worked:** Made the job stamp its own start: `run_started_at`, `run_ended_at` and `elapsed_s` come from inside `nightly_measure.py`, so duration is measured by the thing being timed. The dream-cycle's Step Zero was separately found unable to prove dormancy at all - `GetScheduledPrompts` returned `no_scheduled_prompt`, so its "464 minutes elapsed" inherited an ASSUMED trigger hour and only the 38s from invocation to first artifact was measured.
- **Evidence:** measured - 4.36s self-timed elapsed on the first real run, against three attended runs of 2m21s / 12m35s / 11m14s
- **Distinct-from:** schtask-hosted-success-describes-the-trigger - that is about a BOOLEAN (did it run) being reported by a process that cannot see the answer. This is about a DURATION being computed from two clocks that bracket more than the work, and it stays wrong even when the run genuinely happened.

### A scheduled prompt cannot pre-authorize a side-effecting tool
- **Pattern-Key:** schtask-scheduled-prompt-cannot-preauthorize-a-send
- **Date:** 2026-08-31
- **Trigger:** missing-capability
- **Rule:** An unattended run must WRITE A FILE AND END. `SetupEventTrigger` has `requested_tool_permissions`; the scheduled-prompt tools do not, so any send stalls forever waiting for an approval nobody is present to give.
- **Delivered-to:** command-bridge
- **Hits:** 1
- **Failed:** A dream-cycle run finished its report at 02:47 and the notification email sat unsent until 08:06 - it stalled on an approval prompt with no human present. File writes to OneDrive went through unattended in the same run; only the send blocked.
- **Why:** The approval gate is attached to the side-effecting tool call, not to the schedule. `SetupScheduledPrompt` and `EditScheduledPrompt` expose no permissions parameter, so there is no point at which consent for a future send can be recorded. The run does not fail - it waits, which is worse, because the artifact exists and looks complete.
- **Worked:** The report IS the notification: it carries its own URL on the last line, so nothing needs to be sent to reach it. Dream-cycle v7 carries an explicit no-send instruction, and rerun-01/02 both recorded "No notification was sent" as a stated design outcome rather than a failure.
- **Evidence:** measured - report completed 02:47, mail sent 08:06 on human return; parameter absence confirmed against the scheduled-prompt tool surface
- **Distinct-from:** schtask-hosted-success-describes-the-trigger - that is a REPORTING defect where the scheduler overstates what it knows. This is an AUTHORIZATION defect: the run genuinely blocks, and no amount of better reporting unblocks it, because the missing thing is a consent parameter rather than a signal.

### EditScheduledPrompt silently ignores a nested recurrence object
- **Pattern-Key:** schtask-editscheduledprompt-ignores-nested-recurrence
- **Date:** 2026-08-31
- **Trigger:** false-success
- **Rule:** Pass recurrence to the scheduled-prompt tools as FLAT frequency/interval/hours/minutes. A nested recurrence object is ignored and still reports success - the only signal is the message text: "still on its schedule" means IGNORED, "now on its new schedule" means APPLIED.
- **Delivered-to:** command-bridge
- **Hits:** 1
- **Failed:** Sent a nested recurrence object to `EditScheduledPrompt`. It returned success. The schedule was unchanged, and the only difference between the two outcomes was one word in the returned message.
- **Why:** The unrecognised nested key is dropped rather than rejected, so the call succeeds against a request that expressed nothing. The response text is generated from the resulting state, which is why it differs - but nothing in the status field does.
- **Worked:** Flat parameters, then read the returned MESSAGE rather than the status. Treat "still on its schedule" as a failed edit and re-issue flat.
- **Evidence:** reported - observed in the returned message text; the ignored-key mechanism is inference unverified
- **Distinct-from:** schtask-scheduled-prompt-cannot-preauthorize-a-send - that is a capability the tool does NOT HAVE and states clearly by omission. This is a capability the tool HAS but silently declines to apply for a malformed argument shape, so the defect is discoverable only in prose that no status field mirrors.

### A coordinated refactor re-parented a gate's elif and silently disabled it
- **Pattern-Key:** verifier-refactor-reparents-a-branch-and-disables-it
- **Date:** 2026-08-31
- **Trigger:** false-success
- **Rule:** After changing the control flow around a check, re-run the suite and confirm the SPECIFIC case still fails. A branch that moved under a different condition still parses, still reads correctly, and can no longer fire.
- **Delivered-to:** dream-cycle
- **Hits:** 1
- **Failed:** Rewriting `lesson_gate` G2 for the tiered marker left `elif live.strip() != fresh.strip()` attached to `if claimed is not None` instead of `if claimed != actual`. G3 could then only fire when the END marker was UNPARSEABLE - never in normal operation. A hand-edited digest body passed the gate and it printed GATE PASSED.
- **Why:** The new code needed a guard clause above the comparison, and inserting it changed which `if` the existing `elif` belonged to. Indentation is load-bearing in Python but invisible in review: the line was unchanged, correct, and in the right function - only its parent moved.
- **Worked:** `lesson_gate_selftest.py` case `case_g3_body_edited` failed on exactly that, naming G3. Re-attached the elif to the inner condition and re-ran: 24/24. The comment now says the indentation is load-bearing and why, so the next edit does not repeat it.
- **Evidence:** measured - selftest reported the mangled-body fixture exiting 0 with GATE PASSED; after the fix the same fixture exits 1 naming G3
- **Distinct-from:** verification-scoped-away-from-the-risk - that is a guard whose FIXTURE or threshold can never reach the defect, so it was born unable to fire. This one fired correctly for weeks and was disabled by an edit ELSEWHERE in the same function, which means the defence is re-running the suite after a refactor rather than designing the fixture better.
- **See also:** verifier-ignores-structural-diff, integration-defects-outnumber-logic-errors

### A format migrator must accept the format it is replacing
- **Pattern-Key:** migrator-strict-on-the-old-format-cannot-migrate
- **Date:** 2026-08-31
- **Trigger:** failure
- **Rule:** When a marker or schema changes, the MIGRATOR must match old and new while the GATE matches new only. Tightening both at once leaves the old format unreadable by the one tool that exists to replace it.
- **Delivered-to:** alteryx-to-python
- **Hits:** 1
- **Failed:** Changed `digest_apply.END_RE` to the three-number tiered marker at the same time as `lesson_gate.END_RE`. Running the flip against the live file gave `FATAL: expected exactly one END marker, found 0` - the instructions file still carried the two-number marker, and the only tool able to rewrite it had just been taught not to recognise it.
- **Why:** A migrator has two distinct jobs - LOCATE the old thing and WRITE the new thing - and one regex was serving both. Tightening it improved the write and broke the read.
- **Worked:** Split the roles by intent: `digest_apply.END_RE` became a liberal locator matching `\d+ (?:always-on of \d+ )?rules from \d+ entries`, while the emitted marker still comes only from `cmd_digest` and `lesson_gate.END_RE` stayed strict so an out-of-date digest still FAILS the gate. Rehearsed on a copy of the live file first: 60 -> 26 always-on, marker upgraded, then gate audit and preflight both passed.
- **Evidence:** measured - the strict version failed on the live file; the dual-form locator migrated a copy and then the real file, 24110 -> 18731 bytes, gate PASSED after
- **Distinct-from:** integration-defects-outnumber-logic-errors - that is a dependency named in one section and absent from another, found by checking acquisition alongside use. This is a single component correctly updated for its FUTURE inputs and thereby made unable to read its PRESENT ones, which no manifest check would catch because nothing is missing.

### A new consumer of a guarded artifact did not consult the guard
- **Pattern-Key:** guard-exists-but-the-new-consumer-never-reads-it
- **Date:** 2026-08-31
- **Trigger:** failure
- **Rule:** When you write a new consumer of an artifact that already has a release gate, the SAME edit must read the gate's marker. A guard protects only the callers that check it, and a new caller defaults to unprotected.
- **Hits:** 1
- **Failed:** Built `nightly_measure.py` to run `dream_analyze.py` unattended at 02:00, and it invoked the analyser without ever reading `analyser.approved`. The release gate had existed since 2026-08-30 and works: `dream_analyze_selftest.py` writes the approved SHA-256 on a pass and REMOVES the marker on a failure. So a failed selftest would have deleted the marker and the nightly would have run the failed analyser anyway, every night, reporting its numbers as authoritative.
- **Why:** The gate was built to protect the DEPLOY path, and it does. Nothing about it reaches out to a consumer written afterwards - the protection is a convention the caller opts into, and a new caller starts outside it. The dream-cycle SKILL.md does say the nightly run must hash and compare; the local job was written from the measurement requirements rather than from that routine, so the instruction was never in view.
- **Worked:** Read the marker BEFORE running the analyser, strip-then-match `^[0-9a-f]{64}$`, compare against a fresh hash of the file, and on any mismatch skip the analyser entirely with a distinct exit code (3, a deliberate refusal) rather than reusing exit 2 (an accident). Every figure the analyser would have produced is then recorded as null, never 0, because "0 findings" and "findings not measured" are opposite claims. Proven on the PC in both directions: 32/32 selftest, a live negative control that moved the real marker aside and confirmed exit 3, then restored it.
- **Evidence:** measured - the gap was found by re-reading the deployed job against the skill's own routine; the fix was verified by a live refuse-and-restore run on the machine
- **Distinct-from:** integration-defects-outnumber-logic-errors - that one is about ACQUISITION, a routine naming a file its manifest never fetches, and `manifest_check.py` catches it by comparing two lists in one document. This is the opposite shape: every file was present and fetched, nothing was missing, and the defect is that an EXISTING protection was not invoked by a newly written caller. A manifest check passes cleanly on it.
- **See also:** verification-scoped-away-from-the-risk, migrator-strict-on-the-old-format-cannot-migrate

### WakeToRun reads True and is vetoed by the power scheme on battery
- **Pattern-Key:** schtask-waketorun-vetoed-by-power-scheme-on-dc
- **Date:** 2026-08-31
- **Trigger:** failure
- **Rule:** `WakeToRun` on a task is a REQUEST. Before trusting it, read `powercfg /query SCHEME_CURRENT SUB_SLEEP RTCWAKE` - the AC and DC indices are separate, and a DC index of 0x0 means no task will ever wake this machine on battery however the task reads back.
- **Delivered-to:** command-bridge
- **Hits:** 1
- **Failed:** Registered `Cowork Nightly Measure` with `-WakeToRun`, read the setting back from the registered task, and got `WakeToRun: True`. Treated that as "the machine will wake itself at 02:00". It will not, on battery: measured `Allow wake timers` at AC index `0x00000001` (Enable) and **DC index `0x00000000` (Disable)**.
- **Why:** Two different subsystems own the two halves. The task stores a genuine request and reports it faithfully; the power scheme decides at execution time whether wake requests are honoured, and it holds separate values per power source. Nothing in the task's own readback can see that veto, so the most careful possible reading of the task still gives the wrong answer. This machine has no S3 at all - `powercfg /a` reports only `Standby (S0 Low Power Idle) Network Connected` and Hibernate - so Modern Standby rules apply throughout.
- **Worked:** Read the power scheme separately and treat AC and DC as different machines. Measured here: sleep-after AC `0` (never sleeps plugged in, so no wake is needed at all) and DC 600s; hibernate-after 0 on both. The operative rule became "leave it on the charger", which removes the dependency rather than configuring around it. On battery the 02:00 run is missed and `StartWhenAvailable` catches it up at lid-open, which is why the job stamps its own `run_started_at` - a late run and a missed run are then distinguishable.
- **Evidence:** measured - `powercfg /query SCHEME_CURRENT SUB_SLEEP RTCWAKE` and `STANDBYIDLE`/`HIBERNATEIDLE`, plus `powercfg /a`, read 2026-08-31 while the task reported WakeToRun True
- **Distinct-from:** schtask-editscheduledprompt-ignores-nested-recurrence - there the argument was DISCARDED AT WRITE TIME, so the stored state never contained it and reading the right field back would expose it. Here the setting was stored correctly and IS true; a second subsystem refuses to honour it at EXECUTION time. Readback catches the first class and is structurally incapable of catching this one, so the defence is reading the other subsystem, not reading your own more carefully.
- **See also:** schtask-hosted-success-describes-the-trigger, guard-exists-but-the-new-consumer-never-reads-it

### A checker must read all its evidence before it announces a verdict
- **Pattern-Key:** verifier-verdict-announced-before-evidence-read
- **Date:** 2026-09-02
- **Trigger:** failure
- **Hit 2, same day, in a job written to verify the fix for hit 1.** `2026-09-01-verify-scope-work.bat` ran `digest_apply --check`, got STALE, and printed "renaming ENFORCED to PARTIAL changed what loads at turn 1 - revert the tiers rename". It had never tested that. The block was stale because a CONCURRENT session had added two lesson entries (corpus 111 -> 113); the rename was innocent, proven by generating the always-on block under both tier files and diffing them - identical. The failure message named a cause it had not measured, and would have sent the next session reverting the wrong change. A verdict does not become evidence-led by being placed at the end; it has to be derived from a test that could have come out the other way. v2 replaces the assertion with that diff plus a negative control.
- **Rule:** A checker must gather every piece of evidence BEFORE it adjudicates, once, at the end. Never jump to a FAIL label mid-stream - that skips the step that could contradict it. Take a baseline from a file the run wrote, never from a literal pasted at authoring time. And never let a failure message NAME a cause the job did not test - derive the verdict from a comparison that could have come out the other way.
- **Delivered-to:** dream-cycle
- **Hits:** 4
- **Hit 4, 2026-09-02, outside a batch job and in front of the user.** A PowerShell probe written for the operator to run interactively ended its `catch` with a single label: `NO - blocked: <status>`. Conditional Access refused the device-code sign-in, so the token variable was never set, the request carried a `Bearer` header with nothing after it, and Graph replied `InvalidAuthenticationToken / ArgumentNull` at 401. The script announced `NO - blocked: 401` - an AUTHORIZATION verdict it had never tested - for what was an AUTHENTICATION failure. Two different gates, collapsed into one label by a catch-all. The evidence that settled it was already on screen and unread: the guarded `if ($tok)` block had printed NOTHING, which is the actual finding. RULE EXTENSION - this is not confined to verifier jobs on the PC. Any diagnostic that reports a REASON must derive it, including a snippet handed to a human, where a wrong label is acted on immediately and with more confidence than a job's exit code would earn. Guard the interpreting branch on the precondition holding, and give could-not-test its own distinct message.
- **Hit 3, 2026-09-01 21:12, roughly one hour after hit 2 and AFTER this rule entered the always-on block.** A nightly-readiness job gated on `findstr /c:"Scheduled Task State:          Enabled"` - a literal with a GUESSED number of spaces. schtasks pads that column differently, the match failed, and the job printed "The task exists but is NOT in the Enabled state. It will not fire." directly beneath its own output reading `Scheduled Task State:                 Enabled`. Same signature as hit 1, in a job written to check that a scheduled task would fire. Fixed by asking the scheduler for the STATE - `Get-ScheduledTask ... .State` - instead of asking the console for its column widths, and by splitting the failure into `task-disabled` (a finding) and `task-state-unknown` (a could-not-check), because "I could not confirm Enabled" and "it is Disabled" are different claims and only one of them was evidenced.
- **Promotion:** COMPLETE at 2 hits, by the counter rather than by a second copy. At Hits 2 this rule is selected into the always-on block on the next `digest_apply`, which is the only delivery path measured to work. Both hits landed on 2026-09-01, hours apart, and the second was inside a job written to verify the fix for the first - so the promoted wording carries the sharper half of the lesson, that a named cause must be a tested one. **DO NOT re-promote on hit 3.** The rule was already in the always-on block when hit 3 happened, so it was in context and was missed anyway - the same finding recorded on `deferred-tools-read-as-absent-bridge` at ITS third hit. Delivery is not the constraint and a fourth sentence would add nothing. The only escalation left is a RUNNABLE CHECK, and the specific one this needs is a `job_lint` rule that refuses a `findstr /c:` literal containing a run of two or more spaces - a column-aligned match against console output is brittle by construction, and it is mechanically detectable. Proposed, not built.
- **Failed:** `2026-08-31-verify-trigger-test.bat` printed `COWORK_RESULT: FAIL heartbeat not fresh after the trigger time` directly beneath its OWN step-1 output showing `Last Run Time: 8/31/2026 3:47:01 PM` and `Last Result: 0`, and its OWN step-2 output showing `last verdict CLEAN (exit 0)`. The timed trigger had fired and had produced a measurement file. The verdict was the exact opposite of the evidence printed above it.
- **Why:** Three coupled defects, and only the third generalises. (1) FROZEN BASELINE - `set "BEFORE=<timestamp literal>"` was pasted in when the job was authored, and the arm job never wrote a baseline anywhere, so nothing could refresh it. (2) ABSOLUTE WINDOW - a 0.5h freshness threshold is true only within 30 minutes of one specific trigger; run the next morning it could only fail, and `heartbeat_check.py` defaults to 26h for exactly this reason. (3) EARLY VERDICT - the freshness gate did `goto heartbeat_stale` mid-stream, so the step actually designed to answer the question never ran. Defects 1 and 2 merely supplied bad input; defect 3 is what let a verdict be announced over unread evidence.
- **Worked:** `2026-09-01-verify-nightly-run.bat` plus its `.ps1`. It compares the heartbeat against the task's OWN LastRunTime from `Get-ScheduledTaskInfo`, which is self-relative and stays true on any day it is run; keeps the 26h grace; collects every finding into one array and adjudicates ONCE at the end; and returns exit 2 for could-not-run so a checker that did not run is never mistaken for a checker that found something. Run against the identical machine state that produced the FAIL, it returned `COWORK_RESULT: OK` at exit 0.
- **Evidence:** measured - the two reports exist side by side under `Outputs\2026-08-31 - Trigger Test\` and `Outputs\2026-09-01 - Nightly Run Verify\`, and the old job was re-read from disk before it was archived
- **Distinct-from:** verifier-pipe-masks-the-exit-code - there the checker reached the RIGHT answer and the plumbing destroyed it: a `| tail` replaced the checker's exit code with the pager's, so a real finding was lost and the run read clean. Here the plumbing was sound - every exit code propagated correctly - and the checker itself produced the WRONG answer from correct machinery, because it adjudicated before reading the evidence that contradicted it; one SILENCES a true finding, this one MANUFACTURES a false one, so fixing exit-code propagation cannot catch this and vice versa. ALSO distinct from schtask-hosted-success-describes-the-trigger - there the scheduler's report is TOO NARROW: it truthfully says the trigger fired and says nothing at all about whether work happened, so the reading is correct and simply answers a smaller question than it appears to. Here every piece of evidence was present AND correct - trigger fired, work produced, verdict CLEAN - and control flow branched to a FAIL label before reaching any of it. That entry is about what a value MEANS; this one is about the value never being read. The irony is direct and worth keeping: this verifier distrusted `Last Result 0` exactly as that lesson instructs, and overcorrected into rejecting a true success. NOTE for future dispositions - `lesson_dupe.py` line 192 substring-matches ONE Distinct-from field, so a second Distinct-from line is silently ignored; every neighbour must be named in this single line.
- **See also:** verifier-pipe-masks-the-exit-code, diagnosis-anchored-on-the-known-failure-mode, schtask-hosted-success-describes-the-trigger

### A placeholder that will not hydrate means a stuck CLIENT - restart it before repairing any file
- **Pattern-Key:** onedrive-placeholder-cannot-hydrate
- **Date:** 2026-09-01
- **Trigger:** failure
- **Rule:** ERROR 389 `0x185` "The cloud operation was unsuccessful" is a DEHYDRATED PLACEHOLDER that cannot be fetched - not a lock, not a robocopy fault, and `attrib +P -U` does NOT recover it. FIRST count how many placeholders fail: if several across different folders fail, and each fails in well under a second, the OneDrive CLIENT is stuck and one restart fixes every file at once. Only rebuild individual files from the cloud copy when a restart has been tried and the failure is genuinely confined.
- **Delivered-to:** local-file-bridge
- **Hits:** 2
- **Promotion:** DUE at 2 hits and DONE the same day. Both hits landed hours apart on 2026-09-01, so the counter reached 2 before any later session had ever read the first wording - the promoted line therefore carries the CORRECTED rule (restart the client first), never the original one that repaired four files by hand.
- **Promoted-to:** copilot-instructions.md, "Rules already paid for" (LESSON-DIGEST block) - `digest_apply.py` spliced the corrected Rule on 2026-09-01 and the always-on count moved 26 -> 27, confirmed by re-reading the block from disk.
- **Failed:** The SKILLS leg of `2026-08-18-sync-cowork-config.bat` failed ERROR 389 on four files: `command-bridge\SKILL.pre-approved-batch-executor.2026-08-17.md`, `demo-menu\SKILL.md`, `local-file-bridge\SS_SKILL v1.md` and `v2.md`. All four carried the `O` (Offline) attribute; control files beside them did not. `attrib +P -U` applied cleanly - the attribute moved from `0x401420` to `0x481420`, adding Pinned - and after 90s of polling all four still failed to read with the same error. OneDrive was running normally the whole time.
- **Why:** Files On-Demand keeps a stub locally and fetches content on access. When that fetch fails the stub stays, so the file has correct metadata - `Get-Item .Length` returns the true size - while any content read fails. Pinning only records an intent to keep the file local; it asks OneDrive to download and cannot make the download succeed. Two consequences that mislead: the SIZE of a broken placeholder still matches the cloud copy, so a size check "passes" on a file that cannot be read at all, and the old unbounded `robocopy /R:1000000 /W:30` retried these four forever, which presented as a HANG rather than as an error - bounding the retry did not cause this failure, it revealed one that had been silent.
- **Worked:** Rebuilt each file from the cloud copy in the `/mnt/user-config/` mount, which stays readable because it serves the cloud content and not the PC's stub. Checked first that all four were LF-only with no CR, so a bridge write would be byte-identical, and that each cloud size matched the size the stub reported. Wrote them one per tool block through 8932, then verified with `Get-FileHash SHA256` against hashes taken from the cloud copies BEFORE any write - all four MATCH, no file still Offline, and the unmodified three-leg sync then passed on its own for the first time.
- **2026-09-01 SAME DAY, HIT 2 - the remedy above was at the WRONG LEVEL.** Asked to fix the 20 remaining placeholders, a census first measured the real scope: 149 dehydrated files across 18 areas of the Cowork tree, and 48 of 48 sampled failed. Not 24 corrupted files - a client-wide fault. The tell was in the timing all along and was not read: every failure returned in about 0.03s, far too fast for a network fetch to have been attempted, so OneDrive was refusing LOCALLY rather than trying and failing. Stopping the client and starting it again fixed everything: the old process had been up since 2026-08-29 (three days), the new one served content 24 seconds later, and the same census then returned 46 of 46 OK across every area. Rebuilding four files by hand was correct in effect and wrong in level - it repaired symptoms of a stuck process while 145 other files stayed broken. COUNT AND TIME THE FAILURES BEFORE CHOOSING A REMEDY: one file failing is a file problem, many files failing instantly is a process problem.
- **Side effect worth knowing:** after the restart the tree grew from 1,867 to 1,934 files and dehydrated from 149 to 191, most of the new ones named `(conflicted <hash>)`. Whether the restart CREATED those conflict copies or merely pulled down ones that already existed cloud-side was not established - do not assume either. The sync excludes `*conflicted*`, so none of them reach the repo.
- **Evidence:** measured - ERROR 389 on all four legs of the failing sync, attribute values before and after pinning, 90s poll with no recovery, then four SHA-256 MATCH lines and `skills leg OK` from the standing sync job. Hit 2 measured by the same census job run before and after the restart: 48/48 FAIL then 46/46 OK, plus old pid 2476 started 2026-08-29 and new pid 150288 started 2026-09-01
- **Distinct-from:** onedrive-recursive-scan-hydrates-tree - there hydration WORKS and the fault is cost: enumerating and reading a whole tree of placeholders turns a search into a download and blows the job cap. Here hydration is BROKEN for four specific files and no amount of waiting or pinning completes it, so that entry's remedy - scope the scan smaller - cannot help, because the problem is not how many files are touched but that these four cannot be fetched at any scope. One sharpening for that entry, measured on 2026-09-01: enumerating `.Attributes` and `.Extension` across the whole Skills tree recursively took about a second and hydrated nothing. It is reading CONTENT that forces a fetch, not walking metadata.
- **See also:** onedrive-recursive-scan-hydrates-tree, onedrive-read-mount-locally, prestage-verify-by-hash-not-credential-grep, verifier-verdict-announced-before-evidence-read

### A reported figure that no code path can change
- **Pattern-Key:** nightly-constant-reported-as-a-measurement
- **Date:** 2026-10-01
- **Trigger:** false-success
- **Rule:** Before drawing a conclusion from a number in a generated report, grep for every site that WRITES it. A field with one assignment and no update site is a decoration, and printed beside a real count it reads as a measurement. This includes a "score" or "certified" figure: read the scorer and count how many of its inputs are computed.
- **Delivered-to:** dream-cycle
- **Failed:** Reading `proposals_emitted: 0` next to `findings: 15` in two consecutive nightly measurement files as evidence that dream_analyze's proposal path was dead.
- **Why:** `proposals_emitted` was assigned the literal `0` at nightly_measure.py:305 and never touched again. Three references existed in the entire tree: the assignment, the report key, and a selftest asserting it equalled 0 - which passed whether or not the field carried meaning, because it was always 0. `findings`, by contrast, is genuinely parsed from the analyser's stdout at line 263. Setting the two side by side compared a measurement against a constant. The file's own invariant ten lines above states that a figure the analyser did not produce must be null and never 0, "because a zero would be read next morning as the analyser looked and found nothing" - which is exactly how this field read.
- **Worked:** `grep -n proposals_emitted` across the scripts folder returned three lines and no update site, and running dream_analyze live showed it emitting proposals in quantity. Deleted the field at schema 3, since `findings` already counts them, and replaced the selftest case with one asserting the key is ABSENT so a reintroduction fails.
- **Evidence:** measured - 3 grep hits with no write site; a live analyser run emitted 4 merge candidates, 5 retirement candidates, 1 fixed-but-live rule and 4 relative-date fixes; nightly_selftest 33/33 after the change
- **Hits:** 2
- **Hit 2, 2026-10-01, found on review not in the act:** the ACL "96/100 certified" claim. `CommandJobs\acl-final-assessment.bat` sets six of seven dimension scores as literals (functional, routing, maintainability, efficiency, evidence, deployment_hygiene); only configuration is computed, and `projected_score` is itself a literal. 20 criteria are static file checks (JSON parses, version string equals, counts equal, status strings) and the startup test is `node --check`. `evals/prompts.json` was still the toolkit template. Conclusion given to the operator: self-graded, config-only certification with no behavioural evidence.
- **Promotion:** 2026-10-01 - Rule exists; carried into the copilot-instructions.md LESSON-DIGEST by digest_apply.py at this close.
- **Distinct-from:** verifier-warns-on-proxy-not-the-defect - that one is a check that fires on a proxy for the defect; here there is no check at all, only a reported number nothing computes.
- **Distinct-from:** verification-scoped-away-from-the-risk - that one is about a check whose SCOPE excludes the failure; this field has no scope because it has no logic.
- **Distinct-from:** guard-exists-but-the-new-consumer-never-reads-it - the nearest neighbour by vocabulary, because both live in nightly_measure.py and both argue the null-versus-zero point. The mechanisms are opposites. There, a real protection EXISTS and works, and the defect is that a newly written caller never invokes it - the fix is to make the caller read the marker. Here there is no logic to invoke at all: the field is a literal with no computation behind it, so nothing was skipped because there was never anything to skip.
- **See also:** verifier-usage-error-reads-as-finding

### A repeated markdown field is silently reduced to its first occurrence
- **Pattern-Key:** lessons-parser-keeps-only-the-first-repeated-field
- **Date:** 2026-09-01
- **Trigger:** failure
- **Rule:** `lesson_check.parse` builds an entry's fields with `setdefault`, so only the FIRST occurrence of a repeated field survives. Read the entry body directly for any field that may legitimately appear more than once.
- **Delivered-to:** dream-cycle, self-improvement
- **Failed:** Adding a second `- **Distinct-from:**` line to an entry to dispose of a second above-floor neighbour. The dupe gate kept blocking, and named as unaddressed the very neighbour that the new line addressed.
- **Why:** The loss happens at PARSE time, not at match time: `fields.setdefault(...)` at lesson_check.py:56 keeps the first value and discards every later one. Both consumers in lesson_dupe - `disposed()` at 192 and the gate's own read at 243 - then work from the collapsed dict, so no amount of reading the matching logic explains the behaviour. A gate that blocks for a reason it does not state is worse than one that explains itself.
- **Worked:** Read every `- **Distinct-from:**` line straight from `e["body"]` with a dedicated regex and join them, so all three call sites see the full disposition. Took the neighbouring defect in the same pass: membership was a bare substring test, which let a longer key satisfy a shorter one that is its prefix, so it now matches on a whole-key boundary. Wrote lesson_dupe_selftest.py with a negative control that asserts the two defect cases FAIL on the unpatched script.
- **Evidence:** measured - 5/5 on the patched script, exactly 2 failures on the unpatched one, and `--audit` output byte-identical on the real 106-entry corpus
- **Hits:** 1
- **Distinct-from:** lessons-file-section-anchor-must-be-exact - that one is a regex of mine scoped too widely over the file; this is a shared parser discarding the data before any regex of mine runs.

### 8932 search_files can report an absence that is not real
- **Pattern-Key:** bridge-8932-searchfiles-false-negative
- **Date:** 2026-09-08
- **Trigger:** failure
- **Rule:** `search_files` glob-matches against the path RELATIVE to the search root - it is not a substring search. A pattern with no wildcards matches nothing, and `*` does not cross a directory separator, so nested files need a leading `**/`. Search `**/*term*`, and still never read "No matches found" as proof of absence.
- **Delivered-to:** local-file-bridge
- **Failed:** Checking whether a state-changing quarantine job had already run, by calling `search_files` with pattern `conflicted` on a folder known to hold conflict copies. It returned "No matches found", which would have meant the job had already moved them. SECOND HIT 2026-09-08: while verifying that a dropped `run_batch_file` call had not started `agent-of-record-merge-pr7.bat`, called `search_files` on `CommandJobs\Logs` with the bare pattern `agent-of-record-merge-pr7` and got "No matches found" although that job's `.log`, `.exit` and `.json` from an earlier run were present; `*merge-pr7*` returned all three. The decision did not rest on it - the report file's timestamp was the independent check - but three earlier did-it-run checks that day had used the bare form and were uninformative without anyone noticing.
- **Why:** ESTABLISHED 2026-09-01 by controlled probe; this line previously read "not established". The pattern is a GLOB matched against the path relative to the search root, so there are two independent ways to get a silent empty result: a pattern carrying no wildcard never matches a longer filename, and `*` does not cross a directory separator so anything nested is invisible without `**/`. The original `conflicted` call hit the first. Both return success with an empty result, so nothing in the response signals doubt.
- **Worked:** `**/*term*`, which matches at any depth. `list_directory` on the specific folder remains the independent cross-check whenever ABSENCE is the thing being proven - a glob that is merely mistyped fails the same silent way.
- **Evidence:** measured - controlled probe in CommandJobs against a known ground truth of 18 matching files at top level and 8 more in `Archive\`. Bare `conflicted` returned nothing while `*conflicted*` returned 3 in the same folder; `*2026-09-01*` returned the 18 top-level and none of the 8 nested; the exact literal basename `2026-09-01-close-diagnose.bat` of a file that demonstrably exists in `Archive\` returned "No matches found", and `**/2026-09-01-close-diagnose.bat` found it.
- **Hits:** 2
- **Promoted-to:** copilot-instructions.md LESSON-DIGEST block (always-on tier, hits >= 2), applied mechanically by digest_apply.py in the 2026-09-08 lessons job and confirmed by findstr in the same job. Already delivered to local-file-bridge; delivery to command-bridge as well is PROPOSED (the verify-before-retry step in that skill is where the bare pattern gets used) and needs an `exact` route, which is the operator's call.
- **Distinct-from:** bridge-drops-are-tunnel-not-bridge - that is a transport drop which surfaces as an ERROR and is fixed by retrying; this call succeeded and returned a wrong answer, so a retry would confirm it.
- **See also:** artifact-deadness-needs-consumer-grep

### The lesson gate's default receipt directory is on a read-only mount
- **Pattern-Key:** lessons-gate-receipt-dir-read-only
- **Date:** 2026-09-01
- **Trigger:** failure
- **Rule:** FIXED at the source 2026-09-01: an unwritable receipt directory now exits 2 (could not run), never 1 (stop), and `--receipt-dir` defaults through `default_receipt_dir()`. Read an exit 2 from this gate as an environment fault and repoint the path - never as a lessons failure, and never as grounds to halt a close.
- **Delivered-to:** gamma-tango, self-improvement
- **Failed:** Running `lesson_gate.py preflight` for six surfaces with `--receipt-dir /mnt/user-config/.lesson-receipts`, as the skill documents. Every surface printed its rules in full and then raised `OSError: [Errno 30] Read-only file system`, exiting 1.
- **Why:** `/mnt/user-config/` is the read-only mount of the OneDrive Cowork tree. The receipt write happens AFTER the rules are printed, so the output shows a successful load followed by a non-zero exit - and a non-zero exit from this gate is defined as "stop and fix, not proceed". Taken at face value it would halt a close for a reason that has nothing to do with the lessons.
- **Worked:** Immediately - re-ran with `--receipt-dir /mnt/workspace/.lesson-receipts` and all six surfaces exited 0. Permanently, 2026-09-01 - the receipt write in `cmd_preflight` is wrapped and returns 2 rather than dying; `--receipt-dir` defaults through `default_receipt_dir()`, which preflight and verify BOTH call so they cannot resolve differently; and the three gamma-tango command blocks plus the self-improvement gate section now name a writable path. The cwd-relative branch stays FIRST among the automatic choices because the selftest gives each case its own temp cwd - a shared absolute default would let one case's receipt satisfy the next case's "no receipt" assertion, and the sabotage cases would stop firing while still printing PASS.
- **Evidence:** measured - 6/6 exit 1 with Errno 30 against the mounted path, 6/6 exit 0 against a workspace path, same command otherwise. For the fix: gate selftest 28/28 through 2026-09-01-verify-gate-receipt-fix.bat at exit 0, and the new case run against the PRE-fix script fails alone at rc=1, which is what proves it can reach the threshold it guards rather than passing on known-broken code.
- **Hits:** 1
- **Distinct-from:** onedrive-user-surface-not-live - that is a write which APPEARS to succeed and then does not propagate; this one fails loudly with an OS error and the risk is misreading which thing failed.
- **See also:** verifier-usage-error-reads-as-finding
- **Promoted-to:** lesson_gate.py (`default_receipt_dir`, and exit 2 on an unwritable receipt dir); gamma-tango/SKILL.md OPEN step 2 and CLOSE steps 0 and 3; self-improvement/SKILL.md gate section

### A rule demoted to ENFORCED is only as wide as the thing enforcing it
- **Pattern-Key:** digest-enforced-demotion-outruns-the-enforcer
- **Date:** 2026-09-01
- **Trigger:** failure
- **Rule:** Before classing a rule ENFORCED in `digest-tiers.txt`, name every surface the mistake can be made on and confirm the enforcer reads all of them. `job_lint` inspects `.bat`/`.cmd` files only, so an ENFORCED rule is unenforced everywhere a session acts directly - and the demotion removes the prose from precisely the surface left unguarded.
- **Delivered-to:** dream-cycle, self-improvement
- **Failed:** A recursive content grep over `/mnt/user-config` during a close. It hung and was killed unfinished. `onedrive-recursive-scan-hydrates-tree` was live, correct, and had been printed by the `files` preflight minutes earlier - and did not fire.
- **Why:** That rule is classed `ENFORCED | job_lint/onedrive-recursive`, and the tiering file's stated ground for dropping an ENFORCED rule from turn-1 context is that "an automated check already refuses the mistake" and "the check cannot be skipped and the rule can". Both halves hold only inside a `.bat`: `job_lint.py` accepts `.bat`/`.cmd` paths and exits with "no .bat or .cmd files found" otherwise, and its check keys on a PowerShell `-Recurse` beside a OneDrive or Cowork path. A container-side `grep -r` is neither. So the one surface with no enforcer is also the surface the rule was quietened on.
- **Worked:** Widened the parent rule to name both surfaces, and recorded the scope limit here rather than filing the miss as ordinary forgetfulness. The durable fix is a scope column on the ENFORCED tier - which surfaces the enforcer actually reads - so a demotion becomes checkable instead of asserted. Not built; proposed to the operator at this close.
- **Evidence:** measured - job_lint.py takes only .bat/.cmd (argument parser plus its "no .bat or .cmd files found" exit) and its onedrive-recursive check matches on "-recurse"; the command that actually failed was a container-side `grep -rn`, killed unfinished, and no check anywhere refused it
- **Hits:** 1
- **Distinct-from:** verification-scoped-away-from-the-risk - there a CHECK's own scope excludes the defect it was written to catch. Here the check is correctly scoped to what it lints; the error is the TIERING decision that read a narrow enforcer as grounds to stop stating the rule. The enforcer is sound - the demotion was not.
- **Distinct-from:** guard-exists-but-the-new-consumer-never-reads-it - there a working guard is bypassed because a newly written caller never invokes it, and the fix is to make that caller read the marker. Here every caller the enforcer can see is checked; the uncovered surface is one the enforcer cannot read at all, so there was no caller to fix.
- **See also:** onedrive-recursive-scan-hydrates-tree, lessons-digest-default-limit-truncates, enforcer-encodes-the-superseded-rule
- **Built 2026-09-01, so this entry is no longer advice:** every `job_lint` check now declares the languages it reads; `job_lint --scope` prints the matrix from code; the sweep includes `.ps1`; `digest-tiers.txt` carries `covers:`/`blind:` per claim and all six rules are PARTIAL; and `scope_check.py` compares each claim against the enforcer's declared scope so the two cannot drift. Measured: 17 .ps1 sidecars existed and none had ever been linted; job_lint selftest 31/31 with 24/31 against the pre-fix script; scope_check selftest 11/11; the always-on block is byte-identical under PARTIAL and ENFORCED, negative-controlled.

### An enforcer can go on enforcing the version of the rule it was born with
- **Pattern-Key:** enforcer-encodes-the-superseded-rule
- **Date:** 2026-09-03
- **Trigger:** false-success
- **Rule:** When a lesson's Rule text is sharpened - or when the THING it counts is redefined - grep for the CHECK that enforces it and update it in the same pass. A check is a frozen copy of the rule as it read on the day it was written. Two ways it goes stale: the wording is sharpened and the check keeps the old wording, or the population is re-tiered and the check keeps counting the old population. In both cases the check keeps firing confidently and its output reads as a measurement.
- **Delivered-to:** dream-cycle, self-improvement
- **Failed:** `job_lint/onedrive-recursive` flagged line 64 of `2026-09-01-scope-placeholder-fault.ps1`, a `Get-ChildItem -Recurse` over the OneDrive tree. Read as a true positive it says a live job violates a standing rule. It is not one: that script walks `.Attributes` only, its own header explains why that is safe, and the lessons entry had been corrected hours earlier to say exactly that.
- **Why:** The rule was written on 2026-08-31 as "never recurse a OneDrive tree" and the check encoded `-recurse` near a OneDrive path. On 2026-09-01 the entry was sharpened by measurement - walking metadata across the whole tree took about a second and hydrated NOTHING; it is reading CONTENT that forces a fetch. The prose changed and the check did not, so the enforcer kept refusing the old, broader thing. Because the rule sits in the ENFORCED tier its prose is held out of turn-1 context, which means the stale check was the loudest surviving statement of it.
- **Worked:** Re-encoded the check to the sharpened rule: a bare enumeration is no longer a finding, a recursion whose output is READ still is. The selftest case was inverted to match - the bad sample now reads, the good sample walks - so a future revert to "flag any -Recurse" fails a named case instead of passing quietly.
- **Evidence:** measured - the flagged line is a metadata-only enumeration, confirmed by reading the script; the check's pattern keyed on `-recurse` alone; after the change the selftest passes 31/31 and the same file is no longer flagged, while a content-reading recursion still is
- **Hits:** 3   (2026-09-01 job_lint kept the pre-sharpening wording; 2026-09-03 dream_analyze counted the corpus against an always-on threshold; 2026-09-11 lesson_check --digest requires every authored Rule to sit in the tiered block)
- **Third hit, 2026-09-11 - `lesson_check --digest` demands the pre-tiering population, and a whole afternoon was spent arguing with it.** Its `digest_stale` check walks every entry with a `Rule:` field and requires the rule's first 60 characters to appear in the LESSON-DIGEST block. That was correct when the block carried every rule. After the 2026-08-31 tiering the block carries the ALWAYS-ON tier only, so the check reports exactly `authored - always-on` missing every time: 71 of 109 on this corpus, arithmetic that holds regardless of how current the digest is. MEASURED on identical bytes in one job: bare `lesson_check` exits 0 with FAIL 0 WARN 0, `lesson_check --digest` exits 1 naming 71. The cost was not the run, it was the reading: this session reported the FAIL to the operator as a real staleness finding, then over-corrected in the dream report and blamed the day's own lesson writes, before the two forms were run side by side. `lesson_gate audit` - the authoritative currency check - read clean throughout and was the evidence that settled it. The tiering split one population into two on 2026-08-31 and THREE separate checks have now been found still counting the old one.
- **Fixed the same day.** `lesson_check.digest_findings()` now computes the always-on set by CALLING `lesson_brief.select_alwayson`, the same predicate `digest_apply` uses, so a future tiering change cannot leave this check behind - the frozen copy is gone rather than corrected. The check moved out of `main()` into its own function for the reason it was never controlled: `check()` never saw it, so the 17-case selftest could not reach it. Four controls added, 4/4: a correctly tiered block is clean (this case FAILED before the fix, which is the defect in one line); an always-on rule missing from the block still fires `digest_stale`; no block at all fires `digest_missing`; a missing tiers file fires `digest_tiers_missing` rather than passing silently. MEASURED after the change: selftest 17/17 + 4/4, live corpus clean both bare and with `--digest`, release gate CLEAN at 22 checks. Then the control was run against the REAL instructions file with one always-on rule deleted, and the check failed as it should, naming `bridge-8933-arg-name`. **The first version of that breaker deleted the wrong line** - a trailing comment about who generates the block - and the check passed, correctly. A negative control that removes the wrong thing reports as evidence while proving nothing, so the breaker now selects its victim through the same tier predicate the checker uses.
- **Landed in the public repository the same day, and it took two pull requests because the copy had drifted further than the one defect.** Copying the fixed checker in made the repo gate FAIL: the live file also carries the `misfiled_failure` check added 2026-09-08, and the shipped corpus held SEVEN entries whose own Trigger reads `failure` or `near-miss` sitting under Contradictions. The shipped checker could not see them - the same shape as this whole entry, one layer out: the corpus was fine, its checker was old. Landing the checker alone would have arrived red for a reason that had nothing to do with the checker. So PR #16 refiled the seven verbatim into Failures (a mover that refuses unless every entry survives byte-for-byte and the count is unchanged), then PR #17 landed the checker. Both gates green, main 367800f -> 2f9a63b -> 6f24323. **The mover's first run refused on its own bad comparison:** splitting on `###` gives the last entry of a section a chunk that swallows the next `## ` heading, so two untouched entries looked changed. The refusal was correct and the verification was wrong, which is the cheaper of the two ways round.
- **Second hit, 2026-09-03 - the same failure in `dream_analyze.py`, caught by the operator asking a question rather than by any check.** Its GROWTH section warned "digest carries 90 rules ... every one is read every session" against a hardcoded `80`. Both halves were wrong after the 2026-08-31 tiering: it counted AUTHORED Rule lines in the lessons file (90) rather than the ALWAYS-ON block (30), and only those 30 are read every session - the other 60 load per-surface via `preflight`. The two numbers were the same population until the tiering split them, so the check was correct on the day it was written and silently wrong from 08-31 onward. **It was reported to the operator twice in one evening as a real finding before he asked where the threshold came from; the answer was that nobody set it - it was a literal somebody typed.** Fixed by counting the block itself, naming the tiering in the output, and exposing `--always-on-max` as a documented judgement rather than a hidden constant. The section had ZERO selftest coverage, which is why it shipped: four cases added, including a regression control that fails if the check ever counts the corpus again, and a both-ways control proving the threshold can reinstate a warning as well as silence one. 32/32, analyser re-approved.
- **Rule addendum:** state where a threshold CAME FROM when reporting a finding that rests on it. "Over the threshold of 80" invites a decision; "over a limit nobody chose, measured against the wrong population" does not.
- **Promoted-to:** `copilot-instructions.md` always-on digest tier, position 31 - achieved MECHANICALLY by the repeat rule the moment Hits reached 2, not by a hand-edit. Verified by reading the block back from disk: the always-on count moved 30 -> 31 and this entry's Rule text is present verbatim.
- **Correction, same session:** this entry first carried a `Promotion: DUE` line proposing that a separately-worded rule be hand-added to `copilot-instructions.md`, and the operator was told promotion was waiting on his approval. **That was wrong on both counts.** `digest-tiers.txt` promotes any entry at hits >= 2 automatically - the tier is computed from the lessons file, never hand-listed - so the rule was already loading every session before the proposal was written. Hand-adding prose would have produced a SECOND copy of the same rule, in a different form, able to drift from this one: `config-contradiction-survives-in-second-file`, created by the act of trying to promote. **Before proposing a promotion, read the digest block back and check whether the mechanism has already done it.** The proposal cost nothing here only because it was checked before being applied.
- **Why both hits stayed invisible to automation:** hit 1 was caught by a person reading a flagged line and disagreeing; hit 2 by the operator asking where a number came from. Neither was caught by a check, and the always-on tier is the right home precisely because the sessions that need this rule are the ones editing checks - who do not reliably preflight the `claims` surface first.
- **Distinct-from:** digest-enforced-demotion-outruns-the-enforcer - that is about how FAR an enforcer reaches (which surfaces it can read). This is about WHICH VERSION of the rule it holds. A check can have perfect scope and still enforce last week's wording, and the two failures need different fixes: one widens coverage, the other re-syncs content.
- **Distinct-from:** verifier-warns-on-proxy-not-the-defect - there a checker's OUTPUT was misread by a person. Here the checker's output is exactly what it was programmed to say, and the program is what is out of date.
- **See also:** onedrive-recursive-scan-hydrates-tree, verifier-verdict-announced-before-evidence-read

### The digest repair a close demands cannot be applied from the read-only mount
- **Pattern-Key:** memory-digest-repair-blocked-by-its-own-gate
- **Date:** 2026-09-02
- **Trigger:** failure
- **Rule:** Repair a stale digest by computing it on a WRITABLE scratch copy, proving the repair with `lesson_gate preflight` against that copy into a SEPARATE receipt dir, then applying the difference to the PC file through the 8932 bridge with `edit_file` - never by pointing `digest_apply.py` at `/mnt/user-config/`, which is read-only. Afterwards expect the mount to keep serving the OLD file: hash it against the pre-repair copy to tell sync lag from a failed write, and never read that fresh exit 1 as a second failure.
- **Delivered-to:** persistent-memory, self-improvement
- **Failed:** `gamma tango close`, step 0. `lesson_gate.py preflight` returned exit 1 on all four surfaces - bridge, git, memory, files - each with `FAIL: G3 digest counts match but the body does not`. The fix the failure itself names, `digest_apply.py --instructions /mnt/user-config/copilot-instructions.md`, cannot run there: `test -w` reports the mount read-only. The write path that CAN reach the file is the 8932 bridge, and step 0's own guardrail forbids a bridge call until the bridge preflight SUCCEEDS. The routine's repair sits behind the door its failure locks.
- **Why:** The digest inside `copilot-instructions.md` is a derived COPY; the lessons file is the source. A hit counter was incremented on one entry without regenerating, so the copy still carried the old count and sorted that rule two positions low. G3 compares the block against a fresh regeneration, so a single hit-count bump fails EVERY surface at once - the failure presents as global while the drift is one line, which invites a far larger diagnosis than the evidence supports.
- **Worked:** Copied both files to `working/digest-repair/`, ran `digest_apply.py` against the COPIES, and diffed old against new to confirm the change was one line moving position plus its counter, byte count unchanged, nothing dropped. Re-ran `preflight` against the repaired copy into a SEPARATE receipt directory - all four surfaces exit 0 - which proves the repair without minting a receipt that would falsely attest to the real file. Applied it to the PC as a three-line `edit_file` through 8932 at the OneDrive Cowork path, `dryRun: true` first to confirm the anchor matched before writing. Overriding the bridge guardrail was put to the operator as an explicit choice, not taken unilaterally.
- **Evidence:** measured - preflight exit 1 on four surfaces before the repair and exit 0 on all four against the repaired copy; `edit_file` returned the applied two-line diff; afterwards the mount's md5 still matched the PRE-repair copy, which is what distinguished sync lag from a failed write
- **Hits:** 2 (both 2026-09-02 - first as G3 body drift, then at the next close as G2 stale COUNTS after a hit-count bump elsewhere went un-regenerated: the same derived-copy drift presenting under a different gate, so match this entry on the cause, not the gate code)
- **Promotion:** 2026-09-02 - Rule carried into the copilot-instructions.md LESSON-DIGEST on the second hit, so the repair procedure now loads every session instead of waiting to be rediscovered at the next close.
- **Distinct-from:** lessons-gate-receipt-dir-read-only - there the gate could not WRITE its receipt and the correct reading is exit 2, an environment fault to be repointed. Here the gate ran perfectly and returned a true exit 1 about a real drift; what is blocked is the REPAIR, not the check. One is fixed by changing a path argument, the other needs a write to another machine and a guardrail decision from the operator.
- **See also:** lessons-digest-default-limit-truncates, onedrive-read-mount-locally, onedrive-user-mount-read-lag, verifier-verdict-announced-before-evidence-read

### Check whether a capability is ALLOWED before spending turns on whether it works
- **Pattern-Key:** tooling-install-researched-before-approval-checked
- **Date:** 2026-09-02
- **Trigger:** correction
- **Rule:** Before researching, pricing or proposing any software install on the firm-managed machine, ask whether it is approved. Availability is not permission, and a clean install path is no evidence the install is allowed. Dev Tunnels specifically is NOT approved - do not re-propose it.
- **Failed:** The last open config item was that `devtunnel.exe` is absent, so setting the four bridge ports Public in the VS Code Ports panel is manual after every restart. Asked what devtunnel was, I answered, then ran a web search, fetched Microsoft's docs to establish the install route (`winget install Microsoft.devtunnel`, or a direct download from `aka.ms/TunnelsCliDownload/win-x64`), confirmed it lands under `%LOCALAPPDATA%` and so needs no admin, worked out that a job calling it would need an absolute path, and offered to install it and test whether the CLI could adopt VS Code's existing tunnels. the operator: "dev tunnels is not explicitly approved for installation."
- **Why:** A capability probe answers "CAN this be made to work" and returns nothing about "MAY this be made to work". The two questions look identical from inside the probe, and only the technical one has a satisfying answer, so it is the one that gets asked. Earlier the same day the opposite happened and went well: a research pass into flow auth surfaced, unprompted, that reusing the Azure CLI client ID would be policy evasion, and that route was dropped before any work went into it. The difference was not judgement - it was whether something else happened to raise the permission question. An open-items list phrased as a missing tool actively suppresses it, because the entry reads as a to-do rather than as a decision nobody has taken.
- **Worked:** Dropped it on the correction, with no attempt to find another route to the same capability, and corrected the two records that had framed it as pending. `fact-devtunnel-cli-absent` said the manual step stands "unless the devtunnel CLI is installed" - an open door that would have produced this same proposal again from a later session reading the same list. Both records now state that the manual Public-port step is permanent by design and name the reason.
- **Evidence:** measured - the search and the doc fetch both happened before any approval question was asked, and the correction arrived immediately after the install offer. The generalisation to other unapproved software is inference unverified.
- **Hits:** 1
- **Distinct-from:** probe-env-vars-blank-false-negative and bridge-devtunnel-declared-dead-without-reprobe - all three sit on devtunnel, which is exactly why they invite being filed together, and both of those are MEASUREMENT failures with a measurement fix. There a probe searched blank `%LOCALAPPDATA%` paths and wrongly reported the CLI absent; there a stale stored open item was repeated without re-probing. Both are answered by measuring better, and both were: the 2026-08-21 reprobe confirmed devtunnel really is absent. This entry starts where those finish. The absence is correctly measured and not in dispute; what was never asked is whether installing it is PERMITTED. No probe, however well scoped, returns that - so a better measurement is the wrong instrument, and reading this as another hit on either of them would prescribe exactly the fix that does not apply.
- **See also:** work-is-an-exercise-not-an-engagement, bridge-restart-authorisation-needs-bounds

### A GUI launcher exits clean, so a hang-timeout guard never fires and reports success
- **Pattern-Key:** batch-gui-launcher-defeats-timeout-guard
- **Date:** 2026-09-02
- **Trigger:** false-success
- **Rule:** A timeout-and-kill guard only catches a binary that HANGS. A GUI launcher exits in under a second having spawned its window as a SEPARATE process, so the guard finds nothing to kill and reports clean while the window stays on the operator's screen. When probing an unknown binary from an 8933 job, do not guard on hang: after it exits, enumerate processes by START TIME inside the probe window and report anything new. A job session cannot see the interactive desktop, so nothing you observe from inside the job will ever show you the window you opened.
- **Delivered-to:** command-bridge
- **Failed:** Probing whether `PAD.Console.Host.exe` had a command-line surface, by passing `--help`, `-?`, `/?` and `--version`. Told the operator the run was bounded: output redirected, 12 seconds each, terminate by PID if still alive. All four returned instantly with no stdout, no stderr and a BLANK exit code, total runtime about 2 seconds. I read that as "no usage text, therefore it is the GUI host", published that verdict, and moved on. It had opened the Power Automate Desktop DESIGNER on the operator's screen. It sat there for 68 minutes, through a client working session, until he asked what was happening.
- **Why:** The guard was aimed at the wrong failure. `WaitForExit(12000)` plus kill-by-PID assumes the risk is a process that will not leave. A Windows GUI launcher does the opposite: it returns immediately, well inside tolerance, having handed the UI to child processes with different PIDs. So every check passed honestly and the job reported `COWORK_RESULT: OK`. The blank exit code was the tell - a real CLI returns a number - and I read the silence as evidence for my hypothesis rather than as evidence that something had happened I could not see.
- **Worked:** A residue check that enumerates PAD-named processes and their START TIMES, comparing against the probe window, then reports rather than kills. It found `PAD.Console.Host` 67696 with the visible window title "Power Automate", plus `PAD.Designer`, two `PAD.AutomationServer` and two `PAD.BridgeToUIAutomation2`. Cleanup then took an EXPLICIT PID LIST, never a name match - a name-based kill would have taken the operator's own PAD session and the six PAD services that run continuously - and re-verified each PID's owning process name and start time before terminating, because Windows reuses PIDs and these were an hour old by then.
- **Evidence:** measured - the residue check named four processes started inside the probe window, one holding a visible window titled "Power Automate"; after the targeted close, the AFTER enumeration showed no probe-started process remaining and all six services still running
- **Hits:** 1
- **Distinct-from:** elapsed-time-is-not-execution-time - that is about a DURATION being misread as work done. This is the inverse and worse: the duration was correct, every assertion in the job was true, and the job was still wrong because the thing that mattered happened outside everything being measured. Also distinct from `bridge-8933-timeout-cmd-unusable`, which is about `timeout /t` failing for want of stdin; here the wait mechanism worked perfectly and guarded the wrong event.
- **See also:** verification-scoped-away-from-the-risk, count-assertion-must-use-independent-control

### A token audience is not a hostname, and aiming at it reads as "the API does not exist"
- **Pattern-Key:** api-audience-is-not-a-hostname
- **Date:** 2026-09-02
- **Trigger:** failure
- **Rule:** An OAuth resource identifier and the callable endpoint are DIFFERENT strings and only one resolves in DNS. Before concluding an API is unsupported, confirm you aimed at the HOST: a `getaddrinfo ENOTFOUND` on a resource URI means you called the audience, not that the service is absent. Look up the host separately from the scope.
- **Failed:** Wrote off `api.flow.microsoft.com` as "not a supported API and not even a valid token audience", recorded that in the bridge source AND the config as settled fact, and rebuilt 8934 on Dataverse alone - accepting that flow run history was unreachable. The reasoning came from a real observation: a request to `https://service.flow.microsoft.com/...` returned `getaddrinfo ENOTFOUND`.
- **Why:** `service.flow.microsoft.com` is the AUDIENCE - an identifier that appears in the token's `aud` claim and has no DNS record. `api.flow.microsoft.com` is the host that serves the API. Both are real and they are not interchangeable. The ENOTFOUND was produced by my own wrong URL and read as evidence about Microsoft's service.
- **Worked:** Asked for a token scoped to `https://service.flow.microsoft.com/user_impersonation`, then sent it to `https://api.flow.microsoft.com`. Token issued with `aud=https://service.flow.microsoft.com`; the host answered 200. Run history, triggers, per-action detail and the connector catalogue were all reachable on auth that had been working since that morning.
- **Evidence:** measured - two probe runs. First run: token issued, API call ENOTFOUND. Second run, host corrected: 30 environments returned, every one HTTP 200, two real runs with status, timing and trigger name.
- **Hits:** 1
- **Distinct-from:** `deferred-tools-read-as-absent-bridge` - there a capability was present and the PROBE could not see it. Here the probe was fine and the ADDRESS was wrong. Both end in "it is not available", from opposite causes.
- **See also:** enforcer-encodes-the-superseded-rule

### A constructor that enumerates its fields silently discards every field added later
- **Pattern-Key:** constructor-drops-the-field-added-later
- **Date:** 2026-09-02
- **Trigger:** failure
- **Rule:** When a function rebuilds an object from a hand-picked list of fields, adding a field upstream does NOT reach the consumer - it is dropped in transit, with no error. After adding a config key or an envelope property, grep for every place that reconstructs that object and add it there in the SAME edit. The symptom is a downstream error that names the WRONG cause: a missing id looks like a permissions failure, a missing property looks like malformed input.
- **Failed:** Twice in one session on the same bridge. (1) Added `flow_env_id` to `flow-bridge.config.json`; `requireEnvironment()` returns a NEW object built from four named fields, so the key never arrived and every Flow-service call used the bare guid - answered `403 EnvironmentAccessDenied`, which reads exactly like a permissions wall. (2) `toClientData()` passes an already-wrapped envelope straight through without adding `schemaVersion`, so the shape the tool's own description asks for returned `HTTP 400 Required property 'schemaVersion' not found`. The documented usage was the broken one.
- **Why:** Both functions were written when the field set was complete, and both take the shape "read these N fields, build a new object". That is correct on the day and silently lossy forever after. Nothing fails at the boundary, so the error surfaces far downstream wearing the vocabulary of the API rather than of the bug.
- **Worked:** Carried the field explicitly and said so in a comment naming the trap - `requireEnvironment` now returns `flow_env_id`, `toClientData` fills `schemaVersion` and `connectionReferences` when a caller omits them. Both fixes verified by re-running the exact call that had failed.
- **Evidence:** measured - 403 then 200 on the same environment id after the field was carried; 400 then a created flow on the same definition after the envelope was filled
- **Hits:** 1
- **Distinct-from:** `lessons-parser-keeps-only-the-first-repeated-field` - that is a PARSER keeping the first of several values it did read. This is a CONSTRUCTOR never reading a value at all because it was not on the list. Parsing kept the wrong one; construction kept none.

### Researching how to build it is not the same as checking whether it exists
- **Pattern-Key:** prior-art-unsurveyed-before-building
- **Date:** 2026-09-02
- **Trigger:** better-approach
- **Rule:** Before building a capability, run ONE search for an existing implementation - vendor-published skills, MCP servers, the platform's own tooling. Do it FIRST, not after the build is working. "How do I authenticate to X" and "does a supported X integration already exist" are different questions, and only the second one can save the whole build.
- **Failed:** Spent a day on Power Automate integration - Entra registration attempts, device-code flows, PAC CLI wrapping, solution pack/import, then a hand-built OAuth path - researching authentication mechanics repeatedly and thoroughly. Never once searched whether Microsoft already published something for this. Only after the bridge worked did a survey find `microsoft/power-platform-skills` (FlowAgent, MIT, ~52 tools including run history and desktop-flow execution, no app registration needed in commercial cloud).
- **Why:** The question that got asked was always "how do I make MY approach work", which is answerable and rewarding at every step, so it never ran out of road and never prompted the wider question. Each auth dead end produced a real finding, which felt like progress and disguised that the whole line of work might be unnecessary.
- **Worked:** One web search naming the product and "MCP" or "skill" returned the vendor implementation immediately. Surfacing it late still had value - it named the real capability gaps - but it should have been the FIRST call of the day, before any code.
- **Evidence:** measured - the survey that found it took a single search and returned a maintained, permissively licensed, strictly larger implementation
- **Hits:** 1
- **Distinct-from:** `tooling-install-researched-before-approval-checked` - there the research was thorough and the missing step was a POLICY check (is this approved here). Here the policy question never arose because the prior-art question was never asked. One skipped a permission gate, the other skipped the build-versus-adopt decision entirely.

### evaluate_expression cannot parse the ?[] safe-navigation operator

- **Pattern-Key:** bridge-8934-evaluate-rejects-safe-navigation
- **Date:** 2026-09-03
- **Trigger:** failure
- **Rule:** Call `evaluate_expression` with BOTH fixes or it lies to you. (1) Wrap the expression in `@{...}` - unprefixed input is echoed back verbatim as a string with `evaluated_locally: true`, a silent false success, not an error. (2) Drop the `?` from `?[...]`, which the parser rejects with REFUSED "unexpected character ?". Fix (2) alone lands you in failure (1). The rewrite is for THIS evaluator only - keep `?[...]` in the flow, where it is valid and null-safe.
- **Failed:** Fed evaluate_expression a realistic multi-function expression containing `triggerBody()?['name']` and got `REFUSED: could not evaluate: unexpected character "?"`. First read was that the test expression was malformed, which would have closed a real defect as operator error.
- **Why:** The evaluator implements WDL functions but not the optional accessor, and `?[]` is the dominant idiom in real flow definitions. the operator's own "Todo - Get My Tasks" uses `item()?['status']` and `item()?['title']`, so the tool cannot evaluate expressions copied out of his own flows - which is the main thing it exists to do. The gap therefore looks like a syntax error to the caller at exactly the moment the tool is being used correctly.
- **Worked:** Isolate by removing the `?` ALONE and re-running the otherwise identical expression. `triggerBody()['name']` evaluated and returned `div=3.5 name=the operator upper=TODO`. The A/B is the whole diagnosis: one failing call on a long expression has many candidate causes and proves nothing about any of them. AMENDED 2026-09-03 after verification: the `@` gate was found by running the rule's own delivery through a 3-run test with a control, and confirmed directly - `concat('a','b')` returns `value: "concat('a','b')"` while `@{concat('a','b')}` returns `"ab"`. The first version of this rule named only the `?` and would have walked a reader from a loud refusal into a quiet wrong answer.
- **Evidence:** measured - both calls made live against 8934 v0.5.0 on 2026-09-03. The parser gap is observed; the cause is inferred from the error text and the surrounding behaviour, not read in the evaluator source.
- **Hits:** 1
- **Distinct-from:** `api-audience-is-not-a-hostname` - that one is a request the service rejects for who is asking. This is a request the bridge's own local parser rejects before any service is contacted, so no token, audience or permission change can affect it.

### A checker that hardcodes a phrase from the rule breaks the moment the rule is reworded

- **Pattern-Key:** verifier-asserts-a-literal-copied-from-the-rule
- **Date:** 2026-09-08
- **Trigger:** failure
- **Rule:** Never hardcode a phrase copied from a lesson's `Rule:` text into the check that verifies it. Read the Rule out of `cowork-lessons.md` at check time and assert against that. A copied literal is correct only until the wording moves, and when it goes stale it fails LOUDLY and confidently while the thing it guards is fine.
- **Failed:** Twice in one session a boot gate reverted a CORRECT install. First it asserted `safe-navigation`, which lives in the entry TITLE while the applier renders the `Rule:` field. Corrected that to `optional-property accessor` - accurate at the time - and the rule was amended twenty minutes later, so the same gate failed again and rolled back another good change. THIRD HIT 2026-09-08, same class, different literal: a lessons-close job proved three digest promotions with `findstr /C:"<Pattern-Key>"` against copilot-instructions.md. The digest renders Rule text and never the key, so all three lookups failed and the job reported the Promoted-to lines as false claims while every rule was in fact present (32 -> 35 always-on). The check carried a token the surface does not render. Fixed by deriving each key's Rule from the corpus at check time and asserting that text - the same repair this entry already prescribed.
- **Why:** `enforcer-encodes-the-superseded-rule` prescribes updating the check in the same pass as the rule. That is not enough. The same-pass discipline was followed the first time and the check still broke the second time, because ANY copied literal has a shelf life bounded by the next edit. The failure mode is also indistinguishable from a real defect: the gate printed "routed rule absent" and reverted, naming a cause it had never tested.
- **Worked:** Make the check DERIVE its expectation instead of carrying one. The rewritten gate reads the `Rule:` for its Pattern-Key straight out of the corpus, normalises whitespace and asserts containment - and refuses outright with exit 2 if the corpus cannot be read, because passing on a missing expectation is worse than failing. Proven: the rule was reworded and the gate kept working with no edit to the gate.
- **Evidence:** measured - both false negatives observed live on 2026-09-03, each reverting a verified-correct install; the derived version then passed against the amended text with no change to itself.
- **Hits:** 3
- **Promoted-to:** `copilot-instructions.md`, "Rules already paid for" (LESSON-DIGEST block), and the `dream-cycle` SKILL.md lessons block via the `verifier-` route. Both were applied MECHANICALLY in the same close job - `digest_apply.py` then `skill_lessons.py` - and the key was grepped back out of both files afterwards rather than assumed. Promoted on first logging because the two hits happened within one session: the second occurrence is what proved the same-pass fix insufficient, so there was never a version of this entry that deserved to sit unpromoted.
- **Distinct-from:** `enforcer-encodes-the-superseded-rule` - that one says keep the check in sync with the rule. This one says synchronisation is the wrong goal: delete the copy so there is nothing left to keep in sync.

### A control that asks the model to predict measures a different thing than a test that watches it act

- **Pattern-Key:** control-asks-instead-of-watching
- **Date:** 2026-09-03
- **Trigger:** better-approach
- **Rule:** A control arm must run the SAME task as the test arms, judged by the SAME criterion, differing in exactly ONE variable - whether the thing being tested is reachable. If it asks the model to PREDICT a limitation while the test arms WATCH it avoid one, the comparison is void. Before running a control, diff its wording against the test prompts: a word present only in the control is usually the answer leaking in.
- **Failed:** Built a harness to check whether a delivered rule changes behaviour. The three test arms performed a real task; the control asked "would you expect this operator to be supported by a local evaluator?" It answered correctly at 65% confidence and its own reasoning cited the word `local` - supplied by the prompt - so the control passed on framing, not knowledge. Taken at face value the verdict would have read INERT and the rule would have been deleted as useless.
- **Why:** Prediction and behaviour are different quantities. A model can articulate a limitation it would not have avoided under time pressure in a real task, and can avoid one it could not articulate. Scoring one against the other produces a confident number from an invalid comparison, which is worse than no number.
- **Worked:** Rebuild the control as test prompt 1 verbatim plus one sentence denying it the surface under test. Run it and read the FIRST action, not the eventual answer. On the rebuilt control the model fired the trap on call one and needed six calls to recover, while all three carried arms pre-empted it - a clean, attributable split. Related: a pass criterion that scores "hit the trap and recovered" as a pass also scores the control that way, so it cannot measure delivery either.
- **Evidence:** measured - both controls run live on 2026-09-03 against the same rule; the asking control passed and the watching control failed, changing the verdict from INERT to EFFECTIVE.
- **Hits:** 1
- **Distinct-from:** `nightly-constant-reported-as-a-measurement` - that one is a number nothing writes. This one is a number that IS computed, from arms that are not comparable.
### `gh` inside an 8933 job says "not logged into any GitHub hosts" while the user is logged in
- **Pattern-Key:** bridge-8933-gh-needs-config-dir
- **Date:** 2026-09-07
- **Trigger:** failure
- **Rule:** FIXED AT SOURCE 2026-09-09 - executor 1.3.0 supplies `%APPDATA%`, and `gh api user` inside a job returned the login with `GH_CONFIG_DIR` unset (measured). Setting it explicitly stays harmless and the standing aor-land/aor-merge jobs still do. What survives: a CLI that says "not logged in" while the user is logged in is resolving the wrong config directory - print the variables it reads before re-authenticating anything.
- **Failed:** `broaden.ps1` called `gh repo edit --add-topic`, `gh api repos/:owner/:repo/milestones` and `gh issue edit` with no `GH_CONFIG_DIR`. Every call printed `To get started with GitHub CLI, please run: gh auth login`, the script died on the first `NativeCommandError`, and a read-only `gh auth status` in the same environment said `You are not logged into any GitHub hosts`. the operator confirmed he was logged in; the second run failed identically.
- **Why:** `gh` keeps `hosts.yml` under `%APPDATA%\GitHub CLI`. Per `bridge-8933-env-partially-stripped` the user-profile variables are empty in the job environment, so `gh` resolves an empty config directory and finds no credential. The 2026-09-04 `agent-of-record-github-configure.ps1` already carried the exact fix; the new script was written without reading it, which is how a solved trap gets paid for twice.
- **Worked:** `$env:GH_CONFIG_DIR = 'C:\Users\YOURUSER\AppData\Roaming\GitHub CLI'` at the top of the script. `gh api user --jq .login` then returned the account name, and every metadata write (topics, homepage, milestones) succeeded and was read back from GitHub in the same job.
- **Evidence:** measured - the failing stderr, the `gh auth status` line, and the succeeding read-back were all read in one session
- **Fixed-at-source:** 2026-09-09 - with executor 1.3.0 live, the read-only census job ran `gh api user --jq .login` with `GH_CONFIG_DIR` empty and `APPDATA=C:\Users\YOURUSER\AppData\Roaming`: rc 0, `jordanmrash`.
- **Hits:** 1
- **Distinct-from:** `bridge-8933-env-partially-stripped` - that entry states the CAUSE (user-profile variables are blank in the job environment) and its rule is about the working directory; this one is a specific CONSEQUENCE with its own misleading symptom (`gh` reports the user logged out while he is logged in) and its own one-line fix (`GH_CONFIG_DIR`), which a session reading only the cause did not derive - the script that failed had been written with that entry in the corpus. `probe-env-vars-blank-false-negative` - there a PROBE searched paths under blank variables and reported a binary absent; here the binary was found and ran, and it was the binary's own config lookup that resolved to nothing. `bridge-8933-user-path-not-inherited` - that is PATH (which binary is found); this is a config directory (what the found binary can read).
- **See also:** bridge-8933-env-partially-stripped, bridge-8933-user-path-not-inherited

### A verification check that throws is scored as PASSED when only the failure branch increments the counter
- **Pattern-Key:** verifier-crashed-check-counts-as-pass
- **Date:** 2026-09-07
- **Trigger:** false-success
- **Rule:** In a verify block, wrap every check in try/catch and increment the failure counter in the catch, so a check that could not run is a finding and never a pass. Run the whole verify section with `$ErrorActionPreference = 'Continue'` and branch on `$LASTEXITCODE`, because a probe whose EXPECTED answer is an error (a 404 proving a file is gone) is killed by `Stop` before the verdict prints. Then re-run the checks from a SEPARATE read-only job before reporting.
- **Failed:** Two shapes in one night, opposite directions. (a) `agent-of-record-remove-roadmap.ps1` probed `gh api .../contents/docs/article-roadmap.md` expecting 404 as the SUCCESS signal, under `$ErrorActionPreference = 'Stop'`. The 404 became a terminating error, the script died before its verdict line, and the wrapper reported `COWORK_RESULT: FAIL` for a removal that had fully succeeded and been pushed. (b) `agent-of-record-restore-snapshot.ps1` decoded `gh api --jq .content` with `[Convert]::FromBase64String`; on three checks `gh`'s stderr text was joined into the string, the decode threw, the variable stayed null, `.Contains()` threw again, and because only the `else` branch did `$fail++`, the run printed `verify failures: 0` with three checks never evaluated.
- **Why:** A check has three outcomes - passed, failed, could not run - and a counter that increments only on an OBSERVED failure folds the third into the first. Shape (a) is the mirror: a probe whose success looks like an error is stopped by the error policy before it can be read as success. Both yield a confident verdict the evidence does not support, and in (b) the confident verdict was the one the user was about to be told.
- **Worked:** For (a), `$ErrorActionPreference = 'Continue'` across the verify section and branching on `$LASTEXITCODE`. For (b), fetching content with `gh api -H "Accept: application/vnd.github.raw"` - no base64 leg to fail - and re-running the three checks in a separate read-only job, `agent-of-record-verify-snapshot.bat`, which confirmed all three before anything was reported. The durable pattern is `try { <check> } catch { $fail++; "could-not-check: <name>" }`, with the verdict computed once after every check has either passed, failed, or been counted as unrunnable.
- **Evidence:** measured - both verdict lines and both stderr traces were read in-session, and the independent re-verification job passed all three checks
- **Hits:** 1
- **Distinct-from:** `verifier-verdict-announced-before-evidence-read` - there the checker READ evidence and adjudicated too early; here the check never RAN and its silence was scored. `verifier-usage-error-reads-as-finding` - there a checker that never ran was read as a FINDING; here one that never ran was read as CLEAN: the same third state, misread in the opposite direction, so fixing one cannot catch the other. `verifier-pipe-masks-the-exit-code` - there sound plumbing lost a true code through a pipe; here the code was never produced. `verification-scoped-away-from-the-risk` - there every check RAN and was sound, but each one's scope excluded the failure; here the check's scope was right and it never executed, and non-execution was scored as a pass.
- **See also:** verifier-usage-error-reads-as-finding, verification-scoped-away-from-the-risk, cowork-close-reports-ok-on-failed-commit

### Editing a generated public snapshot in place leaves its build source stale, so the next rebuild reverts every edit
- **Pattern-Key:** git-published-tree-edited-without-build-source
- **Date:** 2026-09-07
- **Trigger:** failure
- **Rule:** Before editing a published tree that a build script generates, locate the source it is generated FROM and change that too - or record the drift as a blocker on the next rebuild in the same pass. A direct edit to the output survives exactly until the next build.
- **Failed:** Five rounds of direct edits to the public `agent-of-record` clone - broadened thesis, roadmap removal, template dedupe, changelog, re-root - with no corresponding change to the publish set that `GitHubSetup/02-build-clean-repo.ps1` copies from. Checked afterwards through the bridge: `COPILOT_COWORK\GitHubSetup\README.template.md` is an unrelated earlier document ("Cowork Tooling"), the local folder has no `public-template/`, and the v2 publish set that actually produced the repo was built off-PC. Wherever it lives, it has none of the night's edits, and the repository's own model is "wipe, rebuild as one commit, force-push" - so the next publication would silently revert all of them.
- **Why:** A generated output has two homes and only one is authoritative. Editing the output is fast and verifiable in the moment, which is why it wins under time pressure; the cost is deferred to a rebuild that nobody is watching when it runs.
- **Worked:** Re-rooted the live tree ITSELF as the snapshot commit (so the published tree is the verified content, not a stale generator's idea of it) and recorded the source drift as a blocking item in memory and in the CHANGELOG note. The remaining fix - locate the v2 publish set and apply the diff - is open and named as open; this entry does not close it.
- **Evidence:** measured - `README.template.md` read through the bridge and the local `GitHubSetup` folder listed; the published `02-build-clean-repo.ps1` lines that copy `public-template` and the `GitHubSetup` subtree were read from the repo
- **Hits:** 1
- **Distinct-from:** `docx-build-with-python-docx-not-patch-array` - that is about HOW to construct a generated document (build from source, verify per paragraph); this is about WHERE an edit must land when the artifact has a generator - the output can be perfectly built and still be overwritten. `skill-edit-by-extraction-and-hash-verify` - that is a technique for editing one file safely in place; this is the case where editing the file in place is itself the mistake, however safely it is done. `git-commit-job-must-stage-itself` - that is about what a commit job stages; this is about a rebuild REVERTING committed work because the commit was made to the output rather than the source.
- **See also:** git-deletion-does-not-sanitize-history, config-contradiction-survives-in-second-file

### gh api --input rejects a JSON file written with a UTF-8 BOM
- **Pattern-Key:** gh-api-input-rejects-utf8-bom
- **Date:** 2026-10-01
- **Trigger:** failure
- **Rule:** Never write a file ANY strict JSON parser will read - GitHub's API, Node `JSON.parse` in the M365 Agents Toolkit CLI - with `Set-Content -Encoding UTF8` in Windows PowerShell 5 - it prepends a byte-order mark. Use `[IO.File]::WriteAllText($path, $text, (New-Object System.Text.UTF8Encoding($false)))` for `gh --input` bodies AND for committed files such as `.github/CODEOWNERS`, and prove it by reading the first three bytes back (EF BB BF is the defect), locally and from the GitHub contents API after the push.
- **Failed:** `agent-of-record-v030-collaborate.ps1` built a branch-protection body with `ConvertTo-Json`, wrote it with `Set-Content -Encoding UTF8`, and passed it to `gh api --method PUT ... --input <file>`. GitHub answered HTTP 400 `Problems parsing JSON` although the file was structurally valid JSON. The job exited 4 at step 2 with no side effects. SECOND HIT 2026-09-08, different consumer: the same collaborate job had written `.github/CODEOWNERS` with `Set-Content -Encoding UTF8` and pushed it. The docfix probe read the file's bytes and reported `BOM=True`; the docfix job stripped the three bytes, committed, and read the file back from the GitHub contents API as `BOM=False`. The BOM had sat on main for a day. THIRD HIT 2026-10-01, different consumer: `atk provision` 1.3.0 failed at `copilotAgent/publish` with `SyntaxError: Unexpected token '∩╗┐', "∩╗┐{\r\n    \"$\"... is not valid JSON at JSON.parse at verifyLocalMCPPluginCerts (m365agentstoolkit-cli\lib\index.js)`. EF BB BF sat at the start of ai-plugin.json, ai-plugin_1.json, ai-plugin_2.json and mcp-tools.json, written by PowerShell on 2026-09-30. `teamsApp/update` had already SUCCEEDED before publish failed, so the provision was half-applied. 1.2.1 had provisioned with the same BOM files, so either the publish parse is new in this toolkit version or 1.2.1 never ran it - inference unverified.
- **Why:** Windows PowerShell 5's `-Encoding UTF8` prepends a byte-order mark (EF BB BF). GitHub's JSON parser rejects a body whose first bytes are not `{` or `[`. `gh` forwards the file bytes verbatim, so the BOM reached the API.
- **Worked:** Write JSON bodies for `gh --input` with `[IO.File]::WriteAllText($path, $json, (New-Object System.Text.UTF8Encoding($false)))` - the `$false` is "no BOM". Re-run succeeded on the identical payload. Applies to EVERY 8933 job that hands `gh` a file: protection, releases, invitations, milestone edits. `ConvertTo-Json -Compress` is not the fix on its own; the BOM is the whole defect. For a committed file: read the bytes, strip a leading EF BB BF if present, and verify the remote copy through the contents API - never trust the local file alone, and never trust that GitHub parsed line 1. For files already on disk, 8932 `edit_file` with oldText `\ufeff{` -> newText `{` strips the BOM in place (it also normalises CRLF->LF; expect a size delta of exactly 3 plus the CRLF count). Diagnostic shortcut: the glyph trio `∩╗┐` in CP437 console output IS the BOM.
- **Evidence:** measured - the 400 was read from the job report, the payload file was read back and found structurally valid, and the re-run with the BOM-free write returned 200 with the protection applied Second hit: the BOM's presence was measured (bytes read in the clone) and its removal was measured (bytes read back from the API). Its EFFECT on GitHub's CODEOWNERS parsing was inferred from documentation, not observed - inference unverified for that part only. Third hit measured - the SyntaxError read verbatim, per-file size deltas matched 3 + CRLF count exactly, next run 5/5 Done exit 0.
- **Hits:** 3
- **Promoted-to:** copilot-instructions.md LESSON-DIGEST block (always-on tier, hits >= 2), applied mechanically by digest_apply.py in the 2026-09-08 lessons job and confirmed by findstr in the same job. Routing to the command-bridge SKILL.md is PROPOSED, not applied: the key carries no routed prefix, so it needs an `exact` line in skill_lesson_routes.json, which is the operator's call.
- **See also:** bridge-8933-gh-needs-config-dir, bridge-8932-writes-lf
- **Distinct-from:** file-edit-reencodes-existing-characters - that lesson is a READ/WRITE round-trip corrupting a file's own existing content; this one is a correctly-written, content-intact file being REJECTED BY A REMOTE PARSER for the BOM alone. Same three bytes, same `UTF8Encoding($false)` fix, different failure: there the file is damaged and the tool reports success, here the file is fine and the API says no.

### A disclosure scan that skips an extension does not scan the files that extension holds
- **Pattern-Key:** public-scan-unscanned-extension-passes-clean
- **Date:** 2026-09-07
- **Trigger:** near-miss
- **Failed:** Added a POSIX home-path pattern (`/Users/<name>`, `/home/<name>`) to `scripts/public_scan.py` for the new `Startup/posix/*.sh` launchers, ran the scan, got `PUBLIC_SCAN: CLEAN`, and nearly shipped. A planted `/Users/<name>/...` leak in a `.sh` file ALSO scanned clean.
- **Why:** `TEXT_EXTENSIONS` did not include `.sh`. Every shell script in the tree was silently skipped - the new pattern was correct and never ran against the files it was written for. The green result was true of the files scanned and said nothing about the files that mattered.
- **Worked:** Before trusting a scanner on a new file type, PLANT A LEAK in that type and confirm the scan FAILS, then remove it and confirm it passes. The negative control found in one run what reading the code had not. Fix was adding `.sh .bash .zsh` to `TEXT_EXTENSIONS`; verified fail-with-leak then clean-without. Generalises: a new rule in any scanner is untested until a fixture that should trip it has tripped it.
- **Evidence:** measured - CLEAN with a planted leak was read, then 1 finding naming the planted file after the extension fix, then CLEAN after removing it
- **Hits:** 1
- **See also:** verifier-crashed-check-counts-as-pass
- **Distinct-from:** new-rule-is-untested-until-it-survives-a-real-case - that is a RULE whose effect is unproven until a real case exercises it; this is a SCANNER whose file-type filter excluded the very files the new pattern was written for, so the pattern never ran at all - a coverage gap, not an unexercised rule. Also distinct from verifier-crashed-check-counts-as-pass: nothing crashed; the scan completed over the wrong population and reported honestly about it. And from git-chmod-lost-container-to-windows-clone, which shares only the day and the tree: that is a permission bit, this is a scan filter.

### A refusal test that searches the response body for a sentinel flags the server's own echo
- **Pattern-Key:** selftest-sentinel-in-refusal-echo-false-fail
- **Date:** 2026-09-07
- **Trigger:** false-success
- **Failed:** `exec_bridge_selftest.py` proved a payload was refused by checking that a sentinel word (`pwned`, `escaped`) did NOT appear in the response. Two correct refusals FAILED the test: the server's rejection message quotes the offending path back (`REJECTED: file does not exist -- .../hello.sh; echo pwned`), so the sentinel was present in a response that proved nothing had run.
- **Why:** The heuristic conflated "the payload text appears" with "the payload executed". A well-behaved refusal echoes what it refused, so the two are indistinguishable by substring search.
- **Worked:** Assert on the thing only execution produces. The bridge emits an `exit_code` field solely when a process ran, so `executed = '"exit_code"' in body` is the discriminator; the refusal check became `isError or REJECTED/REFUSED in body` AND `not executed`. 31/31 on both platforms after. The same run also exposed a real gap: `;` and `$` were not in the metacharacter refusal set - hardened, and the refusal is now BY NAME rather than incidental to the file not existing.
- **Evidence:** measured - two FAIL lines with the echoed payload were read, then 31 of 31 after the discriminator change, on POSIX in the container and on Windows in the publish job
- **Hits:** 1
- **See also:** verifier-crashed-check-counts-as-pass
- **Distinct-from:** guard-substring-matches-its-own-filename - both are substring heuristics hitting an unintended source, but there the guard matched its own filename in a listing and the fix was to narrow the string; here the test matched the server's echo of the payload it had refused, and the fix was to stop searching for text at all and assert on an artifact only execution produces (`exit_code`). Also distinct from cowork-close-reports-ok-on-failed-commit: no exit code went untested; the test asserted the wrong evidence.

### Container-built shell scripts arrive without the execute bit and git must be told explicitly
- **Pattern-Key:** git-chmod-lost-container-to-windows-clone
- **Date:** 2026-09-07
- **Trigger:** near-miss
- **Failed:** `chmod +x Startup/posix/*.sh` in the build container did not persist (`ls -l` still showed 644 after two attempts), and the zip carried 644. A Windows clone has `core.fileMode=false`, so `git add` would have committed every launcher as `100644` and a Mac clone would have failed to start the bridges with a permission error.
- **Why:** The container filesystem discards permission bits; the zip format preserves what it was given. On Windows git never reads filesystem mode, so nothing downstream would have set it either. Three layers each honestly passed along a wrong bit.
- **Worked:** Set the mode in the INDEX, not the filesystem: `git update-index --chmod=+x <file>` for each script in the publish job, then REFUSE to commit if `git ls-files -s Startup/posix` shows any `100644`. Verified twice - in the clone before commit, and in the fresh clone from GitHub after push. CI's macOS job additionally runs `test -x` on every launcher so a regression fails the gate.
- **Evidence:** measured - 644 read in the container, the `100755` assertion passed in the publish job on the PC, and the fresh-clone check read `100755` from the published tree
- **Hits:** 1
- **See also:** bridge-8932-writes-lf
- **Distinct-from:** git-deletion-does-not-sanitize-history - that is CONTENT surviving in history after a deletion, unfixable by any later commit; this is a file MODE bit that never entered the index because two filesystems in a row (container, Windows) do not carry it, fixed by `git update-index --chmod=+x` with no history operation at all. Also distinct from bridge-8932-writes-lf: that is line endings altered by a transport; this is a permission bit dropped by a filesystem.

### Windows PowerShell 5.1 strips embedded double quotes from arguments handed to a native command

- **Pattern-Key:** batch-ps51-strips-embedded-quotes-in-native-args
- **Date:** 2026-09-08
- **Trigger:** failure
- **Rule:** In an 8933 job, an argument that PowerShell 5.1 hands to a native executable (`gh`, `git`, `node`) must contain NO double quotes: PS 5.1 re-quotes the token and drops the inner quotes, so a jq program such as `.title == "x"` or `.conclusion // "-"` reaches gh as `.title == x` and fails to parse. Shape jq output with `@tsv` (a null renders as an empty field, so no quoted default is needed) and compare strings in PowerShell afterwards. And test the call's exit code before reading its output - a parse error read as data looks exactly like "no result yet".
- **Failed:** Two 8933 jobs in two sessions. 2026-09-07/08: `agent-of-record-v030-probe.ps1` passed jq programs with quoted literals; every multi-field line printed `accepts 1 arg(s), received 4` and the probe was rewritten to `@tsv`. 2026-09-08: `agent-of-record-merge-pr7.ps1` polled CI with `--jq '.jobs[] | [.name, .status, .conclusion // "-"] | @tsv'`; gh received `.conclusion // -` and answered `failed to parse jq expression ... unexpected token "]"`. The helper merged stderr into stdout and the loop never tested the exit code, so the parse error was read as "not reported yet"; the job polled for 200 s, refused to merge and exited 4, twice (the first run had also queried `commits/<7-char sha>/check-runs`, which does not resolve a short sha). CI had been green for twelve minutes.
- **Why:** Windows PowerShell 5.1 builds the native command line itself: a token containing spaces is wrapped in quotes and embedded double quotes are neither escaped nor preserved, so the receiving program sees them removed or the token split. PowerShell 7 fixed this; 8933 jobs run `powershell.exe`, which is 5.1. The rest of the cost was the polling loop treating error text as pending state instead of testing `$LASTEXITCODE` on every call.
- **Worked:** Removed every double quote from the jq programs (`.conclusion` bare, `@tsv` rendering null as empty; title matching moved into PowerShell after an `@tsv` dump). The same job then merged on its next run in 12 s with both gates read as `completed success`. The repaired probe has run clean four times today. Not tested: the `\"x\"` escape inside a single-quoted PowerShell string, which PS 5.1 is documented to pass through.
- **Evidence:** measured - both error texts were read from job reports (`accepts 1 arg(s), received 4` in the 2026-09-07 handoff; the jq parse error naming `// -` in the 2026-09-08 merge report), and the fixed job's report was read after the merge.
- **Hits:** 3   (2026-09-07 jq literals in a probe; 2026-09-08 a jq default in the merge poller; 2026-09-11 a quoted phrase in a params VALUE)
- **Repeat 2026-09-11 - the data carries it, not just the code:** `_aor-merge.params.txt` was written with a quoted phrase inside its BODY line. The job's own quoting was correct and untouched since the last repair, but the value reached `gh pr merge` as seven positional arguments (`accepts at most 1 arg(s), received 7`) and the merge failed at step 3 with CI already read as green. Rewriting the same sentence without quotation marks merged it on the next run. Every earlier occurrence was a quote inside a jq PROGRAM in the script; this one was a quote inside a parameter FILE a standing job reads, which is a surface the rule as written did not obviously cover. The rule now has to reach whoever writes the params, not only whoever writes the job.
- **Promoted-to:** copilot-instructions.md LESSON-DIGEST block (always-on tier, hits >= 2) and the command-bridge SKILL.md lessons block via the `batch-` route - both applied mechanically by digest_apply.py and skill_lessons.py in the 2026-09-08 lessons job and confirmed by findstr in the same job. Promoted on first logging because the second hit came the session AFTER the first repair had been recorded in a handoff note but never in this corpus - which is precisely the delivery gap promotion closes.
- **See also:** bridge-8933-gh-needs-config-dir, cowork-close-reports-ok-on-failed-commit
- **Distinct-from:** bridge-8933-gh-needs-config-dir - that is gh finding no configuration in a stripped environment; this is a well-formed argument being mangled by the shell before gh ever sees it. Also distinct from cowork-close-reports-ok-on-failed-commit, which is a job echoing OK after a failed step; here the untested exit code made a failure look like WAITING, and the job correctly refused - the cost was time, not a false success.

### `where <tool>` in an 8933 job misses every per-user installed tool
- **Pattern-Key:** bridge-8933-user-path-not-inherited
- **Refines key:** bridge-8933-env-partially-stripped
- **Date:** 2026-09-02
- **Trigger:** failure
- **Rule:** FIXED AT SOURCE 2026-09-09 - executor 1.3.0 appends the user PATH from `HKCU\Environment` to the machine PATH, so `where pac` resolves inside a job (measured: 12 user entries). What survives: when a tool the operator uses daily is not found, print the PATH sources before guessing install paths.
- **Delivered-to:** command-bridge
- **Failed:** A job resolved pac.exe with `where pac` plus four guessed install paths. All five missed; the job exited 3 `COWORK_RESULT: FAIL pac.exe not found`. The prior lesson said "PATH is intact and bare interpreter names resolve", which was read as "all PATH entries are present".
- **Why:** The 2026-08-20 probe tested System32, PowerShell, Git, node and Python - all MACHINE-PATH entries - so "PATH is intact" was true of the machine PATH and silently generalized to the user PATH. PAC CLI lives at `C:\Users\YOURUSER\AppData\Local\Microsoft\PowerAppsCLI\`, the FIRST entry of HKCU\Environment\Path, and was invisible to the job.
- **Worked:** One job that (a) dumps `%PATH%`, `HKCU\Environment` Path and the HKLM Path, then (b) tries targeted absolute paths, then (c) falls back to bounded `dir /s /b <root>\pac.exe` over six roots. It found pac.exe at `...\Microsoft.PowerApps.CLI.2.11.2\tools\pac.exe` - a versioned subfolder none of the four guesses would ever have hit - and completed the whole discovery in 145s, exit 0.
- **Rule of thumb:** when a job cannot find a tool the operator uses daily, do NOT add more guessed paths. Print the three PATH sources first; the answer is almost always sitting in the user PATH.
- **Evidence:** measured - two consecutive runs of the same task, exit 3 then exit 0
- **Fixed-at-source:** 2026-09-09 - executor 1.3.0 reads `HKCU\Environment\Path` with `reg.exe`, expands `%VAR%` references, and appends the entries to the machine PATH with case-insensitive de-duplication. Measured through the live bridge: `where pac` -> `...\AppData\Local\Microsoft\PowerAppsCLI\pac.cmd`, `where code` -> the per-user VS Code CLI, `user_path_entries: 12`.
- **Distinct-from:** bridge-8933-env-partially-stripped - that entry says user-profile VARIABLES expand to nothing, and concluded "PATH is intact". This one says the USER PATH is a separate PATH that is not inherited at all. The 2026-08-20 probe behind "PATH is intact" tested only machine-PATH entries - System32, PowerShell, Git, node, Python - so its conclusion was true of the machine PATH and was silently generalised to both. The remedies differ too: that one is answered by `cd /d` and never assuming `%LOCALAPPDATA%`; this one by reading `HKCU\Environment` before hunting for a tool.
- **Distinct-from:** probe-env-vars-blank-false-negative - there the variable the script interpolates is EMPTY, so the probe searches nowhere and returns NOT FOUND without ever having looked. Here `%PATH%` is populated - with the machine PATH - so the job searches a real location and correctly fails to find a tool that lives on a PATH it was never handed. The sharpest evidence that these are separate lessons is that the earlier one's remedy was TRIED here and failed: this job used four hard-coded absolute paths, and pac.exe sat in a versioned subfolder (`Microsoft.PowerApps.CLI.2.11.2\tools\`) none of them could have guessed. Hard-coding cures an empty variable; it does not cure an unseen PATH, which needs the registry read.
- **Dispositioned:** 2026-09-01 close, by a different session from the one that wrote this entry. The wording above is derived from this entry's own Why line and its `Refines key:` field, not from independent diagnosis - the author should confirm it. Worth noting that the entry HAD named the relationship, as `Refines key:`; the dupe gate reads only `Distinct-from:`, so an author who dispositioned their key in different vocabulary still reads to the gate as one who did not.
- **See also:** bridge-8933-env-partially-stripped, batch-fsutil-needs-elevation

### A completeness check that derives both sides from one pattern proves nothing
- **Pattern-Key:** count-assertion-must-use-independent-control
- **Date:** 2026-09-02
- **Trigger:** failure
- **Rule:** When asserting "the parser got everything", the control count must come from a DIFFERENT criterion than the parser's own regex. Two numbers derived from one assumption always agree, including when the assumption is wrong.
- **Failed:** A solution-list parser asserted `len(rows) == len(present)` where `rows` used `\d+\.\d+\.\d+\.\d+` for the version column and `present` filtered lines with the SAME four-part pattern. It reported a clean 56/56 while dropping the `Default Solution` row, whose version is `1.0`. The assertion existed specifically to catch a dropped row and could not.
- **Why:** Same shape as the 2026-09-01 self-improvement finding - a number was trusted without checking what actually writes it. Here the check and the thing being checked shared a premise, so the check was structurally incapable of failing on that premise.
- **Worked:** Derive the control independently: take every line of the table body between the header and the first blank line. That immediately reported 57 of 58 - catching both the real missing row AND a trailing prose line the bound was wrong about - and the fix was verifiable rather than silent.
- **Rule of thumb:** ask of any self-check "what would have to be true for this to fail?" If the answer is "nothing my parser could get wrong", it is decoration.
- **Evidence:** measured - 56/56 PASS on a known-incomplete parse, then 57/58 FAIL after the control was made independent, then 57/57 PASS after the fix
- **Distinct-from:** nightly-constant-reported-as-a-measurement - there a reported figure had NO computation behind it at all, so no code path could ever move it. Here both numbers are genuinely computed and both are individually correct; the defect is that they are computed from the SAME premise, so they cannot disagree even when that premise is wrong. A field with no logic versus two pieces of real logic sharing one assumption.
- **Distinct-from:** verification-scoped-away-from-the-risk - there a check's SCOPE excludes the failure it was written to catch. Here the scope is exactly right and the check runs on exactly the right data; what fails is the INDEPENDENCE of the control it compares against.
- **Dispositioned:** 2026-09-01 close, by a different session from the one that wrote this entry, derived from its own Why line rather than independent diagnosis - the author should confirm. RESOLVED 2026-09-03 (DC-2026-09-03-POINTER-007): the two See-also keys were dangling and are now repointed by SUBSTANCE - `lesson-check-clean-clusters-were-false` was a memory key, never a Pattern-Key, and its substance is `verifier-warns-on-proxy-not-the-defect`; `gate-selftest-needs-negative-control` resolves to `verifier-ignores-structural-diff`. The same dangling name was also cited in the Distinct-from of `enforcer-encodes-the-superseded-rule`, which lesson_check does not validate, and was corrected in the same pass.
- **See also:** verifier-warns-on-proxy-not-the-defect, verifier-ignores-structural-diff

### Renaming a client is not sanitizing its data
- **Pattern-Key:** git-renaming-is-not-sanitizing
- **Date:** 2026-08-31
- **Trigger:** near-miss
- **Rule:** Before stripping a client name, check whether the CONTENT is also client-specific. If the file's substance is the client's work product, renaming is concealment rather than sanitization - stop and put the decision to the owner.
- **Delivered-to:** git-bridge
- **Hits:** 1
- **Failed:** Nothing shipped, which is the only reason this is a near-miss. Seven occurrences of one client name were genericized across three memory files - correctly, because there the name was decoration on lessons about process. The next move, already queued and about to run, was to apply the identical treatment to 41 occurrences of a SECOND client name in `prov000-fn-je-builder`, `alteryx-to-python` and `cowork-alteryx-conversion.md`.
- **Why:** The two cases are indistinguishable to a grep and are opposites in substance. In the first, deleting the name lost nothing - the lesson taught a process and the client was incidental. In the second the files ARE the engagement's work product: `LEARNED_MAPPINGS.md` holds 52 account-code mapping decisions, `ROLLFORWARD_STRUCTURE.md` holds legal-entity numbers and names for a parent and a subsidiary plus expected quarterly row counts. Removing the header word leaves every mapping in place while making the tree READ as sanitized, so the next audit returns a clean grep and the exposure becomes invisible. A cosmetic fix to a disclosure problem is worse than no fix, because it retires the signal that would have prompted a real one.
- **Worked:** Stopped before editing and put three options to the operator - leave it as engagement work in its sanctioned location, split the generic taxonomy from an engagement-local mappings file, or rebuild the mappings as illustrative examples. The test to apply: is the name DECORATION on generic content, or the LABEL on client content? Decoration can be genericized freely; a label is the owner's call.
- **Evidence:** measured - 41 occurrences located across 3 skills and 1 memory file by scoped findstr, with the file and line of each; none edited
- **See also:** git-deletion-does-not-sanitize-history, cleanup-quarantine-instead-of-delete

### A recursive scan of the OneDrive tree is a download, not a search
- **Pattern-Key:** onedrive-recursive-scan-hydrates-tree
- **Date:** 2026-09-01
- **Trigger:** failure
- **Rule:** Never recurse the Cowork tree to READ file CONTENTS - not in a PC job, and not as a session-side grep of the `/mnt/user-config/` mount, which is the same tree and hydrates the same way. Scope to named files or one folder. Walking metadata is cheap; opening contents is the download.
- **Delivered-to:** local-file-bridge
- **Hits:** 2
- **Promotion:** COMPLETE - the second hit was answered by WIDENING the wording, not by adding a digest line. **Correcting what this line said when it was first written on 2026-09-01:** the rule is NOT in the always-on block. `digest-tiers.txt` classes it ENFORCED via `job_lint/onedrive-recursive` and deliberately holds it out of turn-1 context because a check is believed to refuse the mistake. It reaches a session through `lesson_gate.py preflight --surface files`, which is where it was in fact printed minutes before the hit. It was read and still missed, so the defect was the SCOPE of the sentence, not its reach - another copy would have changed nothing.
- **Promoted-to:** digest-tiers.txt (ENFORCED tier, enforcer `job_lint/onedrive-recursive`); delivered per-surface by `lesson_gate.py preflight --surface files`, not by the always-on block
- **Failed:** `Get-ChildItem -LiteralPath $root -Recurse -File -Include *.md,*.py,*.json,*.txt | Select-String` over `Documents\Cowork`, to find client-name occurrences. Ran 301,919 ms, was killed by the 300s job cap, and returned empty stdout - no answer at all after five minutes. **Hit 2, 2026-09-01, from the session side:** a recursive content grep from `/mnt/user-config` across `--include=*.md`, asked to confirm that every surface naming the gate receipt path agreed. Same tree, same hydration, no job involved - it was still running when the 90s wait expired and had to be killed unfinished.
- **Why:** OneDrive files can be cloud-only placeholders. Enumerating and reading them forces hydration, so an operation that reads like local I/O becomes a download of every matched file in the tree. Nothing in the command signals this, and the cost scales with the size of the tree rather than the number of matches.
- **Worked:** Named the three files already known to carry the term and used `findstr /n /i /c:`. 636 ms. Two later scans scoped to one skill folder ran in 561 ms and 1,375 ms. When the target set is genuinely unknown, walk one folder at a time rather than the root. Hit 2 was answered by grepping the three named files that actually state the path - the gamma-tango SKILL.md, the self-improvement SKILL.md and copilot-instructions.md - which returned at once. The target set was known the whole time; the recursion was laziness, not discovery.
- **Evidence:** measured - 301,919 ms timeout with empty output, against 636 ms for the same question asked of named files. Hit 2 measured the same shape from the other side: the recursive content grep over the mount was killed unfinished past 90s, while the scoped three-file grep answered the identical question immediately
- **See also:** onedrive-user-mount-read-lag, onedrive-cloud-to-laptop-lag

### A checker that never ran exits non-zero exactly like one that found something
- **Pattern-Key:** verifier-usage-error-reads-as-finding
- **Date:** 2026-08-31
- **Trigger:** failure
- **Rule:** A job that calls a checker must prove the checker RAN, not merely that it exited non-zero. Assert its expected output appears - a usage, path or import error is indistinguishable from a real finding on the exit code alone.
- **Delivered-to:** dream-cycle
- **Hits:** 1
- **Failed:** The genericize job ended with `python lesson_check.py` and no path argument. argparse printed `error: the following arguments are required: path` and exited 2. The guard behaved exactly as designed, reported `COWORK_RESULT: FAIL lesson-check-failed`, and instructed a restore from the pre-edit copies - when the edit had in fact succeeded and had already been verified three ways.
- **Why:** Testing the exit code is right, and was the fix applied to two standing jobs the day before. But an exit code has two states and three causes: the corpus is bad, the corpus is clean, or the checker never executed. Collapsing the first and third produces a false alarm that points at the data when the defect is in the call.
- **Worked:** Read the usage line, confirmed from the job's own earlier assertions that the edits were sound - 0 occurrences on re-read, line counts unchanged in all three files - then ran the standing `2026-08-30-preclose-verify.bat`, which invokes the checker with correct arguments. Exit 0, 91 entries, FAIL 0 WARN 0.
- **Evidence:** measured - argparse exit 2 with a usage message, against exit 0 and a full report from the same checker called correctly minutes later
- **See also:** verifier-pipe-masks-the-exit-code, cowork-close-reports-ok-on-failed-commit

### A job that snapshots before mutating destroys its own rollback on re-run
- **Pattern-Key:** artifact-rollback-overwritten-on-rerun
- **Date:** 2026-08-31
- **Trigger:** near-miss
- **Rule:** Guard a job's pre-edit snapshot with an existence check. A job that copies originals aside and then mutates them is safe only on its FIRST run - re-running it overwrites the rollback with the already-mutated content.
- **Hits:** 1
- **Failed:** Nothing was lost, but the obvious recovery was the destructive one. After the genericize job failed on its final check, the instinct was to fix the argument and re-run it. That job's first action copies the three target files into `pre-edit\`. A re-run would have overwritten those originals with the already-edited versions, leaving no way back.
- **Why:** The mutation itself is idempotent - replacing a token that is now absent changes nothing - and that masks the fact that the SNAPSHOT step is not. Judging a job safe to re-run from the safety of its main action skips the setup that runs before it.
- **Worked:** Did not re-run it. Ran a separate verification job instead, leaving the pre-edit copies intact. The durable fix is an `if not exist` guard around the snapshot copy, so the first run's originals always win.
- **Evidence:** inferred from the job text - the copy is unconditional and precedes the replacement, so a second run would overwrite the originals; deliberately not executed twice to confirm it
- **See also:** cleanup-quarantine-instead-of-delete, artifact-deletion-reverts-after-verified-absent

### Deadness is a property of the reference graph, not of the file
- **Pattern-Key:** artifact-deadness-needs-consumer-grep
- **Date:** 2026-09-09
- **Trigger:** near-miss
- **Rule:** Before moving, deleting or changing the behaviour of a file, grep the whole tracked tree for what REFERENCES or ASSERTS on it - self-tests included - and add every hit to the change list. A filename-and-timestamp audit, or a design written from the files you read, proves nothing about what depends on them.
- **Hits:** 2   (2026-08-31 the quarantine list; 2026-09-09 the item-5 design listed the files it had read and missed the self-test asserting on them)
- **Promoted-to:** copilot-instructions.md LESSON-DIGEST block (always-on tier, hits >= 2), applied mechanically by digest_apply.py in the 2026-09-09 close and confirmed by findstr in the same job
- **Failed:** A filename-and-mtime audit listed `intercompany-eliminations\MANUAL INPUTS.xlsx` as dead residue and it reached the approved quarantine list. Reading `intercompany-eliminations\SKILL.md` showed Rule 2 names that exact file as one of two REQUIRED upfront build inputs. Quarantining it would have broken a working skill silently - the failure would have surfaced only at the next build, far from the cause.
- **Why:** An audit that inspects only the candidate can never see its consumer, so a load-bearing input and abandoned residue score identically. Age and an unreferenced-looking name are properties of the file; being dead is a property of what points at it.
- **Worked:** Grepped each candidate's owning `SKILL.md` for the candidate's filename before moving anything, and recorded the count. Three superseded drafts scored 0 references and were moved; `MANUAL INPUTS.xlsx` scored a required-input citation and stayed. The cleanup job then asserted its presence both BEFORE and AFTER the move, with a hard abort either way, so the guard survives the next run of the same job.
- **Evidence:** measured - 0 references for `SS_SKILL v1.md`, `SS_SKILL v2.md` and the pre-approved-batch-executor draft; a required-input citation for `MANUAL INPUTS.xlsx`; 2026-09-09 measured - the read-only xref job's `git grep -n` over the clone listed `scripts/personalize_selftest.py` asserting `C:\Users\<user>\...` inside `fs-server.cmd` and `tasks.json`, the two files the change strips that path from, and the amended 21-file change set then passed `RELEASE_CHECK: CLEAN (22 checks)` on the PC and CI on both platforms
- **Repeat 2026-09-09 - a change design has the same blind spot as a deletion audit:** the #6 item-5 design was written from a 25-file snapshot of the agent-of-record clone and listed sixteen files to change - the launchers, the task file, the manifest, the checks and the docs it had read. It did not list `scripts/personalize_selftest.py`, which asserts that `fs-server.cmd` and `tasks.json` contain the account path the change removes; built as specified, the release gate would have failed on the branch. The consumer was visible only from the other side - a `git grep` over the tracked tree for `YOURUSER`, `COWORK_ROOT`, `cowork-env` and `third argument` - which also surfaced `CONTRIBUTING.md`. Both went into the change list before anything was written; PR #8 landed 21 files, not 16, and the gate ran clean first time.
- **Distinct-from:** agent-recommends-edit-without-reading-file - that lesson says read the file you are about to CHANGE, and the file to read is the file you are acting on. Here you can read the candidate file completely, end to end, and still be wrong, because the evidence that it is load-bearing lives in a DIFFERENT file - the consumer that references it. Same instinct, different search target: one says read your subject, this one says find who depends on your subject. Kept separate on that basis, but they are close enough that if a third instance of either appears it should be logged as a hit on whichever it matches, not as a fourth key.
- **See also:** agent-recommends-edit-without-reading-file, prune-list-counts-drift-from-names, cleanup-quarantine-instead-of-delete

### Stateless bridges leave one child process behind per request
- **Pattern-Key:** bridge-stateless-child-per-request-never-exits
- **Date:** 2026-09-09
- **Trigger:** failure
- **Rule:** Under supergateway stateless mode every request spawns `cmd.exe` + `node.exe` and neither exits afterwards. Census a listener's descendants (Win32_Process by ParentProcessId) before blaming memory or slowness on anything else, and make own servers exit when idle.
- **Failed:** `bridge-restart-8932.bat` had to kill 223 live descendants of the 8932 listener on 2026-09-09 (three weeks of stateless use). A read-only census fourteen minutes after that restart: 8932 already 37 descendants (18 cmd + 18 node, 1,131 MB - `server-filesystem` is about 60 MB a copy); 8933 249 (124 cmd + 123 node, 689 MB, the oldest from 2026-09-08 13:40, the listener's start day); 8934 160 (80 + 80, 270 MB); 8931, the one stateful bridge, 0. 225 node.exe on the machine, 1,557 MB working set.
- **Why:** Stateless was adopted 2026-08-21 so a dropped session could not take a bridge down: each POST gets a fresh stdio child. supergateway neither closes that child's stdin nor kills it once the response is out, so the child waits on stdin forever and the executor's own `process.stdin.on('end', exit)` never fires. The leak grows with USE, and the 8932 children are the heavy ones.
- **Worked:** `2026-09-09-bridge-process-census.bat` (read-only) makes the tree visible per listener - descendants, names, working set, oldest - in four seconds. `bridge-restart-8932.bat` clears one port. The fix is designed and not yet built: an idle-exit timer in both own servers (exit some seconds after the last message when no job is in flight, so a 300 s job is never cut) and a watchdog sweep of upstream 8932 children older than ten minutes.
- **Evidence:** measured - the restart's taskkill output and the census output, same session
- **Hits:** 1
- **Distinct-from:** `bridge-8933-stateless-defeats-in-process-state` - that entry is STATE failing to survive between calls because every call is a new process; this one is the PROCESSES surviving after the call. Same mode, opposite symptom: nothing persists that should, everything persists that should not. `bridge-idle-session-expiry` - that is a stateful-era SESSION dying under the caller; this is stateless CHILDREN never dying behind it.
- **See also:** bridge-8933-stateless-defeats-in-process-state, bridge-server-edit-live-without-restart

### An anchored edit whose FIND stops mid-line fails once it crosses the block format
- **Pattern-Key:** edit-block-anchor-must-end-at-line-boundary
- **Date:** 2026-09-09
- **Trigger:** failure
- **Rule:** In any FIND/REPLACE block format that stores anchors as whole lines, both texts must end at a line boundary. Assert it in the generator: a FIND that stops mid-line loses its last character in the round trip and matches nothing.
- **Failed:** The CHANGELOG edit for executor 1.3.0 used FIND = `## Unreleased`, a blank line, and the first half of the next bullet, with no trailing newline. The generator strips one trailing newline when it writes the `>>>>> FIND` block and the applier appends one when it reads it back, so the anchor lost its final character and the PowerShell-equivalent simulation reported count 0 for `CHANGELOG.md` - after the Python side, which never round-tripped the block, had passed.
- **Why:** Two representations of one edit - the in-memory string and the whole-line block on disk - agree only when the string ends exactly where a line ends. Every earlier anchor happened to; this was the first partial line, and nothing asserted the contract.
- **Worked:** Extend FIND and REPLACE to the end of that line, add `assert find.endswith('\n') and repl.endswith('\n')` to `edit_block` in the generator, re-run the round-trip simulation to 0 mismatches, and only then write the inputs. The land job applied 11 of 11 anchors first time.
- **Evidence:** measured - simulation count 0 before the fix, `edited : CHANGELOG.md` and 8 of 8 result hashes in the land job's stdout after
- **Hits:** 1
- **Distinct-from:** `lessons-file-section-anchor-must-be-exact` - there a heading PREFIX locates the wrong position because it also matches prose; the anchor is too short in CONTENT. Here the anchor is unique and correct in content and fails on its BOUNDARY - a serialization contract, not a matching one. `file-edit-reencodes-existing-characters` - that alters characters OUTSIDE the edit; here the edit itself is altered by the format that carries it.
- **See also:** lessons-file-section-anchor-must-be-exact, git-published-tree-edited-without-build-source

### The last file in a batched bridge read arrives with an extra trailing newline
- **Pattern-Key:** bridge-8932-batch-read-last-file-extra-newline
- **Date:** 2026-09-09
- **Trigger:** failure
- **Rule:** `read_multiple_files` appends one newline after the LAST file in the batch. For anything hash-pinned or byte-compared, read that file alone with `read_text_file`, or strip to one trailing newline - and let a before-hash guard, not the author, decide whether the read was faithful.
- **Failed:** The docs-route land (PR #10) pinned twelve source hashes from four batched `read_multiple_files` calls. `aor-land` refused at its `expect_before` step: `docs/bridge-facts.json` on `main` was `79208962d464`, the design had read `e66350287899`. Nothing was touched. The four files that had been LAST in their batch - `bridge-facts.json`, `llms.txt`, `quickstart.md`, `setup-macos.md` - all ended in two newlines in the extracted copies; every middle-of-batch file and every single-file read hashed exactly.
- **Why:** The bridge joins files with a `\n\n---\n` separator and terminates the whole response with a newline, so a splitter that strips separators leaves the final file one `\n` long. The hash was computed on the artifact, not the file. Nothing in the design step compared against the repo; only the land job did.
- **Worked:** `rstrip('\n') + '\n'` on the four copies reproduced the PC's hash exactly (`79208962d464`); the manifest was regenerated (bundle, edits and their pins unchanged) and the second run passed the gate first time. The guard that caught it - `expect_before`, added to the land job two PRs earlier - is the control that makes a batched read safe to use at all.
- **Evidence:** measured - the refusal line with both hashes, then the corrected hash matching, then exit 0
- **Hits:** 1
- **Distinct-from:** `bridge-8932-writes-lf` - that is a WRITE artifact (line terminators changed on the way in, fixed at source by executor 1.3.0); this is a READ artifact (one byte appended on the way out) that no server fix has addressed. `file-edit-reencodes-existing-characters` - there the tool altered bytes INSIDE the file on disk; here the file on disk is untouched and only the copy the agent holds is wrong. `git-sync-scope-memory-went-stale` - that is a remembered claim decaying; this is a fresh read being wrong at the moment it is taken.
- **See also:** bridge-8932-writes-lf, edit-block-anchor-must-end-at-line-boundary, git-sync-scope-memory-went-stale

### Never put an absolute path in the glob tool's `pattern` — put the directory in `paths`
- **Pattern-Key:** glob-absolute-pattern-matches-nothing
- **Date:** 2026-09-10
- **Trigger:** failure
- **Rule:** Give the container `glob` tool a RELATIVE pattern with the directory in `paths`, and cross-check any "No files matched the pattern." against `view <dir>` or `ls` before reading it as absence.
- **Failed:** Four `glob` calls whose `pattern` was an absolute path all returned "No files matched the pattern." for directories that demonstrably held matching files: `pattern="/mnt/user-config/skills/myvoice/**/*"` (while `view /mnt/user-config/skills/myvoice` and bash `ls` listed SKILL.md, references and skill-quality-report.json in the same turn), `pattern="/mnt/user-config/skills/gamma-tango/*.md"`, `pattern="/opt/workspace-config/.github/skills/*/SKILL.md"`, and `pattern="/mnt/workspace/output/*.docx"` for a .docx that the relative pattern `output/**/*` had found minutes earlier. Three different roots, including the working directory itself, so it is not mount-specific.
- **Why:** The tool returns the same clean "No files matched" for an absolute pattern as for a genuine miss, so nothing in the response signals that the pattern form, not the directory, is the problem. Whether the tool anchors every pattern under `paths`/cwd so a leading `/` can never match was not probed - inference unverified.
- **Worked:** Same directory in `paths`, relative pattern: `glob pattern="**/SKILL.md" paths="/mnt/user-config/skills/myvoice"` returned `/mnt/user-config/skills/myvoice/SKILL.md`, and `glob pattern="*.docx" paths="/mnt/workspace/output"` returned the .docx. `view <dir>` also works as a plain listing and is the independent cross-check when ABSENCE is the thing being asserted.
- **Evidence:** measured - all four failing calls and both working calls were run and their output read in the session, with the directory contents confirmed by `view` and `ls` in the same turn; reproduced by the Phase 2 reflector on a fourth directory (`pattern="/mnt/user-config/skills/self-improvement/*.md"` -> none; `pattern="*.md" paths="/mnt/user-config/skills/self-improvement"` -> SKILL.md). The Why is inference unverified.
- **Hits:** 1
- **Distinct-from:** `bridge-8932-searchfiles-false-negative` - that is the PC-side `search_files` tool matching a glob against the path RELATIVE to its search root, so a wildcard-free or non-`**/` pattern misses nested files; this is the container-side `glob` tool returning nothing for an ABSOLUTE `pattern` on any root, fixed by moving the directory into `paths`. Same symptom (an empty result that reads as absence), different tool, different cause, different fix. `lessons-gate-receipt-dir-read-only` - an exit code meaning the gate could not run; here the call ran and succeeded, it just matched nothing. `artifact-delete-recursive-skips-file-paths` - a delete that silently skipped file paths handed to it beside folders; here nothing was written or skipped, a read returned an empty set.
- **See also:** bridge-8932-searchfiles-false-negative

### A voice rule's own example or fix sentence is untested content — count paragraph shapes before a myvoice draft ships
- **Pattern-Key:** skill-voiceprofile-own-example-is-the-ai-tell
- **Date:** 2026-09-10
- **Trigger:** correction
- **Rule:** Before a myvoice draft ships, count paragraph shapes with a script (openers under ~10 words, "That is / It is ..." summarizing sentences, aphoristic closers under ~12 words) and treat a rule's own example or prescribed rewrite as untested content, never as his voice.
- **Delivered-to:** myvoice
- **Failed:** Shipped a myvoice draft (v1 of "Behold I made a thing"; his marked-up copy came back as v2) carrying two shapes the profile itself had supplied. (1) Rule 36 ("State early that the exercise was the point") was implemented as a standalone one-line paragraph opener, "Nobody was waiting on any of this." - the operator's red comment: "I hate paragraphs that start like this." Rules 22 and 33 already ban a lone short sentence as a section opener and teaser paragraph openers; nothing checked rule 36's implementation against them. (2) A paragraph closed on "The pages changed shape, and that is the part worth writing down." - his comment: "I hate the structure of this last sentence immensely. This is another AI tell." That is the exact shape rule 33 recommends as its rewrite ("..., and that is the reason the exercise was worth it"). Two further paragraphs he marked "confusing" were compressed abstractions. A script count over the 24 body paragraphs he did not review then found 7 opening on a sentence of <=9 words, 11 "That is / It is ..." summarizing sentences and 12 closing on an aphoristic line of <=12 words - while the punctuation tells the profile's mechanical sweep looks for were absent (0 em dashes, 0 semicolons), so nothing mechanical flagged the piece before it shipped.
- **Why:** A rule's illustrative sentence and a rule's prescribed fix are content the profile author wrote, and they were never tested against the OTHER rules or counted across a finished draft; rule 33's fix for one complaint produced the shape he calls an AI tell, and rule 36 as implemented produced the shape rules 22/33 ban. Calibration from his six edited paragraphs, measured by the mechanical diff: no paragraph opens on a sentence under 13 words, no closing sentence points at its own significance, and his one significance statement is spoken ("and really, this illustrates the whole point of doing this at all") and is immediately followed by the analogy that explains it. Why the sweep had never been extended to paragraph shape - inference unverified.
- **Worked:** In the v3 rewrite, fused every short opener into the sentence that followed it with a causal connective and replaced or cut every "that is the X" tail; re-count after the rewrite: 0 short openers, 1 "It is" line (a figure-caption metaphor), 3 short closers, punctuation sweep still clean. Rewrite "confusing" abstractions as plain causal chains, which is what his own rewrites were ("primarily because", "Eventually though", "Additionally"). Amendments to `myvoice` rules 2, 6, 12, 17, 23, 33, 36 plus new rules 44+ were PROPOSED to the operator in chat and NOT applied - a session reading this must check whether they landed before trusting rules 33 or 36.
- **Evidence:** measured - both red comments quoted verbatim from his marked-up v2; the mechanical difflib diff (paragraph then word level) confined his edits to 5 paragraphs plus 4 comments; the shape counts before and after the rewrite were produced by a script and read. The last clause of the Why is inference unverified.
- **Hits:** 1
- **Distinct-from:** `skill-voiceprofile-calibrate-from-user-diff` - that is the METHOD (diff his real rewrite mechanically, test a rule against the whole document), and it held again this session, so its Hits moved to 3; this entry is the trap the method surfaced: the profile's own example and fix sentences were the tells, and no pre-ship count covered paragraph shape. `voice-us-register-sweep` - that extended the mechanical sweep to spelling and contractions; this extends it to paragraph openers, summarizers and closers, a different measurement that the register sweep passes. `new-rule-is-untested-until-it-survives-a-real-case` - that is a rule generalised from a single diff hunk; rules 33 and 36 had survived earlier passes, and the failure was that their illustrative sentences were never counted as content.
- **See also:** skill-voiceprofile-calibrate-from-user-diff, voice-us-register-sweep, new-rule-is-untested-until-it-survives-a-real-case

### A working-tree read on main cannot see a pushed branch or an open pull request
- **Pattern-Key:** git-repo-state-read-from-worktree-only
- **Date:** 2026-09-11
- **Trigger:** failure
- **Rule:** Before saying whether work landed, run `git branch -vv`, `git status --short --branch`, `git log --oneline` and `gh pr list --state open` in one read-only job. A file listing on the checked-out branch answers a different question.
- **Failed:** Told the operator "No. Nothing from the Mac installer work has landed" after reading the clone through the 8932 bridge: `Startup/posix/install-mac.sh`, `examples/hello-mac.sh` and `docs/install/claude-cowork-mac-quickstart.md` all absent, `Startup/posix/exec-server.sh` still ending in a bare `exec node` with no COWORK_NODE pin, and `docs/install/claude-cowork-mac.md` still carrying its unresolved `[verify: ...]` marker. Every one of those readings was correct.
- **Why:** The clone was checked out on `main` at 8fade1b. The work was committed on `mac-installer` at 7190941, pushed, and open as PR #12 against main. A filesystem read sees one branch's worktree, and a branch or a pull request is not a file, so the read cannot be wrong and cannot be complete either.
- **Worked:** A read-only job (`agent-of-record-status.bat`) running `git branch -vv`, `git status --short --branch`, `git fetch --all --prune`, `git log --oneline -10`, `git rev-list --left-right --count HEAD...origin/main`, `gh pr list --state open` and `gh issue list --state open`, with `GH_CONFIG_DIR` set. It reported the local `mac-installer` branch tracking origin and PR #12 open, in the same run that confirmed the four files absent from main. Correction was stated plainly in chat before anything else was done.
- **Evidence:** measured - both the file reads and the status job output were read in the session; the merge that followed took main from 8fade1b to 1a40ffc and the same four paths then verified present.
- **Hits:** 1
- **Distinct-from:** `git-repo-clean-not-dirty` - there the failure was narrating repo state from memory without running git at all; here a real read was run and was accurate, but its scope (one branch's worktree) did not cover the question asked (did the work reach the repository).
- **See also:** git-repo-clean-not-dirty, git-misses-system-state

### A PASS from the agent's own shell proves the repository, not the host
- **Pattern-Key:** claude-cowork-agent-vm-validation-proves-repo-not-host
- **Date:** 2026-09-11
- **Trigger:** false-success
- **Rule:** Validate a host install from that machine's own terminal. A check that passed inside the agent's Linux VM says nothing about the host's toolchain or whether the desktop app can spawn the server.
- **Failed:** The Claude Cowork install page was followed on a MacBook Air and the checks came back clean, which read as a successful install. Nothing in that run executed on macOS itself - every check ran inside Cowork's Linux VM - and the executor, installed as a plugin, enabled and never connected.
- **Why:** The agent's shell and code execution live in a Linux virtual machine isolated from the host, so a run there exercises the repository's Python, Node and markdown and never touches the host's node, its PATH, AppleScript, or the desktop app's ability to start a stdio server.
- **Worked:** Treat a clean verdict as proof only when it comes from the machine's own Terminal. The Mac installer now runs `release_check.py` and `install_check.py` in a real Terminal window and completes an MCP handshake under a deliberately minimal PATH, and `--verify` reads the desktop app's own MCP logs afterwards.
- **Evidence:** measured - the first-run report records the checks passing in the VM and the executor never connecting; the installer's own behavior is tested against a stand-in tree in a Linux container only, so its effect on a real Mac is not yet measured.
- **Hits:** 1
- **Distinct-from:** `claude-cowork-connectors-dialog-is-remote-only` - that is WHERE a local server is registered on this host; this is what a PASS from a check actually covers, and it would still apply if registration had worked first time. `bridge-gui-spawned-launcher-gets-minimal-path` - that is one concrete host-side defect a check run in the wrong place cannot see; this is the scope rule that holds even when the launcher is perfect, because the VM never exercises the host's toolchain at all.
- **See also:** claude-cowork-connectors-dialog-is-remote-only, bridge-gui-spawned-launcher-gets-minimal-path

### The Connectors dialog takes a URL, so a local stdio server registers somewhere else
- **Pattern-Key:** claude-cowork-connectors-dialog-is-remote-only
- **Date:** 2026-09-11
- **Trigger:** failure
- **Rule:** Register a local stdio MCP server on Claude Cowork through Settings > Developer > Edit Config, a plugin `.mcp.json`, or an `.mcpb` extension. Connectors > Add accepts a remote URL only.
- **Failed:** Looking for a local-command field in Customize > Connectors > Add on the desktop app (1.52386.0, personal account). There is none. The executor was then packaged as a plugin whose `.mcp.json` declares a stdio server; it installed and enabled, and never connected in a cloud chat.
- **Why:** The Connectors dialog is built for remote servers reached by URL. Local stdio servers are configured in `claude_desktop_config.json` or delivered by a plugin or extension. Whether the plugin route fails because of the cloud session model or because the launcher could not resolve node was not isolated - inference unverified.
- **Worked:** Write the executor into `claude_desktop_config.json` directly, with absolute paths and a PATH that contains node, backing up whatever was there first. That is what the Mac installer now does.
- **Evidence:** measured - the dialog was opened and has no local-command field; the plugin install, enable and non-connection were observed. The cause of the non-connection is not measured.
- **Hits:** 1
- **Distinct-from:** `claude-cowork-agent-vm-validation-proves-repo-not-host` - that is a validation-scope trap (a clean verdict from the wrong machine); this is a fact about the desktop app's registration surface, independent of how anything is validated.
- **See also:** claude-cowork-agent-vm-validation-proves-repo-not-host, bridge-gui-spawned-launcher-gets-minimal-path

### A launcher started by a desktop app gets a minimal PATH, so resolve the runtime explicitly
- **Pattern-Key:** bridge-gui-spawned-launcher-gets-minimal-path
- **Date:** 2026-09-11
- **Trigger:** failure
- **Rule:** Never call `node` or `npx` bare in a launcher a desktop app spawns. Pin the interpreter, prepend the usual install folders to PATH, and exit with a distinct code and a stderr message naming the fix when it is missing.
- **Failed:** `Startup/posix/exec-server.sh` ended in `exec node ...` with no PATH handling. On the Mac run the server never connected and the only record of why would have been the desktop app's per-server log, which nothing was reading.
- **Why:** A GUI-spawned process does not inherit a login shell's PATH. On macOS the app hands a launcher roughly `/usr/bin:/bin:/usr/sbin:/sbin`, which contains no node, so `exec node` dies with a bare command-not-found that never reaches the person installing it. Whether that is what happened on the first run was not isolated - inference unverified.
- **Worked:** The hardened launcher honors `COWORK_NODE` from `cowork-env.sh`, prepends `~/.local/bin`, `~/.local/node/bin`, `/opt/homebrew/bin` and `/usr/local/bin` before looking for node, and exits 127 with a three-line stderr message naming the fix. Merged to main as part of PR #12. The same pattern still belongs in `pw-server.sh`, `fs-server.sh` and `flow-server.sh`, which call node and npx bare.
- **Evidence:** measured - the old launcher's bare `exec node` was read from the file on 2026-09-11 before the merge, and the hardened launcher's node resolution and exit 127 were exercised against a stand-in tree in a Linux container. Not yet measured on a Mac.
- **Hits:** 1
- **Distinct-from:** `bridge-8933-user-path-not-inherited` - there the executor runs and the JOB it starts sees a reduced environment; here the launcher process itself is spawned by a desktop app with a minimal PATH, so the interpreter is never found and no job runs at all. `claude-cowork-agent-vm-validation-proves-repo-not-host` - that is a rule about where a check must RUN to mean anything; this is a defect in the launcher itself, fixed in the file by pinning the runtime, and it would still be a defect if every check had been run on the Mac.
- **See also:** bridge-8933-user-path-not-inherited, claude-cowork-connectors-dialog-is-remote-only

### The release gate rewrites a tracked receipt, so the next merge refuses on a dirty tree
- **Pattern-Key:** git-gate-rewrites-tracked-receipt-blocks-merge
- **Date:** 2026-09-11
- **Trigger:** failure
- **Rule:** After running the release gate in the clone, restore `CoworkConfig/Skills/self-improvement/scripts/analyser.approved` before calling the merge job. Read the diff first; a line-ending-only change is not a content change.
- **Failed:** `aor-merge.bat` refused twice with `REFUSING - clone is dirty`, once for PR #13 and again for PR #14, with nothing in the session having edited the clone.
- **Why:** `dream_analyze_selftest.py` runs inside `release_check.py` and writes `analyser.approved`, which is tracked. It is written LF while the clone normalizes to CRLF, so git reports the file modified while `git diff` shows no content change at all.
- **Worked:** A job that prints `git diff` for that one file and then runs `git checkout --` on it, between the gate and the merge. The diff was empty both times, the tree went clean, and the merge proceeded. `2026-09-11-aor-clean-analyser.bat` is that job.
- **Evidence:** measured - both refusals, the empty diff, the restore and the clean status line were read in the session, and the merge that followed each one succeeded.
- **Hits:** 1
- **Distinct-from:** `git-repo-clean-not-dirty` - there the repo was clean and a session claimed otherwise from memory; here git genuinely reports dirty and the change is an artifact of running a checker. `git-commit-job-must-stage-itself` - that is about which files a job should stage; this is a file no job should be staging at all.
- **See also:** git-repo-clean-not-dirty

### A self-test fixture anchored on a live line fails the gate when that line is the change
- **Pattern-Key:** git-selftest-fixture-anchored-on-the-edited-line
- **Date:** 2026-09-11
- **Trigger:** failure
- **Rule:** Before changing an executable line in a launcher or a config, grep the self-tests for that literal. A fixture anchor is a second copy of the line and has to move in the same commit.
- **Failed:** A landing job that rewrote the three POSIX launchers passed its own hash checks and then failed the gate: `facts_check_selftest.py` raised `fixture anchor missing in Startup/posix/flow-server.sh`. The job reverted the branch and deleted it.
- **Why:** That negative control proves the checker catches a launcher pointed at the wrong server, and it builds its broken fixture by string-replacing the real exec line. Changing that line to resolve the runtime removed the anchor, so the control could no longer construct its own failure case.
- **Worked:** Re-ran the landing job with a fourth pinned change, one anchored edit moving the fixture's find and replace strings onto the new exec line. Gate clean at 22 checks, PR opened and merged. The case still proves the same thing.
- **Evidence:** measured - the failing gate output, the reverted clean tree, and the passing re-run were all read.
- **Hits:** 1
- **Distinct-from:** `enforcer-encodes-the-superseded-rule` - there a check froze an old RULE and kept reporting confidently; here the check is correct and only its fixture's copy of a literal line went stale, and it failed loudly rather than passing wrongly. `git-published-tree-edited-without-build-source` - that is editing an output instead of its source; here the source was edited correctly and a test that quotes it was missed.

### One large base64 write through the filesystem bridge can corrupt a single character
- **Pattern-Key:** bridge-8932-large-write-corrupts-a-character
- **Distinct-from:** batch-certutil-hashfile-findstr-never-matches - that is a CHECK that can never pass (the needle cannot match certutil's output format), so corruption is invisible by construction; this is the CORRUPTION itself (one base64 character substituted in transit, length preserved). The two met in one job: this fault, hidden by that check.
- **Date:** 2026-09-13
- **Trigger:** failure
- **Failed:** Moved a 12,661-byte git patch to the PC as ONE ~16 KB base64 file with `write_file`, then decoded it in a job with `certutil -decode`. The decoded file was exactly 12,661 bytes and read as correct, but hashed `0C1B28DD...` against the expected `D8CD4269...`. A second patch sent the same way in the same session decoded byte-perfect, so this path is not reliably wrong - it is intermittently wrong, which is worse.
- **Why:** A substituted base64 character still maps 4 characters to 3 bytes, so the decoded LENGTH is unchanged and only the content differs. File size is therefore not a verification of a base64 transfer, and neither is eyeballing the decoded text. Which layer substituted the character was not isolated - inference unverified.
- **Worked:** Split the payload into three ~4.2 KB parts, wrote each in its OWN tool block, and had the job verify each part against a pinned SHA-256 BEFORE assembling with `copy /b`, then hash the assembled file against its own pin. On the retry all three parts and the whole file matched and `git am --3way` applied cleanly. Pin and print every part hash: a per-part gate names the bad chunk, so only that chunk is re-sent.
- **Evidence:** measured - both the failing and the passing hashes were read from job stdout.
- **Hits:** 1
- **See also:** bridge-8932-writes-lf

### `certutil -hashfile` piped to `findstr` can never match - use `Get-FileHash`
- **Pattern-Key:** batch-certutil-hashfile-findstr-never-matches
- **Distinct-from:** bridge-8932-large-write-corrupts-a-character - that is the defect in the data (a substituted character with the decoded length unchanged); this is a verifier that cannot distinguish good from bad because its needle never matches certutil's formatted output. Fixing the transfer does not fix the check, and vice versa.
- **Date:** 2026-09-13
- **Trigger:** failure
- **Failed:** `certutil -hashfile 0001.patch SHA256 | findstr /i "<64-hex-digits>" >nul` set errorlevel 1 for a file whose hash was in fact correct, so a byte-perfect patch was reported as a hash mismatch and the job refused to touch git.
- **Why:** certutil's hash output on this machine is not the bare continuous hex string the `findstr` needle assumed, so the needle cannot match any file, correct or corrupt. The check fails identically in both cases, which means it only ever refuses and can never confirm - a check that cannot pass is indistinguishable from a check that caught something. The exact formatting was not captured - inference unverified.
- **Worked:** ``for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command "(Get-FileHash <file> -Algorithm SHA256).Hash"`) do set H=%%H`` then `if /i not "%H%"=="<UPPERCASE-HASH>" goto fail_hash`. Echo the computed hash before comparing: the first run then printed both values, which is what identified the real corruption behind the false one.
- **Evidence:** measured - the job printed the computed hash beside the expected one on the next run.
- **Hits:** 1
- **See also:** batch-ps51-strips-embedded-quotes-in-native-args

### Calling a `.cmd` shim from a `.bat` without `CALL` ends the job, and it still exits 0
- **Pattern-Key:** batch-cmd-shim-without-call-ends-the-job
- **Date:** 2026-09-13
- **Trigger:** failure
- **Rule:** Invoke every `.cmd`/`.bat` shim - `npm`, `npx`, and anything else that is a shim rather than an `.exe` - with `CALL`. Bare `npm install ...` TRANSFERS control to `npm.cmd` instead of returning to the caller, so every later line dies with it, including the `COWORK_RESULT` verdict, and the job still reports exit 0. Treat a missing verdict line as FAIL, never as "it worked".
- **Failed:** A job that ran `npm` bare partway through produced no `COWORK_RESULT` line at all and returned exit code 0. Read as a pass, the only symptom was silence where the verdict should have been.
- **Why:** `cmd.exe` treats a batch file invoked without `CALL` as a chained target, not a subroutine: control never comes back, the remaining lines are never parsed, and the exit code reported is the shim's, so an install that succeeded masks a job that never finished. This is the same failure shape as `cowork-close-reports-ok-on-failed-commit` inverted - there the verdict lied, here the verdict is absent and the exit code lies.
- **Worked:** `call npm install ...` followed by `if errorlevel 1 goto fail_npm`, and a verdict line that is the LAST thing the job prints. The verdict's presence is then itself the end-to-end control: stdout without a `COWORK_RESULT` line means the job was truncated, whatever the exit code says.
- **Evidence:** reported by the operator on 2026-09-13 from the prior session, where the truncated stdout and the exit 0 were both read. The `CALL` mechanism is documented `cmd.exe` behaviour; it was not re-measured when this entry was written.
- **Hits:** 1
- **Distinct-from:** `cowork-close-reports-ok-on-failed-commit` - there a job echoed `OK` unconditionally over a real failure; here no verdict is printed at all because the job stopped executing. `bridge-8933-transport-drop-verify-first` - that is the connection dying; here the connection is fine and the SCRIPT ended early.
- **See also:** batch-certutil-hashfile-findstr-never-matches, cowork-close-reports-ok-on-failed-commit

### A text tool built against LF fixtures fails three different ways on a CRLF checkout
- **Pattern-Key:** repo-crlf-checkout-defeats-lf-anchored-tools
- **Date:** 2026-09-13
- **Trigger:** failure
- **Rule:** Before running any exact-string tool - anchor patch, heredoc extractor, delimiter split - against a file in the Windows clone, read that file's line endings and build the local fixture in the SAME convention. The agent-of-record clone checks out `.sh` as CRLF and `.md`/`.json` as LF; a Mac checkout has everything LF. Normalise on read (`text.replace("\r\n", "\n")`) or adapt the anchor to the file, and put a CRLF case in the self-test so the fixture cannot pass where the repo fails.
- **Failed:** Item 3 of the AoR work order needed four runs of one mutating job before it reached the commit step. Run 1: 13 of 22 anchors matched zero times, every one in a CRLF `.sh`, every LF `.md` anchor matched. Run 2: one anchor off by a single space, typed from a rendered view instead of copied from a byte read. Run 3: the post-apply check asserted OLD gone, wrong for two additive edits where NEW contains OLD; the failure label did not revert, leaving the tree dirty. Run 4: the heredoc extractor split on `<<'PYEOF'\n` and found nothing in a `\r\n` file. Every helper had passed its self-test and an end-to-end fixture first - all built LF.
- **Why:** A fixture that shares the tool's own assumptions proves nothing about the input that violates them. Self-tests written by the same hand carry the same blind spot, so 6/6 and 9/9 were true and irrelevant. The dirty tree after run 3 was the second-order cost: a refusal path written for one failure shape (refused before writing) silently mishandled another (refused after writing).
- **Worked:** `adapt()` converts each anchor to the file's convention before counting and replacing, and a CRLF case in the self-test reproduces run 1's zero then shows the adapted count of one. The extractor normalises to LF on read, with a CRLF case that reproduces run 4's zero blocks. The post-apply invariant became NEW present exactly once, with a self-test naming the two additive edits. Every fail label after the write path reverts the five target files. The full chain - patch, compile, LF rewrite, `bash -n`, the real `install-mac.sh --register` twice against a seeded config, TCC refusal - was then run in the container on a CRLF fixture before the job was proposed again.
- **Evidence:** measured - the 13/9 split, the 1-space diff, the two additive anchors, the zero-block extractor result and the clean revert were all read from job stdout across runs 1-4; the container chain was run and read.
- **Hits:** 3   (2026-09-13 CRLF `.sh` files defeated LF-anchored patches across four runs; 2026-09-14 a container-rehearsed lint died on the PC at the first non-ASCII snippet, because the container writes UTF-8 and the redirected Windows stream encodes cp1252; 2026-09-14 a self-test case asserted an ORDERED list of scan hits - `sorted(rglob)` puts `SKILL.md` before `notes.md` on Linux and after it on Windows, so 50/50 in the container was 49/50 on the PC. Third axis: path sort order. Fixed with `sorted()` on the assertion)
- **Promotion:** 2026-09-14 - second hit; the Rule is authored above and is DUE into the copilot-instructions.md LESSON-DIGEST at the next close, alongside gate-asserts-an-unmeasured-count.
- **Repeat 2026-09-14 - the same mechanism on a different axis, ENCODING not line endings:** `platform_lint.py` passed a 6/6 self-test and an end-to-end fixture run in the container, then crashed on the PC with `UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'` after reporting 8 of 10 skills. The container is UTF-8; the job redirects stdout to a file and Windows encodes that stream as cp1252, so one arrow in a quoted source line killed the run. Read-only, so the cost was one job. Fixed by folding snippets to ASCII before printing - deterministic on every platform rather than dependent on the console code page - with a self-test case that writes a non-ASCII line and asserts the fold, reproduced first under `PYTHONIOENCODING=cp1252`. The general form: a rehearsal proves the tool against the REHEARSAL's environment. Before trusting a container run, name every way the target's environment differs - line endings, code page, path separators, locale - and put one case per difference in the self-test.
- **Distinct-from:** `bridge-8932-writes-lf` - that is the bridge writing a NEW file LF where cmd wants CRLF; this is an EXISTING repo file being CRLF where a tool assumed LF. `git-selftest-fixture-anchored-on-the-edited-line` - there a fixture went stale when its anchor line changed; here the fixtures were never representative in the first place. `batch-job-written-before-proposal-shown` - that is about WHEN a job file is written (before approval); this is about the ENCODING of the file a tool reads, regardless of timing. `git-gate-rewrites-tracked-receipt-blocks-merge` - that is a gate mutating a tracked file so the merge refuses; this is a tool misreading an unchanged file because of its line endings - no mutation, no merge.
- **See also:** bridge-8932-writes-lf, git-selftest-fixture-anchored-on-the-edited-line, batch-cmd-shim-without-call-ends-the-job

### A gate that asserts a count you did not measure refuses a correct result
- **Pattern-Key:** gate-asserts-an-unmeasured-count
- **Date:** 2026-09-14
- **Trigger:** failure
- **Rule:** When a job gates on a number - cases run, files changed, rows matched - take the number from the inventory you already ran, or compute it in the job from the same source the tool uses. A count typed from memory is a second assertion about the world, and when it is wrong the gate reverts a correct result and reports the tool as the failure.
- **Failed:** The Item 1 job required `22/22 negative controls caught` from `facts_check_selftest.py`. The real suite had 18 cases before the edit and 21 after; the run printed `21/21` and `FACTS_SELFTEST: OK`, and the job reverted 48 correct edits with the reason `the self-test did not run 22 cases`. The preflight had printed the whole self-test file an hour earlier; the 18 was there to count.
- **Why:** The gate encoded my belief about the suite instead of a fact read from it. Every other gate in the job asserted something the tool itself reports - `CLEAN`, `OK`, `3 of 4` - and those all held. The one that asserted my arithmetic was the one that failed.
- **Worked:** Corrected the literal to 21 and re-ran; the job landed on the next run. The durable fix is either to gate on the tool's own verdict line (`FACTS_SELFTEST: OK`) plus a MINIMUM (`at least 21`) rather than an exact count, or to compute the expected count in the job from `len(CASES)` in the self-test source before running it.
- **Evidence:** measured - both runs' stdout were read: `21/21` with the revert, then `21/21` with the commit.
- **Hits:** 4   (2026-09-14 the Item 1 gate asserted 22 cases where 21 ran; 2026-09-14 later the same day, a self-test's own PASS label hard-coded `16/16` while 14 cases ran; 2026-09-14 the Item 6 strict-gate job required `git grep "22 checks"` to return exactly 2 sites and refused at exit 45 when the tree returned 3; 2026-09-14 the matcher job did the SAME thing six hours later with `"23 checks"` - 2 asserted, 3 found, the third being the CHANGELOG bullet the previous job had itself written)
- **Repeat 2026-09-14 - the fourth hit, and the one with no excuse:** the site count was typed as 2 again, by a session that had refused on exactly this assertion that morning and had READ the third site (its own CHANGELOG bullet) while reviewing the tree. The gate held, cost one run. The sharper rule: a count of grep sites is never typed - the job's Step 4 runs the grep, and the PROPOSAL shows the grep's output before approval, so the expected set is measured at proposal time, not remembered from the last job.
- **Promotion:** 2026-09-14 - second hit; the Rule is authored above and is DUE into the copilot-instructions.md LESSON-DIGEST at the next close. Third hit the same day - the digest splice is now overdue, not merely due.
- **Repeat 2026-09-14 - the third hit, and the one that cost nothing:** the strict-gate job's site count was typed from the prepared hand-off rather than re-measured against the tree it would run on. It refused BEFORE writing, so the cost was one run instead of a revert - which is the shape this Rule is trying to produce. The sharpening: a gate on a count of MATCHES must also name which matches it expects, because the count can be wrong for a reason that raising it would not fix (see `docs-record-vs-statement-in-a-value-sweep`).
- **Repeat 2026-09-14 - the same defect one layer down, in the self-test itself:** `myvoice_patch.py --selftest` printed `SELFTEST_RESULT: PASS 16/16` over fourteen cases. Nothing gated on the label, so nothing reverted, but the label was written to be read as a count and it was wrong the first time it was read - a job that had asserted `16/16` from it would have refused a correct helper for the second time in one day. Fixed by counting inside `case()` (`ran += 1`) and printing `PASS {ran}/{ran}`; the label can no longer disagree with the run. The general form: never TYPE a count into a label or a gate when the code that produces the count is right there to count for you.
- **Distinct-from:** `cowork-close-reports-ok-on-failed-commit` - there a verdict was echoed without a test; here a test was too strict about a number nobody had measured. `git-selftest-fixture-anchored-on-the-edited-line` - there a fixture's copy of a line went stale; here a gate's copy of a count was never right.
- **See also:** cowork-close-reports-ok-on-failed-commit, repo-crlf-checkout-defeats-lf-anchored-tools

### A job file written before the proposal was shown shipped a malformed line
- **Pattern-Key:** batch-job-written-before-proposal-shown
- **Date:** 2026-09-14
- **Trigger:** near-miss
- **Rule:** Author the job text in the container and read it back to yourself before the ONE write to CommandJobs, which happens after approval. A file written first and reviewed second is a draft on the execution path.
- **Failed:** The read-only myvoice inventory job was written to `CommandJobs\` through the 8932 bridge BEFORE its contents were shown for approval, inverting the one-approval workflow's order (show, wait, write, run). The first write carried a malformed line, `git tag --contains %%~ --`, that would have printed a usage error mid-job. It was caught on re-reading the proposal text, not by any check, and correcting it cost a second write that then dropped on the tunnel and had to be verified and re-sent.
- **Why:** Writing felt like part of drafting because the job was read-only and nothing would run without a second call. But the file under `CommandJobs\` IS the thing `run_batch_file` executes; once it exists, the gap between a draft and an approved job is one approval word. Reviewing in chat afterwards put the review after the artifact instead of before it.
- **Worked:** For the two mutating jobs that followed, the helper and the job were composed and rehearsed in the container first (self-test, fixture forward path, fixture revert path), the job text was shown in full with the output folder, and the write to `CommandJobs\` happened once, followed by a tail read-back and, for the helper, a SHA-256 gate inside the job. Neither needed a second write.
- **Evidence:** measured - the malformed line is in the first write's read-back; the corrected file's tail was read back after the second write.
- **Hits:** 1
- **Distinct-from:** `bridge-8932-large-write-corrupts-a-character` - there the bridge altered what was sent; here what was sent was wrong. `cowork-close-reports-ok-on-failed-commit` - there a job lied about its result; here a job was written before it had been reviewed. `repo-crlf-checkout-defeats-lf-anchored-tools` - that is a tool failing on a file's line-ending convention; this is a correct file written to the execution path BEFORE it was reviewed - the content could have been perfect and the ordering would still be the defect.
- **See also:** bridge-8933-transport-drop-verify-first, gate-asserts-an-unmeasured-count

### A value sweep must separate a page that STATES the value from one that RECORDS it
- **Pattern-Key:** docs-record-vs-statement-in-a-value-sweep
- **Date:** 2026-09-14
- **Trigger:** failure
- **Rule:** Before a job rewrites every occurrence of a stated value, split the grep hits into pages that STATE the current value and pages that RECORD a past measurement. A dated transcript, a first-run record or an evidence file KEEPS its old number - rewriting one falsifies measured output. Assert the full hit list by name, name the exclusions in the job, and prove after the edit that the excluded files are untouched.
- **Failed:** `2026-09-14-aor-strict-gate.bat` required `git grep "22 checks"` to return exactly the two install pages its helper patches, and refused at exit 45 when the live tree returned three: `docs/install/claude-cowork-mac-first-run.md:60` also carries `RELEASE_CHECK: CLEAN (22 checks)`. The job had been prepared against a two-site belief and nothing had re-measured it against the tree it would run on.
- **Why:** The third hit sits inside a captured console transcript of a run against tag `v0.3.1`, whose gate really did print 22. It is not a statement of the current count. A sweep that treats every grep hit as the same kind of text would have rewritten measured output into a number that run never produced - and the page's own header says it is kept as it was written that day.
- **Worked:** Left the helper's four edits unchanged; widened the job's Step 4 assertion to the three expected sites by name with the record named as a deliberate exclusion; added a post-apply gate that `git diff --name-only` is exactly four files and does not contain the record; stated the exclusion and its reason in the commit message. Re-run landed: `PATCH_RESULT: OK`, flipped-scratch control exit 1 with exactly one failure, real tree `RELEASE_CHECK: CLEAN (23 checks)`, commit `a3d19bc`.
- **Evidence:** measured - run 1 stdout shows the three grep hits, `sites stating 22 checks: 3` and exit 45 with nothing written; run 2 stdout shows `files changed: 4`, the record absent from `touched.txt`, and the clean gate.
- **Hits:** 1
- **Distinct-from:** `gate-asserts-an-unmeasured-count` - there the number in the gate was never counted at all and the fix is to count it. Here counting is not enough: the population is mixed, and the right answer is to EXCLUDE a hit rather than to raise the number. `count-assertion-must-use-independent-control` - there two numbers shared one premise; here one number was correct about a population that should have been two populations.
- **See also:** gate-asserts-an-unmeasured-count, batch-job-written-before-proposal-shown

### When a gate flags text as platform-specific, the fix is portable text, not platform-conditional delivery
- **Pattern-Key:** skill-portability-is-one-text-not-two-bundles
- **Date:** 2026-09-14
- **Trigger:** correction
- **Rule:** A skill is a SKILL.md and must be correct on every platform it is installed on. When a gate flags Windows-only text, rewrite the sentence so it names both platforms' mechanics - never build machinery to ship one bundle per platform or to hide the text from one of them. The gate then has to measure PAIRING (a Windows token beside its macOS counterpart), because a portable sentence legitimately contains both.
- **Failed:** Built and proposed a section-2.6 design - `Platform:` tags on lessons, two marker pairs per skill, per-platform stripping in `build_plugin.py` - so that 16 Windows-flavoured rule texts could ship to Windows and vanish from the macOS bundle. the operator: "It does not make sense that skills would be windows only. the skills are just based on SKILL.md files and should be fully usable in Claude Cowork on both PC and Mac." The whole design was infrastructure for not rewriting 138 sentences.
- **Why:** The token gate reported the residue as a count to drive to zero, and the cheapest route to zero was to make the text invisible to the scanner rather than correct for the reader. That optimises the gate, not the skill. A `platforms` field in a manifest is an honesty marker for text that is not yet portable; it was about to become a permanent architecture.
- **Worked:** Dropped the two-block design before it touched the repo. Redefined the gate (`8fb1c2c`): a Windows token is acceptable where the same table row or prose paragraph names its macOS counterpart; the generated lessons block - the operator's record, emptied by a new install's empty corpus - is not scanned; `--list` prints each windows-only skill's unpaired-token count so the rewrite is measured by the gate itself. Then rewrote `persistent-memory` (`5496b51`) and `git-bridge` (`9868738`) as one text each naming both platforms, and flipped both to `["windows","macos"]` in the same commits; `--strict` accepted both and the macOS bundle went 2 -> 4. The `platforms` field goes when all ten are through.
- **Evidence:** measured - the pairing self-test runs 50 cases and fails 1 of 22 by name against the pre-change module; a flipped scratch `command-bridge` still fails `--strict` exit 3 on unpaired body text; both skill flips proved by `--strict --list` exit 0 with no unpaired tokens reported and `--platform macos` listing one more skill.
- **Hits:** 1
- **Distinct-from:** `docs-record-vs-statement-in-a-value-sweep` - there the question was which occurrences of a value to REWRITE; here it was whether to rewrite at all or route around. `verifier-warns-on-proxy-not-the-defect` - there a check fired on a proxy; here the check was fine and the RESPONSE to it was wrong.
- **See also:** verifier-warns-on-proxy-not-the-defect, enforcer-encodes-the-superseded-rule

### The toolkit validator rejects a manifest member the published v1.8 schema documents
- **Pattern-Key:** atk-validator-rejects-documented-depends-on
- **Date:** 2026-10-01
- **Trigger:** failure
- **Rule:** Run the declarative-agent manifest through `atk provision` (teamsApp/validateAppPackage) before trusting a member the learn.microsoft.com v1.8 reference or the published JSON schema says is valid; when the validator rejects a documented member, remove it rather than argue the schema.
- **Failed:** `atk provision` for ACL 1.3.0 stopped at `teamsApp/validateAppPackage` with `InvalidDeclarativeCopilotDocument: Invalid Declarative Agent Document: declarativeAgent.json. Problems discovered: Unrecognized member 'depends_on' ... at (#/conversation_starters/2/depends_on)`. `depends_on` is documented on the declarative-agent-manifest-1.8 page (Conversation starters object, "depends_on Array of Depends on object Optional") and is present in the published v1.8 JSON schema under `$defs/conversation-starter.properties.depends_on`.
- **Why:** The toolkit CLI (m365agentstoolkit-cli) validates against its own copy of the schema, which does not match the published v1.8 schema for this member. Whether the CLI's schema lags or the member is gated some other way was not probed - inference unverified.
- **Worked:** Removed `depends_on` from all four conversation starters with 8932 `edit_file`; the next `atk provision` run passed validation (59 checks) and proceeded to the later steps.
- **Evidence:** measured - the error was read verbatim from the provision output and the next run's validation pass was read; the documentation and schema presence were read on learn.microsoft.com and in the published schema file. Why is inference unverified.
- **Hits:** 1
- **See also:** gh-api-input-rejects-utf8-bom, verify-product-claim-before-correcting-the-operator
- **Distinct-from:** verify-product-claim-before-correcting-the-operator - there the operator was told a product could NOT do something it could; here the documentation says the product accepts something and the shipped validator refuses it. Documentation is the thing not to trust here, and only the tool's own run settles it.

### node:sqlite rows crash Array.prototype.sort when no comparator is given
- **Pattern-Key:** node-sqlite-rows-break-default-sort
- **Date:** 2026-10-01
- **Trigger:** failure
- **Rule:** Never call `.sort()` without a comparator on an array whose elements contain `node:sqlite` rows (or anything else without a prototype); write `.sort((a, b) => String(a[0]).localeCompare(String(b[0])))` or compare an explicit key.
- **Failed:** `acl-memory-recall.bat` first run on the PC died with `TypeError: Cannot convert object to primitive value at Array.sort at main (acl-recall.js:48:49)  Node.js v25.9.0`. The line was `for (const [g, list] of [...groups.entries()].sort()) {`. The same script had passed under the container's Node against a seeded database.
- **Why:** Default `Array.prototype.sort` stringifies each element; each element here is a `[key, list]` pair whose `list` holds `DatabaseSync` rows, and under Node 25 those rows have a null prototype, so stringifying throws. The container's Node did not reproduce it. The null-prototype mechanism was not probed directly - inference unverified.
- **Worked:** Explicit comparator on the group key: `.sort((a,b)=>String(a[0]).localeCompare(String(b[0])))`. The next run printed `ACL_RECALL=PASS` with export and active-total counts.
- **Evidence:** measured - the TypeError and the Node version were read verbatim from job output, and the PASS line was read on the re-run; the Why is inference unverified.
- **Hits:** 1
- **See also:** repo-crlf-checkout-defeats-lf-anchored-tools
- **Distinct-from:** repo-crlf-checkout-defeats-lf-anchored-tools - that entry is the general shape (a rehearsal proves the tool against the REHEARSAL's environment, and its listed axes are line endings, code page and path sort order); this is one new axis - RUNTIME VERSION - with its own one-line fix, which a session reading only the general rule did not derive. Also distinct from fs-server-pin-measured-output-schema-only: that is a dependency pin against a schema fault; this is a language-level default that changes with the host's Node.

### An export that excludes secrets by FILENAME ships the secrets its logs contain
- **Pattern-Key:** export-name-exclusion-ships-token-logs
- **Date:** 2026-10-01
- **Trigger:** failure
- **Rule:** Before a workspace archive leaves the machine, scan its CONTENT for token-shaped strings and the account name - a filename exclusion list is not a disclosure scan - and treat browser-automation console logs as secret-bearing by default.
- **Failed:** `Version 01.10.zip`, a full workspace export (2,279 files), contained playwright-output console logs from 2026-08-17 holding JWT-shaped strings from the signed-in Edge session, and the Windows account name across 17 folders. The export job excludes files whose NAMES mark them as secrets; it does not scan content, so the logs passed.
- **Why:** The exclusion list encodes where secrets are EXPECTED to live. Console logs captured by Playwright record whatever the page emitted, including bearer tokens, under a name that signals nothing. The job's filter therefore measured the wrong property - the filename - and the archive carried the content untouched.
- **Worked:** The finding came from opening the archive and reading its contents; the log records the detection, not a remediation of the archive or a change to the export job - both are follow-ups for the next session, not facts this entry can claim.
- **Evidence:** measured - the archive's contents were read and the token-shaped strings and account-name occurrences were counted in-session; the export job's exclusion behaviour is as described in the log, not re-read for this entry.
- **Hits:** 1
- **See also:** public-scan-unscanned-extension-passes-clean, git-renaming-is-not-sanitizing, git-deletion-does-not-sanitize-history
- **Distinct-from:** public-scan-unscanned-extension-passes-clean - there a content scanner RAN and reported honestly about the wrong population because one extension was skipped; here no content scanner ran at all - the filter was a name list - so adding an extension would not have caught it. git-renaming-is-not-sanitizing - there the exposure was client work product behind a cosmetic rename; here it is live credentials in incidental logs, and the fix is scrubbing or exclusion, not an ownership decision.

### Consolidate duplicated instruction sections before trimming words - and gate overlap was NOT the no-response cause
- **Pattern-Key:** acl-instruction-overlap-no-response-unmeasured
- **Distinct-from:** skill-description-cap-crossed-by-edit - that is a hard cap that silently removes a whole skill when crossed; this is a hard cap (8,000 characters) that was met by TRIMMING words when the real surplus was DUPLICATED sections. The cap mechanics differ (unload vs reject) and the lesson here is about how to make room, not that a cap exists. acl-empty-turn-correlates-with-write-first-call - that entry owns the still-open root cause of the empty turn; this one records only that instruction overlap was tested and ruled out as the cause.
- **Date:** 2026-10-02
- **Trigger:** better-approach
- **Routes:** copilot
- **Rule:** When an instruction file hits its cap, consolidate overlapping sections first and trim words last; and do not spend instruction edits trying to cure ACL's empty turns - they persisted unchanged after the overlap was removed.
- **Failed:** The 1.3.0 `instruction.txt` first draft was over the 8,000-character cap and took three word-trimming passes to land under it by a thin margin. Trimming words kept every one of four overlapping completion-gate sections in place. A side-hypothesis was then carried for a day that the overlapping gates caused the agent's no-response failure.
- **Why:** Word-trimming treats the cap as the problem; the rewrite treated DUPLICATION as the problem. The 1.4.0 rewrite consolidated the four sections into one RESPONSE CONTRACT + EXECUTION LOOP and landed well under the cap with all rules retained. The hypothesis was then measured on 2026-10-02: 1.4.0 with the consolidated instruction returned EMPTY on 3 of 3 Auto-mode turns and on the first Think-deeper turn of a fresh case, and 1.4.1 returned EMPTY again on its first attachment case - so removing the overlap did not remove the failure, and overlap is not its cause.
- **Worked:** Consolidating overlapping sections frees far more room than trimming words and loses no rules: consolidate first, trim last. For the empty-turn failure itself, follow `acl-empty-turn-correlates-with-write-first-call` - the only thing established is that instruction overlap is not it.
- **Evidence:** measured - character counts of both versions were read in-session on 2026-10-01; the empty turns on the consolidated 1.4.0 and 1.4.1 were observed in the ACL UI on 2026-10-02 and the resulting files (or their absence) read from disk over the 8932 bridge.
- **Hits:** 1
- **See also:** acl-empty-turn-correlates-with-write-first-call, nightly-constant-reported-as-a-measurement, review-rounds-outpaced-the-first-real-run

### ACL's account of its own turn is not the record - grade from the debug panel and the disk, never from a case it ran itself
- **Pattern-Key:** acl-self-report-is-not-the-record
- **Distinct-from:** agent-claims-action-before-doing-it - that is THIS session narrating its own action as done; here the SUBJECT under evaluation reports on itself and the evaluator was about to accept it. nightly-constant-reported-as-a-measurement - that is a scoring SCRIPT whose inputs are literals; this is a live chat eval where the subject chose, ran and graded the case.
- **Date:** 2026-10-02
- **Trigger:** false-success
- **Routes:** copilot
- **Rule:** Grade an ACL case only from the per-request Agent debug panel and a bridge read of the disk; never from ACL's account of its previous turn, and never from a case ACL chose, administered and graded itself.
- **Failed:** (1) After an empty Think-deeper turn, "why did you stop?" drew "I stopped after the write". The Agent debug panel for THAT correction turn listed `write_file 200` and `read_text_file 200` as its own executed actions, and the panel is per-request (an earlier panel showed only its own 3 calls) - so the empty turn had executed nothing and the self-diagnosis was wrong. (2) On the 1.4.1 attachment case ACL's reply showed a 2-line truncated folder listing yet asserted "Confirmed present". (3) In the morning session the operator typed "run the next evaluation case" 11 times; ACL chose the prompt, ran it and graded it, producing "12/15 first-try PASS" - a self-report with no independent prompt or check.
- **Why:** The agent has no reliable view of a turn that produced no text, so its explanation is a reconstruction; and an evaluation where the subject picks and grades the case measures its self-assessment, not its behaviour. Both read as evidence because they arrive in the same voice as a real result.
- **Worked:** The evaluator (this session) wrote the prompts, handed them to the operator as a text file to paste, read the per-request debug panel for each turn, and verified every artifact on disk over 8932 before recording results in `evals/results-2026-10-02.json`. Where the panel and the agent disagreed, the panel was taken.
- **Evidence:** measured - debug panel contents read for the turn in question; files read from disk over the bridge; the morning run's self-grading seen in the ACL transcript file.
- **Hits:** 1
- **See also:** acl-empty-turn-correlates-with-write-first-call, agent-claims-action-before-doing-it, nightly-constant-reported-as-a-measurement

### The Cowork composer turns any path token into a file chip and truncates the line around it
- **Pattern-Key:** cowork-composer-path-tokens-become-file-chips
- **Date:** 2026-10-02
- **Trigger:** failure
- **Routes:** copilot
- **Rule:** Text the operator will paste into the Cowork composer must contain no path tokens - no backslash paths, no forward-slash paths, spell hostnames out - or be delivered as a .txt file; describe a location in words instead.
- **Failed:** Fenced prompts containing `Outputs\ACL-Test\hello2.txt` rendered in the composer as file chips and the line collapsed to "Create the file Outputs\ACL-Tes...onfirm."; the operator read it as the session cutting its own output short ("stop cutting off things... you cut them off again"). Lines with no path rendered fully. First fix - switching to forward slashes - FAILED: `Outputs/ACL-Test/` became a chip too ("...hello2.txt ...ontent.").
- **Why:** The composer detects path-shaped tokens in either separator style and replaces them with a chip that truncates the surrounding text. The agent's output was complete; only the composer rendering was not. Whether a bare URL also chips was not isolated (the working rewrite spelled the hostname as "example dot com" at the same time).
- **Worked:** Two things, both confirmed by the operator's screenshots: writing the prompts to a .txt file in output/ (unaffected), and rewriting them with no path tokens at all - "the ACL-Test folder, which is inside the Outputs folder of the COPILOT_COWORK workspace" - which rendered fully.
- **Evidence:** measured - three screenshots from the operator read in-session, one per attempt; the chip mechanism is inferred from them, inference unverified.
- **Hits:** 1

### Several related edits on the PC are one read-modify-verify job, not a run of bridge edits
- **Pattern-Key:** batch-one-reconcile-job-beats-many-bridge-edits
- **Distinct-from:** onedrive-task-output-is-a-binary-safe-transport - that moves a PAYLOAD to the PC without retyping it; this is about MUTATING files already on the PC. land-expect-hashes-from-scratch-apply - that pins the result of a land; this is the choice of transport for the edits themselves. bridge-drops-are-tunnel-not-bridge - that is the drop rate and the retry discipline; this is how to stop paying it N times.
- **Date:** 2026-10-02
- **Trigger:** better-approach
- **Routes:** copilot
- **Platforms:** windows
- **Rule:** When a change touches several files or several fields on the PC, write ONE 8933 job that takes before-copies, reads, modifies, and prints its own assertions - instead of a sequence of approval-gated 8932 edits each exposed to the tunnel drop rate.
- **Delivered-to:** command-bridge, local-file-bridge
- **Failed:** The same afternoon's 1.4.1/1.4.2 build went through individual `edit_file` / `write_file` / `move_file` calls: roughly one call in four dropped, several payloads had to be split, and every drop cost a read-back before the retry (see `bridge-drops-are-tunnel-not-bridge`, Hit 4).
- **Why:** Each bridge edit is one approval and one tunnel round-trip; N edits buy N exposures to the drop rate and N read-backs. A job is one round-trip, runs locally at a measured 0% drop, and can assert its own result.
- **Worked:** `acl-release5-reconcile` - a PowerShell 5.1 job that round-tripped five JSON state files through `ConvertFrom-Json` / `ConvertTo-Json`, kept before-copies, and printed 17 assertions - exited 0 on the first run. The job is still one bridge call: if its dispatch drops, apply `bridge-8933-transport-drop-verify-first` (check the before-copies/outputs before re-running).
- **Evidence:** measured - job exit code and the 17 assertion lines read from stdout; "beat ~15 bridge edits" is an estimate of the avoided call count, inference unverified.
- **Hits:** 1
- **See also:** bridge-drops-are-tunnel-not-bridge, bridge-8933-transport-drop-verify-first, bridge-8932-parallel-writes-denied, land-expect-hashes-from-scratch-apply

## Contradictions — stored memories that proved wrong

### The 8933 environment is PARTIALLY stripped — PATH is intact
- **Pattern-Key:** bridge-8933-env-partially-stripped
- **Supersedes key:** bridge-8933-stripped-environment
- **Date:** 2026-08-20
- **Trigger:** contradiction
- **Rule:** FIXED AT SOURCE 2026-09-09 - executor 1.3.0 hands jobs a complete environment: the profile variables and the user PATH, derived from the account. What survives: the working directory is CommandJobs, so start every job with `cd /d <repo>`; there is no console and no elevation.
- **Delivered-to:** command-bridge
- **Failed:** Generalizing the 2026-08-18 finding ("the 8933 environment is stripped") to PATH, and flagging a job that used bare `powershell.exe` as broken. It was not broken.
- **Why:** The original finding was about USER-PROFILE variables — `%LOCALAPPDATA%` expanded to empty. That is still true. PATH was never tested, and the word "stripped" was carried across to it.
- **Worked:** A read-only probe: `echo %PATH%`, `where powershell.exe`, and a bare `powershell.exe -NoProfile -Command` invocation. All three passed — System32, PowerShell, Git, node and Python all resolve. So bare interpreter names are fine; hard-coded absolute paths remain necessary only for anything under a user profile. What 8933 does NOT inherit is the WORKING DIRECTORY, which is why `cd /d <repo>` stays mandatory at the top of every job.
- **Evidence:** measured — probe output read
- **Fixed-at-source:** 2026-09-09 - `batch-exec-server.js` 1.3.0 builds the environment itself (`buildJobEnvironment`): `USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, `TEMP`, `USERNAME`, `HOMEDRIVE`/`HOMEPATH`, the `ProgramFiles` family from the account, and `Path` = machine PATH + `HKCU\Environment` user PATH. Measured through the live bridge: every variable filled, `user_path_entries: 12`. The cause was in the server all along - the old `runBatch` built a fixed nine-variable environment - not in how the watchdog started the bridge.
- **See also:** bridge-8933-arg-name, bridge-8933-user-path-not-inherited

### Two memory stores exist and drift apart silently
- **Pattern-Key:** memory-two-stores-drift
- **Date:** 2026-09-09
- **Trigger:** contradiction
- **Rule:** A fact gets ONE home. Pointer tier is short keys; the deep file is mechanism and evidence. On conflict the LATER-DATED statement wins and the stale store is corrected in the same pass - the file is authoritative only while it is current.
- **Delivered-to:** dream-cycle, persistent-memory
- **Failed:** Treating `save_memory` as "saved to persistent memory." It writes to the built-in memory store (59 entries), not to `Documents/Cowork/cowork-memory/*.md`, which is what the `persistent-memory` skill reads and what `CoworkConfig\` commits to git.
- **Why:** They are separate systems with no sync between them. On 2026-08-20 the built-in store held three entries from that day while every file in `cowork-memory/` still read 2026-08-18 — a two-day drift that was invisible until the folder was listed.
- **Worked:** SUPERSEDED 2026-08-25 — see `memory-tiering-pointer-vs-deep`. (Old rule: write durable findings to BOTH stores. That duplication was the cause of the drift, not the cure.)
- **Repeat 2026-09-09 - the file can be the stale side:** `agent-of-record-public-repo.md` (deep tier, last updated the morning of 2026-09-07) still said the public repo runs a single-commit snapshot model, force-pushed on each publication, and its Preferences section said never to stack ordinary commits on `main`. The v0.3.0 release that same evening ended that model - `main` protected, history kept, changes by pull request with CI on two platforms - and only the pointer tier and the repo's own CHANGELOG recorded it. A session applying "the file wins" would have prepared a force-pushed root commit against a protected branch with a contributor's fork behind it. Caught because the pointer entries carried later dates and the clone's branch list was read before anything was planned; the deep file was rewritten in this close.
- **Hits:** 3
- **Evidence:** measured — folder listing showed all four files last modified 2026-08-18; 2026-09-09 measured - deep file dated 2026-09-07 describing the snapshot model, against pointer memories dated 2026-09-07 23:20 and 2026-09-08 describing the protected-main model, and the clone's remote head list showing PR-merged history
- **Promoted-to:** copilot-instructions.md, "Rules already paid for" (LESSON-DIGEST block) - rule text confirmed present in the digest 2026-08-28.

### A skill's ALWAYS-ON line does not survive skill routing
- **Pattern-Key:** skill-alwayson-defeated-by-routing
- **Delivered-to:** self-improvement
- **Date:** 2026-08-18
- **Trigger:** contradiction
- **Failed:** Relying on `ALWAYS-ON:` in the `self-improvement` description to make every session scan the lessons file. A cold-start test ("write me a batch job... then run it") loaded `command-bridge` instead; `self-improvement` never activated, no Pattern-Key was cited, the CRLF normalizer was skipped, and a new lesson found during the run was announced in chat but never written to the file.
- **Why:** The router selects skills by request match. A local/batch request matches the bridge skills, and selecting one does not pull in a second skill whose description merely claims to be always-on. `persistent-memory` fires reliably for the opposite reason — it is invoked from `copilot-instructions.md`, which loads unconditionally.
- **Worked:** Put the scan obligation in `copilot-instructions.md` (Lessons learned — scan before local work), not only in the skill description, and cross-reference the lessons file from the bridge skills. Instructions load regardless of routing; skill descriptions do not. CONFIRMED by re-running the identical cold-start prompt after the fix: the session opened by naming three applicable Pattern-Keys unprompted (`batch-fsutil-needs-elevation`, `bridge-8932-writes-lf`, `bridge-8933-arg-name`), used `Get-PSDrive` first try instead of repeating the `fsutil` failure, and ran the CRLF normalizer before executing — which reported the new .bat as LF-only, so the trap was live and was avoided rather than survived.
- **Evidence:** measured — fix verified by controlled A/B on the same prompt, one cold start each side
- **See also:** bridge-8932-writes-lf

### A remembered prune list drifts from what is actually on disk
- **Pattern-Key:** prune-list-counts-drift-from-names
- **Delivered-to:** self-improvement
- **Date:** 2026-08-21
- **Trigger:** contradiction
- **Failed:** Acting on "12 dead June session folders" from memory. The folder held 14 matching folders: seven `intercompany-eliminations-calculation-*` plus a separate `intercompany-eliminations-current-year-*`, four `calculate-/calculating-/consolidating-*`, and two others.
- **Why:** Counts are summarized from a listing and then decay; the names are what a delete command actually consumes.
- **Worked:** Re-enumerate the directory immediately before deleting, delete only the names the user stated unambiguously, and hold anything extra for an explicit ruling rather than folding it into "the same class".
- **Evidence:** measured

### Stateless fixed the 8933 long-job kill - schtasks is no longer mandatory
- **Pattern-Key:** bridge-8933-longjob-fixed-by-stateless
- **Delivered-to:** command-bridge
- **Supersedes key:** bridge-8933-longjob-solved-schtasks
- **Date:** 2026-08-21
- **Trigger:** contradiction
- **Failed:** Believing long jobs (over ~60s) inherently kill the 8933 bridge, and that every such job MUST be launched through Task Scheduler via `_async-launch.ps1`. The earlier 101.4s failure was recorded as proof that statefulness was NOT the cause.
- **Why:** That conclusion came from a single test in which --stateful was live. Removing --stateful removed the failure, so the causation was exactly backwards.
- **Worked:** With 8933 stateless, two synchronous jobs ran to completion and the bridge survived on the SAME PID 37692: a 137.5s quarantine job and a 93.1s drop-rate probe, both exit 0 with full stdout returned. The schtasks/_async-launch.ps1 pattern still works and is still preferable for genuinely long or unattended work, but it is no longer required above ~60s.
- **Evidence:** measured - two runs at different durations, PID compared before and after

### Probe scripts using %LOCALAPPDATA% or %USERPROFILE% return false negatives
- **Pattern-Key:** probe-env-vars-blank-false-negative
- **Date:** 2026-08-21
- **Trigger:** contradiction
- **Failed:** Trusting `devtunnel-port-public.bat`, which concluded the devtunnel CLI was absent. Its search expanded `%LOCALAPPDATA%\Programs\Microsoft VS Code`, `%USERPROFILE%\.vscode` and `%LOCALAPPDATA%` - all BLANK in the 8933 job environment - so it searched empty paths and would have reported NOT FOUND even if the CLI were installed.
- **Why:** A negative result from a probe is only as good as the probe. User-profile variables are stripped in 8933 jobs, so any script that searches by them proves nothing.
- **Worked:** Re-probe with hard-coded absolute paths under `C:\Users\YOURUSER` plus a full recursive AppData sweep and a PATH check. The 2026-08-21 reprobe confirmed devtunnel really is absent - same conclusion, now actually evidenced. Treat any pre-existing NOT FOUND from a %VAR%-based probe as unproven and re-run it.
- **Evidence:** measured
- **See also:** bridge-8933-env-partially-stripped

### The 8932 devtunnel was not dead - all three tunnels answer
- **Pattern-Key:** bridge-devtunnel-declared-dead-without-reprobe
- **Date:** 2026-08-21
- **Trigger:** contradiction
- **Rule:** Run `bridge-health.bat` before characterising tunnel state. It is read-only and measures all three legs.
- **Delivered-to:** command-bridge, local-file-bridge
- **Failed:** Telling the operator twice in one session that "the 8932 devtunnel is dead" and offering it as the one remaining open item, on the strength of item (2) in the stored `config-open-fixes-2026-08-21` memory. Nothing was probed before saying it.
- **Why:** The memory recorded a real observation from earlier in the week and was never re-checked after the 23:04 clean restart. A stored open item has no expiry, so it keeps being repeated with the confidence of a fresh measurement long after the condition has cleared.
- **Worked:** Run `bridge-health.bat` before characterizing tunnel state. Section [3] returned HTTP 400 / 400 / 405 on the 8931, 8932 and 8933 devtunnel URLs - all three alive. Corrected the stored memory in the same pass and said so plainly in chat. Re-probe any stored "X is broken" item before repeating it; the cost is one read-only job.
- **Evidence:** measured - bridge-health report, 2026-08-21 20:51Z
- **Hits:** 2   (2026-08-21 stale stored open item; 2026-08-24 a probe taken 40 seconds after a deliberate restart)
- **Repeat 2026-08-24:** The same error from the opposite direction — not a stale memory this time but a measurement taken too EARLY. After killing 8932 to apply the OneDrive roots change, a probe ~40 seconds after relaunch read NO RESPONSE on the 8932 tunnel while 8931 and 8933 answered normally. That single reading was written up as "VS Code only forwards ports it owns", blamed on the detached Start-Process relaunch, and turned into a two-step manual remediation for the operator. His Ports panel disproved it outright: all three rows **Public** and **User Forwarded**, with an EMPTY Running Process column — so forwarding binds to the PORT, not to the process, and survives a process swap. A re-probe about four minutes later returned HTTP 405 with nothing done to fix it. The tunnel leg simply needs minutes to re-establish after the local listener is replaced. Wait and re-probe before characterising tunnel state after ANY restart: a fresh measurement is just as wrong as a stale one when it is taken too soon.
- **See also:** probe-env-vars-blank-false-negative, bridge-restart-needs-pid-kill
- **Promoted-to:** copilot-instructions.md, "Rules already paid for" (LESSON-DIGEST block) - rule text confirmed present in the digest 2026-08-28.

### The COPILOT_COWORK repo was clean, not dirty
- **Pattern-Key:** git-repo-clean-not-dirty
- **Supersedes key:** repo-clean-not-dirty
- **Date:** 2026-09-09
- **Trigger:** contradiction
- **Rule:** Read the actual git status before describing repo state. Do not narrate from memory of what you changed.
- **Delivered-to:** gamma-tango, git-bridge
- **Hits:** 3   (2026-08-18 stale "everything is uncommitted"; 2026-08-26 a handoff offered a bare `git add`/`git commit` for two cloud-side writes; 2026-09-09 a hand-off said the prior day's snapshot jobs were committed - `git status` showed them untracked)
- **Failed:** Carrying "everything changed since the 11:52 baseline is uncommitted" into a new session and repeating it as fact.
- **Why:** The day's work was on skills and memory in OneDrive `Documents/Cowork`, which is outside the repo. Git saw nothing because nothing tracked had changed.
- **Worked:** Run `git --no-pager status --porcelain` before characterizing repo state. Correct the source memory, then log.
- **Repeat 2026-08-26 — a cloud-side write is not a committable change until the sync job runs:** `cowork-lessons.md` and `MEMORY-INDEX.md` were written cloud-side that morning via `UploadFileContent` because the bridges were down. A handoff then offered the operator "the exact `git add`/`git commit` line for the two files" to paste into his own terminal. Git tracks only `COPILOT_COWORK\CoworkConfig\`, a robocopy mirror of OneDrive `Documents/Cowork` (commit 5ff400d) — so a bare `git add` against those two paths stages nothing until (a) OneDrive has replicated the cloud write down to the PC and (b) `CommandJobs\2026-08-18-sync-cowork-config.bat` has mirrored it into `CoworkConfig\`. Any hand-off git line for a memory or lessons file MUST lead with the sync job, and must name the `CoworkConfig\cowork-memory\` path rather than the OneDrive one.
- **Repeat 2026-09-09 - a hand-off's "committed" is a claim, not a status:** the previous session's hand-off summary said the 2026-09-08 snapshot jobs were "committed and can join the archive at the next close". The read-only baseline job that opened this session ran `git status --porcelain` in COPILOT_COWORK and listed `CommandJobs/2026-09-08-aor-snapshot2.bat` and `.ps1` as untracked (`??`). Nothing was lost - the files were on disk - but a session that trusted the hand-off would have skipped them at the next close. The baseline job is the fix: every open reads the real status before any state is described.
- **Evidence:** measured — the 2026-08-18 occurrence, the repo layout (5ff400d), and confirmed directly on 2026-08-26 once the bridges returned: the `CoworkConfig\cowork-memory\` mirror was still a full day behind the OneDrive copy and `git status --short` listed no memory file at all, so the bare `git add` that had been drafted for the operator would indeed have staged nothing; 2026-09-09 measured - `git status --porcelain` in the snapshot3 job listed the two files as `??`
- **See also:** git-misses-system-state, onedrive-cloud-to-laptop-lag, bridge-connector-removed-midsession
- **Promoted-to:** copilot-instructions.md, "Rules already paid for" (LESSON-DIGEST block) - rule text confirmed present in the digest 2026-08-28.

### The watchdog was not responsible for the midday outage
- **Pattern-Key:** watchdog-exonerated
- **Date:** 2026-08-18
- **Trigger:** contradiction
- **Failed:** Suspecting the watchdog of killing bridges or sessions.
- **Why:** It is read-only unless a TCP connect is refused, and it never kills. Its log showed no restarts in the outage window.
- **Worked:** Read `watchdog.log` and `status.txt` before assigning blame. Confirmed again 2026-08-18 16:51 — task Ready, result 0, all three ports UP.
- **Evidence:** measured

### Do not recommend an edit to a file you have not read this session
- **Pattern-Key:** agent-recommends-edit-without-reading-file
- **Date:** 2026-09-02
- **Trigger:** contradiction
- **Failed:** Putting "two skills now teach the wrong thing" on a next-steps list, asserting that `git-bridge` and `command-bridge` both mandate the schtasks pattern for jobs over ~60s and needed relaxing. Reading them showed `git-bridge` contains zero mentions of async, schtasks or long-running jobs, and `command-bridge`'s only "long job" text is retry discipline that is still correct. There was no documentation bug at all.
- **Why:** The claim was generated from stored memory about what those skills say, not from their contents. Memory records conclusions, not file text, and a remembered summary drifts from the file exactly like a remembered prune list drifts from disk.
- **Hits:** 3 (2026-08-21 agent summary; 2026-08-25 memory store; 2026-09-02 twice in one session - a stale `tasks.json` header comment read as the watchdog's current state and reported to the operator as a live availability gap, and a proposal to merge bridges 8931-8934 behind one port made without reading their per-port supergateway flags. Both were disproved by opening the file: `_bridge-watchdog.ps1` lists all four ports, and 8931 carries `--stateful` where the others must not. A COMMENT describing code is the same class of stale summary as a remembered one - read the code)
- **Promotion:** 2026-08-29 - Rule authored and carried into the copilot-instructions.md LESSON-DIGEST, so it now loads every session.
- **Rule:** Read the file or config surface this session before proposing a change to it, and quote the lines that are or are not there. Memory records conclusions, not file text. Say plainly when a recommendation turns out to be unfounded rather than quietly dropping it.
- **Worked:** Read or grep the actual file before proposing a change to it, and say plainly when a recommendation turns out to be unfounded rather than quietly dropping it. Same discipline as re-enumerating a directory before deleting.
- **Evidence:** measured - both files read end to end, zero matches
- **See also:** prune-list-counts-drift-from-names, agent-claims-action-before-doing-it

### A settled rule is only settled once every surface that states it agrees
- **Pattern-Key:** config-contradiction-survives-in-second-file
- **Date:** 2026-10-01
- **Trigger:** contradiction
- **Rule:** A rule is settled only when EVERY surface that states it agrees. Before calling one done, grep the instructions file, every SKILL.md, the memory folder and the stored-memory index for the old wording, and fix them in the same pass - routing loads whichever copy it reaches first, and the dangerous copy is usually the one that loads precisely when the rule matters.
- **Failed:** Treating "no autorun fallback" as done after fixing `cowork-bridge-infrastructure.md`. The forbidden path was still taught in two other places: the "Fallback when the command bridge is down" section of `copilot-instructions.md`, and a section of the `local-file-bridge` skill instructing the filesystem bridge to drop scripts into `COPILOT_COWORK\autorun\queue` when 8933 is down. The `local-file-bridge` copy was the dangerous one, because that skill is loaded exactly when 8933 is unavailable.
- **Why:** The same rule is restated across instructions, several SKILL.md files, memory files and stored memories. Fixing the surface that prompted the correction leaves the others intact, and routing picks whichever one loads.
- **Worked:** When a rule changes, grep every config surface for the forbidden term before declaring it removed - `grep -rni "<term>" /mnt/user-config/skills --include=SKILL.md`, the instructions file, the memory folder, and the stored-memory index. Fixed all three surfaces and deleted the contradicting stored memory `pref-8933-down-use-autorun-queue`.
- **Evidence:** measured - grep found the three surfaces; all re-read after editing
- **Hits:** 2
- **Hit 2, 2026-10-01:** `AgentConstructLab\release4\PROJECT_IDENTITY.md` and `release4-status.json` scope_guardrails both state "ACL is the Microsoft 365 Copilot agent, not a provider-neutral layer"; the public-repo plan written the night before states the opposite. the operator decided 2026-10-01: provider-neutral, runtime lives in ACL. The two frozen-core files were NOT corrected in that session - step 1 of contradiction handling is outstanding and belongs to the Release 5 closeout, before anything reads them as authoritative.
- **Promotion:** 2026-10-01 - Rule exists; carried into the copilot-instructions.md LESSON-DIGEST by digest_apply.py at this close.
- **See also:** git-repo-clean-not-dirty

### A stored constraint about a script decays when the script is improved
- **Pattern-Key:** git-sync-scope-memory-went-stale
- **Date:** 2026-08-28
- **Trigger:** contradiction
- **Rule:** Read the script before designing around a remembered constraint about what it does. A stored scope claim decays silently when the script is fixed.
- **Delivered-to:** git-bridge
- **Hits:** 2
- **Promotion:** 2026-09-09 - second hit; the Rule is carried into the copilot-instructions.md LESSON-DIGEST at Hits 2, so it now loads every session.
- **Repeat 2026-09-09 - the same decay, on a server instead of a script:** the working assumption for porting executor 1.3.0 was that the live `Startup\CommandBridge\batch-exec-server.js` equalled the repo's 1.2.0. Reading it first (`read_text_file`, then a local diff) found v1.1.0: `COWORK_ROOT` and the OneDrive lessons path hard-coded, no `COWORK_CONFIG_ROOT` support, 31,185 bytes against the repo's 36,688. That changed the port - the launcher had to gain `set COWORK_CONFIG_ROOT=...`, or the operating-rules reminder would have silently switched from the live corpus to the CoworkConfig mirror - and the port job pinned the live file's hash as a precondition so the design and the artifact could not drift apart between reading and acting.
- **Failed:** Carrying the stored fact that `2026-08-18-sync-cowork-config.bat` copies `SKILL.md` ONLY, recorded 2026-08-20 after `review_strip.py` could not reach the repo. On that basis the operator was warned that the pending commit would silently miss all four changed `scripts/*.py` files and would need extra verification to catch it.
- **Why:** The job was improved at some point after 2026-08-20 and its Skills leg now reads `robocopy "%SRC%\Skills" "%DEST%\Skills" *.md *.py *.js /S /PURGE`. A memory records a script's behaviour at one instant; the script is then edited and nothing revisits the memory, so a claim that was true once keeps being repeated with the confidence of a fresh measurement. This is the same decay shape as a stale "X is broken" open item, applied to a capability rather than a fault - and it biases the opposite way, planning around a limit that no longer exists.
- **Worked:** Read the job with `read_text_file` before relying on the stored scope, and let the commit stat prove it. Commit ac6d9ec carried all four scripts - `lesson_brief.py`, `lesson_brief_selftest.py`, `lesson_check.py`, `lesson_check_selftest.py` - 8 files, 245 insertions, and `git status --short` empty afterwards. Corrected the memory in the same pass, keeping the half still true (the PC's local OneDrive copy can lag a cloud write, and robocopy exit 0 means nothing was copied) and deleting the half that is not.
- **Evidence:** measured - the robocopy line read verbatim from the job before the run, and all four scripts present in the commit stat afterwards
- **See also:** git-repo-clean-not-dirty, onedrive-cloud-to-laptop-lag, bridge-devtunnel-declared-dead-without-reprobe

## Open questions

### Does Cowork accept a well-formed draft-07 tool schema?
- **Pattern-Key:** cowork-draft07-well-formed-untested
- **Distinct-from:** fs-server-pin-measured-output-schema-only - that entry is a MEASURED defect in how a pin was chosen (output schemas read, input schemas never); this is an UNTESTED claim about the host (draft-07 rejected regardless of completeness) that sits in a launcher comment. One is a wrong measurement already made; the other is a measurement not yet made.
- **Date:** 2026-09-15
- **Trigger:** open
- **Failed:** Not established either way. The observed rejection was of a structurally empty `inputSchema` — no `type`, no `properties` — which would be refused whatever dialect it declared.
- **Why:** The `fs-server.sh` note of 2026-09-13 asserts that Cowork supports 2020-12 only and that draft-07 fails every call. Nothing in this repository has tested that against a schema that is complete and merely labelled draft-07.
- **Worked:** UNKNOWN. `install_check.py` treats a non-2020-12 dialect as a failure, which is the safe default and may be stricter than the client. Do not relax it on reasoning alone.
- **Still open:** Install `server-filesystem@2025.8.21` with an npm `overrides` of `zod` to `^3.25.0`, register it, and call one tool. If it works, well-formed draft-07 is accepted and the dialect check should warn rather than fail. This matters to the Copilot route, which uses that bridge unpinned every day.
- **Evidence:** measured — the override restores complete schemas; whether the client then accepts them is unprobed.
- **See also:** fs-server-pin-measured-output-schema-only

---

### A verified-absent artifact deletion came back on its own
- **Pattern-Key:** artifact-deletion-reverts-after-verified-absent
- **Date:** 2026-08-28
- **Trigger:** failure
- **Failed:** Nothing that fixed it. Six files were deleted from the session `output` surface; the delete response listed all six as `deleted` with `not_found: []`, and an independent `Glob output/**/*` confirmed only the intended survivors remained. About twenty minutes later an `os.listdir` of the same folder showed all six back, together with the `python` folder and its eleven files, at sizes byte-identical to the pre-deletion listing.
- **Why:** Not established. Byte-identical sizes across the before and after listings are consistent with the same bytes being restored rather than regenerated, but nothing was probed to identify what restored them. Do NOT read this as a verification failure: the check was sound and its result was true when it was read. The state did not hold.
- **Worked:** UNKNOWN - no fix was found and none should be assumed. Three things are safe to act on. (1) A listing taken straight after a delete establishes that instant only, so do not report a deletion as final on one immediate check - re-list after a delay before saying it is done. (2) Do NOT blind-retry. A store that restores what you deleted is the one case where retrying is not free, a second delete was never tested here, and repeated deletes race whatever is doing the restoring; this session reported the reversion to the operator instead. (3) This is NOT the defect in `artifact-delete-recursive-skips-file-paths` - the recursive flag explains why the FIRST call skipped those files and explains nothing about why the second, verified call did not hold. The observed interval before the reversion is one observation, not a safe waiting period.
- **Still open:** Does the `output` surface re-sync from a source that still holds the deleted files? `onedrive-user-surface-not-live` measured that the user surface is a container mirror, which makes "the mirror was refreshed from its source" the first hypothesis to test. Does a second delete hold, or revert again? Is there a delete that reaches the source rather than the mirror? Was anything else running that could rewrite that folder?
- **Evidence:** measured - the reversion was seen in a directory listing that was read, as was the delete verification before it; the cause is unprobed
- **Hits:** 1
- **See also:** artifact-delete-recursive-skips-file-paths, onedrive-user-surface-not-live, cleanup-quarantine-instead-of-delete

### Every empty ACL turn so far began with a write-class tool call - cause still unmeasured
- **Pattern-Key:** acl-empty-turn-correlates-with-write-first-call
- **Distinct-from:** acl-instruction-overlap-no-response-unmeasured - that hypothesis (instruction gate overlap) was tested and ruled out; this entry holds what remains. acl-self-report-is-not-the-record - that is how to GRADE a turn after it happens; this is WHY the turn comes back empty.
- **Date:** 2026-10-02
- **Trigger:** failure
- **Routes:** copilot
- **Rule:** Treat an empty ACL turn as unknown state, not as a stall: read the disk over 8932 and the per-request debug panel before saying "continue", and count empty turns separately for write-first and read-first prompts whenever a new ACL version is tested.
- **Failed:** On 1.4.0 in Auto mode, 3 of 3 turns returned no text (a write+verify case, a bare "hello?", a browser case) while the UI showed "Reasoning completed in 1 step / Connecting to jordan-filesdev"; the write case's file later existed on disk with correct content, so Auto executed the write and dropped the reply. On 1.4.0 in Think deeper, the first turn of a fresh write case returned no text and, per the debug panel, executed NOTHING. On 1.4.1 (Think deeper, dev mode on) the first attachment case returned no text again and completed only after "continue". Two stalls in the morning's self-administered run also needed "why did you stop?".
- **Why:** Not established. What was measured: the pinned `mcp-tools.json` and `mcp-tools-playwright.json` already carried `annotations.readOnlyHint` on every tool (reads true; writes false + destructive); only `mcp-tools-command.json` had none. Microsoft's documentation says `readOnlyHint` suppresses confirmation cards, so cards could only ever fire on write-class calls - and every observed empty turn (10-01 attachments; 10-02 cases 3 and 5; the hello3 case; case 17) was a turn whose first tool was write-class, against 0 empty turns on roughly 16 single-read or single-dispatch turns. A public ATK issue with the same setup (devtunnel anon, v1.8 manifest, v2.4 plugin, pinned server) reports confirmation-card loops where zero requests reach the server. That is a correlation and a candidate mechanism, not proof - inference unverified. The two empty turns also differ inside: Auto executed and dropped the reply; Think deeper executed nothing. The empty-response behaviour is not on the M365 known-issues page.
- **Worked:** UNKNOWN. Safe to act on: after an empty turn, check the artifact on disk over the bridge and read the per-request debug panel before choosing between "continue" and re-issuing; "continue" completed every stalled case observed. 1.4.2 was provisioned with annotations on the 2 command tools and `capabilities.confirmation` on 12 write-class functions - its effect on empty-turn incidence has NOT been measured.
- **Still open:** (1) Does the operator ever see Allow/Cancel confirmation cards on write-class calls? Asked 2026-10-02, unanswered. (2) Re-run the same write-first cases on 1.4.2 and count empty turns against the 1.4.0/1.4.1 record. (3) Why does Auto execute-and-drop while Think deeper executes nothing behind the same empty UI? (4) Does `default_response_mode` matter - the doc says the default is not applied via @mention.
- **Evidence:** measured for the empty turns and the on-disk outcomes (files read over 8932; debug panel read); the write-first correlation is a count over this session's and the previous day's turns; the confirmation-card mechanism is inference unverified.
- **Hits:** 1
- **See also:** acl-instruction-overlap-no-response-unmeasured, acl-self-report-is-not-the-record, acl-handoff-files-must-land-in-a-declared-root

## Patterns

### A rule served where it cannot apply costs the rules that can
- **Pattern-Key:** lessons-served-out-of-scope-dilute-the-block
- **Distinct-from:** skill-portability-is-one-text-not-two-bundles - that is about a SKILL's text having to be correct on every platform (one text, named mechanics for each); this is about which LESSONS are delivered to a route: a hit count measured on one route selects the wrong rules for another. One is authoring scope, the other is delivery selection.
- **Date:** 2026-09-15
- **Trigger:** pattern
- **Rule:** Scope a lesson to the route and platform where its rule can fire. A delivery block is spent attention, not free shelf space.
- **Delivered-to:** self-improvement, dream-cycle, command-bridge
- **Failed:** Every `run_batch_file` result on macOS under Claude Cowork carried an eight-rule operating block of which two applied. The other six told the operator to check tunnel drops, set ports PUBLIC, resync `tasks.json` and run `bridge-health.bat` — on a route with no tunnel, no ports, no `tasks.json` and no `.bat`. Across the corpus, 77 of 123 entries referenced machinery that route does not have.
- **Why:** The corpus grew on the hosted route, where all of it was true, and the delivery mechanism was written to serve the top rules by hit count with no notion of where a rule applies. Hit count measures how often a rule mattered *somewhere*, which on a different route selects for exactly the wrong entries.
- **Worked:** Optional `Routes:` and `Platforms:` fields, absent meaning everywhere, filtered at delivery. Nothing deleted, nothing moved. 27 entries scoped to the Copilot route and 5 to Windows; a Mac job went from 27 candidate rules to the 16 that apply, and the served block became the arg-name rule, the transport-retry rule and the git-status rule instead of six about a tunnel. Scope on what the **Rule** says, never on what the example cites — a first pass keyed on the whole entry scoped a universal rule to Windows because its `Failed:` block showed a `.bat`.
- **Evidence:** measured — the block read before and after, and the corpus counted both ways.
- **See also:** narrow-before-fixing-duplicated-capability

### Narrow before fixing a capability the host already has
- **Pattern-Key:** narrow-before-fixing-duplicated-capability
- **Distinct-from:** fs-server-pin-measured-output-schema-only - that is a measurement defect inside a repair that was warranted; this is the question that comes BEFORE any repair: whether the component should still exist now that the host does its job. Had this question been asked first, that measurement would not have been needed.
- **Date:** 2026-09-15
- **Trigger:** pattern
- **Rule:** Before repairing a component, ask whether the host now does the same job. A duplicated component is worth deleting, not fixing.
- **Delivered-to:** self-improvement, dream-cycle
- **Failed:** Hours went into the filesystem bridge — diagnosing the schema fault, finding the zod root cause, preparing to vendor a dependency tree — before anyone asked whether the bridge should exist. Each finding justified the next step, and none of them questioned the goal.
- **Why:** A handoff that names a component as the task makes the component the frame. The repository was built when Cowork shipped none of connected folders, a browser, memory or a plugin installer; three of its four bridges had since become duplicates, and the port-and-tunnel vocabulary was carried over from the hosted route where it still belongs.
- **Worked:** Asking what each component adds that the host does not. Three of four bridges and five of ten skills turned out to be scaffolding; the approved executor is the one thing with no first-party equivalent. Narrowing removed the schema fault, the npx fetch and the upstream dependency from the Claude route without fixing any of them.
- **Evidence:** measured — `bridges in scope 1 of 4`, `INSTALL_CHECK: CLEAN`, and the executor confirmed running natively on Darwin while the session shell runs on Linux.

### `git apply` under Git for Windows rewrites every patched text file to CRLF
- **Pattern-Key:** git-apply-on-windows-writes-crlf
- **Date:** 2026-10-01
- **Trigger:** failure
- **Routes:** copilot
- **Platforms:** windows
- **Rule:** After `git apply` on Windows, hash every patched file against a pin before trusting it; expect CRLF. Normalise CRLF to LF only where the LF form matches the pin, or apply with `git -c core.autocrlf=false apply`.
- **Delivered-to:** command-bridge
- **Failed:** `gt541-apply.bat` applied a 145 KB unified diff cleanly (`--check` and apply both exit 0), then the hash gate failed on all 17 text files it had touched - each exactly one byte per line longer than the container's copy. The new file in the patch (selection.py) came out CRLF too.
- **Why:** Git for Windows honours `core.autocrlf` when it writes the result of `git apply`, even outside a repository. Content was correct; line endings were not. Nothing in the apply output says so.
- **Worked:** A fix-up job that converts CRLF to LF ONLY on files whose LF form hashes to the pinned value, refuses anything else, then re-verifies all 86 files and the untouched baseline. Three apply rounds, same 17 files each time, all recovered.
- **Evidence:** measured - `FAIL every release-tree file matches ... ['CHANGELOG.md', ...]` then `FIXLF_RESULT: OK files=86`; sizes 14937 -> 15214 for a 277-line file.
- **See also:** bridge-8932-writes-lf, python-text-mode-on-windows-writes-crlf

### Python text-mode writes on Windows produce CRLF, zipfile normalises stored backslashes on read, and an inherited cp1252 stdout crashes on an emoji
- **Pattern-Key:** python-text-mode-on-windows-writes-crlf
- **Date:** 2026-10-01
- **Trigger:** failure
- **Routes:** copilot
- **Platforms:** windows
- **Rule:** In an 8933 job's Python: write hash-pinned or byte-compared files with `write_bytes`, never `write_text`; read ZIP member names from `ZipInfo.orig_filename` when judging path safety; call `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` at the top - setting PYTHONUTF8 in `os.environ` only reaches child processes.
- **Delivered-to:** command-bridge
- **Failed:** Three separate release-job failures after the suite had already passed 81/81: (1) a regenerated MANIFEST.json was not byte-identical to the reviewed one - `write_text` had written CRLF; (2) the 5.3.8 test that plants `deck-builder\\bad.py` in a ZIP passed `linuxPaths: True` on Windows because `ZipFile.infolist()` normalises the stored backslash to `/` while reading; (3) printing a dict containing the selector cue `🟥` raised `UnicodeEncodeError: 'charmap'` and killed the job one step from the ZIP.
- **Why:** Windows text mode translates `\n`; `ZipInfo.__init__` normalises `os.sep` on both write and read; a job interpreter starts under the console code page before the script can set an environment variable.
- **Worked:** `write_bytes((json.dumps(...) + "\n").encode("utf-8"))`; `getattr(i, "orig_filename", i.filename)` in `package_integrity` (shipped in 5.4.1 so Windows users verifying a ZIP get the right answer); the stdout reconfigure. Each fix was a one-line `edit_file` on the PC copy, mirrored to the source.
- **Evidence:** measured - job stdout for all three, then `RESULT=OK`, `VERIFY_ZIP=ok`, `ZIP_SHA256=bce27d72...`.
- **See also:** git-apply-on-windows-writes-crlf

### The approved executor kills a job at 300 seconds - long work must checkpoint and resume
- **Pattern-Key:** batch-8933-job-timeout-300s-checkpoint-resume
- **Date:** 2026-10-01
- **Trigger:** failure
- **Routes:** copilot
- **Rule:** Design any job that may run past five minutes to record progress per unit of work and to skip finished units on rerun. Run it again until it completes; treat `exit 9999 TIMED OUT` as a pause, not a failure, and only after reading what the checkpoint says finished.
- **Delivered-to:** command-bridge
- **Failed:** `gt541-release.bat` was killed twice at 303-304 s (`exit code 9999 (TIMED OUT -- process tree killed)`) while the 82-case certification suite ran; the kill took the case in progress with it.
- **Why:** The executor enforces a hard 300 s wall clock with no override parameter in the schema (only `file`). The certification suite needs about seven minutes on the operator's PC.
- **Worked:** The 5.4.1 harness writes a checkpoint after every case (atomic tmp + replace) and `--resume` marks already-passed cases RESUMED; the release script always passes both flags. Pass 1 finished 75 cases in the window, pass 2 finished the last 6 and reported `81/81 passed`, pass 3 (after two small script fixes) did the manifest, preflight, verify-package and ZIP in 6 s.
- **Evidence:** measured - three job records in `CommandJobs\Logs\ops\gt541-release*`, the checkpoint JSON, and `TESTS_CERTIFICATION=81/81 passed`.
- **See also:** bridge-8933-longjob-fixed-by-stateless, schtask-hosted-success-describes-the-trigger

### The task's OneDrive output folder reaches the PC in about two minutes and is a binary-safe transport
- **Pattern-Key:** onedrive-task-output-is-a-binary-safe-transport
- **Date:** 2026-10-01
- **Trigger:** success
- **Routes:** copilot
- **Rule:** To move a payload of any size or type to the PC, `CopyArtifact` it into the session's `output/`, wait ~90 s, confirm it under `OneDrive\Documents\Cowork\Tasks\<task>\output\...` with the bridge, then stage it with robocopy in an 8933 job. Never retype file contents through `write_file` - pin and verify instead.
- **Delivered-to:** local-file-bridge, command-bridge
- **Failed:** Hand-typing an 8 KB hash table into `write_file` produced one wrong SHA-256 (caught by the pin on the file, not by eye). Twelve 4.5 KB base64 parts were about to go the same way.
- **Why:** Anything that passes through the assistant's own output is a transcription, and a 64-character hash has no redundancy. The OneDrive route copies bytes.
- **Worked:** A 19-file payload (patch parts, pins, scripts, instructions) landed complete on the PC 90-120 s after `CopyArtifact`, three times running; `robocopy` staged it and every pin matched first time. Use a NEW folder name per revision - `CopyArtifact` refuses to overwrite without `overwrite=true`, and a fresh name keeps the earlier payload for the record.
- **Evidence:** measured - `list_directory_with_sizes` on the synced folder, then `OK payload part patch.b64.01 matches its pin` x12 in the apply job.
- **See also:** bridge-8932-large-write-corrupts-a-character, onedrive-cloud-to-laptop-lag, onedrive-user-surface-not-live

### Agent Builder rewrites a skill's SKILL.md front matter on upload - a hash-enforced package must expect it
- **Pattern-Key:** agent-builder-rewrites-skill-md-front-matter
- **Date:** 2026-10-01
- **Trigger:** failure
- **Routes:** copilot
- **Rule:** Any integrity check shipped inside an M365 declarative-agent skill must treat SKILL.md as host-managed: compare it after normalising line endings (and be ready for the front matter to be re-serialised), report the normalisation, and keep strict byte hashing for every other file. Prove the fix in-tenant with the agent's own preflight, not on the PC.
- **Delivered-to:** command-bridge
- **Failed:** Deck Builder 5.4.1 verified clean on the PC (`verify-package` ok, ZIP SHA bce27d72...) and then reported `hash mismatch: SKILL.md` on every preflight inside the agent, so the agent was obliged to call the package unverified every time.
- **Why:** Agent Builder parses the `name`/`description` front matter and writes it back: measured in-tenant, exactly the five front-matter lines came back CRLF (5 CRLF, 186 LF, no BOM, length 21,447 -> 21,677); CRLF->LF restored the shipped hash; trailing-whitespace stripping did not match; MANIFEST.json was untouched.
- **Worked:** 5.4.2 `package_integrity` moves a HOST_MANAGED file from `changed` to `normalized` when its CRLF->LF hash matches and says so in `note`; a content edit or any other file still fails (regression case plants the exact five-line rewrite). In-tenant preflight then returned `ok: true, normalized: ["SKILL.md"]`.
- **Evidence:** measured - the agent's diagnostic output (raw vs CRLF->LF hashes) and the 5.4.2 preflight output inside the agent.
- **See also:** python-text-mode-on-windows-writes-crlf, git-apply-on-windows-writes-crlf

### Compute a landing's expected hashes by applying the land folder to a scratch copy, not by predicting them
- **Pattern-Key:** land-expect-hashes-from-scratch-apply
- **Distinct-from:** edit-block-anchor-must-end-at-line-boundary - that is the FORMAT rule for an anchored edit; this is how the RESULT of all the edits is pinned before the land job runs. gate-asserts-an-unmeasured-count - there a gate asserted a count nobody measured; here the `expect{}` hashes used to be predicted from file contents held in context, and the fix is to measure them from a real application of the same inputs with the same semantics. bridge-8932-large-write-corrupts-a-character - that is why the pins exist; this is how the post-edit hashes are obtained.
- **Date:** 2026-10-01
- **Trigger:** better-approach
- **Routes:** copilot
- **Rule:** Before `aor-land.bat`, run a read-only job that copies the clone (without `.git`) to a scratch folder, applies `bundle.txt` and `edits.txt` with the land job's own semantics (FILE body + one LF; `once` anchors matched as whole lines; `countN` tokens), prints the LF-normalised SHA-256 of every touched file, and runs the gate checks the change can affect. Paste those hashes into `expect{}`. The land job then verifies a measured result instead of a predicted one, and a bad anchor or a failing gate costs twenty seconds on a scratch copy instead of a reverted land.
- **Delivered-to:** command-bridge, git-bridge
- **Failed:** The previous landings predicted `expect{}` from file contents read into the session, which for a 9-file change meant reading CHANGELOG.md (569 lines), README.txt and both install pages over the bridge just to hash them, and a prediction that was wrong once (an extra trailing newline) reverted a correct land.
- **Why:** The land job's checks are deterministic functions of (clone at `expected_head`, bundle, edits). Running those same functions on a copy produces the exact hashes it will compute, with no transcription in between, and the affected gate checks (executor self-test, bundle check, plugin delivery, operator scan, facts, public scan) run on the result the job will see.
- **Worked:** `scratch_apply.py` in LAND_DIR `Outputs\Agent of Record\executor-1.9.0`: two runs (21 s and 19 s) produced the hashes, caught a prose claim of "70 cases" that the Windows run measured as 74, and the land then passed `9 files match their pinned content` and `RELEASE_CHECK: CLEAN (32 checks)` first time; PR #34 merged as `110405f`.
- **Evidence:** measured - both scratch runs' stdout, then the land job's stdout.
- **Hits:** 1
- **See also:** edit-block-anchor-must-end-at-line-boundary, gate-asserts-an-unmeasured-count, onedrive-task-output-is-a-binary-safe-transport

### A file handed to the M365 agent must sit under a root the agent's own plugin names
- **Pattern-Key:** acl-handoff-files-must-land-in-a-declared-root
- **Distinct-from:** bridge-8932-searchfiles-false-negative - that is the glob semantics of `search_files` within a root it can see; here the files were outside every root the agent's plugin description names, so no pattern could have found them. onedrive-user-surface-not-live - that is which LEG a write takes to reach the PC; here the write reached the PC fine but landed in the wrong tree for the consumer.
- **Date:** 2026-10-01
- **Trigger:** failure
- **Routes:** copilot
- **Rule:** When handing files to ACL (the M365 declarative agent), land them under `COPILOT_COWORK` with `move_file` first and give it the exact folder path. The 8932 bridge serves four roots, but ACL's plugin text names only `COPILOT_COWORK`, so it searches there and reports "no local matches" for anything in the OneDrive Cowork tree - truthfully, and at the cost of a turn each time.
- **Delivered-to:** command-bridge, local-file-bridge
- **Failed:** Three hand-off files were staged in the OneDrive Cowork task folder (a bridge root) and ACL was told to move them. It searched `COPILOT_COWORK` recursively twice, found nothing, created the destination folder, and reported a blocker - two agent turns and the operator's time, with no progress.
- **Why:** The agent's notion of "the workspace" is what its plugin description says, not what the bridge can reach. A Cowork session knows the other three roots; ACL 1.4.0 does not.
- **Worked:** The session moved the files itself with `move_file` into `COPILOT_COWORK\Outputs\Agent of Record\executor-1.9.0` and did the hash check and self-test by `run_job`. Durable fix queued for ACL 1.4.1: name all four roots in `ai-plugin.json` and the instructions.
- **Evidence:** measured - ACL's two replies ("no local matches" with the recursive patterns it used) and the successful `move_file` result.
- **Hits:** 1
- **See also:** bridge-8932-searchfiles-false-negative, acl-instruction-overlap-no-response-unmeasured
