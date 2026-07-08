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
