# Firecrawl-Powered Per-Company Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the search-snippet-based signal gathering in the `find-leads` skill's per-company research pipeline (stages 1–3) with Firecrawl CLI calls (`search`, `scrape`, `map`) that pull full page content from the candidate's own site, while keeping the same call budget, ICP model, scoring rubric, and CSV schema unchanged.

**Architecture:** This is a prompt-driven Claude Code skill — the "implementation" is entirely edits to `.claude/skills/find-leads/SKILL.md`'s instructions for research subagents. No application code changes (scoring/CSV/report scripts are untouched). Verification is manual: run the actual `firecrawl` CLI commands the updated instructions describe, against real company sites, and confirm the output is usable.

**Tech Stack:** Firecrawl CLI (`firecrawl search|scrape|map|--status`, via `Bash(firecrawl *)`), existing Python helper scripts (unchanged), markdown skill instructions.

## Global Constraints

- Firecrawl targets are limited to the candidate's own public domain and public press/news — never LinkedIn, Crunchbase paid pages, LinkedIn Sales Navigator, or any gated/auth-walled site.
- Never pass `--redact-pii` to `firecrawl scrape` — it risks stripping the buyer's name, which the skill deliberately keeps (name + title only, no email/phone).
- A single failed or thin/empty Firecrawl call never fails a company's research outright — retry once with `--wait-for 3000`, then fall back to Claude's built-in `WebSearch` for that one step.
- If Firecrawl is unavailable for the whole run (no `FIRECRAWL_API_KEY`, CLI not installed) — checked once via `firecrawl --status` at the start of a run — the entire run falls back to `WebSearch` for every step, not per-company.
- Net call budget stays ~4 Firecrawl calls per fully-researched company (1 search + up to 2 scrapes + 1 search), comparable to today's up-to-5 built-in searches.
- ICP definitions, scoring rubric (`scripts/scoring.py`), classification field values, CSV schema (`scripts/csv_store.py` `FIELDNAMES`), and status lifecycle are unchanged — this plan touches only `SKILL.md`'s research-gathering instructions.

---

### Task 1: Add centralized "Firecrawl usage" section to SKILL.md

**Files:**
- Modify: `.claude/skills/find-leads/SKILL.md:15` (insert new section between the end of "## Paths" at line 14 and "## The ICP" at line 16)

**Interfaces:**
- Consumes: none
- Produces: a "## Firecrawl usage" section that Tasks 2–4's stage rewrites reference by name instead of repeating the preflight/fallback/allowed-targets/PII rules inline.

- [ ] **Step 1: Insert the new section**

Insert this block after line 14 (`- Scripts: ...`) and its trailing blank line 15, before `## The ICP`:

```markdown
## Firecrawl usage

Research subagents use the Firecrawl CLI (`firecrawl search|scrape|map`) instead of Claude's built-in `WebSearch` for the per-company pipeline below. Write Firecrawl output to `.firecrawl/` and read it back with `grep`/`head` rather than dumping full page content into context.

- **Preflight (once per run, not per company).** Run `firecrawl --status`. If it reports not authenticated or the CLI isn't found, note "Firecrawl unavailable — falling back to WebSearch for this run" and use Claude's built-in `WebSearch` for every stage below, for every company, for the rest of the run. Do not fail the run.
- **Allowed targets.** Only the candidate's own domain and public press/news pages ever get passed to `firecrawl search`/`scrape`/`map`. Never LinkedIn, Crunchbase paid pages, LinkedIn Sales Navigator, or any gated/auth-walled site.
- **Never use `--redact-pii`** on `firecrawl scrape` calls — it risks stripping the buyer's name, which this skill deliberately keeps (name + title only). The no-email/no-phone rule is enforced when writing the CSV row, not by this flag.
- **Per-call fallback.** If a single `firecrawl` command fails (blocked, timeout, rate-limited) or returns thin/empty content, retry once with `--wait-for 3000`; if it still fails or is still thin, fall back to `WebSearch` for that one step only. One bad Firecrawl call never fails the whole company.
```

- [ ] **Step 2: Verify placement**

Run: `grep -n "^##" ".claude/skills/find-leads/SKILL.md" | head -6`
Expected output shows, in order: `## Paths`, `## Firecrawl usage`, `## The ICP` (and the section starts and ends with correct blank-line spacing — no `##` header glued to the preceding paragraph).

- [ ] **Step 3: Commit**

```bash
cd "F:/_WORKY/blindsight/GITHUB/lead-gen"
git add .claude/skills/find-leads/SKILL.md
git commit -m "feat(find-leads): add centralized Firecrawl usage rules to SKILL.md"
```

---

### Task 2: Rewrite Stage 1 triage to use `firecrawl search`

**Files:**
- Modify: `.claude/skills/find-leads/SKILL.md:98` (the "Stage 1 triage (1 search)" line inside "## Per-company pipeline")

**Interfaces:**
- Consumes: "## Firecrawl usage" section from Task 1 (referenced, not repeated)
- Produces: none consumed elsewhere by name — Stage 1's job (produce a Poor-fit-or-continue decision) is unchanged, only its implementation.

- [ ] **Step 1: Replace line 98**

Current line 98:
```
2. **Stage 1 triage (1 search).** Do one broad web search on the company. If it's clearly a hard disqualifier — a government entity, not an active business, wildly outside the ~20–200 employee range, or a pre-seed startup with no AI angle at all — stop here. Set `icp_match: "Poor fit"` and don't spend further search budget on this company; it doesn't count toward `discover`'s target.
```

Replace with:
```
2. **Stage 1 triage (1 call).** Run `firecrawl search "<company name>" --scrape -o .firecrawl/<domain>-stage1.json --json` (see "Firecrawl usage" above for the preflight/fallback/allowed-targets rules). If it's clearly a hard disqualifier — a government entity, not an active business, wildly outside the ~20–200 employee range, or a pre-seed startup with no AI angle at all — stop here. Set `icp_match: "Poor fit"` and don't spend further budget on this company; it doesn't count toward `discover`'s target.
```

- [ ] **Step 2: Verify the edit**

Run: `grep -n "Stage 1 triage" ".claude/skills/find-leads/SKILL.md"`
Expected: one match, on line 98, containing `firecrawl search` and `--scrape`.

- [ ] **Step 3: Commit**

```bash
cd "F:/_WORKY/blindsight/GITHUB/lead-gen"
git add .claude/skills/find-leads/SKILL.md
git commit -m "feat(find-leads): use firecrawl search for stage 1 triage"
```

---

### Task 3: Rewrite Stage 2 to on-site scraping (homepage + follow-up, with map escalation)

**Files:**
- Modify: `.claude/skills/find-leads/SKILL.md:99` (the "Stage 2 triage (up to 3 more searches...)" line)

**Interfaces:**
- Consumes: "## Firecrawl usage" section from Task 1
- Produces: none consumed elsewhere by name

- [ ] **Step 1: Replace line 99**

Current line 99:
```
3. **Stage 2 triage (up to 3 more searches, 2–4 total).** Search for AI-native product signals, regulated/sensitive-data handling, and agent/agentic-workflow signals (company site, news, job postings) — this single set of searches informs `ai_native_maturity`, `regulatory_data_exposure`, and `agent_deployment_stage` all at once, no separate search budget per dimension. If by search 4 there's no signal on any of the three, stop and record it under `skipped` with reason "Weak signal / insufficient public info".
```

Replace with:
```
3. **Stage 2 on-site research (up to 2 calls, 3 total).** Scrape the candidate's homepage: `firecrawl scrape "<homepage-url>" --only-main-content --format markdown,links -o .firecrawl/<domain>-home.md`. From the links it returns, pick the 1–2 most promising on-site pages (About/Team for buyer info, Careers for agent/AI hiring signal, Product for AI-native depth) and scrape them together: `firecrawl scrape "<url1>" "<url2>" -o .firecrawl/`. Together these inform `ai_native_maturity`, `regulatory_data_exposure`, `agent_deployment_stage`, `buyer_name`, and `buyer_title` — no separate call budget per dimension. If the homepage scrape surfaces no useful on-site links (single-page site, JS-rendered nav not present in the scraped links list), escalate to `firecrawl map "<homepage-url>" --search "about"` (or `"careers"`) to locate the page directly, then scrape it — this is the exception path, not the default. If there's still no signal on any of the three core dimensions after this stage, stop and record it under `skipped` with reason "Weak signal / insufficient public info".
```

- [ ] **Step 2: Verify the edit**

Run: `grep -n "Stage 2" ".claude/skills/find-leads/SKILL.md"`
Expected: one match, on line 99, containing `firecrawl scrape` and `firecrawl map`.

- [ ] **Step 3: Commit**

```bash
cd "F:/_WORKY/blindsight/GITHUB/lead-gen"
git add .claude/skills/find-leads/SKILL.md
git commit -m "feat(find-leads): use firecrawl scrape for stage 2 on-site research"
```

---

### Task 4: Rewrite Stage 3 (full research) to use `firecrawl search` for off-site signals

**Files:**
- Modify: `.claude/skills/find-leads/SKILL.md:100` (the "Full research (up to 1 more search, 5 total)" line)

**Interfaces:**
- Consumes: "## Firecrawl usage" section from Task 1; assumes Stage 2 (Task 3) already ran and may have found buyer/geo info on-site
- Produces: none consumed elsewhere by name

- [ ] **Step 1: Replace line 100**

Current line 100:
```
4. **Full research (up to 1 more search, 5 total).** Only for companies that cleared stage 2: search for a likely buyer (named CEO/CTO/technical leader from publicly published sources only — no LinkedIn scraping or gated-site access) and geography (EU vs. US vs. other, from company site/press/registration).
```

Replace with:
```
4. **Stage 3 off-site research (up to 1 call, 4 total).** Only for companies that cleared stage 2: run `firecrawl search "<company name> CEO OR CTO OR founder" --scrape -o .firecrawl/<domain>-stage3.json --json` for anything not already found on-site in stage 2 — a likely buyer (named CEO/CTO/technical leader from publicly published sources only — no LinkedIn scraping or gated-site access) and geography (EU vs. US vs. other, from company site/press/registration).
```

- [ ] **Step 2: Verify the edit**

Run: `grep -n "Stage 3" ".claude/skills/find-leads/SKILL.md"`
Expected: one match, on line 100, containing `firecrawl search` and the updated "4 total" call count.

- [ ] **Step 3: Commit**

```bash
cd "F:/_WORKY/blindsight/GITHUB/lead-gen"
git add .claude/skills/find-leads/SKILL.md
git commit -m "feat(find-leads): use firecrawl search for stage 3 off-site research"
```

---

### Task 5: Add Firecrawl-specific failure modes to the Error handling section

**Files:**
- Modify: `.claude/skills/find-leads/SKILL.md` (the "## Error handling" section, originally lines 165–174 before Tasks 1–4 shift line numbers down — locate by header text, not line number)

**Interfaces:**
- Consumes: "## Firecrawl usage" section from Task 1 (referenced, not repeated)
- Produces: none

- [ ] **Step 1: Locate the section**

Run: `grep -n "^## Error handling" ".claude/skills/find-leads/SKILL.md"`
Note the returned line number as `N`.

- [ ] **Step 2: Add two bullets immediately after the `## Error handling` header line**

Insert, right after line `N` (the header) and its blank line:
```
- **A Firecrawl call fails or returns thin/empty content** (blocked, timeout, rate-limited, unrendered SPA) — retry once with `--wait-for 3000`, then fall back to `WebSearch` for that one step. See "Firecrawl usage" above.
- **Firecrawl unavailable for the whole run** (no `FIRECRAWL_API_KEY`, CLI not installed) — detected once via `firecrawl --status` at the start of the run; fall back to `WebSearch` for every step, run proceeds normally rather than aborting.
```

- [ ] **Step 3: Verify the edit**

Run: `grep -n "Firecrawl call fails\|Firecrawl unavailable for the whole run" ".claude/skills/find-leads/SKILL.md"`
Expected: two matches, both inside the `## Error handling` section (check with `grep -n "^##" ".claude/skills/find-leads/SKILL.md"` that no other `##` header appears between them and the "Error handling" header).

- [ ] **Step 4: Commit**

```bash
cd "F:/_WORKY/blindsight/GITHUB/lead-gen"
git add .claude/skills/find-leads/SKILL.md
git commit -m "feat(find-leads): document Firecrawl failure modes in error handling"
```

---

### Task 6: Ignore Firecrawl scratch output

**Files:**
- Modify: `.gitignore:4` (append after the existing `.pytest_cache/` line)

**Interfaces:**
- Consumes: none
- Produces: none

- [ ] **Step 1: Append the ignore rule**

Current `.gitignore`:
```
.worktrees/
__pycache__/
*.pyc
.pytest_cache/
```

New `.gitignore`:
```
.worktrees/
__pycache__/
*.pyc
.pytest_cache/
.firecrawl/
```

- [ ] **Step 2: Verify**

Run: `grep -n "^\.firecrawl/$" .gitignore`
Expected: one match.

- [ ] **Step 3: Commit**

```bash
cd "F:/_WORKY/blindsight/GITHUB/lead-gen"
git add .gitignore
git commit -m "chore(find-leads): ignore .firecrawl/ scratch output"
```

---

### Task 7: Live smoke test — confirm each Firecrawl command actually works

**Files:**
- None (verification only, no file changes)

**Interfaces:**
- Consumes: the exact commands written into Tasks 1–4
- Produces: confidence that Tasks 1–4's instructions are runnable as written, before relying on a subagent to follow them

- [ ] **Step 1: Confirm Firecrawl is authenticated**

Run: `firecrawl --status`
Expected: reports `Authenticated via FIRECRAWL_API_KEY` (or a keyless free-tier notice) and a credit balance greater than 0.

- [ ] **Step 2: Run the Stage 1 command against a real company**

```bash
mkdir -p .firecrawl
cd "F:/_WORKY/blindsight/GITHUB/lead-gen"
firecrawl search "DeepJudge" --scrape -o .firecrawl/deepjudge-stage1.json --json
```
Expected: exit code 0; `.firecrawl/deepjudge-stage1.json` exists and `jq -r '.data.web[0].url' .firecrawl/deepjudge-stage1.json` returns a real URL (e.g. `deepjudge.ai` or a press mention).

- [ ] **Step 3: Run the Stage 2 homepage scrape**

```bash
firecrawl scrape "https://deepjudge.ai" --only-main-content --format markdown,links -o .firecrawl/deepjudge-home.json
```
Expected: exit code 0; the output file contains both a `markdown` field with real page text and a `links` field listing at least one internal URL (e.g. an About or Careers page).

- [ ] **Step 4: Run the Stage 2 follow-up scrape on a discovered link**

Pick one URL from Step 3's `links` output (e.g. an About/Team/Careers page), then:
```bash
firecrawl scrape "<url-from-step-3>" -o .firecrawl/deepjudge-followup.md
```
Expected: exit code 0; `.firecrawl/deepjudge-followup.md` contains readable markdown, not an error page or empty file (`wc -l .firecrawl/deepjudge-followup.md` returns more than a few lines).

- [ ] **Step 5: Run the Stage 3 command**

```bash
firecrawl search "DeepJudge CEO OR CTO OR founder" --scrape -o .firecrawl/deepjudge-stage3.json --json
```
Expected: exit code 0; output contains at least one result mentioning a named person.

- [ ] **Step 6: Send search feedback for the two search calls (per Firecrawl's own convention)**

```bash
SEARCH_ID_1=$(jq -r '.id' .firecrawl/deepjudge-stage1.json)
firecrawl search-feedback "$SEARCH_ID_1" --rating good --valuable-sources '[{"url":"https://deepjudge.ai","reason":"Primary source"}]' --silent &
SEARCH_ID_3=$(jq -r '.id' .firecrawl/deepjudge-stage3.json)
firecrawl search-feedback "$SEARCH_ID_3" --rating good --valuable-sources '[{"url":"https://deepjudge.ai","reason":"Primary source"}]' --silent &
wait
```
Expected: exit code 0 for both (feedback is best-effort per Firecrawl's own docs — a non-zero exit here doesn't block anything else).

No commit for this task — it's a live verification pass, not a file change. If any step fails, stop and fix the corresponding Task 1–4 instruction before continuing.

---

### Task 8: Known-answer comparison against existing CSV rows

**Files:**
- None (verification only)

**Interfaces:**
- Consumes: Tasks 1–6 (the fully updated `SKILL.md`)
- Produces: a documented pass/fail judgment on whether the new pipeline is a genuine improvement

- [ ] **Step 1: Re-research DeepJudge (clean marketing site) with the updated pipeline**

Invoke the `find-leads` skill with `score-list DeepJudge` (or manually walk stages 1–4 as a subagent would, using the commands from Task 7). Record the resulting classification fields, `buyer_name`, `buyer_title`, `confidence`, and `sources`.

- [ ] **Step 2: Compare against the existing row**

```bash
cd "F:/_WORKY/blindsight/GITHUB/lead-gen"
python3 -c "
import csv
with open('data/leads.csv', newline='', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if r['company_name'] == 'DeepJudge':
            print(r)
"
```
Expected: the new run's `buyer_name`/`buyer_title`/`confidence` match or improve on the existing row (e.g. `confidence` stays `high`, or a previously-`medium`/blank field becomes populated). If the new run is *worse* (lower confidence, lost buyer info), stop and revisit Task 3's stage 2 instructions before proceeding — this is a real regression signal, not noise.

- [ ] **Step 3: Repeat Steps 1–2 for one JS-heavy SPA candidate**

Pick a company from `leads.csv` whose site is a JS-rendered SPA (or pick any unresearched candidate known to use one, e.g. a company built on a modern JS framework with client-side rendering). Re-research it with `score-list`, and confirm the Task 3 `--wait-for` retry path (or the `map` escalation path) actually engages and still produces usable output — this is the case most likely to expose a gap in the Task 3 instructions.

No commit for this task.

---

### Task 9: Fallback smoke test — Firecrawl unavailable mid-setup

**Files:**
- None (verification only)

**Interfaces:**
- Consumes: Task 1's preflight instruction
- Produces: confidence that a missing/broken Firecrawl setup degrades gracefully instead of breaking the skill

- [ ] **Step 1: Temporarily unset the API key**

```bash
OLD_KEY="$FIRECRAWL_API_KEY"
unset FIRECRAWL_API_KEY
firecrawl --status
```
Expected: reports not authenticated (or drops to the keyless free tier, per the CLI's own behavior) rather than crashing.

- [ ] **Step 2: Confirm the preflight instruction would catch this**

Re-read Task 1's "Preflight" bullet and confirm its wording ("If it reports not authenticated or the CLI isn't found...") matches what Step 1's actual `firecrawl --status` output looks like when unauthenticated. If the real output doesn't clearly say "not authenticated" in a way the instruction's wording anticipates, adjust Task 1's bullet text to match the real CLI output before proceeding.

- [ ] **Step 3: Restore the key**

```bash
export FIRECRAWL_API_KEY="$OLD_KEY"
firecrawl --status
```
Expected: reports authenticated again with the original credit balance.

No commit for this task unless Step 2 required a wording fix to Task 1 — in that case, amend with:
```bash
cd "F:/_WORKY/blindsight/GITHUB/lead-gen"
git add .claude/skills/find-leads/SKILL.md
git commit -m "fix(find-leads): correct Firecrawl preflight wording to match actual CLI output"
```

---

### Task 10: Real `discover --target 5` smoke run

**Files:**
- Modify: `data/leads.csv` (new rows appended by the skill itself, not by hand)
- Create: `runs/<today's-date>-discover-smoke.md` (written by `scripts/report.py`, not by hand)

**Interfaces:**
- Consumes: Tasks 1–6 (fully updated `SKILL.md`); Task 9 confirms the fallback path works, so this run assumes Firecrawl is available
- Produces: a real run report demonstrating end-to-end quality and actual credit cost

- [ ] **Step 1: Record starting credit balance**

```bash
firecrawl credit-usage --json -o .firecrawl/credits-before.json
```

- [ ] **Step 2: Run the smoke discovery**

Invoke the `find-leads` skill with `discover --target 5`.

- [ ] **Step 3: Record ending credit balance and compute cost**

```bash
firecrawl credit-usage --json -o .firecrawl/credits-after.json
jq -r '.credits' .firecrawl/credits-before.json
jq -r '.credits' .firecrawl/credits-after.json
```
Expected: the difference is roughly `5 companies × ~4 calls × ~2 credits/call ≈ 40 credits`, give or take triage stop-outs (companies that stop at Stage 1 use far less). A wildly higher number (e.g. 10x) signals a step is being retried excessively or hitting an unintended fallback loop — investigate before running at full `discover` volume.

- [ ] **Step 4: Read the run report and confirm quality**

Read `runs/<today's-date>-discover-smoke.md`. Confirm: named buyers are present for most results, confidence is mostly `high`/`medium` (not predominantly `low`), and no gated-domain URL appears in any `sources` column.

No commit for this task — `data/leads.csv` and the run report are the skill's own working data, committed (if at all) per the team's existing convention for run outputs, not as part of this implementation plan.

---

## Self-Review

**Spec coverage:** Stage 1/2/3 tool mapping → Tasks 2–4. Preflight/allowed-targets/`--redact-pii`/per-call-fallback constraints → Task 1 (centralized) + Task 5 (error-handling bullets). `.firecrawl/` output convention → Task 1 + Task 6. Known-answer comparison, fallback test, gated-domain review, smoke run → Tasks 7–10 (the spec's four testing/validation items map 1:1 to Tasks 8, 9, 7-Step-nothing-targets-gated-domains-by-construction, and 10). No spec section is without a task.

**Placeholder scan:** No TBD/TODO; every step shows the literal command or markdown text to write, not a description of it.

**Type/name consistency:** `.firecrawl/<domain>-stage1.json`, `-home.json`, `-followup.md`, `-stage3.json` naming is consistent across Tasks 2–4 and 7. The "Firecrawl usage" section name in Task 1 is referenced identically ("see Firecrawl usage above") in Tasks 2, 3, 4, and 5 — no drift.
