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
- `--author-file` - Path to file containing author names (one per line). Names will be looked up automatically.
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
- `--set-email EMAIL` - Set and save email address to config file
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

### Email Configuration

The tool automatically uses a saved email address for the "polite pool" which improves rate limits. 

**Set your email:**
```bash
openalex-tool --set-email your.email@example.com
```

**View current configuration:**
```bash
openalex-tool --show-config
```

The email is saved in `~/.openalex-tool/config.json` and will be used automatically for all API requests. You can override it for a single request using the `--email` flag.

### Author File Format

The `--author-file` option accepts a simple text file with one author name per line:

```
Cris Argueso
Lisa Blecker
Marek Borowiec
```

An example file `authors_example.txt` is included in the repository. You can copy and modify it for your own use.

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
