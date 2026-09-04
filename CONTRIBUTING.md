# Contributing

Thank you for reading this far. A few things worth knowing before you open a
pull request.

Participation is governed by `CODE_OF_CONDUCT.md`.

**This repository is a snapshot, not a working copy.** Development happens in a
private repository on one machine; each publication wipes this tree and rebuilds
it from an explicit include list, as a single commit. Two consequences:

- `main` is force-pushed on every publication (`--force-with-lease`). Rebase a
  branch onto the new `main` before re-submitting.
- A pull request is applied to the private working copy by hand and appears
  here in the next snapshot, credited in the commit message and in
  `CHANGELOG.md`, rather than being merged directly.

**Issues are the best channel.** A reproduction, the exact command, and the
exit code go a long way; the tooling here reports exit codes deliberately, so
please quote them.

**Data hygiene is a hard rule.** Nothing you submit may contain a credential, a
tunnel hostname, a tenant or environment identifier, a real person's or
organization's name, or an absolute path from your machine. Use the same
placeholders the tree already uses (`YOURUSER`, `YOUR-TUNNEL-HOST`,
`you@example.com`, the zero GUID).

**Attribution stays.** Every skill carries an attribution block naming its
original author. If you extend a skill, add your name alongside; do not replace
it. The template is `CoworkConfig/Skills/_ATTRIBUTION-TEMPLATE.md`.

**Self-tests before changes to a checker.** Each script under
`CoworkConfig/Skills/self-improvement/scripts/` has a `_selftest.py` sibling
that breaks it on purpose and asserts the failure. A change to a checker
without a change to its self-test is incomplete.

Before submitting:

```bash
python scripts/public_scan.py
python scripts/release_check.py
```

For an applied accounting skill, also document the purpose, owner, inputs,
evidence, deterministic calculations, hard stops, review points, audit record,
and normal/boundary/failure/sensitive-data tests.
