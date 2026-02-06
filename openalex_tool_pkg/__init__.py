#!/usr/bin/env python3
"""
OpenAlex CLI Tool

A command-line tool for querying the OpenAlex API to fetch scholarly works
and export them as configurable JSON files for LLM ingestion.
"""

import argparse
import sys
from typing import Optional

from .config import get_fields_to_select, ALL_FIELDS
from .openalex_client import search_works, lookup_author_id, lookup_institution_id, OpenAlexAPIError, RateLimitError
from .formatter import format_work, write_json
from .config_manager import get_email, set_email, get_config_path, get_tavily_api_key as get_config_tavily_key, set_tavily_api_key
from .name_resolver import (
    detect_file_format,
    parse_author_line,
    resolve_abbreviated_name,
    get_tavily_api_key,
)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Query OpenAlex API to fetch scholarly works and export as JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search by keywords
  python openalex_tool.py --search "machine learning" --output results.json

  # Search by author ID
  python openalex_tool.py --author-id A2208157607 --fields title,abstract,authors

  # Search by institution
  python openalex_tool.py --institution "Colorado State University" --max-results 50

  # Combine search criteria
  python openalex_tool.py --search "climate change" --institution "MIT" --fields title,abstract,authors,doi
        """
    )
    
    # Search parameters
    search_group = parser.add_argument_group("Search Parameters")
    search_group.add_argument(
        "--search", "-s",
        type=str,
        help="Text search query"
    )
    search_group.add_argument(
        "--author-id", "-a",
        type=str,
        help="Author OpenAlex ID (e.g., A2208157607) or ORCID (e.g., 0000-0002-1825-0097)"
    )
    search_group.add_argument(
        "--institution", "-i",
        type=str,
        help="Institution name (e.g., 'Colorado State University')"
    )
    search_group.add_argument(
        "--author-file",
        type=str,
        help="Path to file containing author names (one per line). Names will be looked up and searched."
    )
    search_group.add_argument(
        "--csu-only",
        action="store_true",
        help="Restrict results to authors whose last known affiliation is Colorado State University"
    )
    
    # Output configuration
    output_group = parser.add_argument_group("Output Configuration")
    output_group.add_argument(
        "--fields", "-f",
        type=str,
        help="Comma-separated list of fields to include (default: core fields)"
    )
    output_group.add_argument(
        "--exclude-fields", "-e",
        type=str,
        help="Comma-separated list of fields to exclude from default set"
    )
    output_group.add_argument(
        "--output", "-o",
        type=str,
        default="openalex_results.json",
        help="Output file path (default: openalex_results.json)"
    )
    
    # Pagination and limits
    pagination_group = parser.add_argument_group("Pagination")
    pagination_group.add_argument(
        "--max-results", "-m",
        type=int,
        default=100,
        help="Maximum number of results to fetch (default: 100, 0 = all)"
    )
    pagination_group.add_argument(
        "--per-page",
        type=int,
        default=25,
        help="Results per page (default: 25, max: 200)"
    )
    pagination_group.add_argument(
        "--sort",
        type=str,
        choices=["year", "year-desc", "year-asc", "citations", "citations-desc", "citations-asc"],
        help="Sort results: 'year' or 'year-desc' (most recent first), 'year-asc' (oldest first), 'citations' or 'citations-desc' (highest first), 'citations-asc' (lowest first)"
    )
    
    # API configuration
    api_group = parser.add_argument_group("API Configuration")
    api_group.add_argument(
        "--email",
        type=str,
        help="Email address for polite pool (overrides saved config)"
    )
    api_group.add_argument(
        "--tavily-api-key",
        type=str,
        help="Tavily API key for name resolution (overrides saved config)"
    )
    api_group.add_argument(
        "--no-tavily",
        action="store_true",
        help="Disable Tavily name resolution for abbreviated author names"
    )
    
    # List available fields
    parser.add_argument(
        "--list-fields",
        action="store_true",
        help="List all available fields and exit"
    )
    
    # Configuration
    config_group = parser.add_argument_group("Configuration")
    config_group.add_argument(
        "--set-email",
        type=str,
        metavar="EMAIL",
        help="Set the email address for polite pool (saved to config file)"
    )
    config_group.add_argument(
        "--set-tavily-key",
        type=str,
        metavar="KEY",
        help="Set the Tavily API key for name resolution (saved to config file)"
    )
    config_group.add_argument(
        "--show-config",
        action="store_true",
        help="Show current configuration and exit"
    )
    
    return parser.parse_args()


def list_available_fields():
    """Print list of available fields."""
    print("Available fields:")
    print("\nCore fields (included by default):")
    from .config import CORE_FIELDS
    for field in CORE_FIELDS:
        print(f"  - {field}")
    
    print("\nExtended fields:")
    from .config import EXTENDED_FIELDS
    for field in EXTENDED_FIELDS:
        print(f"  - {field}")
    
    print("\nField aliases:")
    from .config import FIELD_ALIASES
    for alias, field in sorted(FIELD_ALIASES.items()):
        print(f"  - {alias} → {field}")


def parse_field_list(field_string: Optional[str]) -> Optional[list]:
    """Parse comma-separated field list."""
    if not field_string:
        return None
    return [f.strip() for f in field_string.split(",") if f.strip()]


def main():
    """Main entry point."""
    args = parse_args()
    
    # Handle configuration options
    if args.set_email:
        set_email(args.set_email)
        return 0

    if args.set_tavily_key:
        set_tavily_api_key(args.set_tavily_key)
        return 0

    if args.show_config:
        config_email = get_email()
        tavily_key = get_config_tavily_key()
        print(f"Configuration file: {get_config_path()}")
        print(f"Email: {config_email}")
        print(f"Tavily API key: {'configured' if tavily_key else 'not set'}")
        return 0
    
    # Handle list-fields option
    if args.list_fields:
        list_available_fields()
        return 0
    
    # Handle author file if provided
    author_ids_from_file = []
    if args.author_file:
        try:
            with open(args.author_file, "r", encoding="utf-8") as f:
                lines = [line.rstrip("\n\r") for line in f]

            if not lines or not any(line.strip() for line in lines):
                print(f"Error: Author file '{args.author_file}' is empty", file=sys.stderr)
                return 1

            # Detect file format (TSV with headers vs plain text)
            headers = detect_file_format(lines[0])
            data_lines = lines[1:] if headers else lines

            # Parse author entries
            author_entries = []
            for line in data_lines:
                entry = parse_author_line(line, headers)
                if entry:
                    author_entries.append(entry)

            if not author_entries:
                print(f"Error: No valid author entries in '{args.author_file}'", file=sys.stderr)
                return 1

            # Determine institution context
            institution_name = None
            institution_id = None
            if args.csu_only:
                institution_name = "Colorado State University"
            elif args.institution:
                institution_name = args.institution

            # Look up institution ID for filtered lookups
            email_for_lookup = args.email if args.email else get_email()
            if institution_name:
                institution_id = lookup_institution_id(institution_name, email_for_lookup)

            # Resolve abbreviated names via Tavily if enabled
            use_tavily = not args.no_tavily
            tavily_key = None
            if use_tavily:
                tavily_key = get_tavily_api_key(args.tavily_api_key)

            print(f"Looking up {len(author_entries)} author(s) from file...", flush=True)
            found_count = 0
            for entry in author_entries:
                name = entry["name"]

                # Try Tavily resolution for abbreviated names
                if use_tavily and tavily_key:
                    resolved_name, was_resolved = resolve_abbreviated_name(
                        name,
                        institution=institution_name,
                        department=entry.get("department"),
                        college=entry.get("college"),
                        tavily_api_key=tavily_key,
                    )
                    if was_resolved:
                        print(f"  Resolved: {name} -> {resolved_name}", flush=True)
                        name = resolved_name

                author_id = lookup_author_id(name, email_for_lookup, institution_id)
                if author_id:
                    author_ids_from_file.append(author_id)
                    found_count += 1
                    print(f"  Found: {name} -> {author_id}", flush=True)
                else:
                    print(f"  Not found: {name}", file=sys.stderr)

            if not author_ids_from_file:
                print("Error: No authors found from file", file=sys.stderr)
                return 1

            print(f"Successfully looked up {found_count} of {len(author_entries)} author(s)")
        except FileNotFoundError:
            print(f"Error: Author file '{args.author_file}' not found", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error reading author file: {e}", file=sys.stderr)
            return 1
    
    # Validate that at least one search parameter is provided
    if not any([args.search, args.author_id, author_ids_from_file, args.institution, args.csu_only]):
        print("Error: At least one search parameter (--search, --author-id, --author-file, --institution, or --csu-only) must be provided", file=sys.stderr)
        print("Use --help for usage information", file=sys.stderr)
        return 1
    
    # Parse field lists
    include_fields = parse_field_list(args.fields)
    exclude_fields = parse_field_list(args.exclude_fields)
    
    # Determine which fields to select
    try:
        selected_fields = get_fields_to_select(include_fields, exclude_fields)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    # Build query info for metadata
    query_info = {}
    if args.search:
        query_info["search"] = args.search
    if args.author_id:
        query_info["author_id"] = args.author_id
    if author_ids_from_file:
        query_info["author_ids"] = author_ids_from_file
        query_info["author_file"] = args.author_file
    if args.institution:
        query_info["institution"] = args.institution
    if args.csu_only:
        query_info["csu_only"] = True
    
    # Get email (use command-line arg if provided, otherwise use config)
    email = args.email if args.email else get_email()
    
    # Map user-friendly sort options to OpenAlex API format
    sort_param = None
    if args.sort:
        sort_map = {
            "year": "publication_year:desc",
            "year-desc": "publication_year:desc",
            "year-asc": "publication_year:asc",
            "citations": "cited_by_count:desc",
            "citations-desc": "cited_by_count:desc",
            "citations-asc": "cited_by_count:asc"
        }
        sort_param = sort_map.get(args.sort)
    
    # Search for works
    print("Searching OpenAlex API...")
    try:
        works = search_works(
            search=args.search,
            author_id=args.author_id,
            author_ids=author_ids_from_file if author_ids_from_file else None,
            institution=args.institution,
            csu_only=args.csu_only,
            fields=selected_fields,
            sort=sort_param,
            max_results=args.max_results,
            per_page=args.per_page,
            email=email
        )
    except RateLimitError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except OpenAlexAPIError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    if not works:
        print("No works found matching your criteria.")
        return 0
    
    print(f"Found {len(works)} works. Formatting output...")
    
    # Collect searched author IDs for filtering
    searched_author_ids = []
    if args.author_id:
        # Normalize the author ID
        from .openalex_client import normalize_author_id
        normalized_id = normalize_author_id(args.author_id)
        if normalized_id.startswith("A") and normalized_id[1:].isdigit():
            normalized_id = f"https://openalex.org/{normalized_id}"
        searched_author_ids.append(normalized_id)
    
    if author_ids_from_file:
        # These are already in URL format from lookup
        searched_author_ids.extend(author_ids_from_file)
    
    # Format works
    formatted_works = []
    for work in works:
        formatted = format_work(work, selected_fields, searched_author_ids if searched_author_ids else None)
        formatted_works.append(formatted)
    
    # Write to file
    try:
        write_json(formatted_works, args.output, query_info)
    except IOError as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

