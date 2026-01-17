"""
HTML to PDF Converter.

This module provides functionality to convert HTML content to PDF format
using pdfkit (wkhtmltopdf wrapper). It saves HTML to local files and
disables external resource loading to work with pre-fetched content.
"""

import logging
import tempfile
import os
import re
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

import pdfkit
from bs4 import BeautifulSoup

from .crawler import CrawledPage


# Configure logging
logger = logging.getLogger(__name__)


def sanitize_html(html_content: str) -> str:
    """
    Sanitize HTML content by removing navigation elements and overlays.
    
    This function removes:
    - Navigation elements (<nav>, <header>, <footer>, <aside>)
    - Elements with common navigation class names
    - Fixed/absolute positioned elements that overlay content
    - Script and style tags
    
    Args:
        html_content: The raw HTML content to sanitize.
        
    Returns:
        Sanitized HTML content suitable for PDF conversion.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Remove common navigation and overlay elements by tag
    tags_to_remove = ['nav', 'header', 'footer', 'aside', 'script', 'noscript']
    for tag in tags_to_remove:
        for element in soup.find_all(tag):
            element.decompose()
    
    # Common class patterns for navigation/overlay elements
    nav_class_patterns = [
        'nav', 'menu', 'sidebar', 'header', 'footer', 'breadcrumb',
        'toc', 'navigation', 'toolbar', 'topbar', 'top-bar',
        'navbar', 'nav-bar', 'sidenav', 'side-nav', 'side-menu',
        'mobile-menu', 'hamburger', 'overlay', 'modal', 'popup',
        'cookie', 'banner', 'search-box', 'search-form',
        # MkDocs Material theme specific
        'md-header', 'md-sidebar', 'md-footer', 'md-search', 'md-overlay',
        'md-tabs', 'md-source', 'headerlink'
    ]
    
    # Remove elements with navigation-related classes
    for pattern in nav_class_patterns:
        # Match class names that contain the pattern
        for element in soup.find_all(class_=re.compile(pattern, re.IGNORECASE)):
            element.decompose()
    
    # Remove elements with navigation-related IDs
    nav_id_patterns = ['nav', 'menu', 'sidebar', 'header', 'footer', 'toc', 'navigation', 'toolbar']
    for pattern in nav_id_patterns:
        for element in soup.find_all(id=re.compile(pattern, re.IGNORECASE)):
            element.decompose()
    
    # Remove elements with fixed or absolute positioning (they overlay content)
    for element in soup.find_all(style=True):
        style = element.get('style', '').lower()
        if 'position:' in style.replace(' ', ''):
            if 'fixed' in style or 'absolute' in style:
                # Check if this is a main content element - don't remove those
                element_classes = ' '.join(element.get('class', []))
                if 'content' not in element_classes.lower() and 'main' not in element_classes.lower():
                    element.decompose()
    
    # Remove empty anchor tags that might cause overlay issues
    for anchor in soup.find_all('a'):
        # Remove anchors that are purely for navigation (no visible text)
        text = anchor.get_text(strip=True)
        if not text and not anchor.find('img'):
            anchor.decompose()
    
    # Try to extract just the main content if a main content area exists
    main_content = (
        soup.find('main') or 
        soup.find(class_=re.compile(r'(content|main|article|documentation|docs)', re.IGNORECASE)) or
        soup.find('article') or
        soup.find(id=re.compile(r'(content|main)', re.IGNORECASE))
    )
    
    if main_content:
        # Wrap main content in basic HTML structure
        new_soup = BeautifulSoup('<html><head></head><body></body></html>', 'lxml')
        
        # Copy head elements (title, meta, styles) if they exist
        if soup.head:
            for child in soup.head.children:
                if hasattr(child, 'name') and child.name in ['title', 'meta', 'style']:
                    new_soup.head.append(child.extract())
        
        # Add main content to body
        new_soup.body.append(main_content.extract())
        soup = new_soup
    
    # Add CSS to hide any remaining overlay elements and clean up link styling
    cleanup_css = """
    <style>
        /* Hide any remaining overlay elements */
        [style*="position: fixed"], [style*="position:fixed"],
        [style*="position: absolute"], [style*="position:absolute"] {
            display: none !important;
        }
        /* Hide appended URLs that might be added by print stylesheets */
        a[href]:after { content: none !important; }
        @media print { a[href]:after { content: none !important; } }
        /* Ensure links don't have problematic styling */
        a { position: static !important; display: inline !important; }
        /* Clean up the layout */
        body { max-width: 100%; overflow-x: hidden; }
        /* MkDocs Material theme specific fixes */
        .md-header, .md-sidebar, .md-footer, .md-tabs, .md-search,
        .md-source, .md-overlay { display: none !important; }
        /* Hide headerlink anchors that appear next to headings */
        .headerlink, a.headerlink, .anchor-link { display: none !important; }
        /* Remove sticky/fixed positioning */
        * { position: static !important; }
        .md-content, .md-content__inner, .md-typeset, article, main {
            position: static !important;
            margin: 0 !important;
            padding: 10px !important;
            max-width: 100% !important;
            width: 100% !important;
        }
    </style>
    """
    
    if soup.head:
        soup.head.append(BeautifulSoup(cleanup_css, 'lxml'))
    
    return str(soup)


# pdfkit options - configured to work with local HTML without network access
PDF_OPTIONS = {
    'page-size': 'A4',
    'margin-top': '20mm',
    'margin-right': '15mm',
    'margin-bottom': '20mm',
    'margin-left': '15mm',
    'encoding': 'UTF-8',
    'no-outline': None,
    'enable-local-file-access': None,
    # Note: Page numbers are added during the merge step, not here
    # because each HTML is converted separately and would show "1"
    'quiet': None,
    # Critical options to prevent network access and hanging
    'disable-javascript': None,         # Disable JS - content already rendered
    'no-images': None,                   # Skip images to avoid network requests
    'disable-external-links': None,      # Don't try to fetch external links
    'load-error-handling': 'skip',       # Skip failed resource loads
    'load-media-error-handling': 'skip', # Skip failed media loads
}


@dataclass
class PDFConversionResult:
    """
    Result of a PDF conversion operation.
    
    Attributes:
        pdf_path: Path to the generated PDF file.
        success: Whether the conversion was successful.
        error_message: Error message if conversion failed.
    """
    pdf_path: Optional[str]
    success: bool
    error_message: Optional[str] = None


class PDFConverter:
    """
    Converts HTML pages to PDF format using pdfkit (wkhtmltopdf).
    
    This converter saves HTML content to local files and converts them
    with disabled network access to work with pre-fetched content.
    
    Example:
        converter = PDFConverter()
        result = converter.convert_page(crawled_page, "/output/page1.pdf")
        if result.success:
            print(f"PDF saved to: {result.pdf_path}")
    """
    
    def __init__(self, wkhtmltopdf_path: Optional[str] = None):
        """
        Initialize the PDF converter.
        
        Args:
            wkhtmltopdf_path: Optional path to wkhtmltopdf executable.
                              If not provided, uses system PATH.
        """
        self.temp_dir = tempfile.mkdtemp(prefix="web2pdf_")
        self.config = None
        
        # Try to locate wkhtmltopdf
        if wkhtmltopdf_path:
            self.config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
        else:
            # Try common Windows installation paths
            common_paths = [
                r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
                r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
            ]
            for path in common_paths:
                if os.path.exists(path):
                    self.config = pdfkit.configuration(wkhtmltopdf=path)
                    logger.info(f"Found wkhtmltopdf at: {path}")
                    break
    
    def convert_page(self, page: CrawledPage, output_path: str) -> PDFConversionResult:
        """
        Convert a single crawled page to PDF.
        
        Saves the HTML to a local file first to avoid network issues,
        then converts with disabled external resource loading.
        
        Args:
            page: The CrawledPage to convert.
            output_path: Path where the PDF should be saved.
            
        Returns:
            A PDFConversionResult indicating success or failure.
        """
        try:
            # Save HTML to a local file first
            html_filename = os.path.join(
                self.temp_dir, 
                f"page_{hash(page.url) & 0xFFFFFFFF:08x}.html"
            )
            
            # Sanitize HTML to remove navigation elements and overlays
            html_content = sanitize_html(page.html_content)
            
            # Add base tag to help resolve relative URLs and add source info
            base_tag = f'<base href="{page.url}">'
            source_comment = f'<!-- Source: {page.url} -->\n'
            
            # Insert base tag in head if possible
            if '<head>' in html_content.lower():
                html_content = html_content.replace('<head>', f'<head>\n{base_tag}', 1)
            else:
                html_content = f'{base_tag}\n{html_content}'
            
            html_content = source_comment + html_content
            
            # Write HTML to local file
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Convert from local file (not string) to avoid encoding issues
            pdfkit.from_file(
                html_filename,
                output_path,
                options=PDF_OPTIONS,
                configuration=self.config
            )
            
            # Verify the PDF was created
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return PDFConversionResult(pdf_path=output_path, success=True)
            else:
                return PDFConversionResult(
                    pdf_path=None, 
                    success=False, 
                    error_message="PDF file was not created or is empty"
                )
            
        except Exception as e:
            error_msg = f"Failed to convert {page.url}: {e}"
            logger.error(error_msg)
            return PDFConversionResult(pdf_path=None, success=False, error_message=error_msg)
    
    def convert_pages(self, pages: List[CrawledPage]) -> List[PDFConversionResult]:
        """
        Convert multiple pages to individual PDF files.
        
        Args:
            pages: List of CrawledPage objects to convert.
            
        Returns:
            List of PDFConversionResult objects for each page.
        """
        results = []
        total = len(pages)
        
        for i, page in enumerate(pages):
            # Log progress for each page
            title_short = page.title[:50] if page.title else "Untitled"
            logger.info(f"Converting page {i + 1}/{total}: {title_short}...")
            
            output_path = os.path.join(self.temp_dir, f"page_{i:04d}.pdf")
            result = self.convert_page(page, output_path)
            results.append(result)
            
            if result.success:
                logger.info(f"  ✓ Success: {output_path}")
            else:
                logger.warning(f"  ✗ Failed: {result.error_message}")
        
        return results
    
    def cleanup(self):
        """
        Clean up temporary files created during conversion.
        """
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
            logger.debug(f"Cleaned up temp directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up temp directory: {e}")
