# Setup on macOS and Linux — retired

This page described the **hosted route** on a Mac: `supergateway`, a dev tunnel, a Ports
panel, a connector package, and several bridges started by VS Code tasks.

That route no longer exists on macOS, for two independent reasons:

- **Copilot Cowork is Windows only.** It is the only product that uses the hosted route, so
  a macOS hosted route had no client.
- **Claude Cowork runs on the machine.** It starts each MCP server itself over stdio, so
  there is no tunnel, no port to forward, no connector package and no launchd job.

As of 2026-09-15 exactly one bridge runs on macOS — the approved command executor — and it
is registered by Claude Cowork directly.

**Use [Claude Cowork on a Mac](install/claude-cowork-mac.md) instead.** For the quickest
path, [the quickstart](install/claude-cowork-mac-quickstart.md).

For the Windows hosted route, see [`docs/setup.md`](setup.md).
