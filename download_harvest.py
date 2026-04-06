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
