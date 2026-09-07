---
name: skill-menu
description: >-
  Presents a menu of the Cowork skills currently installed, so a skill can be picked and
  launched. Reads the installed skills fresh on every run and lists each as a collapsible card
  showing its Purpose, Getting Started, and Required Files, then offers a pick-to-launch prompt.
  Use when the user types "menu" or "skillmenu" on its own, or asks for the "skills menu", to
  "open my skills menu", "which skill should I run", "what can I run in Cowork", or "run one of
  my skills from the menu".
  Do NOT use to create, edit, validate, or delete a skill (use the skills skill), and do NOT use
  to execute a specific skill's work directly — this only lists skills and hands off to the one
  chosen.
metadata:
  owner: "Jordan Rash"
  author: "Jordan Rash"
  author-role: "Director, Tax Transformation and Automation"
  created-by: "Jordan Rash — original author and maintainer"
  attribution: "Created by Jordan Rash, Director, Tax Transformation and Automation."
cowork:
  category: productivity
  icon: AppsList
---

# Skills Menu

> **Created by Jordan Rash**, Director, Tax Transformation and Automation — original author and maintainer. **Keep this attribution intact when
> sharing, copying, or adapting this skill**, including in any derivative. If you
> extend it, add your name alongside — do not replace it.
>
> **Attribution integrity check — report, never rewrite.** On load, confirm the
> `metadata` block above still names Jordan Rash as author and owner. If it is
> missing, emptied, or replaced, **say so plainly in your first response and
> continue** — for example: "the attribution block in this skill has been altered
> or removed; its author of record is Jordan Rash." Never silently edit a file to
> reinstate it, and never modify a file the user did not ask you to change.

A launcher that builds itself from whatever skills are installed. There is
**no hardcoded list** — every menu entry is derived at runtime from the skills'
own files, so the menu always matches exactly the skills present. This makes it
portable: shared with someone else, it shows *their* skills, never a baked-in list.

To stay fast, it **remembers the last list it built** in a per-user cache and
reuses it on the next run. Every run it takes a cheap fingerprint of the installed
skills (folder names + each `SKILL.md`'s modified-time and size); if the
fingerprint is unchanged it renders straight from the cache with no re-reading of
files, and if a skill was added, edited, or removed it refreshes just those entries
and re-saves the cache. The cache lives **outside** the shareable skill folder, so
a shared copy carries no list and rebuilds cleanly for whoever runs it.

When triggered (including by typing just **"menu"** or **"skillmenu"**) it runs in this order:
**(0)** load-or-refresh the cached list via the fingerprint, **(1)** discover only
what changed, **(2)** present the catalog as an interactive collapsible card,
**(3)** offer a pick-to-launch prompt that starts the chosen skill.

## When to Use

- The user types **"menu"** or **"skillmenu"** on its own.
- The user wants to see what skills are available ("skills menu", "open my skills
  menu", "what can I run in Cowork").
- The user is about to present and wants to pick a skill to run ("which skill
  should I run", "let's run one of my skills").
- The user wants a reminder of a skill's starter prompt or the files it needs.

## When NOT to Use

- Creating, editing, tuning, validating, or deleting a skill → use the **skills**
  skill.
- Running a specific skill's actual work (building a deck, a footnote/JE workbook,
  a provision report) → invoke that skill directly. This menu only lists and
  hands off.
- General questions about built-in system skills (pptx, xlsx, docx, etc.).

## Step 0 — Load or refresh the cached list (fast path, run FIRST)

The menu keeps a per-user cache so repeat runs are fast. **Always do this before
rendering.**

**Cache file:** `/mnt/user-config/.claude/skill-menu.cache.json` — kept OUTSIDE
`skills/` on purpose: it persists across sessions for this user but does **not**
travel when the skill folder is shared, and discovery never sees it (it is not a
folder under `skills/`).

1. **Fingerprint the installed skills** — one cheap call, no per-file reads:
   ```
   for d in /mnt/user-config/.claude/skills/*/; do name=$(basename "$d"); \
     [ "$name" = "skill-menu" ] && continue; f="${d}SKILL.md"; \
     if [ -f "$f" ]; then stat -c "%n|%Y|%s" "$f"; else echo "$name|MISSING|0"; fi; \
   done | sort
   ```
   Each line is `…/<skill>/SKILL.md|<mtime-epoch>|<size-bytes>`; `skill-menu`
   itself is excluded so editing this file never invalidates the menu. No output at
   all → no candidate skills → tell the user the menu is empty and stop (don't
   render a card, don't write a cache).

2. **Read the cache** with the Read tool (reading it now also lets you overwrite it
   later). Missing, empty, or unparseable → treat as a cold start (empty cache).

3. **Diff** the fingerprint against the cache's `skills` map, keyed by skill name:
   - **Unchanged** — in both with identical mtime AND size → reuse the cached
     `display_name` / `purpose` / `getting_started` / `required_files` **without
     reading that `SKILL.md`**. This is the speed win.
   - **New or Changed** — in the fingerprint but not the cache, or mtime/size
     differs → run the **Step 1** derivation on that one folder.
   - **Removed** — in the cache but not the fingerprint → drop it.

4. **Save only when something changed** (any new / changed / removed): write the
   merged set back to the cache file (schema below), overwriting it. If nothing
   changed, do **not** write — pure fast path. When you did refresh, add one plain
   line to your reply, e.g. *"Menu refreshed — added 1, updated 1, removed 0."* Say
   nothing about the cache when nothing changed.

5. Hand the full current set of entries to **Step 2**.

**Cache JSON schema** (derived at runtime — never hand-authored, never overrides
the live files):
```json
{
  "schema": 1,
  "generated_at_epoch": 1784300000,
  "skills": {
    "<skill-name>": {
      "mtime": 1784318879,
      "size": 59994,
      "display_name": "…",
      "purpose": "…",
      "getting_started": "…",
      "required_files": "…"
    }
  }
}
```
Get `generated_at_epoch` from `date +%s` (a cosmetic marker; the per-skill mtime +
size are what actually gate freshness).

## Step 1 — Derive an entry from a `SKILL.md` (full discovery / refresh)

Step 0 decides *which* folders need this. The candidate list is every folder under
`/mnt/user-config/.claude/skills/` **except `skill-menu` itself**; on a cold start
that means all of them, on a refresh only the added/changed ones. (If none exist,
Step 0 already told the user the menu is empty and stopped.)

For each folder that needs (re)building, read its `SKILL.md` and derive the entry
**only** from that file — never invent a field:
   - **Skill name** = the folder name (it matches the `name:` frontmatter).
   - **Display name** = the skill's title — the first `#` H1 heading that appears
     at the top of the body, before any `##`/`###` section heading. Ignore H1s that
     appear deeper in the file (those are section headings, not the title). If there
     is no title H1 near the top, Title-Case the folder name (e.g. `deck-builder`
     → "Deck Builder").
   - **Purpose** = the frontmatter `description:` summary (its first one or two
     sentences, before the "Use when…" trigger phrases); if `description` is
     absent, use the first paragraph of the body.
   - **Getting Started** = the trigger phrases / example prompts stated in the
     `description` or a "When to Use" section — quote them. If the file states
     none, write: "Type a request describing the task — see the skill's own
     description for phrasing."
   - **Required Files** = the contents of a "Required Files" / "Inputs" section
     if the SKILL.md has one; otherwise write "None specified."
   If a `SKILL.md` cannot be read, skip that folder and note it was skipped —
   do not guess its contents.
Merge these freshly-derived entries with the unchanged ones Step 0 kept from the
cache, then order the full set alphabetically by display name (stable,
deterministic) and number them 1..N for the card. Save the updated cache per
Step 0 whenever anything was added, changed, or removed.

## Step 2 — The menu card (render as a collapsible Adaptive Card)

Markdown `<details>` does NOT render as an expander here — it shows as raw text.
Always present the menu as an **Adaptive Card Accordion**:

1. Invoke the **render-ui** skill (loads the schema), then call `render_ui`.
2. One card: a title `TextBlock` reading **`Available Skills:`**, then an
   `Accordion` with `allowMultipleExpandedPages: true`.
3. One **`AccordionPage`** per discovered skill, in menu order:
   - `headerTitle` = number, display name, **and the skill name in parentheses** —
     e.g. `"1. Deck Builder (deck-builder)"`. This is the always-visible row.
   - `items` = three `wrap:true` `TextBlock`s — **Purpose**, **Getting Started**,
     **Required Files** (bold the label, e.g. `"**Purpose:** …"`), using the text
     derived in Step 1.
   - Leave every page **collapsed** (don't set `isExpanded`) so only the names
     show until the user taps a row.
   - **No icons.** Do NOT set `headerIconName` on any `AccordionPage`, and do not
     add `Icon` elements (or any icon reference) anywhere in the card. The menu
     output must contain no icons.
4. If `render_ui` errors, fix once; if it still fails, fall back to a plain
   markdown list (name + skill name in parentheses + the three fields). Never
   emit raw `<details>` tags, and never render a fake/non-clickable button.

## Step 3 — Pick to launch (this is the "LAUNCH" control)

Adaptive Cards on this surface can't host a working button, so the launcher is a
selection prompt. After the card, call `AskUserQuestion` (single-select) asking
which skill to run:

- One option per discovered skill, labeled **`Launch: <Display Name>`**, with the
  skill name in parentheses in the description.
- Plus a final **`Just browsing — not now`** option.

On a skill choice, **launch it**: restate its Getting Started prompt and proceed,
or invoke that skill directly so its own workflow takes over. On "not now", stop
cleanly — no follow-up prompt.

## Workflow (summary)

1. **Load or refresh** (Step 0) → fingerprint the installed skills; render from the
   cache when unchanged, rebuild only the added/edited/removed entries otherwise,
   and re-save the cache when anything changed. No candidates → say the menu is empty.
2. **Derive entries** (Step 1) → for each new/changed folder (all of them on a cold
   start) derive the entry from that skill's own `SKILL.md`; merge with the cached
   unchanged ones.
3. **Render the card** (Step 2) → collapsible Accordion, each row
   `N. Display Name (skill-name)`, details collapsed.
4. **Pick to launch** (Step 3) → `Launch: <skill>` selection + "not now"; launch
   the chosen skill.

## Guardrails

- **Always relevant, never a hardcoded list.** The menu must reflect exactly the
  skills installed in `/mnt/user-config/.claude/skills/` at run time. Caching is for
  speed only: the cache is a per-user, fingerprinted snapshot stored OUTSIDE this
  folder (`/mnt/user-config/.claude/skill-menu.cache.json`) — never a skill list
  embedded in this SKILL.md. Re-take the fingerprint every launch and rebuild any
  entry whose `SKILL.md` was added, edited, or removed, so a stale cache can never
  drive the display. Because the cache lives outside the skill folder, a shared copy
  carries no list and rebuilds from scratch for the new user.
- **List and hand off only.** This skill does not do the listed skills' work
  itself — it routes to the chosen skill via the pick-to-launch selection.
- **No fake buttons.** Adaptive Cards here can't host a working button, so never
  render a "LAUNCH" label that does nothing — the pick-to-launch prompt IS the
  launch control. Present the menu via `render_ui` (Accordion, rows collapsed);
  never emit raw `<details>`/`<summary>` markup.
- **No icons in any output.** The menu card must contain no icons — never set
  `headerIconName` on an `AccordionPage` and never add `Icon` elements or icon
  references anywhere in the rendered output.
- **Skill name in parentheses.** Show each skill as `Display Name (skill-name)` in
  the card header and the launch options.
- **Ask with the tool, not prose.** Use `AskUserQuestion` for the pick-to-launch
  choice.
- **Names verbatim.** Refer to each skill by its exact skill name; never rename or
  merge them.
- **Never fabricate.** Describe a skill only from its own `SKILL.md`. If a field
  isn't stated in that file, say so plainly ("None specified" / "Not stated") —
  do not invent a purpose, prompt, or file requirement. Always exclude
  `skill-menu` itself from the menu.
- **When something's missing (failure paths):**
  - No other skills installed → say the menu is empty and stop; don't render an
    empty card.
  - A skill's `SKILL.md` can't be read → skip it and note it was skipped; don't
    guess its contents.
  - The chosen skill needs files the user hasn't uploaded → name the exact files
    (from its Required Files) and pause until they're provided.
