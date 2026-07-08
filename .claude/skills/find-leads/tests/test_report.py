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
