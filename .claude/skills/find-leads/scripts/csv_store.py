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
    "domain", "company_name", "icp_match", "vertical", "persona_match",
    "company_stage", "ai_native_maturity", "regulatory_data_exposure",
    "agent_deployment_stage", "geo_fit", "size_fit", "buyer_name",
    "buyer_title", "buyer_accessibility", "wrong_fit_risk",
    "score_total", "score_breakdown", "tier", "reachability_notes",
    "rationale", "sources", "confidence", "first_seen", "last_researched",
    "status", "outcome",
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


def check_fresh_status(row: dict | None, today: date,
                        freshness_days: int = DEFAULT_FRESHNESS_DAYS) -> str:
    """Returns 'missing' | 'disqualified' | 'customer' | 'fresh' | 'stale' for a candidate domain.

    disqualified/customer wins over freshness so a candidate discover would
    otherwise resurface (once its freshness window lapses) stays excluded.
    """
    if row is None:
        return "missing"
    if row.get("status") in ("disqualified", "customer"):
        return row["status"]
    return "fresh" if is_fresh(row, today, freshness_days) else "stale"


def is_active(row: dict) -> bool:
    return row.get("status", "active") == "active"


def is_watchlist(row: dict) -> bool:
    return row.get("status") == "watchlist"


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
        print(check_fresh_status(leads.get(args.domain), today, args.freshness_days))
    elif args.command == "upsert":
        leads = load_leads(args.csv)
        fields = json.loads(args.input)
        leads, action = upsert_lead(leads, fields, today, args.freshness_days)
        save_leads(args.csv, leads)
        print(action)


if __name__ == "__main__":
    _cli()
