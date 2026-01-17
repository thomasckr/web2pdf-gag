"""
Web Documentation to PDF Converter - Main Entry Point.

This module provides the command-line interface for crawling documentation
sites and converting them to a merged PDF file.

Usage:
    python -m src.main https://docs.example.com/ -o documentation.pdf
    python -m src.main --help
"""

import argparse
import logging
import sys
from pathlib import Path

from .config import CrawlerConfig
from .crawler import WebCrawler
from .converter import PDFConverter
from .merger import PDFMerger


def setup_logging(verbose: bool = False) -> None:
    """
    Configure logging for the application.
    
    Args:
        verbose: If True, set log level to DEBUG; otherwise INFO.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description='Crawl web documentation and convert to PDF.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic usage with default settings
    python -m src.main https://docs.example.com/
    
    # Specify output filename
    python -m src.main https://docs.example.com/ -o my_docs.pdf
    
    # Limit crawl depth and add delay
    python -m src.main https://docs.example.com/ --max-depth 5 --delay 1.0
    
    # Verbose output for debugging
    python -m src.main https://docs.example.com/ -v
        """
    )
    
    parser.add_argument(
        'url',
        help='Base URL of the documentation site to crawl'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='documentation.pdf',
        help='Output PDF filename (default: documentation.pdf)'
    )
    
    parser.add_argument(
        '--max-depth',
        type=int,
        default=10,
        help='Maximum crawl depth (default: 10)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=0.5,
        help='Delay between requests in seconds (default: 0.5)'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--max-pages',
        type=int,
        default=None,
        help='Maximum number of pages to convert (for testing)'
    )
    
    return parser.parse_args()


def main() -> int:
    """
    Main entry point for the web documentation to PDF converter.
    
    Orchestrates the crawl -> convert -> merge pipeline.
    
    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    args = parse_arguments()
    setup_logging(args.verbose)
    
    logger = logging.getLogger(__name__)
    
    # Create configuration from arguments
    config = CrawlerConfig(
        base_url=args.url,
        output_filename=args.output,
        max_depth=args.max_depth,
        crawl_delay=args.delay,
        timeout=args.timeout
    )
    
    logger.info("=" * 60)
    logger.info("Web Documentation to PDF Converter")
    logger.info("=" * 60)
    logger.info(f"Base URL: {config.base_url}")
    logger.info(f"Output: {config.output_filename}")
    logger.info(f"Max Depth: {config.max_depth}")
    if args.max_pages:
        logger.info(f"Max Pages: {args.max_pages}")
    logger.info("=" * 60)
    
    # Step 1: Crawl the documentation site
    logger.info("Phase 1: Crawling documentation site...")
    crawler = WebCrawler(config)
    crawl_result = crawler.crawl()
    
    if not crawl_result.pages:
        logger.error("No pages were crawled successfully. Exiting.")
        return 1
    
    logger.info(f"Crawled {len(crawl_result.pages)} pages successfully.")
    
    # Limit pages if --max-pages is specified
    if args.max_pages and len(crawl_result.pages) > args.max_pages:
        logger.info(f"Limiting to first {args.max_pages} pages for testing")
        crawl_result.pages = crawl_result.pages[:args.max_pages]
    
    if crawl_result.failed_urls:
        logger.warning(f"Failed to crawl {len(crawl_result.failed_urls)} URLs")
    
    # Step 2: Convert pages to PDF
    logger.info("Phase 2: Converting pages to PDF...")
    converter = PDFConverter()
    
    try:
        conversion_results = converter.convert_pages(crawl_result.pages)
        
        successful_conversions = sum(1 for r in conversion_results if r.success)
        logger.info(f"Converted {successful_conversions}/{len(crawl_result.pages)} pages to PDF.")
        
        if successful_conversions == 0:
            logger.error("No pages were converted successfully. Exiting.")
            return 1
        
        # Step 3: Merge PDFs
        logger.info("Phase 3: Merging PDFs...")
        merger = PDFMerger()
        merge_result = merger.merge(
            conversion_results,
            crawl_result.pages,
            config.output_filename
        )
        
        if merge_result.success:
            logger.info("=" * 60)
            logger.info("SUCCESS!")
            logger.info(f"Output file: {merge_result.output_path}")
            logger.info(f"Total pages: {merge_result.total_pages}")
            logger.info("=" * 60)
            return 0
        else:
            logger.error(f"Failed to merge PDFs: {merge_result.error_message}")
            return 1
            
    finally:
        # Cleanup temporary files
        converter.cleanup()


if __name__ == '__main__':
    sys.exit(main())
