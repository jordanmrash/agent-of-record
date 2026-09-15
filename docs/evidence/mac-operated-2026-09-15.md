# macOS operated evidence — 2026-09-15

Device: `jordans-macbook-air-local`, Apple arm64, macOS 26.6.2 (Darwin 25.6.0).
Operator route: Claude Cowork, local stdio route, tooling root `~/agent-of-record`.
Commit under test: `6cfc77c` on `main`.

Covers steps 1–3 of "Real-device evidence still needed" in `aor-handoff-2026-09-14.md`.
Steps 4–5 (build/install the macOS `.plugin`, restart Claude, `ListSkills`) are **not** done.

---

## Step 1 — Pull `main` at `6cfc77c` — DONE

The Mac clone was still on the stale feature branch `fix/macos-port-text-and-server-key`
at `fa7473b`. That branch tip was **not** equivalent to the squashed `main`: `main`
carried 55 changed files beyond it, including `scripts/build_plugin.py`,
`scripts/build_plugin_selftest.py` and the `scripts/personalize.py` →
`scripts/copilot/personalize.py` move.

Fetched, switched to `main`, fast-forwarded:

```
$ git log --oneline -1
6cfc77c feat: make the bridges and all ten skills work across Claude Cowork on Windows and macOS
$ git status --short --branch
## main...origin/main
?? CommandJobs/hello-mac.sh
?? CommandJobs/test-executor.sh
?? docs/evidence/install-macos-2026-09-12.json
```

Clean against `origin/main`; the three untracked files are pre-existing local scratch
and prior evidence, not repository drift.

Deletions required by the checkout — the intended PR #18 removals — were:
`CoworkConfig/Skills/myvoice/SKILL.md`, `CoworkConfig/Skills/myvoice/skill-quality-report.json`,
`Startup/posix/flow-server.sh`, `Startup/posix/watchdog/bridge-watchdog.sh`,
`Startup/posix/watchdog/install-launchd.sh`, `scripts/personalize.py`.

## Step 2 — `install_check.py --route local` on Darwin — CLEAN

Run **on the Mac itself**, through the `aor-batch-exec` bridge
(`CommandJobs/mac-evidence-install-check.sh`), not in the desktop Linux workspace.
Full transcript: `Outputs/Mac Evidence 2026-09-15/install-check-macos-20260914-223607.txt`.

```
host:     Darwin 25.6.0 arm64
macOS:    26.6.2
commit:   6cfc77c main
python:   Python 3.14.7
node:     /Users/YOURUSER/.local/bin/node v26.8.2
...
host: Darwin 25.6.0  python 3.14.7  route local
config root: (not given)
INSTALL_CHECK: CLEAN (18 passed, 4 skipped)
```

The four SKIPs are by design: `supergateway` (unused on the local route), the 8931 and
8932 stdio handshakes (upstream servers fetched by npx at first start), and installed
skills (`COWORK_CONFIG_ROOT` is commented out in `Startup/posix/cowork-env.sh`, so the
bridge runs two roots and the in-repo `CoworkConfig/` is used).

Counts differ from the Windows post-merge run (`15 passed, 4 skipped`) because macOS is
in scope for three of four bridges — 8931, 8932, 8933 — and Windows for a different set.
Not a regression.

## Step 3 — one tool on each bridge

| Bridge | Tool called | Result |
|---|---|---|
| `aor-batch-exec` | `run_batch_file("hello-mac.sh")` | **PASS** — exit 0, 60 ms |
| `aor-playwright` | `browser_navigate("https://example.com")` | **PASS** — page title `Example Domain` |
| `aor-filesystem` | `list_allowed_directories`, `get_file_info` | **FAIL** — server in `failed` state |

`aor-batch-exec` returned from the real machine, which is the point of the job:

```
Running as:        jordanrash
Machine:           arm64, macOS 26.6.2
Working directory: /Users/YOURUSER/agent-of-record/CommandJobs
Node the jobs see: /Users/YOURUSER/.local/bin/node
```

`aor-playwright` drove a real browser and wrote its snapshot to
`playwright-output/page-2026-09-15T03-35-30-271Z.yml`.

### `aor-filesystem` — broken, and the existing pin does not fix it

First call returned a client-side schema rejection; the server then reported `failed`:

```
Invalid result for tools/list: [{ "code": "invalid_value", "values": ["object"],
  "path": ["tools", 0, "inputSchema", "type"], ... }]
```

An earlier revision of this file attributed that to the pre-pin launcher and predicted it
would clear at the next Claude restart. **That was wrong.** Measured on this Mac the same
day, by handshaking the pinned launcher directly:

| version | tools | inputSchema missing `type` | input draft-07 | output draft-07 |
|---|---|---|---|---|
| **2025.8.21** (current pin) | 14 | **13** | 13 | 0 |
| 2025.11.25 | 14 | 0 | 14 | 14 |
| 2026.8.31 | 14 | 0 | 14 | 14 |

The pinned release is the worst of the three. Thirteen of its fourteen tools emit an
`inputSchema` of literally `{"$schema": "http://json-schema.org/draft-07/schema#"}` — no
`type`, no `properties`. That is exactly the error Cowork reported, at exactly
`tools[0].inputSchema.type`. Restarting Claude will not fix this bridge.

The `fs-server.sh` pin comment reached the opposite conclusion because the 2026-09-13
measurement read **outputSchema** dialects only. On that axis 2025.8.21 is clean — it has
no output schemas at all. The breakage is on the input side, which was never measured.

**Root cause**, measured the same day: the package declares `zod-to-json-schema ^3.23.5`
and no `zod` of its own, so npx resolves zod 4.x transitively through
`@modelcontextprotocol/sdk` 1.30.0. `zod-to-json-schema@3` cannot read zod 4 internals and
silently emits an empty schema.

```
server-filesystem: 2025.8.21    zod: 4.6.5    zod-to-json-schema: 3.25.2
```

Installing the same version with an npm `overrides` of `zod` to `^3.25.0` restores complete
schemas on all 14 tools:

```
zod: 3.25.76   tools=14  missing-type=0  input-draft07=13
tools[0].inputSchema: { "type": "object", "properties": { "path": {...} },
                        "required": ["path"], "$schema": "...draft-07..." }
```

Structurally valid, still labelled draft-07. **Whether Cowork refuses a well-formed
draft-07 schema has not been verified on this machine** — the 2026-09-13 note asserts it,
and nothing here tests it. That is the remaining unknown for this bridge.

`install_check.py` now handshakes 8931 and 8932 and reports both faults, so this is caught
at check time rather than at first tool call. Against the current pin it correctly fails:

```
PASS  8932 Filesystem: stdio handshake   secure-filesystem-server 0.2.0, 14 tool(s)
FAIL  8932 Filesystem: tool schemas      read_file.inputSchema has no type:object (empty schema)
```

## Step 4 — build the macOS plugin — BUILT (not yet uploaded into Claude)

Built on the Mac through `aor-batch-exec` (`CommandJobs/mac-evidence-build-plugin.sh`).
Transcript: `Outputs/Mac Evidence 2026-09-15/build-plugin-macos-20260914-223919.txt`.

```
host:   Darwin 25.6.0 arm64 / macOS 26.6.2
commit: 6cfc77c main
python: Python 3.14.7

BUILD_PLUGIN_SELFTEST: OK - 55 of 55 cases passed

10 skill(s) selected
OK    10 skill(s), 50 file(s), 238 KB
OK    Outputs/Skills Plugin/agent-of-record-skills-macos.plugin
```

Matches the handoff's claim for the macOS plugin exactly — 10 skills, 50 files, 238 KB —
and `build_plugin_selftest.py` reproduced 55/55 on Darwin/Python 3.14.7, having only been
run on Windows before.

Artifact verified independently of the builder:

```
entries: 50
manifest present: True
skills: 10
  command-bridge, dream-cycle, gamma-tango, git-bridge, local-file-bridge,
  not-a-robot, persistent-memory, playwright-skill, self-improvement, skill-menu
zip integrity: OK
plugin.json: agent-of-record-skills 0.4.0
```

The documented command from `docs/install/claude-cowork-mac.md` —
`python3 scripts/build_plugin.py --strict --platform macos` — also passes, producing the
same artifact. `release_check.py` was run on Darwin as a pre-commit gate and returned
`RELEASE_CHECK: CLEAN (24 checks)`, matching the Windows post-merge figure in the handoff.

### The install instruction on the install pages is wrong

`docs/install/claude-cowork-mac.md:225` said "Open
`Outputs/Skills Plugin/agent-of-record-skills-macos.plugin` in Claude, accept it", and
`build_plugin.py` printed the same line after every build. Opening the file does not work:

```
$ open "Outputs/Skills Plugin/agent-of-record-skills-macos.plugin"
handler: kMDItemContentType = "dyn.ah62d4rv4ge81a5dzq7y06"
No application knows how to open URL ...agent-of-record-skills-macos.plugin
(Error Domain=NSOSStatusErrorDomain Code=-10814 "kLSApplicationNotFoundErr")
```

Claude 1.52386.3 declares `CFBundleDocumentTypes` for `.dxt`/`.mcpb` (Desktop Extension)
and `.skill` (Skill File), but nothing for `.plugin`, so macOS assigns the dynamic UTI
`dyn.ah62d4rv4ge81a5dzq7y06` and Finder has no handler. A double-click fails the same way.

The install path is the app's own picker: **Customize -> Plugins -> Add -> Upload plugin**.
The file is uploaded, not opened. The install pages, the quickstart and the
`build_plugin.py` epilogue have been corrected to say so.

So the artifact is built and verified, but **not installed**.


---

## Status against the handoff

| Step | State |
|---|---|
| 1. Pull `main` at `6cfc77c` | DONE |
| 2. `install_check.py --route local` | DONE — CLEAN on Darwin |
| 3. One tool on each of the three bridges | 2 of 3 PASS; `aor-filesystem` broken, pin does not fix it |
| 4. Build + install `agent-of-record-skills-macos.plugin` | BUILT and verified; upload via Customize -> Plugins -> Add -> Upload plugin |
| 5. Restart Claude, `ListSkills` returns ten skills | NOT DONE |

The install pages cannot move from "not yet operated" to operated yet. What remains:

1. Upload the built `.plugin` through **Customize -> Plugins -> Add -> Upload plugin**.
2. Restart Claude and confirm `ListSkills` returns all ten skills.
3. `aor-filesystem` stays broken regardless. Fixing it means controlling the dependency
   tree instead of handing npx a version string — an npm `overrides` of `zod` to `^3.25.0`
   is measured to restore complete schemas, but whether Cowork then accepts a well-formed
   draft-07 schema is untested.

Steps 1 and 2 are enough to move the install pages to operated for the skills plugin. The
filesystem bridge needs its own fix and its own evidence.

### Housekeeping observed, not acted on

- `git fetch` left 77 stray `.git/objects/tmp_obj_*` files; removed.
- `~/agent-of-record` contains duplicate-suffixed siblings — `.git 2`, `CoworkConfig 2`,
  `examples 2`, `Startup 2` — the usual cloud-sync collision artifacts. Left alone.
- This clone had never pushed: `credential.helper` was `osxkeychain` with no github.com
  credential and no `gh`. Now pushes over SSH; `origin` was switched from the HTTPS remote to the SSH one.
- Neither Homebrew nor `gh` is installed on this Mac.
- `playwright-output/` was untracked and not ignored; the browser bridge writes into it on
  every snapshot. Added to `.gitignore`.
- The `aor-batch-exec` operating-rules block returned with each job is still Windows-only
  (`cmd`, `.bat` CRLF, `reg query HKCU\Environment`). Correct per the design note that
  `SKILL-LESSONS` blocks are operator history and excluded from the portability scan, but
  on a Mac every rule in it is inapplicable.
