"""Shared utilities for Harvest export scripts."""

import calendar
import json
import os
from datetime import date


def load_env(script_dir: str) -> None:
    """Load .env file from script_dir into os.environ if present.

    Existing env vars take precedence over .env values.
    After loading, verifies HARVEST_ACCESS_TOKEN and HARVEST_ACCOUNT_ID are set.
    """
    env_path = os.path.join(script_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                if key and key not in os.environ:
                    os.environ[key] = value

    missing = []
    for var in ("HARVEST_ACCESS_TOKEN", "HARVEST_ACCOUNT_ID"):
        if not os.environ.get(var):
            missing.append(var)
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Set them in .env or as environment variables."
        )


def previous_semimonth(today: date) -> tuple:
    """Return (start, end) of the previous semimonth period.

    If today is in the 1st-15th: returns (prev month 16th, prev month last day).
    If today is in the 16th-end: returns (this month 1st, this month 15th).
    """
    if today.day <= 15:
        if today.month == 1:
            prev_year, prev_month = today.year - 1, 12
        else:
            prev_year, prev_month = today.year, today.month - 1
        last_day = calendar.monthrange(prev_year, prev_month)[1]
        return date(prev_year, prev_month, 16), date(prev_year, prev_month, last_day)
    else:
        return date(today.year, today.month, 1), date(today.year, today.month, 15)


def output_dir(start_date: date, end_date: date) -> str:
    """Return output directory path for a date range, creating it if needed."""
    dirname = f"output/{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}/"
    os.makedirs(dirname, exist_ok=True)
    return dirname


def load_type_mappings(path: str) -> dict:
    """Load type-mappings.json and return a flat {harvest_task: summary_type} dict."""
    with open(path) as f:
        mapping_list = json.load(f)
    result = {}
    for item in mapping_list:
        for key, value in item.items():
            result[key] = value
    return result


def map_task_type(task: str, mappings: dict) -> str:
    """Map a Harvest task name to its summary type. Unmapped tasks pass through."""
    return mappings.get(task, task)
