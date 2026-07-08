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
