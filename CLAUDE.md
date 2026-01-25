# CLAUDE.md - AI Assistant Guide for web2pdf-gag

This document provides guidance for AI assistants working with the web2pdf-gag codebase.

## Project Overview

**web2pdf-gag** is a Python CLI application that crawls documentation websites and converts all pages into a single, merged PDF file with bookmarks and page numbering.

**Repository:** https://github.com/thomasckr/web2pdf-gag
**Version:** v0.2 (v1.0.0 in package)
**Python:** 3.8+

## Project Structure

```
web2pdf-gag/
├── src/                      # Source code
│   ├── __init__.py           # Package metadata
│   ├── main.py               # CLI entry point & orchestration
│   ├── config.py             # Configuration dataclass
│   ├── crawler.py            # Playwright-based web crawler
│   ├── url_utils.py          # URL filtering & normalization
│   ├── converter.py          # HTML to PDF conversion (pdfkit)
│   └── merger.py             # PDF merging & page numbering
├── tests/                    # Unit tests
│   ├── __init__.py
│   ├── test_url_utils.py     # URL utilities tests (26 tests)
│   └── test_crawler.py       # Crawler tests (16 tests)
├── requirements.txt          # Python dependencies
├── README.md                 # User documentation
├── status.md                 # Version history & release notes
└── .gitignore
```

## Architecture

The application follows a **3-phase pipeline**:

1. **Crawl** (`crawler.py`) - Uses Playwright with stealth mode to crawl documentation sites via BFS traversal
2. **Convert** (`converter.py`) - Converts each HTML page to PDF using pdfkit/wkhtmltopdf
3. **Merge** (`merger.py`) - Combines PDFs into single document with bookmarks and page numbers

### Key Data Flow

```
main.py
  └─> WebCrawler.crawl() → CrawlResult (list of CrawledPage)
        └─> PDFConverter.convert_pages() → List[PDFConversionResult]
              └─> PDFMerger.merge() → MergeResult (final PDF)
```

## Key Components

### Data Classes

| Class | Module | Purpose |
|-------|--------|---------|
| `CrawlerConfig` | config.py | Configuration settings (base_url, max_depth, etc.) |
| `CrawledPage` | crawler.py | Single page: url, title, html_content, depth |
| `CrawlResult` | crawler.py | Crawl output: pages, failed_urls, skipped_urls |
| `PDFConversionResult` | converter.py | Conversion result: pdf_path, success, error_message |
| `MergeResult` | merger.py | Merge output: output_path, success, total_pages |

### Core Functions

| Function | Module | Purpose |
|----------|--------|---------|
| `normalize_url()` | url_utils.py | Convert relative URLs, remove fragments |
| `is_internal_link()` | url_utils.py | Check if URL is same domain |
| `is_within_doc_path()` | url_utils.py | Ensure URL stays within doc prefix |
| `is_valid_doc_page()` | url_utils.py | Filter out non-document resources |
| `extract_links()` | url_utils.py | Parse HTML and extract valid links |
| `is_error_page()` | crawler.py | Detect 404-style content (HTTP 200) |
| `sanitize_html()` | converter.py | Remove nav/overlay elements for PDF |

## Development Commands

### Running the Application

```bash
# Basic usage
python -m src.main https://docs.example.com/

# With options
python -m src.main https://docs.example.com/ \
    --output documentation.pdf \
    --max-depth 8 \
    --delay 1.0 \
    --verbose \
    --max-pages 10  # For testing
```

### Running Tests

```bash
# Using pytest
python -m pytest tests/ -v

# Using unittest
python -m unittest discover tests/
```

### Installing Dependencies

```bash
pip install -r requirements.txt

# Also requires wkhtmltopdf system installation
# and playwright browser installation:
playwright install chromium
```

## Code Conventions

### Style Guidelines

- **Type hints:** Full type annotations on all functions
- **Docstrings:** Google-style docstrings with Args/Returns sections
- **Naming:** snake_case for functions/variables, PascalCase for classes
- **Logging:** Use `logging.getLogger(__name__)` for module loggers
- **Imports:** Standard library first, then third-party, then local

### Example Function Signature

```python
def normalize_url(url: str, base_url: str) -> str:
    """
    Normalize a URL by converting relative URLs to absolute.

    Args:
        url: The URL to normalize (can be relative or absolute).
        base_url: The base URL to resolve relative URLs against.

    Returns:
        A normalized absolute URL without fragments.
    """
```

### Pattern Conventions

1. **Data classes** for immutable data structures
2. **Context managers** for browser/file lifecycle management
3. **Set-based tracking** for O(1) visited URL lookups
4. **BFS traversal** to maintain logical page order
5. **Graceful degradation** - continue if some pages fail

## Dependencies

| Package | Purpose |
|---------|---------|
| `playwright` | Browser automation with stealth mode |
| `beautifulsoup4` + `lxml` | HTML parsing |
| `pdfkit` | HTML to PDF (wraps wkhtmltopdf) |
| `PyPDF2` | PDF merging with bookmarks |
| `PyMuPDF` (fitz) | Page number insertion |
| `requests` | HTTP requests (fallback) |

**System requirement:** wkhtmltopdf must be installed separately.

## Testing

Tests use Python's `unittest` framework:

- **test_url_utils.py** - 10 test classes covering URL normalization, filtering, extraction
- **test_crawler.py** - 6 test classes covering config, state tracking, error detection

### Test Patterns

```python
class TestNormalizeUrl(unittest.TestCase):
    """Tests for the normalize_url function."""

    def test_relative_url_same_directory(self):
        """Test normalizing a relative URL in the same directory."""
        base = "https://docs.example.com/guide/start/"
        url = "intro.html"
        expected = "https://docs.example.com/guide/start/intro.html"
        self.assertEqual(normalize_url(url, base), expected)
```

## Key Implementation Details

### Stealth Mode (Anti-Bot Detection)

The crawler uses multiple techniques (`crawler.py`):
- Randomized 2-4 second delays between requests
- Browser context reset every 10 requests
- Custom headers mimicking Chrome
- JavaScript stealth scripts hiding automation markers

### Error Page Filtering

Detects HTTP 200 responses with error content (`crawler.py:29-37`):
```python
ERROR_PAGE_PATTERNS = [
    "the content you're looking for is not here",
    "page not found",
    "404 error",
    # ...
]
```

### HTML Sanitization

Removes overlay elements before PDF conversion (`converter.py:27-149`):
- Strips: nav, header, footer, aside, script tags
- Removes: fixed/absolute positioned elements
- Filters: MkDocs Material theme navigation classes
- Extracts: main content area when available

### Page Numbering

Page numbers are added post-merge using PyMuPDF (`merger.py:134-173`) to ensure sequential numbering across all pages rather than each page showing "1".

## Common Tasks

### Adding New URL Filters

Edit `url_utils.py`:
- Add extensions to `excluded_extensions` set (line 152)
- Add paths to `excluded_patterns` list (line 168)

### Adding Error Page Patterns

Edit `crawler.py`:
- Add patterns to `ERROR_PAGE_PATTERNS` list (line 29)

### Modifying PDF Styling

Edit `converter.py`:
- Modify `PDF_OPTIONS` dict (line 153) for margins/page size
- Update `sanitize_html()` for content filtering

## Git Workflow

- Main development branch: `main`
- Generated PDFs are gitignored
- Commit messages should be descriptive of changes

## Troubleshooting

### Bot Detection Issues

If crawling is blocked:
1. Increase delay: `--delay 2.0`
2. Reduce depth: `--max-depth 5`
3. The crawler auto-resets context every 10 requests

### wkhtmltopdf Not Found

On Windows, the converter checks common installation paths:
- `C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe`
- `C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe`

### Missing Pages in Output

Check if pages are being filtered:
- Error page detection (`is_error_page()`)
- URL path filtering (`is_within_doc_path()`)
- Resource file filtering (`is_valid_doc_page()`)

Run with `--verbose` to see which pages are skipped and why.
