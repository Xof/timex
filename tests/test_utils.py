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
