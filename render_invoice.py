"""Invoice rendering pipeline: Harvest data + rate card → PDF."""

import argparse
import json
import os
from datetime import date
from typing import Optional

try:
    import weasyprint
except (ImportError, OSError):
    import types as _types
    weasyprint = _types.SimpleNamespace(HTML=None)  # type: ignore[assignment]

from jinja2 import Environment, FileSystemLoader

from utils import map_task_type


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


def _format_date_mmddyy(iso_date: str) -> str:
    """Convert '2026-04-01' to '04/01/26'."""
    year, month, day = iso_date.split("-")
    return f"{month}/{day}/{year[2:]}"


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

    line_items = [{k: v for k, v in item.items() if k != "sort_date"} for item in raw_items]
    total = round(sum(item["amount"] for item in line_items), 2) if line_items else 0.0
    return line_items, total


def build_invoice_context(
    harvest_data: dict,
    rate_card: dict,
    client_name: str,
    client_address: list,
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


def render_invoice_html(context: dict) -> str:
    """Render the invoice template to an HTML string."""
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("invoice.html")
    return template.render(**context)


def render_invoice_pdf(html_string: str, output_path: str) -> None:
    """Convert an HTML string to a PDF file via WeasyPrint."""
    weasyprint.HTML(string=html_string).write_pdf(output_path)


def main() -> None:
    from harvest_reports import detailed_time_by_staff_client

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
