# Lead List: Blindsight ICP1/ICP2/ICP3 Prospects

## Summary

Source: Firecrawl CLI (`firecrawl search --scrape` for discovery, `firecrawl scrape` for company homepages, "about"/"team" pages, and funding-announcement press articles). No browser/interact was needed since no gated database, filter form, or login wall was involved.

Filters applied: EU-first geography (Switzerland, Germany, UK, France, Netherlands, Poland, Czech Republic), 20-200 employee target band, Series A-B stage preference (with two intentional stage exceptions noted below), and the three ICP definitions supplied. The 19 companies already known to the team were explicitly excluded from every search and cross-checked by name before inclusion.

Count: 15 leads (6 ICP1, 6 ICP2, 3 ICP3), one named contact per company.

Caveats:
- Two leads sit slightly outside the strict Series A-B band by design: **LogicStar** (pre-seed) is included in ICP3 because it is an unusually clean example of the "earliest-adopter" fully-autonomous-agent profile the tier calls for; **ClaimSorted** (seed) is included in ICP2 because its €11.4M round is one of the largest Insurtech seed raises in Europe and the company is already operating at scale.
- Company headcounts are rarely published; only Dust's 66-person team is a sourced, confirmed figure. All other sizes are inferred from funding stage, not verified (see Data Gaps).
- Every contact below was found named on the company's own website or in a funding-announcement / press article — never on LinkedIn, Crunchbase paid pages, or any gated source. Where LinkedIn URLs appeared incidentally in search results, they were not used as `profile_url` or scraped.
- No email, phone, or LinkedIn URL was genuinely public without gating for any of the 15 leads, so that field is blank throughout (see Data Gaps).

## Leads

### ICP1 — AI-Native Product Companies

| Name | Title | Company | Company URL | Location | Email/Phone/LinkedIn | Industry | Company Size | Funding Stage | Notes | Profile URL |
|---|---|---|---|---|---|---|---|---|---|---|
| Milos Rusic | CEO & Co-Founder | deepset | https://www.deepset.ai/ | Berlin, Germany | *(not publicly available)* | AI Infrastructure / RAG & NLP Platforms (Haystack) | Not disclosed (Series B stage, est. ~50-100) | Series B ($30M, Aug 2023) | AI-native RAG/NLP platform used to build production LLM search & retrieval systems for enterprises; ships continuous AI features and faces prompt-injection/data-leakage risk in customer deployments. | https://www.deepset.ai/about |
| Martin Rehak | CEO and Founder | Resistant AI | https://resistant.ai/ | Prague, Czech Republic | *(not publicly available)* | Fintech / Financial Crime & Fraud Detection AI | Not disclosed (Series B stage, est. ~80-150) | Series B (€21M, Oct 2025) | AI-native fraud/fincrime detection models deployed inside banks' and fintechs' transaction pipelines; company explicitly cites "agentic co-pilots" for risk teams, i.e. production LLM/agent attack surface. | https://www.eu-startups.com/2025/10/resistant-ai-out-of-czechia-tackles-fincrime-and-fraud-prevention-with-new-e21-million/ |
| Meryem Arik | CEO & Co-Founder | Doubleword | https://www.doubleword.ai/ | London, UK | *(not publicly available)* | AI Infrastructure / Enterprise LLM Inference | Not disclosed (Series A stage, est. ~20-60) | Series A ($12M, May 2025) | Sells a self-hosted LLM inference layer that enterprises deploy in production — a natural adopter of runtime guardrails for the models it hosts on customers' behalf. | https://resources.doubleword.ai/resources/doubleword-series-a-announcement |
| Julien Launay | Co-Founder & CEO | Adaptive ML | https://www.adaptive-ml.com/ | Paris, France | *(not publicly available)* | AI Infrastructure / LLM Fine-Tuning & Reinforcement Learning | Not disclosed (Seed stage, est. ~20-50) | Seed ($20M, Mar 2024) | Enterprise platform for continuously fine-tuning and iterating production LLMs via reinforcement learning on live user feedback — models are always-changing, which is exactly the runtime-monitoring gap Blindsight addresses. | https://www.youtube.com/watch?v=iehLFYvqvow |
| Manuel Grenacher | CEO/Founder | Unique | https://www.unique.ai/ | Zurich, Switzerland | *(not publicly available)* | AI / Agentic AI for Financial Services | Not disclosed (Series A stage, est. ~80-150) | Series A ($30M, Feb 2026) | Zurich-based agentic AI platform embedded directly into private banking, wealth and insurance workflows (Pictet, UBP, SIX); high-stakes financial data plus autonomous agent actions make it a strong ICP1/ICP3 crossover and an easy first conversation given shared HQ city. | https://www.unique.ai/team |
| Dr. Chris Parsonson | CEO & Co-Founder | Solve Intelligence | https://www.solveintelligence.com/ | London, UK | *(not publicly available)* | Legal Tech / AI Patent Drafting | Not disclosed (Series B stage, est. ~50-120) | Series B ($40M, Dec 2025) | AI copilot for patent drafting, prosecution and litigation used by 400+ IP teams; ships LLM features continuously into a workflow handling confidential, pre-publication IP data. | https://ipwatchdog.com/press/solve-intelligence-takes-total-funding-to-55m-with-series-b-round-to-build-ai-for-patents-and-launches-new-claim-charting-product/ |

### ICP2 — Sensitive-Data Adopters

| Name | Title | Company | Company URL | Location | Email/Phone/LinkedIn | Industry | Company Size | Funding Stage | Notes | Profile URL |
|---|---|---|---|---|---|---|---|---|---|---|
| Andrew Saula | Head of Cyber Security & Incident Response | Baobab Insurance | https://www.baobab.io/ | Berlin, Germany | *(not publicly available)* | InsurTech / Cyber Insurance | Not disclosed (Series A stage, est. ~30-70) | Series A (€12M, Jun 2025) | German cyber-insurance MGA running an "AI-native underwriting" process on sensitive breach and risk data; this contact already holds the exact security title Blindsight targets (CEO Vincenz Klemm is the other publicly quoted contact, see Data Gaps). | https://www.baobab.io/ |
| Pavel Gertsberg | Founder and CEO | ClaimSorted | https://www.claimsorted.com/ | London, UK | *(not publicly available)* | InsurTech / Claims Automation | Not disclosed (Seed stage, est. ~15-40) | Seed (€11.4M, Oct 2025) | UK insurtech automating claims handling — a function historically outsourced to third-party administrators — with AI directly on policyholder claims data, raising model-oversight and data-handling questions typical of regulated insurance operations. | https://www.eu-startups.com/2025/10/londons-insurtech-offering-claimsorted-raises-e11-4-million-in-one-of-the-largest-insurtech-rounds-this-year/ |
| Duco van Lanschot | Founder | Duna | https://duna.com/ | Amsterdam, Netherlands | *(not publicly available)* | FinTech / RegTech (Business Identity & Compliance) | Not disclosed (Series A stage, est. ~30-70) | Series A (€30M, Feb 2026) | Fintech built by Stripe alumni providing AI-automated business identity verification and onboarding for banks; the AI system sits directly in the KYC/AML decision path on regulated identity data. | https://www.eu-startups.com/2026/02/dutch-fintech-startup-duna-raises-e30-million-to-expand-compliant-ai-for-business-identity-and-onboarding/ |
| Adam Janczewski | Founder | Jutro Medical | https://jutromedical.com/en | Warsaw, Poland | *(not publicly available)* | HealthTech / AI-First Primary Care | Not disclosed (Series A stage; 20 clinics, ~120,000 patients served) | Series A, extended (€36M total, Dec 2025) | AI-first primary care operator embedding AI agents directly into clinical intake, documentation and administrative workflows across its own EHR system, serving 120k+ patients — acute patient-data exposure from production clinical AI. | https://www.vestbee.com/insights/articles/jutro-medical-extends-series-a-to-36-m |
| Avinav Nigam | Founder and CEO | TERN Group | https://www.tern-group.com/ | London, UK | *(not publicly available)* | HR-Tech / Healthcare Workforce & Talent Mobility | Not disclosed (Series A stage, est. ~40-90) | Series A (€20M / ~$24M, Sep 2025) | Clinical AI workforce platform sourcing, vetting and relocating healthcare staff across the UK, India, Germany, the GCC and Japan — AI-driven credentialing/matching combined with sensitive clinician and patient-adjacent data across multiple regulated markets. | https://www.eu-startups.com/2025/09/british-ai-clinical-workforce-platform-tern-group-raises-e20-million-to-tackle-healthcare-workforce-shortage/ |
| Ivan Cossu | CEO & Co-Founder | deskbird | https://www.deskbird.com/ | Zurich, Switzerland | *(not publicly available)* | HR-Tech / Workplace Management SaaS | Not disclosed (Series B stage, est. ~60-120) | Series B ($23M, Sep 2025) | Swiss HR-tech workplace-management platform adding "AI-powered workplace intelligence" on top of employee attendance/location data — internal AI adoption inside a company handling sensitive HR data, matching ICP2's IT/Security-manager buyer. | https://www.deskbird.com/about |

### ICP3 — Agentic Companies

| Name | Title | Company | Company URL | Location | Email/Phone/LinkedIn | Industry | Company Size | Funding Stage | Notes | Profile URL |
|---|---|---|---|---|---|---|---|---|---|---|
| Gabriel Hubert | Co-Founder, CEO | Dust | https://dust.tt/ | Paris, France | *(not publicly available)* | AI / Enterprise AI Agents & Workflow Automation | 66 employees (company-reported, Jul 2025) | Series A ($16M, Jun 2024) | Builds customizable AI agents wired into Slack, Notion and GitHub for 250+ enterprise customers — agents that read and act on internal company data are exactly the runtime exposure Blindsight targets. | https://dust.tt/home/about |
| Dimitri Masin | Co-Founder & CEO | Gradient Labs | https://gradient-labs.ai/ | London, UK | *(not publicly available)* | AI / Autonomous Customer Operations Agents (Financial Services) | Not disclosed (Series A stage, est. ~30-60) | Series A (~$26M total, 2026; initial tranche $13M Jul 2025) | Autonomous AI agents that independently resolve customer service interactions for regulated financial-services clients, taking real account actions without a human in the loop — a textbook agentic-security risk profile. | https://gradient-labs.ai/about |
| Boris Paskalev | Co-Founder and CEO | LogicStar | https://logicstar.ai/ | Zurich, Switzerland | *(not publicly available)* | AI / Agentic Software Maintenance (Dev Tools) | Not disclosed (pre-seed stage, small team) | Pre-Seed ($3M) | ETH Zurich spin-out building fully autonomous AI agents that patch and maintain production software with no human review step — an early and extreme case of the agentic risk ICP3 targets; included despite pre-seed stage for that reason (see Data Gaps). | https://logicstar.ai/ |

## Data Gaps

- **Email / phone / LinkedIn**: Not genuinely public without gating for any of the 15 contacts. All were identified by name and title on the company's own website or in a funding-announcement article; no contact details were scraped from LinkedIn, Sales Navigator, or Crunchbase paid pages, per the hard constraint.
- **Company size**: Only Dust's 66-person team (self-reported, July 2025) is a sourced, confirmed figure. All other "Company Size" cells show an estimated range inferred from funding stage rather than a verified headcount — none of the other 14 companies publish employee counts on their sites or in the press coverage found.
- **LogicStar** (ICP3) is pre-seed, earlier than the general Series A-B target — included as an unusually clean "earliest-adopter" agentic example per the ICP3 description; flag if the team wants strictly Series A+ only.
- **ClaimSorted** (ICP2) is seed-stage, not yet Series A — included given the round's scale (one of the largest European Insurtech seed rounds) and clear fit; flag similarly if stage discipline is required.
- **Baobab Insurance** has two publicly named contacts: Andrew Saula (Head of Cyber Security & Incident Response, listed above as the primary contact because his title is an exact match to ICP2's buyer persona) and CEO/Co-founder Vincenz Klemm (quoted in the €12M Series A press release). Either could be the outreach entry point.
- **Duna, Jutro Medical, TERN Group**: press sources confirm "Founder" (and, for TERN Group, "CEO") but do not always spell out a formal CEO title for the other two; titles above reflect exactly what each source states.
- **Doubleword** and **Adaptive ML**: CEO titles were confirmed via conference/interview material (Slush 2025, a YouTube interview) rather than the companies' own "about"/team pages, since those pages did not list leadership names directly at scrape time.
- **Gradient Labs**: the company's Series A was topped up from an initial $13M (Jul 2025) to ~$26M; the larger, more recent total (per the company's own blog) is cited as the funding stage figure.
- **Industry/vertical classification** for a few companies is a judgment call at the boundary between tiers (e.g., Unique and Gradient Labs sit across ICP1/ICP2/ICP3 given their agentic-finance focus); each was placed in the tier its core company-level fit (AI-native product vs. regulated-industry vs. autonomous-action) most strongly matches, and the crossover is called out in the notes.

## Rerun Inputs

```
workflow: firecrawl-lead-gen
target: Blindsight ICP1/ICP2/ICP3 prospects (~6/6/3 split), excluding 19 companies already in data/leads.csv
source: auto (Firecrawl search/scrape, public sources only)
max_leads: 15
output: markdown
```
