"""Tests for the comp_report module."""

import os
import pytest
from unittest.mock import patch

from openalex_tool_pkg.comp_report import (
    _normalize_header,
    parse_comp_report,
    get_unique_values,
    filter_rows,
    interactive_select,
    rows_to_author_entries,
    load_and_filter_comp_report,
)


# --- Fixtures ---

SAMPLE_CSV = """\
Unit Name,Department,Last Name,First Initial,Job Title,Contract,Appointment Type,FTE,Annual Salary,Extract Date
Veterinary Medicine,Clinical Sciences,Brown,M,Associate Professor,9-Month,Contract/Continuing,0.0001,12.8954,10-SEP-25
Natural Sciences,Chemistry,Bernstein,B,Professor,12-Month,Contract/Continuing,0.005,510.05,10-SEP-25
Natural Sciences,Chemistry,Bernstein,E,Professor,12-Month,Contract/Continuing,0.005,510.05,10-SEP-25
"Engineering,Walter Scott, Jr. (SCOE)",Atmospheric Science,Doesken,N,Research Associate III,12-Month,Temporary,0.01,1305.93,10-SEP-25
"Engineering,Walter Scott, Jr. (SCOE)",Mechanical Engineering,Farnell,C,Resch Sci/Scholar II,12-Month,Temporary,0.02,2401.78,10-SEP-25
"Engineering,Walter Scott, Jr. (SCOE)",Mechanical Engineering,Farnell,C,Resch Sci/Scholar II,12-Month,Temporary,0.02,2401.78,10-SEP-25
Liberal Arts,"School of Music, Theatre and Dance",Hardy,M,Instructor,9-Month,Contract/Continuing,0.0278,1370.262,10-SEP-25
Health and Human Sciences,School of Education,Hurtienne,M,Instructor,9-Month,Contract/Continuing,0.0125,625,10-SEP-25
"""


@pytest.fixture
def sample_csv_path(tmp_path):
    """Write the sample CSV to a temp file and return its path."""
    csv_file = tmp_path / "comp_report.csv"
    csv_file.write_text(SAMPLE_CSV)
    return str(csv_file)


@pytest.fixture
def sample_rows(sample_csv_path):
    """Return parsed rows from the sample CSV."""
    return parse_comp_report(sample_csv_path)


# --- TestParseCompReport ---


class TestParseCompReport:
    def test_valid_csv(self, sample_csv_path):
        rows = parse_comp_report(sample_csv_path)
        assert len(rows) == 8

    def test_quoted_commas_in_unit_name(self, sample_csv_path):
        rows = parse_comp_report(sample_csv_path)
        eng_rows = [r for r in rows if "Walter Scott" in r["Unit Name"]]
        assert len(eng_rows) == 3
        assert eng_rows[0]["Unit Name"] == "Engineering,Walter Scott, Jr. (SCOE)"

    def test_quoted_commas_in_department(self, sample_csv_path):
        rows = parse_comp_report(sample_csv_path)
        music_rows = [r for r in rows if "Music" in r["Department"]]
        assert len(music_rows) == 1
        assert music_rows[0]["Department"] == "School of Music, Theatre and Dance"

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_comp_report("/nonexistent/path/report.csv")

    def test_missing_columns(self, tmp_path):
        csv_file = tmp_path / "bad.csv"
        csv_file.write_text("Name,Rank\nFoo,Professor\n")
        with pytest.raises(ValueError, match="missing required columns"):
            parse_comp_report(str(csv_file))

    def test_empty_csv(self, tmp_path):
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")
        with pytest.raises(ValueError, match="is empty"):
            parse_comp_report(str(csv_file))

    def test_headers_only(self, tmp_path):
        csv_file = tmp_path / "headers_only.csv"
        csv_file.write_text(
            "Unit Name,Department,Last Name,First Initial,Job Title,Contract,Appointment Type,FTE,Annual Salary,Extract Date\n"
        )
        with pytest.raises(ValueError, match="contains no data rows"):
            parse_comp_report(str(csv_file))

    def test_row_fields(self, sample_rows):
        row = sample_rows[0]
        assert row["Last Name"] == "Brown"
        assert row["First Initial"] == "M"
        assert row["Department"] == "Clinical Sciences"
        assert row["Job Title"] == "Associate Professor"
        assert row["Unit Name"] == "Veterinary Medicine"

    def test_bom_handling(self, tmp_path):
        """CSV files exported from Excel often have a UTF-8 BOM prefix."""
        bom_csv = "\ufeff" + SAMPLE_CSV
        csv_file = tmp_path / "bom.csv"
        csv_file.write_text(bom_csv, encoding="utf-8")
        rows = parse_comp_report(str(csv_file))
        assert len(rows) == 8
        # First column header should not have BOM prefix
        assert "Unit Name" in rows[0]

    def test_no_space_column_names(self, tmp_path):
        """Some CSV exports use 'LastName' instead of 'Last Name'."""
        csv_content = (
            "Department,LastName,FirstInitial,Job Title,Contract\n"
            "Chemistry,Bernstein,B,Professor,12-Month\n"
            "Physics,Newton,I,Professor,12-Month\n"
        )
        csv_file = tmp_path / "nospace.csv"
        csv_file.write_text(csv_content)
        rows = parse_comp_report(str(csv_file))
        assert len(rows) == 2
        # Headers should be normalized to canonical names
        assert rows[0]["Last Name"] == "Bernstein"
        assert rows[0]["First Initial"] == "B"

    def test_missing_unit_name_column(self, tmp_path):
        """Unit Name is optional — not all comp report formats include it."""
        csv_content = (
            "Department,Last Name,First Initial,Job Title\n"
            "Chemistry,Bernstein,B,Professor\n"
        )
        csv_file = tmp_path / "no_unit.csv"
        csv_file.write_text(csv_content)
        rows = parse_comp_report(str(csv_file))
        assert len(rows) == 1
        assert rows[0]["Last Name"] == "Bernstein"
        # Unit Name should not be present
        assert "Unit Name" not in rows[0]

    def test_college_header_mapped_to_unit_name(self, tmp_path):
        """'College' column should be normalized to 'Unit Name'."""
        csv_content = (
            "College,Department,LastName,FirstInitial,Job Title\n"
            "Natural Sciences,Chemistry,Bernstein,B,Professor\n"
        )
        csv_file = tmp_path / "college.csv"
        csv_file.write_text(csv_content)
        rows = parse_comp_report(str(csv_file))
        assert len(rows) == 1
        assert rows[0]["Unit Name"] == "Natural Sciences"

    def test_bom_with_no_space_headers(self, tmp_path):
        """BOM + non-standard headers — the combo Katy encountered."""
        csv_content = (
            "\ufeffDepartment,LastName,FirstInitial,Job Title,Contract\n"
            "Chemistry,Bernstein,B,Professor,12-Month\n"
        )
        csv_file = tmp_path / "bom_nospace.csv"
        csv_file.write_text(csv_content, encoding="utf-8")
        rows = parse_comp_report(str(csv_file))
        assert len(rows) == 1
        assert rows[0]["Last Name"] == "Bernstein"
        assert rows[0]["First Initial"] == "B"


# --- TestNormalizeHeader ---


class TestNormalizeHeader:
    def test_canonical_names_unchanged(self):
        assert _normalize_header("Last Name") == "Last Name"
        assert _normalize_header("First Initial") == "First Initial"

    def test_no_space_variants(self):
        assert _normalize_header("LastName") == "Last Name"
        assert _normalize_header("FirstInitial") == "First Initial"
        assert _normalize_header("JobTitle") == "Job Title"
        assert _normalize_header("UnitName") == "Unit Name"

    def test_college_maps_to_unit_name(self):
        assert _normalize_header("College") == "Unit Name"
        assert _normalize_header("college") == "Unit Name"

    def test_case_insensitive(self):
        assert _normalize_header("LASTNAME") == "Last Name"
        assert _normalize_header("FIRSTINITIAL") == "First Initial"
        assert _normalize_header("jobtitle") == "Job Title"
        # Unknown headers are passed through as-is
        assert _normalize_header("firstname") == "firstname"

    def test_whitespace_stripped(self):
        assert _normalize_header("  Last Name  ") == "Last Name"
        assert _normalize_header(" LastName ") == "Last Name"

    def test_unknown_header_passed_through(self):
        assert _normalize_header("Contract") == "Contract"
        assert _normalize_header("Annual Salary") == "Annual Salary"


# --- TestGetUniqueValues ---


class TestGetUniqueValues:
    def test_unique_departments(self, sample_rows):
        depts = get_unique_values(sample_rows, "Department")
        assert "Chemistry" in depts
        assert "Atmospheric Science" in depts
        # Should be sorted
        assert depts == sorted(depts)

    def test_unique_job_titles(self, sample_rows):
        titles = get_unique_values(sample_rows, "Job Title")
        assert "Professor" in titles
        assert "Instructor" in titles
        # No duplicates
        assert len(titles) == len(set(titles))

    def test_empty_input(self):
        assert get_unique_values([], "Department") == []

    def test_no_duplicates(self, sample_rows):
        # Farnell,C appears twice — "Resch Sci/Scholar II" should appear once
        titles = get_unique_values(sample_rows, "Job Title")
        assert titles.count("Resch Sci/Scholar II") == 1


# --- TestFilterRows ---


class TestFilterRows:
    def test_department_filter(self, sample_rows):
        result = filter_rows(sample_rows, department="Chemistry")
        assert len(result) == 2
        assert all(r["Department"] == "Chemistry" for r in result)

    def test_job_title_filter(self, sample_rows):
        result = filter_rows(sample_rows, job_title="Professor")
        # "Associate Professor" and "Professor" both match
        assert len(result) == 3

    def test_case_insensitive(self, sample_rows):
        result = filter_rows(sample_rows, department="chemistry")
        assert len(result) == 2

    def test_substring_match(self, sample_rows):
        result = filter_rows(sample_rows, job_title="Resch")
        assert len(result) == 2  # Farnell,C duplicate rows

    def test_and_logic(self, sample_rows):
        result = filter_rows(sample_rows, department="Chemistry", job_title="Professor")
        assert len(result) == 2

    def test_no_matches(self, sample_rows):
        result = filter_rows(sample_rows, department="Nonexistent")
        assert len(result) == 0

    def test_no_filters(self, sample_rows):
        result = filter_rows(sample_rows)
        assert len(result) == len(sample_rows)


# --- TestInteractiveSelect ---


class TestInteractiveSelect:
    def test_valid_selection(self):
        with patch("builtins.input", return_value="2"):
            result = interactive_select(["Alpha", "Beta", "Gamma"], "test")
        assert result == "Beta"

    def test_empty_input_skips(self):
        with patch("builtins.input", return_value=""):
            result = interactive_select(["Alpha", "Beta"], "test")
        assert result is None

    def test_invalid_then_valid(self):
        with patch("builtins.input", side_effect=["abc", "1"]):
            result = interactive_select(["Alpha", "Beta"], "test")
        assert result == "Alpha"

    def test_out_of_range_then_valid(self):
        with patch("builtins.input", side_effect=["99", "2"]):
            result = interactive_select(["Alpha", "Beta"], "test")
        assert result == "Beta"

    def test_first_item(self):
        with patch("builtins.input", return_value="1"):
            result = interactive_select(["Only"], "test")
        assert result == "Only"


# --- TestRowsToAuthorEntries ---


class TestRowsToAuthorEntries:
    def test_output_format(self, sample_rows):
        entries = rows_to_author_entries(sample_rows)
        entry = next(e for e in entries if e["last_name"] == "Brown")
        assert entry["name"] == "M. Brown"
        assert entry["last_name"] == "Brown"
        assert entry["first_initial"] == "M"
        assert entry["department"] == "Clinical Sciences"
        assert entry["college"] == "Veterinary Medicine"

    def test_deduplication(self, sample_rows):
        entries = rows_to_author_entries(sample_rows)
        # Farnell,C in Mechanical Engineering appears twice in CSV
        farnell_c = [e for e in entries if e["last_name"] == "Farnell" and e["first_initial"] == "C"]
        assert len(farnell_c) == 1

    def test_different_initials_same_name(self, sample_rows):
        entries = rows_to_author_entries(sample_rows)
        # Bernstein B and Bernstein E should both be present
        bernsteins = [e for e in entries if e["last_name"] == "Bernstein"]
        assert len(bernsteins) == 2

    def test_college_from_unit_name(self, sample_rows):
        entries = rows_to_author_entries(sample_rows)
        doesken = next(e for e in entries if e["last_name"] == "Doesken")
        assert doesken["college"] == "Engineering,Walter Scott, Jr. (SCOE)"

    def test_name_format(self, sample_rows):
        entries = rows_to_author_entries(sample_rows)
        doesken = next(e for e in entries if e["last_name"] == "Doesken")
        assert doesken["name"] == "N. Doesken"

    def test_empty_rows(self):
        entries = rows_to_author_entries([])
        assert entries == []

    def test_missing_fields_skipped(self):
        rows = [{"Last Name": "", "First Initial": "A", "Department": "X", "Unit Name": "Y"}]
        entries = rows_to_author_entries(rows)
        assert entries == []

    def test_missing_unit_name_defaults_empty(self):
        """When Unit Name column is absent, college should default to empty string."""
        rows = [{"Last Name": "Smith", "First Initial": "J", "Department": "Biology"}]
        entries = rows_to_author_entries(rows)
        assert len(entries) == 1
        assert entries[0]["college"] == ""


# --- TestLoadAndFilterCompReport ---


class TestLoadAndFilterCompReport:
    def test_with_department_flag(self, sample_csv_path):
        entries = load_and_filter_comp_report(sample_csv_path, department="Chemistry")
        assert len(entries) == 2
        assert all(e["department"] == "Chemistry" for e in entries)

    def test_with_job_title_flag(self, sample_csv_path):
        entries = load_and_filter_comp_report(sample_csv_path, job_title="Instructor")
        assert len(entries) == 2

    def test_with_both_flags(self, sample_csv_path):
        entries = load_and_filter_comp_report(
            sample_csv_path, department="Chemistry", job_title="Professor"
        )
        assert len(entries) == 2

    def test_interactive_mode(self, sample_csv_path):
        with patch(
            "openalex_tool_pkg.comp_report.interactive_select",
            side_effect=["Chemistry", None],
        ):
            entries = load_and_filter_comp_report(sample_csv_path)
        assert len(entries) == 2

    def test_interactive_skip_both(self, sample_csv_path):
        with patch(
            "openalex_tool_pkg.comp_report.interactive_select",
            side_effect=[None, None],
        ):
            entries = load_and_filter_comp_report(sample_csv_path)
        # No filters = all unique authors
        assert len(entries) == 7  # 8 rows, minus 1 duplicate Farnell,C

    def test_no_matches_raises(self, sample_csv_path):
        with pytest.raises(ValueError, match="No rows match"):
            load_and_filter_comp_report(
                sample_csv_path, department="Nonexistent"
            )

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_and_filter_comp_report("/nonexistent/report.csv")
