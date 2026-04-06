# Harvest Export End-to-End Flow — Design Spec

## Overview

Three independent CLI scripts that form a Harvest time-tracking export pipeline: a data downloader, an invoice generator, and a time summary generator. They share config files, date utilities, and output directory conventions but can be run independently.

## Architecture

Three standalone scripts, each independently runnable:

- `download_harvest.py` — fetches and persists raw Harvest data to JSON
- `generate_invoice.py` — produces client-facing PDF invoices
- `generate_summary.py` — produces tab-delimited time summaries

Shared infrastructure:
- `utils.py` — environment loading, semimonth date range logic, output directory management, type-mapping utilities
- `harvest_reports.py` — existing Harvest API layer (unchanged)
- `render_invoice.py` — existing pure rendering functions (CLI removed, type-mapping support added)
- Config files: `.env`, `client-info.json`, `type-mappings.json`, `rate_card.json`

## Shared Utilities (`utils.py`)

### `load_env() -> None`

Loads Harvest credentials into `os.environ`. Looks for a `.env` file in the same directory as the calling script. If found, parses `KEY=VALUE` lines (ignoring blank lines and `#` comments) and sets them in `os.environ`. Existing env vars are not overwritten (env vars take precedence over `.env` values).

After loading, verifies that `HARVEST_ACCESS_TOKEN` and `HARVEST_ACCOUNT_ID` are present in `os.environ`. If either is missing, raises `ValueError` with a clear message listing what's missing and where to set it.

No external dependencies — simple file parsing, not `python-dotenv`.

All three scripts call `load_env()` at startup, before any Harvest API calls. `_harvest_get` in `harvest_reports.py` continues to read from `os.environ` as before.

### `previous_semimonth(today: date) -> tuple[date, date]`

Returns the start and end dates of the previous semimonth period:

- If today is in the 1st–15th: returns (previous month 16th, previous month last day)
- If today is in the 16th–end: returns (this month 1st, this month 15th)

### `output_dir(start_date: date, end_date: date) -> str`

Returns path `output/YYYYMMDD-YYYYMMDD/`, creating the directory if it doesn't exist. All three scripts use this for file placement.

## Config Files

### `client-info.json`

Maps Harvest client name to billing address:

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

Keyed by client name as it appears in Harvest.

### `type-mappings.json`

Maps Harvest task names to summary types. A list of single-key objects:

```json
[
    {"Development": "Engineering"},
    {"Code Review": "Engineering"},
    {"Meetings": "Admin"},
    {"Design": "Creative"}
]
```

Used by both the invoicing script (Task column on the invoice) and the summary script (type grouping). If a Harvest task is not in the mappings, the original task name passes through unchanged.

### `rate_card.json` (modified)

Re-keyed from Harvest task names to mapped summary types:

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

Rate lookup happens after type mapping is applied.

## Script 1: Downloader (`download_harvest.py`)

### CLI Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--start` | No | Previous semimonth start | Start date (YYYY-MM-DD) |
| `--end` | No | Previous semimonth end | End date (YYYY-MM-DD) |
| `--output-dir` | No | `output/YYYYMMDD-YYYYMMDD/` | Output directory override |

### Behavior

1. Resolve date range (explicit args or `previous_semimonth(date.today())`)
2. Call `detailed_time_by_staff_client(start, end)`
3. Call `hours_summary_by_staff_day(start, end)`
4. Save to output directory:
   - `detailed-time.json` — raw detailed report
   - `hours-summary.json` — raw hours summary
5. Print what was saved and where

No transformation — raw Harvest data persisted to disk for archival/reference.

## Script 2: Invoice Generator (`generate_invoice.py`)

### CLI Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--client-name` | Yes | — | Client name (must match key in client-info.json) |
| `--invoice-number` | Yes | — | Invoice number (e.g., INV-2026-042) |
| `--start` | No | Previous semimonth start | Start date (YYYY-MM-DD) |
| `--end` | No | Previous semimonth end | End date (YYYY-MM-DD) |
| `--invoice-date` | No | Today | Invoice date (YYYY-MM-DD) |
| `--terms` | No | "Net 30" | Payment terms |
| `--footer` | No | "Thank you for your business." | Footer text |
| `--rate-card` | No | `rate_card.json` | Rate card path |
| `--client-info` | No | `client-info.json` | Client info path |
| `--type-mappings` | No | `type-mappings.json` | Type mappings path |
| `--output-dir` | No | `output/YYYYMMDD-YYYYMMDD/` | Output directory override |

### Behavior

1. Resolve date range
2. Load `client-info.json`, look up client address by `--client-name` (raise error if not found)
3. Load `type-mappings.json`, build a lookup dict (`{harvest_task: summary_type}`)
4. Load `rate_card.json`
5. Call `detailed_time_by_staff_client(start, end)` from `harvest_reports.py`
6. Filter to the specified client only
7. Apply type mappings to task names (mapped name replaces Harvest task name; unmapped pass through)
8. Build line items with mapped task names — rate lookup uses the mapped type
9. Assemble context via `build_invoice_context`, render HTML, render PDF
10. Save as `output/YYYYMMDD-YYYYMMDD/<invoice-number>.pdf`

### Replaces `render_invoice.py` CLI

The `main()` function and argparse in `render_invoice.py` are removed. The pure functions remain: `load_rate_card`, `lookup_rate`, `build_line_items`, `build_invoice_context`, `render_invoice_html`, `render_invoice_pdf`.

`build_line_items` is updated to accept an optional type-mapping dict. When provided, each entry's task name is mapped via `map_task_type()` before rate lookup and before being stored in the line item. When not provided (or empty), behavior is unchanged. The mapping happens inside `build_line_items` so callers just pass in the mappings dict.

## Script 3: Time Summary Generator (`generate_summary.py`)

### CLI Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--start` | No | Previous semimonth start | Start date (YYYY-MM-DD) |
| `--end` | No | Previous semimonth end | End date (YYYY-MM-DD) |
| `--type-mappings` | No | `type-mappings.json` | Type mappings path |
| `--output-dir` | No | `output/YYYYMMDD-YYYYMMDD/` | Output directory override |

### Behavior

1. Resolve date range
2. Load `type-mappings.json`, build lookup dict
3. Call `hours_summary_by_staff_day(start, end)` from `harvest_reports.py`
4. Apply type mappings to task names (unmapped pass through)
5. Aggregate hours by (staff, date, mapped type) — multiple Harvest tasks mapping to the same type have their hours summed
6. Write tab-delimited file to `output/YYYYMMDD-YYYYMMDD/time-summary.tsv`

### Output Format

Tab-separated, four columns:

```
Staff	Date	Type	Hours
Alice Smith	04/01/26	Admin	1.00
Alice Smith	04/01/26	Engineering	7.50
Alice Smith	04/02/26	Engineering	8.00
Alice Smith		Admin	1.00
Alice Smith		Engineering	15.50
Alice Smith		Total	16.50
Bob Jones	04/01/26	Engineering	6.00
Bob Jones		Engineering	6.00
Bob Jones		Total	6.00
```

Rules:
- Sorted by staff name, then date, then type
- Per-staff grand totals after all date rows: one row per type with empty date column, then an overall "Total" row
- No row generated if zero hours for a type on a given day
- Dates formatted MM/DD/YY (matching the invoice format)
- Hours formatted to two decimal places

## Type Mapping Logic

Shared by the invoicing and summary scripts. A pure function:

```python
def load_type_mappings(path: str) -> dict[str, str]
```

Reads `type-mappings.json` (list of single-key objects) and returns a flat `{harvest_task: summary_type}` dict.

```python
def map_task_type(task: str, mappings: dict[str, str]) -> str
```

Returns `mappings.get(task, task)` — mapped name or original if not found.

These live in a shared location (either `utils.py` renamed to something broader, or a small `config.py`). Since they're config-loading utilities alongside `output_dir`, grouping them makes sense.

## File Structure Changes

| File | Action | Responsibility |
|------|--------|----------------|
| `utils.py` | Create | `previous_semimonth()`, `output_dir()`, `load_type_mappings()`, `map_task_type()` |
| `download_harvest.py` | Create | Downloader CLI |
| `generate_invoice.py` | Create | Invoice generator CLI |
| `generate_summary.py` | Create | Time summary CLI |
| `client-info.json` | Create | Example client address mapping |
| `type-mappings.json` | Create | Example Harvest task → summary type mapping |
| `render_invoice.py` | Modify | Remove `main()` and argparse; update `build_line_items` to accept optional type mappings |
| `rate_card.json` | Modify | Re-key from Harvest task names to mapped summary types |
| `harvest_reports.py` | Unchanged | API layer and report functions |
| `tests/test_utils.py` | Create | Semimonth, output dir, type mapping tests |
| `tests/test_generate_invoice.py` | Create | Invoice pipeline integration tests |
| `tests/test_generate_summary.py` | Create | Summary generation tests |
| `tests/test_render_invoice.py` | Modify | Update for type-mapping parameter on build_line_items |

## Error Handling

- Missing client in `client-info.json`: raise `ValueError` with the client name and available clients
- Missing type mapping: pass through original task name (not an error)
- Missing rate card entry (no default): raise `ValueError` with the staff/mapped-type combo
- Empty date range from Harvest: downloader saves empty JSON arrays; invoice produces $0.00 total; summary produces header-only TSV

## Dependencies

No new dependencies beyond what the project already uses:
- `requests` — Harvest API
- `jinja2` — template rendering
- `weasyprint` — HTML-to-PDF
- `pytest` — testing

All new code uses only the standard library plus these existing dependencies.
