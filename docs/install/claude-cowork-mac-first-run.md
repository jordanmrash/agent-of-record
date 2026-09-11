# Claude Cowork on a Mac: the first-run record

> **What this is.** The record of the first attempt to follow
> [claude-cowork-mac.md](claude-cowork-mac.md) on a Mac someone uses, kept as it was written
> that day. Its reading of the cause ("a local session is required") was revised afterwards
> and is **not** the current view; the status note at the top of the Mac page says what is
> and is not known, and `Startup/posix/install-mac.sh` exists because of what this run found.
> Two things in it are still open: whether a fresh install can start a local session at all,
> and whether the plugin's server failed to spawn (the launcher could not find `node` under
> the PATH a desktop app passes) or was never started. `install-mac.sh --verify` reads the
> desktop app's own logs to tell those apart.

---

# agent-of-record — Claude Cowork (Mac) install attempt, 2026-09-11

**Result: blocked before the executor bridge could be called from a normal Cowork chat.**
Everything up through installing a working local MCP server succeeded. The step that
failed is Cowork actually connecting that server's tools inside a chat session — and the
failure is reproducible and specific enough to describe exactly.

This was run against `main` @ `8fade1b` (tag `v0.3.1`), following
`docs/install/claude-cowork-mac.md`.

---

## Environment

| | |
|---|---|
| Device | MacBook Air, macOS (darwin, arm64) |
| Claude desktop app | version 1.49585.0 → updated mid-session to 1.52386.0 (Electron 44.2.0) |
| Node (reported by the app) | v24.20.0 |
| Repo location | `~/Documents/agent-of-record` |
| Assistant | Claude (Cowork), operating via a cloud session linked to the Mac through the desktop app's device bridge |

**Important caveat on "operated on a Mac."** All shell validation below (`release_check.py`,
`install_check.py`, etc.) ran through Cowork's device-bridge shell, which the app itself
describes as an isolated Linux VM on the Mac — not the real macOS Terminal. This is the
same isolation `docs/install/claude-cowork-mac.md` already describes for Cowork's native
shell. So this round of testing is real progress but still doesn't satisfy "someone ran it in
an actual Mac terminal."

GitHub and the npm registry were both unreachable from that sandboxed shell (`403` from a
proxy on `git clone` and on `npx`), so the repo was transferred in via the device bridge's
file-commit mechanism instead of a direct clone, and the optional Playwright/filesystem
bridges' first-run `npx` fetch could not be tested at all. Neither is a repo bug — both are
sandbox network restrictions specific to this assistant's environment.

---

## What was validated successfully

```
$ python3 scripts/release_check.py
...
PASS  self-test: exec_bridge_selftest.py     0.1s  EXEC_SELFTEST: OK - 40 of 40 cases passed on POSIX
RELEASE_CHECK: CLEAN (22 checks)
```

```
$ python3 scripts/install_check.py --route local --json install-results.json
...
PASS  8933 Command: stdio handshake               cowork-batch-exec 1.3.0, 1 tool(s)
PASS  8934 Power Automate: stdio handshake         cowork-power-automate 0.5.0, 29 tool(s)
...
INSTALL_CHECK: CLEAN (21 passed, 4 skipped)
```

Both own-code bridges (8933 executor, 8934 Power Automate) completed a real, live stdio
MCP handshake. Execute bits on `Startup/posix/*.sh` were already correct (preserved
through the transfer). `cowork-env.sh` was created from the template and left at defaults,
since this route keeps the corpus in-repo (`COWORK_CONFIG_ROOT` unset), per the doc.

## A doc/content issue found along the way (not yet acted on)

`CoworkConfig/Skills/self-improvement/SKILL.md` is described in
`docs/install/claude-cowork-mac.md` as host-agnostic ("its scripts are host-agnostic").
That's true of the Python scripts, but **not** of the SKILL.md prose itself — its
"Environment facts" and "Reading and writing it" sections hardcode OneDrive paths, `.bat`,
`C:\Users\YOURUSER`, and "the 8932 bridge." Uploading it as-is to a Claude Cowork session
would hand it wrong operating instructions. None of the 11 skills were uploaded for this
reason; that host-adapter pass (tracked as issue #6 for the *bridge* skills) apparently
needs to cover `self-improvement` too, not just the bridge-named skills.

---

## Where it actually broke: registering and reaching the executor from a chat

### 1. The documented "Option B — by hand" path doesn't exist as described

`docs/install/claude-cowork-mac.md` step 6 says to add the executor "as a **stdio** server"
in the host's connector settings. In the current app, Customize → Connectors → Add only
offers:

- **Name**
- **MCP server URL** — "The HTTPS address where the server accepts MCP requests"

There is no field for a local command/launcher path. This dialog is for remote MCP
servers only.

### 2. Cowork Plugins *do* support a local stdio command — so a plugin was built instead

Customize → Plugins → Add → **Upload plugin** accepts a `.plugin` package containing a
`.mcp.json` with a `stdio` server definition (`command` + `args`). This isn't documented
anywhere in `docs/install/claude-cowork*.md` as a route, but it's the one place in the
current UI that accepts a local command.

Built and installed `agent-of-record-executor` v0.1.0:

**`.claude-plugin/plugin.json`**
```json
{
  "name": "agent-of-record-executor",
  "version": "0.1.0",
  "description": "Runs the agent-of-record repo's approved batch executor as a local MCP server, so Cowork can execute pre-written, human-approved .sh scripts on this Mac.",
  "author": {
    "name": "Jordan Rash"
  }
}
```

**`.mcp.json`**
```json
{
  "mcpServers": {
    "cowork-batch-exec": {
      "command": "bash",
      "args": ["${HOME}/Documents/agent-of-record/Startup/posix/exec-server.sh"]
    }
  }
}
```

This installed cleanly (Customize → Plugins → Yours shows it as **Installed**, toggle
**on**, `0.1.0`, one connector listed: `cowork-batch-exec`).

### 3. The plugin's MCP server never actually connects in a chat

A test job was placed at `CommandJobs/test-executor.sh`:

```bash
#!/bin/bash
# COWORK_OUTPUT: ../Outputs/2026-09-11 - Executor Test
set -euo pipefail

echo "Hello from the real Mac shell, via the agent-of-record executor."
echo "Running as: $(whoami)"
echo "Working directory: $(pwd)"
echo "Date: $(date)"
echo "This proves the executor plugin reaches your actual machine, not a sandboxed VM."

echo "executor test ran ok at $(date)" > "$COWORK_JOB_OUTPUT/result.txt"
```

Two separate, brand-new Cowork chats were asked to read that file and call
`run_batch_file`. **In both, the tool did not exist.** The second attempt was explicit
about checking why, and reported back verbatim:

> "`agent-of-record-executor` shows up as an enabled plugin, but it isn't among the
> actually-connected MCP servers in this session (only Google Calendar, Google Drive, and
> the standard remote-devices/memory/chrome servers are connected)."

It also confirmed the plugin appears under "Your installed plugins" as **Installed**, and
that refreshing MCP tools didn't surface it either.

### Why, per Anthropic's own current docs

This was checked directly against `support.claude.com` on 2026-09-11 (not just inferred
from this repo's docs):

- [Claude Cowork architecture overview](https://support.claude.com/en/articles/14479288-claude-cowork-architecture-overview) — "Cowork sessions run in the cloud by default: the agent loop and code execution run on Anthropic's servers." Local MCP servers run natively only in a **local session**; in a cloud session they do not run at all.
- [Use Claude Cowork on web, desktop, and mobile](https://support.claude.com/en/articles/15520349-use-claude-cowork-on-web-desktop-and-mobile) — "Local connectors and plugins that include local MCP servers work through the desktop app only" — a distinct category from the cloud-session file/browser bridge.

Both new chats used to test this were ordinary Cowork chats — the same kind this whole
session ran as — which is, per the above, a cloud session. The plugin's `.mcp.json`
stdio server is exactly the "plugin-bundled local MCP server" category these docs say
needs a local session. That matches, exactly, what was observed: correctly installed,
correctly enabled, never connected.

**Unresolved at the point this report was written:** whether there's an app/account-level
"local execution" or "developer mode" setting (separate from installing the plugin) that
would change this. Jordan was in the middle of checking Settings for one when this
session's connection to the device dropped and work shifted to writing this report up.
Worth checking before concluding the route is fully blocked — but as of now, no such
toggle had been found, and nothing in `docs/install/claude-cowork-mac.md` mentions one.

---

## Net finding for the repo

`docs/install/claude-cowork-mac.md` currently reads "not yet operated." A more precise
status, as of this session:

- Repo validates clean on the target platform (with the Linux-VM-not-real-Darwin caveat above).
- The executor's own stdio handshake works (`install_check.py --route local`).
- The doc's registration instructions ("Option B — by hand," a stdio connector) do not
  match the current app UI — there is no local-command connector field, only a
  remote-URL one.
- A plugin-based workaround can be installed successfully.
- That workaround's local MCP server does not connect inside a normal Cowork chat, which
  — per Anthropic's current documentation — is because normal chats are cloud sessions,
  and local/plugin-bundled MCP servers require a local session. Whether Claude Cowork's
  UI currently exposes a way to start a local session (as opposed to a cloud session with
  a device bridge) is the open question this report ends on.

## Suggested next steps

1. Confirm whether a "local session" is reachable at all from the current Cowork UI for a
   personal (non-managed) account, and if so, how it's started.
2. If it isn't reachable yet, `docs/install/claude-cowork-mac.md` probably needs a stronger
   caveat than "not yet operated" — closer to "the required component cannot currently be
   reached from this host's standard chat interface."
3. Separately: the `self-improvement` SKILL.md prose needs the same host-adapter pass
   already planned (issue #6) for the bridge-named skills.
4. If/when a local session is confirmed reachable, retest with the plugin above (or the
   originally-documented raw connector registration, if that field reappears in a future
   app version).
