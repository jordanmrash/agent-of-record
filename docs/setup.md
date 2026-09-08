# Setup from zero

This is the Windows path. For macOS or Linux, follow
[Setup on macOS and Linux](setup-macos.md); the two share every step that is not
about launchers, the watchdog or the shell.

This guide takes a Windows PC with nothing installed to four running bridges
that a Microsoft 365 Copilot Cowork session can call, with the skills, the
lessons corpus and the memory files in place. It is the path the author's own
machine followed, reconstructed from the files in this repository rather than
from recollection; where a step depends on your tenant, it says so.

Read [`SECURITY.md`](../SECURITY.md) first. Two of the four bridges - the
filesystem bridge and the batch executor - act on the PC with your authority
over a public tunnel. The guide does not make that safe; it makes it narrow and
reviewable. Use a test account and a test folder until you have watched the
approval flow work.

## 1. What you are installing

```
Cowork session ──► dev tunnel (VS Code Ports panel, Public) ──► supergateway on the PC
                                                                 ├─ 8931 Playwright    (upstream @playwright/mcp, dedicated Edge profile)
                                                                 ├─ 8932 Filesystem    (upstream server-filesystem, three roots)
                                                                 ├─ 8933 Batch executor (own code, one tool: run an existing .bat)
                                                                 └─ 8934 Power Automate (own code, refuses until configured)
```

Each bridge is a stdio MCP server wrapped by `supergateway` as a streamable-HTTP
endpoint on one local port. VS Code forwards the four ports through a dev
tunnel, and a connector package per port tells Cowork the tunnel URL. The
skills in `CoworkConfig/Skills/` address the bridges by connector id; the
lessons corpus and the memory files give a session its operating history.
[`docs/architecture.md`](architecture.md) has the full picture.

## 2. Prerequisites

| Need | Why | Check |
|---|---|---|
| Windows 10 or 11, a standard user account | Every path is `C:\Users\<account>\...`; nothing requires elevation | `whoami` |
| Node.js 20 LTS or later | Runs supergateway and the two own-code servers; `npx` fetches the two upstream servers | `node --version`, `npx --version` |
| Python 3.10 or later | The gate, the checkers, the lesson tooling | `python --version` |
| Git | The local repository and the publishing tooling | `git --version` |
| Visual Studio Code, signed in for dev tunnels | Auto-starts the bridges and forwards the ports; port forwarding requires a GitHub or Microsoft account sign-in in VS Code | Accounts menu shows a signed-in account |
| Microsoft Edge | The Playwright bridge drives an Edge profile (`--browser msedge`) | Edge opens |
| Microsoft 365 Copilot with Cowork, and permission to add a custom app | The connector packages are uploaded as custom apps; many tenants restrict this to administrators | Ask your tenant administrator before step 8 |
| GitHub CLI (`gh`), optional | Only the publishing jobs in `GitHubSetup/` use it | `gh auth status` |
| Power Automate access, optional | Only for the 8934 bridge; everything else runs without it | - |

Internet access is needed at first start: `npx -y @playwright/mcp@latest` and
`npx -y @modelcontextprotocol/server-filesystem` download on demand. Nothing in
`Startup/CommandBridge/` or `Startup/FlowBridge/` downloads anything.

## 3. Place the repository

The launchers, the watchdog and the jobs hard-code the tooling root, so clone
to exactly this path:

```powershell
git clone https://github.com/jordanmrash/agent-of-record.git "$env:USERPROFILE\Documents\COPILOT_COWORK"
cd "$env:USERPROFILE\Documents\COPILOT_COWORK"
python scripts\release_check.py
```

The gate should end with `RELEASE_CHECK: CLEAN`. If it does not, stop: the
checkout is not what was published, and nothing below will behave as
documented.

Two folders named for Cowork exist on the finished machine, and the memory
files are firm about keeping them straight:

| Folder | Holds | Reached by |
|---|---|---|
| `C:\Users\<account>\Documents\COPILOT_COWORK` | this repository: `Startup`, `CommandJobs`, `Outputs`, the git history | the filesystem bridge and the batch executor |
| `C:\Users\<account>\<OneDrive folder>\Documents\Cowork` | what Cowork itself loads: `skills\`, `copilot-instructions.md`, `cowork-memory\` | Cowork directly, and the filesystem bridge's third root |

`<OneDrive folder>` is `OneDrive` on a personal account and `OneDrive - <Your
Organization>` on a work account. Look at `C:\Users\<account>` to see which you
have.

## 4. Personalize the tree

Every operating file carries `YOURUSER` and the connector packages carry
`YOUR-TUNNEL-HOST`. `scripts/personalize.py` replaces them in one pass and is a
dry run until you add `--apply`:

```powershell
python scripts\personalize.py --user <account> --onedrive-folder "OneDrive - Contoso"
python scripts\personalize.py --user <account> --onedrive-folder "OneDrive - Contoso" --apply
```

Leave out `--onedrive-folder` when yours is plain `OneDrive`. Leave out
`--tunnel-host` for now - you learn it in step 6 and run the script again.

What changes: `Startup/`, `CommandJobs/`, `CoworkConfig/` and
`docs/bridge-facts.json`. What does not: the documentation that explains the
placeholders, the publishing tooling in `GitHubSetup/`, `scripts/`, and the
`author-email` lines in the skills, which name the author rather than the
operator. The script prints every file it touched with a count, and refuses a
user name that is itself a placeholder.

A personalized tree is an installation, not a publication. `scripts/public_scan.py`
now fails on it by design - do not push it to a public remote. Keep your
personal changes on a local branch or in a private remote.

## 5. Install the bridge runtime

```powershell
cd Startup
npm install
cd ..
```

`Startup/package.json` pins `supergateway 3.4.3`; `Startup/.vscode/tasks.json`
runs it from `Startup/node_modules` rather than through `npx`, so the version
that starts is the version that was tested. `node_modules` is ignored by git.

Create the Edge profile folder the Playwright bridge will use and sign in once:

```powershell
mkdir "$env:USERPROFILE\pw-sso-profile"
& "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe" --user-data-dir="$env:USERPROFILE\pw-sso-profile"
```

Sign in to whatever the bridge will need to reach, then close the window. The
profile keeps the sessions; the bridge never sees a password. Use a test
account here until you trust the approval flow.

## 6. First start and the tunnel host

1. Double-click `Startup\GO.bat`. It opens VS Code on the `Startup` folder.
   Allow automatic tasks if VS Code asks; the four bridge tasks start in the
   terminal panel.
2. Open the **Ports** panel. The four ports are forwarded automatically
   (`Startup/.vscode/settings.json` does that). Set each one to **Public**:
   right-click, Port Visibility, Public. This does not persist across restarts
   - you repeat it every launch. Nothing on the PC can do it for you: the
   watchdog (step 9) restarts a dead listener but cannot change visibility.
3. Read the forwarded address of any port. It has the form
   `https://<tunnel-host>-8931.<region>.devtunnels.ms`. The label before
   `-8931` is your tunnel host; the label after the port is your region.

Now finish personalizing:

```powershell
python scripts\personalize.py --user <account> --onedrive-folder "OneDrive - Contoso" --tunnel-host <tunnel-host> --apply
```

Add `--tunnel-domain <region>.devtunnels.ms` if the region is not `use`. The
four connector manifests under `Startup/Plugins/` now point at your tunnel, and
each has been given its own app id.

If a task fails with `EADDRINUSE`, something already holds the port -
`Startup/README.txt` has the recovery commands. If `node` is not found, the
Node installer did not put it on `PATH` for a new terminal; sign out and in.

## 7. Verify the bridges from the PC

Before involving Cowork, prove the endpoints answer, first locally and then
through the tunnel:

```powershell
Get-NetTCPConnection -LocalPort 8931,8932,8933,8934 -State Listen
foreach ($p in 8931,8932,8933,8934) { curl.exe -s -m 5 -o NUL -D - "http://127.0.0.1:$p/mcp" | findstr /R "^HTTP/" }
foreach ($p in 8931,8932,8933,8934) { curl.exe -s -m 10 -o NUL -D - "https://<tunnel-host>-$p.<region>.devtunnels.ms/mcp" | findstr /R "^HTTP/" }
```

Four listeners, then four HTTP status lines twice. A reachable bridge answers a
bare GET with HTTP 400 or 405 - the endpoint exists and refuses that method,
which is the expected shape. No HTTP line at all means the listener or the
tunnel is not there; a tunnel line that says 401 or 403 means the port is still
private. `CommandJobs\bridge-health.bat` runs the same probes for the first
three ports plus the checks that matter after a restart, and writes its report
to the job's output folder; it is written to run through the batch executor,
which is step 8.

## 8. Register the connectors in Cowork

Each folder under `Startup/Plugins/` is one connector package: a Teams app
manifest (`manifest.json`, schema 1.29, `agentConnectors` pointing at
`https://<tunnel-host>-<port>.<region>.devtunnels.ms/mcp` with no
authorization) and its two icons. Package each one as a zip **with the three
files at the zip root** (not inside a folder):

```powershell
Get-ChildItem Startup\Plugins -Directory | ForEach-Object {
  Compress-Archive -Path "$($_.FullName)\*" -DestinationPath "$($_.FullName).zip" -Force
}
```

Upload each zip as a custom app in Microsoft 365 Copilot (Apps, Manage your
apps, Upload a custom app - the menu names vary by release), then enable the
connector for Cowork. If the upload option is missing, your tenant's app setup
policy does not allow custom apps for your account and an administrator has to
add the packages through the Teams admin center. Tenant policy also decides
whether the connector is available in Cowork at all; this repository cannot
change that.

Keep the connector ids as shipped - `jordan-local-playwright-8931-v1`,
`jordan-local-filesystem-8932-v1`, `jordan-approved-batch-8933-v1`,
`jordan-power-automate-8934-v1`. They are the tool namespaces the skills
address; `scripts/facts_check.py` fails if a manifest drifts from them.

Start a **new** Cowork session. Connectors register at session start and a
session that began before the upload does not see them. First calls that prove
each bridge, in order of risk:

| Bridge | First call | Expect |
|---|---|---|
| 8932 | list the allowed directories | exactly the three roots |
| 8933 | run `bridge-health.bat` | the health report for the first three ports, stdout and an exit code of 0 |
| 8931 | open a page in the profile | the page, signed in if the profile is |
| 8934 | `bridge_status` | `config_loaded: false`, `read_only: true`, no allowed environments - every flow tool refuses until step 10 |

Expect the platform to drop the occasional call - the author measured one to
two percent on the tunnel hop. A dropped call is retried once; a bridge is
called "down" only when a repeated probe fails.

## 9. Install the watchdog

```powershell
powershell -ExecutionPolicy Bypass -File Startup\_watchdog-install.ps1
```

This registers a scheduled task, `CoworkBridgeWatchdog`, at logon and every two
minutes, running `Startup/_bridge-watchdog.ps1` headless. It probes the four
ports and starts a listener only on a port that refuses connections, never
kills anything, and will not restart the same port twice inside its cooldown
window. It cannot restore tunnel visibility, and it cannot help when VS Code
itself is closed - that still needs `GO.bat`. The header of the watchdog script
says why a restart is enough when it is, and the lessons block in
`CoworkConfig/Skills/command-bridge/SKILL.md` carries what the author learned
about restarting bridges the wrong way.

## 10. Power Automate (optional)

Copy `Startup/FlowBridge/flow-bridge.config.example.json` to
`Startup/FlowBridge/flow-bridge.config.json`, fill in your tenant id and the
environments you want reachable, and leave `read_only` true and `allow_delete`
false until you have watched the bridge refuse. The real config and the token
cache are gitignored; keep the cache outside the repository. Authentication is
interactive on the first call - a browser opens for delegated sign-in through
the public client id Microsoft publishes in its own Dataverse documentation, so
no private app registration is needed and there is no secret to keep.
`docs/quickstart.md` lists the guard rails.

## 11. Install the Cowork configuration

`CoworkConfig/` mirrors what the author's Cowork loads. Copy it into the
OneDrive Cowork folder:

```powershell
$cowork = "$env:USERPROFILE\OneDrive - Contoso\Documents\Cowork"   # or ...\OneDrive\Documents\Cowork
New-Item -ItemType Directory -Force "$cowork\skills" | Out-Null
Copy-Item CoworkConfig\Skills\* "$cowork\skills\" -Recurse -Force
Copy-Item CoworkConfig\copilot-instructions.md "$cowork\"
Copy-Item CoworkConfig\cowork-memory "$cowork\" -Recurse -Force
```

[`CoworkConfig/README.md`](../CoworkConfig/README.md) explains what each piece
is, which files are generated from which, and - important before you start -
how to begin with an **empty** corpus instead of the author's. The shipped
`cowork-lessons.md` and memory files are one operator's record: they refer to
his machine, his measurements and his decisions. They are the right thing to
read and the wrong thing to operate under.

Two honest limits. Skills load reliably and are the carrier that works
everywhere; `copilot-instructions.md` did not take effect on the author's
tenant, which is why the digest is routed into the skills as well. And a skill
whose frontmatter `description` exceeds 1024 characters is silently dropped by
the loader with no error - the lesson is in the corpus under
`An always-on skill over the 1024-char description cap never loads at all`.
Keep it in mind for skills you write.

## 12. Prove the loop once

In a new session, say `gamma tango` - the session bookend skill. It should load
the memory index, report the repository's git status, and at close log any
lesson, refresh the memory file and propose a commit. The first close on an
empty corpus is covered in `CoworkConfig/README.md`. When that round trip has
worked once, you have what this repository describes: bridges the agent can
reach, a corpus the agent writes to, and a gate that checks what it wrote.

## What is not covered

- **Anything tenant-side.** Whether custom apps can be uploaded, whether
  connectors are enabled for Cowork, and how long a new connector takes to
  appear are decided by your administrator and the platform.
- **The platform's own behavior.** The author's measurements - connectors
  registering partially at session start, being removed minutes later, the drop
  rate on the tunnel - are in the lessons corpus with dates. They describe his
  tenant in the weeks recorded, not a guarantee about yours.
- **Making the executor safe.** A `.bat` under `CommandJobs` runs as you. The
  control point is reading the proposed file before approving it. Treat write
  access to `CommandJobs` as execute access, as `SECURITY.md` says.
