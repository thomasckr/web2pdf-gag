"""
URL Utilities for the Web Documentation Crawler.

This module provides functions for URL normalization, validation,
and link extraction. It ensures that only internal documentation
links are followed while external links are filtered out.
"""

from urllib.parse import urlparse, urljoin, urldefrag
from typing import List, Set
from bs4 import BeautifulSoup
import re


def normalize_url(url: str, base_url: str) -> str:
    """
    Normalize a URL by converting relative URLs to absolute and removing fragments.
    
    This function handles:
    - Relative URLs (e.g., "../page.html" or "subpage/")
    - Fragment removal (e.g., "#section" anchors)
    - Trailing slash normalization
    
    Args:
        url: The URL to normalize (can be relative or absolute).
        base_url: The base URL to resolve relative URLs against.
        
    Returns:
        A normalized absolute URL without fragments.
        
    Example:
        >>> normalize_url("../intro.html", "https://docs.example.com/guide/start/")
        'https://docs.example.com/intro.html'
    """
    # Join with base URL to handle relative URLs
    absolute_url = urljoin(base_url, url)
    
    # Remove URL fragments (e.g., #section-id)
    defragged_url, _ = urldefrag(absolute_url)
    
    # Normalize trailing slashes for consistency
    # Keep trailing slash only for directory-like URLs
    if defragged_url.endswith('/') and '.' in defragged_url.split('/')[-2]:
        defragged_url = defragged_url.rstrip('/')
    
    return defragged_url


def get_domain(url: str) -> str:
    """
    Extract the domain (netloc) from a URL.
    
    Args:
        url: The URL to extract the domain from.
        
    Returns:
        The domain portion of the URL (e.g., "docs.example.com").
    """
    parsed = urlparse(url)
    return parsed.netloc.lower()


def is_internal_link(url: str, base_url: str) -> bool:
    """
    Check if a URL points to the same domain as the base URL.
    
    This function is crucial for filtering out external links during crawling.
    It considers a link internal if:
    - It has no domain (relative URL)
    - Its domain matches the base URL's domain
    
    Args:
        url: The URL to check.
        base_url: The base URL to compare domains against.
        
    Returns:
        True if the URL is internal, False otherwise.
        
    Example:
        >>> is_internal_link("https://docs.example.com/page", "https://docs.example.com/")
        True
        >>> is_internal_link("https://external.com/page", "https://docs.example.com/")
        False
    """
    parsed_url = urlparse(url)
    base_domain = get_domain(base_url)
    
    # Relative URLs are always internal
    if not parsed_url.netloc:
        return True
    
    # Compare domains (case-insensitive)
    url_domain = parsed_url.netloc.lower()
    return url_domain == base_domain


def is_within_doc_path(url: str, base_url: str) -> bool:
    """
    Check if a URL is within the same documentation path as the base URL.
    
    This restricts crawling to only pages that share the same path prefix
    as the starting URL (e.g., /web-help/anyware_manager_enterprise/).
    
    Args:
        url: The URL to check.
        base_url: The base URL containing the documentation path prefix.
        
    Returns:
        True if the URL is within the documentation path, False otherwise.
        
    Example:
        >>> is_within_doc_path(
        ...     "https://site.com/docs/guide/page", 
        ...     "https://site.com/docs/"
        ... )
        True
        >>> is_within_doc_path(
        ...     "https://site.com/blog/post", 
        ...     "https://site.com/docs/"
        ... )
        False
    """
    parsed_url = urlparse(url)
    parsed_base = urlparse(base_url)
    
    # Must be same domain first
    if parsed_url.netloc.lower() != parsed_base.netloc.lower():
        return False
    
    # Get the base path prefix (the documentation root)
    base_path = parsed_base.path.rstrip('/')
    url_path = parsed_url.path
    
    # URL must start with the base documentation path
    return url_path.startswith(base_path)


def is_valid_doc_page(url: str) -> bool:
    """
    Check if a URL points to a valid documentation page (not a resource file).
    
    This filters out non-document resources like images, stylesheets, scripts,
    and downloadable files that should not be converted to PDF.
    
    Args:
        url: The URL to validate.
        
    Returns:
        True if the URL likely points to a documentation page, False otherwise.
    """
    # Extensions that indicate non-document resources
    excluded_extensions = {
        '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
        '.pdf', '.zip', '.tar', '.gz', '.exe', '.dmg', '.msi',
        '.mp4', '.mp3', '.webm', '.woff', '.woff2', '.ttf', '.eot',
        '.json', '.xml', '.yaml', '.yml'
    }
    
    parsed = urlparse(url)
    path = parsed.path.lower()
    
    # Check if URL ends with an excluded extension
    for ext in excluded_extensions:
        if path.endswith(ext):
            return False
    
    # Exclude common non-documentation paths
    excluded_patterns = [
        '/api/', '/assets/', '/static/', '/images/', '/css/', '/js/',
        '/download/', '/downloads/', '/cdn/', '/_next/', '/_nuxt/',
        '/blog/', '/knowledge/', '/knowledge?', '/lifecycle/', '/partners/',
        '/support/', '/saml_login', '/find/', '/third-party-licenses/',
        '/sites/default/files/', '/taxonomy/', '/oem-', '/gpl-source-code',
        '/reference/eulas', '/support-programs', '/professional-services'
    ]
    
    for pattern in excluded_patterns:
        if pattern in path.lower():
            return False
    
    return True


def extract_links(html_content: str, base_url: str) -> List[str]:
    """
    Extract all valid internal documentation links from HTML content.
    
    This function parses the HTML, finds all anchor tags, and filters
    the links to include only internal documentation pages.
    
    Args:
        html_content: The raw HTML content to parse.
        base_url: The base URL for resolving relative links and domain checking.
        
    Returns:
        A list of normalized, unique internal URLs found in the HTML.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    links: Set[str] = set()
    
    # Find all anchor tags with href attributes
    for anchor in soup.find_all('a', href=True):
        href = anchor['href']
        
        # Skip empty hrefs, javascript links, and mailto links
        if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
            continue
        
        # Normalize the URL
        normalized = normalize_url(href, base_url)
        
        # Apply filters: must be internal and a valid doc page
        if is_internal_link(normalized, base_url) and is_valid_doc_page(normalized):
            links.add(normalized)
    
    return list(links)


def get_page_title(html_content: str) -> str:
    """
    Extract the page title from HTML content.
    
    Attempts to get the title from:
    1. The <title> tag
    2. The first <h1> tag
    3. Falls back to "Untitled Page"
    
    Args:
        html_content: The raw HTML content to parse.
        
    Returns:
        The extracted page title as a string.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Try to get title from <title> tag
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    
    # Try to get from first <h1>
    h1 = soup.find('h1')
    if h1 and h1.get_text():
        return h1.get_text().strip()
    
    return "Untitled Page"
