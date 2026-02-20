"""
Compensation report CSV ingestion module.

Parses CSU compensation report CSV files, provides interactive filtering
by department and job title, and converts rows to author entries compatible
with the Tavily + OpenAlex pipeline.
"""

import csv
import sys
from typing import Dict, List, Optional


REQUIRED_COLUMNS = {"Last Name", "First Initial", "Department", "Job Title"}

# Map common column name variants to canonical names
_HEADER_ALIASES = {
    "lastname": "Last Name",
    "last name": "Last Name",
    "firstinitial": "First Initial",
    "first initial": "First Initial",
    "jobtitle": "Job Title",
    "job title": "Job Title",
    "department": "Department",
    "unitname": "Unit Name",
    "unit name": "Unit Name",
    "college": "Unit Name",
}


def _normalize_header(header: str) -> str:
    """Normalize a CSV header to its canonical name."""
    return _HEADER_ALIASES.get(header.strip().lower(), header.strip())


def parse_comp_report(file_path: str) -> List[Dict[str, str]]:
    """
    Parse a CSU compensation report CSV file.

    Uses csv.DictReader to handle quoted fields with commas (e.g.,
    'Engineering,Walter Scott, Jr. (SCOE)').

    Args:
        file_path: Path to the CSV file

    Returns:
        List of row dicts keyed by column header

    Raises:
        FileNotFoundError: If the file does not exist
        ValueError: If required columns are missing or file is empty
    """
    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSV file '{file_path}' is empty")

        # Normalize column headers to canonical names
        canonical_names = [_normalize_header(h) for h in reader.fieldnames]

        missing = REQUIRED_COLUMNS - set(canonical_names)
        if missing:
            raise ValueError(
                f"CSV file missing required columns: {', '.join(sorted(missing))}"
            )

        # Re-key each row using normalized headers
        rows = []
        for raw_row in reader:
            row = {}
            for orig_key, canon_key in zip(reader.fieldnames, canonical_names):
                row[canon_key] = raw_row[orig_key]
            rows.append(row)

    if not rows:
        raise ValueError(f"CSV file '{file_path}' contains no data rows")

    return rows


def get_unique_values(rows: List[Dict[str, str]], column: str) -> List[str]:
    """
    Return sorted unique non-empty values for a column.

    Args:
        rows: List of row dicts from parse_comp_report
        column: Column name to extract unique values from

    Returns:
        Sorted list of unique non-empty string values
    """
    values = set()
    for row in rows:
        val = row.get(column, "").strip()
        if val:
            values.add(val)
    return sorted(values)


def filter_rows(
    rows: List[Dict[str, str]],
    department: Optional[str] = None,
    job_title: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Filter rows by department and/or job title.

    Uses case-insensitive substring matching. When both filters are provided,
    AND logic is applied (both must match).

    Args:
        rows: List of row dicts
        department: Department substring filter, or None to skip
        job_title: Job title substring filter, or None to skip

    Returns:
        Filtered list of row dicts
    """
    result = rows
    if department:
        dept_lower = department.lower()
        result = [r for r in result if dept_lower in r.get("Department", "").lower()]
    if job_title:
        title_lower = job_title.lower()
        result = [r for r in result if title_lower in r.get("Job Title", "").lower()]
    return result


def interactive_select(values: List[str], label: str) -> Optional[str]:
    """
    Display a numbered list and prompt the user to select one value.

    Args:
        values: List of values to choose from
        label: Label for the prompt (e.g., "Department")

    Returns:
        Selected value string, or None if user skips (empty input)
    """
    print(f"\nAvailable {label}s:")
    for i, val in enumerate(values, 1):
        print(f"  {i}. {val}")

    while True:
        choice = input(f"\nSelect a {label} (number), or press Enter to skip: ").strip()
        if not choice:
            return None
        try:
            idx = int(choice)
            if 1 <= idx <= len(values):
                return values[idx - 1]
            print(f"Please enter a number between 1 and {len(values)}.")
        except ValueError:
            print("Please enter a valid number.")


def rows_to_author_entries(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Convert CSV rows to author entry dicts for the resolution pipeline.

    Deduplicates by (last_name, first_initial, department) to preserve
    distinct people who share a name initial but are in different departments.

    Args:
        rows: List of row dicts from parse_comp_report/filter_rows

    Returns:
        List of author entry dicts with keys: name, last_name, first_initial,
        department, college
    """
    seen = set()
    entries = []
    for row in rows:
        last_name = row.get("Last Name", "").strip()
        first_initial = row.get("First Initial", "").strip()
        department = row.get("Department", "").strip()
        college = row.get("Unit Name", "").strip()

        if not last_name or not first_initial:
            continue

        key = (last_name.lower(), first_initial.lower(), department.lower())
        if key in seen:
            continue
        seen.add(key)

        initial = first_initial.rstrip(".")
        entries.append({
            "name": f"{initial}. {last_name}",
            "last_name": last_name,
            "first_initial": first_initial,
            "department": department,
            "college": college,
        })

    return entries


def load_and_filter_comp_report(
    file_path: str,
    department: Optional[str] = None,
    job_title: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Load a compensation report CSV, apply filters, and return author entries.

    If neither department nor job_title is provided, prompts the user
    interactively to select from the unique values in the file.

    Args:
        file_path: Path to the CSV file
        department: Department filter (case-insensitive substring), or None
        job_title: Job title filter (case-insensitive substring), or None

    Returns:
        List of author entry dicts ready for the resolution pipeline

    Raises:
        FileNotFoundError: If the file does not exist
        ValueError: If the file is invalid or no authors remain after filtering
    """
    rows = parse_comp_report(file_path)

    # Interactive selection when no flags provided
    if department is None and job_title is None:
        departments = get_unique_values(rows, "Department")
        department = interactive_select(departments, "Department")

        job_titles = get_unique_values(rows, "Job Title")
        job_title = interactive_select(job_titles, "Job Title")

    filtered = filter_rows(rows, department=department, job_title=job_title)

    if not filtered:
        raise ValueError("No rows match the specified filters")

    entries = rows_to_author_entries(filtered)

    if not entries:
        raise ValueError("No valid author entries after filtering")

    print(f"Filtered to {len(entries)} unique author(s) from {len(filtered)} row(s)")
    return entries
