"""Invoice rendering pipeline: Harvest data + rate card → PDF."""

import json
import os
import sys
from datetime import date
from typing import Optional

# WeasyPrint loads Pango/Cairo/GObject through cffi's dlopen using bare library
# names (e.g. "libgobject-2.0-0"). On macOS the dynamic loader only searches the
# dyld cache and /usr/lib — never package-manager prefixes such as MacPorts'
# /opt/local/lib or Homebrew's /opt/homebrew/lib — so the import fails with an
# opaque OSError even when the libraries are installed. The search path must be
# extended BEFORE importing weasyprint, because the dlopen happens at import
# time; macOS re-reads DYLD_FALLBACK_LIBRARY_PATH for explicit dlopen() calls,
# so setting it here (rather than only in the shell) is enough.
_NATIVE_LIB_PREFIXES = ("/opt/local/lib", "/opt/homebrew/lib", "/usr/local/lib")


def _ensure_native_lib_path(prefixes=_NATIVE_LIB_PREFIXES):
    """Add known macOS native-library prefixes to DYLD_FALLBACK_LIBRARY_PATH.

    No-op off macOS and for prefixes that don't exist on disk; preserves any
    paths already present so a user-provided value is never clobbered.
    """
    if sys.platform != "darwin":
        return
    existing = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
    parts = existing.split(os.pathsep) if existing else []
    for prefix in prefixes:
        if os.path.isdir(prefix) and prefix not in parts:
            parts.append(prefix)
    if parts:
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = os.pathsep.join(parts)


_ensure_native_lib_path()

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
                    "notes": entry.get("notes", ""),
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
    type_mappings: dict = None,
) -> dict:
    """Assemble the full template context dict for an invoice."""
    line_items, total = build_line_items(harvest_data, rate_card, type_mappings)
    total_hours = round(sum(item["hours"] for item in line_items), 2) if line_items else 0.0
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
        "total_hours": total_hours,
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
    # When the native-library import failed, weasyprint is a stub with HTML=None.
    # Fail with an actionable message here instead of letting the call below blow
    # up as "TypeError: 'NoneType' object is not callable" deep in the stack.
    if weasyprint.HTML is None:
        raise RuntimeError(
            "WeasyPrint's native libraries (Pango/Cairo/GObject) could not be "
            "loaded, so PDF rendering is unavailable. On macOS install them with "
            "your package manager (MacPorts: `sudo port install pango cairo`; "
            "Homebrew: `brew install pango`) and ensure the library directory "
            "(e.g. /opt/local/lib or /opt/homebrew/lib) exists. See "
            "https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation"
        )
    weasyprint.HTML(string=html_string).write_pdf(output_path)


