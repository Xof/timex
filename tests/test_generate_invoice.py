import json
import os
import pytest
from datetime import date
from unittest.mock import patch

from generate_invoice import load_client_info, filter_by_client, build_and_render


class TestLoadClientInfo:
    def test_loads_client_address(self, tmp_path):
        path = tmp_path / "clients.json"
        path.write_text(json.dumps({
            "Acme": {"address": ["123 St", "City, ST 12345"]}
        }))
        result = load_client_info(str(path), "Acme")
        assert result == ["123 St", "City, ST 12345"]

    def test_missing_client_raises(self, tmp_path):
        path = tmp_path / "clients.json"
        path.write_text(json.dumps({"Acme": {"address": ["123 St"]}}))
        with pytest.raises(ValueError, match="Unknown.*client.*did you mean.*Acme"):
            load_client_info(str(path), "Nonexistent")


class TestFilterByClient:
    def test_filters_to_single_client(self):
        harvest_data = {
            "Alice": {
                "Acme": [{"date": "2026-04-01", "task": "Dev", "hours": 3.0}],
                "Globex": [{"date": "2026-04-01", "task": "Dev", "hours": 2.0}],
            },
            "Bob": {
                "Acme": [{"date": "2026-04-02", "task": "Dev", "hours": 5.0}],
            },
        }
        result = filter_by_client(harvest_data, "Acme")
        assert result == {
            "Alice": {
                "Acme": [{"date": "2026-04-01", "task": "Dev", "hours": 3.0}],
            },
            "Bob": {
                "Acme": [{"date": "2026-04-02", "task": "Dev", "hours": 5.0}],
            },
        }

    def test_filters_out_staff_with_no_client_entries(self):
        harvest_data = {
            "Alice": {
                "Globex": [{"date": "2026-04-01", "task": "Dev", "hours": 3.0}],
            },
        }
        result = filter_by_client(harvest_data, "Acme")
        assert result == {}

    def test_empty_data(self):
        result = filter_by_client({}, "Acme")
        assert result == {}


class TestBuildAndRender:
    @patch("generate_invoice.render_invoice_pdf")
    def test_produces_pdf(self, mock_pdf, tmp_path):
        harvest_data = {
            "Alice": {
                "Acme": [
                    {"date": "2026-04-01", "task": "Development", "hours": 4.0},
                ],
            },
        }
        rate_card = {
            "rates": {"Alice": {"Engineering": 175.00}},
            "default_rate": None,
        }
        type_mappings = {"Development": "Engineering"}
        output_path = str(tmp_path / "INV-001.pdf")

        build_and_render(
            harvest_data=harvest_data,
            rate_card=rate_card,
            type_mappings=type_mappings,
            client_name="Acme Corp",
            client_address=["123 St"],
            invoice_number="INV-001",
            invoice_date=date(2026, 4, 6),
            terms="Net 30",
            footer="Thanks!",
            output_path=output_path,
        )

        mock_pdf.assert_called_once()
        call_args = mock_pdf.call_args
        assert call_args[0][1] == output_path
        html = call_args[0][0]
        assert "Acme Corp" in html
        assert "INV-001" in html
