# Security

## What this repository exposes

Two of the four bridges are own code and run with the signed-in user's
privileges on a real machine behind a public dev tunnel:

- **8933 approved batch executor** - runs a `.bat`/`.cmd` that already exists
  under `CommandJobs`, by relative path only. The boundary is the folder and
  the file type, not the script contents: anything able to write into
  `CommandJobs` can cause execution on the next call. Treat write access to
  that folder as execute access. The controls are documented in
  `Startup/CommandBridge/README.txt` (canonical-path containment, no
  arguments, fixed timeout, one concurrent job, no elevation, per-run logs).
- **8934 Power Automate bridge** - delegated user auth with a cached refresh
  token stored outside the repository. Environments are refused until
  allow-listed; production is flagged explicitly; deletion needs a separate
  opt-in plus a name confirmation; every mutating attempt is audited.

A dev-tunnel hostname is a live ingress to the machine, not merely an
identifier of it. It is never committed here; if one ever appears in a
published tree, treat it as an incident: rotate the tunnel, then remove the
value in a follow-up commit and, because a commit does not unpublish what an
earlier one exposed, rotate anything else the history now reveals.

## Supported versions

Through v0.3.0 this was a published snapshot, rebuilt in full on each
publication; from v0.3.0 `main` keeps its history and accepts pull requests.
Either way, only the
current `main` and the latest tagged release are maintained.

## Reporting

Please do not open a public issue for a security problem. Use GitHub's private
vulnerability reporting on this repository, or contact the author through the
profile linked from the repository. Expect an acknowledgement within a few
days; this is a personal project with no on-call rota.

## What is deliberately absent

No credentials, tokens, tenant or environment identifiers, tunnel hostnames,
client material, or firm-internal material are present.

The lessons corpus (`CoworkConfig/cowork-memory/cowork-lessons.md`) is the
operational record of a working assistant and ships in full. Before publication
every entry passed a substitution pass that replaced, by category: the account
name and every user-profile path; the firm and its abbreviations; the tenant and
every environment identifier and organization URL; the tunnel host; client and
colleague names; and file names carrying any of those. The categories are
documented in `GitHubSetup/PUBLISHING.md`; the values live only in local lists
that are gitignored and never copied. Entries whose substance, not merely whose
labels, described non-public work were withheld rather than rewritten. The publish gate in
`GitHubSetup/` scans for credential shapes, a local denylist of names, and
name-shaped prose in CI on every push and pull request, and the history before
v0.3.0 is a series of single commits
so nothing can be recovered from an earlier revision.

GitHub Actions also runs `scripts/public_scan.py`, which checks public-safe
shapes without embedding any private denylist values in the repository.
