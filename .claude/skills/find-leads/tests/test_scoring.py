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
