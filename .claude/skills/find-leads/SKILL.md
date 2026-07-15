---
name: find-leads
description: Discover and score potential Blindsight sales leads against the company's ICP (ICP1 AI-native product companies, ICP2 sensitive-data adopters, ICP3 agentic companies/watchlist), or score a list of companies already on hand. Use when the team needs new leads, wants existing prospects ranked and classified, or needs to recheck the ICP3 watchlist.
---

# Find Leads

Discovers and/or scores companies against Blindsight's ICP (three tiers: AI-Native Product, Sensitive-Data Adopter, Agentic/watchlist), producing a persistent CSV and a per-run markdown report.

## Paths (this installation)

- Leads CSV: `F:\_WORKY\blindsight\GITHUB\lead-gen\data\leads.csv`
- Run reports: `F:\_WORKY\blindsight\GITHUB\lead-gen\runs\`
- Scripts: `F:\_WORKY\blindsight\GITHUB\lead-gen\.claude\skills\find-leads\scripts\`

## Firecrawl usage

Research subagents use the Firecrawl CLI (`firecrawl search|scrape|map`) instead of Claude's built-in `WebSearch` for the per-company pipeline below. Write Firecrawl output to `.firecrawl/` and read it back with `grep`/`head` rather than dumping full page content into context.

- **Preflight (once per run, not per company).** Run `firecrawl --status`. If it reports not authenticated or the CLI isn't found, note "Firecrawl unavailable — falling back to WebSearch for this run" and use Claude's built-in `WebSearch` for every stage below, for every company, for the rest of the run. Do not fail the run.
- **Allowed targets.** Only the candidate's own domain and public press/news pages ever get passed as explicit URLs to `firecrawl scrape`/`map`, or named in a `firecrawl search` query. Never LinkedIn, Crunchbase paid pages, LinkedIn Sales Navigator, or any gated/auth-walled site. Note: `search --scrape` auto-scrapes whatever the search engine returns, which is outside your control — Firecrawl's backend currently declines to scrape LinkedIn results, but don't rely on that; never manually re-scrape a gated URL surfaced in search results.
- **Never use `--redact-pii`** on `firecrawl scrape` calls — it risks stripping the buyer's name, which this skill deliberately keeps (name + title only). The no-email/no-phone rule is enforced when writing the CSV row, not by this flag.
- **Per-call fallback.** If a single `firecrawl` command fails (blocked, timeout, rate-limited) or returns thin/empty content, retry once with `--wait-for 3000`; if it still fails or is still thin, fall back to `WebSearch` for that one step only. One bad Firecrawl call never fails the whole company.
- **Cost note.** `search --scrape` bills for the search plus a scrape of every result returned (up to the default limit), not a flat per-call cost — real per-company spend runs higher than a naive "~N calls × 2 credits" estimate. Check `firecrawl credit-usage` before/after a batch run rather than trusting a call-count estimate.

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

## Modes

### `discover [segment] [--target N] [--segments a,b,c]`

Searches the web for new candidate companies matching the ICP. Default target: 15 new leads. With no segment/`--segments` given, sweeps all three ICPs using the weighted split below.

### `score-list <companies>`

Given a list of company names/domains/URLs (pasted, or from a file), skips discovery and researches+scores each one directly. No target count — bounded by the list. If the list exceeds 50 companies, process in batches of ~10. If an entry is a typo'd name or a dead/unresolvable domain, record it under `skipped` with reason "Could not resolve" and do not add it to the CSV.

### `recheck-watchlist`

No arguments. Re-researches every `status = watchlist` row in the CSV (ICP3 leads seeded via `discover`/`score-list`), regardless of the normal 30-day freshness window — refreshing watchlist rows on a schedule is this mode's entire purpose. For each row:

1. Re-run the per-company pipeline (see "Per-company pipeline" below), same ~4-call budget and triage stages as discover/score-list, dispatched via the same Workflow `pipeline()` call with `mode: "recheck-watchlist"` — this bypasses the freshness check (Stage A step 1) by design.
2. Re-classify and re-score; update `agent_deployment_stage` and all other fields; bump `last_researched` (pass `force_refresh: true` to `csv_store.py upsert`).
3. If the new `agent_deployment_stage` is `Production agents` → set `status: active` (promoted off the watchlist, regardless of overall tier).
4. If the company is now clearly dead or has pivoted away from agents entirely → set `status: disqualified`.
5. Otherwise → leave `status: watchlist`, fields refreshed.
6. Accumulate one entry per company into a `rechecked` list: `{company_name, domain, prev_status, new_status, prev_agent_deployment_stage, new_agent_deployment_stage, score_total, tier}`. This is produced automatically as the `rechecked` field returned by `research-pipeline.js` for this mode — no manual accumulation needed.

After processing all watchlist rows, run:
```
python scripts/report.py --mode recheck-watchlist --date <YYYY-MM-DD> --rechecked '<JSON list of rechecked dicts>' --out "F:\_WORKY\blindsight\GITHUB\lead-gen\runs\<YYYY-MM-DD>-watchlist-recheck.md"
```
using the `rechecked` list returned by the Workflow pipeline run.

This mode is meant to run on a weekly schedule (wired up separately via a Claude Code scheduled routine that invokes this skill with `recheck-watchlist` — not something this skill sets up itself). No push notification; the written report is checked like any other run report.

## ICP segments & weights (for `discover` with no `--segments` override)

Run `python scripts/segments.py --target <N>` to get the JSON per-segment allocation (or add `--segments a,b,c` to split evenly across an explicit list instead). Valid segment keys: `icp1`, `icp2`, `icp3`.

Default weighting (~40/40/20, reflecting "ICP1/ICP2 spend now, ICP3 seed now"):

| Segment key | ICP | Weight |
|---|---|---|
| `icp1` | AI-Native Product Companies | 40% |
| `icp2` | Sensitive-Data Adopters | 40% |
| `icp3` | Agentic Companies (watchlist) | 20% |

When search across segments turns up the same company more than once (e.g. it matches both ICP1 and ICP2 searches), dedup the candidate list by domain *before* starting research on any of them.

## Per-company pipeline

For every candidate company (from discovery search results or the provided list), research and persistence run as two subagent stages — Stage A (Research) and Stage B (Classify & Persist) — dispatched per-company via the Workflow tool's `pipeline()` (see "Dispatch" below) so a company that clears Stage A early moves straight into Stage B instead of idling for batch-mates.

### Stage A — Research (steps 1–4)

Given a company's `domain`, `company_name`, and the run's `mode`:

1. **Freshness check.** Run `python scripts/csv_store.py check-fresh --csv "F:\_WORKY\blindsight\GITHUB\lead-gen\data\leads.csv" --domain <domain>`. It prints one of `missing` | `fresh` | `stale` | `disqualified` | `customer` (the latter two win over freshness, so a disqualified/customer row is never resurfaced by `discover`/`score-list` even once its freshness window lapses). `fresh` → skip with reason "already fresh in CSV". `disqualified`/`customer` → skip with reason "already {status} in CSV". `missing`/`stale` → proceed to research. Rows with `status: watchlist` ARE resurfaced normally by `discover`/`score-list` freshness rules — only `recheck-watchlist` treats them specially (bypassing freshness entirely). **Skip this step entirely when `mode` is `recheck-watchlist`** — that mode bypasses freshness by design.
2. **Stage 1 triage (1 call).** Run `firecrawl search "<company name>" --scrape -o .firecrawl/<domain>-stage1.json --json` (see "Firecrawl usage" above for the preflight/fallback/allowed-targets rules). If it's clearly a hard disqualifier — a government entity, not an active business, wildly outside the ~20–200 employee range, or a pre-seed startup with no AI angle at all — stop here. Set `icp_match: "Poor fit"` and don't spend further budget on this company; it doesn't count toward `discover`'s target.
3. **Stage 2 on-site research (up to 2 calls, 3 total).** Scrape the candidate's homepage: `firecrawl scrape "<homepage-url>" --only-main-content --format markdown,links -o .firecrawl/<domain>-home.json` (output is JSON with `markdown`/`links` fields, not raw markdown text). From the links it returns, pick the 1–2 most promising on-site pages (About/Team for buyer info, Careers for agent/AI hiring signal, Product for AI-native depth) and scrape them together: `firecrawl scrape "<url1>" "<url2>" -o .firecrawl/`. Together these inform `ai_native_maturity`, `regulatory_data_exposure`, `agent_deployment_stage`, `buyer_name`, and `buyer_title` — no separate call budget per dimension. If the homepage's links list has no About/Team/Careers/Product-style page — not simply "few links"; most homepages return several, just rarely the right category — escalate to `firecrawl map "<homepage-url>" --search "about"` (or `"careers"`) to locate the page directly, then scrape it. In practice this triggers often (many modern marketing sites bury About/Careers in a footer or JS-driven nav that the homepage scrape doesn't surface) — budget for it rather than treating it as rare. If there's still no signal on any of the three core dimensions after this stage, stop and record it under `skipped` with reason "Weak signal / insufficient public info".
4. **Stage 3 off-site research (up to 1 call, 4 total).** Only for companies that cleared stage 2: run `firecrawl search "<company name> CEO OR CTO OR founder" --scrape -o .firecrawl/<domain>-stage3.json --json` for anything not already found on-site in stage 2 — a likely buyer (named CEO/CTO/technical leader from publicly published sources only — no LinkedIn scraping or gated-site access) and geography (EU vs. US vs. other, from company site/press/registration).

Stop-and-skip points above (fresh, disqualified/customer, poor fit at triage, weak signal after stage 2, unresolvable domain in `score-list`) become a `skipped` entry with a reason. Otherwise, hand off a written findings summary — buyer, maturity/exposure/deployment signals, geography, source URLs — rich enough for Stage B to classify and score without re-researching (Stage B has no Firecrawl/WebSearch access).

### Stage B — Classify & Persist (steps 5–9)

Given Stage A's findings for a company that wasn't skipped (a Stage A skip passes straight through — Stage B does nothing further for it):

5. **Classify.** From what Stage A found, produce a classification object using the exact allowed values below.
6. **Score.** Run `python scripts/scoring.py score --input '<classification JSON>'` to get `score_total`, `score_breakdown`, `score_breakdown_str`, and `tier`.
7. **Set status.** `icp_match == "ICP3"` → `status: "watchlist"`, unconditionally, even if `agent_deployment_stage` is already `"Production agents"` on this first pass (promotion only happens on a later `recheck-watchlist` run). `icp_match` in `{"ICP1", "ICP2"}` → `status: "active"` as normal. `icp_match == "Poor fit"` → don't persist to the CSV at all (record under `skipped` per stage-1 triage above). For `recheck-watchlist` runs, this step is superseded by that mode's own status rules (see the `recheck-watchlist` mode section above) — production agents promote to `active`, dead/pivoted companies go `disqualified`, otherwise stay `watchlist`, and the upsert passes `force_refresh: true`.
8. **Persist.** Merge the classification fields, status, and score fields into one row (see "CSV row — column reference" below) and run `python scripts/csv_store.py upsert --csv "F:\_WORKY\blindsight\GITHUB\lead-gen\data\leads.csv" --input '<row JSON>'`.
9. **Accumulate** the row into this run's `results` list (or into `skipped` with a reason, for anything stopped at freshness/triage in Stage A or persistence in Stage B).

### Dispatch

Invoke the per-company pipeline via the Workflow tool rather than manual Agent-tool batching — a company that clears Stage A early starts Stage B immediately instead of waiting on the rest of a 5–8-company batch:

```
Workflow({ scriptPath: "F:\_WORKY\blindsight\GITHUB\lead-gen\.claude\skills\find-leads\scripts\research-pipeline.js", args: { companies: [{domain, company_name}, ...], mode: "<discover|score-list|recheck-watchlist>" } })
```

Use the returned `results`/`skipped` (and, for `recheck-watchlist`, `rechecked`) in place of manually aggregating per-company subagent output — see "After all companies in the run are processed" below.

### Classification field values (must match exactly — `scoring.py` rejects anything else)

- `icp_match`: `ICP1` | `ICP2` | `ICP3` | `Poor fit` — primary classification. Pick the strongest/primary fit; if a company plausibly fits more than one ICP (e.g. an AI-native product company that also handles regulated data), note the secondary fit in `rationale` rather than losing it.
- `vertical`: `fintech` | `healthtech` | `insurtech` | `legaltech` | `hr-tech` | `other` | *(blank)* — populate **only** when `icp_match = ICP2`; leave blank for ICP1/ICP3.
- `persona_match`: one of `1A`, `1B`, `1C`, `2A`, `2B`, `2C`, `3A`, `3B`, `3C`, or `"No clear match"` — whichever defined persona the identified buyer maps to (see `docs/brand/personas.md` for what each code means).
- `company_stage`: `On-target` | `Adjacent` | `Out of range` — On-target = Series A–B for ICP1/ICP3, growing mid-market for ICP2. Adjacent = one stage off (late seed, Series C). Out of range = pre-seed or enterprise/public.
- `ai_native_maturity`: `Strong` | `Moderate` | `Weak/Unknown` — proprietary LLM/RAG/ML shipping continuously in production. Assess for every company regardless of `icp_match`.
- `regulatory_data_exposure`: `Explicit` | `Implicit` | `None apparent` — regulated/sensitive data handling with AI touching it. Assess for every company.
- `agent_deployment_stage`: `Production agents` | `Piloting/building` | `Exploring/considering` | `None` — autonomous agents taking actions/calling tools/transacting. Assess for every company; this is also the ICP3 watchlist-promotion trigger.
- `geo_fit`: `EU` | `US` | `Other` — all three ICPs are EU-first, US second.
- `size_fit`: `In range (20-200)` | `Out of range`
- `buyer_accessibility`: `Named` | `Known but unclear` | `Unknown`
- `wrong_fit_risk`: boolean — true if the company's public content suggests it needs infrastructure/identity security rather than AI/data security. Does not disqualify; changes routing/rationale framing.

### Other row fields to fill in directly (no fixed vocabulary)

- `buyer_name`, `buyer_title` — from public sources only; empty string if unknown
- `reachability_notes` — e.g. known conference/event overlap, or "likely only reachable via channel partner" if relevant
- `rationale` — one or two sentences a rep can sanity-check at a glance; note any secondary ICP fit here
- `sources` — the URL(s) actually used, semicolon-separated
- `confidence` — `high` | `medium` | `low`, reflecting how solid the public data was
- `status` — set per step 7 above (`active`/`watchlist`); `csv_store.py upsert` preserves an existing `disqualified`/`customer` status unless you explicitly pass a different one

### CSV row — column reference

The row you pass as `--input '<row JSON>'` to `csv_store.py upsert` must have one key per column below (these are `scripts/csv_store.py`'s `FIELDNAMES`, in order). Don't invent extra keys or rename any of these.

| # | Column | Where the value comes from |
|---|--------|------------------------------|
| 1 | `domain` | The candidate itself (the domain you researched) |
| 2 | `company_name` | The candidate itself |
| 3 | `icp_match` | Classification enum |
| 4 | `vertical` | Classification enum (ICP2 only, else blank) |
| 5 | `persona_match` | Classification value |
| 6 | `company_stage` | Classification enum |
| 7 | `ai_native_maturity` | Classification enum |
| 8 | `regulatory_data_exposure` | Classification enum |
| 9 | `agent_deployment_stage` | Classification enum |
| 10 | `geo_fit` | Classification enum |
| 11 | `size_fit` | Classification enum |
| 12 | `buyer_name` | "Other row fields to fill in directly" |
| 13 | `buyer_title` | "Other row fields to fill in directly" |
| 14 | `buyer_accessibility` | Classification enum |
| 15 | `wrong_fit_risk` | Classification enum (boolean) |
| 16 | `score_total` | `scoring.py score` output — `score_total` field |
| 17 | `score_breakdown` | `scoring.py score` output — **use the `score_breakdown_str` value (the compact `"k=v;k=v"` string), NOT the `score_breakdown` field (a JSON object/dict).** Putting the dict here defeats the column's purpose and Python's CSV writer will stringify it as `"{'icp_match': 25, ...}"`. |
| 18 | `tier` | `scoring.py score` output — `tier` field |
| 19 | `reachability_notes` | "Other row fields to fill in directly" |
| 20 | `rationale` | "Other row fields to fill in directly" |
| 21 | `sources` | "Other row fields to fill in directly" |
| 22 | `confidence` | "Other row fields to fill in directly" |
| 23 | `first_seen` | Auto-managed by `csv_store.py` — do not send this; it's set/preserved on upsert |
| 24 | `last_researched` | Auto-managed by `csv_store.py` — do not send this; it's set on every upsert |
| 25 | `status` | Set per step 7 above |
| 26 | `outcome` | Leave empty (`""`) — filled in manually by the sales team later, not by this skill |

## Error handling

- **A Firecrawl call fails or returns thin/empty content** (blocked, timeout, rate-limited, unrendered SPA) — retry once with `--wait-for 3000`, then fall back to `WebSearch` for that one step. See "Firecrawl usage" above.
- **Firecrawl unavailable for the whole run** (no `FIRECRAWL_API_KEY`, CLI not installed) — detected once via `firecrawl --status` at the start of the run; fall back to `WebSearch` for every step, run proceeds normally rather than aborting.
- **`docs/brand/personas.md` unreadable** (docs repo missing, moved, or
  the path changed) — stop the run gracefully and report the expected
  path (`F:\_WORKY\blindsight\GITHUB\docs\brand\personas.md`). Never
  classify a company against guessed, remembered, or stale persona/ICP
  data — there is no embedded fallback copy by design.
- **Conflicting signals across sources** (e.g. one source says 80 employees, another says 400) — keep the most authoritative/recent source, note the discrepancy in `rationale`, and set `confidence` to `low` for that company rather than silently picking one value.
- **A research subagent errors out or times out** — retry that company once. If it still fails, record it under `skipped` with reason "Research failed" so it's visible and re-triable next run.
- **Web search starts failing broadly mid-run** (rate limiting/throttling) — stop the run gracefully rather than pushing through with empty results, and report how far it got, e.g. "8 of target 15 researched before search access degraded."
- **No public data found at all for a company that clears triage** — record it with `confidence: "low"` and `rationale: "Unknown / insufficient data"` rather than guessing; it still appears in the CSV and report so a human can look manually.
- **Company plausibly fits more than one ICP** — `icp_match` picks the primary/strongest signal; note the secondary fit in `rationale` rather than dropping it.
- **No persona match found** — `persona_match: "No clear match"`, not blocking, still persisted.
- **`recheck-watchlist` finds a dead/pivoted-away company** — `status: "disqualified"`, not left stuck on the watchlist indefinitely.

## Personal data handling

Only store what's already publicly published (name + title). Never add personal contact info (email/phone) even if found. Marking a row `disqualified` in the CSV means "stop surfacing this person" in future `discover` runs.

## After all companies in the run are processed

For `discover`/`score-list`, use the `results` and `skipped` lists returned by the Workflow `pipeline()` run (see "Dispatch" above) and run:
```
python scripts/report.py --mode <discover|score-list> --segment <segment-or-omit> --date <YYYY-MM-DD> --results '<JSON list of result rows>' --skipped '<JSON list of {company_name, reason}>' --out "F:\_WORKY\blindsight\GITHUB\lead-gen\runs\<YYYY-MM-DD>-<mode>-<segment-or-list>.md"
```

For `recheck-watchlist`, see the mode's own reporting command above.

Report the output file path and a one-paragraph summary back to the user.
