# Firecrawl-Powered Per-Company Research — Design

Date: 2026-07-10
Status: Approved, ready for implementation planning
Extends: `2026-07-08-lead-gen-design.md` and `2026-07-09-icp-update-watchlist-design.md` — this design only changes the **per-company research process** (how signal is gathered per candidate). ICP definitions, scoring rubric, classification fields, CSV schema, and status lifecycle are unchanged.

## Purpose

The `find-leads` skill currently researches every candidate using only Claude's built-in web search — a deliberate original constraint ("no paid enrichment APIs, no scraping of gated sites"). The team has since installed the Firecrawl CLI plugin. This design integrates it into the per-company research step to get fuller, more reliable signal (full page content instead of search snippets) from the candidate's own public site, while keeping the same public-only, no-gated-site posture.

This is the first of three planned Firecrawl integrations for `lead-gen`, sequenced deliberately:

1. **Richer per-company research (this design)** — foundational; the other two both still depend on this same research step.
2. Bulk discovery via `firecrawl crawl` (harvesting many candidate domains from directories/portfolios instead of ad hoc segment searches) — future spec.
3. Event-driven watchlist rechecking via `firecrawl monitor` (recheck ICP3 companies when something changes, not blindly every week) — future spec.

## Evidence From Current Runs

The 2026-07-10 `discover-all` run (14 companies) shows the existing pipeline is not obviously *broken* on quality — 10/14 rows `confidence: high`, 4/14 `medium`, 0 `low`; 14/14 have a named buyer. The gain from Firecrawl here is depth/reliability per search-budget call (full page vs. snippet), not fixing broken data. (Separately, that run's report flagged an ICP2 sourcing gap — general web search over-surfaces AI-native product companies relative to quiet regulated-industry AI adopters. That's a discovery-breadth problem, addressed by the future bulk-discovery spec, not by this one.)

## What Firecrawl Is, Concretely

Firecrawl is installed as a CLI (`firecrawl`), invoked via `Bash(firecrawl *)`, authenticated via `FIRECRAWL_API_KEY`, credit-metered per call (`firecrawl --status` / `firecrawl credit-usage`). Relevant commands:

- `firecrawl search "<query>" --scrape` — web search with full page content per result (vs. Claude's built-in `WebSearch`, which returns snippets). 2 credits, refunded to 1 after the required feedback call.
- `firecrawl scrape <url> [url2 ...] --only-main-content --format markdown,links` — full clean markdown of one or more URLs (concurrent), optionally including every link found on the page.
- `firecrawl map <url> --search "<term>"` — discover URLs on a site (not used in this design's default path; see below).

## Pipeline Changes

The per-company pipeline (freshness check → stage 1 → stage 2 → stage 3 → classify → score → persist) is unchanged in shape. Only the *implementation* of stages 1–3 changes:

### Stage 1 — hard-disqualifier triage (1 call, unchanged budget)

Swap Claude's built-in `WebSearch` for `firecrawl search "<company>" --scrape`. Same purpose (real, in-range, going-concern business?), richer content per call at comparable cost.

### Stage 2 — on-site signal gathering (2 calls, replaces 2–3 built-in searches)

1. `firecrawl scrape <homepage> --only-main-content --format markdown,links` — one call returns the homepage's full content *and* every nav link on it (About, Careers, Product, etc.), avoiding a separate URL-discovery call on typical marketing sites.
2. A follow-up `firecrawl scrape <url1> <url2>` on the 1–2 most promising links surfaced by step 1 — e.g. About/Team (buyer info), Careers (agent/AI hiring signal), Product (AI-native depth) — scraped concurrently in one call.

This feeds `ai_native_maturity`, `regulatory_data_exposure`, `agent_deployment_stage`, `buyer_name`, and `buyer_title` from primary-source content instead of search snippets.

**Escalation for sites where the homepage doesn't surface useful links** (e.g. a single-page site, or nav that's all JS-rendered menus not present in the scraped links list): fall back to `firecrawl map <domain> --search "about"` (or `"careers"`) to locate the page directly, then scrape it. This is the exception path, not the default, to avoid paying for a `map` call on every company.

### Stage 3 — off-site signals (up to 1 call, unchanged budget)

Funding stage, press, breach history, and buyer cross-check live off the candidate's own domain — these stay a `firecrawl search` call, since scraping can't surface information that isn't on the site being scraped.

### Net call budget

~4 Firecrawl calls per fully-researched company (1 search + 2 scrapes + 1 search) vs. today's up-to-5 built-in searches — comparable or fewer total external calls, each returning full-page content rather than a snippet.

## Constraints (carried over, now enforced at the URL level)

- Firecrawl targets are limited to the candidate's own public domain plus public press/news. Never LinkedIn, Crunchbase paid pages, LinkedIn Sales Navigator, or any gated/auth-walled site — same rule as the original "no scraping of gated sites," now enforced by which URLs get passed to `scrape`/`search`/`map`.
- Do not use `scrape --redact-pii`. It risks stripping the buyer's name, which the skill deliberately keeps (name + title only). The existing personal-data policy (no email/phone, ever) stays enforced at the prompt/write layer, not by this flag.

## Error Handling

- **A Firecrawl call fails** (blocked, timeout, rate-limited) — retry once with `--wait-for 3000` (helps JS-heavy sites render before scraping); if it still fails, fall back to Claude's built-in `WebSearch` for that one step. Firecrawl is an enhancement, not a hard dependency — a company's research never fails outright just because Firecrawl had a bad call.
- **`FIRECRAWL_API_KEY` not configured / CLI not installed** — checked once at the start of a run (`firecrawl --status`); if unavailable, the entire run falls back to the original all-`WebSearch` pipeline rather than failing per company.
- **Homepage scrape returns thin/empty content** (unrendered SPA, bot-blocked) — one retry with `--wait-for`, then fall back to search, same as the general failure path above.
- All other error handling (conflicting signals, unresolvable `score-list` entries, partial subagent failure, search throttling mid-run, dead/pivoted watchlist companies) is unchanged from the prior specs.

## Testing / Validation

1. **Known-answer comparison** — re-run 2–3 companies already in `leads.csv` (e.g. DeepJudge as a clean marketing site, plus one JS-heavy SPA) through the new pipeline; compare resulting fields/confidence side-by-side against their existing rows to confirm this is a genuine improvement, not just a different result.
2. **Fallback test** — temporarily unset `FIRECRAWL_API_KEY` and confirm a run still completes correctly via the `WebSearch` fallback rather than erroring out.
3. **Gated-domain check** — spot-check (prompt review) that no scrape/search/map call in the updated `SKILL.md` instructions ever targets a gated domain; this is enforced by instruction, not code, so it's a review item, not a test assertion.
4. **Smoke run** — a real `discover --target 5` run to sanity-check output quality and actual credit cost before relying on this for a full-size run.

## Out of Scope (this design)

- Bulk discovery via `firecrawl crawl` (future spec #2).
- Event-driven watchlist rechecking via `firecrawl monitor` (future spec #3).
- Any change to ICP definitions, scoring rubric, classification fields, CSV schema, or status lifecycle.
- Structured extraction via `firecrawl agent` — considered and set aside for this pass; many classification signals (funding, news, regulatory context) live off the candidate's own domain and wouldn't be reachable by a single-domain structured-extraction call anyway, so it doesn't cleanly replace the search-based stage 3 step.
- Migrating the existing 14 `leads.csv` rows to be re-researched under the new pipeline (optional follow-up, not required — old rows remain valid, just gathered via the prior method).
