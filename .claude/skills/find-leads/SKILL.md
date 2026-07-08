---
name: find-leads
description: Discover and score potential Blindsight sales leads against the company's ICP (mid-market, AI-active, regulated verticals), or score a list of companies already on hand. Use when the team needs new leads or wants existing prospects ranked and classified.
---

# Find Leads

Discovers and/or scores companies against Blindsight's ideal customer profile (ICP), producing a persistent CSV and a per-run markdown report.

## Paths (this installation)

- Leads CSV: `F:\_WORKY\blindsight\lead-gen\data\leads.csv`
- Run reports: `F:\_WORKY\blindsight\lead-gen\runs\`
- Scripts: `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\scripts\`

## Modes

### `discover [segment] [--target N] [--segments a,b,c]`

Searches the web for new candidate companies matching the ICP. Default target: 15 new leads. With no segment/`--segments` given, sweeps all seven core segments using the weighted split below.

### `score-list <companies>`

Given a list of company names/domains/URLs (pasted, or from a file), skips discovery and researches+scores each one directly. No target count — bounded by the list. If the list exceeds 50 companies, process in batches of ~10. If an entry is a typo'd name or a dead/unresolvable domain, record it under `skipped` with reason "Could not resolve" and do not add it to the CSV.

## Segments & weights (for `discover` with no `--segments` override)

Run `python scripts/segments.py --target <N>` to get the JSON per-segment allocation (or add `--segments a,b,c` to split evenly across an explicit list instead). Valid segment keys: `healthcare`, `finance`, `legal`, `ai-native`, `ai-native-startups`, `consultancies`, `smart-factories`.

When search across segments turns up the same company more than once (e.g. it matches both "healthcare" and "ai-native" searches), dedup the candidate list by domain *before* starting research on any of them — don't spend search budget researching the same company twice in one run.

## Per-company pipeline

For every candidate company (from discovery search results or the provided list):

1. **Freshness check.** Run `python scripts/csv_store.py check-fresh --csv "F:\_WORKY\blindsight\lead-gen\data\leads.csv" --domain <domain>`. If it prints `fresh`, skip research entirely — record it under `skipped` with reason "already fresh in CSV" and move to the next company. If it prints anything for a row whose `status` is `disqualified` or `customer`, also skip it (don't resurface disqualified/customer companies in `discover`).
2. **Stage 1 triage (1 search).** Do one broad web search on the company. If it's clearly a hard disqualifier — a government entity, not an active business, wildly outside the ~50–1000 employee range, or a pre-seed startup with no AI-native angle — stop here. Set `segment_fit: "Poor fit"` and don't spend further search budget on this company; it doesn't count toward `discover`'s target.
3. **Stage 2 triage (up to 3 more searches, 2–4 total).** Search for industry/vertical and AI-adoption signals (company site, news, job postings). If by search 4 there's no signal of *either* a regulated/AI-native vertical *or* active AI adoption, stop and record it under `skipped` with reason "Weak signal / insufficient public info" rather than spending the 5th search chasing buyer details for a probable non-fit.
4. **Full research (up to 1 more search, 5 total).** Only for companies that cleared stage 2: search for regulatory-exposure evidence (GDPR/HIPAA/SOC2/EU AI Act/FADP mentions) and a likely buyer (named CEO/CTO/technical leader from publicly published sources only — no LinkedIn scraping or gated-site access).
5. **Classify.** From what was found, produce a classification object using the exact allowed values below.
6. **Score.** Run `python scripts/scoring.py score --input '<classification JSON>'` to get `score_total`, `score_breakdown`, `score_breakdown_str`, and `tier`.
7. **Persist.** Merge the classification fields and the score fields into one row (see CSV columns below) and run `python scripts/csv_store.py upsert --csv "F:\_WORKY\blindsight\lead-gen\data\leads.csv" --input '<row JSON>'`.
8. **Accumulate** the row into this run's `results` list (or into `skipped` with a reason, for anything stopped at freshness or triage).

Research companies in parallel (one subagent per company via the Agent tool), 5–8 at a time, each following steps 1–8 independently; aggregate afterward.

### Classification field values (must match exactly — `scoring.py` rejects anything else)

- `segment_fit`: `Primary ICP` | `Secondary ICP` | `Exploratory` | `Poor fit`
- `company_stage`: `Pre-seed/Seed` | `Series A+` | `Established/Mid-market` | `Enterprise`
- `vertical`: `Healthcare` | `Finance` | `Finance - crypto-finance` | `Legal` | `AI-native` | `Smart manufacturing` | `Consultancy-agency` | `Other`
- `ai_adoption`: `Strong` | `Moderate` | `Weak/Unknown`
- `regulatory_exposure`: `Explicit` | `Implicit` | `None apparent`
- `size_fit`: `In range (50-500)` | `Extended range (501-1000)` | `Out of range`
- `buyer_accessibility`: `Named` | `Known but unclear` | `Unknown`
- `wrong_fit_risk`: boolean — true if the company's public content suggests it needs infrastructure/identity security rather than AI/data security (the interview's deepfake-sector example)
- `startup_stigma_routing`: `Direct sales viable` | `Route via channel partner` | `SDK starter tier` — use "Route via channel partner" for mid-market/enterprise companies likely to have a "no startups" purchasing policy, "SDK starter tier" for sub-10-person AI-native startups, otherwise "Direct sales viable"

### Other row fields to fill in directly (no fixed vocabulary)

- `buyer_name`, `buyer_title` — from public sources only; empty string if unknown
- `reachability_notes` — e.g. known conference/event overlap, or "likely only reachable via channel partner" if that's the routing
- `rationale` — one or two sentences a rep can sanity-check at a glance
- `sources` — the URL(s) actually used, semicolon-separated
- `confidence` — `high` | `medium` | `low`, reflecting how solid the public data was
- `status` — `active` for new/updated rows; `csv_store.py upsert` preserves an existing `disqualified`/`customer` status unless you explicitly pass a different one

## Error handling

- **Conflicting signals across sources** (e.g. one source says 80 employees, another says 400) — keep the most authoritative/recent source, note the discrepancy in `rationale`, and set `confidence` to `low` for that company rather than silently picking one value.
- **A research subagent errors out or times out** — retry that company once. If it still fails, record it under `skipped` with reason "Research failed" so it's visible and re-triable next run, rather than silently missing from the output.
- **Web search starts failing broadly mid-run** (rate limiting/throttling) — stop the run gracefully rather than pushing through with empty results, and report how far it got, e.g. "8 of target 15 researched before search access degraded."
- **No public data found at all for a company that clears triage** — record it with `confidence: "low"` and `rationale: "Unknown / insufficient data"` rather than guessing; it still appears in the CSV and report so a human can look manually.

## Personal data handling

Only store what's already publicly published (name + title). Never add personal contact info (email/phone) even if found. Marking a row `disqualified` in the CSV means "stop surfacing this person" in future `discover` runs.

## After all companies in the run are processed

Run:
```
python scripts/report.py --mode <discover|score-list> --segment <segment-or-omit> --date <YYYY-MM-DD> --results '<JSON list of result rows>' --skipped '<JSON list of {company_name, reason}>' --out "F:\_WORKY\blindsight\lead-gen\runs\<YYYY-MM-DD>-<mode>-<segment-or-list>.md"
```

Report the output file path and a one-paragraph summary back to the user.
