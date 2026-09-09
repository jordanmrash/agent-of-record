# Contributing

Thank you for reading this far. A few things worth knowing before you open a
pull request.

Participation is governed by `CODE_OF_CONDUCT.md`.

## How this repository is developed

`main` is the working branch and keeps its history. Changes arrive as pull
requests, pass the gate in CI on **both Windows and macOS**, get a review from
the owner of the area they touch (`.github/CODEOWNERS`), and merge. Nothing is
force-pushed and nothing is rebuilt from a private copy.

That was not always so. Through v0.3.0 the tree was a snapshot: one commit,
force-pushed on each publication from a private working copy. The history before
v0.3.0 is therefore a series of roots, not a lineage, and a branch cut before
that tag will not rebase cleanly. Start from `main` as it is now.

## Contributing the macOS side

The POSIX layer - `Startup/posix/`, `docs/setup-macos.md`, the launchd watchdog -
was written on Linux and is the part of this repository most in need of someone
who runs it on a Mac every day. If that is you:

- **Your branch, your evidence.** The gate runs on `macos-latest` in CI for every
  pull request, and `scripts/exec_bridge_selftest.py` starts the real command
  bridge and tries thirty-one ways out of it in the platform's own script
  language. A green macOS run is the claim "this works on a Mac", made by a
  machine rather than a person.
- **Commit `install-results.json` from a real install** when you have one. It is
  gitignored at the root so an operator's private run never lands by accident;
  the reviewed place for it is `docs/evidence/`. A results file from a real Mac,
  with its host block, is worth more than any sentence in `setup-macos.md`.
- **What must stay identical across platforms** is anything that carries a safety
  property: the path validation and containment checks in
  `Startup/CommandBridge/batch-exec-server.js`, the refusal set the self-test
  asserts, the single-flight lock, the fixed timeout. The platform may choose
  the shell, the extension, the comment marker and the kill mechanism. It may
  not choose a refusal. A pull request that relaxes one on POSIX to make a Mac
  case pass will be declined, and the self-test is there so it fails first.
- **Machine-specific values are configuration, never code.** They go in the
  gitignored `Startup/cowork-env.cmd` (Windows) or `Startup/posix/cowork-env.sh`
  (POSIX), each documented by the `cowork-env.example.*` beside it. The launchers
  derive their own root on both platforms and carry no `C:\Users\` or `/Users/`
  path; `scripts/facts_check.py` fails one that does. `scripts/public_scan.py`
  refuses a tracked file with a real home directory in it, and CI runs it.

## The rules the checks enforce

**Data hygiene is a hard rule.** Nothing you submit may contain a credential, a
tunnel hostname, a tenant or environment identifier, a real person's or
organization's name, or an absolute path from your machine - `C:\Users\<you>`
and `/Users/<you>` alike. Use the placeholders the tree already uses
(`YOURUSER`, `YOUR-TUNNEL-HOST`, `you@example.com`, the zero GUID).

**Bridge facts have one home.** Ports, names, launchers, statefulness and roots
live in `docs/bridge-facts.json`; every surface that restates them is verified
against it. Change the manifest first, then the surfaces.

**Generated blocks are regenerated, not edited.** The lesson blocks in each
`SKILL.md` and the digest in `copilot-instructions.md` come from
`CoworkConfig/cowork-memory/cowork-lessons.md`. Edit the lesson; rerun the
generator.

**A checker change needs a self-test change.** Every checker has a `_selftest.py`
sibling that breaks it on purpose. A change to one without the other is
incomplete, and the reviewer will ask.

**Attribution stays.** Every skill carries an attribution block naming its
original author. Extend it with your name alongside; never replace it. The
template is `CoworkConfig/Skills/_ATTRIBUTION-TEMPLATE.md`.

## Before you push

```bash
python scripts/release_check.py
```

`RELEASE_CHECK: CLEAN` locally, then let CI say the same on the other platform.

**Issues are the best channel** for anything that is not yet a pull request. A
reproduction, the exact command, and the exit code go a long way; the tooling
here reports exit codes deliberately, so please quote them.

For an applied accounting skill, also document the purpose, owner, inputs,
evidence, deterministic calculations, hard stops, review points, audit record,
and normal/boundary/failure/sensitive-data tests.
