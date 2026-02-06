# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenAlex CLI Tool — a Python command-line interface for querying the [OpenAlex](https://openalex.org/) scholarly publication API. It fetches academic works with flexible filtering and exports structured JSON optimized for LLM ingestion. Has special support for Colorado State University (CSU) affiliation filtering.

## Setup & Commands

```bash
# Install (editable/development mode with test dependencies)
pip install -e ".[dev]"

# Run the CLI
openalex-tool --search "machine learning" --output results.json

# Run tests
python -m pytest tests/ -v
```

## Architecture

All source code lives in `openalex_tool_pkg/`. The installed package entry point is `openalex_tool_pkg:main`.

### Module Responsibilities

- **`openalex_tool_pkg/__init__.py`** — CLI entry point. Argument parsing (`parse_args`), validation, orchestration of the full pipeline: parse → lookup authors → search → format → write.
- **`openalex_tool_pkg/openalex_client.py`** — All OpenAlex API interaction. Handles pagination, request batching (max 25 author IDs per request due to URL length limits), deduplication, rate limiting (exponential backoff + Retry-After), and "polite pool" access via email parameter.
- **`openalex_tool_pkg/formatter.py`** — Transforms API responses to output JSON. Key logic: abstract reconstruction from OpenAlex's inverted index format, author filtering (1 author per work—searched author if applicable, else first author).
- **`openalex_tool_pkg/config.py`** — Field definitions. `CORE_FIELDS` (7 default fields), `EXTENDED_FIELDS` (19 optional), `FIELD_ALIASES` (e.g., `date` → `publication_date`, `citations` → `cited_by_count`). Field include/exclude resolution.
- **`openalex_tool_pkg/name_resolver.py`** — Tavily search integration for resolving abbreviated author names (first initials) to full names. Handles TSV author file parsing, abbreviation detection, and institutional context for better lookups.
- **`openalex_tool_pkg/comp_report.py`** — CSU compensation report CSV ingestion. Parses CSV with quoted fields, interactive department/job-title filtering, deduplication, and conversion to author entries for the resolution pipeline.
- **`openalex_tool_pkg/config_manager.py`** — Persistent user config at `~/.openalex-tool/config.json`. Stores email for polite pool API access and Tavily API key.

### Data Flow

CLI args → validate (at least one search param required) → parse author file (TSV or plain text) or compensation report CSV (with department/job-title filtering) → resolve abbreviated names via Tavily (if enabled) → lookup author IDs via OpenAlex API (with optional institution filter) → build query filters → paginated API search (with batching/dedup) → format each work → write JSON with metadata.

### Key Design Decisions

- **1 author per work**: Output intentionally limits to one author to keep data clean for LLM training.
- **CSU filtering**: Fetches all CSU-affiliated authors from `last_known_institutions`, then filters works by those author IDs (up to 1000 authors).
- **Inverted index abstracts**: OpenAlex stores abstracts as `{"word": [positions]}`. The tool reconstructs readable text by sorting on position.
- **Batching**: Author queries over 25 IDs are split into batches with results deduplicated by work ID.

## OpenAlex API Surface

### Endpoints (constants in `openalex_client.py`)

- `BASE_URL` = `https://api.openalex.org/works` — search and retrieve scholarly works
- `INSTITUTIONS_URL` = `https://api.openalex.org/institutions` — look up institutions by name
- `AUTHORS_URL` = `https://api.openalex.org/authors` — look up authors by name or institution

### Filter Syntax

- Format: `field.operator:value` (e.g., `display_name.search:MIT`)
- Pipe `|` for OR logic: `authorships.author.id:A1|A2`
- Comma `,` for AND logic (multiple filters): `filter=authorships.author.id:A1,authorships.institutions.id:I123`

### Pagination

- Offset-based: `page` + `per_page` parameters (not cursor-based)
- The tool paginates automatically until `max_results` is reached or no more results

### Key Query Parameters

- `mailto` — email for polite pool (better rate limits)
- `search` — full-text search query
- `filter` — structured filters (see syntax above)
- `per_page` — results per page (max 200)
- `page` — page number (1-indexed)
- `select` — fields to return (used only for author ID lookups, not for works)
- `sort` — sort order (e.g., `publication_year:desc`, `cited_by_count:desc`)

### Key Constants

- `DEFAULT_PER_PAGE = 25`
- `MAX_PER_PAGE = 200`
- `DEFAULT_MAX_RESULTS = 100`
- `MAX_AUTHORS_PER_FILTER = 25` (defined in `search_works()`)

## Dependencies

Single runtime dependency: `requests>=2.31,<3`. Dev dependency: `pytest>=7.0`. Optional dependency: `tavily-python>=0.3.0` (install via `pip install -e ".[tavily]"`). Python 3.8+.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for project structure, how-to guides, and git workflow.
