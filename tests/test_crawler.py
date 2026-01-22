"""
Unit Tests for the Web Crawler.

These tests validate the crawler's state management, URL tracking,
and crawl behavior.
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import CrawlerConfig
from src.crawler import WebCrawler, CrawledPage, CrawlResult, is_error_page


class TestCrawlerConfig(unittest.TestCase):
    """Tests for CrawlerConfig dataclass."""
    
    def test_default_values(self):
        """Test that default configuration values are set correctly."""
        config = CrawlerConfig(base_url="https://example.com/")
        
        self.assertEqual(config.output_filename, "documentation.pdf")
        self.assertEqual(config.max_depth, 10)
        self.assertEqual(config.crawl_delay, 0.5)
        self.assertEqual(config.timeout, 30)
        self.assertEqual(config.max_retries, 3)
    
    def test_custom_values(self):
        """Test that custom configuration values override defaults."""
        config = CrawlerConfig(
            base_url="https://example.com/",
            output_filename="custom.pdf",
            max_depth=5,
            crawl_delay=1.0
        )
        
        self.assertEqual(config.output_filename, "custom.pdf")
        self.assertEqual(config.max_depth, 5)
        self.assertEqual(config.crawl_delay, 1.0)


class TestWebCrawler(unittest.TestCase):
    """Tests for WebCrawler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = CrawlerConfig(
            base_url="https://docs.example.com/",
            max_depth=2,
            crawl_delay=0  # No delay for tests
        )
        self.crawler = WebCrawler(self.config)
    
    def test_visited_tracking(self):
        """Test that visited URLs are tracked correctly."""
        self.crawler.visited_urls.add("https://docs.example.com/page1")
        self.crawler.visited_urls.add("https://docs.example.com/page2")
        
        self.assertIn("https://docs.example.com/page1", self.crawler.visited_urls)
        self.assertIn("https://docs.example.com/page2", self.crawler.visited_urls)
        self.assertNotIn("https://docs.example.com/page3", self.crawler.visited_urls)
    
    def test_no_duplicate_visits(self):
        """Test that URLs are not visited twice."""
        # Add the same URL multiple times
        self.crawler.visited_urls.add("https://docs.example.com/page1")
        self.crawler.visited_urls.add("https://docs.example.com/page1")
        
        # Should only have one entry
        self.assertEqual(len(self.crawler.visited_urls), 1)
    
    def test_session_headers(self):
        """Test that the session has proper browser headers."""
        headers = self.crawler.session.headers
        
        self.assertIn("User-Agent", headers)
        self.assertIn("Accept", headers)
        self.assertIn("Mozilla", headers["User-Agent"])
    
    @patch.object(WebCrawler, 'fetch_page')
    def test_crawl_respects_max_depth(self, mock_fetch):
        """Test that crawling respects max_depth setting."""
        # Configure mock to return HTML with links
        def return_html(url):
            if "page" not in url:
                # Root page
                return '''
                <html>
                <head><title>Root</title></head>
                <body>
                    <a href="page1.html">Page 1</a>
                </body>
                </html>
                '''
            elif "page1" in url:
                return '''
                <html>
                <head><title>Page 1</title></head>
                <body>
                    <a href="page2.html">Page 2</a>
                </body>
                </html>
                '''
            elif "page2" in url:
                return '''
                <html>
                <head><title>Page 2</title></head>
                <body>
                    <a href="page3.html">Page 3</a>
                </body>
                </html>
                '''
            else:
                return '<html><head><title>Page</title></head><body></body></html>'
        
        mock_fetch.side_effect = return_html
        
        # Set max_depth to 1 (should only get root and page1)
        self.config.max_depth = 1
        crawler = WebCrawler(self.config)
        result = crawler.crawl()
        
        # Should have crawled root (depth 0) and page1 (depth 1)
        # page2 would be at depth 2, which exceeds max_depth
        self.assertLessEqual(len(result.pages), 2)


class TestCrawledPage(unittest.TestCase):
    """Tests for CrawledPage dataclass."""
    
    def test_crawled_page_creation(self):
        """Test creating a CrawledPage instance."""
        page = CrawledPage(
            url="https://docs.example.com/guide",
            title="User Guide",
            html_content="<html>...</html>",
            depth=1
        )
        
        self.assertEqual(page.url, "https://docs.example.com/guide")
        self.assertEqual(page.title, "User Guide")
        self.assertEqual(page.depth, 1)


class TestCrawlResult(unittest.TestCase):
    """Tests for CrawlResult dataclass."""
    
    def test_empty_result(self):
        """Test creating an empty CrawlResult."""
        result = CrawlResult()
        
        self.assertEqual(len(result.pages), 0)
        self.assertEqual(len(result.failed_urls), 0)
        self.assertEqual(len(result.skipped_urls), 0)
    
    def test_result_with_data(self):
        """Test CrawlResult with pages and errors."""
        result = CrawlResult()
        
        result.pages.append(CrawledPage(
            url="https://example.com/",
            title="Home",
            html_content="<html></html>",
            depth=0
        ))
        result.failed_urls.append("https://example.com/broken")
        result.skipped_urls.append("https://external.com/")
        
        self.assertEqual(len(result.pages), 1)
        self.assertEqual(len(result.failed_urls), 1)
        self.assertEqual(len(result.skipped_urls), 1)


class TestErrorPageDetection(unittest.TestCase):
    """Tests for is_error_page() function."""
    
    def test_detects_hp_error_page(self):
        """Test detection of HP's custom 404 error page."""
        html = '''
        <html>
        <head><title>Error</title></head>
        <body>
            <h1>The content you're looking for is not here.</h1>
            <p>If you think there's been a mistake, please open a support ticket.</p>
        </body>
        </html>
        '''
        self.assertTrue(is_error_page(html))
    
    def test_detects_page_not_found(self):
        """Test detection of 'Page not found' error."""
        html = '<html><body><h1>Page Not Found</h1></body></html>'
        self.assertTrue(is_error_page(html))
    
    def test_detects_404_error(self):
        """Test detection of 404 error message."""
        html = '<html><body><h1>404 Error</h1><p>The page does not exist.</p></body></html>'
        self.assertTrue(is_error_page(html))
    
    def test_valid_page_not_detected_as_error(self):
        """Test that valid documentation pages are not flagged as errors."""
        html = '''
        <html>
        <head><title>Installation Guide</title></head>
        <body>
            <h1>Installation Guide</h1>
            <p>This guide explains how to install the software.</p>
        </body>
        </html>
        '''
        self.assertFalse(is_error_page(html))
    
    def test_case_insensitive_matching(self):
        """Test that error detection is case-insensitive."""
        html = '<html><body>THE CONTENT YOU\'RE LOOKING FOR IS NOT HERE</body></html>'
        self.assertTrue(is_error_page(html))


if __name__ == '__main__':
    unittest.main()

