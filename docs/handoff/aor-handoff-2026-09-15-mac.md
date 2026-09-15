# Handoff for the Mac - 2026-09-15 evening

For: the Claude Cowork session on the Mac that finishes and tests the narrowed route.
From: the Windows PC (Copilot Cowork), after the route review and PR #19.

## 1. Where the code is

- Use branch **`fix/route-review-2026-09-15`** (PR #19 against `main`). It carries your nine
  narrowing commits (`6e0d58d..4ab0051`) unchanged plus two PC commits on top. If PR #19 has
  merged by the time you read this, use `main`.
- `git fetch origin && git checkout fix/route-review-2026-09-15 && git pull --ff-only`
- Do not push to `main` directly. `704071e` reached `main` by admin bypass; the rewind was
  refused. Everything goes through a PR.

## 2. What the PC changed, and why

1. **The four skills you deleted are back, and every skill ships to every product.**
   `local-file-bridge`, `playwright-skill`, `git-bridge`, `skill-menu` were deleted in
   `6e0d58d`; Copilot Cowork still uses all four (its bridges survived, its skills did not).
   Jordan's decision: a skill that is redundant in one configuration and needed in another is
   kept and marked, and the person disables it in the host. Each of the five affected skills
   (the four plus `persistent-memory`) carries a "When this skill is redundant" section;
   `docs/skills-by-configuration.md` is the matrix. `plugin.json` no longer scopes any skill
   by product; `build_plugin.py --product` still works for a narrower build.
2. **The narrowing of the bridges stands.** One server on the Claude route, `aor-batch-exec`.
   `install-mac.sh` registers it alone and retires `aor-filesystem` / `aor-playwright`.
3. **The reversal is recorded.** `CHANGELOG.md` Unreleased opens with it now.
4. **The model behind the session may not be Claude.** Claude Desktop's third-party
   inference mode (Developer > Configure Third-Party Inference; Ollama offers a one-toggle
   setup on macOS) runs Cowork against a gateway or a local model. The route is unchanged.
   What is unknown: whether account memory exists when the session is signed out of the
   Anthropic account. See step 9.
5. **Lessons.** Your Part 3 entries and one new PC entry
   (`verify-product-claim-before-correcting-the-operator`) are in the repository corpus and
   in the live Copilot corpus. `lesson_scope_tag.py` was dry-run only; nothing was tagged.

## 3. Tonight's steps

| # | Step | Done when |
|---|---|---|
| 1 | Check out the branch (section 1). `git log --oneline -3` shows the PC commits above `4ab0051`. | |
| 2 | `python3 scripts/release_check.py` | `RELEASE_CHECK: CLEAN (25 checks)` |
| 3 | `python3 scripts/build_plugin.py --strict --platform macos` | `OK 10 skill(s)` (not five) |
| 4 | Claude: Customize > Plugins > Add > **Upload plugin** > `Outputs/Skills Plugin/agent-of-record-skills-macos.plugin` | appears under "Created by you" |
| 5 | Quit Claude completely (Cmd+Q) and reopen | |
| 6 | `ListSkills` returns **ten** | ten names |
| 7 | Signed in with an Anthropic account: disable `persistent-memory`, `local-file-bridge`, `playwright-skill`, `git-bridge`, `skill-menu` under Customize. Note which toggle exists (per skill or per plugin only) - that detail is undocumented and goes in the evidence file. | five off, five on |
| 8 | Connector list shows one: `aor-batch-exec`, one tool. `run_batch_file` on `hello-mac.sh` | exit 0 |
| 9 | Optional but valuable: enable third-party inference with a local Ollama model, start a new session, and test whether memory persists across sessions when signed out. Re-enable `persistent-memory` if it does not. | a yes/no with the model named |
| 10 | `python3 scripts/install_check.py --route local` | `INSTALL_CHECK: CLEAN` |
| 11 | Read the operating-rules block on the first job after the restart | rules that apply to this route |
| 12 | Write `docs/evidence/mac-operated-2026-09-15b.md` with the results of 3-11, commit on a branch, open a PR. Post the `install-mac.sh --verify` output to #15. | PR open, #15 has the output |

Only after 6-10 pass: flip `docs/install/claude-cowork-mac.md` and the quickstart from
"not yet operated" to operated, in the same PR.

## 4. Do not

- Delete a skill because it is redundant here. Disable it.
- Claim the third-party inference path is operated on Windows. It is written on the
  assumption Windows will catch up; the first real call on the PC is still owed.
- Relax `install_check`'s schema dialect check by reasoning. The Copilot route showed the
  hosted client accepts draft-07; a Claude-side test is still the open question
  `cowork-draft07-well-formed-untested`.

## 5. Open after tonight

- Routes for the ten new lessons in `skill_lesson_routes.json` / `plugin_lesson_routes.json`
  (they are in the corpus, not yet delivered into skills).
- Live Copilot skill bodies on the PC still lack the redundancy sections until the next
  repo-to-live sync (a PC job; no action on the Mac).
- Release 0.4.0 with the `CITATION.cff` bump once PR #19 and tonight's PR are merged.
- Ruleset: whether admins may keep bypassing the pull-request requirement.
