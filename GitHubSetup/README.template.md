# README template (retired)

Through v0.3.0 the public tree was rebuilt from a private working copy on each
publication, and this file was the source of its `README.md`. From v0.3.0 `main`
keeps its history and `README.md` is edited there directly, so this template no
longer has a reader. It is kept as this note rather than deleted so that older
links to it still resolve. The one thing it still carries is the bridge table
below, because `scripts/facts_check.py` reads it as a surface and verifies it
against `docs/bridge-facts.json`; keep it identical to the table in `README.md`.

| Port | Bridge | Purpose | Implementation |
|---|---|---|---|
| 8931 | Playwright | Browser automation in a signed-in profile | Upstream `@playwright/mcp`, stateful |
| 8932 | Filesystem | Read and write explicitly named local roots | Upstream filesystem MCP server, stateless |
| 8933 | Approved batch executor | Execute an existing `.bat` or `.cmd` under `CommandJobs` | Own code, stateless |
| 8934 | Power Automate | Flow definitions, runs, connections, solutions, DLP, and ownership | Own code, 29 tools, stateless |
