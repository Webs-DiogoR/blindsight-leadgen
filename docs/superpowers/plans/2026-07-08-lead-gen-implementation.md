# Lead Discovery & Scoring Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code skill (`find-leads`) that discovers and/or scores Blindsight sales leads against the company's ICP, producing a persistent CSV and per-run markdown reports.

**Architecture:** Deterministic scoring/classification-rollup, CSV persistence, segment weighting, and report generation live in small, independently tested Python modules under `scripts/`. A `SKILL.md` instructs Claude on the research/classification workflow (which is judgment-based and not unit-testable) and tells it exactly when and how to call those scripts, so scoring stays consistent across runs instead of being re-derived ad hoc by the model each time.

**Tech Stack:** Python 3 standard library only (`csv`, `json`, `argparse`, `datetime`, `unittest`) — no third-party dependencies. Markdown skill file for Claude Code (`.claude/skills/find-leads/SKILL.md`).

## Global Constraints

- Data sources: public web search only. No paid enrichment APIs, no scraping of gated sites (per spec Constraints).
- No CRM integration in this version (per spec Out of Scope).
- Freshness window default: 30 days (per spec Output Format).
- Concurrency cap: ~5–8 companies researched in parallel (per spec Run Bounds).
- Per-company search budget: 5 total searches — 1 for Stage 1 triage, up to 3 more for Stage 2, 1 more for full research if both stages pass (per spec Per-Company Research Process).
- `discover` default target: 15 new leads, split across segments roughly 80/20 toward validated vs. exploratory segments (per spec Discover Mode — Segment Sweep).
- No git repository for this project (removed by user request; will be set up later) — skip all git/commit steps in this plan.
- Python: standard library only. `pytest` is not installed in this environment, so tests use the built-in `unittest` module — do not add a `pytest` dependency.
- Buyer names/titles stored are limited to what's publicly published; no personal contact info (per spec Output Format).
- Project root: `F:\_WORKY\blindsight\lead-gen`.

---

## File Structure

```
F:\_WORKY\blindsight\lead-gen\
  .claude\skills\find-leads\
    SKILL.md
    scripts\
      __init__.py
      scoring.py       # classification -> {score_total, score_breakdown, tier}
      csv_store.py      # leads.csv load/save/upsert/freshness
      segments.py        # discover-mode target-count splitting across ICP segments
      report.py            # per-run markdown report generation
    tests\
      __init__.py
      test_scoring.py
      test_csv_store.py
      test_segments.py
      test_report.py
  data\
    leads.csv       # created empty (header only) during Task 5
  runs\                # per-run markdown reports land here
```

---

### Task 1: Project scaffolding + scoring engine

**Files:**
- Create: `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\scripts\__init__.py`
- Create: `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\tests\__init__.py`
- Create: `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\scripts\scoring.py`
- Test: `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\tests\test_scoring.py`

**Interfaces:**
- Produces: `compute_score(classification: dict) -> dict` returning `{"score_total": int, "score_breakdown": dict, "tier": str}`. `format_breakdown(breakdown: dict) -> str`. `InvalidClassificationError(ValueError)`.
- CLI: `python scripts/scoring.py score --input '<json classification>'` prints a JSON object with `score_total`, `score_breakdown`, `score_breakdown_str`, `tier`.

- [ ] **Step 1: Create the package scaffolding**

Create `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\scripts\__init__.py` (empty file) and `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\tests\__init__.py` (empty file).

- [ ] **Step 2: Write the failing tests**

Create `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\tests\test_scoring.py`:

```python
import unittest

from scripts.scoring import compute_score, format_breakdown, InvalidClassificationError

PRIMARY_ICP_STRONG = {
    "segment_fit": "Primary ICP",
    "ai_adoption": "Strong",
    "regulatory_exposure": "Explicit",
    "size_fit": "In range (50-500)",
    "buyer_accessibility": "Named",
    "vertical": "Healthcare",
    "wrong_fit_risk": False,
}


class ComputeScoreTests(unittest.TestCase):
    def test_full_score_primary_icp_strong_signals_is_hot(self):
        result = compute_score(PRIMARY_ICP_STRONG)
        self.assertEqual(result["score_total"], 100)
        self.assertEqual(result["tier"], "Hot")

    def test_poor_fit_is_always_not_a_fit_regardless_of_other_fields(self):
        classification = dict(PRIMARY_ICP_STRONG, segment_fit="Poor fit")
        result = compute_score(classification)
        self.assertEqual(result["tier"], "Not-a-fit")
        self.assertEqual(result["score_total"], 70)

    def test_crypto_finance_vertical_gets_bonus_capped_at_100(self):
        classification = dict(PRIMARY_ICP_STRONG, vertical="Finance - crypto-finance")
        result = compute_score(classification)
        self.assertEqual(result["score_breakdown"]["vertical_bonus"], 5)
        self.assertEqual(result["score_total"], 100)

    def test_wrong_fit_risk_reduces_score_but_does_not_disqualify(self):
        classification = dict(PRIMARY_ICP_STRONG, wrong_fit_risk=True)
        result = compute_score(classification)
        self.assertEqual(result["score_breakdown"]["wrong_fit_penalty"], -10)
        self.assertEqual(result["score_total"], 90)
        self.assertEqual(result["tier"], "Hot")

    def test_low_score_is_not_a_fit_tier(self):
        classification = {
            "segment_fit": "Exploratory",
            "ai_adoption": "Weak/Unknown",
            "regulatory_exposure": "None apparent",
            "size_fit": "Out of range",
            "buyer_accessibility": "Unknown",
            "vertical": "Other",
            "wrong_fit_risk": False,
        }
        result = compute_score(classification)
        self.assertEqual(result["score_total"], 10)
        self.assertEqual(result["tier"], "Not-a-fit")

    def test_cold_tier_for_mid_score(self):
        classification = {
            "segment_fit": "Exploratory",
            "ai_adoption": "Moderate",
            "regulatory_exposure": "Implicit",
            "size_fit": "Out of range",
            "buyer_accessibility": "Unknown",
            "vertical": "Other",
            "wrong_fit_risk": False,
        }
        result = compute_score(classification)
        self.assertEqual(result["score_total"], 30)
        self.assertEqual(result["tier"], "Cold")

    def test_unknown_segment_fit_value_raises(self):
        classification = dict(PRIMARY_ICP_STRONG, segment_fit="Nonsense")
        with self.assertRaises(InvalidClassificationError):
            compute_score(classification)

    def test_format_breakdown_produces_compact_string(self):
        breakdown = {"segment_fit": 30, "ai_adoption": 20}
        self.assertEqual(format_breakdown(breakdown), "segment_fit=30;ai_adoption=20")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the tests to verify they fail**

Run (from the `find-leads` directory):
```
cd "F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads"
python -m unittest tests.test_scoring -v
```
Expected: `ImportError: No module named 'scripts.scoring'` (or similar) — `scoring.py` doesn't exist yet.

- [ ] **Step 4: Write the implementation**

Create `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\scripts\scoring.py`:

```python
"""Deterministic scoring/tiering for a researched, classified lead.

Classification (segment_fit, ai_adoption, etc.) is decided by the research
subagent from public signals; this module turns that classification into a
reproducible 0-100 score, a breakdown, and a Hot/Warm/Cold/Not-a-fit tier.
"""

import argparse
import json

SEGMENT_FIT_POINTS = {
    "Primary ICP": 30,
    "Secondary ICP": 20,
    "Exploratory": 10,
    "Poor fit": 0,
}

AI_ADOPTION_POINTS = {
    "Strong": 20,
    "Moderate": 10,
    "Weak/Unknown": 0,
}

REGULATORY_EXPOSURE_POINTS = {
    "Explicit": 20,
    "Implicit": 10,
    "None apparent": 0,
}

SIZE_FIT_POINTS = {
    "In range (50-500)": 15,
    "Extended range (501-1000)": 10,
    "Out of range": 0,
}

BUYER_ACCESSIBILITY_POINTS = {
    "Named": 15,
    "Known but unclear": 7,
    "Unknown": 0,
}

VERTICAL_BONUS = {
    "Finance - crypto-finance": 5,
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

    `classification` must contain: segment_fit, ai_adoption, regulatory_exposure,
    size_fit, buyer_accessibility, vertical, wrong_fit_risk (bool).
    """
    breakdown = {
        "segment_fit": _lookup(SEGMENT_FIT_POINTS, classification["segment_fit"], "segment_fit"),
        "ai_adoption": _lookup(AI_ADOPTION_POINTS, classification["ai_adoption"], "ai_adoption"),
        "regulatory_exposure": _lookup(
            REGULATORY_EXPOSURE_POINTS, classification["regulatory_exposure"], "regulatory_exposure"
        ),
        "size_fit": _lookup(SIZE_FIT_POINTS, classification["size_fit"], "size_fit"),
        "buyer_accessibility": _lookup(
            BUYER_ACCESSIBILITY_POINTS, classification["buyer_accessibility"], "buyer_accessibility"
        ),
        "vertical_bonus": VERTICAL_BONUS.get(classification["vertical"], 0),
    }

    breakdown["wrong_fit_penalty"] = -WRONG_FIT_RISK_PENALTY if classification.get("wrong_fit_risk", False) else 0

    score_total = max(0, min(100, sum(breakdown.values())))

    if classification["segment_fit"] == "Poor fit":
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

- [ ] **Step 5: Run the tests to verify they pass**

Run:
```
python -m unittest tests.test_scoring -v
```
Expected: all 8 tests `OK`.

- [ ] **Step 6: Smoke-test the CLI**

Run:
```
python scripts/scoring.py score --input '{"segment_fit": "Primary ICP", "ai_adoption": "Strong", "regulatory_exposure": "Explicit", "size_fit": "In range (50-500)", "buyer_accessibility": "Named", "vertical": "Healthcare", "wrong_fit_risk": false}'
```
Expected: a single line of JSON containing `"score_total": 100` and `"tier": "Hot"`.

---

### Task 2: CSV store module

**Files:**
- Create: `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\scripts\csv_store.py`
- Test: `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\tests\test_csv_store.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `FIELDNAMES: list[str]`, `load_leads(csv_path: str) -> dict`, `save_leads(csv_path: str, leads: dict) -> None`, `is_fresh(row: dict, today: date, freshness_days: int = 30) -> bool`, `upsert_lead(leads: dict, fields: dict, today: date, freshness_days: int = 30) -> tuple[dict, str]` (action is `"inserted"`, `"updated"`, or `"skipped_fresh"`), `is_active(row: dict) -> bool`.
- CLI: `python scripts/csv_store.py check-fresh --csv <path> --domain <domain> [--freshness-days N]` prints `fresh`/`stale`/`missing`. `python scripts/csv_store.py upsert --csv <path> --input '<json row>' [--freshness-days N]` prints the action.

- [ ] **Step 1: Write the failing tests**

Create `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\tests\test_csv_store.py`:

```python
import os
import shutil
import tempfile
import unittest
from datetime import date

from scripts.csv_store import (
    load_leads, save_leads, upsert_lead, is_active, FIELDNAMES,
)

BASE_FIELDS = {
    "domain": "example.com",
    "company_name": "Example Inc",
    "segment_fit": "Primary ICP",
    "company_stage": "Established/Mid-market",
    "vertical": "Healthcare",
    "ai_adoption": "Strong",
    "regulatory_exposure": "Explicit",
    "size_fit": "In range (50-500)",
    "buyer_name": "Jane Doe",
    "buyer_title": "CTO",
    "buyer_accessibility": "Named",
    "wrong_fit_risk": "False",
    "startup_stigma_routing": "Direct sales viable",
    "score_total": "90",
    "score_breakdown": "segment_fit=30;ai_adoption=20",
    "tier": "Hot",
    "reachability_notes": "Speaking at HealthTech Summit 2026",
    "rationale": "Strong AI adoption, explicit HIPAA exposure",
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
        today = date(2026, 7, 8)
        leads, action = upsert_lead({}, BASE_FIELDS, today)
        self.assertEqual(action, "inserted")
        row = leads["example.com"]
        self.assertEqual(row["first_seen"], "2026-07-08")
        self.assertEqual(row["last_researched"], "2026-07-08")
        self.assertEqual(row["company_name"], "Example Inc")

    def test_upsert_lead_skips_when_existing_row_is_fresh(self):
        today = date(2026, 7, 8)
        leads, _ = upsert_lead({}, BASE_FIELDS, today)
        later = date(2026, 7, 20)
        leads2, action = upsert_lead(leads, BASE_FIELDS, later)
        self.assertEqual(action, "skipped_fresh")
        self.assertEqual(leads2["example.com"]["last_researched"], "2026-07-08")

    def test_upsert_lead_updates_when_existing_row_is_stale(self):
        today = date(2026, 7, 8)
        leads, _ = upsert_lead({}, BASE_FIELDS, today)
        much_later = date(2026, 9, 1)
        updated_fields = dict(BASE_FIELDS, tier="Warm", score_total="60")
        leads2, action = upsert_lead(leads, updated_fields, much_later)
        self.assertEqual(action, "updated")
        self.assertEqual(leads2["example.com"]["last_researched"], "2026-09-01")
        self.assertEqual(leads2["example.com"]["first_seen"], "2026-07-08")
        self.assertEqual(leads2["example.com"]["tier"], "Warm")

    def test_upsert_lead_force_refresh_overrides_freshness(self):
        today = date(2026, 7, 8)
        leads, _ = upsert_lead({}, BASE_FIELDS, today)
        later = date(2026, 7, 20)
        forced_fields = dict(BASE_FIELDS, force_refresh=True, tier="Cold")
        leads2, action = upsert_lead(leads, forced_fields, later)
        self.assertEqual(action, "updated")
        self.assertEqual(leads2["example.com"]["tier"], "Cold")

    def test_save_and_load_roundtrip_preserves_data(self):
        today = date(2026, 7, 8)
        leads, _ = upsert_lead({}, BASE_FIELDS, today)
        save_leads(self.csv_path, leads)
        reloaded = load_leads(self.csv_path)
        self.assertEqual(reloaded["example.com"]["company_name"], "Example Inc")
        self.assertEqual(set(reloaded["example.com"].keys()), set(FIELDNAMES))

    def test_is_active_true_when_status_active(self):
        self.assertTrue(is_active({"status": "active"}))

    def test_is_active_false_when_status_disqualified(self):
        self.assertFalse(is_active({"status": "disqualified"}))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```
cd "F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads"
python -m unittest tests.test_csv_store -v
```
Expected: `ImportError: No module named 'scripts.csv_store'`.

- [ ] **Step 3: Write the implementation**

Create `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\scripts\csv_store.py`:

```python
"""Persistent CSV storage for researched/scored leads.

One row per company, keyed by `domain`. Re-running discover/score-list
updates existing rows in place rather than duplicating them.
"""

import argparse
import csv
import json
import os
from datetime import date, datetime

FIELDNAMES = [
    "domain", "company_name", "segment_fit", "company_stage", "vertical",
    "ai_adoption", "regulatory_exposure", "size_fit", "buyer_name",
    "buyer_title", "buyer_accessibility", "wrong_fit_risk",
    "startup_stigma_routing", "score_total", "score_breakdown", "tier",
    "reachability_notes", "rationale", "sources", "confidence",
    "first_seen", "last_researched", "status", "outcome",
]

DEFAULT_FRESHNESS_DAYS = 30


def load_leads(csv_path: str) -> dict:
    """Load leads.csv into a dict keyed by domain. Returns {} if the file doesn't exist."""
    if not os.path.exists(csv_path):
        return {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["domain"]: row for row in reader}


def save_leads(csv_path: str, leads: dict) -> None:
    """Write the full leads dict back to csv_path, sorted by domain for stable diffs."""
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for domain in sorted(leads):
            writer.writerow(leads[domain])


def is_fresh(row: dict, today: date, freshness_days: int = DEFAULT_FRESHNESS_DAYS) -> bool:
    """True if row's last_researched is within freshness_days of today."""
    last = datetime.strptime(row["last_researched"], "%Y-%m-%d").date()
    return (today - last).days < freshness_days


def upsert_lead(leads: dict, fields: dict, today: date,
                 freshness_days: int = DEFAULT_FRESHNESS_DAYS):
    """Insert or update one lead. Returns (updated_leads, action) where
    action is 'inserted', 'updated', or 'skipped_fresh'.

    `fields` must include `domain` and the FIELDNAMES this row should carry;
    `first_seen` and `last_researched` are managed by this function. Pass
    `force_refresh: True` in `fields` to bypass the freshness check.
    """
    domain = fields["domain"]
    existing = leads.get(domain)

    if existing is not None and is_fresh(existing, today, freshness_days) \
            and not fields.get("force_refresh"):
        return leads, "skipped_fresh"

    row = {name: fields.get(name, "") for name in FIELDNAMES}
    row["domain"] = domain
    row["last_researched"] = today.isoformat()
    row["first_seen"] = existing["first_seen"] if existing else today.isoformat()
    if existing and "status" not in fields:
        row["status"] = existing["status"]
    if existing and "outcome" not in fields:
        row["outcome"] = existing["outcome"]

    new_leads = dict(leads)
    new_leads[domain] = row
    return new_leads, ("updated" if existing else "inserted")


def is_active(row: dict) -> bool:
    return row.get("status", "active") == "active"


def _cli(argv=None):
    parser = argparse.ArgumentParser(description="Lead CSV store")
    sub = parser.add_subparsers(dest="command", required=True)

    check_p = sub.add_parser("check-fresh")
    check_p.add_argument("--csv", required=True)
    check_p.add_argument("--domain", required=True)
    check_p.add_argument("--freshness-days", type=int, default=DEFAULT_FRESHNESS_DAYS)

    upsert_p = sub.add_parser("upsert")
    upsert_p.add_argument("--csv", required=True)
    upsert_p.add_argument("--input", required=True, help="JSON object with lead fields")
    upsert_p.add_argument("--freshness-days", type=int, default=DEFAULT_FRESHNESS_DAYS)

    args = parser.parse_args(argv)
    today = date.today()

    if args.command == "check-fresh":
        leads = load_leads(args.csv)
        row = leads.get(args.domain)
        if row is None:
            print("missing")
        elif is_fresh(row, today, args.freshness_days):
            print("fresh")
        else:
            print("stale")
    elif args.command == "upsert":
        leads = load_leads(args.csv)
        fields = json.loads(args.input)
        leads, action = upsert_lead(leads, fields, today, args.freshness_days)
        save_leads(args.csv, leads)
        print(action)


if __name__ == "__main__":
    _cli()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:
```
python -m unittest tests.test_csv_store -v
```
Expected: all 8 tests `OK`.

- [ ] **Step 5: Smoke-test the CLI**

Run (using a throwaway path):
```
python scripts/csv_store.py check-fresh --csv "F:\_WORKY\blindsight\lead-gen\data\leads.csv" --domain nobody.example
```
Expected: `missing` (file doesn't exist yet — created in Task 5).

---

### Task 3: Segment weight splitter

**Files:**
- Create: `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\scripts\segments.py`
- Test: `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\tests\test_segments.py`

**Interfaces:**
- Consumes: nothing from Tasks 1–2.
- Produces: `SEGMENT_WEIGHTS: dict`, `ALL_SEGMENTS: list[str]`, `UnknownSegmentError(ValueError)`, `split_target(target: int, segments: list | None = None) -> dict[str, int]`.
- CLI: `python scripts/segments.py --target N [--segments a,b,c]` prints the allocation as JSON.

- [ ] **Step 1: Write the failing tests**

Create `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\tests\test_segments.py`:

```python
import unittest

from scripts.segments import split_target, UnknownSegmentError, ALL_SEGMENTS


class SplitTargetTests(unittest.TestCase):
    def test_split_target_default_sweep_sums_to_target(self):
        allocation = split_target(15)
        self.assertEqual(sum(allocation.values()), 15)
        self.assertEqual(set(allocation.keys()), set(ALL_SEGMENTS))

    def test_split_target_weights_high_segments_more_than_low(self):
        allocation = split_target(20)
        self.assertGreater(allocation["healthcare"], allocation["consultancies"])
        self.assertEqual(allocation["healthcare"], allocation["finance"])
        self.assertEqual(allocation["healthcare"], allocation["legal"])
        self.assertEqual(allocation["healthcare"], allocation["ai-native"])

    def test_split_target_with_explicit_segments_splits_evenly(self):
        allocation = split_target(10, segments=["healthcare", "legal"])
        self.assertEqual(allocation, {"healthcare": 5, "legal": 5})

    def test_split_target_unknown_segment_raises(self):
        with self.assertRaises(UnknownSegmentError):
            split_target(10, segments=["not-a-segment"])

    def test_split_target_small_target_still_sums_correctly(self):
        allocation = split_target(3)
        self.assertEqual(sum(allocation.values()), 3)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```
cd "F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads"
python -m unittest tests.test_segments -v
```
Expected: `ImportError: No module named 'scripts.segments'`.

- [ ] **Step 3: Write the implementation**

Create `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\scripts\segments.py`:

```python
"""Segment weighting for discover-mode target-count splitting.

Weights are ~80/20 toward Blindsight's validated ICP segments (healthcare,
finance, legal, AI-native) over its exploratory ones (consultancies,
smart-factories), with the secondary ICP (AI-native startups selling into
regulated verticals) weighted in between.
"""

import argparse
import json

SEGMENT_WEIGHTS = {
    "healthcare": 4,
    "finance": 4,
    "legal": 4,
    "ai-native": 4,
    "ai-native-startups": 2,
    "consultancies": 1,
    "smart-factories": 1,
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

- [ ] **Step 4: Run the tests to verify they pass**

Run:
```
python -m unittest tests.test_segments -v
```
Expected: all 5 tests `OK`.

- [ ] **Step 5: Smoke-test the CLI**

Run:
```
python scripts/segments.py --target 15
```
Expected: a JSON object with 7 keys (`healthcare`, `finance`, `legal`, `ai-native`, `ai-native-startups`, `consultancies`, `smart-factories`) whose values sum to 15.

---

### Task 4: Report generator

**Files:**
- Create: `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\scripts\report.py`
- Test: `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\tests\test_report.py`

**Interfaces:**
- Consumes: nothing from Tasks 1–3 (result/skipped rows are plain dicts constructed by the SKILL.md workflow; `score_total`/`tier`/`rationale` keys match what `scoring.py`'s output supplies).
- Produces: `generate_run_report(mode: str, segment, run_date: date, results: list, skipped: list) -> str`.
- CLI: `python scripts/report.py --mode M --segment S --date YYYY-MM-DD --results '<json list>' --skipped '<json list>' --out <path>` writes the report to `<path>` and prints `wrote <path>`.

- [ ] **Step 1: Write the failing tests**

Create `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\tests\test_report.py`:

```python
import unittest
from datetime import date

from scripts.report import generate_run_report

RESULT_A = {
    "company_name": "Acme Health",
    "domain": "acmehealth.com",
    "score_total": 90,
    "tier": "Hot",
    "rationale": "Strong AI adoption, explicit HIPAA exposure",
    "wrong_fit_risk": False,
    "startup_stigma_routing": "Direct sales viable",
}

RESULT_B = {
    "company_name": "Beta Legal",
    "domain": "betalegal.com",
    "score_total": 60,
    "tier": "Warm",
    "rationale": "Regulated vertical, moderate AI signal",
    "wrong_fit_risk": True,
    "startup_stigma_routing": "Route via channel partner",
}


class GenerateRunReportTests(unittest.TestCase):
    def test_report_includes_header_with_mode_segment_and_date(self):
        report = generate_run_report("discover", "healthcare", date(2026, 7, 8), [], [])
        self.assertIn("discover", report)
        self.assertIn("healthcare", report)
        self.assertIn("2026-07-08", report)

    def test_report_lists_top_5_sorted_by_score_descending(self):
        report = generate_run_report("discover", None, date(2026, 7, 8), [RESULT_B, RESULT_A], [])
        self.assertLess(report.index("Acme Health"), report.index("Beta Legal"))

    def test_report_flags_wrong_fit_risk_and_routing(self):
        report = generate_run_report("discover", None, date(2026, 7, 8), [RESULT_A, RESULT_B], [])
        flags_section = report.split("## Flags needing attention")[1]
        self.assertIn("Beta Legal", flags_section)
        self.assertIn("wrong-fit risk", flags_section)
        self.assertIn("Route via channel partner", flags_section)

    def test_report_does_not_flag_clean_results(self):
        report = generate_run_report("discover", None, date(2026, 7, 8), [RESULT_A], [])
        self.assertNotIn("Flags needing attention", report)

    def test_report_lists_skipped_with_reasons(self):
        skipped = [{"company_name": "Gamma Corp", "reason": "already fresh in CSV"}]
        report = generate_run_report("discover", None, date(2026, 7, 8), [], skipped)
        self.assertIn("Gamma Corp", report)
        self.assertIn("already fresh in CSV", report)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```
cd "F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads"
python -m unittest tests.test_report -v
```
Expected: `ImportError: No module named 'scripts.report'`.

- [ ] **Step 3: Write the implementation**

Create `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\scripts\report.py`:

```python
"""Markdown run-report generation for a discover/score-list run."""

import argparse
import json
import os
from datetime import date as date_cls


def generate_run_report(mode: str, segment, run_date, results: list, skipped: list) -> str:
    """Build the markdown report for one run.

    `results`: list of dicts with at least company_name, domain, score_total,
      tier, rationale, wrong_fit_risk (bool), startup_stigma_routing.
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

    flagged = [
        r for r in results
        if r.get("wrong_fit_risk") or r.get("startup_stigma_routing") not in (None, "", "Direct sales viable")
    ]
    if flagged:
        lines.append("## Flags needing attention")
        for r in flagged:
            flag_bits = []
            if r.get("wrong_fit_risk"):
                flag_bits.append("wrong-fit risk")
            routing = r.get("startup_stigma_routing")
            if routing and routing != "Direct sales viable":
                flag_bits.append(routing)
            lines.append(f"- **{r['company_name']}** — {', '.join(flag_bits)}")
        lines.append("")

    if skipped:
        lines.append("## Skipped")
        for s in skipped:
            lines.append(f"- {s['company_name']} — {s['reason']}")
        lines.append("")

    return "\n".join(lines)


def _cli(argv=None):
    parser = argparse.ArgumentParser(description="Generate a lead run markdown report")
    parser.add_argument("--mode", required=True)
    parser.add_argument("--segment", default=None)
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--results", required=True, help="JSON list of result dicts")
    parser.add_argument("--skipped", default="[]", help="JSON list of skipped dicts")
    parser.add_argument("--out", required=True, help="output markdown file path")
    args = parser.parse_args(argv)

    run_date = date_cls.fromisoformat(args.date)
    results = json.loads(args.results)
    skipped = json.loads(args.skipped)
    report = generate_run_report(args.mode, args.segment, run_date, results, skipped)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    _cli()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:
```
python -m unittest tests.test_report -v
```
Expected: all 5 tests `OK`.

---

### Task 5: SKILL.md, seed data, and end-to-end verification

**Files:**
- Create: `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\SKILL.md`
- Create: `F:\_WORKY\blindsight\lead-gen\data\leads.csv` (header row only)
- Create: `F:\_WORKY\blindsight\lead-gen\runs\` (directory)

**Interfaces:**
- Consumes: `scripts/scoring.py` (`score` CLI command), `scripts/csv_store.py` (`check-fresh`, `upsert` CLI commands), `scripts/segments.py` (CLI), `scripts/report.py` (CLI) — all from Tasks 1–4.
- Produces: nothing consumed by other tasks (this is the last task).

- [ ] **Step 1: Seed the output locations**

Run:
```
mkdir -p "F:\_WORKY\blindsight\lead-gen\runs"
```

Create `F:\_WORKY\blindsight\lead-gen\data\leads.csv` with only the header row:
```
domain,company_name,segment_fit,company_stage,vertical,ai_adoption,regulatory_exposure,size_fit,buyer_name,buyer_title,buyer_accessibility,wrong_fit_risk,startup_stigma_routing,score_total,score_breakdown,tier,reachability_notes,rationale,sources,confidence,first_seen,last_researched,status,outcome
```

- [ ] **Step 2: Write SKILL.md**

Create `F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads\SKILL.md`:

```markdown
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
```

- [ ] **Step 3: Verify the scoring → persistence → report pipeline end to end**

Run (from the `find-leads` directory):
```
cd "F:\_WORKY\blindsight\lead-gen\.claude\skills\find-leads"
python scripts/scoring.py score --input '{"segment_fit": "Primary ICP", "ai_adoption": "Strong", "regulatory_exposure": "Explicit", "size_fit": "In range (50-500)", "buyer_accessibility": "Named", "vertical": "Healthcare", "wrong_fit_risk": false}'
```
Expected: JSON with `"score_total": 100`, `"tier": "Hot"`.

```
python scripts/csv_store.py upsert --csv "F:\_WORKY\blindsight\lead-gen\data\leads.csv" --input '{"domain": "testcorp.com", "company_name": "TestCorp", "segment_fit": "Primary ICP", "company_stage": "Established/Mid-market", "vertical": "Healthcare", "ai_adoption": "Strong", "regulatory_exposure": "Explicit", "size_fit": "In range (50-500)", "buyer_name": "Jane Doe", "buyer_title": "CTO", "buyer_accessibility": "Named", "wrong_fit_risk": "False", "startup_stigma_routing": "Direct sales viable", "score_total": "100", "score_breakdown": "segment_fit=30;ai_adoption=20;regulatory_exposure=20;size_fit=15;buyer_accessibility=15;vertical_bonus=0;wrong_fit_penalty=0", "tier": "Hot", "reachability_notes": "Speaking at HealthTech Summit 2026", "rationale": "Strong AI adoption, explicit HIPAA exposure", "sources": "https://testcorp.com/about", "confidence": "medium", "status": "active", "outcome": ""}'
```
Expected: `inserted`.

```
cat "F:\_WORKY\blindsight\lead-gen\data\leads.csv"
```
Expected: header row plus one `testcorp.com` row with `tier` = `Hot`.

```
python scripts/report.py --mode discover --segment healthcare --date 2026-07-08 --results '[{"company_name": "TestCorp", "domain": "testcorp.com", "score_total": 100, "tier": "Hot", "rationale": "Strong AI adoption, explicit HIPAA exposure", "wrong_fit_risk": false, "startup_stigma_routing": "Direct sales viable"}]' --skipped '[]' --out "F:\_WORKY\blindsight\lead-gen\runs\2026-07-08-discover-healthcare.md"
```
Expected: `wrote F:\_WORKY\blindsight\lead-gen\runs\2026-07-08-discover-healthcare.md`.

```
cat "F:\_WORKY\blindsight\lead-gen\runs\2026-07-08-discover-healthcare.md"
```
Expected: a markdown report containing `TestCorp`, `100/100`, `Hot`.

- [ ] **Step 4: Remove the smoke-test row before real use**

The `testcorp.com` row and the `2026-07-08-discover-healthcare.md` report from Step 3 are test fixtures, not real leads. Remove the `testcorp.com` row from `data\leads.csv` (leaving just the header) and delete the test report file, so the first real run starts clean.

---

## Post-implementation validation (not a build task — do this after Task 5, using the live skill)

The spec's Validation Approach requires actually invoking `/find-leads` with real web search, which only exists once the skill is loaded into a live Claude Code session — it can't be scripted as a build-time step. Once Task 5 is complete, run these manually before trusting the skill for real outreach decisions:

1. **Known-answer test** — `score-list` against a company you already know well (e.g. a current customer like Clínic Barcelona, or an obvious non-fit like a local retail shop) and confirm the score/tier/classification matches intuition.
2. **Discover smoke test** — `discover healthcare --target 5` and manually check a few results are real, plausible companies (not hallucinated).
3. **Edge-case check** — `score-list` with a typo'd company name and a dead/nonexistent domain, confirm both come back as "Could not resolve" in the report rather than producing garbage CSV rows.
