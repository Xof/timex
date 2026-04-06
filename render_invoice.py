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
