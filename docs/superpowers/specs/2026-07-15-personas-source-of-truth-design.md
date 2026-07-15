# find-leads: move ICP/persona definitions to the source-of-truth repo

## Problem

find-leads' `SKILL.md` embeds Blindsight's full ICP taxonomy — three
tiers (AI-Native Product, Sensitive-Data Adopter, Agentic) and nine buyer
personas (fears, conversion angles, buyer type) — inside a lead-gen
automation skill. This is real, durable Blindsight business knowledge,
but it's invisible to everything outside find-leads: `scribe` (copy),
`designer`, or a human skimming `docs/brand/` for GTM context. Checked
`docs/brand/content-strategy.md` and `copywriting-voice-guide.md` — the
ICP tiers/personas aren't documented there today, so this is a gap to
close, not a drift to reconcile.

## Design

**New file:** `docs/brand/personas.md` in the source-of-truth repo
(`F:\_WORKY\blindsight\GITHUB\docs`) becomes the canonical copy of the
ICP tier descriptions and all nine personas — the "## The ICP" section
of find-leads' `SKILL.md`, moved essentially verbatim (tier profile:
company size/stage/geo/lead product/wedge/core pain; per-tier personas:
name, buyer type, fear, conversion angle; the "personas are a working
hypothesis" caveat; the cross-cutting ShadowAI wedge note). One line at
the top notes it's consumed by lead-gen's find-leads skill, so it doesn't
read as an orphaned file to someone who lands on it later.

**Stays in `SKILL.md`** (lead-gen repo), unchanged:
- **"Classification field values"** table — the exact `icp_match` /
  `persona_match` enum contract. `scripts/scoring.py` hardcodes
  `icp_match` values (`ICP1`/`ICP2`/`ICP3`/`Poor fit`) for its scoring
  math, so this is a validation contract, not narrative — it stays put
  regardless of where the descriptive text lives. Persona codes (`1A`,
  `2A`, etc.) remain valid short labels here; their meaning now lives in
  `personas.md`, not duplicated as prose in both places.
- **"ICP segments & weights"** (the discover-mode 40/40/20 split) — an
  operational parameter for how `discover` allocates search budget, not
  a durable business definition. Out of scope for this move.

**`SKILL.md`'s "## The ICP" section** shrinks to a short pointer: three
tier names as a one-line table of contents, plus an instruction that
Stage B (classification) must read `docs/brand/personas.md` before
assigning `icp_match`/`persona_match`.

**Dispatch mechanism:** `research-pipeline.js`'s `persistPrompt` (Stage
B — classify/score/persist) currently tells its subagent to read
`SKILL.md`'s "The ICP" section. That instruction changes to read
`docs/brand/personas.md` instead, absolute path:
`F:\_WORKY\blindsight\GITHUB\docs\brand\personas.md`.

**Missing-file behavior:** `docs/brand/personas.md` is a hard read
dependency with no embedded fallback copy — a fallback copy would
recreate the exact two-copies-can-drift problem this change removes.
If Stage B can't read it, the run stops and reports the gap, following
the same pattern as `SKILL.md`'s existing "Firecrawl unavailable for the
whole run" handling: this is a new bullet in the "Error handling"
section — "`docs/brand/personas.md` unreadable (docs repo missing/moved)
— stop the run gracefully, report the path that was expected, don't
classify against guessed or stale data."

## Out of scope

- ICP segment weighting (`ICP segments & weights` section) — stays as
  lead-gen tooling config.
- `scripts/scoring.py`'s enum validation logic — unchanged.
- Any change to `recheck-watchlist`'s freshness/status rules (unrelated,
  already fixed in board task 0715-find).
- Retroactively updating `docs/brand/content-strategy.md` or
  `copywriting-voice-guide.md` to cross-reference `personas.md` — future
  work if `scribe` ends up using it, not needed for this move.

## Verification

Two-repo change, no automated tests to write (this is doc content +
prompt text, same class of change as board task 0715-convert). Verify
by hand: `personas.md` renders the same tier/persona content that used
to live in `SKILL.md`, nothing was dropped or reworded in the move;
`research-pipeline.js`'s Stage B prompt correctly points at the new
path; a quick manual read of the restructured `SKILL.md` "The ICP"
section confirms it still makes sense standalone to a subagent that
hasn't seen the old version.
