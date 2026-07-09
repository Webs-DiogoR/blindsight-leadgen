# ICP Update, Personas & ICP3 Watchlist — Design

Date: 2026-07-09
Status: Approved, ready for implementation planning
Supersedes: `2026-07-08-lead-gen-design.md`'s ICP context, scoring rubric, and segment model (everything else in that spec — architecture, modes, per-company research process, error handling not called out below — still stands).

## Purpose

Blindsight's ICP has moved on from the original CEO decoding interview (general "mid-market, AI-active, regulated verticals"). There's now a concrete, product-sequenced ICP with three tiers and named buyer personas per tier. This design updates the `find-leads` skill's classification and scoring model to match, and adds a **watchlist** status/workflow for ICP3 (the "seed now, convert later" tier) so those companies get tracked and automatically promoted once they mature, instead of falling out of the pipeline or being scored like an active-close lead.

## Context: The New ICP Base

Three ICPs, sequenced by priority — ICP1 and ICP2 are where the team spends now; ICP3 is a watchlist populated today but not actively closed until the Authorization Broker is past prototype.

**ICP1 — AI-Native Product Companies (runtime security core).** Companies whose product runs on proprietary LLMs, RAG, or ML in production, shipping AI features continuously. Size 20–200, Stage Series A–B, Geo EU-first (Zürich base + GDPR/EU AI Act tailwind), US second. Lead product: Runtime Security Proxy. Wedge: ShadowAI (free demo). Core pain: their own AI runtime is an unmonitored attack surface — prompt injection, exfiltration, an unauthorized/unauditable agent action.

**ICP2 — Sensitive-Data Adopters (DLP + PII wedge).** Mid-market companies handling regulated or sensitive data — fintech, healthtech, insurtech, legaltech, HR-tech — adopting AI across internal operations. Size 20–200, fast-moving but carrying real compliance exposure, Geo EU-first. Lead product: ShadowAI (client-side DLP) → Runtime Proxy once internal AI/RAG is found. Core pain: employees pasting contracts/patient records/financials into unsanctioned AI tools; PII leaking invisibly; GDPR/EU AI Act/HIPAA liability regardless of intent.

**ICP3 — Agentic Companies (seed now, convert later).** Companies deploying autonomous agents in production — agents that take actions, call tools, transact. Size 20–200, Series A–B, earliest-adopter profile. Lead product: Authorization Broker (prototype) + Runtime Proxy for agentic pipelines. Core pain: agents acting without authorization or audit trail, instruction hijacking, tool-call abuse. Status: pipeline-seeding, not active-close — build the list, warm the relationships, sell when the product is ready.

**Cross-cutting note:** ShadowAI is the universal free wedge, not exclusive to ICP2 — it's how you get in the door everywhere. What converts differs: Runtime Proxy for the builders (ICP1), PII/DLP depth for the adopters (ICP2).

### Personas

**ICP1 — AI-Native Product Companies**
- **1A. Founder/CEO** (economic buyer) — technical, now runs the company, is the de facto CISO at this stage. Owns budget, investor relationships, the trust story. Fear: a security failure that torches customer trust or an unanswerable due-diligence question. Convert with investor optics and liability framing. Signs, but rarely finds you first.
- **1B. Head of Engineering/VP Eng** (technical champion) — owns AI systems in production, feels the black-box problem daily. No budget, but the door-opener and validator. Convert with mechanism/depth — the runtime proxy, what it catches, how it deploys. Entry point at most ICP1 accounts.
- **1C. AI/ML Lead or Staff ML Engineer** (hands-on user) — would actually run ShadowAI and read the flags. Feels the pain most, can't authorize a purchase. Generates internal urgency upward. Convert with the product experience itself.

**ICP2 — Sensitive-Data Adopters**
- **2A. CISO/Head of Security** (economic buyer) — real security function and compliance exposure, AI spreading faster than he can govern. Fear: a regulated-data leak he can't see or prove he tried to prevent. Convert with visibility and audit trails. Clearest budget holder of the nine personas.
- **2B. Head of Compliance/DPO** (co-buyer, urgency engine) — owns GDPR/HIPAA/EU AI Act exposure, thinks in liability/audit-readiness, not "security tools." Rarely initiates but can force a purchase by naming the risk. Convert by turning compliance into a feature. Pair with the CISO to move the deal.
- **2C. IT/Security Manager** (technical champion) — runs endpoint tooling, knows employees are pasting sensitive data but can't quantify it. ShadowAI hands him the number, which he takes to the CISO as evidence — the deal opener.

**ICP3 — Agentic Companies (seed now)**
- **3A. Founder/CEO** (economic buyer) — building an agentic product, betting the company on autonomy. Trust/auditability existential — one unauthorized agent action in front of the wrong customer is business-ending. Convert later with Authorization Broker; warm now by already thinking about agent security.
- **3B. Head of AI/Agent Platform Lead** (technical champion) — owns agent pipelines, tool-calling, orchestration; lives closest to instruction hijacking and tool-call abuse. Convert with runtime proxy for agentic pipelines today, Authorization Broker tomorrow. The live relationship in ICP3 — co-designs if you show up early.
- **3C. Security Engineer** (hands-on user) — would instrument agents and read authorization logs. The internal signal that agent security is a real budget line, not a someday. Convert with mechanism/depth once the Broker is past prototype.

Personas are a working hypothesis ("a guess... we'll need to scrounge through LinkedIn and find more roles") — expect refinement as real research accumulates.

## What This Replaces

The old 7-segment model (`healthcare`, `finance`, `legal`, `ai-native`, `ai-native-startups`, `consultancies`, `smart-factories`) and its `segment_fit`/`vertical`/`startup_stigma_routing` classification fields are **retired**. The interview-derived ICP context in the prior spec is superseded by the ICP base above.

## Classification Model

Each researched company is classified along these dimensions:

| Dimension | Values | Notes |
|---|---|---|
| `icp_match` | `ICP1` / `ICP2` / `ICP3` / `Poor fit` | Primary classification. Single-select — pick the strongest/primary fit; if a company plausibly fits more than one ICP (e.g. an AI-native product company that also handles regulated data), note the secondary fit in `rationale` rather than losing it. |
| `vertical` | `fintech` / `healthtech` / `insurtech` / `legaltech` / `hr-tech` / `other` / *(blank)* | Sub-tag, populated **only** for `icp_match = ICP2` (these are the named ICP2 verticals). Blank for ICP1/ICP3 — they're defined by tech posture, not industry. |
| `persona_match` | e.g. `1B`, `2A — CISO/Head of Security`, or `No clear match` | Whichever of the 9 defined personas the identified buyer maps to. Descriptive only — does not feed the score. |
| `company_stage` | `On-target` / `Adjacent` / `Out of range` | On-target = Series A–B for ICP1/ICP3, growing mid-market for ICP2. Adjacent = one stage off (e.g. late seed, Series C). Out of range = pre-seed or enterprise/public. |
| `ai_native_maturity` | `Strong` / `Moderate` / `Weak/Unknown` | Core ICP1 signal — proprietary LLM/RAG/ML shipping continuously in production. Assessed for every company regardless of `icp_match` (useful context even off-ICP1). |
| `regulatory_data_exposure` | `Explicit` / `Implicit` / `None apparent` | Core ICP2 signal — handling regulated/sensitive data (PII, health records, financials) with AI touching it. Assessed for every company. |
| `agent_deployment_stage` | `Production agents` / `Piloting/building` / `Exploring/considering` / `None` | Core ICP3 signal and the watchlist trigger — see below. Assessed for every company from the same research already done for AI-adoption signals; no extra search budget needed. |
| `geo_fit` | `EU` / `US` / `Other` | All three ICPs are EU-first, US second. |
| `size_fit` | `In range (20-200)` / `Out of range` | Same 20–200 range across all three ICPs (down from the old 50–1000). |
| `buyer_accessibility` | `Named` / `Known but unclear` / `Unknown` | Unchanged from the old rubric — is there an actual named person, regardless of persona classification. |
| `wrong_fit_risk` | boolean | Unchanged — flagged if public content suggests the company needs infra/identity security rather than AI/data security. Does not disqualify; changes routing/rationale framing. |

`startup_stigma_routing` is **dropped** — the new target profile (20–200, Series A–B) is startups by definition; there's no "no startups" policy to route around when the target *is* a startup.

## Scoring Rubric

| Dimension | Points |
|---|---|
| `icp_match` | ICP1 / ICP2 / ICP3 = 25 · Poor fit = 0 |
| Core signal (whichever of `ai_native_maturity` / `regulatory_data_exposure` / `agent_deployment_stage` corresponds to the assigned `icp_match`) | Strong / Production = 20 · Moderate / Piloting = 10 · Weak / Exploring = 4 · None = 0 |
| `size_fit` | In range = 15 · Out of range = 0 |
| `company_stage` | On-target = 10 · Adjacent = 5 · Out of range = 0 |
| `geo_fit` | EU = 15 · US = 8 · Other = 0 |
| `buyer_accessibility` | Named = 15 · Known but unclear = 7 · Unknown = 0 |
| `wrong_fit_risk` | −10 penalty if flagged |

Core dimensions sum to exactly 100 (25+20+15+10+15+15). Result is clamped to 0–100 as before. Same Hot(≥70)/Warm(≥45)/Cold(≥20)/Not-a-fit tier thresholds. `icp_match = Poor fit` always forces tier `Not-a-fit`, same as the old `segment_fit = Poor fit` rule.

`icp_match` scores ICP1/ICP2/ICP3 **identically** (25 each) — the watchlist status, not a lower score, is what deprioritizes ICP3. A `Cold`/`Warm` ICP3 lead sitting on the watchlist is expected and fine.

The old `vertical_bonus` (crypto-finance +5) is dropped — no equivalent callout in the new ICP base.

## Status Lifecycle & the ICP3 Watchlist

Statuses: `active` / `disqualified` / `customer` / `watchlist` (new).

- **ICP1 / ICP2 matches** follow the existing pipeline: `active` on a normal pass, `disqualified` via stage-1 hard-disqualifier triage (government, not an active business, wildly outside size range, pre-seed with no AI-native angle) — unchanged from today.
- **ICP3 matches always enter as `status = watchlist`**, unconditionally, on first sight — even if `agent_deployment_stage` is already `Production agents` on the very first research pass. Every ICP3 company spends at least one cycle on the watchlist; promotion happens only on a subsequent recheck, never on first entry. This keeps the entry rule simple (`icp_match == ICP3` → `watchlist`, no exceptions) and matches "seed now, convert later" — even a mature find gets a beat to warm the relationship before being treated as active-close.
- Watchlist rows still get scored normally (`score_total`/`score_breakdown`/`tier` computed same as any lead) — `status` is what marks it out, not the score.
- **Promotion:** a `recheck-watchlist` run (below) that finds `agent_deployment_stage == Production agents` flips `status: watchlist → active`, regardless of the resulting overall score/tier.
- **Falling off:** if a recheck finds the company has died, pivoted away from agents entirely, or is otherwise a clear non-fit, mark `disqualified` rather than leaving it stuck on the watchlist indefinitely.

## Discover Mode — ICP Weighting

Default sweep (no segment specified) splits the target count:

| ICP | Weight |
|---|---|
| ICP1 — AI-Native Product | 40% |
| ICP2 — Sensitive-Data Adopter | 40% |
| ICP3 — Agentic (watchlist) | 20% |

`--segments icp1,icp2` (etc.) still overrides the sweep to target specific ICPs directly, same mechanism as today's segment override.

## New Mode: `recheck-watchlist`

```
recheck-watchlist
```

No arguments — always operates on every `status = watchlist` row in the CSV.

1. Pull all `status = watchlist` rows.
2. For each, re-run the standard per-company research pipeline (same ~5-search budget, same triage stages) — **ignoring the normal 30-day freshness gate**, since refreshing watchlist rows on a schedule is this mode's entire purpose.
3. Re-classify and re-score. Update `agent_deployment_stage` and all other fields; bump `last_researched`.
4. If `agent_deployment_stage == Production agents` → promote `status: watchlist → active`.
5. If the company is now clearly dead/disqualified → `status: watchlist → disqualified`.
6. Otherwise → stays `watchlist`, fields refreshed.
7. Write `runs/YYYY-MM-DD-watchlist-recheck.md`: count rechecked, promotions (company + what changed), disqualifications, stage progressions that didn't yet reach promotion (e.g. `Exploring → Piloting`), and a no-change count. Same skimmable style as existing per-run reports.

**Scheduling:** this mode is designed to run unattended, but wiring the actual weekly trigger is a follow-up setup step *after* implementation (e.g. a Claude Code scheduled routine that invokes the skill with `recheck-watchlist`), not code inside the skill itself. Cadence: weekly. No push notification — the written report is checked like any other run report.

## CSV Schema

**Added columns:** `icp_match`, `vertical` (ICP2 sub-tag), `persona_match`, `ai_native_maturity`, `regulatory_data_exposure`, `agent_deployment_stage`, `geo_fit`

**Removed columns:** old `segment_fit`, old `vertical` (7-segment enum), `startup_stigma_routing`

**Changed:** `size_fit` range redefined (20–200, was 50–1000); `company_stage` redefined to `On-target`/`Adjacent`/`Out of range` (was `Pre-seed/Seed`/`Series A+`/`Established/Mid-market`/`Enterprise`); `status` enum gains `watchlist`

**Unchanged:** `domain`, `company_name`, `buyer_name`, `buyer_title`, `buyer_accessibility`, `wrong_fit_risk`, `score_total`, `score_breakdown`, `tier`, `reachability_notes`, `rationale`, `sources`, `confidence`, `first_seen`, `last_researched`, `outcome`

**Proposed column order** (`csv_store.py`'s `FIELDNAMES`):

`domain | company_name | icp_match | vertical | persona_match | company_stage | ai_native_maturity | regulatory_data_exposure | agent_deployment_stage | geo_fit | size_fit | buyer_name | buyer_title | buyer_accessibility | wrong_fit_risk | score_total | score_breakdown | tier | reachability_notes | rationale | sources | confidence | first_seen | last_researched | status | outcome`

**Existing `leads.csv` data:** the 7 rows currently in the CSV (scored under the old rubric) are stale under this model — they carry old-schema columns (`segment_fit`, old `vertical`, `startup_stigma_routing`) that no longer exist. Migration/backfill approach (re-research vs. drop vs. leave as an archived old-schema snapshot) is an implementation-planning decision, not a schema decision — flagged here so it isn't lost.

## Error Handling & Edge Cases

Carries over unchanged from the prior spec: conflicting signals across sources (keep most authoritative, lower confidence), unresolvable `score-list` entries (`Could not resolve`, excluded from CSV), partial subagent failure (retry once, then `Research failed`), search throttling mid-run (stop gracefully, report progress).

New for this update:
- **Company plausibly fits more than one ICP** — `icp_match` picks the primary/strongest signal; note the secondary fit in `rationale` rather than dropping it.
- **No persona match found** — `persona_match = "No clear match"`, not blocking, still persisted.
- **Watchlist recheck finds a dead/pivoted-away company** — `disqualified`, not left stuck on the watchlist indefinitely (see Status Lifecycle above).

## Validation Approach

Same known-answer + smoke-test approach as the original spec, extended:

1. **Known-answer test** — `score-list` a known ICP1 example, a known ICP2 example, and an obvious non-fit; confirm `icp_match`/score/tier match intuition.
2. **ICP3 watchlist smoke test** — `score-list` a known agentic-AI company; confirm it lands as `status = watchlist` regardless of its `agent_deployment_stage` value.
3. **Recheck-watchlist smoke test** — with at least one watchlist row present, run `recheck-watchlist` and confirm: freshness gate is bypassed, fields refresh, and a company manually set to `agent_deployment_stage = Production agents` promotes to `active`.
4. **Edge-case check** — feed `score-list` a typo'd name and a dead domain, confirm `Could not resolve` path still works.

## Out of Scope (this update)

- Push notifications on watchlist changes (written report only).
- A general (non-ICP3) watchlist mechanism — this is agent-harness/ICP3-specific for now.
- Adaptive segment/ICP weighting from outcome data (carried over from original spec's out-of-scope).
- CRM integration, paid enrichment APIs (carried over).
- Automated test suite (carried over — this remains a prompt-driven skill).
- Actually wiring the weekly cron trigger (implementation-planning/follow-up step, not part of this design).
- Migrating/backfilling the 7 existing `leads.csv` rows to the new schema (flagged above as an implementation-planning decision).
