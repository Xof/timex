# Invoice Template — Design Spec

## Overview

A Jinja2 HTML template rendered to PDF via WeasyPrint. Produces client-facing billing invoices from Harvest time entry data combined with an external rate card. The template is a pure renderer — all data is pre-computed by the pipeline script before being passed to the template.

## Architecture

Single-file approach: one Jinja2 `.html` template with embedded `<style>` block containing all CSS including `@page` print rules.

### New Files

- `templates/invoice.html` — Jinja2 + CSS template
- `rate_card.json` — staff/task rate mapping
- `render_invoice.py` — pipeline script: fetches Harvest data, applies rate card, assembles context, renders PDF

### Existing Files (unchanged)

- `harvest_reports.py` — `_harvest_get` and report functions provide the raw time data

## Template Data Model

The template receives a single context dict:

```python
{
    "company": {
        "name": "DVV Entertainment",
        "address": ["PO Box 6317", "Alameda, CA 94501"],
        "email": "accounting@dvvent.com",
        "logo_path": "/path/to/dvv logo.svg"
    },
    "client": {
        "name": "Widget Corp",
        "address": ["456 Oak Ave, Floor 3", "San Francisco, CA 94102"]
    },
    "invoice_number": "INV-2026-042",
    "invoice_date": "04/06/26",
    "terms": "Net 30",
    "line_items": [
        {
            "date": "04/01/26",
            "staff": "A. Smith",
            "task": "Development",
            "hours": 6.0,
            "rate": 175.00,
            "amount": 1050.00
        }
    ],
    "total": 2662.50,
    "footer": "Thank you for your business."
}
```

The template performs no computation. All amounts, totals, and date formatting are pre-computed by `render_invoice.py`.

## Page Setup

- US Letter (8.5" × 11"), portrait
- Margins: ~0.75" all sides
- Single page target, but line items flow to additional pages if needed

## Layout

### Header Row

Left side:
- DVV logo (SVG, ~120px wide)
- Company name in Nunito Bold, 11px
- Address lines and email in Nunito, 8px, gray (#777)

Right side:
- "INVOICE" label in Nunito Light, 13px, letter-spacing 3px, color #201e20
- Invoice number (value in Droid Sans Mono), date, and terms stacked below, 10px

### Bill To Block

Below header, separated by a 1px #e5e5e5 top border:
- "BILL TO" label: 7px uppercase, letter-spacing 1.5px, gray (#999)
- Client name: Nunito Bold, 11px
- Client address: 8px, gray (#777)

### Line Items Table

Columns with percentage widths:

| Column | Width | Align | Font |
|--------|-------|-------|------|
| Date   | 12%   | left  | Nunito |
| Staff  | 28%   | left  | Nunito |
| Task   | 24%   | left  | Nunito |
| Hours  | 10%   | right | Droid Sans Mono |
| Rate   | 12%   | right | Droid Sans Mono |
| Amount | 14%   | right | Droid Sans Mono |

- Header row: 7px uppercase bold, 2px solid #201e20 bottom border
- Data rows: 7.5px, separated by 1px #f0f0f0 bottom borders
- Row padding: 4px vertical, 6px horizontal
- Sorted chronologically by date, then by staff name within each date
- Dates formatted as MM/DD/YY
- Amounts formatted with `$` prefix, comma thousands separator, two decimal places

### Total

- Right-aligned, 220px wide block
- 2px solid #201e20 top border
- "Total" label and amount on the same line, Nunito Bold 14px
- Amount in Droid Sans Mono

### Footer

- Centered, separated by 1px #e5e5e5 top border
- 9px italic, gray (#aaa)
- Parameterized — usually "Thank you for your business."
- 40px top margin above the border

## Typography

- **Body font:** Nunito (Google Fonts) — weights 300, 400, 600, 700
- **Monospace font:** Droid Sans Mono (Google Fonts) — for Hours, Rate, Amount columns
- Loaded via `@font-face` from Google Fonts URLs; WeasyPrint fetches at render time

## Brand Colors

- Primary dark: #201e20 (from DVV logo background)
- Accent red: #ee3725 (from DVV logo "V")
- Text: #333 (body), #555 (column headers), #777 (secondary), #999 (labels), #aaa (footer)
- Rules: #e5e5e5 (section dividers), #f0f0f0 (row separators)
- Background: #fff

The accent red is available but not used in the current layout — it comes from the logo itself.

## Rate Card Format

`rate_card.json` — nested JSON mapping staff name → task name → hourly rate:

```json
{
    "rates": {
        "A. Smith": {
            "Development": 175.00,
            "Meetings": 175.00
        },
        "B. Jones": {
            "Development": 150.00,
            "Code Review": 150.00
        }
    },
    "default_rate": null
}
```

- `default_rate`: optional fallback. If `null`, a missing staff/task combo raises an error. If set to a number, that rate is used for any combo not explicitly listed.

## Pipeline Script (`render_invoice.py`)

Responsibilities:

1. Call `detailed_time_by_staff_client(start_date, end_date)` from `harvest_reports.py`
2. Look up rates from `rate_card.json` for each (staff, task) combination
3. Compute `amount = hours * rate` per line item
4. Format dates as MM/DD/YY
5. Format amounts with `$`, commas, two decimals
6. Sort line items chronologically, then by staff name within each date
7. Sum all amounts into `total`
8. Assemble the full context dict
9. Render the Jinja2 template with the context
10. Pass HTML to WeasyPrint to produce PDF

## Error Handling

- Missing rate card entry (no default): raise `ValueError` with the staff/task combo that's missing
- Empty time entries for the date range: produce an invoice with no line items and $0.00 total

## Dependencies

New dependencies beyond what the project already uses:

- `jinja2` — template rendering
- `weasyprint` — HTML-to-PDF

## Company Identity (Baked In)

The DVV company info is provided in the context dict, not hardcoded in the template. However, the default values for the pipeline script are:

- **Name:** DVV Entertainment
- **Address:** PO Box 6317, Alameda, CA 94501
- **Email:** accounting@dvvent.com
- **Logo:** `assets/dvv-logo.svg` (copied into the project from the source file)
