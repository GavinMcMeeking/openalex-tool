"""Tests for openalex_tool_pkg.config_manager module."""

import json
import pytest
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path

from openalex_tool_pkg.config_manager import (
    load_config,
    save_config,
    get_email,
    set_email,
    get_config_path,
    DEFAULT_EMAIL,
    CONFIG_FILE,
)


class TestLoadConfig:
    @patch("openalex_tool_pkg.config_manager.CONFIG_FILE")
    def test_no_file_returns_default(self, mock_path):
        mock_path.exists.return_value = False
        config = load_config()
        assert config == {"email": DEFAULT_EMAIL}

    @patch("builtins.open", mock_open(read_data='{"email": "user@example.com"}'))
    @patch("openalex_tool_pkg.config_manager.CONFIG_FILE")
    def test_reads_existing_config(self, mock_path):
        mock_path.exists.return_value = True
        config = load_config()
        assert config["email"] == "user@example.com"

    @patch("builtins.open", mock_open(read_data="not json"))
    @patch("openalex_tool_pkg.config_manager.CONFIG_FILE")
    def test_corrupted_file_returns_default(self, mock_path):
        mock_path.exists.return_value = True
        config = load_config()
        assert config == {"email": DEFAULT_EMAIL}


class TestSaveConfig:
    @patch("openalex_tool_pkg.config_manager.get_config_dir")
    @patch("builtins.open", mock_open())
    def test_writes_config(self, mock_dir):
        save_config({"email": "test@example.com"})
        handle = open
        # Verify open was called with the config file path
        handle.assert_called()


class TestGetEmail:
    @patch("openalex_tool_pkg.config_manager.load_config")
    def test_returns_configured_email(self, mock_load):
        mock_load.return_value = {"email": "user@example.com"}
        assert get_email() == "user@example.com"

    @patch("openalex_tool_pkg.config_manager.load_config")
    def test_returns_default_when_missing(self, mock_load):
        mock_load.return_value = {}
        assert get_email() == DEFAULT_EMAIL


class TestSetEmail:
    @patch("openalex_tool_pkg.config_manager.save_config")
    @patch("openalex_tool_pkg.config_manager.load_config")
    def test_saves_email(self, mock_load, mock_save):
        mock_load.return_value = {}
        set_email("new@example.com")
        mock_save.assert_called_once_with({"email": "new@example.com"})


class TestGetConfigPath:
    def test_returns_string(self):
        result = get_config_path()
        assert isinstance(result, str)
        assert "config.json" in result
