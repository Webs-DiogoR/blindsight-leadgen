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
