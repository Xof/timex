"""Invoice rendering pipeline: Harvest data + rate card → PDF."""

import json
from typing import Optional


def load_rate_card(path: str) -> dict:
    """Load a rate card JSON file."""
    with open(path) as f:
        return json.load(f)


def lookup_rate(rate_card: dict, staff: str, task: str) -> float:
    """Look up the hourly rate for a staff/task combination.

    Falls back to default_rate if set; raises ValueError otherwise.
    """
    rates = rate_card.get("rates", {})
    if staff in rates and task in rates[staff]:
        return rates[staff][task]
    default = rate_card.get("default_rate")
    if default is not None:
        return default
    raise ValueError(
        f"No rate for staff={staff!r}, task={task!r} and no default_rate set"
    )


def _format_date_mmddyy(iso_date: str) -> str:
    """Convert '2026-04-01' to '04/01/26'."""
    year, month, day = iso_date.split("-")
    return f"{month}/{day}/{year[2:]}"


def build_line_items(harvest_data: dict, rate_card: dict) -> tuple:
    """Build sorted, priced line items from Harvest report data and a rate card.

    Returns (line_items, total).
    """
    raw_items = []
    for staff, clients in harvest_data.items():
        for _client, entries in clients.items():
            for entry in entries:
                rate = lookup_rate(rate_card, staff, entry["task"])
                amount = round(entry["hours"] * rate, 2)
                raw_items.append({
                    "sort_date": entry["date"],
                    "date": _format_date_mmddyy(entry["date"]),
                    "staff": staff,
                    "task": entry["task"],
                    "hours": entry["hours"],
                    "rate": rate,
                    "amount": amount,
                })

    raw_items.sort(key=lambda x: (x["sort_date"], x["staff"]))

    # Strip the sort key
    line_items = [{k: v for k, v in item.items() if k != "sort_date"} for item in raw_items]
    total = round(sum(item["amount"] for item in line_items), 2) if line_items else 0.0
    return line_items, total
