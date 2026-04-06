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
            day_by_type = defaultdict(float)
            for task, hours in day_data["tasks"].items():
                mapped = map_task_type(task, type_mappings)
                day_by_type[mapped] += hours

            formatted_date = _format_date_mmddyy(iso_date)
            for mapped_type in sorted(day_by_type.keys()):
                hours = round(day_by_type[mapped_type], 2)
                rows.append((staff, formatted_date, mapped_type, hours))
                grand_totals[mapped_type] += hours

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
