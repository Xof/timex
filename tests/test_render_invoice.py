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
