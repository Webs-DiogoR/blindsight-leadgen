# ICP Update, Personas & ICP3 Watchlist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `find-leads` skill's old 7-segment ICP/scoring model with the new 3-ICP model (AI-Native Product, Sensitive-Data Adopter, Agentic) plus buyer personas, and add an ICP3 "watchlist" status with a `recheck-watchlist` mode that promotes leads once their agent deployment matures.

**Architecture:** Same shape as the existing skill — pure-stdlib Python scripts (`scoring.py`, `segments.py`, `csv_store.py`, `report.py`) invoked by Claude via `SKILL.md` instructions, no new files. `scoring.py` and `segments.py` get their rubric/weights replaced; `csv_store.py` gets a new column set; `report.py` gains a second report generator for the new mode; `SKILL.md` is rewritten to match. Existing `leads.csv` data (old schema) is archived rather than migrated, since the new schema has no equivalent for most old fields.

**Tech Stack:** Python 3 standard library only (`csv`, `json`, `argparse`, `datetime`, `unittest`) — no third-party dependencies, no `pytest`.

## Global Constraints

- Python: standard library only. Tests use the built-in `unittest` module — do not add a `pytest` dependency.
- Tests run from `.claude/skills/find-leads/` via `python -m unittest tests.test_<module> -v` (or `python -m unittest discover -v` for the whole suite).
- No CRM integration, no paid enrichment APIs (unchanged from the original spec).
- No automated test suite for `SKILL.md` itself — it's a prompt-driven instruction file; verify it by review, not unit tests.
- Scoring dimensions must sum to exactly 100 pre-penalty: `icp_match`(25) + core signal(20) + `size_fit`(15) + `company_stage`(10) + `geo_fit`(15) + `buyer_accessibility`(15) = 100.
- `icp_match` scores ICP1/ICP2/ICP3 identically (25 each) — status, not score, is what marks ICP3 as lower-priority.
- Every `icp_match == "ICP3"` classification gets `status: "watchlist"` unconditionally on first sight, even if `agent_deployment_stage` is already `"Production agents"`. Promotion to `active` only happens on a later `recheck-watchlist` run.
- Wiring the actual weekly cron trigger for `recheck-watchlist` is out of scope for this plan (a follow-up setup step using Claude Code's own scheduling, not skill code).

---

## Task 1: Rewrite `scoring.py` for the new ICP rubric

**Files:**
- Modify: `.claude/skills/find-leads/scripts/scoring.py` (full rewrite)
- Test: `.claude/skills/find-leads/tests/test_scoring.py` (full rewrite)

**Interfaces:**
- Consumes: nothing (leaf module)
- Produces: `compute_score(classification: dict) -> dict` returning `{"score_total": int, "score_breakdown": dict, "tier": str}`; `format_breakdown(breakdown: dict) -> str`; `InvalidClassificationError`. `classification` must contain `icp_match`, `size_fit`, `company_stage`, `geo_fit`, `buyer_accessibility`, `wrong_fit_risk` (bool), plus whichever of `ai_native_maturity` / `regulatory_data_exposure` / `agent_deployment_stage` corresponds to `icp_match`. These are consumed downstream by Task 3 (CSV row shape) and Task 6 (`SKILL.md` classification instructions).

- [ ] **Step 1: Write the failing test suite**

Replace the full contents of `.claude/skills/find-leads/tests/test_scoring.py` with:

```python
import unittest

from scripts.scoring import compute_score, format_breakdown, InvalidClassificationError

ICP1_STRONG = {
    "icp_match": "ICP1",
    "ai_native_maturity": "Strong",
    "size_fit": "In range (20-200)",
    "company_stage": "On-target",
    "geo_fit": "EU",
    "buyer_accessibility": "Named",
    "wrong_fit_risk": False,
}

ICP2_STRONG = {
    "icp_match": "ICP2",
    "regulatory_data_exposure": "Explicit",
    "size_fit": "In range (20-200)",
    "company_stage": "On-target",
    "geo_fit": "EU",
    "buyer_accessibility": "Named",
    "wrong_fit_risk": False,
}

ICP3_PRODUCTION = {
    "icp_match": "ICP3",
    "agent_deployment_stage": "Production agents",
    "size_fit": "In range (20-200)",
    "company_stage": "On-target",
    "geo_fit": "EU",
    "buyer_accessibility": "Named",
    "wrong_fit_risk": False,
}


class ComputeScoreTests(unittest.TestCase):
    def test_full_score_icp1_strong_signals_is_hot(self):
        result = compute_score(ICP1_STRONG)
        self.assertEqual(result["score_total"], 100)
        self.assertEqual(result["tier"], "Hot")

    def test_full_score_icp2_strong_signals_is_hot(self):
        result = compute_score(ICP2_STRONG)
        self.assertEqual(result["score_total"], 100)
        self.assertEqual(result["tier"], "Hot")

    def test_full_score_icp3_production_agents_is_hot(self):
        result = compute_score(ICP3_PRODUCTION)
        self.assertEqual(result["score_total"], 100)
        self.assertEqual(result["tier"], "Hot")

    def test_icp3_scores_identically_to_icp1_when_all_dimensions_maxed(self):
        self.assertEqual(
            compute_score(ICP1_STRONG)["score_total"],
            compute_score(ICP3_PRODUCTION)["score_total"],
        )

    def test_poor_fit_is_always_not_a_fit_regardless_of_other_fields(self):
        classification = dict(ICP1_STRONG, icp_match="Poor fit")
        result = compute_score(classification)
        self.assertEqual(result["tier"], "Not-a-fit")
        self.assertEqual(result["score_breakdown"]["icp_match"], 0)
        self.assertEqual(result["score_breakdown"]["core_signal"], 0)

    def test_wrong_fit_risk_reduces_score_but_does_not_disqualify(self):
        classification = dict(ICP1_STRONG, wrong_fit_risk=True)
        result = compute_score(classification)
        self.assertEqual(result["score_breakdown"]["wrong_fit_penalty"], -10)
        self.assertEqual(result["score_total"], 90)
        self.assertEqual(result["tier"], "Hot")

    def test_agent_deployment_stage_exploring_scores_low_but_nonzero(self):
        classification = dict(
            ICP3_PRODUCTION,
            agent_deployment_stage="Exploring/considering",
            company_stage="Adjacent",
            geo_fit="US",
            buyer_accessibility="Known but unclear",
        )
        result = compute_score(classification)
        # icp_match 25 + core_signal 4 + size_fit 15 + company_stage 5 + geo_fit 8 + buyer_accessibility 7 = 64
        self.assertEqual(result["score_total"], 64)
        self.assertEqual(result["tier"], "Warm")

    def test_low_score_is_not_a_fit_tier(self):
        classification = {
            "icp_match": "ICP2",
            "regulatory_data_exposure": "None apparent",
            "size_fit": "Out of range",
            "company_stage": "Out of range",
            "geo_fit": "Other",
            "buyer_accessibility": "Unknown",
            "wrong_fit_risk": False,
        }
        result = compute_score(classification)
        self.assertEqual(result["score_total"], 25)
        self.assertEqual(result["tier"], "Cold")

    def test_unknown_icp_match_value_raises(self):
        classification = dict(ICP1_STRONG, icp_match="Nonsense")
        with self.assertRaises(InvalidClassificationError):
            compute_score(classification)

    def test_unknown_core_signal_value_raises(self):
        classification = dict(ICP1_STRONG, ai_native_maturity="Nonsense")
        with self.assertRaises(InvalidClassificationError):
            compute_score(classification)

    def test_format_breakdown_produces_compact_string(self):
        breakdown = {"icp_match": 25, "core_signal": 20}
        self.assertEqual(format_breakdown(breakdown), "icp_match=25;core_signal=20")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run from `.claude/skills/find-leads/`:
```
python -m unittest tests.test_scoring -v
```
Expected: failures/errors — old `scoring.py` doesn't recognize `icp_match`, `ai_native_maturity`, etc. (raises `InvalidClassificationError` or `KeyError` for every test).

- [ ] **Step 3: Rewrite the implementation**

Replace the full contents of `.claude/skills/find-leads/scripts/scoring.py` with:

```python
"""Deterministic scoring/tiering for a researched, classified lead.

Classification (icp_match, ai_native_maturity, etc.) is decided by the
research subagent from public signals; this module turns that
classification into a reproducible 0-100 score, a breakdown, and a
Hot/Warm/Cold/Not-a-fit tier.
"""

import argparse
import json

ICP_MATCH_POINTS = {
    "ICP1": 25,
    "ICP2": 25,
    "ICP3": 25,
    "Poor fit": 0,
}

AI_NATIVE_MATURITY_POINTS = {
    "Strong": 20,
    "Moderate": 10,
    "Weak/Unknown": 0,
}

REGULATORY_DATA_EXPOSURE_POINTS = {
    "Explicit": 20,
    "Implicit": 10,
    "None apparent": 0,
}

AGENT_DEPLOYMENT_STAGE_POINTS = {
    "Production agents": 20,
    "Piloting/building": 10,
    "Exploring/considering": 4,
    "None": 0,
}

CORE_SIGNAL_BY_ICP = {
    "ICP1": ("ai_native_maturity", AI_NATIVE_MATURITY_POINTS),
    "ICP2": ("regulatory_data_exposure", REGULATORY_DATA_EXPOSURE_POINTS),
    "ICP3": ("agent_deployment_stage", AGENT_DEPLOYMENT_STAGE_POINTS),
}

SIZE_FIT_POINTS = {
    "In range (20-200)": 15,
    "Out of range": 0,
}

COMPANY_STAGE_POINTS = {
    "On-target": 10,
    "Adjacent": 5,
    "Out of range": 0,
}

GEO_FIT_POINTS = {
    "EU": 15,
    "US": 8,
    "Other": 0,
}

BUYER_ACCESSIBILITY_POINTS = {
    "Named": 15,
    "Known but unclear": 7,
    "Unknown": 0,
}

WRONG_FIT_RISK_PENALTY = 10

TIER_THRESHOLDS = (
    ("Hot", 70),
    ("Warm", 45),
    ("Cold", 20),
    ("Not-a-fit", 0),
)


class InvalidClassificationError(ValueError):
    pass


def _lookup(table, key, field_name):
    if key not in table:
        raise InvalidClassificationError(
            f"Unknown value {key!r} for {field_name}; expected one of {sorted(table)}"
        )
    return table[key]


def compute_score(classification: dict) -> dict:
    """Compute score_total, score_breakdown, and tier for one company.

    `classification` must contain: icp_match, size_fit, company_stage,
    geo_fit, buyer_accessibility, wrong_fit_risk (bool), and whichever of
    ai_native_maturity / regulatory_data_exposure / agent_deployment_stage
    corresponds to icp_match (ICP1 / ICP2 / ICP3 respectively).
    """
    icp_match_points = _lookup(ICP_MATCH_POINTS, classification["icp_match"], "icp_match")

    if classification["icp_match"] in CORE_SIGNAL_BY_ICP:
        field_name, points_table = CORE_SIGNAL_BY_ICP[classification["icp_match"]]
        core_signal_points = _lookup(points_table, classification[field_name], field_name)
    else:
        core_signal_points = 0

    breakdown = {
        "icp_match": icp_match_points,
        "core_signal": core_signal_points,
        "size_fit": _lookup(SIZE_FIT_POINTS, classification["size_fit"], "size_fit"),
        "company_stage": _lookup(COMPANY_STAGE_POINTS, classification["company_stage"], "company_stage"),
        "geo_fit": _lookup(GEO_FIT_POINTS, classification["geo_fit"], "geo_fit"),
        "buyer_accessibility": _lookup(
            BUYER_ACCESSIBILITY_POINTS, classification["buyer_accessibility"], "buyer_accessibility"
        ),
    }

    breakdown["wrong_fit_penalty"] = -WRONG_FIT_RISK_PENALTY if classification.get("wrong_fit_risk", False) else 0

    score_total = max(0, min(100, sum(breakdown.values())))

    if classification["icp_match"] == "Poor fit":
        tier = "Not-a-fit"
    else:
        tier = next(name for name, floor in TIER_THRESHOLDS if score_total >= floor)

    return {
        "score_total": score_total,
        "score_breakdown": breakdown,
        "tier": tier,
    }


def format_breakdown(breakdown: dict) -> str:
    """Serialize a score breakdown dict to the compact CSV string format."""
    return ";".join(f"{k}={v}" for k, v in breakdown.items())


def _cli(argv=None):
    parser = argparse.ArgumentParser(description="Score a classified lead")
    sub = parser.add_subparsers(dest="command", required=True)
    score_parser = sub.add_parser("score")
    score_parser.add_argument("--input", required=True, help="JSON classification object")
    args = parser.parse_args(argv)

    if args.command == "score":
        classification = json.loads(args.input)
        result = compute_score(classification)
        result["score_breakdown_str"] = format_breakdown(result["score_breakdown"])
        print(json.dumps(result))


if __name__ == "__main__":
    _cli()
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```
python -m unittest tests.test_scoring -v
```
Expected: `OK` — all tests in `ComputeScoreTests` pass.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/find-leads/scripts/scoring.py .claude/skills/find-leads/tests/test_scoring.py
git commit -m "feat(find-leads): rebuild scoring rubric for the 3-ICP model"
```

---

## Task 2: Rewrite `segments.py` for the new ICP weighting

**Files:**
- Modify: `.claude/skills/find-leads/scripts/segments.py`
- Test: `.claude/skills/find-leads/tests/test_segments.py` (full rewrite)

**Interfaces:**
- Consumes: nothing (leaf module)
- Produces: `split_target(target: int, segments=None) -> dict` (unchanged signature), `SEGMENT_WEIGHTS` now keyed `icp1`/`icp2`/`icp3`, `ALL_SEGMENTS = ["icp1", "icp2", "icp3"]`, `UnknownSegmentError`. Consumed by Task 6's `SKILL.md` discover-mode instructions.

- [ ] **Step 1: Write the failing test suite**

Replace the full contents of `.claude/skills/find-leads/tests/test_segments.py` with:

```python
import unittest

from scripts.segments import split_target, UnknownSegmentError, ALL_SEGMENTS


class SplitTargetTests(unittest.TestCase):
    def test_split_target_default_sweep_sums_to_target(self):
        allocation = split_target(20)
        self.assertEqual(sum(allocation.values()), 20)
        self.assertEqual(set(allocation.keys()), set(ALL_SEGMENTS))

    def test_split_target_weights_icp1_and_icp2_equally_above_icp3(self):
        allocation = split_target(20)
        self.assertEqual(allocation["icp1"], allocation["icp2"])
        self.assertGreater(allocation["icp1"], allocation["icp3"])

    def test_split_target_matches_40_40_20_ratio(self):
        allocation = split_target(10)
        self.assertEqual(allocation, {"icp1": 4, "icp2": 4, "icp3": 2})

    def test_split_target_with_explicit_segments_splits_evenly(self):
        allocation = split_target(10, segments=["icp1", "icp2"])
        self.assertEqual(allocation, {"icp1": 5, "icp2": 5})

    def test_split_target_unknown_segment_raises(self):
        with self.assertRaises(UnknownSegmentError):
            split_target(10, segments=["not-a-segment"])

    def test_split_target_small_target_still_sums_correctly(self):
        allocation = split_target(3)
        self.assertEqual(sum(allocation.values()), 3)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```
python -m unittest tests.test_segments -v
```
Expected: failures — old `SEGMENT_WEIGHTS` keys (`healthcare`, `finance`, ...) don't match `icp1`/`icp2`/`icp3`.

- [ ] **Step 3: Rewrite the implementation**

Replace the full contents of `.claude/skills/find-leads/scripts/segments.py` with:

```python
"""Segment (ICP) weighting for discover-mode target-count splitting.

Weights reflect priority sequencing from the ICP base: ICP1 and ICP2 are
where the team spends now (equal weight), ICP3 is seeded at a lighter
weight since it's pipeline-building for the Authorization Broker, not
actively closed yet.
"""

import argparse
import json

SEGMENT_WEIGHTS = {
    "icp1": 2,
    "icp2": 2,
    "icp3": 1,
}

ALL_SEGMENTS = list(SEGMENT_WEIGHTS)


class UnknownSegmentError(ValueError):
    pass


def split_target(target: int, segments=None) -> dict:
    """Split `target` leads across segments.

    If `segments` is given, split evenly across exactly those segments
    (ignoring weights). Otherwise, split across ALL_SEGMENTS proportional
    to SEGMENT_WEIGHTS. Uses the largest-remainder method so allocations
    always sum exactly to `target`.
    """
    if segments is not None:
        for s in segments:
            if s not in SEGMENT_WEIGHTS:
                raise UnknownSegmentError(f"Unknown segment {s!r}; expected one of {ALL_SEGMENTS}")
        weights = {s: 1 for s in segments}
    else:
        weights = SEGMENT_WEIGHTS

    total_weight = sum(weights.values())
    raw = {s: target * w / total_weight for s, w in weights.items()}
    floors = {s: int(v) for s, v in raw.items()}
    remainder = target - sum(floors.values())

    remainders_sorted = sorted(weights, key=lambda s: raw[s] - floors[s], reverse=True)
    for s in remainders_sorted[:remainder]:
        floors[s] += 1

    return floors


def _cli(argv=None):
    parser = argparse.ArgumentParser(description="Split a discover-mode target across ICP segments")
    parser.add_argument("--target", type=int, required=True)
    parser.add_argument("--segments", help="comma-separated segment override")
    args = parser.parse_args(argv)
    segments = args.segments.split(",") if args.segments else None
    print(json.dumps(split_target(args.target, segments)))


if __name__ == "__main__":
    _cli()
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```
python -m unittest tests.test_segments -v
```
Expected: `OK` — all tests in `SplitTargetTests` pass.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/find-leads/scripts/segments.py .claude/skills/find-leads/tests/test_segments.py
git commit -m "feat(find-leads): reweight discover segments to icp1/icp2/icp3 (40/40/20)"
```

---

## Task 3: Update `csv_store.py` schema for the new columns

**Files:**
- Modify: `.claude/skills/find-leads/scripts/csv_store.py`
- Test: `.claude/skills/find-leads/tests/test_csv_store.py` (full rewrite)

**Interfaces:**
- Consumes: nothing new (schema-agnostic storage logic unchanged)
- Produces: `FIELDNAMES` (new column list/order below), `load_leads`, `save_leads`, `is_fresh`, `upsert_lead`, `is_active(row) -> bool` (unchanged), plus new `is_watchlist(row) -> bool`. Consumed by Task 5 (CSV migration) and Task 6 (`SKILL.md` CSV column reference / `recheck-watchlist` instructions).

- [ ] **Step 1: Write the failing test suite**

Replace the full contents of `.claude/skills/find-leads/tests/test_csv_store.py` with:

```python
import os
import shutil
import tempfile
import unittest
from datetime import date

from scripts.csv_store import (
    load_leads, save_leads, upsert_lead, is_active, is_watchlist, FIELDNAMES,
)

BASE_FIELDS = {
    "domain": "example.com",
    "company_name": "Example Inc",
    "icp_match": "ICP1",
    "vertical": "",
    "persona_match": "1B",
    "company_stage": "On-target",
    "ai_native_maturity": "Strong",
    "regulatory_data_exposure": "None apparent",
    "agent_deployment_stage": "None",
    "geo_fit": "EU",
    "size_fit": "In range (20-200)",
    "buyer_name": "Jane Doe",
    "buyer_title": "CTO",
    "buyer_accessibility": "Named",
    "wrong_fit_risk": "False",
    "score_total": "90",
    "score_breakdown": "icp_match=25;core_signal=20",
    "tier": "Hot",
    "reachability_notes": "Speaking at AI Native Summit 2026",
    "rationale": "Strong AI-native product signal, EU-based",
    "sources": "https://example.com/about",
    "confidence": "medium",
    "status": "active",
    "outcome": "",
}


class CsvStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.csv_path = os.path.join(self.tmp_dir, "leads.csv")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_load_leads_returns_empty_dict_when_file_missing(self):
        self.assertEqual(load_leads(self.csv_path), {})

    def test_upsert_lead_inserts_new_row_with_first_seen_and_last_researched_set(self):
        today = date(2026, 7, 9)
        leads, action = upsert_lead({}, BASE_FIELDS, today)
        self.assertEqual(action, "inserted")
        row = leads["example.com"]
        self.assertEqual(row["first_seen"], "2026-07-09")
        self.assertEqual(row["last_researched"], "2026-07-09")
        self.assertEqual(row["company_name"], "Example Inc")

    def test_upsert_lead_skips_when_existing_row_is_fresh(self):
        today = date(2026, 7, 9)
        leads, _ = upsert_lead({}, BASE_FIELDS, today)
        later = date(2026, 7, 20)
        leads2, action = upsert_lead(leads, BASE_FIELDS, later)
        self.assertEqual(action, "skipped_fresh")
        self.assertEqual(leads2["example.com"]["last_researched"], "2026-07-09")

    def test_upsert_lead_updates_when_existing_row_is_stale(self):
        today = date(2026, 7, 9)
        leads, _ = upsert_lead({}, BASE_FIELDS, today)
        much_later = date(2026, 9, 1)
        updated_fields = dict(BASE_FIELDS, tier="Warm", score_total="60")
        leads2, action = upsert_lead(leads, updated_fields, much_later)
        self.assertEqual(action, "updated")
        self.assertEqual(leads2["example.com"]["last_researched"], "2026-09-01")
        self.assertEqual(leads2["example.com"]["first_seen"], "2026-07-09")
        self.assertEqual(leads2["example.com"]["tier"], "Warm")

    def test_upsert_lead_force_refresh_overrides_freshness(self):
        today = date(2026, 7, 9)
        leads, _ = upsert_lead({}, BASE_FIELDS, today)
        later = date(2026, 7, 20)
        forced_fields = dict(BASE_FIELDS, force_refresh=True, tier="Cold")
        leads2, action = upsert_lead(leads, forced_fields, later)
        self.assertEqual(action, "updated")
        self.assertEqual(leads2["example.com"]["tier"], "Cold")

    def test_save_and_load_roundtrip_preserves_data(self):
        today = date(2026, 7, 9)
        leads, _ = upsert_lead({}, BASE_FIELDS, today)
        save_leads(self.csv_path, leads)
        reloaded = load_leads(self.csv_path)
        self.assertEqual(reloaded["example.com"]["company_name"], "Example Inc")
        self.assertEqual(set(reloaded["example.com"].keys()), set(FIELDNAMES))

    def test_is_active_true_when_status_active(self):
        self.assertTrue(is_active({"status": "active"}))

    def test_is_active_false_when_status_disqualified(self):
        self.assertFalse(is_active({"status": "disqualified"}))

    def test_is_watchlist_true_when_status_watchlist(self):
        self.assertTrue(is_watchlist({"status": "watchlist"}))

    def test_is_watchlist_false_when_status_active(self):
        self.assertFalse(is_watchlist({"status": "active"}))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```
python -m unittest tests.test_csv_store -v
```
Expected: failures — `is_watchlist` doesn't exist yet; `FIELDNAMES` doesn't match `BASE_FIELDS`' new keys, so the roundtrip key-set assertion fails.

- [ ] **Step 3: Update the implementation**

In `.claude/skills/find-leads/scripts/csv_store.py`, replace the `FIELDNAMES` list:

```python
FIELDNAMES = [
    "domain", "company_name", "icp_match", "vertical", "persona_match",
    "company_stage", "ai_native_maturity", "regulatory_data_exposure",
    "agent_deployment_stage", "geo_fit", "size_fit", "buyer_name",
    "buyer_title", "buyer_accessibility", "wrong_fit_risk",
    "score_total", "score_breakdown", "tier", "reachability_notes",
    "rationale", "sources", "confidence", "first_seen", "last_researched",
    "status", "outcome",
]
```

And add `is_watchlist` immediately after the existing `is_active` function:

```python
def is_active(row: dict) -> bool:
    return row.get("status", "active") == "active"


def is_watchlist(row: dict) -> bool:
    return row.get("status") == "watchlist"
```

No other changes to `csv_store.py` — `load_leads`, `save_leads`, `is_fresh`, `upsert_lead`, and the CLI are all schema-agnostic (they operate generically over `FIELDNAMES`).

- [ ] **Step 4: Run tests to verify they pass**

Run:
```
python -m unittest tests.test_csv_store -v
```
Expected: `OK` — all tests in `CsvStoreTests` pass.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/find-leads/scripts/csv_store.py .claude/skills/find-leads/tests/test_csv_store.py
git commit -m "feat(find-leads): update leads.csv schema for icp_match/persona_match/geo_fit and add is_watchlist"
```

---

## Task 4: Update `report.py` — drop old flag, add `recheck-watchlist` report

**Files:**
- Modify: `.claude/skills/find-leads/scripts/report.py`
- Test: `.claude/skills/find-leads/tests/test_report.py` (full rewrite)

**Interfaces:**
- Consumes: nothing new (accepts plain dicts, no dependency on Task 1-3's modules)
- Produces: `generate_run_report(mode, segment, run_date, results, skipped) -> str` (flagging logic simplified to `wrong_fit_risk` only), new `generate_watchlist_recheck_report(run_date, rechecked: list) -> str`. CLI gains `--mode recheck-watchlist` and a `--rechecked` argument. Consumed by Task 6's `SKILL.md` reporting instructions.

- [ ] **Step 1: Write the failing test suite**

Replace the full contents of `.claude/skills/find-leads/tests/test_report.py` with:

```python
import unittest
from datetime import date

from scripts.report import generate_run_report, generate_watchlist_recheck_report

RESULT_A = {
    "company_name": "Acme AI",
    "domain": "acmeai.com",
    "score_total": 90,
    "tier": "Hot",
    "rationale": "Strong AI-native product signal, EU-based",
    "wrong_fit_risk": False,
}

RESULT_B = {
    "company_name": "Beta Legal",
    "domain": "betalegal.com",
    "score_total": 60,
    "tier": "Warm",
    "rationale": "Regulated data exposure, moderate signal",
    "wrong_fit_risk": True,
}


class GenerateRunReportTests(unittest.TestCase):
    def test_report_includes_header_with_mode_segment_and_date(self):
        report = generate_run_report("discover", "icp1", date(2026, 7, 9), [], [])
        self.assertIn("discover", report)
        self.assertIn("icp1", report)
        self.assertIn("2026-07-09", report)

    def test_report_lists_top_5_sorted_by_score_descending(self):
        report = generate_run_report("discover", None, date(2026, 7, 9), [RESULT_B, RESULT_A], [])
        self.assertLess(report.index("Acme AI"), report.index("Beta Legal"))

    def test_report_flags_wrong_fit_risk(self):
        report = generate_run_report("discover", None, date(2026, 7, 9), [RESULT_A, RESULT_B], [])
        flags_section = report.split("## Flags needing attention")[1]
        self.assertIn("Beta Legal", flags_section)
        self.assertIn("wrong-fit risk", flags_section)

    def test_report_does_not_flag_clean_results(self):
        report = generate_run_report("discover", None, date(2026, 7, 9), [RESULT_A], [])
        self.assertNotIn("Flags needing attention", report)

    def test_report_lists_skipped_with_reasons(self):
        skipped = [{"company_name": "Gamma Corp", "reason": "already fresh in CSV"}]
        report = generate_run_report("discover", None, date(2026, 7, 9), [], skipped)
        self.assertIn("Gamma Corp", report)
        self.assertIn("already fresh in CSV", report)


PROMOTED = {
    "company_name": "Agentic Co",
    "domain": "agenticco.com",
    "prev_status": "watchlist",
    "new_status": "active",
    "prev_agent_deployment_stage": "Piloting/building",
    "new_agent_deployment_stage": "Production agents",
    "score_total": 74,
    "tier": "Hot",
}

DISQUALIFIED = {
    "company_name": "Defunct Inc",
    "domain": "defunct.com",
    "prev_status": "watchlist",
    "new_status": "disqualified",
    "prev_agent_deployment_stage": "Exploring/considering",
    "new_agent_deployment_stage": "None",
    "score_total": 10,
    "tier": "Not-a-fit",
}

PROGRESSED = {
    "company_name": "Warming Up Co",
    "domain": "warmingup.com",
    "prev_status": "watchlist",
    "new_status": "watchlist",
    "prev_agent_deployment_stage": "Exploring/considering",
    "new_agent_deployment_stage": "Piloting/building",
    "score_total": 50,
    "tier": "Warm",
}

UNCHANGED = {
    "company_name": "Steady Co",
    "domain": "steadyco.com",
    "prev_status": "watchlist",
    "new_status": "watchlist",
    "prev_agent_deployment_stage": "Exploring/considering",
    "new_agent_deployment_stage": "Exploring/considering",
    "score_total": 40,
    "tier": "Cold",
}


class GenerateWatchlistRecheckReportTests(unittest.TestCase):
    def test_report_includes_header_with_date_and_count(self):
        report = generate_watchlist_recheck_report(date(2026, 7, 16), [PROMOTED])
        self.assertIn("2026-07-16", report)
        self.assertIn("1 companies rechecked", report)

    def test_report_lists_promotions_with_stage_change(self):
        report = generate_watchlist_recheck_report(date(2026, 7, 16), [PROMOTED])
        section = report.split("## Promoted to active")[1]
        self.assertIn("Agentic Co", section)
        self.assertIn("Piloting/building", section)
        self.assertIn("Production agents", section)

    def test_report_lists_disqualified(self):
        report = generate_watchlist_recheck_report(date(2026, 7, 16), [DISQUALIFIED])
        section = report.split("## Disqualified")[1]
        self.assertIn("Defunct Inc", section)

    def test_report_lists_progressed_but_not_yet_promoted(self):
        report = generate_watchlist_recheck_report(date(2026, 7, 16), [PROGRESSED])
        section = report.split("## Progressed (still watching)")[1]
        self.assertIn("Warming Up Co", section)
        self.assertIn("Exploring/considering", section)
        self.assertIn("Piloting/building", section)

    def test_report_counts_unchanged_without_listing_them_individually(self):
        report = generate_watchlist_recheck_report(date(2026, 7, 16), [UNCHANGED])
        self.assertIn("1 companies unchanged", report)
        self.assertNotIn("Steady Co", report)

    def test_report_with_no_changes_omits_promoted_disqualified_progressed_sections(self):
        report = generate_watchlist_recheck_report(date(2026, 7, 16), [UNCHANGED])
        self.assertNotIn("## Promoted to active", report)
        self.assertNotIn("## Disqualified", report)
        self.assertNotIn("## Progressed (still watching)", report)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```
python -m unittest tests.test_report -v
```
Expected: failures — `generate_watchlist_recheck_report` doesn't exist yet (`ImportError`); existing flag test still passes but is being replaced.

- [ ] **Step 3: Update the implementation**

Replace the full contents of `.claude/skills/find-leads/scripts/report.py` with:

```python
"""Markdown run-report generation for discover/score-list/recheck-watchlist runs."""

import argparse
import json
import os
from datetime import date as date_cls


def generate_run_report(mode: str, segment, run_date, results: list, skipped: list) -> str:
    """Build the markdown report for one discover/score-list run.

    `results`: list of dicts with at least company_name, domain, score_total,
      tier, rationale, wrong_fit_risk (bool).
    `skipped`: list of dicts with company_name and a `reason` string.
    """
    lines = []
    segment_label = segment or "all segments"
    lines.append(f"# Lead run — {mode} — {segment_label} — {run_date.isoformat()}")
    lines.append("")
    lines.append(f"**{len(results)} companies researched, {len(skipped)} skipped.**")
    lines.append("")

    top5 = sorted(results, key=lambda r: r["score_total"], reverse=True)[:5]
    if top5:
        lines.append("## Top 5")
        for r in top5:
            lines.append(
                f"- **{r['company_name']}** ({r['domain']}) — "
                f"{r['score_total']}/100, {r['tier']} — {r['rationale']}"
            )
        lines.append("")

    flagged = [r for r in results if r.get("wrong_fit_risk")]
    if flagged:
        lines.append("## Flags needing attention")
        for r in flagged:
            lines.append(f"- **{r['company_name']}** — wrong-fit risk")
        lines.append("")

    if skipped:
        lines.append("## Skipped")
        for s in skipped:
            lines.append(f"- {s['company_name']} — {s['reason']}")
        lines.append("")

    return "\n".join(lines)


def generate_watchlist_recheck_report(run_date, rechecked: list) -> str:
    """Build the markdown report for a recheck-watchlist run.

    `rechecked`: list of dicts with company_name, domain, prev_status,
      new_status, prev_agent_deployment_stage, new_agent_deployment_stage,
      score_total, tier.
    """
    lines = [f"# Watchlist recheck — {run_date.isoformat()}", ""]
    lines.append(f"**{len(rechecked)} companies rechecked.**")
    lines.append("")

    promoted = [r for r in rechecked if r["new_status"] == "active"]
    disqualified = [r for r in rechecked if r["new_status"] == "disqualified"]
    progressed = [
        r for r in rechecked
        if r["new_status"] == "watchlist"
        and r["new_agent_deployment_stage"] != r["prev_agent_deployment_stage"]
    ]
    changed_domains = {r["domain"] for r in promoted + disqualified + progressed}
    unchanged = [r for r in rechecked if r["domain"] not in changed_domains]

    if promoted:
        lines.append("## Promoted to active")
        for r in promoted:
            lines.append(
                f"- **{r['company_name']}** ({r['domain']}) — "
                f"{r['prev_agent_deployment_stage']} → {r['new_agent_deployment_stage']}, "
                f"{r['score_total']}/100 {r['tier']}"
            )
        lines.append("")

    if disqualified:
        lines.append("## Disqualified")
        for r in disqualified:
            lines.append(f"- **{r['company_name']}** ({r['domain']})")
        lines.append("")

    if progressed:
        lines.append("## Progressed (still watching)")
        for r in progressed:
            lines.append(
                f"- **{r['company_name']}** ({r['domain']}) — "
                f"{r['prev_agent_deployment_stage']} → {r['new_agent_deployment_stage']}"
            )
        lines.append("")

    lines.append(f"**{len(unchanged)} companies unchanged.**")
    lines.append("")

    return "\n".join(lines)


def _cli(argv=None):
    parser = argparse.ArgumentParser(description="Generate a lead run markdown report")
    parser.add_argument("--mode", required=True, choices=["discover", "score-list", "recheck-watchlist"])
    parser.add_argument("--segment", default=None)
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--results", default=None, help="JSON list of result dicts")
    parser.add_argument("--skipped", default="[]", help="JSON list of skipped dicts")
    parser.add_argument("--rechecked", default=None, help="JSON list of recheck dicts (recheck-watchlist mode)")
    parser.add_argument("--out", required=True, help="output markdown file path")
    args = parser.parse_args(argv)

    run_date = date_cls.fromisoformat(args.date)

    if args.mode == "recheck-watchlist":
        rechecked = json.loads(args.rechecked or "[]")
        report = generate_watchlist_recheck_report(run_date, rechecked)
    else:
        results = json.loads(args.results or "[]")
        skipped = json.loads(args.skipped)
        report = generate_run_report(args.mode, args.segment, run_date, results, skipped)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    _cli()
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```
python -m unittest tests.test_report -v
```
Expected: `OK` — all tests in `GenerateRunReportTests` and `GenerateWatchlistRecheckReportTests` pass.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/find-leads/scripts/report.py .claude/skills/find-leads/tests/test_report.py
git commit -m "feat(find-leads): add recheck-watchlist report generator, drop startup_stigma_routing flag"
```

---

## Task 5: Archive the old-schema `leads.csv` data

The 7 rows currently in `data/leads.csv` were scored under the retired 7-segment rubric and carry columns (`segment_fit`, old `vertical`, `startup_stigma_routing`) that no longer exist in `FIELDNAMES`. Rather than attempt a lossy field-by-field migration, archive the old file as-is and start a fresh, empty CSV under the new schema — companies worth keeping can be re-run through `score-list` to get real ICP1/ICP2/ICP3 classifications.

**Files:**
- Create: `data/archive/leads-v1-2026-07-08.csv` (copy of current `data/leads.csv`)
- Modify: `data/leads.csv` (replaced with header-only, new schema)

**Interfaces:**
- Consumes: `FIELDNAMES` from Task 3's `csv_store.py`
- Produces: an empty `leads.csv` ready for `discover`/`score-list` to populate under the new schema

- [ ] **Step 1: Archive the current file**

From the repo root:
```bash
mkdir -p data/archive
cp data/leads.csv data/archive/leads-v1-2026-07-08.csv
```

- [ ] **Step 2: Replace `data/leads.csv` with a new, empty, new-schema file**

From `.claude/skills/find-leads/`:
```bash
python -c "
import sys
sys.path.insert(0, '.')
from scripts.csv_store import save_leads
save_leads('../../../data/leads.csv', {})
"
```

- [ ] **Step 3: Verify the new file has the correct header and no data rows**

From the repo root:
```bash
python -c "
with open('data/leads.csv', encoding='utf-8') as f:
    lines = f.readlines()
assert len(lines) == 1, f'expected header only, got {len(lines)} lines'
assert lines[0].strip() == (
    'domain,company_name,icp_match,vertical,persona_match,company_stage,'
    'ai_native_maturity,regulatory_data_exposure,agent_deployment_stage,'
    'geo_fit,size_fit,buyer_name,buyer_title,buyer_accessibility,wrong_fit_risk,'
    'score_total,score_breakdown,tier,reachability_notes,rationale,sources,'
    'confidence,first_seen,last_researched,status,outcome'
), 'header does not match new FIELDNAMES'
print('OK: leads.csv is header-only under the new schema')
"
```
Expected output: `OK: leads.csv is header-only under the new schema`

- [ ] **Step 4: Commit**

```bash
git add data/leads.csv data/archive/leads-v1-2026-07-08.csv
git commit -m "chore(find-leads): archive old-schema leads.csv, reset to new ICP schema"
```

---

## Task 6: Rewrite `SKILL.md` for the new ICP model, personas, and `recheck-watchlist` mode

**Files:**
- Modify: `.claude/skills/find-leads/SKILL.md` (full rewrite)

**Interfaces:**
- Consumes: `icp1`/`icp2`/`icp3` segment keys (Task 2), new `FIELDNAMES` column order (Task 3), `report.py --mode recheck-watchlist` CLI (Task 4)
- Produces: the instructions Claude follows when running this skill — no code interface, this is the skill's prompt surface

- [ ] **Step 1: Replace the full contents of `.claude/skills/find-leads/SKILL.md`**

```markdown
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

## The ICP

Three ICPs, sequenced by priority — ICP1 and ICP2 are where the team spends now; ICP3 is a watchlist populated today but not actively closed until the Authorization Broker is past prototype.

### ICP1 — AI-Native Product Companies (runtime security core)

Companies whose product runs on proprietary LLMs, RAG, or ML in production, shipping AI features continuously. Size 20–200, Stage Series A–B, Geo EU-first (Zürich base + GDPR/EU AI Act tailwind), US second. Lead product: Runtime Security Proxy. Wedge in: ShadowAI (free demo). Core pain: their own AI runtime is an unmonitored attack surface — prompt injection, exfiltration, an unauthorized/unauditable agent action.

**Personas:**
- **1A. Founder/CEO** (economic buyer) — technical, now runs the company, is the de facto CISO at this stage. Owns budget, investor relationships, the trust story. Fear: a security failure that torches customer trust or an unanswerable due-diligence question. Convert with investor optics and liability framing. Signs, but rarely finds you first.
- **1B. Head of Engineering/VP Eng** (technical champion) — owns AI systems in production, feels the black-box problem daily. No budget, but the door-opener and validator. Convert with mechanism/depth — the runtime proxy, what it catches, how it deploys. Entry point at most ICP1 accounts.
- **1C. AI/ML Lead or Staff ML Engineer** (hands-on user) — would actually run ShadowAI and read the flags. Feels the pain most, can't authorize a purchase. Generates internal urgency upward. Convert with the product experience itself.

### ICP2 — Sensitive-Data Adopters (DLP + PII wedge)

Mid-market companies handling regulated or sensitive data — fintech, healthtech, insurtech, legaltech, HR-tech — adopting AI across internal operations. Size 20–200, fast-moving but carrying real compliance exposure, Geo EU-first. Lead product: ShadowAI (client-side DLP) → Runtime Proxy once internal AI/RAG is found. Core pain: employees pasting contracts/patient records/financials into unsanctioned AI tools; PII leaking invisibly; GDPR/EU AI Act/HIPAA liability regardless of intent.

**Personas:**
- **2A. CISO/Head of Security** (economic buyer) — real security function and compliance exposure, AI spreading faster than he can govern. Fear: a regulated-data leak he can't see or prove he tried to prevent. Convert with visibility and audit trails. Clearest budget holder of the nine personas.
- **2B. Head of Compliance/DPO** (co-buyer, urgency engine) — owns GDPR/HIPAA/EU AI Act exposure, thinks in liability/audit-readiness, not "security tools." Rarely initiates but can force a purchase by naming the risk. Convert by turning compliance into a feature. Pair with the CISO to move the deal.
- **2C. IT/Security Manager** (technical champion) — runs endpoint tooling, knows employees are pasting sensitive data but can't quantify it. ShadowAI hands him the number, which he takes to the CISO as evidence — the deal opener.

### ICP3 — Agentic Companies (seed now, convert later)

Companies deploying autonomous agents in production — agents that take actions, call tools, transact. Size 20–200, Series A–B, earliest-adopter profile. Lead product: Authorization Broker (prototype) + Runtime Proxy for agentic pipelines. Core pain: agents acting without authorization or audit trail, instruction hijacking, tool-call abuse. Status: pipeline-seeding, not active-close — build the list, warm the relationships, sell when the product is ready.

**Personas:**
- **3A. Founder/CEO** (economic buyer) — building an agentic product, betting the company on autonomy. Trust/auditability existential — one unauthorized agent action in front of the wrong customer is business-ending. Convert later with Authorization Broker; warm now by already thinking about agent security.
- **3B. Head of AI/Agent Platform Lead** (technical champion) — owns agent pipelines, tool-calling, orchestration; lives closest to instruction hijacking and tool-call abuse. Convert with runtime proxy for agentic pipelines today, Authorization Broker tomorrow. The live relationship in ICP3 — co-designs if you show up early.
- **3C. Security Engineer** (hands-on user) — would instrument agents and read authorization logs. The internal signal that agent security is a real budget line, not a someday. Convert with mechanism/depth once the Broker is past prototype.

Personas are a working hypothesis — refine as real research (LinkedIn, org charts, press) accumulates.

**Cross-cutting:** ShadowAI is the universal free wedge, not exclusive to ICP2 — it's how you get in the door everywhere. What converts differs: Runtime Proxy for the builders (ICP1), PII/DLP depth for the adopters (ICP2).

## Modes

### `discover [segment] [--target N] [--segments a,b,c]`

Searches the web for new candidate companies matching the ICP. Default target: 15 new leads. With no segment/`--segments` given, sweeps all three ICPs using the weighted split below.

### `score-list <companies>`

Given a list of company names/domains/URLs (pasted, or from a file), skips discovery and researches+scores each one directly. No target count — bounded by the list. If the list exceeds 50 companies, process in batches of ~10. If an entry is a typo'd name or a dead/unresolvable domain, record it under `skipped` with reason "Could not resolve" and do not add it to the CSV.

### `recheck-watchlist`

No arguments. Re-researches every `status = watchlist` row in the CSV (ICP3 leads seeded via `discover`/`score-list`), regardless of the normal 30-day freshness window — refreshing watchlist rows on a schedule is this mode's entire purpose. For each row:

1. Re-run the standard per-company research pipeline (same ~5-search budget, same triage stages as discover/score-list).
2. Re-classify and re-score; update `agent_deployment_stage` and all other fields; bump `last_researched` (pass `force_refresh: true` to `csv_store.py upsert`).
3. If the new `agent_deployment_stage` is `Production agents` → set `status: active` (promoted off the watchlist, regardless of overall tier).
4. If the company is now clearly dead or has pivoted away from agents entirely → set `status: disqualified`.
5. Otherwise → leave `status: watchlist`, fields refreshed.
6. Accumulate one entry per company into a `rechecked` list: `{company_name, domain, prev_status, new_status, prev_agent_deployment_stage, new_agent_deployment_stage, score_total, tier}`.

After processing all watchlist rows, run:
```
python scripts/report.py --mode recheck-watchlist --date <YYYY-MM-DD> --rechecked '<JSON list of rechecked dicts>' --out "F:\_WORKY\blindsight\GITHUB\lead-gen\runs\<YYYY-MM-DD>-watchlist-recheck.md"
```

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

For every candidate company (from discovery search results or the provided list):

1. **Freshness check.** Run `python scripts/csv_store.py check-fresh --csv "F:\_WORKY\blindsight\GITHUB\lead-gen\data\leads.csv" --domain <domain>`. If it prints `fresh`, skip research entirely — record it under `skipped` with reason "already fresh in CSV" and move to the next company. If it prints anything for a row whose `status` is `disqualified` or `customer`, also skip it (don't resurface disqualified/customer companies in `discover`). Rows with `status: watchlist` ARE resurfaced normally by `discover`/`score-list` freshness rules — only `recheck-watchlist` treats them specially (bypassing freshness entirely).
2. **Stage 1 triage (1 search).** Do one broad web search on the company. If it's clearly a hard disqualifier — a government entity, not an active business, wildly outside the ~20–200 employee range, or a pre-seed startup with no AI angle at all — stop here. Set `icp_match: "Poor fit"` and don't spend further search budget on this company; it doesn't count toward `discover`'s target.
3. **Stage 2 triage (up to 3 more searches, 2–4 total).** Search for AI-native product signals, regulated/sensitive-data handling, and agent/agentic-workflow signals (company site, news, job postings) — this single set of searches informs `ai_native_maturity`, `regulatory_data_exposure`, and `agent_deployment_stage` all at once, no separate search budget per dimension. If by search 4 there's no signal on any of the three, stop and record it under `skipped` with reason "Weak signal / insufficient public info".
4. **Full research (up to 1 more search, 5 total).** Only for companies that cleared stage 2: search for a likely buyer (named CEO/CTO/technical leader from publicly published sources only — no LinkedIn scraping or gated-site access) and geography (EU vs. US vs. other, from company site/press/registration).
5. **Classify.** From what was found, produce a classification object using the exact allowed values below.
6. **Score.** Run `python scripts/scoring.py score --input '<classification JSON>'` to get `score_total`, `score_breakdown`, `score_breakdown_str`, and `tier`.
7. **Set status.** `icp_match == "ICP3"` → `status: "watchlist"`, unconditionally, even if `agent_deployment_stage` is already `"Production agents"` on this first pass (promotion only happens on a later `recheck-watchlist` run). `icp_match` in `{"ICP1", "ICP2"}` → `status: "active"` as normal. `icp_match == "Poor fit"` → don't persist to the CSV at all (record under `skipped` per stage-1 triage above).
8. **Persist.** Merge the classification fields, status, and score fields into one row (see "CSV row — column reference" below) and run `python scripts/csv_store.py upsert --csv "F:\_WORKY\blindsight\GITHUB\lead-gen\data\leads.csv" --input '<row JSON>'`.
9. **Accumulate** the row into this run's `results` list (or into `skipped` with a reason, for anything stopped at freshness or triage).

Research companies in parallel (one subagent per company via the Agent tool), 5–8 at a time, each following steps 1–9 independently; aggregate afterward.

### Classification field values (must match exactly — `scoring.py` rejects anything else)

- `icp_match`: `ICP1` | `ICP2` | `ICP3` | `Poor fit` — primary classification. Pick the strongest/primary fit; if a company plausibly fits more than one ICP (e.g. an AI-native product company that also handles regulated data), note the secondary fit in `rationale` rather than losing it.
- `vertical`: `fintech` | `healthtech` | `insurtech` | `legaltech` | `hr-tech` | `other` | *(blank)* — populate **only** when `icp_match = ICP2`; leave blank for ICP1/ICP3.
- `persona_match`: one of `1A`, `1B`, `1C`, `2A`, `2B`, `2C`, `3A`, `3B`, `3C`, or `"No clear match"` — whichever defined persona the identified buyer maps to (see "The ICP" personas above).
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

For `discover`/`score-list`, run:
```
python scripts/report.py --mode <discover|score-list> --segment <segment-or-omit> --date <YYYY-MM-DD> --results '<JSON list of result rows>' --skipped '<JSON list of {company_name, reason}>' --out "F:\_WORKY\blindsight\GITHUB\lead-gen\runs\<YYYY-MM-DD>-<mode>-<segment-or-list>.md"
```

For `recheck-watchlist`, see the mode's own reporting command above.

Report the output file path and a one-paragraph summary back to the user.
```

- [ ] **Step 2: Review checklist (manual — no automated test for this file)**

Confirm each of the following by reading the rewritten `SKILL.md`:
- [ ] All 9 personas (1A–3C) are present with their convert-with guidance.
- [ ] Every classification field name/value matches exactly what `scripts/scoring.py` (Task 1) accepts — cross-check against `ICP_MATCH_POINTS`, `AI_NATIVE_MATURITY_POINTS`, `REGULATORY_DATA_EXPOSURE_POINTS`, `AGENT_DEPLOYMENT_STAGE_POINTS`, `SIZE_FIT_POINTS`, `COMPANY_STAGE_POINTS`, `GEO_FIT_POINTS`, `BUYER_ACCESSIBILITY_POINTS`.
- [ ] Segment keys (`icp1`/`icp2`/`icp3`) match `scripts/segments.py`'s `SEGMENT_WEIGHTS` (Task 2).
- [ ] CSV column reference table's 26 columns, in order, match `scripts/csv_store.py`'s `FIELDNAMES` (Task 3).
- [ ] `recheck-watchlist`'s reporting command matches `scripts/report.py`'s `--mode recheck-watchlist` / `--rechecked` CLI args (Task 4).
- [ ] No remaining references to the retired `segment_fit`, old `vertical` enum, or `startup_stigma_routing`.

- [ ] **Step 3: Run the full test suite as a final regression check**

From `.claude/skills/find-leads/`:
```
python -m unittest discover -v
```
Expected: `OK` — all tests across `test_scoring.py`, `test_segments.py`, `test_csv_store.py`, `test_report.py` pass (26+ tests, exact count depends on additions above).

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/find-leads/SKILL.md
git commit -m "docs(find-leads): rewrite SKILL.md for the 3-ICP model, personas, and recheck-watchlist mode"
```

---

## Post-implementation validation (not a build task — do this after Task 6, using the live skill)

The spec's Validation Approach requires actually invoking `/find-leads` with real web search, which only exists once the skill is loaded into a live Claude Code session — it can't be scripted as a build-time step. Once Task 6 is complete, run these manually before trusting the skill for real outreach decisions:

1. **Known-answer test** — `score-list` a known ICP1 example (an AI-native product company you already know well), a known ICP2 example (a fintech/healthtech/etc. company adopting AI internally), and an obvious non-fit; confirm `icp_match`/score/tier match intuition for each.
2. **ICP3 watchlist smoke test** — `score-list` a known agentic-AI company (one that's already running production agents) and confirm it still lands as `status = watchlist` on this first pass, per the "always enters as watchlist" rule — it should NOT go straight to `active` even though `agent_deployment_stage` is `Production agents`.
3. **Recheck-watchlist smoke test** — with at least one `status = watchlist` row present (from Step 2 above), run `recheck-watchlist` and confirm: the freshness gate is bypassed (the row refreshes even though it's brand new), and if you manually re-run with the same company's `agent_deployment_stage` still `Production agents`, it promotes to `status = active`.
4. **Edge-case check** — `score-list` a typo'd company name and a dead/nonexistent domain, confirm both come back as "Could not resolve" in the report rather than producing garbage CSV rows.
