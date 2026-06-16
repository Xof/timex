# timex

Harvest time-tracking report generator. Pulls time entries from the Harvest v2
API and produces three outputs: raw JSON snapshots, a tab-delimited time
summary, and a rendered PDF invoice.

## Installation

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/). `uv sync` creates a
virtual environment and installs the project — including its console commands —
along with the test tooling:

```
uv sync
```

`weasyprint` has system-library dependencies (Pango, Cairo, GDK-PixBuf). On
macOS: `brew install pango`. On Debian/Ubuntu: see the
[weasyprint install guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html).

## Configuration

Create a `.env` file in the project root (values can also be supplied via the
environment — real env vars win over `.env`):

```
HARVEST_ACCESS_TOKEN=your-personal-access-token
HARVEST_ACCOUNT_ID=123456
```

Tokens are issued at <https://id.getharvest.com/developers>.

Three JSON files drive reporting:

| File | Purpose |
| --- | --- |
| `rate_card.json` | Hourly rates. Either a flat `default_rate`, or per-staff/per-task `rates: { staff: { task: rate } }`. |
| `client-info.json` | Map of client name → billing address (list of lines). Must match the client name exactly as it appears in Harvest. |
| `type-mappings.json` | List of `{harvest_task_name: summary_label}` objects. Used to collapse Harvest task names into report/invoice categories. Unmapped tasks pass through unchanged. |

## Default date range

If you don't pass `--start` / `--end`, every script reports on the **previous
semimonth**:

- Run on days 1–15 → previous month's 16th through end of month.
- Run on days 16–end → current month's 1st through 15th.

Output is written to `output/YYYYMMDD-YYYYMMDD/` (the date range), unless
`--output-dir` is given.

## Scripts

### `download-harvest` — snapshot raw data

Fetches a detailed time report and a per-staff / per-day hours summary, and
writes each to a JSON file. Useful for archiving or for feeding other tools.

```
uv run download-harvest [--start 2026-04-01] [--end 2026-04-15] [--output-dir path]
```

Writes:
- `detailed-time.json`
- `hours-summary.json`

### `generate-summary` — tab-delimited time summary

Produces a flat TSV with one row per (staff, date, mapped-task-type), plus
per-staff subtotals and a grand total per staff member. Suitable for pasting
into a spreadsheet.

```
uv run generate-summary [--start ...] [--end ...] \
    [--type-mappings type-mappings.json] [--output-dir path]
```

Writes `time-summary.tsv` with columns: `Staff  Date  Type  Hours` (dates are
`MM/DD/YY`; subtotal and total rows leave `Date` empty).

### `generate-invoice` — PDF invoice

Renders a per-client PDF invoice from the Harvest detail, priced against
`rate_card.json`.

```
uv run generate-invoice \
    --client-name "PGX Inc." \
    --invoice-number INV-2026-042 \
    [--start ...] [--end ...] \
    [--invoice-date 2026-04-17] \
    [--terms "Net 30"] \
    [--footer "Thank you for your business."] \
    [--rate-card rate_card.json] \
    [--client-info client-info.json] \
    [--type-mappings type-mappings.json] \
    [--output-dir path]
```

`--client-name` must match a key in `client-info.json`; the script errors and
lists known clients if it doesn't. Output is `<invoice-number>.pdf` in the
resolved output directory.

## Typical workflow

```
# 1. Archive the period's raw data
uv run download-harvest

# 2. Produce a summary for internal review
uv run generate-summary

# 3. Generate a client invoice
uv run generate-invoice --client-name "PGX Inc." --invoice-number INV-2026-042
```

All three default to the same previous-semimonth range, so they land in the
same `output/` subdirectory.

## Tests

```
uv run pytest tests/ -v
```
