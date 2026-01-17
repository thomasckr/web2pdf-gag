"""
PDF Merger Module.

This module provides functionality to merge multiple PDF files into
a single document while maintaining page order and generating a
table of contents.
"""

import logging
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

from PyPDF2 import PdfMerger, PdfReader
import fitz  # PyMuPDF for page numbering

from .crawler import CrawledPage
from .converter import PDFConversionResult


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class MergeResult:
    """
    Result of a PDF merge operation.
    
    Attributes:
        output_path: Path to the merged PDF file.
        success: Whether the merge was successful.
        total_pages: Total number of pages in the merged PDF.
        error_message: Error message if merge failed.
    """
    output_path: Optional[str]
    success: bool
    total_pages: int = 0
    error_message: Optional[str] = None


class PDFMerger:
    """
    Merges multiple PDF files into a single document.
    
    This merger combines individual PDF pages while:
    - Maintaining the order of pages
    - Adding bookmarks for each section
    - Generating a table of contents based on page titles
    
    Example:
        merger = PDFMerger()
        result = merger.merge(conversion_results, pages, "output.pdf")
        if result.success:
            print(f"Merged PDF: {result.output_path} ({result.total_pages} pages)")
    """
    
    def __init__(self):
        """Initialize the PDF merger."""
        self.merger = PdfMerger()
    
    def merge(
        self,
        conversion_results: List[PDFConversionResult],
        original_pages: List[CrawledPage],
        output_path: str
    ) -> MergeResult:
        """
        Merge multiple PDF files into a single document.
        
        Args:
            conversion_results: List of PDFConversionResult from the converter.
            original_pages: List of original CrawledPage objects for metadata.
            output_path: Path where the merged PDF should be saved.
            
        Returns:
            A MergeResult indicating success or failure.
        """
        try:
            total_pages = 0
            current_page = 0
            
            for i, (result, page) in enumerate(zip(conversion_results, original_pages)):
                if not result.success or result.pdf_path is None:
                    logger.warning(f"Skipping failed conversion: {page.url}")
                    continue
                
                # Read the PDF to get page count
                pdf_reader = PdfReader(result.pdf_path)
                page_count = len(pdf_reader.pages)
                
                # Append PDF with a bookmark for navigation
                self.merger.append(
                    result.pdf_path,
                    outline_item=page.title
                )
                
                logger.debug(f"Added {page.title} ({page_count} pages)")
                
                total_pages += page_count
                current_page += page_count
            
            # Write the merged PDF to a temporary location first
            temp_output = output_path + '.temp'
            with open(temp_output, 'wb') as output_file:
                self.merger.write(output_file)
            
            # Add page numbers to the merged PDF
            self._add_page_numbers(temp_output, output_path)
            
            # Remove temp file
            Path(temp_output).unlink(missing_ok=True)
            
            logger.info(f"Merged PDF created: {output_path} ({total_pages} pages)")
            
            return MergeResult(
                output_path=output_path,
                success=True,
                total_pages=total_pages
            )
            
        except Exception as e:
            error_msg = f"Failed to merge PDFs: {e}"
            logger.error(error_msg)
            return MergeResult(
                output_path=None,
                success=False,
                error_message=error_msg
            )
        
        finally:
            self.merger.close()
    
    def _add_page_numbers(self, input_path: str, output_path: str):
        """
        Add page numbers to a PDF file.
        
        Args:
            input_path: Path to the input PDF without page numbers.
            output_path: Path where the PDF with page numbers should be saved.
        """
        doc = fitz.open(input_path)
        total_pages = len(doc)
        
        for page_num in range(total_pages):
            page = doc[page_num]
            
            # Get page dimensions
            rect = page.rect
            width = rect.width
            height = rect.height
            
            # Create page number text
            text = str(page_num + 1)
            
            # Position at bottom center
            font_size = 9
            text_width = fitz.get_text_length(text, fontname="helv", fontsize=font_size)
            x = (width - text_width) / 2
            y = height - 15  # 15 points from bottom
            
            # Insert page number
            page.insert_text(
                (x, y),
                text,
                fontname="helv",
                fontsize=font_size,
                color=(0, 0, 0)
            )
        
        doc.save(output_path)
        doc.close()
        logger.debug(f"Added page numbers to {total_pages} pages")
    
    def merge_files(
        self,
        pdf_paths: List[str],
        titles: List[str],
        output_path: str
    ) -> MergeResult:
        """
        Merge PDF files directly from file paths.
        
        This is a simpler interface when you already have PDF files
        and their corresponding titles.
        
        Args:
            pdf_paths: List of paths to PDF files to merge.
            titles: List of titles for bookmarks (same length as pdf_paths).
            output_path: Path where the merged PDF should be saved.
            
        Returns:
            A MergeResult indicating success or failure.
        """
        try:
            total_pages = 0
            merger = PdfMerger()
            
            for pdf_path, title in zip(pdf_paths, titles):
                if not Path(pdf_path).exists():
                    logger.warning(f"PDF file not found: {pdf_path}")
                    continue
                
                pdf_reader = PdfReader(pdf_path)
                page_count = len(pdf_reader.pages)
                
                merger.append(pdf_path, outline_item=title)
                total_pages += page_count
            
            with open(output_path, 'wb') as output_file:
                merger.write(output_file)
            
            merger.close()
            
            return MergeResult(
                output_path=output_path,
                success=True,
                total_pages=total_pages
            )
            
        except Exception as e:
            error_msg = f"Failed to merge PDFs: {e}"
            logger.error(error_msg)
            return MergeResult(
                output_path=None,
                success=False,
                error_message=error_msg
            )
