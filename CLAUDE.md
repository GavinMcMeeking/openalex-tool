# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenAlex CLI Tool — a Python command-line interface for querying the [OpenAlex](https://openalex.org/) scholarly publication API. It fetches academic works with flexible filtering and exports structured JSON optimized for LLM ingestion. Has special support for Colorado State University (CSU) affiliation filtering.

## Setup & Commands

```bash
# Install (editable/development mode)
pip install -e .

# Run the CLI
openalex-tool --search "machine learning" --output results.json

# Run directly without installing
python openalex_tool.py [args]
```

There are no tests, linter, or build steps configured.

## Architecture

The codebase has a dual structure: modules exist at both the root level and inside `openalex_tool_pkg/`. The installed package entry point is `openalex_tool_pkg:main`. Running directly uses `openalex_tool.py` at the root.

### Module Responsibilities

- **`openalex_tool.py` / `openalex_tool_pkg/__init__.py`** — CLI entry point. Argument parsing (`parse_args`), validation, orchestration of the full pipeline: parse → lookup authors → search → format → write.
- **`openalex_client.py`** — All OpenAlex API interaction. Handles pagination, request batching (max 25 author IDs per request due to URL length limits), deduplication, rate limiting (exponential backoff + Retry-After), and "polite pool" access via email parameter.
- **`formatter.py`** — Transforms API responses to output JSON. Key logic: abstract reconstruction from OpenAlex's inverted index format, author filtering (1 author per work—searched author if applicable, else first author).
- **`config.py`** — Field definitions. `CORE_FIELDS` (7 default fields), `EXTENDED_FIELDS` (19 optional), `FIELD_ALIASES` (e.g., `date` → `publication_date`, `citations` → `cited_by_count`). Field include/exclude resolution.
- **`config_manager.py`** — Persistent user config at `~/.openalex-tool/config.json`. Currently stores email for polite pool API access.

### Data Flow

CLI args → validate (at least one search param required) → resolve author names to IDs via API (if `--author-file`) → build query filters → paginated API search (with batching/dedup) → format each work → write JSON with metadata.

### Key Design Decisions

- **1 author per work**: Output intentionally limits to one author to keep data clean for LLM training.
- **CSU filtering**: Fetches all CSU-affiliated authors from `last_known_institutions`, then filters works by those author IDs (up to 1000 authors).
- **Inverted index abstracts**: OpenAlex stores abstracts as `{"word": [positions]}`. The tool reconstructs readable text by sorting on position.
- **Batching**: Author queries over 25 IDs are split into batches with results deduplicated by work ID.

## Dependencies

Single runtime dependency: `requests>=2.31,<3`. Python 3.8+.
