"""
Web Crawler for Documentation Sites.

This module implements the core crawling logic for traversing documentation
websites. It uses Playwright for browser-based page fetching with stealth
techniques to handle JavaScript-rendered content and bypass bot detection.
"""

import time
import logging
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeout

from .config import CrawlerConfig
from .url_utils import normalize_url, rewrite_versioned_url, extract_links, get_page_title, is_internal_link, is_within_doc_path


# Configure logging for the crawler module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Error page detection patterns (common 404-style messages that return HTTP 200)
ERROR_PAGE_PATTERNS = [
    "the content you're looking for is not here",
    "page not found",
    "this page does not exist",
    "content not available",
    "404 error",
    "404 - page not found",
    "the requested page could not be found",
]


def is_error_page(html_content: str) -> bool:
    """
    Check if the page content indicates an error/missing page.
    
    Some websites return HTTP 200 with error content instead of proper 404s.
    This function detects common error page patterns to filter them out.
    
    Args:
        html_content: The HTML content to check.
        
    Returns:
        True if the content appears to be an error page, False otherwise.
    """
    content_lower = html_content.lower()
    for pattern in ERROR_PAGE_PATTERNS:
        if pattern in content_lower:
            return True
    return False


@dataclass
class CrawledPage:
    """
    Represents a single crawled documentation page.
    
    Attributes:
        url: The URL of the page.
        title: The extracted page title.
        html_content: The raw HTML content of the page.
        depth: The crawl depth at which this page was discovered.
    """
    url: str
    title: str
    html_content: str
    depth: int


@dataclass
class CrawlResult:
    """
    Contains the complete results of a crawl operation.
    
    Attributes:
        pages: List of successfully crawled pages in discovery order.
        failed_urls: List of URLs that failed to fetch.
        skipped_urls: List of URLs that were skipped (external or invalid).
    """
    pages: List[CrawledPage] = field(default_factory=list)
    failed_urls: List[str] = field(default_factory=list)
    skipped_urls: List[str] = field(default_factory=list)


class WebCrawler:
    """
    A web crawler for documentation sites using Playwright with stealth mode.
    
    This crawler uses a real browser to render JavaScript content,
    bypassing bot detection with stealth techniques including:
    - Randomized delays between requests
    - Periodic browser context resets
    - Human-like browser fingerprint
    """
    
    def __init__(self, config: CrawlerConfig):
        """
        Initialize the web crawler with the given configuration.
        
        Args:
            config: A CrawlerConfig object containing crawl settings.
        """
        self.config = config
        self.visited_urls: Set[str] = set()
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.request_count = 0
        self.max_requests_per_context = 10  # Reset context after this many requests
        
    def _start_browser(self):
        """Start the Playwright browser with stealth settings."""
        logger.info("Starting browser with stealth mode...")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
            ]
        )
        self._create_context()
        logger.info("Browser started successfully")
    
    def _create_context(self):
        """Create a new browser context with stealth settings."""
        if self.context:
            self.context.close()
        
        self.context = self.browser.new_context(
            user_agent=self.config.user_agent,
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            java_script_enabled=True,
        )
        
        # Add stealth scripts to hide automation
        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        """)
        
        self.page = self.context.new_page()
        self.request_count = 0
    
    def _stop_browser(self):
        """Stop the Playwright browser."""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("Browser stopped")
    
    def _random_delay(self):
        """Add a random delay to mimic human behavior."""
        delay = random.uniform(2.0, 4.0)  # Longer delays to avoid detection
        time.sleep(delay)
    
    def fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch the HTML content of a single page using Playwright.
        
        Args:
            url: The URL to fetch.
            
        Returns:
            The HTML content as a string, or None if the fetch failed.
        """
        try:
            # Reset context periodically to avoid detection
            self.request_count += 1
            if self.request_count >= self.max_requests_per_context:
                logger.info("Resetting browser context to avoid detection...")
                self._create_context()
            
            # Navigate to the page
            self.page.goto(url, wait_until='domcontentloaded', timeout=self.config.timeout * 1000)
            
            # Wait for page to fully render
            time.sleep(2)
            
            # Try to wait for network to be idle
            try:
                self.page.wait_for_load_state('networkidle', timeout=10000)
            except PlaywrightTimeout:
                pass  # Continue even if network doesn't become idle
            
            # Get the page content
            content = self.page.content()
            
            # Check if we got a valid page (not a bot detection page)
            if 'JavaScript is disabled' in content or 'verify that you\'re not a robot' in content.lower():
                logger.warning(f"Bot detection triggered for {url}, waiting longer...")
                # Wait longer and try again
                time.sleep(5)
                content = self.page.content()
                
                if 'JavaScript is disabled' in content:
                    return None  # Still blocked
            
            return content
            
        except PlaywrightTimeout:
            logger.error(f"Timeout loading {url}")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
    
    def crawl(self) -> CrawlResult:
        """
        Perform a complete crawl starting from the base URL.
        
        Uses breadth-first search to traverse the documentation site,
        maintaining the order in which pages appear in the navigation.
        
        Returns:
            A CrawlResult containing all crawled pages and any errors.
        """
        result = CrawlResult()
        
        # Start the browser
        self._start_browser()
        
        try:
            # Queue entries are (url, depth) tuples
            queue: deque[Tuple[str, int]] = deque()
            
            # Normalize and enqueue the starting URL
            start_url = normalize_url(self.config.base_url, self.config.base_url)
            queue.append((start_url, 0))
            self.visited_urls.add(start_url)
            
            logger.info(f"Starting crawl from: {start_url}")
            logger.info(f"Max depth: {self.config.max_depth}")
            
            while queue:
                current_url, depth = queue.popleft()
                
                # Skip if we've exceeded max depth
                if depth > self.config.max_depth:
                    logger.debug(f"Skipping {current_url}: exceeded max depth")
                    continue
                
                logger.info(f"Crawling [{depth}] ({len(result.pages)} done): {current_url}")
                
                # Add random delay to mimic human behavior
                self._random_delay()
                
                # Fetch the page content
                html_content = self.fetch_page(current_url)
                
                if html_content is None:
                    result.failed_urls.append(current_url)
                    continue
                
                # Check if we got actual content (not bot detection)
                if 'JavaScript is disabled' in html_content:
                    logger.warning(f"Skipping bot-blocked page: {current_url}")
                    result.failed_urls.append(current_url)
                    continue
                
                # Check if we got an error page (404-style content with HTTP 200)
                if is_error_page(html_content):
                    logger.warning(f"Skipping error page: {current_url}")
                    result.failed_urls.append(current_url)
                    continue
                
                # Extract page title and create CrawledPage
                title = get_page_title(html_content)
                page = CrawledPage(
                    url=current_url,
                    title=title,
                    html_content=html_content,
                    depth=depth
                )
                result.pages.append(page)
                
                # Extract and enqueue new links
                links = extract_links(html_content, current_url)
                
                for link in links:
                    normalized_link = normalize_url(link, current_url)
                    # Rewrite version-less URLs to include the version from base URL
                    normalized_link = rewrite_versioned_url(normalized_link, self.config.base_url)
                    
                    # Skip already visited URLs
                    if normalized_link in self.visited_urls:
                        continue
                    
                    # Skip external URLs (double-check)
                    if not is_internal_link(normalized_link, self.config.base_url):
                        result.skipped_urls.append(normalized_link)
                        continue
                    
                    # Skip URLs outside the documentation path
                    if not is_within_doc_path(normalized_link, self.config.base_url):
                        result.skipped_urls.append(normalized_link)
                        continue
                    
                    # Add to queue and mark as visited
                    self.visited_urls.add(normalized_link)
                    queue.append((normalized_link, depth + 1))
            
            logger.info(f"Crawl complete. Pages: {len(result.pages)}, "
                       f"Failed: {len(result.failed_urls)}, "
                       f"Skipped: {len(result.skipped_urls)}")
            
            return result
        
        finally:
            # Always stop the browser
            self._stop_browser()
