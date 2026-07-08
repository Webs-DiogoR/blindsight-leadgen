# Lead Discovery & Scoring Skill — Design

Date: 2026-07-08
Status: Approved, ready for implementation planning

## Purpose

A Claude Code skill that helps the Blindsight team find and prioritize new sales leads. It can discover new candidate companies matching Blindsight's ideal customer profile (ICP) via public web search, and/or score & classify a list of companies the team already has. Output is a persistent, filterable CSV plus a short markdown summary per run.

## Context: Blindsight's ICP

Drawn from the CEO decoding interview (`Version 11 - Blindsight decoding interview report (brand graphics).html`, July 2026):

- **Primary ICP:** mid-market companies (~50–500, up to ~1000 employees), actively using or deploying AI, in regulated verticals — healthcare, finance (incl. crypto-finance, called out with particular optimism), legal — or AI-native companies generally.
- **Secondary ICP:** startups that sell AI into regulated verticals (Blindsight becomes their claimable security/compliance partner).
- **Exploratory segments (not yet validated):** consultancies, marketing/design bureaus (heavy client data + AI usage), smart-factory/agentic-systems companies (one design partner exists).
- **Not a fit right now:** government (1–2 year procurement cycles favor big/local incumbents), pre-seed/seed non-AI-native startups (can't afford security yet — routed instead to a near-free SDK starter tier for teams under 10 people).
- **Buyer:** mid-market tech CEO or technical leader (budget holder), typically aware of a security concern but without a security background. Influencers: security champions/engineers.
- **#1 reason deals are lost:** being perceived as "just a startup" — mid-market/enterprise prospects with policies against buying from startups. Mitigated via channel partners, not direct sale.
- **#2 reason:** general awareness gap ("would I ever be targeted?").
- **#3 reason:** wrong-fit prospects — e.g. companies that actually need infrastructure/identity security, not AI/data security.
- **Channels that work:** conferences/events (3–10 interested people per event), warm intros/referrals (15–20% commission), channel partners (bypasses "no startups" policies).
- **Channel that's dead:** cold calls/LinkedIn outreach (0 replies across 1000–2000 attempts).

This context directly shapes the scoring rubric and the "reachability" guidance below — a lead tool for Blindsight should optimize for warm paths, not cold-list volume.

## Constraints

- **Data sources:** public web search only (Claude's built-in web search/fetch). No paid enrichment APIs (Apollo, Clay, Crunchbase API, LinkedIn Sales Navigator, Clearbit), no scraping of gated sites. Employee counts, funding stage, etc. are therefore estimates, not confirmed data — every field carries a confidence level and source citation.
- **No CRM integration** in this version — output is a local CSV + markdown reports.

## Architecture & Modes

Two entry modes, one shared pipeline:

- **`discover [segment] [--target N] [--segments a,b,c]`** — searches the web for candidate companies matching the ICP. With no segment specified, sweeps all core ICP segments (weighted, see below). Feeds candidates into the same research+scoring pipeline as `score-list`.
- **`score-list <companies>`** — given a list of companies (names, domains, or URLs), skips discovery and goes straight to research+scoring.

Both modes converge on one **per-company research routine**, run in parallel across companies (capped concurrency, ~5–8 at a time). Each research subagent gathers public signals for one company and returns a structured, unscored record. A **final aggregation step** applies the scoring rubric centrally (so scoring logic is consistent and lives in one place, not re-derived per subagent), merges results into the persistent CSV (dedup by domain), and writes a short markdown report for that run.

## Scoring & Classification Rubric

Each company is classified along these dimensions:

| Dimension | Values |
|---|---|
| Segment fit | Primary ICP / Secondary ICP / Exploratory / Poor fit |
| Company stage | Pre-seed/Seed / Series A+ / Established/Mid-market / Enterprise |
| Vertical | Healthcare / Finance (incl. crypto-finance) / Legal / AI-native / Smart manufacturing / Consultancy-agency / Other |
| AI adoption signal | Strong / Moderate / Weak-Unknown |
| Regulatory exposure | Explicit (named regulation) / Implicit (industry implies it) / None apparent |
| Size fit | employee-count bucket vs. 50–500 (up to ~1000) sweet spot |
| Buyer accessibility | Named tech CEO/CTO found / leadership known but unclear / unknown |
| Wrong-fit risk | Flagged if public content suggests the company needs infra/identity security rather than AI/data security |
| Startup-stigma routing | "Route via channel partner" / "Direct sales viable" / "SDK starter tier" (sub-10-person startups) |

These roll up into a **0–100 conversion-likelihood score** with a **Hot / Warm / Cold / Not-a-fit** tier. The output includes:

- A **score breakdown** (what each dimension contributed), not just the total — so weights can be retuned as the team learns what actually converts.
- A **human-readable rationale** per company, not just the number.
- A **reachability note** — e.g. known conference/event overlap, or "likely only reachable via channel partner" — since cold outreach is a dead channel for Blindsight; this is often more actionable than the score alone.
- **Confidence level + source URL(s)** per key field, since data comes from free web search rather than a paid enrichment source.

A "startup-stigma" or "wrong-fit-risk" flag does **not** disqualify a lead — conversion is still possible with the right person/channel — it changes the routing recommendation instead.

## Per-Company Research Process

Research subagents gather facts only; they do not score. Sources, via public web search:

- **Company site** — product/about pages, AI-related language, leadership names/titles.
- **News & press** — funding announcements, product launches, security incidents (breach history is a real urgency signal per the interview's "breach cost" pitch), AI-adoption news.
- **Job postings** (via search) — AI/ML hiring signals active AI adoption; security-role hiring is a secondary signal (could mean an already-covered buyer, or a security-aware one).
- **Public funding/company data** — Crunchbase public profile pages, press releases, About pages, when discoverable via search (estimate-confidence, not confirmed, since there's no paid API).
- **Regulatory footprint** — mentions of HIPAA/GDPR/SOC2/EU AI Act/FADP, or industry membership implying it (e.g. healthcare provider, licensed fintech).

Each subagent returns one structured, unscored record: company identity, all rubric-input fields with confidence + source, buyer-role guess, raw notes.

### Two-stage triage (to make the per-company search budget go further)

Each company gets a fixed budget of ~5 targeted searches (site, news, jobs, funding, regulatory), spent in two gated stages — a hard rule, not left to subagent judgment, until there's real usage data to calibrate a softer approach:

1. **Stage 1 (1 search) — hard-disqualifier triage.** Checks for obvious disqualifiers: government entity, not an active business, wildly outside the size range, pre-seed with no AI-native angle. Any hit → stop immediately, mark `Poor fit` with reason, don't consume further budget, don't count toward the discover-mode target.
2. **Stage 2 (2–3 searches) — soft-continue check.** Core searches for industry + AI adoption. If neither of the two load-bearing ICP criteria (regulated vertical, active AI use) shows any signal, stop and mark `Weak signal / insufficient public info` for optional manual follow-up, rather than spending the rest of the budget.
3. Only companies clearing both stages get the **full remaining budget** (regulatory-exposure search, buyer-role search).

## Discover Mode — Segment Sweep

When no segment is specified, `discover` splits its target count across segments using a weighted default (roughly 80/20 toward validated segments):

| Segment | Weight |
|---|---|
| Healthcare (regulated mid-market) | High |
| Finance incl. crypto-finance (regulated mid-market) | High |
| Legal (regulated mid-market) | High |
| AI-native companies (mid-market) | High |
| AI-native startups selling into regulated verticals | Medium |
| Consultancies / marketing-design bureaus | Low |
| Smart factories / agentic systems | Low |

`--segments a,b,c` overrides the sweep to target specific segments directly.

**Future evolution (not building now):** once the `Outcome` column (see below) has real conversion data, these static weights could become adaptive — favoring whichever segments actually convert. Not in scope for this version.

## Run Bounds

- `discover` has a **default target lead count** (e.g. 15 new leads), overridable via `--target N`. It searches until it hits that many new (not already in the CSV) qualifying candidates, or exhausts a reasonable search-attempt ceiling — always terminating predictably.
- `score-list` is bounded by the input list size; large lists (50+) are processed in batches so runs stay predictable and resumable.
- Concurrency is capped (~5–8 companies researched in parallel) to bound runtime and avoid hammering search.

## Output Format

### Persistent CSV (`leads.csv`)

One row per company, columns:

`domain | company_name | segment_fit | company_stage | vertical | ai_adoption | regulatory_exposure | size_fit | buyer_name | buyer_title | buyer_accessibility | wrong_fit_risk | startup_stigma_routing | score_total | score_breakdown | tier | reachability_notes | rationale | sources | confidence | first_seen | last_researched | status | outcome`

- `status`: `active` / `disqualified` / `customer`. `discover` mode skips anything not `active` when checking for duplicates, so disqualified/customer companies don't keep resurfacing.
- `outcome`: empty by default, manually filled in by the team after acting on a lead (replied / meeting / closed / lost) — seeds future rubric recalibration.
- Dedup key: `domain`. Re-running either mode updates existing rows in place (refreshing `last_researched`) rather than duplicating, respecting a freshness window (default 30 days) unless a refresh is explicitly requested.
- Buyer names/titles stored are limited to what's publicly published (name + title); no personal contact info (email/phone) unless already public. Marking a row `disqualified` also means "stop surfacing this person."

### Per-run markdown report (`runs/YYYY-MM-DD-<mode>-<segment>.md`)

Short and skimmable: count of companies found/scored, top 5 by score with one-line rationale each, any `wrong_fit_risk` or `startup_stigma_routing` flags worth attention, and a note on anything skipped (already fresh in CSV, or disqualified) so nothing is silently dropped.

## Error Handling & Edge Cases

- **No/ambiguous public data** → `Unknown / insufficient data`, still shown in the report rather than dropped silently.
- **Conflicting signals across sources** → keep the most authoritative/recent, note the discrepancy in `rationale`, lower confidence for that field.
- **Duplicate candidates within one discover run** (surfaced via multiple segment searches) → dedup by domain *before* scoring, not after.
- **Unresolvable `score-list` entries** (typo, dead domain, not a real company) → `Could not resolve`, excluded from the CSV rather than adding a garbage row.
- **Partial subagent failure** → retry once, then log as `Research failed` in the run report if still failing, so it's visible and re-triable.
- **Search throttling mid-run** → stop gracefully, report how far it got (e.g. "8 of target 15 researched before search access degraded").
- **Concurrent writes to the CSV** → not handled in this version; the tool runs locally for 1–2 people and the CSV isn't shared yet. Revisit once usage moves beyond a single local user.

## Validation Approach

No automated test suite (this is a prompt-driven skill). Before relying on it for real outreach decisions, run:

1. **Known-answer test** — `score-list` against companies already well understood (e.g. a current customer like Clínic Barcelona, and an obvious non-fit) to confirm the score/tier/classification matches intuition.
2. **Discover smoke test** — small-target (`--target 5`) run on one segment; manually verify results are real, plausible companies.
3. **Edge-case check** — feed `score-list` a typo'd name and a dead domain, confirm the `Could not resolve` path works instead of producing a garbage row.

## Out of Scope (this version)

- Scheduled/cron execution (the design supports it later without rework, but the first build is on-demand only).
- CRM integration.
- Paid enrichment APIs.
- Adaptive segment-weighting based on outcome data.
- Automated test suite.
