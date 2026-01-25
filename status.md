# Web2PDF Project Status

**Version:** v0.3  
**Last Updated:** 2026-01-24

## ✅ Project Status: COMPLETE

The web documentation to PDF converter is **fully implemented** and functional.

---

## Release v0.3 Highlights

### Bug Fixes
- **Fixed version-less URL handling** - Sites with navigation links that omit version numbers (e.g., `/product/subpath/` instead of `/product/25.10/subpath/`) are now properly crawled

### New Features
- **URL version rewriting** - `rewrite_versioned_url()` function automatically injects version numbers from the base URL into version-less navigation links
- **Enhanced path matching** - `is_within_doc_path()` now matches URLs with different version segment patterns

### Test Results
HP Anyware Connector 25.10 documentation:
- **Pages crawled:** 30
- **PDF pages generated:** 48
- **Output file:** `anyware_connector_25.10.pdf`

---

## Release v0.2 Highlights

### Bug Fixes
- **Fixed error page inclusion** - Custom 404-style error pages (HTTP 200 with "content not found" messages) are now filtered out instead of being included in the PDF output

### New Features
- **Error page detection** - `is_error_page()` function detects common error patterns in HTML content
- **Extended error patterns** - Supports HP-style "content you're looking for is not here" and other common 404 messages

### Test Results
HP Anyware Manager as a Service documentation:
- **Before fix:** 72 pages crawled → 109 PDF pages (including error pages)
- **After fix:** 66 pages crawled → 103 PDF pages (error pages filtered)
- **Error pages filtered:** 6

---

## Release v0.1 Highlights

### Bug Fixes
- **Fixed hyperlink overlap** - MkDocs Material theme elements (headerlinks, sticky headers/sidebars) no longer appear on top of text
- **Fixed page numbering** - Pages now show correct sequential numbers (was showing "1" on every page)
- **Fixed crawler scope** - Crawler now stays within documentation path only (was crawling entire site)

### New Features
- **Path-based filtering** - `is_within_doc_path()` restricts crawling to documentation subdirectory
- **Post-merge page numbering** - PyMuPDF adds sequential page numbers after PDF merge
- **Enhanced URL filtering** - Expanded excluded patterns for non-documentation paths

---

## Implementation Summary

| Component | File | Status |
|-----------|------|--------|
| Configuration | `src/config.py` | ✅ Complete |
| URL Utilities | `src/url_utils.py` | ✅ Complete |
| Web Crawler | `src/crawler.py` | ✅ Complete |
| PDF Converter | `src/converter.py` | ✅ Complete |
| PDF Merger | `src/merger.py` | ✅ Complete |
| CLI Entry Point | `src/main.py` | ✅ Complete |
| Unit Tests | `tests/` | ✅ Complete |
| Documentation | `README.md` | ✅ Complete |

---

## Key Features

1. **Playwright-based Crawler** - Real browser with stealth mode for JavaScript rendering and bot detection bypass

2. **URL Filtering** - Filters external links, excludes assets, restricts to documentation path

3. **Error Page Detection** - Filters out 404-style error pages that return HTTP 200 *(new in v0.2)*

4. **Versioned URL Rewriting** - Automatically injects version numbers into version-less navigation links *(new in v0.3)*

5. **PDF Conversion** - wkhtmltopdf via pdfkit with sanitized HTML (removes overlays, navigation elements)

6. **PDF Merging** - PyPDF2 merging with bookmarks + PyMuPDF page numbering

7. **CLI Interface** - Custom output, configurable depth, adjustable delay, verbose logging

---

## Usage

```bash
# Basic usage
python -m src.main https://docs.example.com/

# With options
python -m src.main https://docs.example.com/ \
    --output documentation.pdf \
    --max-depth 8 \
    --delay 1.0 \
    --verbose
```

---

## Dependencies

- **playwright** - Browser automation with stealth
- **beautifulsoup4** + **lxml** - HTML parsing
- **pdfkit** + wkhtmltopdf - HTML to PDF conversion
- **PyPDF2** - PDF merging
- **PyMuPDF** - Page numbering (added in v0.1)
- **requests** - HTTP requests (fallback)

---

## Repository

GitHub: https://github.com/thomasckr/web2pdf-gag

