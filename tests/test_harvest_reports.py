import os
from datetime import date
from unittest.mock import patch, MagicMock

from harvest_reports import _harvest_get, detailed_time_by_staff_client


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

    @patch.dict(os.environ, {"HARVEST_ACCESS_TOKEN": "tok", "HARVEST_ACCOUNT_ID": "123"})
    @patch("harvest_reports.requests.get")
    def test_pagination(self, mock_get):
        page1 = _mock_response({
            "time_entries": [{"id": 1}],
            "links": {"next": "https://api.harvestapp.com/v2/time_entries?cursor=abc"},
        })
        page2 = _mock_response({
            "time_entries": [{"id": 2}],
            "links": {"next": None},
        })
        mock_get.side_effect = [page1, page2]

        result = _harvest_get("/v2/time_entries", {"from": "2026-04-01", "to": "2026-04-30"})

        assert result == [{"id": 1}, {"id": 2}]
        assert mock_get.call_count == 2

    @patch.dict(os.environ, {"HARVEST_ACCESS_TOKEN": "tok", "HARVEST_ACCOUNT_ID": "123"})
    @patch("harvest_reports.time.sleep")
    @patch("harvest_reports.requests.get")
    def test_rate_limit_retry(self, mock_get, mock_sleep):
        rate_limited = _mock_response({}, status_code=429, headers={"Retry-After": "5"})
        success = _mock_response({
            "time_entries": [{"id": 1}],
            "links": {"next": None},
        })
        mock_get.side_effect = [rate_limited, success]

        result = _harvest_get("/v2/time_entries", {})

        assert result == [{"id": 1}]
        mock_sleep.assert_called_once_with(5)

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_env_vars(self):
        import pytest as pt
        with pt.raises(ValueError, match="HARVEST_ACCESS_TOKEN"):
            _harvest_get("/v2/time_entries", {})


class TestDetailedTimeByStaffClient:
    @patch("harvest_reports._harvest_get")
    def test_groups_and_sums(self, mock_get):
        mock_get.return_value = [
            {
                "spent_date": "2026-04-01",
                "hours": 2.0,
                "user": {"id": 1, "name": "Alice"},
                "client": {"id": 10, "name": "Acme"},
                "task": {"id": 100, "name": "Development"},
            },
            {
                "spent_date": "2026-04-01",
                "hours": 1.5,
                "user": {"id": 1, "name": "Alice"},
                "client": {"id": 10, "name": "Acme"},
                "task": {"id": 100, "name": "Development"},
            },
            {
                "spent_date": "2026-04-01",
                "hours": 1.0,
                "user": {"id": 1, "name": "Alice"},
                "client": {"id": 10, "name": "Acme"},
                "task": {"id": 101, "name": "Meetings"},
            },
            {
                "spent_date": "2026-04-02",
                "hours": 4.0,
                "user": {"id": 2, "name": "Bob"},
                "client": {"id": 11, "name": "Globex"},
                "task": {"id": 100, "name": "Development"},
            },
        ]

        result = detailed_time_by_staff_client(date(2026, 4, 1), date(2026, 4, 30))

        assert result == {
            "Alice": {
                "Acme": [
                    {"date": "2026-04-01", "task": "Development", "hours": 3.5},
                    {"date": "2026-04-01", "task": "Meetings", "hours": 1.0},
                ],
            },
            "Bob": {
                "Globex": [
                    {"date": "2026-04-02", "task": "Development", "hours": 4.0},
                ],
            },
        }
        mock_get.assert_called_once_with(
            "/v2/time_entries", {"from": "2026-04-01", "to": "2026-04-30"}
        )

    @patch("harvest_reports._harvest_get")
    def test_empty(self, mock_get):
        mock_get.return_value = []
        result = detailed_time_by_staff_client(date(2026, 4, 1), date(2026, 4, 30))
        assert result == {}
