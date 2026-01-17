# Web Documentation to PDF Converter

A Python application that crawls documentation websites and converts all pages into a single, merged PDF file.

## Features

- **Recursive Crawling**: Discovers and follows all internal documentation links
- **External Link Filtering**: Automatically excludes links to external domains
- **Order Preservation**: Maintains logical page order using breadth-first traversal
- **PDF Conversion**: Clean, styled PDFs with page headers and footers
- **Table of Contents**: Generates bookmarks from page titles in the merged PDF
- **Polite Crawling**: Configurable delays between requests

## Installation

### Prerequisites

- Python 3.8 or higher
- GTK/Pango libraries (required by WeasyPrint on Windows)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Windows Users

WeasyPrint requires GTK libraries. Install via MSYS2:

```bash
# Using MSYS2 (https://www.msys2.org/)
pacman -S mingw-w64-x86_64-pango mingw-w64-x86_64-gdk-pixbuf2
```

Or use the GTK installer: https://github.com/nicothin/MSYS2-GTK3

## Usage

### Basic Usage

```bash
python -m src.main https://docs.example.com/
```

### With Options

```bash
python -m src.main https://docs.example.com/ \
    --output documentation.pdf \
    --max-depth 5 \
    --delay 1.0 \
    --verbose
```

### Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `url` | Base URL of the documentation site | (required) |
| `-o, --output` | Output PDF filename | `documentation.pdf` |
| `--max-depth` | Maximum crawl depth | 10 |
| `--delay` | Delay between requests (seconds) | 0.5 |
| `--timeout` | Request timeout (seconds) | 30 |
| `-v, --verbose` | Enable verbose logging | False |

## Examples

### HP Anyware Manager Documentation

```bash
python -m src.main https://anyware.hp.com/web-help/anyware_manager_enterprise/ \
    --output anyware_docs.pdf \
    --max-depth 8
```

## Project Structure

```
web2pdf-gag/
├── src/
│   ├── __init__.py       # Package init
│   ├── config.py         # Configuration settings
│   ├── url_utils.py      # URL filtering and normalization
│   ├── crawler.py        # Web crawler implementation
│   ├── converter.py      # HTML-to-PDF conversion
│   ├── merger.py         # PDF merging logic
│   └── main.py           # CLI entry point
├── tests/
│   ├── test_url_utils.py # URL utility tests
│   └── test_crawler.py   # Crawler tests
├── requirements.txt
└── README.md
```

## Running Tests

```bash
python -m pytest tests/ -v
```

Or with unittest:

```bash
python -m unittest discover tests/
```

## Architecture

### Crawling Logic

1. Start from the base URL
2. Use breadth-first search (BFS) to traverse links
3. Normalize URLs (resolve relative paths, remove fragments)
4. Filter external links by comparing domains
5. Track visited URLs in a Set for O(1) lookup

### PDF Conversion

1. Extract and clean HTML content
2. Apply consistent CSS styling via WeasyPrint
3. Convert each page to an individual PDF
4. Merge all PDFs with PyPDF2, adding bookmarks

## License

MIT License
