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
