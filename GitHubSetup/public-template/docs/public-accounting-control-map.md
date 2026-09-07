# Public Accounting Control Map

This map translates the repository's technical design into concerns familiar to public-accounting, risk, internal-control, and technology leaders.

| Professional concern | Foundation capability | Evidence in this repository | Current boundary |
|---|---|---|---|
| Confidential information leaves an approved environment | Restricted filesystem roots; clean-room publication; local denylist and sanitization passes | `Startup/fs-server.cmd`, `GitHubSetup/` | Configuration still depends on the operator maintaining the local lists |
| An agent executes an unauthorized command | Filename-only batch executor; exact file reviewed before execution; no arguments or command string | `Startup/CommandBridge/`, `CommandJobs/` | Anything able to write into `CommandJobs` has potential execute authority |
| An agent changes a production flow accidentally | Explicit `production` and `read_only` flags; allowlist; exact-name confirmation for delete | `Startup/FlowBridge/` | The example configuration must be replaced and reviewed locally |
| A conclusion cannot be traced to evidence | Memory records provenance and correction; applied skills are expected to carry evidence contracts | `CoworkConfig/cowork-memory/` | The foundation does not itself validate the evidence used by every future skill |
| The same error repeats in later periods | Lessons corpus; generated delivery into owning skills and tools | `cowork-lessons.md`, `skill_lessons.py`, `plugin_lessons.py` | A delivered rule may still be ignored |
| A new control exists only on paper | Three carried behavioral tests plus a control arm | `verify_delivery.py`, `verification_cases.json`, `verification-ledger.json` | Only a small number of rules have completed behavioral verification |
| A check claims broader coverage than it has | Checks declare covered and blind surfaces; scope audit compares the claim with code | `digest-tiers.txt`, `scope_check.py` | Direct session behavior remains outside file-linter visibility |
| An incorrect memory becomes institutional knowledge | One authoritative home per fact; correction and supersession; monthly consolidation proposals | `MEMORY-INDEX.md`, memory files, `dream-cycle` | Human review is required to judge whether a lesson is actually correct |
| Automation changes without review | Git-versioned configuration; named-file commits; release checks | `git-bridge`, `gamma-tango`, `GitHubSetup/` | The working repository is local and needs a separate durability strategy |
| A reviewer cannot explain why the process changed | Lessons capture failed, worked, why, evidence, hits, routes, and verification verdicts | `cowork-lessons.md`, `verification-ledger.json` | The volume of operational detail requires disciplined indexing |
| A model fills in missing data confidently | Hard-stop and failure-contract design is required for applied skills | Skill-design rules and roadmap | The foundation cannot guarantee that a future skill implements the contract correctly |
| Production and test are confused | Environment classification is authored data, not a naming heuristic | Flow bridge configuration schema | Classification is only as good as the maintainer's configuration |
| The public repository exposes deleted material through history | Disposable one-commit snapshot built by copying named folders into a new tree | `GitHubSetup/02-build-clean-repo.ps1` | Force-pushed snapshots trade conventional public history for disclosure control |
| A person approves without seeing the actual action | Proposed batch contents and output folder shown before the approved file is written | Command bridge workflow | Approval quality depends on the reviewer reading the proposal |
| A professional signs work generated through an undocumented process | Standard contract planned for applied skills: inputs, evidence, calculations, stops, review, audit | `docs/roadmap.md` | The common applied-skill contract is not yet implemented |

## Design principle

A control is not complete because it was written down. It needs:

1. **A sensor** that observes the relevant behavior.
2. **A specification** defining what acceptable behavior looks like.
3. **An actuator** that blocks, corrects, or escalates the deviation.
4. **Evidence** showing the control operated.
5. **A declared blind spot** where the sensor cannot observe.

The repository deliberately reports controls that lack one of these components as partial.
