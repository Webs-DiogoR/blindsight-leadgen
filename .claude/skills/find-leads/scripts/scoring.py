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
