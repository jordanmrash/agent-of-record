# Quick Start

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
python scripts/release_check.py
node --check Startup/CommandBridge/batch-exec-server.js
node --check Startup/FlowBridge/flow-mcp-server.js
```

The checks should exit zero. The release check runs the live integrity checks and ten negative-control self-test suites.

## Configure the Power Automate example

1. Copy `Startup/FlowBridge/flow-bridge.config.example.json` to `flow-bridge.config.json`.
2. Replace every placeholder.
3. Keep production environments read-only and outside `allow_prod` until separately reviewed.
4. Keep `allow_delete` false until deletion behavior has been tested.
5. Store the token cache outside the repository.

The real configuration is intentionally gitignored.

## Configure local paths

Replace:

- `C:\Users\YOURUSER\...`
- `YOUR-TUNNEL-HOST`
- `you@example.com`
- zero GUID placeholders
- `yourorg.crm.dynamics.com`

Do not commit the resulting local configuration.

## Understand the command bridge before use

The bridge does not make arbitrary execution safe. It narrows the interface so the person can review the exact batch file before it runs.

Treat write access to `CommandJobs` as execute access.

## Run a synthetic walkthrough

Read `examples/synthetic-control-loop/README.md`. It demonstrates the learning and verification architecture without accessing a real accounting process or system.

## What not to do

- Do not expose a real tunnel host in a repository.
- Do not use a production browser profile for experimentation.
- Do not enable Power Automate writes broadly.
- Do not treat a successful self-test as professional validation of an applied workflow.
- Do not copy client, firm, tenant, or engagement material into the public tree.
