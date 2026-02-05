"""Tests for openalex_tool_pkg.formatter module."""

import pytest
from openalex_tool_pkg.formatter import (
    reconstruct_abstract_from_inverted_index,
    extract_authors,
    extract_institutions,
    extract_concepts,
    extract_keywords,
    extract_source,
    format_work,
)


class TestReconstructAbstract:
    def test_simple_reconstruction(self):
        inverted_index = {"Hello": [0], "world": [1]}
        assert reconstruct_abstract_from_inverted_index(inverted_index) == "Hello world"

    def test_word_at_multiple_positions(self):
        inverted_index = {"the": [0, 2], "cat": [1], "dog": [3]}
        result = reconstruct_abstract_from_inverted_index(inverted_index)
        assert result == "the cat the dog"

    def test_empty_index(self):
        assert reconstruct_abstract_from_inverted_index({}) == ""

    def test_none_index(self):
        assert reconstruct_abstract_from_inverted_index(None) == ""

    def test_single_word(self):
        inverted_index = {"Abstract": [0]}
        assert reconstruct_abstract_from_inverted_index(inverted_index) == "Abstract"

    def test_realistic_abstract(self):
        inverted_index = {
            "Despite": [0],
            "growing": [1],
            "interest": [2],
            "in": [3],
            "machine": [4],
            "learning,": [5],
            "challenges": [6],
            "remain.": [7],
        }
        result = reconstruct_abstract_from_inverted_index(inverted_index)
        assert result == "Despite growing interest in machine learning, challenges remain."


class TestExtractAuthors:
    def _make_authorship(self, author_id, name, orcid=None, position="first"):
        return {
            "author": {
                "id": author_id,
                "display_name": name,
                "orcid": orcid or "",
            },
            "author_position": position,
        }

    def test_first_author_only(self):
        authorships = [
            self._make_authorship("A1", "Alice", position="first"),
            self._make_authorship("A2", "Bob", position="middle"),
        ]
        result = extract_authors(authorships)
        assert len(result) == 1
        assert result[0]["name"] == "Alice"
        assert result[0]["id"] == "A1"
        assert result[0]["position"] == "first"

    def test_searched_author_returned(self):
        authorships = [
            self._make_authorship("A1", "Alice", position="first"),
            self._make_authorship("A2", "Bob", position="middle"),
        ]
        result = extract_authors(authorships, searched_author_ids=["A2"])
        assert len(result) == 1
        assert result[0]["name"] == "Bob"

    def test_empty_authorships(self):
        assert extract_authors([]) == []
        assert extract_authors(None) == []

    def test_searched_author_not_present(self):
        authorships = [
            self._make_authorship("A1", "Alice", position="first"),
        ]
        result = extract_authors(authorships, searched_author_ids=["A999"])
        assert result == []


class TestExtractInstitutions:
    def test_basic_extraction(self):
        authorships = [
            {
                "institutions": [
                    {"display_name": "MIT"},
                    {"display_name": "Stanford"},
                ]
            }
        ]
        result = extract_institutions(authorships)
        assert result == ["MIT", "Stanford"]

    def test_deduplication(self):
        authorships = [
            {"institutions": [{"display_name": "MIT"}]},
            {"institutions": [{"display_name": "MIT"}]},
        ]
        result = extract_institutions(authorships)
        assert result == ["MIT"]

    def test_empty(self):
        assert extract_institutions([]) == []
        assert extract_institutions(None) == []

    def test_missing_display_name(self):
        authorships = [{"institutions": [{"id": "I123"}]}]
        result = extract_institutions(authorships)
        assert result == []


class TestExtractConcepts:
    def test_basic_extraction(self):
        concepts = [
            {"id": "C1", "display_name": "Machine Learning", "score": 0.95},
            {"id": "C2", "display_name": "AI", "score": 0.80},
        ]
        result = extract_concepts(concepts)
        assert len(result) == 2
        assert result[0]["name"] == "Machine Learning"
        assert result[0]["score"] == 0.95

    def test_empty(self):
        assert extract_concepts([]) == []
        assert extract_concepts(None) == []


class TestExtractKeywords:
    def test_basic_extraction(self):
        keywords = [
            {"display_name": "neural networks"},
            {"display_name": "deep learning"},
        ]
        result = extract_keywords(keywords)
        assert result == ["neural networks", "deep learning"]

    def test_skips_empty_names(self):
        keywords = [
            {"display_name": "valid"},
            {"display_name": ""},
            {"other_field": "no name"},
        ]
        result = extract_keywords(keywords)
        assert result == ["valid"]

    def test_empty(self):
        assert extract_keywords([]) == []
        assert extract_keywords(None) == []


class TestExtractSource:
    def test_basic_extraction(self):
        primary_location = {
            "source": {
                "id": "S1",
                "display_name": "Nature",
                "issn_l": "0028-0836",
                "type": "journal",
            }
        }
        result = extract_source(primary_location)
        assert result["name"] == "Nature"
        assert result["issn"] == "0028-0836"
        assert result["type"] == "journal"

    def test_none_location(self):
        assert extract_source(None) is None

    def test_no_source(self):
        assert extract_source({}) is None
        assert extract_source({"source": None}) is None


class TestFormatWork:
    def _make_work(self):
        return {
            "id": "W123",
            "title": "Test Paper",
            "doi": "https://doi.org/10.1234/test",
            "type": "article",
            "publication_date": "2023-06-15",
            "abstract_inverted_index": {"Hello": [0], "world": [1]},
            "authorships": [
                {
                    "author": {
                        "id": "A1",
                        "display_name": "Alice",
                        "orcid": "",
                    },
                    "author_position": "first",
                    "institutions": [{"display_name": "MIT"}],
                }
            ],
            "concepts": [{"id": "C1", "display_name": "ML", "score": 0.9}],
            "keywords": [{"display_name": "deep learning"}],
            "primary_location": {
                "source": {
                    "id": "S1",
                    "display_name": "Nature",
                    "issn_l": "0028-0836",
                    "type": "journal",
                }
            },
            "cited_by_count": 42,
        }

    def test_core_fields(self):
        work = self._make_work()
        result = format_work(work, ["id", "title", "doi"])
        assert result["id"] == "W123"
        assert result["title"] == "Test Paper"
        assert result["doi"] == "https://doi.org/10.1234/test"

    def test_abstract_from_inverted_index(self):
        work = self._make_work()
        result = format_work(work, ["abstract"])
        assert result["abstract"] == "Hello world"

    def test_abstract_direct(self):
        work = self._make_work()
        work["abstract"] = "Direct abstract"
        result = format_work(work, ["abstract"])
        assert result["abstract"] == "Direct abstract"

    def test_authors_extraction(self):
        work = self._make_work()
        result = format_work(work, ["authors"])
        assert len(result["authors"]) == 1
        assert result["authors"][0]["name"] == "Alice"

    def test_concepts_extraction(self):
        work = self._make_work()
        result = format_work(work, ["concepts"])
        assert result["concepts"][0]["name"] == "ML"

    def test_keywords_extraction(self):
        work = self._make_work()
        result = format_work(work, ["keywords"])
        assert result["keywords"] == ["deep learning"]

    def test_sources_extraction(self):
        work = self._make_work()
        result = format_work(work, ["sources"])
        assert result["source"]["name"] == "Nature"

    def test_institutions_extraction(self):
        work = self._make_work()
        result = format_work(work, ["institutions"])
        assert result["institutions"] == ["MIT"]

    def test_missing_field_returns_none(self):
        work = self._make_work()
        result = format_work(work, ["language"])
        assert result["language"] is None

    def test_publisher_extraction(self):
        work = self._make_work()
        result = format_work(work, ["publisher"])
        assert result["publisher"] == "Nature"
