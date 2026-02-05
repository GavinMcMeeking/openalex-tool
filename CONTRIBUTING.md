# Contributing

## Project Structure

```
openalex-tool/
├── openalex_tool_pkg/          # All source code
│   ├── __init__.py             # CLI entry point (main, parse_args)
│   ├── config.py               # Field definitions and validation
│   ├── config_manager.py       # Persistent user config (~/.openalex-tool/)
│   ├── formatter.py            # API response → output JSON
│   └── openalex_client.py      # OpenAlex API client
├── tests/                      # pytest test suite
│   ├── test_config.py
│   ├── test_config_manager.py
│   ├── test_formatter.py
│   └── test_openalex_client.py
├── setup.py                    # Package configuration
├── requirements.txt            # Runtime dependencies
├── CLAUDE.md                   # AI coding agent guidance
├── CONTRIBUTING.md             # This file
├── README.md                   # User documentation
└── TODO.md                     # Project roadmap
```

## Error Handling

The codebase uses three exception types defined in `openalex_client.py`:

- **`OpenAlexAPIError`** — base exception for all API errors (network failures, unexpected status codes)
- **`RateLimitError(OpenAlexAPIError)`** — raised on HTTP 429; `make_request()` retries automatically with `Retry-After` header before raising
- **`ValueError`** — raised for invalid user input (unknown fields, institution not found, missing search parameters)

All exceptions are caught in `main()` and printed to stderr with a non-zero exit code.

## How to Add a New Output Field

1. **Define the field** in `openalex_tool_pkg/config.py`:
   - Add to `EXTENDED_FIELDS` list
   - Optionally add user-friendly aliases to `FIELD_ALIASES`
   - If the field requires nested extraction, add to `NESTED_FIELDS`

2. **Add extraction logic** in `openalex_tool_pkg/formatter.py`:
   - If the field maps directly to an API response key, no change needed — `format_work()` handles it via `work.get(field)`
   - If the field needs transformation, add an `elif field == "your_field"` branch in `format_work()`

3. **Add tests** in `tests/test_formatter.py` and `tests/test_config.py`:
   - Test that the field resolves correctly
   - Test extraction with realistic mock data

## How to Add a New CLI Argument

1. **Add the argument** in `openalex_tool_pkg/__init__.py`:
   - Add to the appropriate argument group in `parse_args()`
   - Handle the argument in `main()`

2. **If it affects the API query**, update `build_query_params()` in `openalex_tool_pkg/openalex_client.py`

3. **Add tests** for the new behavior

## Design Decisions

- **1 author per work**: Output intentionally limits to one author per work. When searching by author ID, the searched author is returned; otherwise, the first author is returned. This keeps data clean and predictable for LLM training pipelines.

- **CSU-specific filtering**: The `--csu-only` flag fetches all authors whose `last_known_institutions` includes Colorado State University, then uses their IDs to filter works. This is a two-step process because the OpenAlex API doesn't support filtering works by author institution affiliation directly.

- **Abstract inverted index reconstruction**: OpenAlex stores abstracts as `{"word": [positions]}` rather than plain text. The tool reconstructs readable text by sorting words by their position indices.

## Running Tests

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run all tests
python -m pytest tests/ -v
```

## Git Workflow

1. Create a feature branch off `main`
2. Make changes, add tests
3. Run `python -m pytest tests/ -v` and verify all tests pass
4. Commit with a descriptive message
5. Open a PR to `main`
