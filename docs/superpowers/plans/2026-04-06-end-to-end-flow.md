# Harvest Export End-to-End Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build three CLI scripts (downloader, invoice generator, time summary) that share config files, date utilities, and output directory conventions for a complete Harvest time-tracking export pipeline.

**Architecture:** Three standalone scripts sharing a `utils.py` module (env loading, semimonth dates, output dirs, type mappings). The existing `render_invoice.py` keeps its pure functions but gets its CLI removed and type-mapping support added. Config files (`client-info.json`, `type-mappings.json`, updated `rate_card.json`) provide runtime parameters.

**Tech Stack:** Python 3.9+, requests, Jinja2, WeasyPrint, pytest

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `utils.py` | Create | `load_env()`, `previous_semimonth()`, `output_dir()`, `load_type_mappings()`, `map_task_type()` |
| `tests/test_utils.py` | Create | Tests for all utils functions |
| `render_invoice.py` | Modify | Remove `main()`/argparse, add `type_mappings` param to `build_line_items` |
| `tests/test_render_invoice.py` | Modify | Update `build_line_items` tests for type mappings |
| `rate_card.json` | Modify | Re-key from Harvest task names to mapped summary types |
| `client-info.json` | Create | Example client address config |
| `type-mappings.json` | Create | Example Harvest task → summary type config |
| `download_harvest.py` | Create | Downloader CLI script |
| `generate_invoice.py` | Create | Invoice generator CLI script |
| `tests/test_generate_invoice.py` | Create | Invoice generator tests |
| `generate_summary.py` | Create | Time summary CLI script |
| `tests/test_generate_summary.py` | Create | Time summary tests |

---

### Task 1: `load_env()` in `utils.py` (TDD)

**Files:**
- Create: `utils.py`
- Create: `tests/test_utils.py`

- [ ] **Step 1: Write failing tests for load_env**

Create `tests/test_utils.py`:

```python
import os
import pytest
from unittest.mock import patch

from utils import load_env


class TestLoadEnv:
    def test_loads_from_dotenv_file(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("HARVEST_ACCESS_TOKEN=tok123\nHARVEST_ACCOUNT_ID=acc456\n")
        monkeypatch.delenv("HARVEST_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("HARVEST_ACCOUNT_ID", raising=False)

        load_env(str(tmp_path))

        assert os.environ["HARVEST_ACCESS_TOKEN"] == "tok123"
        assert os.environ["HARVEST_ACCOUNT_ID"] == "acc456"

    def test_env_vars_take_precedence_over_dotenv(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("HARVEST_ACCESS_TOKEN=fromfile\nHARVEST_ACCOUNT_ID=fromfile\n")
        monkeypatch.setenv("HARVEST_ACCESS_TOKEN", "fromenv")
        monkeypatch.setenv("HARVEST_ACCOUNT_ID", "fromenv")

        load_env(str(tmp_path))

        assert os.environ["HARVEST_ACCESS_TOKEN"] == "fromenv"
        assert os.environ["HARVEST_ACCOUNT_ID"] == "fromenv"

    def test_ignores_comments_and_blank_lines(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\n\nHARVEST_ACCESS_TOKEN=tok\n\nHARVEST_ACCOUNT_ID=acc\n")
        monkeypatch.delenv("HARVEST_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("HARVEST_ACCOUNT_ID", raising=False)

        load_env(str(tmp_path))

        assert os.environ["HARVEST_ACCESS_TOKEN"] == "tok"
        assert os.environ["HARVEST_ACCOUNT_ID"] == "acc"

    def test_no_dotenv_uses_existing_env_vars(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HARVEST_ACCESS_TOKEN", "tok")
        monkeypatch.setenv("HARVEST_ACCOUNT_ID", "acc")

        load_env(str(tmp_path))  # no .env file in tmp_path

        assert os.environ["HARVEST_ACCESS_TOKEN"] == "tok"
        assert os.environ["HARVEST_ACCOUNT_ID"] == "acc"

    def test_missing_token_raises(self, tmp_path, monkeypatch):
        monkeypatch.delenv("HARVEST_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("HARVEST_ACCOUNT_ID", raising=False)

        with pytest.raises(ValueError, match="HARVEST_ACCESS_TOKEN"):
            load_env(str(tmp_path))

    def test_missing_account_id_raises(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HARVEST_ACCESS_TOKEN", "tok")
        monkeypatch.delenv("HARVEST_ACCOUNT_ID", raising=False)

        with pytest.raises(ValueError, match="HARVEST_ACCOUNT_ID"):
            load_env(str(tmp_path))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_utils.py -v`
Expected: ImportError — `utils` does not exist yet.

- [ ] **Step 3: Implement load_env**

Create `utils.py`:

```python
"""Shared utilities for Harvest export scripts."""

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_utils.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add utils.py tests/test_utils.py
git commit -m "feat: add load_env utility for .env file loading"
```

---

### Task 2: `previous_semimonth()` (TDD)

**Files:**
- Modify: `utils.py`
- Modify: `tests/test_utils.py`

- [ ] **Step 1: Write failing tests for previous_semimonth**

Append to `tests/test_utils.py`:

```python
from datetime import date

from utils import previous_semimonth


class TestPreviousSemimonth:
    def test_day_in_first_half_returns_prev_month_second_half(self):
        # April 6 -> March 16-31
        start, end = previous_semimonth(date(2026, 4, 6))
        assert start == date(2026, 3, 16)
        assert end == date(2026, 3, 31)

    def test_day_on_15th_returns_prev_month_second_half(self):
        # April 15 -> March 16-31
        start, end = previous_semimonth(date(2026, 4, 15))
        assert start == date(2026, 3, 16)
        assert end == date(2026, 3, 31)

    def test_day_on_16th_returns_same_month_first_half(self):
        # April 16 -> April 1-15
        start, end = previous_semimonth(date(2026, 4, 16))
        assert start == date(2026, 4, 1)
        assert end == date(2026, 4, 15)

    def test_day_on_last_day_returns_same_month_first_half(self):
        # April 30 -> April 1-15
        start, end = previous_semimonth(date(2026, 4, 30))
        assert start == date(2026, 4, 1)
        assert end == date(2026, 4, 15)

    def test_january_first_half_wraps_to_december(self):
        # Jan 10 -> Dec 16-31
        start, end = previous_semimonth(date(2026, 1, 10))
        assert start == date(2025, 12, 16)
        assert end == date(2025, 12, 31)

    def test_february_second_half_handles_short_month(self):
        # Feb 28 (non-leap) -> Feb 1-15
        start, end = previous_semimonth(date(2026, 2, 28))
        assert start == date(2026, 2, 1)
        assert end == date(2026, 2, 15)

    def test_march_first_half_handles_feb_end(self):
        # March 5 -> Feb 16-28 (non-leap year 2026)
        start, end = previous_semimonth(date(2026, 3, 5))
        assert start == date(2026, 2, 16)
        assert end == date(2026, 2, 28)

    def test_march_first_half_handles_feb_leap(self):
        # March 5 2028 (leap year) -> Feb 16-29
        start, end = previous_semimonth(date(2028, 3, 5))
        assert start == date(2028, 2, 16)
        assert end == date(2028, 2, 29)
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `python3 -m pytest tests/test_utils.py::TestPreviousSemimonth -v`
Expected: ImportError — `previous_semimonth` not yet defined.

- [ ] **Step 3: Implement previous_semimonth**

Add to `utils.py`, after `load_env`:

```python
import calendar


def previous_semimonth(today: date) -> tuple:
    """Return (start, end) of the previous semimonth period.

    If today is in the 1st-15th: returns (prev month 16th, prev month last day).
    If today is in the 16th-end: returns (this month 1st, this month 15th).
    """
    if today.day <= 15:
        # Previous month's second half
        if today.month == 1:
            prev_year, prev_month = today.year - 1, 12
        else:
            prev_year, prev_month = today.year, today.month - 1
        last_day = calendar.monthrange(prev_year, prev_month)[1]
        return date(prev_year, prev_month, 16), date(prev_year, prev_month, last_day)
    else:
        # This month's first half
        return date(today.year, today.month, 1), date(today.year, today.month, 15)
```

Note: add `import calendar` to the top of the file.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_utils.py -v`
Expected: All 14 tests PASS (6 load_env + 8 semimonth).

- [ ] **Step 5: Commit**

```bash
git add utils.py tests/test_utils.py
git commit -m "feat: add previous_semimonth date utility"
```

---

### Task 3: `output_dir()` (TDD)

**Files:**
- Modify: `utils.py`
- Modify: `tests/test_utils.py`

- [ ] **Step 1: Write failing tests for output_dir**

Append to `tests/test_utils.py`:

```python
from utils import output_dir


class TestOutputDir:
    def test_returns_formatted_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = output_dir(date(2026, 4, 1), date(2026, 4, 15))
        assert result == "output/20260401-20260415/"

    def test_creates_directory(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = output_dir(date(2026, 4, 1), date(2026, 4, 15))
        assert os.path.isdir(result)

    def test_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result1 = output_dir(date(2026, 4, 1), date(2026, 4, 15))
        result2 = output_dir(date(2026, 4, 1), date(2026, 4, 15))
        assert result1 == result2
        assert os.path.isdir(result1)
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `python3 -m pytest tests/test_utils.py::TestOutputDir -v`
Expected: ImportError — `output_dir` not yet defined.

- [ ] **Step 3: Implement output_dir**

Add to `utils.py`:

```python
def output_dir(start_date: date, end_date: date) -> str:
    """Return output directory path for a date range, creating it if needed.

    Returns 'output/YYYYMMDD-YYYYMMDD/'.
    """
    dirname = f"output/{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}/"
    os.makedirs(dirname, exist_ok=True)
    return dirname
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_utils.py -v`
Expected: All 17 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add utils.py tests/test_utils.py
git commit -m "feat: add output_dir utility"
```

---

### Task 4: Type mapping utilities (TDD)

**Files:**
- Modify: `utils.py`
- Modify: `tests/test_utils.py`

- [ ] **Step 1: Write failing tests for load_type_mappings and map_task_type**

Append to `tests/test_utils.py`:

```python
import json

from utils import load_type_mappings, map_task_type


SAMPLE_MAPPINGS_JSON = [
    {"Development": "Engineering"},
    {"Code Review": "Engineering"},
    {"Meetings": "Admin"},
    {"Design": "Creative"},
]


class TestLoadTypeMappings:
    def test_loads_and_flattens(self, tmp_path):
        path = tmp_path / "mappings.json"
        path.write_text(json.dumps(SAMPLE_MAPPINGS_JSON))
        result = load_type_mappings(str(path))
        assert result == {
            "Development": "Engineering",
            "Code Review": "Engineering",
            "Meetings": "Admin",
            "Design": "Creative",
        }

    def test_empty_list(self, tmp_path):
        path = tmp_path / "mappings.json"
        path.write_text("[]")
        result = load_type_mappings(str(path))
        assert result == {}

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_type_mappings("/nonexistent/mappings.json")


class TestMapTaskType:
    def test_mapped_task(self):
        mappings = {"Development": "Engineering"}
        assert map_task_type("Development", mappings) == "Engineering"

    def test_unmapped_task_passes_through(self):
        mappings = {"Development": "Engineering"}
        assert map_task_type("Unknown Task", mappings) == "Unknown Task"

    def test_empty_mappings(self):
        assert map_task_type("Development", {}) == "Development"
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `python3 -m pytest tests/test_utils.py::TestLoadTypeMappings tests/test_utils.py::TestMapTaskType -v`
Expected: ImportError — functions not yet defined.

- [ ] **Step 3: Implement load_type_mappings and map_task_type**

Add to `utils.py`:

```python
import json


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
```

Note: `json` is already imported for `load_env` if it uses it — but actually `load_env` doesn't use json. Add `import json` to the top of `utils.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_utils.py -v`
Expected: All 23 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add utils.py tests/test_utils.py
git commit -m "feat: add type mapping utilities"
```

---

### Task 5: Config files

**Files:**
- Create: `client-info.json`
- Create: `type-mappings.json`
- Modify: `rate_card.json`

- [ ] **Step 1: Create client-info.json**

Create `client-info.json`:

```json
{
    "Widget Corp": {
        "address": ["456 Oak Ave, Floor 3", "San Francisco, CA 94102"]
    },
    "Globex Inc": {
        "address": ["789 Pine St", "Portland, OR 97201"]
    }
}
```

- [ ] **Step 2: Create type-mappings.json**

Create `type-mappings.json`:

```json
[
    {"Development": "Engineering"},
    {"Code Review": "Engineering"},
    {"Meetings": "Admin"},
    {"Design": "Creative"}
]
```

- [ ] **Step 3: Update rate_card.json to use mapped types**

Replace `rate_card.json` contents with:

```json
{
    "rates": {
        "Alice Example": {
            "Engineering": 175.00,
            "Admin": 175.00
        },
        "Bob Example": {
            "Engineering": 150.00,
            "Creative": 140.00
        }
    },
    "default_rate": null
}
```

- [ ] **Step 4: Commit**

```bash
git add client-info.json type-mappings.json rate_card.json
git commit -m "feat: add config files and re-key rate card to mapped types"
```

---

### Task 6: Add type mappings to `build_line_items` (TDD)

**Files:**
- Modify: `render_invoice.py`
- Modify: `tests/test_render_invoice.py`

- [ ] **Step 1: Write failing test for type-mapping support in build_line_items**

Append to `tests/test_render_invoice.py`:

```python
class TestBuildLineItemsWithTypeMappings:
    def test_maps_task_names(self):
        harvest_data = {
            "Alice": {
                "Acme": [
                    {"date": "2026-04-01", "task": "Development", "hours": 3.5},
                    {"date": "2026-04-01", "task": "Code Review", "hours": 1.0},
                ],
            },
        }
        rate_card = {
            "rates": {
                "Alice": {"Engineering": 175.00},
            },
            "default_rate": None,
        }
        type_mappings = {"Development": "Engineering", "Code Review": "Engineering"}

        line_items, total = build_line_items(harvest_data, rate_card, type_mappings)

        assert line_items[0]["task"] == "Engineering"
        assert line_items[1]["task"] == "Engineering"
        assert line_items[0]["rate"] == 175.00
        assert total == 787.50

    def test_unmapped_tasks_pass_through(self):
        harvest_data = {
            "Alice": {
                "Acme": [
                    {"date": "2026-04-01", "task": "Unusual Task", "hours": 2.0},
                ],
            },
        }
        rate_card = {
            "rates": {
                "Alice": {"Unusual Task": 100.00},
            },
            "default_rate": None,
        }
        type_mappings = {"Development": "Engineering"}

        line_items, total = build_line_items(harvest_data, rate_card, type_mappings)

        assert line_items[0]["task"] == "Unusual Task"
        assert total == 200.00

    def test_no_type_mappings_backward_compat(self):
        harvest_data = {
            "Alice": {
                "Acme": [
                    {"date": "2026-04-01", "task": "Development", "hours": 2.0},
                ],
            },
        }
        rate_card = {
            "rates": {"Alice": {"Development": 100.00}},
            "default_rate": None,
        }

        # No type_mappings arg — backward compatible
        line_items, total = build_line_items(harvest_data, rate_card)

        assert line_items[0]["task"] == "Development"
        assert total == 200.00
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `python3 -m pytest tests/test_render_invoice.py::TestBuildLineItemsWithTypeMappings -v`
Expected: TypeError — `build_line_items` does not accept a third argument.

- [ ] **Step 3: Update build_line_items to accept type_mappings**

In `render_invoice.py`, modify the `build_line_items` function. Add `from utils import map_task_type` at the top of the file. Change the signature and add mapping logic:

```python
from utils import map_task_type


def build_line_items(harvest_data: dict, rate_card: dict, type_mappings: dict = None) -> tuple:
    """Build sorted, priced line items from Harvest report data and a rate card.

    If type_mappings is provided, task names are mapped before rate lookup.
    Returns (line_items, total).
    """
    if type_mappings is None:
        type_mappings = {}
    raw_items = []
    for staff, clients in harvest_data.items():
        for _client, entries in clients.items():
            for entry in entries:
                task = map_task_type(entry["task"], type_mappings)
                rate = lookup_rate(rate_card, staff, task)
                amount = round(entry["hours"] * rate, 2)
                raw_items.append({
                    "sort_date": entry["date"],
                    "date": _format_date_mmddyy(entry["date"]),
                    "staff": staff,
                    "task": task,
                    "hours": entry["hours"],
                    "rate": rate,
                    "amount": amount,
                })

    raw_items.sort(key=lambda x: (x["sort_date"], x["staff"]))

    # Strip the sort key
    line_items = [{k: v for k, v in item.items() if k != "sort_date"} for item in raw_items]
    total = round(sum(item["amount"] for item in line_items), 2) if line_items else 0.0
    return line_items, total
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `python3 -m pytest tests/ -v`
Expected: All tests PASS (existing tests still work since `type_mappings` defaults to `None`).

- [ ] **Step 5: Commit**

```bash
git add render_invoice.py tests/test_render_invoice.py
git commit -m "feat: add type-mapping support to build_line_items"
```

---

### Task 7: Remove CLI from `render_invoice.py`

**Files:**
- Modify: `render_invoice.py`

- [ ] **Step 1: Remove main() and argparse import**

In `render_invoice.py`, remove:
- `import argparse` from the imports
- The entire `main()` function
- The `if __name__ == "__main__": main()` block

- [ ] **Step 2: Run all tests to verify no regressions**

Run: `python3 -m pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add render_invoice.py
git commit -m "refactor: remove CLI from render_invoice.py"
```

---

### Task 8: Downloader script (`download_harvest.py`)

**Files:**
- Create: `download_harvest.py`

- [ ] **Step 1: Write the downloader script**

Create `download_harvest.py`:

```python
"""Download Harvest time data for a date range and save to JSON files."""

import argparse
import json
import os
from datetime import date

from harvest_reports import detailed_time_by_staff_client, hours_summary_by_staff_day
from utils import load_env, output_dir, previous_semimonth


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download Harvest time data and save as JSON."
    )
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--output-dir", help="Output directory override")
    args = parser.parse_args()

    load_env(os.path.dirname(os.path.abspath(__file__)))

    if args.start and args.end:
        start_date = date.fromisoformat(args.start)
        end_date = date.fromisoformat(args.end)
    else:
        start_date, end_date = previous_semimonth(date.today())

    out = args.output_dir or output_dir(start_date, end_date)
    os.makedirs(out, exist_ok=True)

    print(f"Downloading Harvest data for {start_date} to {end_date}...")

    detailed = detailed_time_by_staff_client(start_date, end_date)
    detailed_path = os.path.join(out, "detailed-time.json")
    with open(detailed_path, "w") as f:
        json.dump(detailed, f, indent=2)
    print(f"  Saved detailed time report to {detailed_path}")

    summary = hours_summary_by_staff_day(start_date, end_date)
    summary_path = os.path.join(out, "hours-summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  Saved hours summary to {summary_path}")

    print("Done.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the help text works**

Run: `python3 download_harvest.py --help`
Expected: Usage text showing `--start`, `--end`, `--output-dir` arguments.

- [ ] **Step 3: Commit**

```bash
git add download_harvest.py
git commit -m "feat: add Harvest data downloader script"
```

---

### Task 9: Invoice generator script (TDD)

**Files:**
- Create: `generate_invoice.py`
- Create: `tests/test_generate_invoice.py`

- [ ] **Step 1: Write failing tests for the invoice generation pipeline**

Create `tests/test_generate_invoice.py`:

```python
import json
import os
import pytest
from datetime import date
from unittest.mock import patch

from generate_invoice import load_client_info, filter_by_client, build_and_render


class TestLoadClientInfo:
    def test_loads_client_address(self, tmp_path):
        path = tmp_path / "clients.json"
        path.write_text(json.dumps({
            "Acme": {"address": ["123 St", "City, ST 12345"]}
        }))
        result = load_client_info(str(path), "Acme")
        assert result == ["123 St", "City, ST 12345"]

    def test_missing_client_raises(self, tmp_path):
        path = tmp_path / "clients.json"
        path.write_text(json.dumps({"Acme": {"address": ["123 St"]}}))
        with pytest.raises(ValueError, match="Unknown.*client.*did you mean.*Acme"):
            load_client_info(str(path), "Nonexistent")


class TestFilterByClient:
    def test_filters_to_single_client(self):
        harvest_data = {
            "Alice": {
                "Acme": [{"date": "2026-04-01", "task": "Dev", "hours": 3.0}],
                "Globex": [{"date": "2026-04-01", "task": "Dev", "hours": 2.0}],
            },
            "Bob": {
                "Acme": [{"date": "2026-04-02", "task": "Dev", "hours": 5.0}],
            },
        }
        result = filter_by_client(harvest_data, "Acme")
        assert result == {
            "Alice": {
                "Acme": [{"date": "2026-04-01", "task": "Dev", "hours": 3.0}],
            },
            "Bob": {
                "Acme": [{"date": "2026-04-02", "task": "Dev", "hours": 5.0}],
            },
        }

    def test_filters_out_staff_with_no_client_entries(self):
        harvest_data = {
            "Alice": {
                "Globex": [{"date": "2026-04-01", "task": "Dev", "hours": 3.0}],
            },
        }
        result = filter_by_client(harvest_data, "Acme")
        assert result == {}

    def test_empty_data(self):
        result = filter_by_client({}, "Acme")
        assert result == {}


class TestBuildAndRender:
    @patch("generate_invoice.render_invoice_pdf")
    def test_produces_pdf(self, mock_pdf, tmp_path):
        harvest_data = {
            "Alice": {
                "Acme": [
                    {"date": "2026-04-01", "task": "Development", "hours": 4.0},
                ],
            },
        }
        rate_card = {
            "rates": {"Alice": {"Engineering": 175.00}},
            "default_rate": None,
        }
        type_mappings = {"Development": "Engineering"}
        output_path = str(tmp_path / "INV-001.pdf")

        build_and_render(
            harvest_data=harvest_data,
            rate_card=rate_card,
            type_mappings=type_mappings,
            client_name="Acme Corp",
            client_address=["123 St"],
            invoice_number="INV-001",
            invoice_date=date(2026, 4, 6),
            terms="Net 30",
            footer="Thanks!",
            output_path=output_path,
        )

        mock_pdf.assert_called_once()
        call_args = mock_pdf.call_args
        assert call_args[0][1] == output_path
        # The HTML should contain the invoice data
        html = call_args[0][0]
        assert "Acme Corp" in html
        assert "INV-001" in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_generate_invoice.py -v`
Expected: ImportError — `generate_invoice` does not exist yet.

- [ ] **Step 3: Implement generate_invoice.py**

Create `generate_invoice.py`:

```python
"""Generate a PDF invoice from Harvest time data."""

import argparse
import json
import os
from datetime import date

from harvest_reports import detailed_time_by_staff_client
from render_invoice import (
    build_invoice_context,
    build_line_items,
    load_rate_card,
    render_invoice_html,
    render_invoice_pdf,
)
from utils import load_env, load_type_mappings, output_dir, previous_semimonth


def load_client_info(path: str, client_name: str) -> list:
    """Load client address from client-info.json by client name."""
    with open(path) as f:
        clients = json.load(f)
    if client_name not in clients:
        available = ", ".join(sorted(clients.keys()))
        raise ValueError(
            f"Unknown client {client_name!r} — did you mean one of: {available}"
        )
    return clients[client_name]["address"]


def filter_by_client(harvest_data: dict, client_name: str) -> dict:
    """Filter harvest data to entries for a single client."""
    result = {}
    for staff, clients in harvest_data.items():
        if client_name in clients:
            result[staff] = {client_name: clients[client_name]}
    return result


def build_and_render(
    harvest_data: dict,
    rate_card: dict,
    type_mappings: dict,
    client_name: str,
    client_address: list,
    invoice_number: str,
    invoice_date: date,
    terms: str,
    footer: str,
    output_path: str,
) -> None:
    """Build invoice context and render to PDF."""
    context = build_invoice_context(
        harvest_data=harvest_data,
        rate_card=rate_card,
        client_name=client_name,
        client_address=client_address,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        terms=terms,
        footer=footer,
        type_mappings=type_mappings,
    )
    html = render_invoice_html(context)
    render_invoice_pdf(html, output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a PDF invoice from Harvest time data.")
    parser.add_argument("--client-name", required=True, help="Client name (must match client-info.json)")
    parser.add_argument("--invoice-number", required=True, help="Invoice number (e.g. INV-2026-042)")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--invoice-date", help="Invoice date (YYYY-MM-DD), defaults to today")
    parser.add_argument("--terms", default="Net 30", help="Payment terms")
    parser.add_argument("--footer", default="Thank you for your business.", help="Footer text")
    parser.add_argument("--rate-card", default="rate_card.json", help="Rate card path")
    parser.add_argument("--client-info", default="client-info.json", help="Client info path")
    parser.add_argument("--type-mappings", default="type-mappings.json", help="Type mappings path")
    parser.add_argument("--output-dir", help="Output directory override")
    args = parser.parse_args()

    load_env(os.path.dirname(os.path.abspath(__file__)))

    if args.start and args.end:
        start_date = date.fromisoformat(args.start)
        end_date = date.fromisoformat(args.end)
    else:
        start_date, end_date = previous_semimonth(date.today())

    inv_date = date.fromisoformat(args.invoice_date) if args.invoice_date else date.today()
    out = args.output_dir or output_dir(start_date, end_date)

    client_address = load_client_info(args.client_info, args.client_name)
    type_mappings = load_type_mappings(args.type_mappings)
    rate_card = load_rate_card(args.rate_card)

    harvest_data = detailed_time_by_staff_client(start_date, end_date)
    harvest_data = filter_by_client(harvest_data, args.client_name)

    output_path = os.path.join(out, f"{args.invoice_number}.pdf")

    build_and_render(
        harvest_data=harvest_data,
        rate_card=rate_card,
        type_mappings=type_mappings,
        client_name=args.client_name,
        client_address=client_address,
        invoice_number=args.invoice_number,
        invoice_date=inv_date,
        terms=args.terms,
        footer=args.footer,
        output_path=output_path,
    )
    print(f"Invoice written to {output_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Update build_invoice_context to pass type_mappings through**

In `render_invoice.py`, update `build_invoice_context` to accept and pass `type_mappings`:

```python
def build_invoice_context(
    harvest_data: dict,
    rate_card: dict,
    client_name: str,
    client_address: list,
    invoice_number: str,
    invoice_date: date,
    terms: str = "Net 30",
    footer: str = "Thank you for your business.",
    type_mappings: dict = None,
) -> dict:
    """Assemble the full template context dict for an invoice."""
    line_items, total = build_line_items(harvest_data, rate_card, type_mappings)
    return {
        "company": {
            "name": "DVV Entertainment",
            "address": ["PO Box 6317", "Alameda, CA 94501"],
            "email": "accounting@dvvent.com",
            "logo_path": os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "assets", "dvv-logo.svg"
            ),
        },
        "client": {
            "name": client_name,
            "address": client_address,
        },
        "invoice_number": invoice_number,
        "invoice_date": invoice_date.strftime("%m/%d/%y"),
        "terms": terms,
        "line_items": line_items,
        "total": total,
        "footer": footer,
    }
```

- [ ] **Step 5: Run all tests to verify they pass**

Run: `python3 -m pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add generate_invoice.py tests/test_generate_invoice.py render_invoice.py
git commit -m "feat: add invoice generator script"
```

---

### Task 10: Time summary generator (TDD)

**Files:**
- Create: `generate_summary.py`
- Create: `tests/test_generate_summary.py`

- [ ] **Step 1: Write failing tests for the summary generation logic**

Create `tests/test_generate_summary.py`:

```python
import os
import pytest
from datetime import date

from generate_summary import build_summary_rows, write_summary_tsv


class TestBuildSummaryRows:
    def test_basic_summary(self):
        hours_data = {
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
        type_mappings = {"Development": "Engineering", "Meetings": "Admin"}

        rows = build_summary_rows(hours_data, type_mappings)

        expected = [
            ("Alice", "04/01/26", "Admin", 1.0),
            ("Alice", "04/01/26", "Engineering", 3.5),
            ("Alice", "04/02/26", "Engineering", 7.0),
            ("Alice", "", "Admin", 1.0),
            ("Alice", "", "Engineering", 10.5),
            ("Alice", "", "Total", 11.5),
        ]
        assert rows == expected

    def test_multiple_tasks_same_mapped_type(self):
        hours_data = {
            "Alice": {
                "2026-04-01": {
                    "tasks": {"Development": 3.0, "Code Review": 2.0},
                    "total": 5.0,
                },
            },
        }
        type_mappings = {"Development": "Engineering", "Code Review": "Engineering"}

        rows = build_summary_rows(hours_data, type_mappings)

        expected = [
            ("Alice", "04/01/26", "Engineering", 5.0),
            ("Alice", "", "Engineering", 5.0),
            ("Alice", "", "Total", 5.0),
        ]
        assert rows == expected

    def test_unmapped_task_passes_through(self):
        hours_data = {
            "Alice": {
                "2026-04-01": {
                    "tasks": {"Unusual": 2.0},
                    "total": 2.0,
                },
            },
        }
        type_mappings = {"Development": "Engineering"}

        rows = build_summary_rows(hours_data, type_mappings)

        expected = [
            ("Alice", "04/01/26", "Unusual", 2.0),
            ("Alice", "", "Unusual", 2.0),
            ("Alice", "", "Total", 2.0),
        ]
        assert rows == expected

    def test_multiple_staff_sorted(self):
        hours_data = {
            "Zara": {
                "2026-04-01": {"tasks": {"Development": 4.0}, "total": 4.0},
            },
            "Alice": {
                "2026-04-01": {"tasks": {"Development": 3.0}, "total": 3.0},
            },
        }
        type_mappings = {"Development": "Engineering"}

        rows = build_summary_rows(hours_data, type_mappings)

        staff_order = [r[0] for r in rows]
        assert staff_order == ["Alice", "Alice", "Alice", "Zara", "Zara", "Zara"]

    def test_empty_data(self):
        rows = build_summary_rows({}, {})
        assert rows == []


class TestWriteSummaryTsv:
    def test_writes_file(self, tmp_path):
        rows = [
            ("Alice", "04/01/26", "Engineering", 3.5),
            ("Alice", "", "Engineering", 3.5),
            ("Alice", "", "Total", 3.5),
        ]
        path = str(tmp_path / "summary.tsv")
        write_summary_tsv(rows, path)

        with open(path) as f:
            lines = f.readlines()

        assert lines[0] == "Staff\tDate\tType\tHours\n"
        assert lines[1] == "Alice\t04/01/26\tEngineering\t3.50\n"
        assert lines[2] == "Alice\t\tEngineering\t3.50\n"
        assert lines[3] == "Alice\t\tTotal\t3.50\n"
        assert len(lines) == 4
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_generate_summary.py -v`
Expected: ImportError — `generate_summary` does not exist yet.

- [ ] **Step 3: Implement generate_summary.py**

Create `generate_summary.py`:

```python
"""Generate a tab-delimited time summary from Harvest data."""

import argparse
import os
from collections import defaultdict
from datetime import date

from harvest_reports import hours_summary_by_staff_day
from utils import load_env, load_type_mappings, map_task_type, output_dir, previous_semimonth


def _format_date_mmddyy(iso_date: str) -> str:
    """Convert '2026-04-01' to '04/01/26'."""
    year, month, day = iso_date.split("-")
    return f"{month}/{day}/{year[2:]}"


def build_summary_rows(hours_data: dict, type_mappings: dict) -> list:
    """Build sorted summary rows from hours_summary_by_staff_day output.

    Returns list of (staff, date_str, type, hours) tuples.
    date_str is MM/DD/YY for daily rows, empty string for totals.
    """
    rows = []
    for staff in sorted(hours_data.keys()):
        dates = hours_data[staff]
        grand_totals = defaultdict(float)

        for iso_date in sorted(dates.keys()):
            day_data = dates[iso_date]
            # Aggregate by mapped type for this day
            day_by_type = defaultdict(float)
            for task, hours in day_data["tasks"].items():
                mapped = map_task_type(task, type_mappings)
                day_by_type[mapped] += hours

            formatted_date = _format_date_mmddyy(iso_date)
            for mapped_type in sorted(day_by_type.keys()):
                hours = round(day_by_type[mapped_type], 2)
                rows.append((staff, formatted_date, mapped_type, hours))
                grand_totals[mapped_type] += hours

        # Grand total rows for this staff member
        overall = 0.0
        for mapped_type in sorted(grand_totals.keys()):
            hours = round(grand_totals[mapped_type], 2)
            rows.append((staff, "", mapped_type, hours))
            overall += hours
        rows.append((staff, "", "Total", round(overall, 2)))

    return rows


def write_summary_tsv(rows: list, path: str) -> None:
    """Write summary rows to a tab-delimited file."""
    with open(path, "w") as f:
        f.write("Staff\tDate\tType\tHours\n")
        for staff, date_str, type_name, hours in rows:
            f.write(f"{staff}\t{date_str}\t{type_name}\t{hours:.2f}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a time summary from Harvest data.")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--type-mappings", default="type-mappings.json", help="Type mappings path")
    parser.add_argument("--output-dir", help="Output directory override")
    args = parser.parse_args()

    load_env(os.path.dirname(os.path.abspath(__file__)))

    if args.start and args.end:
        start_date = date.fromisoformat(args.start)
        end_date = date.fromisoformat(args.end)
    else:
        start_date, end_date = previous_semimonth(date.today())

    out = args.output_dir or output_dir(start_date, end_date)

    type_mappings = load_type_mappings(args.type_mappings)
    hours_data = hours_summary_by_staff_day(start_date, end_date)

    rows = build_summary_rows(hours_data, type_mappings)
    output_path = os.path.join(out, "time-summary.tsv")
    write_summary_tsv(rows, output_path)
    print(f"Time summary written to {output_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `python3 -m pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add generate_summary.py tests/test_generate_summary.py
git commit -m "feat: add time summary generator script"
```

---

### Task 11: Full test suite verification

**Files:**
- No new files

- [ ] **Step 1: Run the complete test suite**

Run: `python3 -m pytest tests/ -v`
Expected: All tests PASS across all test files:
- `tests/test_harvest_reports.py` — existing API and report tests
- `tests/test_render_invoice.py` — invoice rendering with type mapping support
- `tests/test_utils.py` — env loading, semimonth, output dir, type mappings
- `tests/test_generate_invoice.py` — invoice generator pipeline
- `tests/test_generate_summary.py` — time summary generation

- [ ] **Step 2: Verify all three scripts show help text**

Run:
```bash
python3 download_harvest.py --help
python3 generate_invoice.py --help
python3 generate_summary.py --help
```
Expected: Each shows its argument list.

- [ ] **Step 3: Commit (if any fixes were needed)**

Only commit if previous steps required fixes. Otherwise, skip.
