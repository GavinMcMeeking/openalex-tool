"""Tests for openalex_tool_pkg.config module."""

import pytest
from openalex_tool_pkg.config import (
    resolve_field_name,
    validate_fields,
    get_fields_to_select,
    get_default_fields,
    CORE_FIELDS,
    EXTENDED_FIELDS,
    ALL_FIELDS,
    FIELD_ALIASES,
)


class TestResolveFieldName:
    def test_core_field(self):
        assert resolve_field_name("title") == "title"

    def test_extended_field(self):
        assert resolve_field_name("cited_by_count") == "cited_by_count"

    def test_alias_resolves(self):
        assert resolve_field_name("citations") == "cited_by_count"
        assert resolve_field_name("date") == "publication_date"
        assert resolve_field_name("author") == "authors"
        assert resolve_field_name("journal") == "sources"

    def test_case_insensitive(self):
        assert resolve_field_name("Title") == "title"
        assert resolve_field_name("CITATIONS") == "cited_by_count"

    def test_strips_whitespace(self):
        assert resolve_field_name("  title  ") == "title"

    def test_unknown_field_raises(self):
        with pytest.raises(ValueError, match="Unknown field"):
            resolve_field_name("nonexistent_field")


class TestGetDefaultFields:
    def test_returns_core_fields(self):
        assert get_default_fields() == CORE_FIELDS

    def test_returns_copy(self):
        defaults = get_default_fields()
        defaults.append("extra")
        assert "extra" not in get_default_fields()


class TestValidateFields:
    def test_valid_fields(self):
        result = validate_fields(["title", "abstract", "doi"])
        assert result == ["title", "abstract", "doi"]

    def test_aliases_resolved(self):
        result = validate_fields(["citations", "date"])
        assert result == ["cited_by_count", "publication_date"]

    def test_unknown_field_raises(self):
        with pytest.raises(ValueError, match="Unknown field"):
            validate_fields(["title", "bogus"])

    def test_empty_list(self):
        assert validate_fields([]) == []


class TestGetFieldsToSelect:
    def test_defaults_when_no_args(self):
        result = get_fields_to_select()
        assert result == CORE_FIELDS

    def test_include_overrides_defaults(self):
        result = get_fields_to_select(include_fields=["title", "doi"])
        assert result == ["title", "doi"]

    def test_exclude_removes_from_defaults(self):
        result = get_fields_to_select(exclude_fields=["abstract"])
        assert "abstract" not in result
        assert "title" in result

    def test_include_and_exclude_combined(self):
        result = get_fields_to_select(
            include_fields=["title", "abstract", "doi"],
            exclude_fields=["abstract"],
        )
        assert result == ["title", "doi"]

    def test_alias_in_include(self):
        result = get_fields_to_select(include_fields=["citations"])
        assert result == ["cited_by_count"]

    def test_alias_in_exclude(self):
        result = get_fields_to_select(exclude_fields=["date"])
        assert "publication_date" not in result
