# Invoice Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce client-facing PDF invoices from Harvest time data and an external rate card, rendered via Jinja2 + WeasyPrint.

**Architecture:** A single pipeline script (`render_invoice.py`) containing pure functions for rate card lookup, line item assembly, and context building. A Jinja2 HTML template (`templates/invoice.html`) with embedded CSS handles all presentation. WeasyPrint converts the rendered HTML to PDF.

**Tech Stack:** Python 3.9+, Jinja2, WeasyPrint, pytest

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `assets/dvv-logo.svg` | Create | Company logo (copied from source) |
| `templates/invoice.html` | Create | Jinja2 template with embedded CSS — pure renderer |
| `rate_card.json` | Create | Example rate card mapping (staff, task) → rate |
| `render_invoice.py` | Create | Pipeline: load rate card, build line items, assemble context, render PDF |
| `tests/test_render_invoice.py` | Create | Tests for all pipeline functions |

---

### Task 1: Project setup — copy logo, add dependencies

**Files:**
- Create: `assets/dvv-logo.svg`

- [ ] **Step 1: Create assets directory and copy the logo**

```bash
mkdir -p assets
cp "/Users/xof/Desktop/DVV/Logos and Graphics/dvv logo.svg" assets/dvv-logo.svg
```

- [ ] **Step 2: Add jinja2 and weasyprint to pyproject.toml**

In `pyproject.toml`, change the `dependencies` line:

```toml
dependencies = ["requests", "jinja2", "weasyprint"]
```

- [ ] **Step 3: Install dependencies**

```bash
pip install jinja2 weasyprint
```

- [ ] **Step 4: Commit**

```bash
git add assets/dvv-logo.svg pyproject.toml
git commit -m "chore: add DVV logo and jinja2/weasyprint dependencies"
```

---

### Task 2: Rate card loading and lookup (TDD)

**Files:**
- Create: `render_invoice.py`
- Create: `tests/test_render_invoice.py`

- [ ] **Step 1: Write failing tests for rate card functions**

Create `tests/test_render_invoice.py`:

```python
import json
import os
import pytest

from render_invoice import load_rate_card, lookup_rate


SAMPLE_RATE_CARD = {
    "rates": {
        "Alice": {
            "Development": 175.00,
            "Meetings": 150.00,
        },
        "Bob": {
            "Development": 125.00,
        },
    },
    "default_rate": None,
}


class TestLoadRateCard:
    def test_loads_json_file(self, tmp_path):
        path = tmp_path / "rates.json"
        path.write_text(json.dumps(SAMPLE_RATE_CARD))
        result = load_rate_card(str(path))
        assert result == SAMPLE_RATE_CARD

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_rate_card("/nonexistent/rates.json")


class TestLookupRate:
    def test_exact_match(self):
        assert lookup_rate(SAMPLE_RATE_CARD, "Alice", "Development") == 175.00

    def test_missing_combo_no_default_raises(self):
        with pytest.raises(ValueError, match="No rate.*Alice.*Code Review"):
            lookup_rate(SAMPLE_RATE_CARD, "Alice", "Code Review")

    def test_missing_staff_no_default_raises(self):
        with pytest.raises(ValueError, match="No rate.*Charlie.*Development"):
            lookup_rate(SAMPLE_RATE_CARD, "Charlie", "Development")

    def test_missing_combo_with_default(self):
        card = {**SAMPLE_RATE_CARD, "default_rate": 100.00}
        assert lookup_rate(card, "Alice", "Code Review") == 100.00

    def test_missing_staff_with_default(self):
        card = {**SAMPLE_RATE_CARD, "default_rate": 100.00}
        assert lookup_rate(card, "Charlie", "Development") == 100.00
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_render_invoice.py -v`
Expected: ImportError — `render_invoice` does not exist yet.

- [ ] **Step 3: Implement load_rate_card and lookup_rate**

Create `render_invoice.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_render_invoice.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add render_invoice.py tests/test_render_invoice.py
git commit -m "feat: add rate card loading and lookup with tests"
```

---

### Task 3: Line item assembly (TDD)

**Files:**
- Modify: `render_invoice.py`
- Modify: `tests/test_render_invoice.py`

- [ ] **Step 1: Write failing tests for build_line_items**

Append to `tests/test_render_invoice.py`:

```python
from render_invoice import build_line_items


class TestBuildLineItems:
    def test_builds_and_sorts_line_items(self):
        harvest_data = {
            "Bob": {
                "Acme": [
                    {"date": "2026-04-02", "task": "Development", "hours": 7.0},
                ],
            },
            "Alice": {
                "Acme": [
                    {"date": "2026-04-01", "task": "Development", "hours": 3.5},
                    {"date": "2026-04-01", "task": "Meetings", "hours": 1.0},
                ],
            },
        }
        rate_card = {
            "rates": {
                "Alice": {"Development": 175.00, "Meetings": 150.00},
                "Bob": {"Development": 125.00},
            },
            "default_rate": None,
        }

        line_items, total = build_line_items(harvest_data, rate_card)

        assert line_items == [
            {"date": "04/01/26", "staff": "Alice", "task": "Development",
             "hours": 3.5, "rate": 175.00, "amount": 612.50},
            {"date": "04/01/26", "staff": "Alice", "task": "Meetings",
             "hours": 1.0, "rate": 150.00, "amount": 150.00},
            {"date": "04/02/26", "staff": "Bob", "task": "Development",
             "hours": 7.0, "rate": 125.00, "amount": 875.00},
        ]
        assert total == 1637.50

    def test_empty_harvest_data(self):
        line_items, total = build_line_items({}, {"rates": {}, "default_rate": None})
        assert line_items == []
        assert total == 0.0

    def test_missing_rate_raises(self):
        harvest_data = {
            "Alice": {
                "Acme": [
                    {"date": "2026-04-01", "task": "Unknown Task", "hours": 1.0},
                ],
            },
        }
        rate_card = {"rates": {"Alice": {"Development": 175.00}}, "default_rate": None}
        with pytest.raises(ValueError, match="No rate.*Unknown Task"):
            build_line_items(harvest_data, rate_card)

    def test_sort_by_date_then_staff(self):
        harvest_data = {
            "Zara": {
                "Acme": [
                    {"date": "2026-04-01", "task": "Development", "hours": 2.0},
                ],
            },
            "Alice": {
                "Acme": [
                    {"date": "2026-04-01", "task": "Development", "hours": 3.0},
                    {"date": "2026-04-02", "task": "Development", "hours": 1.0},
                ],
            },
        }
        rate_card = {
            "rates": {
                "Alice": {"Development": 100.00},
                "Zara": {"Development": 100.00},
            },
            "default_rate": None,
        }

        line_items, _ = build_line_items(harvest_data, rate_card)

        staff_order = [item["staff"] for item in line_items]
        assert staff_order == ["Alice", "Zara", "Alice"]
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `python3 -m pytest tests/test_render_invoice.py::TestBuildLineItems -v`
Expected: ImportError — `build_line_items` not yet defined.

- [ ] **Step 3: Implement build_line_items**

Add to `render_invoice.py`, after the existing functions:

```python
def _format_date_mmddyy(iso_date: str) -> str:
    """Convert '2026-04-01' to '04/01/26'."""
    year, month, day = iso_date.split("-")
    return f"{month}/{day}/{year[2:]}"


def build_line_items(harvest_data: dict, rate_card: dict) -> tuple[list[dict], float]:
    """Build sorted, priced line items from Harvest report data and a rate card.

    Returns (line_items, total).
    """
    raw_items = []
    for staff, clients in harvest_data.items():
        for _client, entries in clients.items():
            for entry in entries:
                rate = lookup_rate(rate_card, staff, entry["task"])
                amount = round(entry["hours"] * rate, 2)
                raw_items.append({
                    "sort_date": entry["date"],
                    "date": _format_date_mmddyy(entry["date"]),
                    "staff": staff,
                    "task": entry["task"],
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_render_invoice.py -v`
Expected: All 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add render_invoice.py tests/test_render_invoice.py
git commit -m "feat: add line item assembly from Harvest data and rate card"
```

---

### Task 4: Context assembly (TDD)

**Files:**
- Modify: `render_invoice.py`
- Modify: `tests/test_render_invoice.py`

- [ ] **Step 1: Write failing test for build_invoice_context**

Append to `tests/test_render_invoice.py`:

```python
from datetime import date

from render_invoice import build_invoice_context


class TestBuildInvoiceContext:
    def test_assembles_full_context(self):
        harvest_data = {
            "Alice": {
                "Acme": [
                    {"date": "2026-04-01", "task": "Development", "hours": 3.5},
                ],
            },
        }
        rate_card = {
            "rates": {"Alice": {"Development": 175.00}},
            "default_rate": None,
        }

        ctx = build_invoice_context(
            harvest_data=harvest_data,
            rate_card=rate_card,
            client_name="Acme Corp",
            client_address=["456 Oak Ave", "San Francisco, CA 94102"],
            invoice_number="INV-2026-001",
            invoice_date=date(2026, 4, 6),
        )

        assert ctx["company"]["name"] == "DVV Entertainment"
        assert ctx["company"]["address"] == ["PO Box 6317", "Alameda, CA 94501"]
        assert ctx["company"]["email"] == "accounting@dvvent.com"
        assert ctx["company"]["logo_path"].endswith("dvv-logo.svg")
        assert ctx["client"] == {
            "name": "Acme Corp",
            "address": ["456 Oak Ave", "San Francisco, CA 94102"],
        }
        assert ctx["invoice_number"] == "INV-2026-001"
        assert ctx["invoice_date"] == "04/06/26"
        assert ctx["terms"] == "Net 30"
        assert len(ctx["line_items"]) == 1
        assert ctx["line_items"][0]["amount"] == 612.50
        assert ctx["total"] == 612.50
        assert ctx["footer"] == "Thank you for your business."

    def test_custom_terms_and_footer(self):
        ctx = build_invoice_context(
            harvest_data={},
            rate_card={"rates": {}, "default_rate": None},
            client_name="Test",
            client_address=["123 St"],
            invoice_number="INV-001",
            invoice_date=date(2026, 1, 15),
            terms="Net 15",
            footer="Payment due on receipt.",
        )
        assert ctx["terms"] == "Net 15"
        assert ctx["footer"] == "Payment due on receipt."
        assert ctx["total"] == 0.0
        assert ctx["line_items"] == []
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `python3 -m pytest tests/test_render_invoice.py::TestBuildInvoiceContext -v`
Expected: ImportError — `build_invoice_context` not yet defined.

- [ ] **Step 3: Implement build_invoice_context**

Add to `render_invoice.py`:

```python
import os
from datetime import date


def build_invoice_context(
    harvest_data: dict,
    rate_card: dict,
    client_name: str,
    client_address: list[str],
    invoice_number: str,
    invoice_date: date,
    terms: str = "Net 30",
    footer: str = "Thank you for your business.",
) -> dict:
    """Assemble the full template context dict for an invoice."""
    line_items, total = build_line_items(harvest_data, rate_card)
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

Note: the `import os` and `from datetime import date` should be added to the imports at the top of the file.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_render_invoice.py -v`
Expected: All 11 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add render_invoice.py tests/test_render_invoice.py
git commit -m "feat: add invoice context assembly"
```

---

### Task 5: Jinja2 invoice template

**Files:**
- Create: `templates/invoice.html`

- [ ] **Step 1: Create the templates directory**

```bash
mkdir -p templates
```

- [ ] **Step 2: Write the Jinja2 template**

Create `templates/invoice.html`:

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;600;700&display=swap');
  @import url('https://fonts.googleapis.com/css2?family=Droid+Sans+Mono&display=swap');

  @page {
    size: letter portrait;
    margin: 0.75in;
  }

  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  body {
    font-family: 'Nunito', sans-serif;
    font-size: 11px;
    color: #333;
    line-height: 1.5;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 28px;
  }

  .header-left {
    display: flex;
    gap: 14px;
    align-items: flex-start;
  }

  .logo {
    width: 120px;
    height: auto;
  }

  .company-name {
    font-weight: 700;
    font-size: 11px;
    color: #201e20;
  }

  .company-detail {
    font-size: 8px;
    color: #777;
  }

  .header-right {
    text-align: right;
  }

  .invoice-label {
    font-size: 13px;
    font-weight: 300;
    color: #201e20;
    letter-spacing: 3px;
    margin-bottom: 8px;
  }

  .invoice-meta {
    font-size: 10px;
  }

  .invoice-meta .label {
    color: #999;
  }

  .invoice-meta .mono {
    font-family: 'Droid Sans Mono', monospace;
  }

  .bill-to {
    margin-bottom: 24px;
    padding: 14px 0;
    border-top: 1px solid #e5e5e5;
  }

  .bill-to-label {
    color: #999;
    font-size: 7px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 3px;
    font-weight: 600;
  }

  .client-name {
    font-weight: 700;
    font-size: 11px;
    color: #201e20;
  }

  .client-detail {
    font-size: 8px;
    color: #777;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 20px;
    font-size: 7.5px;
  }

  thead tr {
    border-bottom: 2px solid #201e20;
  }

  th {
    text-align: left;
    padding: 5px 6px;
    font-weight: 700;
    font-size: 7px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #555;
  }

  th.num {
    text-align: right;
    font-family: 'Droid Sans Mono', monospace;
  }

  td {
    padding: 4px 6px;
  }

  tbody tr {
    border-bottom: 1px solid #f0f0f0;
  }

  td.num {
    text-align: right;
    font-family: 'Droid Sans Mono', monospace;
  }

  .col-date  { width: 12%; }
  .col-staff { width: 28%; }
  .col-task  { width: 24%; }
  .col-hours { width: 10%; }
  .col-rate  { width: 12%; }
  .col-amount { width: 14%; }

  .total-row {
    display: flex;
    justify-content: flex-end;
  }

  .total-block {
    width: 220px;
  }

  .total-line {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-top: 2px solid #201e20;
    font-weight: 700;
    font-size: 14px;
    color: #201e20;
  }

  .total-amount {
    font-family: 'Droid Sans Mono', monospace;
  }

  .footer {
    margin-top: 40px;
    padding-top: 12px;
    border-top: 1px solid #e5e5e5;
    color: #aaa;
    font-size: 9px;
    text-align: center;
    font-style: italic;
  }
</style>
</head>
<body>

  <div class="header">
    <div class="header-left">
      <img class="logo" src="file://{{ company.logo_path }}" alt="{{ company.name }}">
      <div>
        <div class="company-name">{{ company.name }}</div>
        {% for line in company.address %}
        <div class="company-detail">{{ line }}</div>
        {% endfor %}
        <div class="company-detail">{{ company.email }}</div>
      </div>
    </div>
    <div class="header-right">
      <div class="invoice-label">INVOICE</div>
      <div class="invoice-meta"><span class="label">No:</span> <span class="mono">{{ invoice_number }}</span></div>
      <div class="invoice-meta"><span class="label">Date:</span> {{ invoice_date }}</div>
      <div class="invoice-meta"><span class="label">Terms:</span> {{ terms }}</div>
    </div>
  </div>

  <div class="bill-to">
    <div class="bill-to-label">Bill To</div>
    <div class="client-name">{{ client.name }}</div>
    {% for line in client.address %}
    <div class="client-detail">{{ line }}</div>
    {% endfor %}
  </div>

  <table>
    <thead>
      <tr>
        <th class="col-date">Date</th>
        <th class="col-staff">Staff</th>
        <th class="col-task">Task</th>
        <th class="col-hours num">Hours</th>
        <th class="col-rate num">Rate</th>
        <th class="col-amount num">Amount</th>
      </tr>
    </thead>
    <tbody>
      {% for item in line_items %}
      <tr>
        <td>{{ item.date }}</td>
        <td>{{ item.staff }}</td>
        <td>{{ item.task }}</td>
        <td class="num">{{ "%.2f"|format(item.hours) }}</td>
        <td class="num">{{ "$%,.2f"|format(item.rate) }}</td>
        <td class="num">{{ "$%,.2f"|format(item.amount) }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <div class="total-row">
    <div class="total-block">
      <div class="total-line">
        <span>Total</span>
        <span class="total-amount">{{ "$%,.2f"|format(total) }}</span>
      </div>
    </div>
  </div>

  {% if footer %}
  <div class="footer">{{ footer }}</div>
  {% endif %}

</body>
</html>
```

- [ ] **Step 3: Commit**

```bash
git add templates/invoice.html
git commit -m "feat: add Jinja2 invoice template with print CSS"
```

---

### Task 6: HTML rendering function (TDD)

**Files:**
- Modify: `render_invoice.py`
- Modify: `tests/test_render_invoice.py`

- [ ] **Step 1: Write failing test for render_invoice_html**

Append to `tests/test_render_invoice.py`:

```python
from render_invoice import render_invoice_html


class TestRenderInvoiceHtml:
    def test_renders_template_with_context(self):
        ctx = {
            "company": {
                "name": "DVV Entertainment",
                "address": ["PO Box 6317", "Alameda, CA 94501"],
                "email": "accounting@dvvent.com",
                "logo_path": "/tmp/logo.svg",
            },
            "client": {
                "name": "Acme Corp",
                "address": ["456 Oak Ave"],
            },
            "invoice_number": "INV-001",
            "invoice_date": "04/06/26",
            "terms": "Net 30",
            "line_items": [
                {"date": "04/01/26", "staff": "Alice", "task": "Dev",
                 "hours": 2.0, "rate": 100.00, "amount": 200.00},
            ],
            "total": 200.00,
            "footer": "Thanks!",
        }
        html = render_invoice_html(ctx)

        assert "DVV Entertainment" in html
        assert "Acme Corp" in html
        assert "INV-001" in html
        assert "Alice" in html
        assert "$200.00" in html
        assert "Thanks!" in html

    def test_empty_line_items(self):
        ctx = {
            "company": {
                "name": "DVV Entertainment",
                "address": [],
                "email": "test@test.com",
                "logo_path": "/tmp/logo.svg",
            },
            "client": {"name": "Test", "address": []},
            "invoice_number": "INV-001",
            "invoice_date": "01/01/26",
            "terms": "Net 30",
            "line_items": [],
            "total": 0.0,
            "footer": "",
        }
        html = render_invoice_html(ctx)

        assert "$0.00" in html
        assert "<tbody>" in html
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `python3 -m pytest tests/test_render_invoice.py::TestRenderInvoiceHtml -v`
Expected: ImportError — `render_invoice_html` not yet defined.

- [ ] **Step 3: Implement render_invoice_html**

Add to `render_invoice.py`:

```python
from jinja2 import Environment, FileSystemLoader


def render_invoice_html(context: dict) -> str:
    """Render the invoice template to an HTML string."""
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("invoice.html")
    return template.render(**context)
```

Note: add the `jinja2` import to the top of the file.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_render_invoice.py -v`
Expected: All 13 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add render_invoice.py tests/test_render_invoice.py
git commit -m "feat: add Jinja2 HTML rendering function"
```

---

### Task 7: PDF rendering function (TDD)

**Files:**
- Modify: `render_invoice.py`
- Modify: `tests/test_render_invoice.py`

- [ ] **Step 1: Write failing test for render_invoice_pdf**

Append to `tests/test_render_invoice.py`:

```python
from unittest.mock import patch, MagicMock

from render_invoice import render_invoice_pdf


class TestRenderInvoicePdf:
    @patch("render_invoice.weasyprint.HTML")
    def test_calls_weasyprint_and_writes_pdf(self, mock_html_cls, tmp_path):
        output_path = str(tmp_path / "invoice.pdf")
        html_string = "<html><body>test</body></html>"

        render_invoice_pdf(html_string, output_path)

        mock_html_cls.assert_called_once_with(string=html_string)
        mock_html_cls.return_value.write_pdf.assert_called_once_with(output_path)
```

- [ ] **Step 2: Run tests to verify new test fails**

Run: `python3 -m pytest tests/test_render_invoice.py::TestRenderInvoicePdf -v`
Expected: ImportError — `render_invoice_pdf` not yet defined.

- [ ] **Step 3: Implement render_invoice_pdf**

Add to `render_invoice.py`:

```python
import weasyprint


def render_invoice_pdf(html_string: str, output_path: str) -> None:
    """Convert an HTML string to a PDF file via WeasyPrint."""
    weasyprint.HTML(string=html_string).write_pdf(output_path)
```

Note: add the `weasyprint` import to the top of the file.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_render_invoice.py -v`
Expected: All 14 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add render_invoice.py tests/test_render_invoice.py
git commit -m "feat: add WeasyPrint PDF rendering function"
```

---

### Task 8: Example rate card

**Files:**
- Create: `rate_card.json`

- [ ] **Step 1: Create example rate card**

Create `rate_card.json`:

```json
{
    "rates": {
        "Alice Example": {
            "Development": 175.00,
            "Meetings": 175.00,
            "Code Review": 175.00
        },
        "Bob Example": {
            "Development": 150.00,
            "Meetings": 150.00,
            "Design": 140.00
        }
    },
    "default_rate": null
}
```

- [ ] **Step 2: Commit**

```bash
git add rate_card.json
git commit -m "feat: add example rate card"
```

---

### Task 9: CLI entry point

**Files:**
- Modify: `render_invoice.py`

- [ ] **Step 1: Add CLI main function**

Add to the bottom of `render_invoice.py`:

```python
import argparse

from harvest_reports import detailed_time_by_staff_client


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a PDF invoice from Harvest time data.")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--client-name", required=True, help="Client name for the invoice")
    parser.add_argument("--client-address", required=True, nargs="+",
                        help="Client address lines (e.g. '456 Oak Ave' 'City, ST 12345')")
    parser.add_argument("--invoice-number", required=True, help="Invoice number (e.g. INV-2026-042)")
    parser.add_argument("--invoice-date", required=True, help="Invoice date (YYYY-MM-DD)")
    parser.add_argument("--rate-card", default="rate_card.json", help="Path to rate card JSON")
    parser.add_argument("--output", default="invoice.pdf", help="Output PDF path")
    parser.add_argument("--terms", default="Net 30", help="Payment terms")
    parser.add_argument("--footer", default="Thank you for your business.",
                        help="Footer text")

    args = parser.parse_args()

    start_date = date.fromisoformat(args.start)
    end_date = date.fromisoformat(args.end)
    invoice_date = date.fromisoformat(args.invoice_date)

    rate_card = load_rate_card(args.rate_card)

    harvest_data = detailed_time_by_staff_client(start_date, end_date)

    context = build_invoice_context(
        harvest_data=harvest_data,
        rate_card=rate_card,
        client_name=args.client_name,
        client_address=args.client_address,
        invoice_number=args.invoice_number,
        invoice_date=invoice_date,
        terms=args.terms,
        footer=args.footer,
    )

    html = render_invoice_html(context)
    render_invoice_pdf(html, args.output)
    print(f"Invoice written to {args.output}")


if __name__ == "__main__":
    main()
```

Note: add the `argparse` import to the top of the file. The `from harvest_reports import` can also go at the top, but since it requires env vars at call time (not import time), top-level is fine.

- [ ] **Step 2: Verify the help text works**

Run: `python3 render_invoice.py --help`
Expected: Usage text showing all arguments.

- [ ] **Step 3: Commit**

```bash
git add render_invoice.py
git commit -m "feat: add CLI entry point for invoice generation"
```

---

### Task 10: End-to-end smoke test

**Files:**
- Modify: `tests/test_render_invoice.py`

- [ ] **Step 1: Write an integration test that renders a real PDF**

Append to `tests/test_render_invoice.py`:

```python
from render_invoice import render_invoice_html, render_invoice_pdf, build_invoice_context


class TestEndToEnd:
    def test_generates_pdf_file(self, tmp_path):
        harvest_data = {
            "Alice": {
                "Acme": [
                    {"date": "2026-04-01", "task": "Development", "hours": 6.0},
                    {"date": "2026-04-01", "task": "Meetings", "hours": 1.5},
                ],
            },
            "Bob": {
                "Acme": [
                    {"date": "2026-04-02", "task": "Development", "hours": 7.0},
                ],
            },
        }
        rate_card = {
            "rates": {
                "Alice": {"Development": 175.00, "Meetings": 150.00},
                "Bob": {"Development": 125.00},
            },
            "default_rate": None,
        }

        ctx = build_invoice_context(
            harvest_data=harvest_data,
            rate_card=rate_card,
            client_name="Acme Corp",
            client_address=["456 Oak Ave, Floor 3", "San Francisco, CA 94102"],
            invoice_number="INV-2026-042",
            invoice_date=date(2026, 4, 6),
        )

        html = render_invoice_html(ctx)
        output = str(tmp_path / "test-invoice.pdf")
        render_invoice_pdf(html, output)

        assert os.path.exists(output)
        assert os.path.getsize(output) > 0

        # PDF files start with %PDF
        with open(output, "rb") as f:
            assert f.read(4) == b"%PDF"
```

- [ ] **Step 2: Run the full test suite**

Run: `python3 -m pytest tests/test_render_invoice.py -v`
Expected: All 15 tests PASS. The end-to-end test will take a moment as WeasyPrint renders the actual PDF.

- [ ] **Step 3: Run all tests to check for regressions**

Run: `python3 -m pytest tests/ -v`
Expected: All tests across both test files PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_render_invoice.py
git commit -m "test: add end-to-end PDF generation smoke test"
```
