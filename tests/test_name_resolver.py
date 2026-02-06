"""Tests for openalex_tool_pkg.name_resolver module."""

import os
import pytest
from unittest.mock import patch, MagicMock
from openalex_tool_pkg.name_resolver import (
    is_abbreviated_name,
    detect_file_format,
    parse_author_line,
    get_tavily_api_key,
    extract_full_name_from_results,
    resolve_abbreviated_name,
)


class TestIsAbbreviatedName:
    def test_single_initial_with_period(self):
        assert is_abbreviated_name("E. Kelly") is True

    def test_single_initial_without_period(self):
        assert is_abbreviated_name("E Kelly") is True

    def test_full_name(self):
        assert is_abbreviated_name("Eugene Kelly") is False

    def test_multiple_initials(self):
        assert is_abbreviated_name("J. R. Smith") is True

    def test_empty_string(self):
        assert is_abbreviated_name("") is False

    def test_single_word(self):
        assert is_abbreviated_name("Kelly") is False

    def test_whitespace_only(self):
        assert is_abbreviated_name("   ") is False

    def test_full_first_with_middle_initial(self):
        assert is_abbreviated_name("Eugene R. Kelly") is False

    def test_initial_with_full_middle(self):
        assert is_abbreviated_name("E. Robert Kelly") is False


class TestDetectFileFormat:
    def test_tsv_header_detected(self):
        line = "College\tDepartment\tLastName\tFirstInitial\tRank"
        result = detect_file_format(line)
        assert result is not None
        assert "College" in result
        assert "LastName" in result

    def test_plain_text_returns_none(self):
        assert detect_file_format("Eugene Kelly") is None

    def test_tab_without_expected_headers(self):
        assert detect_file_format("foo\tbar\tbaz") is None

    def test_underscore_variant(self):
        line = "College\tDepartment\tLast_Name\tFirst_Name"
        result = detect_file_format(line)
        assert result is not None


class TestParseAuthorLine:
    def test_plain_text_line(self):
        result = parse_author_line("Eugene Kelly")
        assert result == {"name": "Eugene Kelly"}

    def test_plain_text_empty_line(self):
        assert parse_author_line("") is None
        assert parse_author_line("   ") is None

    def test_tsv_with_headers(self):
        headers = ["College", "Department", "LastName", "FirstInitial", "Rank"]
        line = "Natural Sciences\tChemistry\tBernstein\tB\tProfessor"
        result = parse_author_line(line, headers)
        assert result["name"] == "B. Bernstein"
        assert result["last_name"] == "Bernstein"
        assert result["first_initial"] == "B"
        assert result["department"] == "Chemistry"
        assert result["college"] == "Natural Sciences"

    def test_tsv_missing_lastname(self):
        headers = ["College", "Department", "LastName", "FirstInitial"]
        line = "Natural Sciences\tChemistry\t\tB"
        assert parse_author_line(line, headers) is None

    def test_tsv_no_first_initial(self):
        headers = ["College", "Department", "LastName", "FirstInitial"]
        line = "Natural Sciences\tChemistry\tSmith\t"
        result = parse_author_line(line, headers)
        assert result["name"] == "Smith"


class TestGetTavilyApiKey:
    def test_cli_key_wins(self):
        assert get_tavily_api_key("cli-key-123") == "cli-key-123"

    def test_env_var_used(self):
        with patch.dict(os.environ, {"TAVILY_API_KEY": "env-key-456"}):
            assert get_tavily_api_key(None) == "env-key-456"

    @patch("openalex_tool_pkg.name_resolver.get_tavily_api_key.__module__", "openalex_tool_pkg.name_resolver")
    def test_config_used(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove TAVILY_API_KEY from env if present
            env = os.environ.copy()
            env.pop("TAVILY_API_KEY", None)
            with patch.dict(os.environ, env, clear=True):
                with patch("openalex_tool_pkg.config_manager.get_tavily_api_key", return_value="config-key-789"):
                    result = get_tavily_api_key(None)
                    assert result == "config-key-789"

    def test_none_when_nothing_set(self):
        with patch.dict(os.environ, {}, clear=True):
            env = os.environ.copy()
            env.pop("TAVILY_API_KEY", None)
            with patch.dict(os.environ, env, clear=True):
                with patch("openalex_tool_pkg.config_manager.get_tavily_api_key", return_value=None):
                    assert get_tavily_api_key(None) is None


class TestExtractFullNameFromResults:
    def test_extracts_from_answer(self):
        response = {
            "answer": "Professor Eugene Kelly is a faculty member at Colorado State University.",
            "results": [],
        }
        result = extract_full_name_from_results(response, "Kelly")
        assert result == "Eugene Kelly"

    def test_extracts_from_result_content(self):
        response = {
            "answer": "",
            "results": [
                {
                    "title": "Faculty Profile",
                    "content": "Dr. Eugene Kelly specializes in philosophy.",
                    "url": "https://colostate.edu/profile",
                }
            ],
        }
        result = extract_full_name_from_results(response, "Kelly")
        assert result == "Eugene Kelly"

    def test_prefers_institutional_domain(self):
        response = {
            "answer": "",
            "results": [
                {
                    "title": "Michael Kelly - Other Univ",
                    "content": "Michael Kelly is a professor.",
                    "url": "https://other.edu/profile",
                },
                {
                    "title": "Eugene Kelly - CSU",
                    "content": "Eugene Kelly teaches philosophy.",
                    "url": "https://colostate.edu/profile",
                },
            ],
        }
        result = extract_full_name_from_results(response, "Kelly", "Colorado State University")
        assert result == "Eugene Kelly"

    def test_returns_none_on_no_match(self):
        response = {
            "answer": "No relevant information found.",
            "results": [],
        }
        assert extract_full_name_from_results(response, "Kelly") is None

    def test_handles_missing_answer(self):
        response = {"results": []}
        assert extract_full_name_from_results(response, "Kelly") is None

    def test_extracts_from_result_title(self):
        response = {
            "answer": "",
            "results": [
                {
                    "title": "Eugene Kelly | Department of Philosophy",
                    "content": "",
                    "url": "https://colostate.edu",
                }
            ],
        }
        result = extract_full_name_from_results(response, "Kelly")
        assert result == "Eugene Kelly"


class TestResolveAbbreviatedName:
    def test_non_abbreviated_passthrough(self):
        name, resolved = resolve_abbreviated_name("Eugene Kelly")
        assert name == "Eugene Kelly"
        assert resolved is False

    @patch.dict("sys.modules", {"tavily": None})
    def test_no_tavily_installed(self):
        # Simulate tavily not installed by making import fail
        import importlib
        with patch("builtins.__import__", side_effect=ImportError("No module named 'tavily'")):
            with pytest.warns(match="tavily-python not installed"):
                name, resolved = resolve_abbreviated_name(
                    "E. Kelly", tavily_api_key="test-key"
                )
            assert name == "E. Kelly"
            assert resolved is False

    def test_no_api_key_warns(self):
        with patch("openalex_tool_pkg.name_resolver.is_abbreviated_name", return_value=True):
            # Mock tavily import to succeed
            mock_tavily = MagicMock()
            with patch.dict("sys.modules", {"tavily": mock_tavily}):
                with pytest.warns(match="No Tavily API key"):
                    name, resolved = resolve_abbreviated_name("E. Kelly")
                assert name == "E. Kelly"
                assert resolved is False

    def test_successful_resolution(self):
        mock_tavily_module = MagicMock()
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "answer": "Eugene Kelly is a professor at Colorado State University.",
            "results": [],
        }
        mock_tavily_module.TavilyClient.return_value = mock_client

        with patch.dict("sys.modules", {"tavily": mock_tavily_module}):
            name, resolved = resolve_abbreviated_name(
                "E. Kelly",
                institution="Colorado State University",
                department="Philosophy",
                tavily_api_key="test-key",
            )
        assert name == "Eugene Kelly"
        assert resolved is True

    def test_failed_resolution_returns_original(self):
        mock_tavily_module = MagicMock()
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "answer": "No information found.",
            "results": [],
        }
        mock_tavily_module.TavilyClient.return_value = mock_client

        with patch.dict("sys.modules", {"tavily": mock_tavily_module}):
            name, resolved = resolve_abbreviated_name(
                "E. Kelly",
                tavily_api_key="test-key",
            )
        assert name == "E. Kelly"
        assert resolved is False

    def test_tavily_search_exception(self):
        mock_tavily_module = MagicMock()
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("API error")
        mock_tavily_module.TavilyClient.return_value = mock_client

        with patch.dict("sys.modules", {"tavily": mock_tavily_module}):
            name, resolved = resolve_abbreviated_name(
                "E. Kelly",
                tavily_api_key="test-key",
            )
        assert name == "E. Kelly"
        assert resolved is False
