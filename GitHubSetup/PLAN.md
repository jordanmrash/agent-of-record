# Publishing Agent of Record

## Repository purpose

`agent-of-record` is a public reference implementation for governed AI agents in public accounting. The current release is the foundation layer: memory, approval-gated execution, operational learning, behavioral verification, auditability, and clean-room publication. Applied accounting skills are added later as independently tested components.

## Publication model

The private working repository is never pushed. Its history has held non-public material, and a later deletion does not remove a path from prior commits.

The public repository is rebuilt as a disposable one-commit snapshot:

1. Copy explicitly included folders into a new directory.
2. Exclude non-public skills, outputs, logs, local configuration, and staging files.
3. Apply local substitutions to contents, filenames, and folder names.
4. Copy public repository templates.
5. Regenerate generated skill-control blocks.
6. Scan the built tree.
7. Run the repository release checks.
8. Initialize one commit and push with `--force-with-lease` on later publications.

## Public repository files

The public layer includes:

- Root governance and contribution files.
- `.github` CI and issue configuration.
- `docs` public-accounting vision, control map, architecture, evidence, roadmap, limitations, writing, and article roadmap.
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

## Build

On the Windows machine:

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

7. Confirm the repository has exactly one commit.
8. Push the first snapshot normally; later snapshots use `git push --force-with-lease origin main`.

## GitHub settings

- Description: `A governed foundation for AI agents in public accounting: memory, human-approved execution, behavioral learning, and auditable automation.`
- Topics: `public-accounting`, `accounting`, `ai-agents`, `microsoft-365-copilot`, `mcp`, `agent-memory`, `ai-governance`, `power-automate`, `behavioral-testing`, `tax-technology`
- Enable Issues, Discussions, secret scanning, push protection, Dependabot alerts, and private vulnerability reporting.
- Protect `main`; allow maintainer force pushes because the publication history is intentionally rebuilt.

## Release gate

A release is ready only when:

- Public scan exits zero.
- Release check exits zero.
- Both own-code MCP servers parse.
- No local-list or real configuration file exists in the built tree.
- The README measurements match the release output.
- The synthetic example contains no real person, firm, client, tenant, or system data.
- CHANGELOG and version metadata are current.
