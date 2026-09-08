# Setup on macOS and Linux

This guide takes a Mac with nothing installed to four running bridges that a
Copilot Cowork or Claude Cowork session can call, with the skills, the lessons
corpus and the memory files in place. [`docs/setup.md`](setup.md) is the Windows
path; this is its sibling, and the two differ in fewer places than you would
expect.

Read [`SECURITY.md`](../SECURITY.md) first. Two of the four bridges - the
filesystem bridge and the command bridge - act on the machine with your
authority over a public tunnel. This guide does not make that safe; it makes it
narrow and reviewable. Use a test account and a test folder until you have
watched the approval flow work.

## What is different from Windows

Only these. Everything else in `docs/setup.md` applies unchanged.

| | Windows | macOS / Linux |
|---|---|---|
| Launchers | `Startup/*.cmd` | `Startup/posix/*.sh` |
| Executable job scripts | `.bat` and `.cmd` | `.sh` |
| Output directive | `REM COWORK_OUTPUT: ...` | `# COWORK_OUTPUT: ...` |
| Job shell | `cmd.exe /d /s /c` | `/bin/bash <script>` |
| Local paths | `scripts/personalize.py` rewrites them | launchers derive them; overrides in `cowork-env.sh` |
| Watchdog | Task Scheduler, `_watchdog-install.ps1` | `launchd`, `Startup/posix/watchdog/` |
| Playwright browser | `msedge` | `chrome` by default, `COWORK_PW_BROWSER` to change |

The command bridge enforces the **same refusal set on both**, and
`scripts/exec_bridge_selftest.py` proves it in the platform's own script
language - so a refusal that holds on Windows and not on a Mac fails the gate
rather than shipping.

## 1. Prerequisites

| Need | Why | Check |
|---|---|---|
| macOS 13+ or a current Linux | Every path is `$HOME`-relative; nothing requires root | `uname -a` |
| Node.js 20 LTS or later | Runs supergateway and the two own-code servers | `node --version` |
| Python 3.10 or later | The gate, the checkers, the lesson tooling | `python3 --version` |
| Git | The local repository and the publishing tooling | `git --version` |
| Visual Studio Code, signed in for dev tunnels | Auto-starts the bridges and forwards the ports | Accounts menu shows a signed-in account |
| A Chromium browser | The Playwright bridge drives a profile | Chrome or Edge opens |
| Cowork, and permission to add a custom app | The connector packages are uploaded as custom apps; many tenants restrict this | Ask your administrator before step 6 |

Internet access is needed at first start: the two upstream servers are fetched
by `npx` on demand. Nothing in `Startup/CommandBridge/` or `Startup/FlowBridge/`
downloads anything.

## 2. Clone and validate

Unlike the Windows path, the location is yours to choose - the POSIX launchers
derive the tooling root from their own location, so nothing is hard-coded.

```bash
git clone https://github.com/jordanmrash/agent-of-record.git ~/Documents/COPILOT_COWORK
cd ~/Documents/COPILOT_COWORK
python3 scripts/release_check.py
```

Expect `RELEASE_CHECK: CLEAN`. If you do not get it, stop: the checkout is not
what was published.

## 3. Install the runtime and mark the launchers executable

```bash
cd Startup && npm install && cd ..
chmod +x Startup/posix/*.sh
```

`Startup/package.json` pins supergateway, and the tasks run it from
`Startup/node_modules` rather than through `npx`, so the version that starts is
the version that was tested.

The `chmod` is not optional and is easy to forget: a clone can arrive without
the execute bit, and `install_check.py` will tell you so by name.

## 4. Point the bridges at your Cowork folder

The filesystem bridge takes a third root - the folder Cowork itself loads, with
your skills, `copilot-instructions.md` and `cowork-memory`. Writing there
directly is what lets an agent update its own corpus instead of uploading to the
cloud and waiting on replication.

There is no portable default for that path, so it is configuration rather than
code:

```bash
cp Startup/posix/cowork-env.example.sh Startup/posix/cowork-env.sh
$EDITOR Startup/posix/cowork-env.sh
```

Set `COWORK_CONFIG_ROOT`. On a Mac with OneDrive for Business it usually looks
like `$HOME/Library/CloudStorage/OneDrive-<Org>/Documents/Cowork`; with personal
OneDrive, `$HOME/OneDrive/Documents/Cowork`. Leave it unset to run with two
roots and keep the corpus inside the repository instead.

`cowork-env.sh` is gitignored, and `scripts/public_scan.py` refuses any tracked
file containing a real home directory path. That is deliberate: your account
name is not something to publish.

## 5. First start and the tunnel host

1. Run `Startup/posix/GO.sh`, or open the `Startup` folder in VS Code yourself.
   Allow automatic tasks if prompted; the four bridge tasks start in the
   terminal panel. VS Code picks the `osx` or `linux` task variant on its own.
2. Open the **Ports** panel. The four ports forward automatically. Set each one
   to **Public**: right-click, Port Visibility, Public. This does not persist
   across restarts, and nothing on the machine can do it for you - the watchdog
   restarts a dead listener but cannot change visibility.
3. Read the forwarded address of any port:
   `https://<tunnel-host>-8931.<region>.devtunnels.ms`.

Then verify the endpoints answer, locally and through the tunnel:

```bash
lsof -nP -iTCP:8931-8934 -sTCP:LISTEN
for p in 8931 8932 8933 8934; do
  printf '%s ' "$p"; curl -s -o /dev/null -w '%{http_code}\n' -m 5 "http://127.0.0.1:$p/mcp"
done
```

A reachable bridge answers a bare GET with 400 or 405 - the endpoint exists and
refuses that method, which is the expected shape. No status at all means the
listener is not there; 401 or 403 through the tunnel means the port is still
private.

## 6. Register the connectors

Identical to the Windows path - see [`docs/setup.md`](setup.md) step 8 - except
for how you build the zips. Each folder under `Startup/Plugins/` is one
connector package and the three files must sit at the **zip root**:

```bash
cd Startup/Plugins
for d in */; do (cd "$d" && zip -q -r "../${d%/}.zip" .); done
cd ../..
```

Keep the connector ids as shipped; they are the tool namespaces the skills
address, and `scripts/facts_check.py` fails if a manifest drifts from them.

Start a **new** Cowork session afterwards. Connectors register at session start,
and a session that began before the upload will not see them.

## 7. Install the watchdog

```bash
bash Startup/posix/watchdog/install-launchd.sh
```

This installs a `launchd` agent that probes the four ports every two minutes and
starts a listener only on a port that refuses connections. It never kills
anything, and it will not restart the same port twice inside its cooldown
window. Like its Windows counterpart it cannot restore tunnel visibility, and it
cannot help when VS Code itself is closed.

To remove it: `bash Startup/posix/watchdog/install-launchd.sh --uninstall`.

## 8. Install the Cowork configuration

```bash
COWORK="$HOME/Library/CloudStorage/OneDrive-Example/Documents/Cowork"   # yours
mkdir -p "$COWORK/skills"
cp -R CoworkConfig/Skills/* "$COWORK/skills/"
cp CoworkConfig/copilot-instructions.md "$COWORK/"
cp -R CoworkConfig/cowork-memory "$COWORK/"
```

[`CoworkConfig/README.md`](../CoworkConfig/README.md) explains what each piece
is, which files are generated from which, and - important before you start - how
to begin with an **empty** corpus rather than the author's. The shipped lessons
and memory files are one operator's record of one machine. They are the right
thing to read and the wrong thing to operate under.

Two limits worth knowing before you rely on either. Skills load reliably and are
the carrier that works everywhere; `copilot-instructions.md` did not take effect
on the author's tenant, which is why the digest is routed into the skills as
well. And a skill whose frontmatter `description` exceeds 1024 characters is
dropped by the loader silently, with no error - `install_check.py` enforces that
cap for exactly this reason.

## 9. Prove the installation

```bash
python3 scripts/install_check.py --config-root "$COWORK" --json install-results.json
```

`INSTALL_CHECK: CLEAN` is the finish line. The check starts each own-code bridge
as a real stdio MCP server and completes a handshake, rather than testing that a
file exists - so a server that parses but cannot start is caught here rather
than in a Cowork session.

Then, in a new session, say `gamma tango`. It should load the memory index,
report git status, and at close log any lesson, refresh the memory file and
propose a commit. When that round trip has worked once, you have what this
repository describes.

## What is not covered

- **Anything tenant-side.** Whether custom apps can be uploaded, whether
  connectors are enabled for Cowork, and how long a new connector takes to
  appear are decided by your administrator and the platform.
- **Making the executor safe.** A `.sh` under `CommandJobs` runs as you. The
  control point is reading the proposed file before approving it. Treat write
  access to `CommandJobs` as execute access, as `SECURITY.md` says.
- **Power Automate on a Mac.** The 8934 bridge starts and refuses by default the
  same way it does on Windows. Its usefulness depends on tenant policy, not on
  this repository.
