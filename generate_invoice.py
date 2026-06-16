"""Generate a PDF invoice from Harvest time data."""

import argparse
import json
import os
from datetime import date
from typing import Optional

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
    output_path: str,
    terms: Optional[str] = None,
    footer: Optional[str] = None,
) -> None:
    """Build invoice context and render to PDF.

    terms/footer are forwarded only when provided; when omitted they fall through
    to build_invoice_context's defaults, keeping a single source of truth for the
    default payment terms and footer text.
    """
    overrides = {}
    if terms is not None:
        overrides["terms"] = terms
    if footer is not None:
        overrides["footer"] = footer
    context = build_invoice_context(
        harvest_data=harvest_data,
        rate_card=rate_card,
        client_name=client_name,
        client_address=client_address,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        type_mappings=type_mappings,
        **overrides,
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
    parser.add_argument("--terms", help="Payment terms (defaults to the invoice's standard terms)")
    parser.add_argument("--footer", help="Footer text (defaults to the invoice's standard footer)")
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
