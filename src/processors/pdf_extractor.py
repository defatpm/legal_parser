"""PDF text extraction with OCR fallback."""
from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import List, Optional

import fitz  # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image

from ..models.document import PageContent

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extracts text from PDF files with OCR fallback for scanned documents."""
    
    def __init__(self, ocr_threshold: int = 50):
        """Initialize extractor with OCR threshold.
        
        Args:
            ocr_threshold: Minimum word count per page before applying OCR
        """
        self.ocr_threshold = ocr_threshold
    
    def extract_pages(self, pdf_path: Path) -> List[PageContent]:
        """Extract text from all pages of a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of PageContent objects with extracted text
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: For PDF processing errors
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        pages = []
        
        try:
            # Primary extraction with PyMuPDF
            with fitz.open(pdf_path) as doc:
                for page_num in range(doc.page_count):
                    page = doc[page_num]
                    text = page.get_text()
                    
                    # Check if OCR is needed
                    word_count = len(text.split())
                    needs_ocr = word_count < self.ocr_threshold
                    
                    if needs_ocr:
                        try:
                            # Apply OCR to the page
                            ocr_text = self._apply_ocr_to_page(page)
                            if len(ocr_text.split()) > word_count:
                                text = ocr_text
                                needs_ocr = True
                            else:
                                needs_ocr = False
                        except Exception as e:
                            logger.warning(f"OCR failed for page {page_num + 1}: {e}")
                            needs_ocr = False
                    
                    pages.append(PageContent(
                        page_number=page_num + 1,
                        raw_text=text,
                        is_ocr_applied=needs_ocr
                    ))
        
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed: {e}")
            # Fallback to pdfplumber
            pages = self._extract_with_pdfplumber(pdf_path)
        
        return pages
    
    def _apply_ocr_to_page(self, page: fitz.Page) -> str:
        """Apply OCR to a single page using Tesseract.
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            OCR extracted text
        """
        # Convert page to image
        pix = page.get_pixmap()
        img_data = pix.tobytes("png")
        
        # Convert to PIL Image and apply OCR
        img = Image.open(io.BytesIO(img_data))
        text = pytesseract.image_to_string(img, config='--psm 6')
        
        return text.strip()
    
    def _extract_with_pdfplumber(self, pdf_path: Path) -> List[PageContent]:
        """Fallback extraction using pdfplumber.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of PageContent objects
        """
        pages = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    
                    pages.append(PageContent(
                        page_number=page_num + 1,
                        raw_text=text,
                        is_ocr_applied=False
                    ))
        
        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}")
            raise
        
        return pages