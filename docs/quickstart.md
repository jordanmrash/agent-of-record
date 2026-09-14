# Quick Start

This page validates the published snapshot and runs the demonstration. To
install the bridges and the configuration, start at [Choose your route](install/README.md):
Copilot Cowork follows [Setup from zero](setup.md) on Windows or
[Setup on macOS and Linux](setup-macos.md) on a Mac; Claude Cowork, which runs on the
machine and needs no tunnel, follows [Claude Cowork on a Windows PC](install/claude-cowork-windows.md)
or [Claude Cowork on a Mac](install/claude-cowork-mac.md) and installs only the executor.

## Read the foundation first

This repository contains software capable of acting with the signed-in user's authority. Do not begin by running the bridges.

1. Read `SECURITY.md`.
2. Read `docs/architecture.md`.
3. Read `Startup/CommandBridge/README.txt`.
4. Review every placeholder and local path.
5. Use a test environment and test account.

## Validate the published snapshot

Python 3.10+ and Node are required.

```bash
python scripts/public_scan.py
python scripts/release_check.py --json release-results.json
node --check Startup/CommandBridge/batch-exec-server.js
node --check Startup/FlowBridge/flow-mcp-server.js
```

The checks should exit zero. The release check runs the live integrity checks, the cross-surface bridge facts check, the synthetic control-loop demonstration, and thirteen negative-control self-test suites. `--json` writes the same results to a file; CI runs the gate on Windows and macOS for every push and pull request and publishes one results file per platform as a build artifact.

## Run the demonstration

```bash
python examples/synthetic-control-loop/run.py
```

A missing required input becomes a hard stop, and a delivered rule is judged against a control by the real verification harness. It needs nothing but Python and runs in about a second.

## Configure the Power Automate example

1. Copy `Startup/FlowBridge/flow-bridge.config.example.json` to `flow-bridge.config.json`.
2. Replace every placeholder.
3. Keep production environments read-only and outside `allow_prod` until separately reviewed.
4. Keep `allow_delete` false until deletion behavior has been tested.
5. Store the token cache outside the repository.

The real configuration is intentionally gitignored.

## Configure local paths

`scripts/copilot/personalize.py` replaces the placeholders in the operating trees in one
pass - `C:\Users\YOURUSER\...`, the OneDrive folder name, `YOUR-TUNNEL-HOST`,
and the shared placeholder app id in the connector packages. It is a dry run
until `--apply` is passed and prints every file it changes. It does not touch
the Power Automate placeholders (`yourorg.crm.dynamics.com`, the zero tenant
GUID), which belong in the gitignored `flow-bridge.config.json`.

A personalized tree fails `scripts/public_scan.py` by design. Do not commit it to
anything public.

## Understand the command bridge before use

The bridge does not make arbitrary execution safe. It narrows the interface so the person can review the exact batch file before it runs.

Treat write access to `CommandJobs` as execute access.

## Read the walkthrough

`examples/synthetic-control-loop/README.md` explains what the demonstration runs and how each file maps to the architecture.

## What not to do

- Do not expose a real tunnel host in a repository.
- Do not use a production browser profile for experimentation.
- Do not enable Power Automate writes broadly.
- Do not treat a successful self-test as professional validation of an applied workflow.
- Do not copy client, firm, tenant, or engagement material into the public tree.
