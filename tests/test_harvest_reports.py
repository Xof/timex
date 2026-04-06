import os
from datetime import date
from unittest.mock import patch, MagicMock

from harvest_reports import _harvest_get


def _mock_response(json_data, status_code=200, headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400 and status_code != 429:
        from requests.exceptions import HTTPError
        resp.raise_for_status.side_effect = HTTPError(response=resp)
    return resp


class TestHarvestGet:
    @patch.dict(os.environ, {"HARVEST_ACCESS_TOKEN": "tok", "HARVEST_ACCOUNT_ID": "123"})
    @patch("harvest_reports.requests.get")
    def test_single_page(self, mock_get):
        mock_get.return_value = _mock_response({
            "time_entries": [
                {"id": 1, "hours": 2.0},
                {"id": 2, "hours": 3.0},
            ],
            "links": {"next": None},
        })

        result = _harvest_get("/v2/time_entries", {"from": "2026-04-01", "to": "2026-04-30"})

        assert result == [{"id": 1, "hours": 2.0}, {"id": 2, "hours": 3.0}]
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == "https://api.harvestapp.com/v2/time_entries"
        assert kwargs["headers"]["Authorization"] == "Bearer tok"
        assert kwargs["headers"]["Harvest-Account-Id"] == "123"
        assert "User-Agent" in kwargs["headers"]
