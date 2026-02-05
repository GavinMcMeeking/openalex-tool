"""Tests for openalex_tool_pkg.openalex_client module."""

import pytest
from unittest.mock import patch, MagicMock
from openalex_tool_pkg.openalex_client import (
    normalize_author_id,
    build_query_params,
    make_request,
    OpenAlexAPIError,
    RateLimitError,
    BASE_URL,
    DEFAULT_PER_PAGE,
    MAX_PER_PAGE,
)


class TestNormalizeAuthorId:
    def test_openalex_id(self):
        assert normalize_author_id("A1234567890") == "A1234567890"

    def test_orcid_bare(self):
        result = normalize_author_id("0000-0002-1825-0097")
        assert result == "https://orcid.org/0000-0002-1825-0097"

    def test_orcid_url(self):
        result = normalize_author_id("https://orcid.org/0000-0002-1825-0097")
        assert result == "https://orcid.org/0000-0002-1825-0097"

    def test_strips_whitespace(self):
        assert normalize_author_id("  A1234567890  ") == "A1234567890"

    def test_passthrough_unknown(self):
        assert normalize_author_id("something_else") == "something_else"


class TestBuildQueryParams:
    def test_search_only(self):
        params = build_query_params(search="machine learning")
        assert params["search"] == "machine learning"
        assert params["per_page"] == DEFAULT_PER_PAGE
        assert params["page"] == 1

    def test_email_added(self):
        params = build_query_params(search="test", email="me@example.com")
        assert params["mailto"] == "me@example.com"

    def test_no_email_when_none(self):
        params = build_query_params(search="test")
        assert "mailto" not in params

    def test_author_id_filter(self):
        params = build_query_params(author_id="A123")
        assert "authorships.author.id:https://openalex.org/A123" in params["filter"]

    def test_multiple_author_ids_or(self):
        params = build_query_params(author_ids=["A1", "A2"])
        # Should use pipe separator for OR
        assert "|" in params["filter"]

    def test_per_page_capped(self):
        params = build_query_params(search="test", per_page=999)
        assert params["per_page"] == MAX_PER_PAGE

    def test_sort_param(self):
        params = build_query_params(search="test", sort="cited_by_count:desc")
        assert params["sort"] == "cited_by_count:desc"

    @patch("openalex_tool_pkg.openalex_client.lookup_institution_id")
    def test_institution_filter(self, mock_lookup):
        mock_lookup.return_value = "https://openalex.org/I123"
        params = build_query_params(institution="MIT")
        assert "authorships.institutions.id:https://openalex.org/I123" in params["filter"]

    @patch("openalex_tool_pkg.openalex_client.lookup_institution_id")
    def test_institution_not_found_raises(self, mock_lookup):
        mock_lookup.return_value = None
        with pytest.raises(ValueError, match="not found"):
            build_query_params(institution="Nonexistent University")


class TestMakeRequest:
    @patch("openalex_tool_pkg.openalex_client.requests.get")
    def test_successful_request(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"id": "W1"}]}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = make_request("https://api.openalex.org/works", {"search": "test"})
        assert result == {"results": [{"id": "W1"}]}

    @patch("openalex_tool_pkg.openalex_client.requests.get")
    def test_rate_limit_raises(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "1"}
        mock_get.return_value = mock_response

        with pytest.raises(RateLimitError):
            make_request("https://api.openalex.org/works", {}, max_retries=1)

    @patch("openalex_tool_pkg.openalex_client.requests.get")
    def test_api_error_raises(self, mock_get):
        import requests as req

        mock_get.side_effect = req.exceptions.ConnectionError("fail")

        with pytest.raises(OpenAlexAPIError):
            make_request("https://api.openalex.org/works", {}, max_retries=1)
