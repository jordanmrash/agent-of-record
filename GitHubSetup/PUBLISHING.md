# Publishing Agent of Record

This document describes how the public repository is produced. It is the procedure, not a plan.

## Repository purpose

`agent-of-record` is a public reference implementation for governed AI agents doing work a person signs their name to, built and operated in public accounting. The current release is the foundation layer: memory, approval-gated execution, operational learning, behavioral verification, auditability, and clean-room publication. Applied accounting skills are added later as independently tested components.

## Publication model

**From v0.3.0: `main` keeps its history.** Changes arrive as pull requests, pass
the gate on Windows and macOS in CI, and merge after review by the owner named
in `.github/CODEOWNERS`. A release is a tag on `main` plus a GitHub release
whose notes are that version's `CHANGELOG.md` section. Nothing is force-pushed.

**Through v0.3.0 the model was different**, and the tooling for it remains here.
The private working repository was never pushed - its history had held
non-public material, and a later deletion does not remove a path from prior
commits - so the public repository was rebuilt on each publication as a
disposable one-commit snapshot:

1. Copy explicitly included folders into a new directory.
2. Exclude non-public skills, outputs, logs, local configuration, and staging files.
3. Apply local substitutions to contents, filenames, and folder names.
4. Copy public repository templates.
5. Regenerate generated skill-control blocks.
6. Scan the built tree.
7. Run the repository release checks.
8. Initialize one commit and push with `--force-with-lease`.

That procedure is still the way to produce a clean public tree from a private
working copy if one is ever needed again. It is no longer how `main` is updated,
and the history before the `v0.3.0` tag is the series of roots it produced.

## Public repository files

The public layer includes:

- Root governance and contribution files.
- `.github` CI and issue configuration.
- `docs` public-accounting vision, control map, architecture, evidence, roadmap, limitations, and writing.
- `examples` synthetic demonstrations.
- `scripts` public disclosure and release checks.
- Anonymized Startup, CommandJobs, CoworkConfig, and GitHubSetup implementation files.

## Local-only files

The following never enter the repository:

- `denylist.local.txt`
- `sanitize.local.txt`
- `allow.local.txt`
- `excludes.local.txt`
- `flow-bridge.config.json`
- Token caches, credentials, logs, output, receipts, and commit-message files

The `*.local.example.txt` files document the formats without carrying real values.

## Releasing from `main`

1. Open a pull request. CI runs `release_check.py` on `windows-latest` and
   `macos-latest`; both must be green. `CHANGELOG.md` gains the version's
   section and `CITATION.cff` its version in the same pull request.
2. Merge after review.
3. On the merge commit: `git tag -a vX.Y.Z -m "..."`, push the tag, and create
   the GitHub release with the changelog section as its notes.
4. **Fresh-clone audit.** Clone the repository from GitHub into a temporary
   folder and run `python scripts/release_check.py` there. This proves that what
   is published is what was built; a prior release was edited in the published
   tree without the build source being updated, and a later rebuild silently
   reverted it.
5. Close the milestone; move anything unfinished to the next one.

## Rebuilding a clean tree (legacy)

Only when a fresh public tree must be produced from a private working copy. On
the Windows machine:

1. Run the source preflight scan.
2. Run the build dry run.
3. Run the apply build.
4. Run the built-tree scan.
5. Review the name-shape scans and prose sweep.
6. From the built tree run:

```text
python scripts/public_scan.py
python scripts/release_check.py
node --check Startup/CommandBridge/batch-exec-server.js
node --check Startup/FlowBridge/flow-mcp-server.js
```

## GitHub settings

- Description: `A governed foundation for AI agents doing work a person signs their name to, built and operated in public accounting: durable memory, human-approved execution, behavioral learning, and auditable automation.`
- Topics: `public-accounting`, `accounting`, `ai-agents`, `ai-governance`, `agent-memory`, `behavioral-testing`, `mcp`, `mcp-server`, `microsoft-365-copilot`, `power-automate`, `tax-technology`, `human-in-the-loop`, `enterprise-ai`
- Homepage: the most recent published article on the learning architecture.
- Enable Issues, Discussions, secret scanning, push protection, Dependabot alerts, and private vulnerability reporting.
- Protect `main`: require a pull request with one approving review, require the `gate (windows-latest)` and `gate (macos-latest)` status checks, require linear history and conversation resolution, and **disallow force pushes and deletions**. Force pushes were allowed through v0.3.0 for the snapshot model; that ended with the model.

## Release gate

A release is ready only when:

- Public scan exits zero.
- Release check exits zero.
- Both own-code MCP servers parse.
- No local-list or real configuration file exists in the built tree.
- The README measurements match the release output.
- `scripts/facts_check.py` passes, so every surface states the same bridge facts, including the four connector packages.
- `scripts/personalize_selftest.py` passes, so an operator can personalize the tree and the scan still refuses the result.
- `examples/synthetic-control-loop/run.py` exits zero, so the demonstration runs on a clean checkout.
- The synthetic example contains no real person, firm, client, tenant, or system data.
- CHANGELOG and version metadata are current.
