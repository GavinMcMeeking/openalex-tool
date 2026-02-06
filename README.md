# OpenAlex CLI Tool

A simple command-line tool for querying the OpenAlex API to fetch scholarly works and export them as configurable JSON files for LLM ingestion.

## Installation

### Requirements

- Python 3.8 or higher
- pip (usually comes with Python)

### Quick Install

1. Clone or download this repository:

```bash
git clone https://github.com/YOUR_USERNAME/openalex-tool.git
cd openalex-tool
```

2. Install the package:

```bash
pip install .
```

This will install the tool and its dependencies. After installation, you can use the `openalex-tool` command from anywhere on your system.

### Alternative: User-Level Installation

If you don't have admin/sudo access, you can install to your user directory:

```bash
pip install --user .
```

### Alternative: Development Installation

If you want to modify the code, install in editable mode:

```bash
pip install -e .
```

### Uninstalling

To uninstall the tool:

```bash
pip uninstall openalex-tool
```

## Usage

After installation, you can use the `openalex-tool` command from any directory:

### Basic Examples

**Search by keywords:**
```bash
openalex-tool --search "machine learning" --output results.json
```

**Search by author ID:**
```bash
openalex-tool --author-id A2208157607 --fields title,abstract,authors
```

**Search by institution:**
```bash
openalex-tool --institution "Colorado State University" --max-results 50
```

**Combine search criteria:**
```bash
openalex-tool --search "climate change" --institution "MIT" --fields title,abstract,authors,doi
```

**Search by author names from file:**
```bash
openalex-tool --author-file authors_example.txt --max-results 50
```

**Search with CSU-only restriction:**
```bash
openalex-tool --author-file authors_example.txt --csu-only --output csu_authors.json
```

### Command-Line Arguments

#### Search Parameters

- `--search`, `-s` - Text search query
- `--author-id`, `-a` - Author OpenAlex ID (e.g., `A2208157607`) or ORCID (e.g., `0000-0002-1825-0097`)
- `--author-file` - Path to file containing author names. Supports plain text (one name per line) or TSV format with headers. Names will be looked up automatically.
- `--institution`, `-i` - Institution name (e.g., "Colorado State University")
- `--csu-only` - Restrict results to authors whose last known affiliation is Colorado State University

At least one search parameter must be provided.

#### Output Configuration

- `--fields`, `-f` - Comma-separated list of fields to include (default: core fields)
- `--exclude-fields`, `-e` - Comma-separated list of fields to exclude from default set
- `--output`, `-o` - Output file path (default: `openalex_results.json`)

#### Pagination

- `--max-results`, `-m` - Maximum number of results to fetch (default: 100, use `0` for all)
- `--per-page` - Results per page (default: 25, max: 200)

#### API Configuration

- `--email` - Email address for polite pool (overrides saved config, optional)
- `--tavily-api-key KEY` - Tavily API key for name resolution (overrides saved config)
- `--no-tavily` - Disable Tavily name resolution for abbreviated author names
- `--set-email EMAIL` - Set and save email address to config file
- `--set-tavily-key KEY` - Set and save Tavily API key to config file
- `--show-config` - Display current configuration

#### CSU-Specific Options

- `--csu-only` - Restrict results to authors whose last known institution is Colorado State University

#### Other Options

- `--list-fields` - List all available fields and exit
- `--help`, `-h` - Show help message

## Available Fields

### Core Fields (included by default)

- `id` - OpenAlex work ID
- `title` - Work title
- `abstract` - Abstract text
- `authors` - List of authors with names, IDs, and ORCIDs
- `publication_date` - Publication date
- `doi` - Digital Object Identifier
- `type` - Work type (article, book, etc.)

### Extended Fields

- `concepts` - Research concepts/topics
- `keywords` - Keywords
- `cited_by_count` - Number of citations
- `institutions` - Associated institutions
- `sources` - Journal/source information
- `publisher` - Publisher name
- `language` - Language code
- `is_oa` - Open access status
- `open_access` - Open access details
- `primary_location` - Primary publication location
- `locations` - All publication locations
- `referenced_works` - Works this work references
- `related_works` - Related works
- `year` - Publication year
- `created_date` - Record creation date
- `updated_date` - Record update date
- `publication_year` - Publication year
- `cited_by_api_url` - API URL for citations
- `related_works_api_url` - API URL for related works

### Field Aliases

You can use these aliases instead of the full field names:

- `author` → `authors`
- `date` → `publication_date`
- `pub_date` → `publication_date`
- `citation_count` → `cited_by_count`
- `citations` → `cited_by_count`
- `institution` → `institutions`
- `source` → `sources`
- `journal` → `sources`
- `venue` → `sources`
- `open_access` → `is_oa`
- `oa` → `is_oa`

### Listing Available Fields

To see all available fields:

```bash
openalex-tool --list-fields
```

## Output Format

The tool outputs a JSON file with the following structure:

```json
{
  "works": [
    {
      "id": "https://openalex.org/W1234567890",
      "title": "Example Title",
      "abstract": "Abstract text...",
      "authors": [
        {
          "id": "https://openalex.org/A2208157607",
          "name": "Author Name",
          "orcid": "https://orcid.org/0000-0002-1825-0097",
          "position": "first"
        }
      ],
      "publication_date": "2023-01-01",
      "doi": "https://doi.org/10.1234/example",
      "type": "article"
    }
  ],
  "metadata": {
    "total": 1,
    "timestamp": "2024-01-01T12:00:00Z",
    "query": {
      "search": "machine learning",
      "institution": "MIT"
    }
  }
}
```

## Examples

### Example 1: Basic Search

```bash
openalex-tool --search "quantum computing" --output quantum_papers.json
```

### Example 2: Author-Specific Search

```bash
openalex-tool --author-id 0000-0002-1825-0097 --max-results 200
```

### Example 3: Institution Search with Custom Fields

```bash
openalex-tool \
  --institution "Stanford University" \
  --fields title,abstract,authors,doi,cited_by_count \
  --max-results 50 \
  --output stanford_papers.json
```

### Example 4: Combined Search with Email

```bash
openalex-tool \
  --search "artificial intelligence" \
  --institution "MIT" \
  --email your.email@example.com \
  --max-results 0 \
  --output ai_papers.json
```

### Example 5: Author File Search

```bash
openalex-tool --author-file authors_example.txt --max-results 50 --output authors_works.json
```

### Example 6: CSU-Only Search

```bash
openalex-tool --csu-only --search "climate change" --max-results 100 --output csu_climate.json
```

### Example 7: Author File with CSU Restriction

```bash
openalex-tool --author-file authors_example.txt --csu-only --output csu_authors_works.json
```

## Configuration

All configuration is stored in `~/.openalex-tool/config.json` and persists across sessions. View your current settings at any time:

```bash
openalex-tool --show-config
```

### Email (OpenAlex Polite Pool)

Setting an email address gives you access to OpenAlex's "polite pool" with better rate limits.

```bash
# Save your email (persists across sessions)
openalex-tool --set-email your.email@example.com

# Override for a single run
openalex-tool --email other@example.com --search "machine learning"
```

### Tavily API Key (Name Resolution)

A [Tavily](https://tavily.com/) API key enables automatic resolution of abbreviated author names (see [Tavily Name Resolution](#tavily-name-resolution) below). You can get a free API key at [app.tavily.com](https://app.tavily.com/).

```bash
# Save your API key (persists across sessions)
openalex-tool --set-tavily-key YOUR_KEY_HERE

# Override for a single run
openalex-tool --tavily-api-key YOUR_KEY --author-file faculty.tsv

# Or set via environment variable
export TAVILY_API_KEY=YOUR_KEY_HERE
```

Key lookup priority: `--tavily-api-key` flag > `TAVILY_API_KEY` env var > saved config.

You also need to install the optional Tavily dependency:

```bash
pip install -e ".[tavily]"
```

## Author File Format

The `--author-file` option supports two formats, auto-detected based on file content.

### Plain Text Format

One full author name per line:

```
Cris Argueso
Lisa Blecker
Marek Borowiec
```

Use this format when you have full author names. Each name is looked up directly on OpenAlex.

### TSV Format

Tab-separated values with a header row. The required columns are `LastName` and `FirstInitial`. Optional columns `College` and `Department` provide institutional context for Tavily name resolution.

```
College	Department	LastName	FirstInitial	Rank	AppointmentType	Status	Value
Natural Sciences	Chemistry	Bernstein	B	Professor	12-Month	Contract/Continuing	0.005
Agricultural Sciences	Soil and Crop Sciences	Kelly	E	Professor	9-Month	Tenured	0.010
```

The tool auto-detects TSV format when the first line contains tabs and a recognized header (`LastName` or `Last_Name`). Extra columns (Rank, AppointmentType, etc.) are ignored.

When combined with Tavily name resolution, the College and Department columns provide critical context. For example, "E. Kelly" in "Soil and Crop Sciences" resolves to "Eugene F. Kelly" — without that context, OpenAlex returns the wrong person.

### Tavily Name Resolution

When author names contain only first initials (e.g., "E. Kelly" or "S. Kreidenweis"), the OpenAlex API often returns the wrong author. Tavily search resolves these abbreviated names to full names using institutional context before the OpenAlex lookup.

**Requirements:**
1. Install the optional dependency: `pip install -e ".[tavily]"`
2. Configure an API key (see [Tavily API Key](#tavily-api-key-name-resolution) above)

**How it works:**
1. The tool detects abbreviated names (single-letter first names like "E." or "S.")
2. Queries Tavily with the name plus college/department/institution context
3. Extracts the full name from search results
4. Looks up the full name on OpenAlex instead of the abbreviation

**Examples:**
```bash
# TSV file with abbreviated names — Tavily resolves them automatically
openalex-tool --author-file faculty.tsv --csu-only --output results.json

# Disable Tavily (fall back to abbreviated name lookup)
openalex-tool --author-file faculty.tsv --csu-only --no-tavily

# One-time API key override
openalex-tool --author-file faculty.tsv --tavily-api-key YOUR_KEY
```

**Verified results:**

| TSV Input | Resolved Name | Correct Author Found |
|-----------|--------------|---------------------|
| E. Kelly (Soil and Crop Sciences) | Eugene F. Kelly | Yes |
| S. Kreidenweis (Atmospheric Science) | Sonia M. Kreidenweis | Yes |
| H. Blackburn (Biology) | Heather Blackburn | Yes |

**Graceful degradation:** If `tavily-python` is not installed, no API key is configured, or `--no-tavily` is passed, the tool falls back to looking up the abbreviated name directly on OpenAlex.

## Rate Limits

The OpenAlex API has a daily limit of 100,000 requests per user. To improve rate limits and performance:

1. Set your email address using `--set-email` (saved automatically)
2. This adds you to the "polite pool" which provides better rate limits

## Error Handling

The tool handles common errors:

- **Rate limit exceeded**: Automatically retries with exponential backoff
- **Network errors**: Provides clear error messages
- **Invalid field names**: Validates and reports unknown fields
- **Missing search parameters**: Requires at least one search parameter

## Author ID Formats

The tool accepts author IDs in multiple formats:

- OpenAlex ID: `A2208157607`
- ORCID (with URL): `https://orcid.org/0000-0002-1825-0097`
- ORCID (without URL): `0000-0002-1825-0097`

## Institution Search

Institution names are matched using fuzzy search. You can use:

- Full names: "Colorado State University"
- Partial names: "MIT" (may match multiple institutions)
- Case-insensitive matching

## Tips for LLM Ingestion

When preparing data for LLM ingestion:

1. **Select relevant fields**: Use `--fields` to include only what you need
2. **Limit results**: Use `--max-results` to control dataset size
3. **Combine filters**: Use multiple search parameters to narrow results
4. **Review output**: Check the JSON structure before ingestion

Example for LLM training:

```bash
openalex-tool \
  --search "your topic" \
  --fields title,abstract,authors,doi \
  --max-results 1000 \
  --output training_data.json
```

## Troubleshooting

**No results found:**
- Try broader search terms
- Check author ID format
- Verify institution name spelling

**Abbreviated author name resolves to wrong person:**
- Ensure the TSV file has correct College and Department columns — these provide the context Tavily needs
- Check that `tavily-python` is installed: `pip install -e ".[tavily]"`
- Verify your API key: `openalex-tool --show-config`
- Some authors may not have a strong web presence at their institution, limiting Tavily's ability to resolve them

**Author found by Tavily but not in OpenAlex:**
- Some faculty (especially teaching-focused) may not have an OpenAlex profile linked to their institution
- The tool automatically falls back to an unfiltered lookup, but the result may be a different person with the same name

**Rate limit errors:**
- Add `--email` parameter
- Reduce `--per-page` value
- Wait and retry later

**Invalid field errors:**
- Use `--list-fields` to see available fields
- Check field name spelling
- Use aliases if available

## License

This tool is provided as-is for querying the OpenAlex API. OpenAlex data is available under CC0 license.

## References

- [OpenAlex API Documentation](https://docs.openalex.org/)
- [OpenAlex Website](https://openalex.org/)
