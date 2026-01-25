# CLAUDE.md - AI Assistant Guide for Web2PDF-GAG

This document provides essential context for AI assistants working with this codebase.

## Project Overview

**Web2PDF-GAG** is a Python application that crawls documentation websites and converts them into a single, merged PDF file. It handles JavaScript-rendered pages, bot detection circumvention, and custom error page filtering.

- **Version:** v0.2
- **Status:** Complete and production-ready
- **Repository:** https://github.com/thomasckr/web2pdf-gag

## Quick Reference

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python -m src.main <URL> [options]

# Run tests
python -m pytest tests/ -v
# or
python -m unittest discover tests/
```

## Codebase Structure

```
web2pdf-gag/
├── src/                          # Main application code
│   ├── __init__.py              # Package initialization
│   ├── main.py                  # CLI entry point - orchestrates pipeline
│   ├── config.py                # CrawlerConfig dataclass with defaults
│   ├── crawler.py               # Playwright-based web crawler
│   ├── url_utils.py             # URL normalization, filtering, extraction
│   ├── converter.py             # HTML-to-PDF conversion with pdfkit
│   └── merger.py                # PDF merging with bookmarks & page numbers
├── tests/                        # Unit tests (unittest framework)
│   ├── test_url_utils.py        # URL utility tests
│   └── test_crawler.py          # Crawler tests
├── requirements.txt             # Python dependencies
├── README.md                    # User documentation
├── status.md                    # Release notes
└── .gitignore                   # Git exclusions
```

## Key Files and Their Purposes

| File | Purpose | Key Exports |
|------|---------|-------------|
| `main.py` | CLI entry point | `main()`, argument parsing |
| `crawler.py` | Web crawling | `DocumentationCrawler`, `CrawledPage`, `CrawlResult` |
| `url_utils.py` | URL processing | `normalize_url()`, `is_valid_doc_link()`, `extract_links()` |
| `converter.py` | PDF generation | `convert_html_to_pdf()`, `sanitize_html()` |
| `merger.py` | PDF merging | `merge_pdfs()`, `add_page_numbers()` |
| `config.py` | Configuration | `CrawlerConfig` dataclass |

## Architecture

The application follows a **pipeline pattern** with three phases:

```
1. CRAWL (crawler.py)
   └── Playwright browser automation
   └── BFS traversal with URL filtering
   └── Error page detection

2. CONVERT (converter.py)
   └── HTML sanitization
   └── pdfkit/wkhtmltopdf conversion
   └── Temporary file management

3. MERGE (merger.py)
   └── PyPDF2 merging with bookmarks
   └── PyMuPDF page numbering
```

## Technology Stack

| Category | Technology | Purpose |
|----------|------------|---------|
| Browser Automation | Playwright (sync_api) | JavaScript rendering, stealth mode |
| HTML Parsing | BeautifulSoup4 + lxml | Content extraction, link discovery |
| PDF Conversion | pdfkit + wkhtmltopdf | HTML to PDF |
| PDF Manipulation | PyPDF2 | Merging, bookmarks |
| Page Numbering | PyMuPDF (fitz) | Post-merge numbering |
| HTTP (fallback) | requests | Simple HTTP requests |

## Code Conventions

### Type Hints
All functions use type annotations:
```python
def normalize_url(url: str, base_url: str) -> str:
```

### Docstrings
Comprehensive docstrings at module, class, and function levels.

### Logging
Uses Python's `logging` module with DEBUG, INFO, WARNING, ERROR levels:
```python
logger = logging.getLogger(__name__)
logger.info("Processing page: %s", url)
```

### Error Handling
Graceful failure with logging - individual page failures don't crash the pipeline.

### Dataclasses
Immutable configuration and results:
```python
@dataclass
class CrawlerConfig:
    base_url: str
    max_depth: int = 10
    ...
```

## Important Implementation Details

### URL Filtering (`url_utils.py`)

**Excluded extensions:** `.css`, `.js`, `.png`, `.jpg`, `.pdf`, `.zip`, `.mp4`, `.woff`, `.json`, etc.

**Excluded paths:** `/api/`, `/assets/`, `/blog/`, `/support/`, `/saml_login`, `/oem-`

**Key functions:**
- `normalize_url()` - Relative to absolute, fragment removal
- `is_valid_doc_link()` - Filters non-documentation URLs
- `is_within_doc_path()` - Restricts to documentation subdirectory

### Bot Detection Bypass (`crawler.py`)

- Stealth scripts hide WebDriver detection
- Randomized delays (2-4 seconds)
- Browser context reset every 10 requests
- User-Agent spoofing (Chrome 120.0)

### Error Page Detection (`crawler.py`)

Detects HTTP 200 responses with 404 content. Patterns include:
- "the content you're looking for is not here"
- "page not found"
- "this page does not exist"
- "content not available"

### HTML Sanitization (`converter.py`)

Removes before PDF conversion:
- Navigation elements (`<nav>`, `.md-sidebar`, `.md-header`)
- MkDocs Material theme overlays
- Fixed positioning elements
- External resource loading disabled

### PDF Output (`merger.py`)

- A4 page size
- 20mm top/bottom, 15mm side margins
- Bookmarks generated from page titles
- Sequential page numbers added post-merge

## Testing Guidelines

### Test Framework
Python's `unittest` module with `mock.patch` for mocking.

### Running Tests
```bash
python -m pytest tests/ -v
python -m unittest discover tests/
```

### Test Coverage
- `test_url_utils.py` - URL normalization, filtering, link extraction
- `test_crawler.py` - Configuration, error detection, crawl results

### Writing Tests
- Mock external dependencies (Playwright, HTTP requests)
- Test edge cases (case sensitivity, protocol-relative URLs)
- Use descriptive test method names: `test_normalize_url_removes_fragments`

## CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `url` | Base documentation URL | Required |
| `-o, --output` | Output PDF filename | `documentation.pdf` |
| `--max-depth` | Maximum crawl depth | 10 |
| `--delay` | Delay between requests (seconds) | 0.5 |
| `--timeout` | Request timeout (seconds) | 30 |
| `-v, --verbose` | Enable debug logging | False |
| `--max-pages` | Limit pages (for testing) | None |

## Common Development Tasks

### Adding New URL Filters
Edit `url_utils.py`:
- Add to `EXCLUDED_EXTENSIONS` or `EXCLUDED_PATHS`
- Update `is_valid_doc_link()` for complex logic

### Modifying PDF Styling
Edit `converter.py`:
- Update `sanitize_html()` for content cleaning
- Modify pdfkit options for margins/headers

### Adding Error Page Patterns
Edit `crawler.py`:
- Add patterns to `is_error_page()` function
- Test with real pages that trigger false positives

### Debugging Crawl Issues
```bash
python -m src.main <URL> --verbose --max-pages 5
```

## External Dependencies

### System Requirements
- **wkhtmltopdf** - Must be installed separately for pdfkit
- **Playwright browsers** - Run `playwright install chromium`

### Installation Notes
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Install wkhtmltopdf (Ubuntu/Debian)
sudo apt-get install wkhtmltopdf
```

## Known Behaviors

1. **Crawl order** - BFS preserves navigation hierarchy
2. **Duplicate handling** - URLs normalized and tracked in visited set
3. **Error recovery** - Failed pages logged but don't stop processing
4. **Memory usage** - Large sites may require `--max-pages` limit
5. **Rate limiting** - Adjust `--delay` if getting blocked

## Changelog Summary

### v0.2
- Error page filtering (HTTP 200 with 404 content)
- Extended error pattern detection

### v0.1
- Fixed hyperlink overlap from MkDocs theme
- Fixed page numbering (was showing "1" on every page)
- Path-based crawl restriction
