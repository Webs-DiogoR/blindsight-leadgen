# Personas Source-of-Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move Blindsight's ICP tier and persona definitions out of find-leads' `SKILL.md` and into the source-of-truth docs repo, so they're visible outside lead-gen, with find-leads referencing the new canonical copy instead of embedding it.

**Architecture:** A new file, `docs/brand/personas.md` (source-of-truth repo), becomes the canonical copy of the "## The ICP" content that currently lives in `lead-gen/.claude/skills/find-leads/SKILL.md`. `SKILL.md`'s own ICP section shrinks to a pointer + tier summary table. `research-pipeline.js`'s Stage B (classify/score/persist) subagent prompt is updated to read the new file instead of `SKILL.md`'s old section, with a hard-stop (no embedded fallback) if it's unreadable.

**Tech Stack:** Markdown docs, no code changes beyond one JS prompt-string edit in an existing Workflow script (`research-pipeline.js`).

## Global Constraints

- Docs repo path (this installation): `F:\_WORKY\blindsight\GITHUB\docs`
- lead-gen repo path (this installation): `F:\_WORKY\blindsight\GITHUB\lead-gen`
- `scripts/scoring.py` hardcodes the `icp_match` enum (`ICP1`/`ICP2`/`ICP3`/`Poor fit`) — the "Classification field values" table in `SKILL.md` stays unchanged; only narrative/descriptive text moves.
- "ICP segments & weights" (40/40/20 discover-mode split) stays in `SKILL.md` — out of scope for this move (spec decision).
- No embedded fallback copy of persona content anywhere — a missing `docs/brand/personas.md` is a hard stop, not a silent guess.
- This is a prose/doc-content change with no automated test suite to extend — verification is manual diff/read checks and `node --check` for the one JS edit, per this project's existing convention for SKILL.md-only changes (see board task 0715-convert).

---

### Task 1: Create `docs/brand/personas.md` in the source-of-truth repo

**Files:**
- Create: `F:\_WORKY\blindsight\GITHUB\docs\brand\personas.md`

**Interfaces:**
- Consumes: nothing (new standalone doc).
- Produces: the canonical ICP/persona text that Task 2 will point `SKILL.md` and `research-pipeline.js` at. Any later task referencing this file uses the path `F:\_WORKY\blindsight\GITHUB\docs\brand\personas.md` (Windows) / `F:/_WORKY/blindsight/GITHUB/docs/brand/personas.md` (POSIX-style, for JS string literals).

- [ ] **Step 1: Write the file**

Create `F:\_WORKY\blindsight\GITHUB\docs\brand\personas.md` with this exact content:

```markdown
# Blindsight ICP & Personas

Canonical source of truth for Blindsight's Ideal Customer Profile tiers
and buyer personas. Consumed by lead-gen's `find-leads` skill (Stage B —
classify & persist) for lead scoring/classification; available to anyone
else doing GTM, messaging, or content work who needs the same targeting
definitions.

Three ICPs, sequenced by priority — ICP1 and ICP2 are where the team
spends now; ICP3 is a watchlist populated today but not actively closed
until the Authorization Broker is past prototype.

## ICP1 — AI-Native Product Companies (runtime security core)

Companies whose product runs on proprietary LLMs, RAG, or ML in
production, shipping AI features continuously. Size 20–200, Stage Series
A–B, Geo EU-first (Zürich base + GDPR/EU AI Act tailwind), US second.
Lead product: Runtime Security Proxy. Wedge in: ShadowAI (free demo).
Core pain: their own AI runtime is an unmonitored attack surface —
prompt injection, exfiltration, an unauthorized/unauditable agent
action.

**Personas:**
- **1A. Founder/CEO** (economic buyer) — technical, now runs the
  company, is the de facto CISO at this stage. Owns budget, investor
  relationships, the trust story. Fear: a security failure that torches
  customer trust or an unanswerable due-diligence question. Convert
  with investor optics and liability framing. Signs, but rarely finds
  you first.
- **1B. Head of Engineering/VP Eng** (technical champion) — owns AI
  systems in production, feels the black-box problem daily. No budget,
  but the door-opener and validator. Convert with mechanism/depth — the
  runtime proxy, what it catches, how it deploys. Entry point at most
  ICP1 accounts.
- **1C. AI/ML Lead or Staff ML Engineer** (hands-on user) — would
  actually run ShadowAI and read the flags. Feels the pain most, can't
  authorize a purchase. Generates internal urgency upward. Convert with
  the product experience itself.

## ICP2 — Sensitive-Data Adopters (DLP + PII wedge)

Mid-market companies handling regulated or sensitive data — fintech,
healthtech, insurtech, legaltech, HR-tech — adopting AI across internal
operations. Size 20–200, fast-moving but carrying real compliance
exposure, Geo EU-first. Lead product: ShadowAI (client-side DLP) →
Runtime Proxy once internal AI/RAG is found. Core pain: employees
pasting contracts/patient records/financials into unsanctioned AI
tools; PII leaking invisibly; GDPR/EU AI Act/HIPAA liability regardless
of intent.

**Personas:**
- **2A. CISO/Head of Security** (economic buyer) — real security
  function and compliance exposure, AI spreading faster than he can
  govern. Fear: a regulated-data leak he can't see or prove he tried to
  prevent. Convert with visibility and audit trails. Clearest budget
  holder of the nine personas.
- **2B. Head of Compliance/DPO** (co-buyer, urgency engine) — owns
  GDPR/HIPAA/EU AI Act exposure, thinks in liability/audit-readiness,
  not "security tools." Rarely initiates but can force a purchase by
  naming the risk. Convert by turning compliance into a feature. Pair
  with the CISO to move the deal.
- **2C. IT/Security Manager** (technical champion) — runs endpoint
  tooling, knows employees are pasting sensitive data but can't
  quantify it. ShadowAI hands him the number, which he takes to the
  CISO as evidence — the deal opener.

## ICP3 — Agentic Companies (seed now, convert later)

Companies deploying autonomous agents in production — agents that take
actions, call tools, transact. Size 20–200, Series A–B, earliest-adopter
profile. Lead product: Authorization Broker (prototype) + Runtime Proxy
for agentic pipelines. Core pain: agents acting without authorization or
audit trail, instruction hijacking, tool-call abuse. Status:
pipeline-seeding, not active-close — build the list, warm the
relationships, sell when the product is ready.

**Personas:**
- **3A. Founder/CEO** (economic buyer) — building an agentic product,
  betting the company on autonomy. Trust/auditability existential — one
  unauthorized agent action in front of the wrong customer is
  business-ending. Convert later with Authorization Broker; warm now by
  already thinking about agent security.
- **3B. Head of AI/Agent Platform Lead** (technical champion) — owns
  agent pipelines, tool-calling, orchestration; lives closest to
  instruction hijacking and tool-call abuse. Convert with runtime proxy
  for agentic pipelines today, Authorization Broker tomorrow. The live
  relationship in ICP3 — co-designs if you show up early.
- **3C. Security Engineer** (hands-on user) — would instrument agents
  and read authorization logs. The internal signal that agent security
  is a real budget line, not a someday. Convert with mechanism/depth
  once the Broker is past prototype.

Personas are a working hypothesis — refine as real research (LinkedIn,
org charts, press) accumulates.

**Cross-cutting:** ShadowAI is the universal free wedge, not exclusive
to ICP2 — it's how you get in the door everywhere. What converts
differs: Runtime Proxy for the builders (ICP1), PII/DLP depth for the
adopters (ICP2).
```

- [ ] **Step 2: Verify the content matches the source verbatim**

Run (from the lead-gen repo, before Task 2 touches `SKILL.md`):

```
diff <(sed -n '26,59p' ".claude/skills/find-leads/SKILL.md") /dev/null
```

This just prints the old section for a manual side-by-side read against
the new `personas.md` — confirm every tier, every persona (1A–3C), the
"working hypothesis" line, and the cross-cutting note all made it across
with no wording drift beyond formatting (line-wrap width changed;
content shouldn't have).

Expected: the two texts match in substance. If anything's missing, fix
`personas.md` before continuing.

- [ ] **Step 3: Commit (docs repo)**

```bash
cd "F:\_WORKY\blindsight\GITHUB\docs"
git add docs/brand/personas.md
git commit -m "docs(brand): add Blindsight ICP tiers and buyer personas

Canonical source of truth for the ICP/persona definitions previously
embedded only in lead-gen's find-leads skill."
```

Note: check `docs/brand/personas.md` is the actual staged path (the
repo root is `docs/`, so from inside that repo the path is
`brand/personas.md` — verify with `git status` before committing; adjust
the `git add` path if the working directory differs from what's shown
above).

---

### Task 2: Point find-leads at the new source of truth

**Files:**
- Modify: `F:\_WORKY\blindsight\GITHUB\lead-gen\.claude\skills\find-leads\SKILL.md` (the "## The ICP" section, and the "## Error handling" section)
- Modify: `F:\_WORKY\blindsight\GITHUB\lead-gen\.claude\skills\find-leads\scripts\research-pipeline.js` (add a `PERSONAS_MD` path constant; update `persistPrompt`'s ICP-reading instruction)

**Interfaces:**
- Consumes: `docs/brand/personas.md` from Task 1 (path:
  `F:\_WORKY\blindsight\GITHUB\docs\brand\personas.md` /
  `F:/_WORKY/blindsight/GITHUB/docs/brand/personas.md`).
- Produces: nothing further downstream — this is the last task in the
  plan.

- [ ] **Step 1: Replace `SKILL.md`'s "## The ICP" section**

In `F:\_WORKY\blindsight\GITHUB\lead-gen\.claude\skills\find-leads\SKILL.md`,
replace the entire section from `## The ICP` (line 26) through the line
ending "...PII/DLP depth for the adopters (ICP2)." (line 59) with:

```markdown
## The ICP

Full ICP tier and persona definitions live in the source-of-truth repo:
`F:\_WORKY\blindsight\GITHUB\docs\brand\personas.md`. Three tiers,
sequenced by priority — ICP1 and ICP2 are where the team spends now;
ICP3 is a watchlist populated today but not actively closed until the
Authorization Broker is past prototype:

| Tier | Name | Lead product |
|---|---|---|
| ICP1 | AI-Native Product Companies | Runtime Security Proxy |
| ICP2 | Sensitive-Data Adopters | ShadowAI → Runtime Proxy |
| ICP3 | Agentic Companies (watchlist) | Authorization Broker (prototype) |

Stage B (classify & persist, below) must read `docs/brand/personas.md`
before assigning `icp_match`/`persona_match` — it is not optional
background reading, the classification enums require it.
```

- [ ] **Step 2: Add the missing-file error-handling bullet**

In the same file's "## Error handling" section, add this as a new bullet
(placement: anywhere in the existing list, e.g. right after the
"Firecrawl unavailable for the whole run" bullet since both are
"external dependency missing at run start" cases):

```markdown
- **`docs/brand/personas.md` unreadable** (docs repo missing, moved, or
  the path changed) — stop the run gracefully and report the expected
  path (`F:\_WORKY\blindsight\GITHUB\docs\brand\personas.md`). Never
  classify a company against guessed, remembered, or stale persona/ICP
  data — there is no embedded fallback copy by design.
```

- [ ] **Step 3: Add a `PERSONAS_MD` constant to `research-pipeline.js`**

In `F:\_WORKY\blindsight\GITHUB\lead-gen\.claude\skills\find-leads\scripts\research-pipeline.js`,
find this existing line (near the top, just above the `RESEARCH_SCHEMA`
constant):

```js
const SKILL_MD = 'F:/_WORKY/blindsight/GITHUB/lead-gen/.claude/skills/find-leads/SKILL.md'
```

Add immediately after it:

```js
const PERSONAS_MD = 'F:/_WORKY/blindsight/GITHUB/docs/brand/personas.md'
```

- [ ] **Step 4: Update `persistPrompt` to read `PERSONAS_MD`**

In the same file, find this line inside `persistPrompt`:

```js
Read ${SKILL_MD} yourself first — "The ICP" section, the "Per-company pipeline" section's Stage B (steps 5-9), the "Classification field values" table, and the "CSV row — column reference" table — for exact allowed field values and column names.${mode === 'recheck-watchlist' ? ' Also read the recheck-watchlist mode section for this mode\'s status rules.' : ''}
```

Replace it with:

```js
Read ${PERSONAS_MD} first — Blindsight's full ICP tier and persona definitions, the canonical source for classifying this company. If that file is unreadable, STOP: return status "skip" with skipReason "docs/brand/personas.md unreadable — source-of-truth repo missing/moved" instead of classifying without it.

Then read ${SKILL_MD} — the "Per-company pipeline" section's Stage B (steps 5-9), the "Classification field values" table, and the "CSV row — column reference" table — for exact allowed field values and column names.${mode === 'recheck-watchlist' ? ' Also read the recheck-watchlist mode section for this mode\'s status rules.' : ''}
```

- [ ] **Step 5: Syntax-check the script**

Run:

```bash
cd "/f/_WORKY/blindsight/GITHUB/lead-gen"
node --check ".claude/skills/find-leads/scripts/research-pipeline.js"
```

Expected: no output, exit code 0 (matches the check already used for
this file in board task 0715-convert).

- [ ] **Step 6: Manual read-through**

Re-read the full, edited `SKILL.md` "The ICP" section and "Error
handling" section top to bottom — confirm the tier-summary table reads
correctly standalone (a subagent seeing only this section, without the
old prose, should still know there are three tiers and where to find
the rest), and that the new error-handling bullet's placement doesn't
duplicate or contradict the existing "Firecrawl unavailable" bullet.

Re-read `persistPrompt`'s full template string (both the
`PERSONAS_MD`/`SKILL_MD` reads and the existing `statusRuleNote`
variable usage) to confirm the two `Read ...` sentences compose
correctly for all three modes (`discover`, `score-list`,
`recheck-watchlist`) — the recheck-watchlist-specific clause should
still only append when `mode === 'recheck-watchlist'`.

- [ ] **Step 7: Commit (lead-gen repo)**

```bash
cd "/f/_WORKY/blindsight/GITHUB/lead-gen"
git add ".claude/skills/find-leads/SKILL.md" ".claude/skills/find-leads/scripts/research-pipeline.js"
git commit -m "feat(find-leads): reference docs/brand/personas.md for ICP/persona data

SKILL.md's 'The ICP' section previously embedded all three tiers and
nine personas directly; that content now lives in the source-of-truth
repo (docs/brand/personas.md) where it's visible outside lead-gen.
Stage B's classify/persist prompt reads the new file directly, with a
hard stop (no embedded fallback) if it's unreadable.

Board task: personas-source-of-truth (see docs/superpowers/specs/2026-07-15-personas-source-of-truth-design.md)."
```

---

## Self-review notes

- **Spec coverage:** new `personas.md` file (Task 1) ✓; `SKILL.md`
  pointer + tier table (Task 2 Step 1) ✓; "Classification field values"
  and "ICP segments & weights" left untouched (no task touches them) ✓;
  `research-pipeline.js` Stage B prompt updated (Task 2 Steps 3-4) ✓;
  hard-stop-no-fallback behavior on missing file, both at the
  `SKILL.md` documentation level (Task 2 Step 2) and the actual subagent
  prompt level (Task 2 Step 4) ✓; two-repo commit boundary respected
  (Task 1 commits in `docs`, Task 2 commits in `lead-gen`) ✓.
- **Placeholder scan:** no TBD/TODO markers; every step has literal file
  content, not a description of content.
- **Type/name consistency:** `PERSONAS_MD` constant name and its value
  match between where it's declared (Task 2 Step 3) and where it's used
  (Task 2 Step 4); path casing/separators match the existing `SKILL_MD`
  constant's convention (forward slashes, same drive/path).
