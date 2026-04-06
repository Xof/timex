# Harvest Time Reports — Design Spec

## Overview

A Python module (`harvest_reports.py`) that fetches time entry data from the Harvest API v2 and returns structured reports as plain Python data structures. Two public functions, each accepting a date range.

PDF/presentation is deferred to a future phase.

## Dependencies

- Python 3.x
- `requests` (sole external dependency)
- Environment variables: `HARVEST_ACCESS_TOKEN`, `HARVEST_ACCOUNT_ID`

## API Layer

### `_harvest_get(endpoint, params) -> list[dict]`

Private helper that handles all Harvest API communication:

- Reads `HARVEST_ACCESS_TOKEN` and `HARVEST_ACCOUNT_ID` from environment variables
- Sets required headers: `Authorization: Bearer ...`, `Harvest-Account-Id: ...`, `User-Agent: timex (contact info)`
- Follows cursor-based pagination via `links.next` URLs
- On HTTP 429 (rate limited), sleeps for the `Retry-After` duration and retries
- Returns all collected records as a flat list

Both report functions share a single call to `_harvest_get("/v2/time_entries", {"from": start, "to": end})`, then do in-memory grouping.

## Report 1: Detailed Time Per Staff Per Client

### `detailed_time_by_staff_client(start_date: date, end_date: date) -> dict`

Groups time entries by **user -> client -> (date, task)**, summing hours per (date, task) tuple.

### Return structure

```python
{
    "Staff Name": {
        "Client Name": [
            {"date": "2026-04-01", "task": "Development", "hours": 3.5},
            {"date": "2026-04-01", "task": "Meetings", "hours": 1.0},
        ]
    }
}
```

- Outer key: staff member full name
- Inner key: client name
- Value: list of dicts, each with date (ISO 8601 string), task name, and summed hours
- Sorted by date, then task name within each client group

## Report 2: Hours Summary Per Day Per Staff Per Task

### `hours_summary_by_staff_day(start_date: date, end_date: date) -> dict`

Groups time entries by **user -> date -> task**, summing hours, with a total across all tasks per day.

### Return structure

```python
{
    "Staff Name": {
        "2026-04-01": {
            "tasks": {"Development": 3.5, "Meetings": 1.0},
            "total": 4.5
        },
        "2026-04-02": {
            "tasks": {"Development": 7.0},
            "total": 7.0
        }
    }
}
```

- Outer key: staff member full name
- Date key: ISO 8601 date string
- `tasks`: dict mapping task name to summed hours
- `total`: sum of all task hours for that day
- Dates sorted chronologically

## Data Source

Both functions fetch from `GET /v2/time_entries?from={start}&to={end}`. Each time entry returned by Harvest includes nested objects for `user`, `client`, `task`, and `project` with `id` and `name` fields, so no additional API calls are needed.

## Rate Limiting

- Harvest allows 100 requests per 15 seconds for regular endpoints
- The pagination helper respects HTTP 429 responses and backs off using the `Retry-After` header
- For typical usage (date ranges of a month or so), pagination will require only a handful of requests

## Error Handling

- Missing environment variables: raise `ValueError` with a clear message
- HTTP errors (non-429): raise with status code and response body
- Empty date ranges: return empty dicts

## Future Work (Part 2)

- PDF generation from the returned data structures
- Formatting, layout, and presentation choices TBD
