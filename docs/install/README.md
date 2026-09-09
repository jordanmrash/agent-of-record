# Choose your route

The same bridges, jobs, gate and lessons machinery serve two agent hosts. What differs
is how the host reaches the machine and what the host already does on its own — so each
route installs a different subset of this repository. Pick the host you use, read what
the repository adds to it, then follow the page for your platform.

| Host | What the repository adds | Windows PC | Mac |
|---|---|---|---|
| **Copilot Cowork** — runs in Microsoft's cloud, reaches the bridges through a dev tunnel | [What this adds to Copilot Cowork](copilot-cowork.md) | [Setup from zero](../setup.md) · operated daily | [Setup on macOS and Linux](../setup-macos.md) · not yet operated |
| **Claude Cowork** — runs on your machine in a local session, starts the bridges itself | [What this adds to Claude Cowork](claude-cowork.md) | [Claude Cowork on a Windows PC](claude-cowork-windows.md) · not yet operated | [Claude Cowork on a Mac](claude-cowork-mac.md) · not yet operated |

**Not yet operated** means nobody has run that page end to end. If you do, open a pull
request with your `install_check.py` result — that is what flips the status.

The code is not split by host. `Startup/` holds the Windows launchers and the two own-code
servers, `Startup/posix/` the macOS and Linux launchers, and both hosts start the same
files. A route is a choice of *which* launchers to register and *how*, not a second copy
of anything.

## What each host does before this repository is installed

Stated from the vendors' own descriptions, read 2026-09-09: Microsoft's Copilot Cowork
documentation and the operated tenant for the left column; Anthropic's *Claude Cowork
architecture overview* (Help Center), *Claude's memory works everywhere* (blog) and
*Browse skills, connectors, and plugins* (Help Center) for the right. Where a cell says
*expected*, nobody has measured it on a machine yet.

| Capability | Copilot Cowork | Claude Cowork (local desktop session) |
|---|---|---|
| Where the agent runs | Microsoft's cloud, in a per-session Linux container | On the device; shell commands and code Claude writes run in a Linux VM (Hyper-V on Windows, Apple Virtualization on macOS) |
| Reads and writes local files | No path to the machine | Yes — folders the user connects, permission-gated |
| Runs a script on the host OS (`.bat`, `.cmd`, `.sh`, AppleScript) | No | **No.** The VM is Linux and isolated from the host; only a local MCP server reaches the host |
| Starts a local MCP server | No — it can only call an HTTP endpoint it can reach from the cloud | Yes, as a stdio process, in a **local** session only; cloud sessions do not run local MCP servers |
| Browser | Hosted browsing without your sign-ins | Reaches the device's browser through the desktop app *(expected)* |
| Microsoft 365 tenant — mail, calendar, Teams, SharePoint, Power BI | Yes, natively | No |
| Power Platform / Power Automate | Through connectors the tenant allows; no flow administration | No |
| Remembers across sessions | A keyed memory store, 512 characters per entry (measured on the operated tenant) | One account-wide memory shared with chat; editable topic files; on by default for individual plans, off for Team/Enterprise until turned on |
| Records failures as tested rules | No | No |
| Custom skills | `SKILL.md` folders under the user's OneDrive Cowork folder; a description over 1024 characters is dropped silently | `SKILL.md` uploaded as your own skill or delivered by a plugin; installed directory skills are view-only |
| Standing instructions file | `copilot-instructions.md` exists but never took effect on the operated tenant | No equivalent file *(expected)* |
| Version control | None | None (git in the VM only if the repo is visible there — *unverified*) |
| Keeps a process alive between sessions | Nothing on the machine | Nothing — the host owns each MCP server's lifetime |

## What this repository adds, by route

| Component | Copilot Cowork | Claude Cowork |
|---|---|---|
| **Approved batch executor** (8933) — runs an existing `.bat`/`.cmd`/`.sh` by relative name; no command, arguments, cwd, environment, timeout or elevation parameter | Required — the only execution path | Required — the only path to the host OS |
| **Job conventions** — `CommandJobs/`, the `COWORK_RESULT` contract, per-run logs, standing parameterized jobs | Required | Required |
| **Release gate and `install_check.py`** — proof by handshake and negative controls | Required | Required |
| **Lessons machinery** — failure → keyed entry → rule → generated delivery into skills and tool descriptions, with checkers | Required | Required — nothing native does this |
| **Deep-tier memory files** — mechanism and evidence, one home per fact, under git | Required | Required — the host's memory is the pointer tier, not this |
| **Pointer-tier memory** | The host's 512-character store, indexed to the deep files | Use the host's own memory; no workaround shipped |
| **Filesystem bridge** (8932) — named roots | Required — the only way to read or write the machine | Optional — connect the folder instead; register the bridge only for tool parity with the hosted route |
| **Browser bridge** (8931) — a signed-in profile, traces and screenshots to disk | Required for authenticated browsing | Optional |
| **Power Automate bridge** (8934) — flow administration, allow-listed environments, audited writes | Optional, needs a tenant | Optional, needs a tenant |
| **supergateway, dev tunnel, Ports panel, connector packages, watchdog, personalizer** | Required — they exist to reach a machine from a cloud | Not installed — nothing to reach across |
| **Skills** — the bridge skills and the operating bookends | Required; written to this host's tool names | Machinery works; the skill prose needs its host-adapter sections (issue #6) |

Every setup, on every platform, keeps the same refusal contract: the executor runs only a
script that already exists under `CommandJobs`, named by relative path, with fixed
controls, and a refusal is the control working. The host determines how far away the
agent is; the repository determines what it may do once it gets here.

Agents: the install contract is in [`AGENTS.md`](../../AGENTS.md); it names both routes.
