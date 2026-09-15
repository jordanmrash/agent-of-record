# What this repository adds to Copilot Cowork

Copilot Cowork is the host this repository was built on and is operated with daily. It
runs in Microsoft's cloud, inside a per-session container that holds the user's Microsoft
365 tenant — mail, calendar, Teams, SharePoint, Power BI — and nothing of the user's own
machine. Every capability below exists because that container cannot see a PC, and
because a person has to remain accountable for what an agent does once it can.

Install pages: [Windows PC](../setup.md) (operated daily) · [Mac or Linux](../setup-macos.md)
(not yet operated). The route comparison is in [Choose your route](README.md).

## What the host does on its own

- Reads and acts on the tenant with the user's identity: documents, mail, meetings, chats,
  Power BI, Power Platform connectors the tenant permits.
- Runs code in its own cloud container — Python, Node, a shell — with no path to the
  machine and no outbound network beyond what Microsoft allows.
- Loads skills (`SKILL.md` folders in the user's OneDrive Cowork folder) and keeps a
  per-user memory store of short keyed facts (512 characters per entry, measured).
- Calls MCP servers it can reach over HTTPS, after an administrator has allowed the
  connector.

What it cannot do: read a local file, run a local program, use a signed-in browser,
administer Power Automate as an operator would, remember *why* something is true, or
learn from a failure in a way that changes the next session.

## What the repository adds, and what each part lets you do

**Governed reach into the machine.** Four stdio MCP servers on the PC, each wrapped by
`supergateway` on its own port and forwarded through a dev tunnel; a connector package per
port tells Cowork the URL. This is what lets a Cowork session read a spreadsheet on disk,
run a job against it, and write the result back — work the tenant alone cannot host.

**Approval-gated execution** — the batch executor. One tool, `run_batch_file`, which runs
an existing `.bat` or `.cmd` under `CommandJobs` named by relative path. The agent proposes
the exact script, a person reads and approves it, the filesystem bridge writes it, the
executor runs that named file with fixed controls (300 s, 5 MB, one job, no elevation, no
console) and reports stdout, stderr, exit code and every file created or changed. It
enables anything the signed-in user could do at a prompt — git, `gh`, the Power Platform
CLI, PowerShell against Office files — while keeping the unit of approval a reviewable
file rather than a command string.

**A signed-in browser.** The Playwright bridge drives a dedicated Edge profile the user has
signed into once, so an agent can reach pages the hosted browser cannot, with traces and
screenshots written to disk.

**Power Automate administration under control.** Twenty-nine tools over flows, runs,
connections, solutions, DLP and ownership, with environments denied until allow-listed,
production flagged, writes pinnable off per environment, deletion requiring the current
flow name, and every mutating attempt audited.

**A deep memory tier.** The host's memory store holds pointers; the repository adds the
files those pointers resolve to — mechanism, evidence and dates, one home per fact, under
git — so a session can start from what is known rather than what was summarized.

**Lessons that become controls.** A failure is written as a keyed entry with the approach
that failed and the one that worked; a repeat increments a hit count; a twice-hit rule is
promoted into the instructions digest and regenerated into the skills and the executor's
own tool description, and checkers fail the release when any of those surfaces drifts.
This is the part of the repository with no native counterpart on any host.

**Standing jobs and a release gate.** Parameterized jobs that land a change on a protected
`main` only after the gate runs clean on the machine, plus clean-room publication tooling
that refuses a tree carrying a real path, hostname or identifier.

## What it costs

Everything in the first bullet is infrastructure a local host does not need: the tunnel,
its ports set Public after every restart, the watchdog that restarts a bridge the tunnel
lost, connector packages, the personalizer that writes the operator's paths into them, and
a 1–2 % dropped-call rate on the tunnel hop that the skills teach the agent to retry rather
than misdiagnose. The Windows page explains each piece where it is installed. Under
[Claude Cowork](claude-cowork.md) the same bridges are registered directly and none of it
exists.


## Addendum 2026-09-15 - skills by configuration, and the model behind the session

Every skill in the repository ships to this route; the ones that duplicate a host capability
here say so in their own "When this skill is redundant" section, and the matrix is in
`docs/skills-by-configuration.md`. Disable a redundant skill in the host; re-enable it when
the configuration changes. If the session runs under third-party inference (a gateway or a
local model), the route is identical - the host, its folders, browser, plugins and MCP
servers are unchanged - but keep `persistent-memory` enabled until account memory is
confirmed present when signed out, and expect enforced controls to carry more weight than
delivered rules with a smaller model.
