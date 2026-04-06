import json
import os
import pytest

from render_invoice import load_rate_card, lookup_rate, build_line_items


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
