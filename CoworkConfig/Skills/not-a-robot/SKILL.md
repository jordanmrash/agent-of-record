---
name: not-a-robot
description: >-
  Make writing sound like a real person, not a robot. Strips "AI slop", consulting and
  corporate jargon, and the full catalog of AI-writing tells, then adds real voice — without
  ever inventing facts. Runs consent-gated and interactive: asks before starting, flags each
  robotic passage with reword options, and ends with an overused-words report.
  Use when the user says "make this sound human", "does this sound AI-generated", "de-AI this",
  "humanize this", "make this less robotic", "cut the jargon", "make this sound like me",
  "clean up this email", or "tighten this up".
  Do NOT use to draft from scratch — a client tax email (use tax-client-emails), a team update
  (use stakeholder-comms), or a memo or doc file (use docx). It only refines existing text.
license: MIT
metadata:
  author: "Jordan Rash"
  version: "3.0"
  author-role: "Director, Tax Transformation and Automation"
  created-by: "Jordan Rash — original author and maintainer"
  owner: "Jordan Rash"
  attribution: "Created by Jordan Rash, Director, Tax Transformation and Automation."
cowork:
  category: writing
  icon: TextGrammarWand
---

# Not a Robot

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

## Purpose

Not a Robot takes writing that sounds machine-made — stiff, generic, over-polished, jargon-stuffed — and makes it read like a real, capable person wrote it. Specifically, like Jordan.

It does two things at once:

1. **Removes the tells.** Consulting and corporate jargon, plus the full catalog of AI-writing patterns (below).
2. **Adds a pulse.** Clean-but-lifeless writing is just as obviously non-human as slop. The goal isn't sterile — it's human.

And it does this **with the user in the loop**: it asks before it runs, walks each robotic passage with real choices instead of silently rewriting, and ends with a warning report of overused words.

## Two Unbreakable Rules

1. **Meaning is preserved and nothing is invented.** No new facts, numbers, dates, names, sources, citations, quotes, commitments, or conclusions. No dropped caveats, risks, or qualifiers. Making something sound human must never change what it says. (See the fabrication warning under Guardrails — it is the one place this skill's own pattern library can bite you.)
2. **The user decides.** This skill proposes; it does not overwrite the user's words without a choice.

## Invocation and Consent Behavior

**Ask permission before running — every time**, even when the request clearly implies it.

### Gate 1 — ask before running

When the skill is triggered, do **not** rewrite anything yet. Confirm in one short line, naming the target:

> This looks like a good candidate for a de-robot pass. I'll scan it for anything that sounds AI-generated or jargony, then walk you through each spot with options — nothing changes without your call. Want me to go ahead?

- Yes → run the analysis.
- No → stop; continue with the original request untouched.
- "Just do it, don't ask each time" (said this session) → you may skip Gate 1 for the rest of the session, but still run the Gate 2 review.
- No obvious target text → ask which text (a pasted draft, a specific email, a Teams message, a file in `input/`).

### Gate 2 — interactive review, one passage at a time

After approval, analyze and present the review below. Never return a silently rewritten version.

## Workflow

1. **Get the text.** Use the pasted draft. If the user points at an email or Teams message, read it first (`GetMessage` / `ListMessages` / `ListChatMessages`). If a file, read it from `input/`.
2. **(Optional) Refresh the voice.** If the user says "match how I've been writing," sample recent sent mail and Teams (`ListMessages` on `sentitems`; `SearchM365` with `from_user` on Teams). **Skip any sample that is itself pervasively jargon-heavy** — those aren't good voice models. If sampling adds nothing, rely on the Voice Profile below.
3. **Detect** every passage that trips the Detection Library (below) — jargon, an AI tell, over-hedging, a formatting tell, chatbot residue, or anything that just doesn't sound like Jordan. Mark each with a short quote so the user knows exactly where it is.
4. **Present each flagged passage with two options** (Gate 2 format). Offer two more if asked.
5. **Apply the user's choices exactly.** Keep = leave verbatim. Never merge in an unpicked option.
6. **Run the overused-words warning report** across the whole document.
7. **Return the final text** reflecting the choices, then the warning report.

### Gate 2 review format

Handle flagged passages **in order, one at a time** (or small numbered batches for long text):

```
Passage 1 of N — sounds AI-generated (rule of three + promotional)
Original:
  "Our robust, end-to-end solution leverages cutting-edge automation to unlock
   seamless value across the tax lifecycle."

Option A (plain / direct):
  "Our tool automates the manual steps in the tax process."

Option B (closer to your voice):
  "This automates the parts of the tax process your team does by hand today."

Keep as-is, use A, use B, or see two more?
```

- More → give **Option C** and **Option D**, materially different from A/B and each other.
- Loop on that passage until the user picks or says keep.
- Make the two options differ usefully (A = plainest/shortest; B = warmest/closest to Jordan).

### Overused-words warning report

After the passage review, scan the whole document and flag any word or phrase used **3+ times**, anything on the jargon/AI-tell lists, and any repeated sentence opener. Short table:

```
⚠️ Overused words & phrases
| Word / phrase              | Count | Note / suggestion                       |
|----------------------------|-------|-----------------------------------------|
| leverage                   | 4     | Replace with "use"                      |
| robust                     | 3     | Say what you mean (reliable? thorough?) |
| "It's important to note"   | 2     | Cut — throat-clearing                   |
| Sentences opening "This"   | 3     | Vary the openers                        |
```

If nothing is overused: "No overused words or jargon flags — this one reads clean."

---

## Detection Library

Flag and offer to fix anything below. When a flagged word is genuinely the right **technical term** ("apportionment," "unitary," "provision," "workpapers," "robust" in an engineering spec), keep it — the target is empty buzzwords, not precise vocabulary.

### A. Business & consulting jargon → plain words
leverage→use · utilize→use · facilitate→help/run · operationalize→set up · synergy→(say the actual benefit) · holistic→whole · robust→(reliable/thorough) · seamless→smooth · streamline→simplify · optimize→improve · circle back→follow up · deep dive→look closely · drill down / double-click→dig into · level-set→get aligned · socialize→share · take offline→discuss separately · low-hanging fruit→quick wins · move the needle→make a difference · boil the ocean→do too much at once · north star→goal · value-add→(the specific benefit) · best-in-class / world-class / best practice→(what makes it good) · bandwidth→time/capacity · wheelhouse→area · heavy lift→a lot of work · ask (noun)→request · spend (noun)→cost · learnings→lessons · cadence→schedule · touchpoint→check-in · transformative→(describe the change) · journey→(cut) · unlock/unleash→(cut) · empower→let/help · drive value→produce/lead to · end-to-end→start to finish · turnkey→ready to use · scalable→(can grow) · granular→detailed · ecosystem/landscape→(be literal) · game-changing / cutting-edge / paradigm shift / mission-critical / thought leadership / table stakes→(cut or state the plain fact) · "please do not hesitate to reach out"→"let me know"

### B. AI content tells
- **Inflated significance / legacy.** "stands as a testament," "marks a pivotal moment," "a lasting impact," "the evolving landscape," "setting the stage for." → State the plain fact. *"marks a pivotal moment in regional statistics" → "was created to publish regional statistics."*
- **Promotional / brochure language.** "nestled in the heart of," "boasts," "vibrant," "breathtaking," "renowned," "rich cultural heritage," "must-visit." → Neutral description.
- **Superficial "-ing" tails.** Sentences padded with "…, highlighting…," "…, ensuring…," "…, reflecting the community's deep connection." → Cut the tail or make it a plain clause.
- **Vague attributions / weasel words.** "Experts believe," "Industry reports suggest," "Observers have noted," "several sources." → Name the real source **only if the writer actually has it**; if not, cut the claim. **Never invent a source or citation to replace the vague one.**
- **Formulaic "Challenges / Future Outlook" sections.** "Despite these challenges…, it continues to thrive." → Cut the filler; keep only concrete specifics.
- **Negative parallelism.** "It's not just X, it's Y," "not only… but also." → Say the point once, directly.
- **Rule of three.** Forced trios: "innovation, inspiration, and industry insights." → Use the number of items that's actually true, often one or two.
- **Elegant variation (synonym cycling).** "the protagonist… the main character… the central figure… the hero." → Pick one term and reuse it.
- **False ranges.** "from the Big Bang to dark matter," "from strategy to execution" where the ends aren't a real scale. → Just list what's covered.
- **Copula avoidance.** "serves as," "stands as," "boasts," "features," "represents" where "is / has" is meant. → Use "is / are / has."
- **AI vocabulary tells (high co-occurrence):** additionally, moreover, delve, intricate, interplay, tapestry, underscore, testament, pivotal, showcase, foster, garner, enduring, vibrant, crucial, align with. → Cut or swap for a plain word.
- **Filler phrases.** "in order to"→"to" · "due to the fact that"→"because" · "at this point in time"→"now" · "has the ability to"→"can" · "it is important to note that the data shows"→"the data shows."
- **Excessive hedging.** "It could potentially possibly be argued that it might…" → "It may…" Keep *real* caveats; cut stacked empty ones.
- **Generic positive conclusions.** "The future looks bright; exciting times lie ahead." → Cut, or replace with a concrete fact the source already contains — never a fabricated one.

### C. Formatting & mechanical tells
- **Em-dash overuse.** Multiple —dramatic— dashes per paragraph → commas, periods, or parentheses.
- **Boldface overuse.** Mechanically bolded phrases mid-sentence → normal text; bold only a true heading.
- **Inline-header bullet lists.** "**Performance:** Performance was improved…" repeated per bullet → fold into prose or plain bullets without the bolded colon-headers.
- **Title Case Headings.** "Strategic Negotiations And Global Partnerships" → sentence case.
- **Emojis** decorating headings/bullets (🚀 ✅ 💡) → remove for business writing.
- **Curly quotes** (" " ' ') where straight quotes are the house style → straighten. (Watch this when text was pasted from a chatbot.)

### D. Chatbot residue
- **Collaborative artifacts.** "Certainly!," "Of course!," "I hope this helps," "Would you like me to…," "Here is a…" left inside the content → delete.
- **Knowledge-cutoff disclaimers.** "As of my last update," "While specific details are limited…" → delete; keep only what's actually known.
- **Sycophancy.** "Great question!," "You're absolutely right," "That's an excellent point." → delete.

---

## Add a Pulse (voice, bounded by the facts)

Removing tells is only half the job. Sterile, uniform writing reads as machine-made too. Add voice — **scaled to the audience, and never by inventing content.**

- **Vary the rhythm.** Short, punchy sentences. Then a longer one that takes its time. Don't let every sentence run the same length.
- **Let a real opinion or reaction show** where it's appropriate ("this one's worth flagging," "I'd push back on the timeline"). Judgment the writer actually holds — not manufactured drama.
- **Use "I" / "we" when it's honest.** "I think we should…," "here's what I'd watch," reads like a person, not a press release.
- **Allow a little human texture** — a brief aside, a plain admission ("this part is still rough"). Perfect symmetry feels algorithmic.
- **Be specific over vague** — but only with specifics the source already contains. "This is concerning" → name the concrete thing the writer already identified, not an invented one.

**Audience dial:**
- **Internal / casual (teammates, Teams):** more voice, contractions, brevity, the occasional "Hola" / "Outstanding!" — match how Jordan actually writes.
- **Client-facing / formal / tax / audit:** dial voice *down*. Warm and human, yes — but accuracy, diplomacy, and preserved caveats come first. Never trade correctness for personality here.

## Jordan's Voice Profile (learned from real Outlook + Teams)

Default to this unless the user asks for a different voice. His real writing is already clean and jargon-light — match it, don't inflate it.

- **Greetings:** `Hi [First],` (default) · `Hello [First],` / `Hello all,` (group) · `Hola,` (casual).
- **Sign-offs:** `Thanks!` (go-to) · `Thank you!` / `Thank you.` Short. No "Warm regards" unless asked.
- **How he sounds:** short plain sentences; contractions everywhere; first person and direct; the ask stated plainly, then lightly softened.
- **Softeners:** "just wanted to send a quick reminder," "sooner rather than later," "if you could please," "when you get a chance."
- **Check-ins:** "just wanted to check in," "touch base with you on," "Hope all is well."
- **Human tells:** "Sorry for the delay," "the day got away from me," "totally fine," "Outstanding!," "here you go," and on Teams the occasional lowercase "i'll / i'm."
- **Structure:** greeting → one line of context → the ask → thanks; numbered list for multiple items; Teams even shorter.
- **Keep-list (authentic to Jordan — do NOT flag as jargon):** `touch base`, `check in`, `regroup`, `sooner rather than later`, `Hope all is well`, `just wanted to`, `Thanks!`, `Hola`, `from a high level`, `workplan`, `quick reminder`.

## Output Rules

- Default output: the reviewed final text (reflecting the user's choices), then the overused-words report.
- No commentary unless the user asks, the rewrite changed structure materially, or you spotted a possible unsupported claim, dropped caveat, or missing context — flag those.
- If the user asks for options up front instead of the interactive review, give up to three clearly different full versions: **Concise**, **Warm**, **Direct**.

## When NOT to Use

This skill only *refines text that already exists.* It never drafts from scratch and owns no document type. Hand off when:

- **Drafting a client tax email from nothing** → **tax-client-emails** (polish the draft here afterward).
- **Drafting a leadership update, announcement, or stakeholder status from nothing** → **stakeholder-comms**.
- **Producing a formal document, memo, letter, SOP, or report as a saved file** → **docx**. **Slides** → **pptx**. **Spreadsheets** → **xlsx**.
- The user wants substantive editing (new content, restructured argument, fact-checking) rather than tone/voice — that's a writing task, not de-roboting.

If the user is *creating* something new, route to the skill that owns it, then offer a de-robot pass.

## Guardrails

- **Never fabricate — and beware the pattern library's own trap.** Several tells above are fixed by "replace the vague thing with a specific one." Do that **only** with specifics already in the source. Do **not** invent a date, a citation ("according to a 2019 survey…"), a statistic, a measurement, a named source, or a quote to make a sentence sound more concrete. If the specific isn't in the source, cut the vague claim instead of inventing a real-sounding one.
- **Preserve substance.** Keep every caveat, qualifier, risk, dependency, uncertainty, and required action. Don't soften a real risk or a firm ask into vagueness.
- **Preserve confidentiality.** Privileged, confidential, client, tax, legal, or audit content stays as-is; don't expand or restate beyond what's needed.
- **No AI-detection claims.** Don't help misrepresent authorship or claim the output "beats AI detectors." Rewrite for genuine clarity and voice — and say so if the user frames it as detector-evasion.
- **Meaning over style.** If sounding more human would change the meaning, keep the meaning and flag the tension.
- **User's choice is final.** Apply exactly what's picked. "Keep as-is" means untouched.

## Failure Handling / Edge Cases

- **No text provided** → ask which text (pasted draft, a specific email/Teams message, or a file in `input/`). Don't invent a sample.
- **Already clean or very short** → say it reads fine; don't manufacture flags to look busy.
- **Pervasively jargon-heavy source** → review it, but tell the user it needs a heavier rewrite; consider offering the three-version option instead of dozens of prompts.
- **A referenced email/message can't be read** → say so and ask for the pasted text.
- **Ambiguous audience/tone** → default to Jordan's professional voice; only ask if it would materially change the rewrite (external client vs. internal teammate).
- **User declines at Gate 1** → drop it and continue with their original request.

## Credits

Detection taxonomy adapted from [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) (WikiProject AI Cleanup) and the open-source `humanizer` skill by @blader, combined with Jordan's own voice and a consent-gated, no-fabrication workflow.
