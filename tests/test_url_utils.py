"""
Unit Tests for URL Utilities.

These tests validate the URL filtering, normalization, and link extraction
functions to ensure external links are correctly rejected and internal
links are properly processed.
"""

import unittest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.url_utils import (
    normalize_url,
    is_internal_link,
    is_valid_doc_page,
    extract_links,
    get_page_title,
    get_domain
)


class TestNormalizeUrl(unittest.TestCase):
    """Tests for the normalize_url function."""
    
    def test_relative_url_same_directory(self):
        """Test normalizing a relative URL in the same directory."""
        base = "https://docs.example.com/guide/start/"
        url = "intro.html"
        expected = "https://docs.example.com/guide/start/intro.html"
        self.assertEqual(normalize_url(url, base), expected)
    
    def test_relative_url_parent_directory(self):
        """Test normalizing a relative URL with parent directory reference."""
        base = "https://docs.example.com/guide/start/"
        url = "../overview.html"
        expected = "https://docs.example.com/guide/overview.html"
        self.assertEqual(normalize_url(url, base), expected)
    
    def test_absolute_url_same_domain(self):
        """Test that absolute URLs on same domain are returned as-is."""
        base = "https://docs.example.com/guide/"
        url = "https://docs.example.com/api/reference.html"
        expected = "https://docs.example.com/api/reference.html"
        self.assertEqual(normalize_url(url, base), expected)
    
    def test_fragment_removal(self):
        """Test that URL fragments are removed."""
        base = "https://docs.example.com/"
        url = "page.html#section-2"
        result = normalize_url(url, base)
        self.assertNotIn('#', result)
        self.assertEqual(result, "https://docs.example.com/page.html")
    
    def test_root_relative_url(self):
        """Test normalizing a root-relative URL."""
        base = "https://docs.example.com/deep/nested/path/"
        url = "/api/docs.html"
        expected = "https://docs.example.com/api/docs.html"
        self.assertEqual(normalize_url(url, base), expected)


class TestIsInternalLink(unittest.TestCase):
    """Tests for the is_internal_link function."""
    
    def test_same_domain_is_internal(self):
        """Test that same domain URLs are considered internal."""
        base = "https://docs.example.com/"
        url = "https://docs.example.com/page.html"
        self.assertTrue(is_internal_link(url, base))
    
    def test_different_domain_is_external(self):
        """Test that different domain URLs are considered external."""
        base = "https://docs.example.com/"
        url = "https://external.com/page.html"
        self.assertFalse(is_internal_link(url, base))
    
    def test_subdomain_is_external(self):
        """Test that subdomain URLs are considered external."""
        base = "https://docs.example.com/"
        url = "https://api.example.com/reference.html"
        self.assertFalse(is_internal_link(url, base))
    
    def test_relative_url_is_internal(self):
        """Test that relative URLs are always considered internal."""
        base = "https://docs.example.com/"
        url = "subpage/intro.html"
        self.assertTrue(is_internal_link(url, base))
    
    def test_root_relative_is_internal(self):
        """Test that root-relative URLs are considered internal."""
        base = "https://docs.example.com/section/"
        url = "/api/docs.html"
        self.assertTrue(is_internal_link(url, base))
    
    def test_protocol_relative_external(self):
        """Test that protocol-relative external URLs are detected."""
        base = "https://docs.example.com/"
        url = "//external.example.org/page"
        self.assertFalse(is_internal_link(url, base))
    
    def test_case_insensitive_domain_matching(self):
        """Test that domain matching is case-insensitive."""
        base = "https://Docs.Example.COM/"
        url = "https://docs.example.com/page.html"
        self.assertTrue(is_internal_link(url, base))


class TestIsValidDocPage(unittest.TestCase):
    """Tests for the is_valid_doc_page function."""
    
    def test_html_page_is_valid(self):
        """Test that HTML pages are considered valid."""
        self.assertTrue(is_valid_doc_page("https://docs.example.com/guide.html"))
    
    def test_no_extension_is_valid(self):
        """Test that URLs without extension are considered valid."""
        self.assertTrue(is_valid_doc_page("https://docs.example.com/guide/"))
    
    def test_css_file_is_invalid(self):
        """Test that CSS files are filtered out."""
        self.assertFalse(is_valid_doc_page("https://docs.example.com/style.css"))
    
    def test_js_file_is_invalid(self):
        """Test that JavaScript files are filtered out."""
        self.assertFalse(is_valid_doc_page("https://docs.example.com/app.js"))
    
    def test_image_file_is_invalid(self):
        """Test that image files are filtered out."""
        self.assertFalse(is_valid_doc_page("https://docs.example.com/logo.png"))
        self.assertFalse(is_valid_doc_page("https://docs.example.com/photo.jpg"))
        self.assertFalse(is_valid_doc_page("https://docs.example.com/icon.svg"))
    
    def test_pdf_file_is_invalid(self):
        """Test that PDF files are filtered out."""
        self.assertFalse(is_valid_doc_page("https://docs.example.com/manual.pdf"))
    
    def test_assets_path_is_invalid(self):
        """Test that asset paths are filtered out."""
        self.assertFalse(is_valid_doc_page("https://docs.example.com/assets/image.png"))
        self.assertFalse(is_valid_doc_page("https://docs.example.com/static/bundle.js"))


class TestExtractLinks(unittest.TestCase):
    """Tests for the extract_links function."""
    
    def test_extract_simple_links(self):
        """Test extracting simple anchor links."""
        html = '''
        <html>
        <body>
            <a href="page1.html">Page 1</a>
            <a href="page2.html">Page 2</a>
        </body>
        </html>
        '''
        base = "https://docs.example.com/"
        links = extract_links(html, base)
        
        self.assertIn("https://docs.example.com/page1.html", links)
        self.assertIn("https://docs.example.com/page2.html", links)
    
    def test_external_links_filtered(self):
        """Test that external links are filtered out."""
        html = '''
        <html>
        <body>
            <a href="internal.html">Internal</a>
            <a href="https://external.com/page">External</a>
        </body>
        </html>
        '''
        base = "https://docs.example.com/"
        links = extract_links(html, base)
        
        self.assertIn("https://docs.example.com/internal.html", links)
        self.assertNotIn("https://external.com/page", links)
    
    def test_javascript_links_skipped(self):
        """Test that javascript: links are skipped."""
        html = '''
        <a href="javascript:void(0)">Click me</a>
        <a href="real-page.html">Real page</a>
        '''
        base = "https://docs.example.com/"
        links = extract_links(html, base)
        
        self.assertEqual(len(links), 1)
        self.assertIn("https://docs.example.com/real-page.html", links)
    
    def test_mailto_links_skipped(self):
        """Test that mailto: links are skipped."""
        html = '''
        <a href="mailto:test@example.com">Email</a>
        <a href="page.html">Page</a>
        '''
        base = "https://docs.example.com/"
        links = extract_links(html, base)
        
        self.assertEqual(len(links), 1)
    
    def test_hash_only_links_skipped(self):
        """Test that pure fragment links are skipped."""
        html = '''
        <a href="#section">Jump to section</a>
        <a href="page.html">Page</a>
        '''
        base = "https://docs.example.com/"
        links = extract_links(html, base)
        
        self.assertEqual(len(links), 1)
    
    def test_asset_links_filtered(self):
        """Test that asset file links are filtered out."""
        html = '''
        <a href="style.css">Stylesheet</a>
        <a href="script.js">Script</a>
        <a href="image.png">Image</a>
        <a href="guide.html">Guide</a>
        '''
        base = "https://docs.example.com/"
        links = extract_links(html, base)
        
        self.assertEqual(len(links), 1)
        self.assertIn("https://docs.example.com/guide.html", links)


class TestGetPageTitle(unittest.TestCase):
    """Tests for the get_page_title function."""
    
    def test_title_from_title_tag(self):
        """Test extracting title from <title> tag."""
        html = '''
        <html>
        <head><title>My Page Title</title></head>
        <body><h1>Content Header</h1></body>
        </html>
        '''
        self.assertEqual(get_page_title(html), "My Page Title")
    
    def test_title_from_h1_fallback(self):
        """Test falling back to <h1> when no title tag."""
        html = '''
        <html>
        <body><h1>Main Heading</h1></body>
        </html>
        '''
        self.assertEqual(get_page_title(html), "Main Heading")
    
    def test_untitled_fallback(self):
        """Test fallback to 'Untitled Page' when no title or h1."""
        html = '<html><body><p>Just some text</p></body></html>'
        self.assertEqual(get_page_title(html), "Untitled Page")


class TestGetDomain(unittest.TestCase):
    """Tests for the get_domain function."""
    
    def test_extract_domain(self):
        """Test extracting domain from URL."""
        url = "https://docs.example.com/path/to/page"
        self.assertEqual(get_domain(url), "docs.example.com")
    
    def test_domain_lowercase(self):
        """Test that domain is returned lowercase."""
        url = "https://DOCS.EXAMPLE.COM/page"
        self.assertEqual(get_domain(url), "docs.example.com")


if __name__ == '__main__':
    unittest.main()
