"""
Configuration module for the Web Documentation to PDF Converter.

This module contains all configurable settings for the crawler and converter.
Modify these values to customize the behavior for different documentation sites.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CrawlerConfig:
    """
    Configuration settings for the web crawler.
    
    Attributes:
        base_url: The root URL of the documentation site to crawl.
        output_filename: The name of the output PDF file.
        max_depth: Maximum crawl depth to prevent infinite recursion.
        crawl_delay: Delay (in seconds) between requests for politeness.
        user_agent: Custom User-Agent header for HTTP requests.
        timeout: Request timeout in seconds.
        max_retries: Number of retry attempts for failed requests.
    """
    base_url: str
    output_filename: str = "documentation.pdf"
    max_depth: int = 10
    crawl_delay: float = 0.5
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    timeout: int = 30
    max_retries: int = 3
    

# Default configuration for the HP Anyware Manager documentation
DEFAULT_CONFIG = CrawlerConfig(
    base_url="https://anyware.hp.com/web-help/anyware_manager_enterprise/",
    output_filename="anyware_manager_documentation.pdf",
    max_depth=10,
    crawl_delay=0.5
)
