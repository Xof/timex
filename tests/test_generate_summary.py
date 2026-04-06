import os
import pytest
from datetime import date

from generate_summary import build_summary_rows, write_summary_tsv


class TestBuildSummaryRows:
    def test_basic_summary(self):
        hours_data = {
            "Alice": {
                "2026-04-01": {
                    "tasks": {"Development": 3.5, "Meetings": 1.0},
                    "total": 4.5,
                },
                "2026-04-02": {
                    "tasks": {"Development": 7.0},
                    "total": 7.0,
                },
            },
        }
        type_mappings = {"Development": "Engineering", "Meetings": "Admin"}

        rows = build_summary_rows(hours_data, type_mappings)

        expected = [
            ("Alice", "04/01/26", "Admin", 1.0),
            ("Alice", "04/01/26", "Engineering", 3.5),
            ("Alice", "04/02/26", "Engineering", 7.0),
            ("Alice", "", "Admin", 1.0),
            ("Alice", "", "Engineering", 10.5),
            ("Alice", "", "Total", 11.5),
        ]
        assert rows == expected

    def test_multiple_tasks_same_mapped_type(self):
        hours_data = {
            "Alice": {
                "2026-04-01": {
                    "tasks": {"Development": 3.0, "Code Review": 2.0},
                    "total": 5.0,
                },
            },
        }
        type_mappings = {"Development": "Engineering", "Code Review": "Engineering"}

        rows = build_summary_rows(hours_data, type_mappings)

        expected = [
            ("Alice", "04/01/26", "Engineering", 5.0),
            ("Alice", "", "Engineering", 5.0),
            ("Alice", "", "Total", 5.0),
        ]
        assert rows == expected

    def test_unmapped_task_passes_through(self):
        hours_data = {
            "Alice": {
                "2026-04-01": {
                    "tasks": {"Unusual": 2.0},
                    "total": 2.0,
                },
            },
        }
        type_mappings = {"Development": "Engineering"}

        rows = build_summary_rows(hours_data, type_mappings)

        expected = [
            ("Alice", "04/01/26", "Unusual", 2.0),
            ("Alice", "", "Unusual", 2.0),
            ("Alice", "", "Total", 2.0),
        ]
        assert rows == expected

    def test_multiple_staff_sorted(self):
        hours_data = {
            "Zara": {
                "2026-04-01": {"tasks": {"Development": 4.0}, "total": 4.0},
            },
            "Alice": {
                "2026-04-01": {"tasks": {"Development": 3.0}, "total": 3.0},
            },
        }
        type_mappings = {"Development": "Engineering"}

        rows = build_summary_rows(hours_data, type_mappings)

        staff_order = [r[0] for r in rows]
        assert staff_order == ["Alice", "Alice", "Alice", "Zara", "Zara", "Zara"]

    def test_empty_data(self):
        rows = build_summary_rows({}, {})
        assert rows == []


class TestWriteSummaryTsv:
    def test_writes_file(self, tmp_path):
        rows = [
            ("Alice", "04/01/26", "Engineering", 3.5),
            ("Alice", "", "Engineering", 3.5),
            ("Alice", "", "Total", 3.5),
        ]
        path = str(tmp_path / "summary.tsv")
        write_summary_tsv(rows, path)

        with open(path) as f:
            lines = f.readlines()

        assert lines[0] == "Staff\tDate\tType\tHours\n"
        assert lines[1] == "Alice\t04/01/26\tEngineering\t3.50\n"
        assert lines[2] == "Alice\t\tEngineering\t3.50\n"
        assert lines[3] == "Alice\t\tTotal\t3.50\n"
        assert len(lines) == 4
