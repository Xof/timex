"""Harvest time report functions."""

import os
import time
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

        resp.raise_for_status()
        data = resp.json()

        # The response key is the last segment of the endpoint path
        # e.g. /v2/time_entries -> "time_entries"
        resource_key = endpoint.rstrip("/").split("/")[-1]
        all_records.extend(data.get(resource_key, []))

        url = data.get("links", {}).get("next")
        params = None  # params are baked into the next URL

    return all_records
