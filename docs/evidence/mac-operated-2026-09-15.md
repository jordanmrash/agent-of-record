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

### `aor-filesystem` — known failure, fix already in `6cfc77c`, clears on restart

First call returned a client-side schema rejection; the server then reported `failed`:

```
Invalid result for tools/list: [{ "code": "invalid_value", "values": ["object"],
  "path": ["tools", 0, "inputSchema", "type"], ... }]
```

This is exactly the draft-07 failure that the header comment in
`Startup/posix/fs-server.sh` documents, and that `FS_SERVER_VERSION=2025.8.21` pins
against. That pin lands **only in `6cfc77c`** — `git show fa7473b:Startup/posix/fs-server.sh`
has no pin at all. The server process Claude is currently running was started from the
pre-pin launcher, so `npx` fetched a recent `@modelcontextprotocol/server-filesystem`
with draft-07 output schemas on all 14 tools.

So this is not a defect in `main`; it is the pre-pin launcher still resident in memory.
The pinned `fs-server.sh` is now on disk and will be used at the next Claude restart —
the same restart step 5 already requires. **Re-run step 3 for `aor-filesystem` after that
restart before calling this bridge operated.**

Related gap worth noting: `install_check.py` SKIPs the 8931/8932 stdio handshakes, so a
CLEAN install check cannot catch this class of failure. The `fs-server.sh` comment already
says why it is dangerous — "the handshake passing is what makes it dangerous: nothing looks
wrong until a tool is used" — and in this case not even the handshake was checked.

## Step 4 — build the macOS plugin — BUILT (not yet accepted in Claude)

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

### The install page's instruction does not work on this Mac

`docs/install/claude-cowork-mac.md:225` says "Open
`Outputs/Skills Plugin/agent-of-record-skills-macos.plugin` in Claude, accept it", and
`build_plugin.py` prints the same line after every build. On this machine that is not
possible: no application claims the `.plugin` extension.

```
$ open "Outputs/Skills Plugin/agent-of-record-skills-macos.plugin"
handler: kMDItemContentType = "dyn.ah62d4rv4ge81a5dzq7y06"
No application knows how to open URL ...agent-of-record-skills-macos.plugin
(Error Domain=NSOSStatusErrorDomain Code=-10814 "kLSApplicationNotFoundErr:
 E.g. no application claims the file")
```

`dyn.ah62d4rv4ge81a5dzq7y06` is the dynamic UTI macOS assigns an extension it has no
declaration for — Claude has not registered a document type for `.plugin`. A Finder
double-click fails the same way. The real install gesture on macOS therefore has to be
something other than "open the file"; it has not been established here, and the install
page and the `build_plugin.py` epilogue both need correcting once it is.

So the artifact is built and verified, but **not installed**.


---

## Status against the handoff

| Step | State |
|---|---|
| 1. Pull `main` at `6cfc77c` | DONE |
| 2. `install_check.py --route local` | DONE — CLEAN on Darwin |
| 3. One tool on each of the three bridges | 2 of 3 PASS; `aor-filesystem` blocked on restart |
| 4. Build + install `agent-of-record-skills-macos.plugin` | BUILT and verified; install gesture unknown on macOS |
| 5. Restart Claude, `ListSkills` returns ten skills | NOT DONE |

The install pages cannot move from "not yet operated" to operated yet. What remains is the
in-app accept of the built plugin, the Claude restart, and then two post-restart checks:
`ListSkills` returning ten skills, and one `aor-filesystem` tool call succeeding.

### Housekeeping observed, not acted on

- `git fetch` left 77 stray `.git/objects/tmp_obj_*` files; removed.
- `~/agent-of-record` contains duplicate-suffixed siblings — `.git 2`, `CoworkConfig 2`,
  `examples 2`, `Startup 2` — the usual cloud-sync collision artifacts. Left alone.
- This clone has never pushed: `credential.helper` is `osxkeychain` but holds no
  github.com credential, and `gh` is not installed, so the evidence commit is local only.
- `playwright-output/` was untracked and not ignored; the browser bridge writes into it on
  every snapshot. Added to `.gitignore`.
- The `aor-batch-exec` operating-rules block returned with each job is still Windows-only
  (`cmd`, `.bat` CRLF, `reg query HKCU\Environment`). Correct per the design note that
  `SKILL-LESSONS` blocks are operator history and excluded from the portability scan, but
  on a Mac every rule in it is inapplicable.
