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
