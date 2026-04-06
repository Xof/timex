"""Harvest time report functions."""

import os
import time
from collections import defaultdict
from datetime import date
from typing import Optional

import requests

BASE_URL = "https://api.harvestapp.com"


def _harvest_get(endpoint: str, params: Optional[dict] = None) -> list[dict]:
    """Fetch all records from a paginated Harvest API endpoint."""
    token = os.environ.get("HARVEST_ACCESS_TOKEN")
    account_id = os.environ.get("HARVEST_ACCOUNT_ID")
    if not token or not account_id:
        raise ValueError(
            "HARVEST_ACCESS_TOKEN and HARVEST_ACCOUNT_ID environment variables are required"
        )

    headers = {
        "Authorization": f"Bearer {token}",
        "Harvest-Account-Id": account_id,
        "User-Agent": "timex (harvest-reports)",
    }

    url = f"{BASE_URL}{endpoint}"
    all_records = []

    while url:
        resp = requests.get(url, headers=headers, params=params)

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 15))
            time.sleep(retry_after)
            continue

        if not resp.ok:
            raise requests.HTTPError(
                f"HTTP {resp.status_code}: {resp.text}", response=resp
            )

        data = resp.json()

        # The response key is the last segment of the endpoint path
        # e.g. /v2/time_entries -> "time_entries"
        resource_key = endpoint.rstrip("/").split("/")[-1]
        all_records.extend(data.get(resource_key, []))

        url = data.get("links", {}).get("next")
        params = None  # params are baked into the next URL

    return all_records


def detailed_time_by_staff_client(start_date: date, end_date: date) -> dict:
    """Detailed time report grouped by staff member, then client, with daily task totals."""
    entries = _harvest_get(
        "/v2/time_entries",
        {"from": start_date.isoformat(), "to": end_date.isoformat()},
    )

    # Accumulate hours: (user, client, date, task) -> hours
    totals = defaultdict(float)
    for entry in entries:
        key = (
            entry["user"]["name"],
            entry["client"]["name"],
            entry["spent_date"],
            entry["task"]["name"],
        )
        totals[key] += entry["hours"]

    # Build nested structure
    result: dict[str, dict[str, list]] = {}
    for (user, client, spent_date, task), hours in sorted(totals.items()):
        result.setdefault(user, {}).setdefault(client, []).append(
            {"date": spent_date, "task": task, "hours": round(hours, 2)}
        )

    return result


def hours_summary_by_staff_day(start_date: date, end_date: date) -> dict:
    """Hours summary grouped by staff member, then date, with per-task breakdown and daily total."""
    entries = _harvest_get(
        "/v2/time_entries",
        {"from": start_date.isoformat(), "to": end_date.isoformat()},
    )

    # Accumulate hours: (user, date, task) -> hours
    totals = defaultdict(float)
    for entry in entries:
        key = (
            entry["user"]["name"],
            entry["spent_date"],
            entry["task"]["name"],
        )
        totals[key] += entry["hours"]

    # Build nested structure
    result: dict[str, dict[str, dict]] = {}
    for (user, spent_date, task), hours in sorted(totals.items()):
        day_data = result.setdefault(user, {}).setdefault(
            spent_date, {"tasks": {}, "total": 0.0}
        )
        rounded = round(hours, 2)
        day_data["tasks"][task] = rounded
        day_data["total"] = round(day_data["total"] + rounded, 2)

    return result
