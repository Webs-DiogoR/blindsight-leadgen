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
