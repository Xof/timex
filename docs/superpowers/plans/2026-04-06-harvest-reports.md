# Harvest Reports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python module that fetches time entries from the Harvest API and returns two structured reports (detailed time by staff/client, and hours summary by staff/day/task).

**Architecture:** Single module `harvest_reports.py` with a private API helper and two public report functions. Tests mock the HTTP layer using `unittest.mock.patch` on `requests.get`. No classes — just functions.

**Tech Stack:** Python 3.x, `requests`, `pytest`

---

## File Structure

| File | Responsibility |
|---|---|
| `harvest_reports.py` | API helper + two public report functions |
| `tests/test_harvest_reports.py` | All tests |
| `requirements.txt` | Dependencies (`requests`, `pytest`) |

---

### Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
requests>=2.28
pytest>=7.0
```

- [ ] **Step 2: Create empty test package**

Create `tests/__init__.py` as an empty file.

- [ ] **Step 3: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: Successfully installed requests and pytest

- [ ] **Step 4: Commit**

```bash
git init
git add requirements.txt tests/__init__.py
git commit -m "chore: project setup with requirements"
```

---

### Task 2: API Helper — `_harvest_get`

**Files:**
- Create: `harvest_reports.py`
- Create: `tests/test_harvest_reports.py`

- [ ] **Step 1: Write failing test for single-page fetch**

In `tests/test_harvest_reports.py`:

```python
import os
from datetime import date
from unittest.mock import patch, MagicMock

from harvest_reports import _harvest_get


def _mock_response(json_data, status_code=200, headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400 and status_code != 429:
        from requests.exceptions import HTTPError
        resp.raise_for_status.side_effect = HTTPError(response=resp)
    return resp


class TestHarvestGet:
    @patch.dict(os.environ, {"HARVEST_ACCESS_TOKEN": "tok", "HARVEST_ACCOUNT_ID": "123"})
    @patch("harvest_reports.requests.get")
    def test_single_page(self, mock_get):
        mock_get.return_value = _mock_response({
            "time_entries": [
                {"id": 1, "hours": 2.0},
                {"id": 2, "hours": 3.0},
            ],
            "links": {"next": None},
        })

        result = _harvest_get("/v2/time_entries", {"from": "2026-04-01", "to": "2026-04-30"})

        assert result == [{"id": 1, "hours": 2.0}, {"id": 2, "hours": 3.0}]
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == "https://api.harvestapp.com/v2/time_entries"
        assert kwargs["headers"]["Authorization"] == "Bearer tok"
        assert kwargs["headers"]["Harvest-Account-Id"] == "123"
        assert "User-Agent" in kwargs["headers"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_harvest_reports.py::TestHarvestGet::test_single_page -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Write minimal implementation**

In `harvest_reports.py`:

```python
"""Harvest time report functions."""

import os
import time
from datetime import date

import requests

BASE_URL = "https://api.harvestapp.com"


def _harvest_get(endpoint: str, params: dict | None = None) -> list[dict]:
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_harvest_reports.py::TestHarvestGet::test_single_page -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add harvest_reports.py tests/test_harvest_reports.py
git commit -m "feat: add Harvest API helper with pagination"
```

---

### Task 3: API Helper — Pagination and Rate Limiting Tests

**Files:**
- Modify: `tests/test_harvest_reports.py`

- [ ] **Step 1: Write failing test for multi-page pagination**

Append to `TestHarvestGet` in `tests/test_harvest_reports.py`:

```python
    @patch.dict(os.environ, {"HARVEST_ACCESS_TOKEN": "tok", "HARVEST_ACCOUNT_ID": "123"})
    @patch("harvest_reports.requests.get")
    def test_pagination(self, mock_get):
        page1 = _mock_response({
            "time_entries": [{"id": 1}],
            "links": {"next": "https://api.harvestapp.com/v2/time_entries?cursor=abc"},
        })
        page2 = _mock_response({
            "time_entries": [{"id": 2}],
            "links": {"next": None},
        })
        mock_get.side_effect = [page1, page2]

        result = _harvest_get("/v2/time_entries", {"from": "2026-04-01", "to": "2026-04-30"})

        assert result == [{"id": 1}, {"id": 2}]
        assert mock_get.call_count == 2
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/test_harvest_reports.py::TestHarvestGet::test_pagination -v`
Expected: PASS (implementation already handles pagination)

- [ ] **Step 3: Write failing test for rate limiting**

Append to `TestHarvestGet` in `tests/test_harvest_reports.py`:

```python
    @patch.dict(os.environ, {"HARVEST_ACCESS_TOKEN": "tok", "HARVEST_ACCOUNT_ID": "123"})
    @patch("harvest_reports.time.sleep")
    @patch("harvest_reports.requests.get")
    def test_rate_limit_retry(self, mock_get, mock_sleep):
        rate_limited = _mock_response({}, status_code=429, headers={"Retry-After": "5"})
        success = _mock_response({
            "time_entries": [{"id": 1}],
            "links": {"next": None},
        })
        mock_get.side_effect = [rate_limited, success]

        result = _harvest_get("/v2/time_entries", {})

        assert result == [{"id": 1}]
        mock_sleep.assert_called_once_with(5)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_harvest_reports.py::TestHarvestGet::test_rate_limit_retry -v`
Expected: PASS (implementation already handles 429)

- [ ] **Step 5: Write failing test for missing env vars**

Append to `TestHarvestGet` in `tests/test_harvest_reports.py`:

```python
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_env_vars(self):
        import pytest as pt
        with pt.raises(ValueError, match="HARVEST_ACCESS_TOKEN"):
            _harvest_get("/v2/time_entries", {})
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_harvest_reports.py::TestHarvestGet::test_missing_env_vars -v`
Expected: PASS

- [ ] **Step 7: Run all tests**

Run: `pytest tests/ -v`
Expected: All 4 tests PASS

- [ ] **Step 8: Commit**

```bash
git add tests/test_harvest_reports.py
git commit -m "test: add pagination, rate limiting, and env var tests"
```

---

### Task 4: Report 1 — `detailed_time_by_staff_client`

**Files:**
- Modify: `harvest_reports.py`
- Modify: `tests/test_harvest_reports.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_harvest_reports.py`:

```python
from harvest_reports import detailed_time_by_staff_client


class TestDetailedTimeByStaffClient:
    @patch("harvest_reports._harvest_get")
    def test_groups_and_sums(self, mock_get):
        mock_get.return_value = [
            {
                "spent_date": "2026-04-01",
                "hours": 2.0,
                "user": {"id": 1, "name": "Alice"},
                "client": {"id": 10, "name": "Acme"},
                "task": {"id": 100, "name": "Development"},
            },
            {
                "spent_date": "2026-04-01",
                "hours": 1.5,
                "user": {"id": 1, "name": "Alice"},
                "client": {"id": 10, "name": "Acme"},
                "task": {"id": 100, "name": "Development"},
            },
            {
                "spent_date": "2026-04-01",
                "hours": 1.0,
                "user": {"id": 1, "name": "Alice"},
                "client": {"id": 10, "name": "Acme"},
                "task": {"id": 101, "name": "Meetings"},
            },
            {
                "spent_date": "2026-04-02",
                "hours": 4.0,
                "user": {"id": 2, "name": "Bob"},
                "client": {"id": 11, "name": "Globex"},
                "task": {"id": 100, "name": "Development"},
            },
        ]

        result = detailed_time_by_staff_client(date(2026, 4, 1), date(2026, 4, 30))

        assert result == {
            "Alice": {
                "Acme": [
                    {"date": "2026-04-01", "task": "Development", "hours": 3.5},
                    {"date": "2026-04-01", "task": "Meetings", "hours": 1.0},
                ],
            },
            "Bob": {
                "Globex": [
                    {"date": "2026-04-02", "task": "Development", "hours": 4.0},
                ],
            },
        }
        mock_get.assert_called_once_with(
            "/v2/time_entries", {"from": "2026-04-01", "to": "2026-04-30"}
        )

    @patch("harvest_reports._harvest_get")
    def test_empty(self, mock_get):
        mock_get.return_value = []
        result = detailed_time_by_staff_client(date(2026, 4, 1), date(2026, 4, 30))
        assert result == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_harvest_reports.py::TestDetailedTimeByStaffClient -v`
Expected: FAIL with `ImportError` (function not defined yet)

- [ ] **Step 3: Write implementation**

Append to `harvest_reports.py`:

```python
from collections import defaultdict


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
    for (user, client, spent_date, task), hours in sorted(totals):
        result.setdefault(user, {}).setdefault(client, []).append(
            {"date": spent_date, "task": task, "hours": round(hours, 2)}
        )

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_harvest_reports.py::TestDetailedTimeByStaffClient -v`
Expected: Both tests PASS

- [ ] **Step 5: Commit**

```bash
git add harvest_reports.py tests/test_harvest_reports.py
git commit -m "feat: add detailed_time_by_staff_client report"
```

---

### Task 5: Report 2 — `hours_summary_by_staff_day`

**Files:**
- Modify: `harvest_reports.py`
- Modify: `tests/test_harvest_reports.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_harvest_reports.py`:

```python
from harvest_reports import hours_summary_by_staff_day


class TestHoursSummaryByStaffDay:
    @patch("harvest_reports._harvest_get")
    def test_groups_sums_and_totals(self, mock_get):
        mock_get.return_value = [
            {
                "spent_date": "2026-04-01",
                "hours": 2.0,
                "user": {"id": 1, "name": "Alice"},
                "client": {"id": 10, "name": "Acme"},
                "task": {"id": 100, "name": "Development"},
            },
            {
                "spent_date": "2026-04-01",
                "hours": 1.5,
                "user": {"id": 1, "name": "Alice"},
                "client": {"id": 10, "name": "Acme"},
                "task": {"id": 100, "name": "Development"},
            },
            {
                "spent_date": "2026-04-01",
                "hours": 1.0,
                "user": {"id": 1, "name": "Alice"},
                "client": {"id": 10, "name": "Acme"},
                "task": {"id": 101, "name": "Meetings"},
            },
            {
                "spent_date": "2026-04-02",
                "hours": 7.0,
                "user": {"id": 1, "name": "Alice"},
                "client": {"id": 11, "name": "Globex"},
                "task": {"id": 100, "name": "Development"},
            },
        ]

        result = hours_summary_by_staff_day(date(2026, 4, 1), date(2026, 4, 30))

        assert result == {
            "Alice": {
                "2026-04-01": {
                    "tasks": {"Development": 3.5, "Meetings": 1.0},
                    "total": 4.5,
                },
                "2026-04-02": {
                    "tasks": {"Development": 7.0},
                    "total": 7.0,
                },
            },
        }

    @patch("harvest_reports._harvest_get")
    def test_empty(self, mock_get):
        mock_get.return_value = []
        result = hours_summary_by_staff_day(date(2026, 4, 1), date(2026, 4, 30))
        assert result == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_harvest_reports.py::TestHoursSummaryByStaffDay -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write implementation**

Append to `harvest_reports.py`:

```python
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
    for (user, spent_date, task), hours in sorted(totals):
        day_data = result.setdefault(user, {}).setdefault(
            spent_date, {"tasks": {}, "total": 0.0}
        )
        rounded = round(hours, 2)
        day_data["tasks"][task] = rounded
        day_data["total"] = round(day_data["total"] + rounded, 2)

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_harvest_reports.py::TestHoursSummaryByStaffDay -v`
Expected: Both tests PASS

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS (8 total)

- [ ] **Step 6: Commit**

```bash
git add harvest_reports.py tests/test_harvest_reports.py
git commit -m "feat: add hours_summary_by_staff_day report"
```
