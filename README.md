# OpenAlex CLI Tool

A simple command-line tool for querying the OpenAlex API to fetch scholarly works and export them as configurable JSON files for LLM ingestion.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python openalex_tool.py --search "machine learning" --output results.json
```

## Features

- Search works by keywords, author IDs, or institutions
- Configurable field selection for output
- Automatic pagination support
- JSON output optimized for LLM ingestion

## Requirements

- Python 3.8+

