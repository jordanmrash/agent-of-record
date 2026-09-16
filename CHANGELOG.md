# Changelog

All notable changes to the published repository. Through 0.3.0 each entry
summarized one rebuilt snapshot; from 0.3.0 `main` keeps its history and each
entry summarizes a release.

## 0.3.4 - 2026-09-16

The skills plugin is installable from this repository as a marketplace; closes #21.

- **`CoworkConfig/plugin/` is a real plugin root.** It carries `.claude-plugin/plugin.json` and a
  `skills/` tree, generated from `CoworkConfig/Skills/` by `scripts/build_plugin.py --tree` and
  checked byte for byte by `--check-tree`, which joins the release gate. `CoworkConfig/Skills`
  stays the source of truth; the copy is delivery, regenerated and never edited, the same rule the
  digest and the lesson blocks already follow.
- **The manifest's shipping list moved to `metadata.skills`.** Claude Code ignores fields it does
  not recognise but fails to load a recognised field with the wrong shape, and `skills` is a
  recognised path field; the list of `{name}` objects that lived there would have refused to load
  in place, which is why the upload path worked only because the builder stripped it. `metadata`
  is the schema's free-form object for a plugin's own data. `build_plugin.py` refuses the old
  shape with a message that says where the list now lives, and the packaged manifest is the same
  file with `metadata` removed.
- **`.claude-plugin/marketplace.json` at the root**, one entry, `source: ./CoworkConfig/plugin`.
  In Claude Code: `/plugin marketplace add jordanmrash/agent-of-record` then
  `/plugin install agent-of-record-skills@agent-of-record`. In Claude Cowork the upload of the
  built `.plugin` through Customize → Plugins → Add → Upload plugin remains the documented path;
  neither install has been operated on a real machine yet and the install pages say so.
- **Not verified here:** `claude plugin validate` was not available on the publishing machine.
  The gate's `--check-tree` validates what it can - manifest shape, catalog entry, and that the
  source path is a plugin root containing every shipped skill.
- **The operator-name scan skips the generated tree.** It excludes transcript records by their
  source path; the byte copy of the same records under `CoworkConfig/plugin/skills/` sat at a path
  the exclusion did not name, and the first run of this release failed the local gate on it (3
  lines). The source is scanned and `--check-tree` proves the copy identical, so the copy is skipped
  whole; the self-test plants a copy with a hit and proves it is neither counted nor rewritten by
  `--fix` (12 -> 15 cases).
- **`analyser.approved` is declared LF.** The first CI run of this release failed the Windows gate
  only: `.gitattributes` had no rule for the `.approved` extension, so the Windows runner checked the
  marker out with CRLF in the source and the generated copy alike; `dream_analyze_selftest.py` then
  rewrote the source LF, as it is built to, and the byte-for-byte tree comparison inside
  `build_plugin_selftest.py` saw the copy differ (1 of 72 cases). The macOS gate and the local
  Windows gate passed because their checkouts were already LF. `*.approved text eol=lf` makes the
  checkout canonical on every platform; the failure was reproduced and the fix proven on fresh
  `core.autocrlf=true` clones before the fix was pushed.
- `CITATION.cff` 0.3.4. The skills plugin stays at 0.6.1: no skill changed.

## 0.3.3 - 2026-09-15

Housekeeping after the 2026-09-15 public validation - a fresh clone of `73eedf4`, the GitHub API,
the gate and the demonstration run against it: the published tree now states what its own evidence
records, its measured table is generated, and its operating text no longer names the operator.

- **The Mac cells match the evidence.** `README.md`, `docs/install/README.md`,
  `docs/install/claude-cowork.md` and the two Mac pages said "not yet operated" while
  `docs/evidence/mac-operated-2026-09-15.md` recorded `install_check.py --route local` CLEAN,
  `run_batch_file` on the machine itself and `install-mac.sh --register` retiring the two entries
  the route no longer needs. They now say what happened: executor and install check operated,
  skills-plugin upload not yet confirmed. The Copilot Cowork Mac cell says not supported, which the
  retired `docs/setup-macos.md` already said; the README's bridge section describes the two routes
  as `docs/bridge-facts.json` declares them; the quickstart's "five repository skills" is ten.
- **The measured table is generated, and the gate fails when it is stale.**
  `scripts/measured_table.py` computes every figure from the digest marker, the corpus, the routes,
  the ledger, the tier file and `release_check.py` itself, and writes one block into `README.md` and
  `docs/measured-results.md`; `--check` joins the gate, with a self-test that breaks it. The typed
  tables had drifted: 123 entries and 93 rules against 120 and 94 in the corpus, 13 self-test suites
  against the 15 the gate ran.
- **Operating text no longer names the operator.** `scripts/operator_name_check.py` reads the
  author's given name from `CITATION.cff` and fails the gate on any skill instruction, lesson, digest
  line, job or server text that addresses that person by name outside an attribution block; `--fix`
  rewrote 198 line(s) to "the operator" ("the author" under `docs/`) and the digest, skill and plugin
  blocks were regenerated from the corrected corpus. Rule lines of ledger-verified lessons are kept
  as written and reported, because their text carries a behavioral verdict.
- **Spent jobs archived.** The four dated one-off jobs and the eleven `mac-evidence-*.sh` scripts
  moved to `CommandJobs/archive/`, still runnable by relative path; `CommandJobs/README.txt` points
  at the new location.
- **README restructured, not rewritten.** Badges, a contents line and the runnable demonstration with
  its captured output come first; the article list lives only in `docs/published-writing.md`, which
  gains the 2026-09-11 article, and the applied-skill list only in `docs/roadmap.md`. The skills
  plugin is offered from the release assets with the upload path spelled out.
- **Repository hygiene.** `.github/dependabot.yml` for the pinned npm runtime under `Startup/` and
  the actions CI uses; `CITATION.cff` 0.3.3; skills plugin 0.6.1 for the text changes above; the
  release gate is `RELEASE_CHECK: CLEAN (29 checks)`.
- **Known gap, tracked as #21.** A marketplace-installable layout - `.claude-plugin/marketplace.json`
  at the root pointing at a plugin root that contains `skills/` - needs the skills tree moved or
  generated; `/plugin marketplace add jordanmrash/agent-of-record` does not work yet, and the upload
  path above is the install path.

The Claude Cowork route narrows to the approved command executor, reversing the
three-bridge scope recorded further down this section; every skill ships to every
product, with redundancy documented per configuration instead of resolved by deletion;
the model behind a session may be Claude or a third-party gateway; and the reserved-name
entry the 0.3.2 installer left behind is retired on upgrade.

- **The Claude route is one bridge, `aor-batch-exec`. This reverses three entries below
  from the 2026-09-13/14 work: "Three bridges on a Mac, not one", "`install-mac.sh`
  registers all three bridges" and "the Claude pages and the macOS setup page describe
  three bridges".** Measured on macOS 2026-09-15 (`docs/evidence/mac-operated-2026-09-15.md`):
  Claude Cowork reads and writes connected folders and drives a browser first-party, so
  `aor-filesystem` and `aor-playwright` duplicated the host while adding an `npx` fetch and
  an upstream dependency - and the pinned `server-filesystem@2025.8.21` was unusable there
  regardless: 13 of its 14 tools emit an `inputSchema` carrying only a draft-07 `$schema`,
  which the 2026-09-13 measurement missed by reading output schemas alone. The executor has
  no first-party equivalent - the session's own shell is a sandboxed Linux VM; the executor
  runs natively as the user. `docs/bridge-facts.json` now carries 8931 and 8932 as
  `products: ["copilot"]`, `platforms: ["windows"]`; `Startup/posix/fs-server.sh`,
  `pw-server.sh` and `GO.sh` are removed; `install-mac.sh --register` registers the executor
  only and retires `aor-filesystem` and `aor-playwright` entries that point at this
  repository's launchers. Nothing changes for the Windows hosted route: the `.cmd`
  launchers, `tasks.json`, the connector packages and the watchdog are untouched, and
  Copilot Cowork keeps all four bridges.
- **Every skill ships to every product; redundancy is documented, not deleted.**
  `persistent-memory`, `local-file-bridge`, `playwright-skill`, `git-bridge` and `skill-menu`
  duplicate a host capability in some configurations - account memory, connected folders, the
  built-in browser, git through the executor, the Customize list under Claude Cowork signed in
  to an Anthropic account - and none of it on Copilot Cowork or, until tested, under
  third-party inference where the session is signed out. Each carries a "When this skill is
  redundant" section, `docs/skills-by-configuration.md` holds the matrix, and the person
  disables a skill in the host rather than the repository deleting it. `build_plugin.py
  --product` remains for a narrower build. This supersedes `6e0d58d`, which deleted four of
  the five, and the interim `products: ["copilot"]` scoping.
- **The model behind the session may not be Claude.** Claude Desktop's third-party inference
  mode runs Cowork against a gateway or a local model with the same harness, folders,
  browser, plugins and MCP servers, so the route and the executor are unchanged. The install
  pages carry an addendum: keep `persistent-memory` enabled until account memory is confirmed
  when signed out; a smaller model leans on the enforced controls rather than delivered
  rules; a local model or an approved enterprise gateway keeps data inside the operator's
  boundary. Written on the assumption Windows reaches parity; every claim still needs one
  real call before it is marked operated.
- **Lessons carry optional `Routes:` and `Platforms:` fields; absent means everywhere.**
  The executor filters the operating-rules block it returns with each job by platform, and
  by route when `COWORK_ROUTE` is set (`exec-server.sh` sets `claude`; the Windows launcher
  sets nothing, so Copilot keeps serving every rule). `lesson_check.py` fails on an unknown
  value; `lesson_scope_selftest.py` joins the gate, now `RELEASE_CHECK: CLEAN (25 checks)`.
- **Real-device evidence and two corrected instructions.** `docs/evidence/mac-operated-2026-09-15.md`
  records `run_batch_file`, the install check, the release gate and the plugin build running
  on a Mac through `aor-batch-exec`. A built `.plugin` is installed through Customize >
  Plugins > Add > Upload plugin, never by opening the file. `install_check.py` now
  handshakes every stdio server it can start and reports schema faults instead of skipping.

- **Upgrading from 0.3.2 on a Mac.** The 0.3.2 installer registered the executor
  under the name `cowork-batch-exec`. Claude Desktop reserves the `cowork` prefix
  and refuses that entry at every launch, and because `install-mac.sh` merges
  into `claude_desktop_config.json` rather than replacing it, upgrading alone left
  the dead entry in place. `install-mac.sh --register` now retires it when it
  points at an agent-of-record launcher, prints what it removed, and keeps the
  dated backup it always took. A `cowork-batch-exec` that is not this
  repository's is left alone with a warning. If you registered by hand, remove
  the key yourself. The names are now `aor-batch-exec`, `aor-filesystem` and
  `aor-playwright`.
- **`install-mac.sh` registers all three bridges**, not only the executor, and
  `--verify` reads the desktop app's logs for all three names. Before this a Mac
  user who followed the quickstart ended up with one connector and no sign the
  other two existed.
- **`fs-server.sh` pins `@modelcontextprotocol/server-filesystem@2025.8.21`.**
  Measured across twelve published releases: from 2025.11.25 onward the package
  declares draft-07 output schemas on all 14 tools, and Claude Cowork supports
  JSON Schema 2020-12 only, so an unpinned bridge handshakes, advertises 14 tools
  and fails every call. 2025.8.21 is the last release with no output schemas and
  carries the same 14 tools. `COWORK_FS_SERVER_VERSION` overrides the pin;
  `docs/bridge-facts.json` records it as `posix_package_pin`. The Windows
  launcher stays unpinned: the hosted route accepts draft-07.
- **The Power Automate bridge is Copilot Cowork on Windows only, and the manifest says
  so.** `docs/bridge-facts.json` carries `products` and `platforms` for every bridge and
  no stated count. `facts_check.py` derives the counts, requires a POSIX launcher only for
  a macOS bridge and refuses one on a Windows-only bridge, and checks each Claude and
  macOS surface against the bridges that exist there. `install_check.py` tests only the
  bridges in scope for its route and platform and says how many. `Startup/posix/flow-server.sh`
  is removed, the 8934 task keeps its Windows variant only, and the Claude pages and the
  macOS setup page describe three bridges. `docs/install/README.md` states the supported
  matrix.
- **A skill-install path for Claude Cowork.** `scripts/build_plugin.py` packages
  `CoworkConfig/Skills` into a `.plugin` from the manifest at
  `CoworkConfig/plugin/.claude-plugin/plugin.json`; `--strict` fails when a skill declared
  for macOS carries Windows-only text. The eight bridge, memory and bookend skills still
  do, so they are declared for Windows only and the macOS bundle carries `not-a-robot`
  and `skill-menu`; the rest follow as their text is made platform-correct.
- **The `myvoice` skill leaves the repository.** It describes one person's writing
  register and is not part of the toolkit. It shipped in v0.2.0 through v0.3.2 and stays in
  the history of those tags. The skill set is ten: `command-bridge`, `local-file-bridge`,
  `git-bridge`, `playwright-skill`, `persistent-memory`, `self-improvement`, `dream-cycle`,
  `gamma-tango`, `not-a-robot` and `skill-menu`. Its lesson route is gone too, so
  `skill_lessons.py --check` opens only skills that exist here; the macOS bundle carries
  `not-a-robot` and `skill-menu`.
- **The release gate enforces the plugin manifest.** `release_check.py` runs
  `scripts/build_plugin.py --strict --list` as a check, so a manifest entry with no skill
  directory, or a skill declared for macOS that still carries Windows-only text, fails the
  gate and CI on both platforms instead of failing only when someone builds the plugin by
  hand.
- **The `--strict` matcher fires on the defect it names.** The bridge-port pattern matched
  the digits inside any hyphenated identifier, so a lesson key such as `bridge-8933-arg-name`
  or a route id such as `command-bridge-8933` read as Windows-only text - 71 of the 141 port
  hits across the ten skills, measured. A key is the retrieval mechanism and may never be
  renamed, so no bridge skill could ever have passed. The pattern now matches a port number
  standing in prose and not one embedded in an identifier; the Copilot connector ids, which
  are platform text, are named as their own pattern. `scripts/build_plugin_selftest.py`
  holds the positive and negative controls and joins the gate, which now reports
  `RELEASE_CHECK: CLEAN (24 checks)`.
- **`--strict` measures portability, not the presence of a Windows word.** A skill that is
  correct on both platforms says both - "the job script, `.bat`/`.cmd` on Windows, `.sh` on
  macOS" - and the token heuristic failed exactly those sentences. A Windows-specific token
  is now acceptable where the same table row or prose paragraph names its macOS counterpart;
  one that stands alone is still Windows-only text. The generated `SKILL-LESSONS` block is
  not scanned: it is the operator's record, regenerated from the corpus, and a new install
  starts with an empty corpus. `--list` now reports how many unpaired tokens remain in each
  skill still declared for Windows only. The `devtunnel` pattern gets the identifier guard
  the port pattern got, so a lesson key no longer reads as a platform claim.
- **`persistent-memory` is declared for both platforms.** Its write path names the
  mechanism per host - the filesystem bridge at the OneDrive path under Copilot Cowork on
  Windows, the connected folder's file tools at `<config root>/cowork-memory/` under Claude
  Cowork on either platform - instead of one Windows user-profile path. First of the eight.
- **`git-bridge` is declared for both platforms.** Its mechanics section described one
  host's connector, a Windows user-profile repository root, `.bat` authoring, a CRLF fix job
  and a stripped environment as THE way; the last two were fixed at source in executor 1.3.0.
  It now names the executor by its tool, the job script per platform (`.bat`/`.cmd` on
  Windows, `.sh` on macOS), the tooling root by derivation, and shows the status job in both
  shapes. Second of the eight.
- **`self-improvement` is declared for both platforms.** Its environment facts named one
  host's paths and two traps executor 1.3.0 had already removed; they now name the job
  script, the working directory and the corpus location per platform. Three route titles
  drop their port numbers, so three skills' lessons-block headers regenerate. Where a thing
  is genuinely Windows-only - the Power Automate bridge, a `.bat` verification case - the
  text says so instead of pretending otherwise. Third of the eight.
- **All ten skills are portable.** The last five skills were rewritten by the gate's own
  unit boundaries: every table row or prose paragraph that names a Windows mechanism also
  names its macOS counterpart. The manifest's temporary per-skill `platforms` field is gone;
  an entry now defaults to both platforms, and `build_plugin_selftest.py` scans the ten real
  skill directories and fails if any unpaired unit returns. The macOS and Windows plugin
  builds carry the same ten skills.
- **Claude installs the ten skills from the repository plugin.** Both Claude install
  pages now build the platform-named `.plugin`, open it in the app and verify all ten with
  `ListSkills`; manual one-file uploads and the stale two-skill warning are gone.
- **Hosted-only utilities are scoped to Copilot Cowork on Windows.** The personalizer moves
  to `scripts/copilot/personalize.py`; its self-test follows it. The POSIX port watchdog and
  launchd installer are removed because Claude owns its stdio children and exposes no tunnel
  ports to poll; the Windows Task Scheduler watchdog remains.
- `public_scan.py` scans what git would commit and honours path arguments; the executor
  names itself `aor-batch-exec`; `docs/evidence/README.md` shows the checker command per
  route; two pages stop saying `install-results.json` names your machine; `.DS_Store` is
  ignored.

## 0.3.2 - 2026-09-11

Installable on a Mac in one command, and every POSIX launcher finds its own
runtime rather than assuming the caller's PATH holds one.

- **`Startup/posix/install-mac.sh`** - one command from the macOS Terminal:
  it places the tree, installs Node without sudo when it is missing and pins
  it in `cowork-env.sh`, creates the folders and sets the execute bits, runs
  `release_check.py` and `install_check.py` in a real Terminal rather than an
  agent's shell, completes an MCP handshake under a deliberately minimal PATH,
  registers the executor in `claude_desktop_config.json` behind a dated backup,
  and prints the steps only a person can do. `--verify` reads the desktop app's
  own MCP logs and says whether the server was started; `--register` rewrites
  only the config entry; `--replace` refreshes an existing tree while keeping
  `CommandJobs`, `Outputs` and `cowork-env.sh`.
- **Every POSIX launcher resolves its runtime.** A desktop app that starts a
  launcher as a child process hands it a minimal PATH, which on macOS holds no
  node, so `exec node` or a bare `npx` died with a command-not-found that only
  the host's per-server log recorded. `exec-server.sh`, `pw-server.sh`,
  `fs-server.sh` and `flow-server.sh` now prepend the folders node is installed
  in, honour `COWORK_NODE` from `cowork-env.sh`, resolve `npx` beside a pinned
  node, and exit 127 with a message naming the fix. The facts-check fixture for
  a launcher pointed at the wrong server re-anchors on the new exec line.
- **The Mac page says what the first run measured.** The executor, packaged as
  a plugin because the Connectors dialog takes a remote URL only, installed and
  enabled and never connected in a cloud chat, and the cause is not isolated
  because nothing in that run executed on macOS itself. The page now names the
  three routes that do accept a local stdio server, says to validate in the
  machine's own Terminal because an agent's shell is a Linux VM that proves the
  repository rather than the host, and keeps its `not yet operated` status.
- `docs/install/claude-cowork-mac-quickstart.md`, the short version of that
  page, and `docs/install/claude-cowork-mac-first-run.md`, the record of the
  run itself.
- `CITATION.cff` 0.3.2.

## 0.3.1 - 2026-09-10

Documentation. The pages that still described one host describe both routes,
the counts agree with the shipped corpus, and the release metadata matches
`main` before the repository is linked publicly.

- **Both routes on every architecture page.** The README diagram and its Host
  and Install rows, the `docs/architecture.md` system view and the opening of
  `SECURITY.md` now state the hosted route (Copilot Cowork reaching the bridges
  through a dev tunnel) and the local route (Claude Cowork starting the servers
  as stdio processes) side by side, and the executor's file types read
  `.bat`/`.cmd` on Windows and `.sh` on POSIX wherever they are named.
- `CoworkConfig/README.md` counted 126 shipped lesson entries; the shipped
  corpus has 123, as the README and `docs/measured-results.md` say.
- `docs/measured-results.md` no longer lists as future targets the facts check
  and the consolidated CI runner, both shipped in 0.2.0.
- `dream-cycle` carries the attribution block every other skill carries, as
  `CONTRIBUTING.md` promises for all of them.
- `GitHubSetup/README.template.md`, a stale copy of the README whose
  root-relative links did not resolve from its folder, is reduced to a note plus
  the one table `facts_check.py` still reads from it: `README.md` is edited on
  `main` directly.
- The published-writing lists name the two newest articles.
- `CITATION.cff` 0.3.1.

- **The Claude Cowork route installs only what that host lacks.** Read against
  Anthropic's published description of Claude Cowork: in a local session its
  agent loop is native but every shell command runs in a Linux VM isolated from
  the host, so the approved batch executor is the only path from a session to
  the operating system - and the one required component. Both Claude Cowork
  pages are rewritten around that: the browser and filesystem bridges become
  optional, the package install for `supergateway` (an HTTP wrapper only the
  tunnel route uses) is gone, the pages state that a local desktop session is
  required because local MCP servers do not run in a cloud session, and they
  say what to do with skills, instructions and memory on a host that already
  has a memory. `install_check.py --route local` reports `supergateway` as
  skipped rather than required. Three new pages: `docs/install/README.md`
  (choose your route, with a host-by-host feature matrix),
  `docs/install/copilot-cowork.md` and `docs/install/claude-cowork.md` (what the
  repository adds to each host and what that lets you do). `AGENTS.md`,
  `docs/quickstart.md`, `docs/limitations.md`, `llms.txt`, the README picker and
  the banners on both hosted pages point at them, and the new pages join the
  facts check's stale-phrase surfaces.
- **The executor normalizes script line endings** (`batch-exec-server.js` 1.3.0).
  Before an approved script runs, its line terminators are rewritten in place
  to the platform's convention: an LF-only `.bat`/`.cmd` becomes CRLF on
  Windows, where cmd.exe mis-parses LF-only files silently, and a CRLF `.sh`
  becomes LF on POSIX, where bash rejects the CR. Nothing but the terminators
  changes, a file that already mixes both is left alone, and the result reports
  what happened as `line_endings`. Scripts written by the filesystem bridge
  (LF) no longer need a separate normalizing job before their first run.
- **The executor hands jobs a complete environment.** It is still built by the
  server alone - the MCP caller has no parameter that reaches it - but it now
  carries what an interactive session of the same account would: on Windows the
  profile variables (`USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, `TEMP`,
  `HOMEDRIVE`/`HOMEPATH`, `USERNAME`, the `ProgramFiles` family) derived from
  the account when the launching process lacks them, and the user's PATH from
  `HKCU\Environment` appended to the machine PATH; on POSIX `HOME`, `USER`,
  `LOGNAME` and the conventional user bin directories. A bridge started by the
  scheduled-task watchdog had been handing its jobs empty profile variables and
  the machine PATH only, so per-user tools had to be located by hand inside
  every script. The result reports `user_path_entries`.
- `scripts/exec_bridge_selftest.py` grows from 31 to 40 cases: a script written
  in the other platform's convention runs and is reported normalized, its
  on-disk terminators are checked, a mixed file is proven untouched, and a
  second server started with the profile variables stripped must still hand a
  job every one of them. Run against the 1.2.0 server, seven of the new cases
  fail.
- **The Windows launchers derive their root.** `Startup/*.cmd` compute
  `COWORK_ROOT` from their own location (`%~dp0`), the way `Startup/posix/*.sh`
  already did, so a clone runs from any directory without personalization.
  `exec-server.cmd` creates `CommandJobs` and `Outputs` if the clone did not
  bring them; `fs-server.cmd` passes `%COWORK_ROOT%`, `%USERPROFILE%\Downloads`
  and - only when it is set and exists - `%COWORK_CONFIG_ROOT%`, otherwise it
  says so on stderr and starts with two roots rather than letting the upstream
  server exit on a missing folder. Machine-specific values live in a gitignored
  `Startup/cowork-env.cmd`, documented by `cowork-env.example.cmd`; the file is
  refused by name in `scripts/public_scan.py`, as `cowork-env.sh` is.
- **Roots by variable.** The Windows arguments in `Startup/.vscode/tasks.json`
  (and the KnownGood copy) use `${workspaceFolder}` like the `osx` and `linux`
  overrides; `docs/bridge-facts.json` states the filesystem roots as the launcher
  variables. `scripts/personalize.py` now finds nothing to rewrite in the
  launchers, the task file or the manifest roots - its scope is the watchdog,
  the connector packages, the shipped jobs and the skills. Issue #6, item 5.
- `facts_check.py` enforces the Windows half of the derivation rule: every
  `.cmd` launcher must set `COWORK_ROOT` from `%~dp0` and may not carry a
  `C:\Users\` path, and a filesystem root counts only when it is on the command
  line that starts the server. Two new negative controls, one re-anchored;
  `personalize_selftest.py` now asserts the launchers stay free of account paths
  before and after personalization.
- `docs/setup.md`, `docs/setup-macos.md`, `docs/install/claude-cowork-windows.md`
  and `AGENTS.md` describe the new shape: the hosted route still clones to the
  fixed path because its watchdog and jobs are personalized; a client that
  starts the launchers directly clones anywhere and sets its config root in
  `cowork-env.cmd`.

## 0.3.0 - 2026-09-07

Portable. Runs where the contributor is. 0.2.1 made the tree installable on Windows; this
makes it installable on a Mac, and makes "installed" a thing a machine can
prove rather than a thing a person believes.

- **The command bridge is cross-platform.** `batch-exec-server.js` now runs on
  Windows and POSIX from one source. The platform chooses the shell (`cmd.exe`
  vs `bash`), the executable extension (`.bat`/`.cmd` vs `.sh`), the comment
  marker the `COWORK_OUTPUT` directive hides behind, and how a runaway tree is
  killed. It chooses nothing else: the path validation, the containment checks,
  the single-flight lock and the fixed timeout are one implementation used by
  both. `scripts/exec_bridge_selftest.py` starts the real server as a stdio MCP
  process and tries 31 ways out of it, in the platform's own script language -
  so a refusal that holds on Windows and not on a Mac fails the gate.
- **The server carries no personalized path.** The tooling root comes from
  `COWORK_ROOT`, set by the launcher, and the lessons path from
  `COWORK_CONFIG_ROOT`. Two fewer files the personalizer has to rewrite.
- **POSIX launchers** under `Startup/posix/`, one per bridge, deriving the
  tooling root from their own location - so a clone runs from any directory
  without personalization. Machine-specific values live in a gitignored
  `cowork-env.sh`; `cowork-env.example.sh` documents each one.
- **One task file, two platforms.** `Startup/.vscode/tasks.json` gained `osx`
  and `linux` overrides that point at the POSIX launchers via
  `${workspaceFolder}`. The Windows arguments are unchanged, byte for byte.
- **A launchd watchdog** (`Startup/posix/watchdog/`) with the same contract as
  the Windows one: restart only a port that refuses connections, never kill,
  honour a cooldown, and say plainly that it cannot restore tunnel visibility.
- **`scripts/install_check.py`** - the definition of done for the install
  contract now in `AGENTS.md`. It completes a real stdio MCP handshake against
  each own-code bridge rather than testing that a file exists, checks the pinned
  runtime, enforces the 1024-character skill description cap that silently drops
  a skill, and runs the corpus checks. `--json` writes the evidence.
- **`docs/setup-macos.md`** - the POSIX path from zero, and an explicit table of
  the seven things that differ from Windows.
- **The disclosure scan reads shell scripts.** `.sh`, `.bash` and `.zsh` were
  not in the scanned extension set, so every file added above would have been
  unscanned; a POSIX home-directory pattern (`/Users/...`, `/home/...`) was
  added alongside the Windows one, and `cowork-env.sh` is refused by name. The
  gap was found by running the negative control, not by reading the code.
- `facts_check.py` verifies the POSIX launcher for each bridge, that it derives
  its root rather than hard-coding one, and that the task file actually starts
  it per platform - five new negative controls, 16 of 16 caught.
- **The snapshot model ends with this release.** Through 0.3.0 `main` was one
  commit, force-pushed on each publication from a private working copy. From
  here it keeps its history: changes arrive as pull requests, CI runs the gate on
  `windows-latest` **and** `macos-latest`, and merge needs a review from the
  owner named in `.github/CODEOWNERS`. `CONTRIBUTING.md`, `SECURITY.md`,
  `GitHubSetup/PUBLISHING.md`, `docs/architecture.md` and `docs/limitations.md`
  now describe that model and mark the old one as history. The macOS layer has
  a contributor, and a force-pushed root would have destroyed their fork.
- `docs/evidence/` is the reviewed home for `install_check.py --json` results
  from real machines. The checker now writes the file to be committed: the
  config root and home directory are replaced with placeholders before the
  file is written, so the disclosure scan does not have to catch them after.

## 0.2.1 - 2026-09-07

Installable. The 0.2.0 audit found a reference implementation that could be read
and validated but not stood up: no from-zero guide, placeholders in 65 files with
nothing to replace them, a connector package for one bridge out of four, and a
lessons corpus with no way to start empty. This snapshot closes those four gaps.

- `docs/setup.md`: from a bare Windows PC to four reachable bridges and an
  installed configuration, in twelve steps, each stated from the files in the
  tree rather than from memory. Tenant-dependent steps say so.
- `scripts/personalize.py`: replaces `YOURUSER`, the OneDrive folder name,
  `YOUR-TUNNEL-HOST` and the shared placeholder app id across `Startup/`,
  `CommandJobs/`, `CoworkConfig/` and `docs/bridge-facts.json`; dry run by
  default; leaves the documentation, the publishing tooling and the skill
  attribution lines alone. `scripts/personalize_selftest.py` proves each of
  those properties on a throwaway copy and that `public_scan.py` refuses the
  personalized result; the release gate runs it.
- Connector packages for all four bridges under `Startup/Plugins/` (the 8934
  package moves there from `Startup/FlowBridge/plugin/`). `facts_check.py` now
  verifies each package's connector id against the name the skills address, its
  URL against its port, and that no two personalized packages share an app id -
  three new negative controls in its self-test.
- `CoworkConfig/README.md`: what installs where, which blocks are generated from
  what, and the procedure for starting with an empty corpus - including what the
  checkers report on an empty file and why.
- `GO.bat` and `Startup/README.txt` corrected: the launcher comment still
  described two bridges and two ports.

## 0.2.0 - 2026-09-07

Verification and integrity. Three of the five v0.2 roadmap items ship here; the
other two - behavioral verdicts for ten routed rules, and reduction of duplicated
configuration statements - carry to v0.3.

- Cross-surface bridge facts check (`scripts/facts_check.py`, `docs/bridge-facts.json`):
  one manifest of ports, names, statefulness and roots, verified against the README,
  the Startup README, `tasks.json`, the watchdog and both bridge skills. Wired into
  the release check and CI. Closes #3. On first run it found two stale statements
  in the published skills (a "three bridges" count and a claim that port 8934 did
  not exist); both are corrected in this release.
- Runnable synthetic control loop (`examples/synthetic-control-loop/run.py`): a
  deterministic manifest validator that stops on a missing required segment, then
  the recorded three-arm-plus-control transcripts judged by `verify_delivery.py`
  into a demonstration ledger. No host, tunnel or network required. Wired into the
  release check and CI. Closes #4.
- Machine-readable release results: `release_check.py --json` writes
  `release-results.json`; CI publishes it as a build artifact.
- README: status, platform and host stated in the first screen; the bridges are
  described as standard MCP servers with Cowork as the client they were built
  against. Tagline changed from "proven in" to "built and operated in public
  accounting" to match the evidence table.
- Publication model restored to a single rebuilt commit on `main`; `v0.1.0` re-cut
  as a single commit carrying the released tree minus the editorial roadmap files
  and the links to them, otherwise unchanged.
- Removed: the editorial article roadmap (publishing intent, not documentation);
  `GitHubSetup/public-template/`, a duplicate of `docs/`, `examples/`, `scripts/`
  and `.github/`; `docs/initial-issues.md` (the issues are open on GitHub); the
  Cowork runtime folder notice that shipped as `CoworkConfig/AGENTS.md`.
- Added: root `AGENTS.md` for agents working in this repository;
  `GitHubSetup/PUBLISHING.md` (formerly `PLAN.md`) with current settings; a
  substitution statement for the published lessons corpus in `SECURITY.md`.
- Corrected in `CoworkConfig/Skills`: `git-bridge` no longer states that port 8934
  does not exist and scopes its never-push rule to the working repository;
  `local-file-bridge` counts four bridges and four tasks.

## 0.1.0 - 2026-09-03

Foundation-layer publication.

- Four bridges: Playwright (8931), filesystem (8932), approved batch executor
  (8933, v1.1.0), Power Automate (8934, v0.5.0 with 29 tools and a plugin
  manifest). Watchdog covering all four ports; bounded auto-recovery policy
  with a self-test.
- Eleven skills, each carrying a generated `SKILL-LESSONS` block where lessons
  route to it.
- The self-improvement toolchain: lessons corpus (123 entries), always-on
  digest with tiering, per-surface gate with receipts, job linter, skill and
  plugin lesson delivery, delivery verification (three carried runs plus a
  control), nightly consolidation analyser and measurement, and a self-test for
  every checker.
- Two-tier memory files and their index.
- The publish gate itself (`GitHubSetup/`): preflight scan, clean-room build
  with sanitization of contents and file names, name-shape autoscans, and a
  prose sweep for engagement vocabulary.
- Public-accounting positioning: vision, control map, architecture, measured
  results, limitations, roadmap, and published-writing assessment.
- Synthetic control-loop demonstration showing a missing input becoming a
  hard-stop rule and a behavioral verification case.
- Public repository infrastructure: CI, issue forms, CODEOWNERS, pull-request
  controls, support boundary, citation metadata, and machine-readable
  `llms.txt`.
- One-command public scan and release check.
- Anonymized throughout: account, firm, tenant, environments, tunnel host,
  client and colleague names replaced with placeholders; firm-abbreviated file
  names renamed (`cowork-close.bat`, `deck-builder`).

Withheld from this and every snapshot: engagement-shaped skills, the firm's
brand-standard skill, two memory files describing non-public work, outputs,
logs, local configuration, and the verification jobs that embed the strings
they check for.
