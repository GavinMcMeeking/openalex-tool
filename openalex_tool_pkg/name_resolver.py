"""
Name resolver module for handling abbreviated author names.

Provides Tavily search integration for resolving first initials to full names,
TSV author file parsing, and institutional context for better lookups.
"""

import os
import re
import sys
import warnings
from typing import Dict, List, Optional, Tuple


def is_abbreviated_name(name: str) -> bool:
    """
    Detect if a name contains only first initials (no full first name).

    Args:
        name: Author name string (e.g., "E. Kelly" or "Eugene Kelly")

    Returns:
        True if all parts except the last are single characters (with optional period)
    """
    if not name or not name.strip():
        return False

    parts = name.strip().split()
    if len(parts) < 2:
        return False

    # Check if all parts except the last are single-character initials
    first_parts = parts[:-1]
    return all(
        len(p.rstrip(".")) == 1 and p.rstrip(".").isalpha()
        for p in first_parts
    )


def detect_file_format(first_line: str) -> Optional[List[str]]:
    """
    Detect whether an author file is TSV format with headers or plain text.

    Args:
        first_line: The first line of the file

    Returns:
        List of header column names if TSV format, None if plain text
    """
    if "\t" not in first_line:
        return None

    columns = [col.strip() for col in first_line.split("\t")]
    # Check for expected header names (case-insensitive)
    lower_columns = [c.lower() for c in columns]
    if "lastname" in lower_columns or "last_name" in lower_columns:
        return columns

    return None


def parse_author_line(line: str, headers: Optional[List[str]] = None) -> Optional[Dict[str, str]]:
    """
    Parse a single line from an author file.

    Args:
        line: A single line from the author file
        headers: Column headers if TSV format, None for plain text

    Returns:
        Dictionary with author info, or None if line is empty/invalid
    """
    line = line.strip()
    if not line:
        return None

    if headers is None:
        # Plain text mode: line is the full name
        return {"name": line}

    # TSV mode: split by tabs and map to headers
    values = line.split("\t")
    row = {}
    header_lower_map = {}
    for i, header in enumerate(headers):
        lower = header.strip().lower()
        header_lower_map[lower] = i

    def get_val(key):
        idx = header_lower_map.get(key)
        if idx is not None and idx < len(values):
            return values[idx].strip()
        return ""

    last_name = get_val("lastname") or get_val("last_name")
    first_initial = get_val("firstinitial") or get_val("first_initial") or get_val("firstname") or get_val("first_name")
    department = get_val("department")
    college = get_val("college")

    if not last_name:
        return None

    # Construct name from initial + last name
    if first_initial:
        initial = first_initial.rstrip(".")
        name = f"{initial}. {last_name}"
    else:
        name = last_name

    result = {"name": name, "last_name": last_name}
    if first_initial:
        result["first_initial"] = first_initial
    if department:
        result["department"] = department
    if college:
        result["college"] = college

    return result


def get_tavily_api_key(cli_key: Optional[str] = None) -> Optional[str]:
    """
    Get Tavily API key from CLI arg, environment variable, or config file.

    Args:
        cli_key: API key provided via CLI argument

    Returns:
        API key string, or None if not found
    """
    if cli_key:
        return cli_key

    env_key = os.environ.get("TAVILY_API_KEY")
    if env_key:
        return env_key

    try:
        from .config_manager import get_tavily_api_key as get_config_key
        return get_config_key()
    except Exception:
        return None


def extract_full_name_from_results(tavily_response: dict, last_name: str, institution: Optional[str] = None) -> Optional[str]:
    """
    Extract a full author name from Tavily search results.

    Searches the response answer, result titles, and content for a full name
    matching the given last name.

    Args:
        tavily_response: Response dict from TavilyClient.search()
        last_name: The author's last name to match
        institution: Optional institution name for domain preference

    Returns:
        Full name string if found, None otherwise
    """
    # Regex to find "FirstName [MiddleInitial] LastName"
    pattern = re.compile(
        r'\b([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?)\s+' + re.escape(last_name) + r'\b'
    )

    # 1. Check the answer field first (most reliable)
    answer = tavily_response.get("answer", "") or ""
    match = pattern.search(answer)
    if match:
        first_part = match.group(1).strip()
        return f"{first_part} {last_name}"

    # 2. Check results, preferring institutional domain matches
    results = tavily_response.get("results", [])

    # Separate institutional and non-institutional results
    inst_results = []
    other_results = []
    inst_domain = None
    if institution and "colorado state" in institution.lower():
        inst_domain = "colostate.edu"

    for r in results:
        url = r.get("url", "")
        if inst_domain and inst_domain in url:
            inst_results.append(r)
        else:
            other_results.append(r)

    # Search institutional results first
    for r in inst_results + other_results:
        for field in ["title", "content"]:
            text = r.get(field, "") or ""
            match = pattern.search(text)
            if match:
                first_part = match.group(1).strip()
                return f"{first_part} {last_name}"

    return None


def resolve_abbreviated_name(
    name: str,
    institution: Optional[str] = None,
    department: Optional[str] = None,
    college: Optional[str] = None,
    tavily_api_key: Optional[str] = None,
) -> Tuple[str, bool]:
    """
    Resolve an abbreviated name to a full name using Tavily search.

    If the name is not abbreviated, returns it unchanged. If Tavily is
    unavailable or resolution fails, returns the original name.

    Args:
        name: Author name (e.g., "E. Kelly")
        institution: Institution name for search context
        department: Department name for search context
        college: College name for search context
        tavily_api_key: Tavily API key

    Returns:
        Tuple of (resolved_name, was_resolved)
    """
    if not is_abbreviated_name(name):
        return (name, False)

    # Check if tavily-python is installed
    try:
        from tavily import TavilyClient  # noqa: F401
    except ImportError:
        warnings.warn(
            "tavily-python not installed. Install with: pip install tavily-python",
            stacklevel=2,
        )
        return (name, False)

    if not tavily_api_key:
        warnings.warn(
            "No Tavily API key configured. Set with --set-tavily-key or TAVILY_API_KEY env var.",
            stacklevel=2,
        )
        return (name, False)

    # Extract last name for matching
    parts = name.strip().split()
    last_name = parts[-1]

    # Build search query with institutional context
    query_parts = [name]
    if college:
        query_parts.append(college)
    if department:
        query_parts.append(department)
    if institution:
        query_parts.append(institution)
    query_parts.append("professor")
    query = " ".join(query_parts)

    # Set up domain filter for known institutions
    search_kwargs = {
        "query": query,
        "include_answer": "advanced",
        "max_results": 5,
    }
    inst_domain = None
    if institution and "colorado state" in institution.lower():
        inst_domain = "colostate.edu"

    try:
        client = TavilyClient(api_key=tavily_api_key)

        # Try with domain filter first, fall back to unrestricted
        if inst_domain:
            search_kwargs["include_domains"] = [inst_domain]
        response = client.search(**search_kwargs)
        full_name = extract_full_name_from_results(response, last_name, institution)

        if not full_name and inst_domain:
            # Retry without domain restriction
            search_kwargs.pop("include_domains", None)
            response = client.search(**search_kwargs)
            full_name = extract_full_name_from_results(response, last_name, institution)
    except Exception as e:
        print(f"  Warning: Tavily search failed for '{name}': {e}", file=sys.stderr)
        return (name, False)

    if full_name:
        return (full_name, True)

    return (name, False)
