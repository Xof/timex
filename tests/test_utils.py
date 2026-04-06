import json
import os
import pytest
from datetime import date
from unittest.mock import patch

from utils import load_env


class TestLoadEnv:
    def test_loads_from_dotenv_file(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("HARVEST_ACCESS_TOKEN=tok123\nHARVEST_ACCOUNT_ID=acc456\n")
        monkeypatch.delenv("HARVEST_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("HARVEST_ACCOUNT_ID", raising=False)

        load_env(str(tmp_path))

        assert os.environ["HARVEST_ACCESS_TOKEN"] == "tok123"
        assert os.environ["HARVEST_ACCOUNT_ID"] == "acc456"

    def test_env_vars_take_precedence_over_dotenv(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("HARVEST_ACCESS_TOKEN=fromfile\nHARVEST_ACCOUNT_ID=fromfile\n")
        monkeypatch.setenv("HARVEST_ACCESS_TOKEN", "fromenv")
        monkeypatch.setenv("HARVEST_ACCOUNT_ID", "fromenv")

        load_env(str(tmp_path))

        assert os.environ["HARVEST_ACCESS_TOKEN"] == "fromenv"
        assert os.environ["HARVEST_ACCOUNT_ID"] == "fromenv"

    def test_ignores_comments_and_blank_lines(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\n\nHARVEST_ACCESS_TOKEN=tok\n\nHARVEST_ACCOUNT_ID=acc\n")
        monkeypatch.delenv("HARVEST_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("HARVEST_ACCOUNT_ID", raising=False)

        load_env(str(tmp_path))

        assert os.environ["HARVEST_ACCESS_TOKEN"] == "tok"
        assert os.environ["HARVEST_ACCOUNT_ID"] == "acc"

    def test_no_dotenv_uses_existing_env_vars(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HARVEST_ACCESS_TOKEN", "tok")
        monkeypatch.setenv("HARVEST_ACCOUNT_ID", "acc")

        load_env(str(tmp_path))

        assert os.environ["HARVEST_ACCESS_TOKEN"] == "tok"
        assert os.environ["HARVEST_ACCOUNT_ID"] == "acc"

    def test_missing_token_raises(self, tmp_path, monkeypatch):
        monkeypatch.delenv("HARVEST_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("HARVEST_ACCOUNT_ID", raising=False)

        with pytest.raises(ValueError, match="HARVEST_ACCESS_TOKEN"):
            load_env(str(tmp_path))

    def test_missing_account_id_raises(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HARVEST_ACCESS_TOKEN", "tok")
        monkeypatch.delenv("HARVEST_ACCOUNT_ID", raising=False)

        with pytest.raises(ValueError, match="HARVEST_ACCOUNT_ID"):
            load_env(str(tmp_path))


from utils import previous_semimonth


class TestPreviousSemimonth:
    def test_day_in_first_half_returns_prev_month_second_half(self):
        start, end = previous_semimonth(date(2026, 4, 6))
        assert start == date(2026, 3, 16)
        assert end == date(2026, 3, 31)

    def test_day_on_15th_returns_prev_month_second_half(self):
        start, end = previous_semimonth(date(2026, 4, 15))
        assert start == date(2026, 3, 16)
        assert end == date(2026, 3, 31)

    def test_day_on_16th_returns_same_month_first_half(self):
        start, end = previous_semimonth(date(2026, 4, 16))
        assert start == date(2026, 4, 1)
        assert end == date(2026, 4, 15)

    def test_day_on_last_day_returns_same_month_first_half(self):
        start, end = previous_semimonth(date(2026, 4, 30))
        assert start == date(2026, 4, 1)
        assert end == date(2026, 4, 15)

    def test_january_first_half_wraps_to_december(self):
        start, end = previous_semimonth(date(2026, 1, 10))
        assert start == date(2025, 12, 16)
        assert end == date(2025, 12, 31)

    def test_february_second_half_handles_short_month(self):
        start, end = previous_semimonth(date(2026, 2, 28))
        assert start == date(2026, 2, 1)
        assert end == date(2026, 2, 15)

    def test_march_first_half_handles_feb_end(self):
        start, end = previous_semimonth(date(2026, 3, 5))
        assert start == date(2026, 2, 16)
        assert end == date(2026, 2, 28)

    def test_march_first_half_handles_feb_leap(self):
        start, end = previous_semimonth(date(2028, 3, 5))
        assert start == date(2028, 2, 16)
        assert end == date(2028, 2, 29)


from utils import output_dir


class TestOutputDir:
    def test_returns_formatted_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = output_dir(date(2026, 4, 1), date(2026, 4, 15))
        assert result == "output/20260401-20260415/"

    def test_creates_directory(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = output_dir(date(2026, 4, 1), date(2026, 4, 15))
        assert os.path.isdir(result)

    def test_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result1 = output_dir(date(2026, 4, 1), date(2026, 4, 15))
        result2 = output_dir(date(2026, 4, 1), date(2026, 4, 15))
        assert result1 == result2
        assert os.path.isdir(result1)


from utils import load_type_mappings, map_task_type


SAMPLE_MAPPINGS_JSON = [
    {"Development": "Engineering"},
    {"Code Review": "Engineering"},
    {"Meetings": "Admin"},
    {"Design": "Creative"},
]


class TestLoadTypeMappings:
    def test_loads_and_flattens(self, tmp_path):
        path = tmp_path / "mappings.json"
        path.write_text(json.dumps(SAMPLE_MAPPINGS_JSON))
        result = load_type_mappings(str(path))
        assert result == {
            "Development": "Engineering",
            "Code Review": "Engineering",
            "Meetings": "Admin",
            "Design": "Creative",
        }

    def test_empty_list(self, tmp_path):
        path = tmp_path / "mappings.json"
        path.write_text("[]")
        result = load_type_mappings(str(path))
        assert result == {}

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_type_mappings("/nonexistent/mappings.json")


class TestMapTaskType:
    def test_mapped_task(self):
        mappings = {"Development": "Engineering"}
        assert map_task_type("Development", mappings) == "Engineering"

    def test_unmapped_task_passes_through(self):
        mappings = {"Development": "Engineering"}
        assert map_task_type("Unknown Task", mappings) == "Unknown Task"

    def test_empty_mappings(self):
        assert map_task_type("Development", {}) == "Development"
