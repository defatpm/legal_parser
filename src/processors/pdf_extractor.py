"""PDF text extraction with OCR fallback."""
from __future__ import annotations

import io
import logging
import time
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image

from ..models.document import PageContent
from ..utils.error_handler import (
    error_context,
    graceful_degradation,
    handle_exceptions,
    retry_on_error,
)
from ..utils.exceptions import (
    FileSystemError,
    OCRError,
    PDFProcessingError,
    ValidationError,
)
from ..utils.performance import (
    get_processing_optimizer,
    performance_context,
    performance_profile,
)
from .base import (
    BaseProcessor,
    ProcessingContext,
    ProcessingResult,
    ProcessorMetadata,
    register_processor,
)

logger = logging.getLogger(__name__)


class PDFExtractor(BaseProcessor):
    """Extracts text from PDF files with OCR fallback for scanned documents."""

    def __init__(self, config: dict[str, Any] | None = None, ocr_threshold: int | None = None):
        """Initialize extractor with OCR threshold.

        Args:
            config: Optional configuration dictionary
            ocr_threshold: Minimum word count per page before applying OCR.
                          If None, uses value from configuration.
        """
        # Initialize base processor
        super().__init__(config)
        # Use provided value or fall back to config
        if ocr_threshold is not None:
            self.ocr_threshold = ocr_threshold
        else:
            # Calculate threshold from config - if confidence is low, use lower threshold
            confidence = self.config.pdf_extraction.ocr["confidence_threshold"]
            self.ocr_threshold = max(10, 100 - confidence)
        # Store configuration for use in methods
        self.ocr_enabled = self.config.pdf_extraction.ocr["enabled"]
        self.ocr_language = self.config.pdf_extraction.ocr["language"]
        self.ocr_dpi = self.config.pdf_extraction.ocr["dpi"]
        self.normalize_whitespace = self.config.pdf_extraction.text["normalize_whitespace"]
        self.min_text_length = self.config.pdf_extraction.text["min_text_length"]

    @property
    def metadata(self) -> ProcessorMetadata:
        """Get processor metadata."""
        return ProcessorMetadata(
            name="PDFExtractor",
            version="1.0.0",
            description="Extracts text from PDF files with OCR fallback for scanned documents",
            input_types=["Path", "str"],
            output_types=["List[PageContent]"],
            capabilities=["text_extraction", "ocr", "pdf_processing"],
            configuration_schema={
                "ocr_threshold": {"type": "int", "default": None},
                "ocr_enabled": {"type": "bool", "default": True},
                "ocr_language": {"type": "str", "default": "eng"},
                "ocr_dpi": {"type": "int", "default": 300},
                "normalize_whitespace": {"type": "bool", "default": True},
                "min_text_length": {"type": "int", "default": 10}
            },
            dependencies=["PyMuPDF", "pdfplumber", "pytesseract", "PIL"]
        )

    def process(self, input_data: Any, context: ProcessingContext | None = None) -> ProcessingResult:
        """Process PDF file to extract text.

        Args:
            input_data: Path to PDF file (str or Path)
            context: Optional processing context

        Returns:
            ProcessingResult with extracted pages
        """
        start_time = time.time()
        context = self._update_processing_context(context)
        try:
            # Convert input to Path if needed
            if isinstance(input_data, str):
                pdf_path = Path(input_data)
            elif isinstance(input_data, Path):
                pdf_path = input_data
            else:
                raise ValidationError(
                    f"Input must be str or Path, got {type(input_data)}",
                    field_name="input_data"
                )
            # Update context with file info
            context.source_path = str(pdf_path)
            context.metadata.update({
                "file_size_mb": pdf_path.stat().st_size / (1024 * 1024),
                "processor_config": {
                    "ocr_enabled": self.ocr_enabled,
                    "ocr_threshold": self.ocr_threshold,
                    "ocr_language": self.ocr_language
                }
            })
            # Extract pages
            from .base import ProcessorStatus
            self.status = ProcessorStatus.PROCESSING
            pages = self.extract_pages(pdf_path)
            # Update processing stats
            processing_time = time.time() - start_time
            self.processing_stats.update({
                "pages_processed": len(pages),
                "ocr_pages": sum(1 for page in pages if page.is_ocr_applied),
                "processing_time": processing_time
            })
            return self._create_success_result(
                output=pages,
                metadata={
                    "pages_count": len(pages),
                    "ocr_pages_count": sum(1 for page in pages if page.is_ocr_applied),
                    "file_path": str(pdf_path)
                },
                processing_time=processing_time
            )
        except Exception as e:
            processing_time = time.time() - start_time
            self.error_handler.handle_error(e, context.to_dict())
            return self._create_error_result(e, processing_time)

    def _get_required_config_sections(self) -> list[str]:
        """Get required configuration sections."""
        return ["pdf_extraction"]

    def _validate_input(self, input_data: Any) -> bool:
        """Validate input data."""
        if isinstance(input_data, str | Path):
            path = Path(input_data)
            return path.exists() and path.is_file() and path.suffix.lower() == '.pdf'
        return False

    def extract_pages(self, pdf_path: Path) -> list[PageContent]:
        """Extract text from all pages of a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of PageContent objects with extracted text

        Raises:
            FileSystemError: If PDF file doesn't exist or can't be accessed
            PDFProcessingError: For PDF processing errors
            ValidationError: For invalid input parameters
        """
        # Input validation
        if not isinstance(pdf_path, Path):
            raise ValidationError("pdf_path must be a Path object", field_name="pdf_path")
        if not pdf_path.exists():
            raise FileSystemError(
                f"PDF file not found: {pdf_path}",
                file_path=str(pdf_path),
                operation="read"
            )
        if not pdf_path.is_file():
            raise FileSystemError(
                f"Path is not a file: {pdf_path}",
                file_path=str(pdf_path),
                operation="read"
            )
        # Check file size
        file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
        max_size = self.config.processing.max_file_size_mb
        if file_size_mb > max_size:
            raise ValidationError(
                f"PDF file size ({file_size_mb:.1f}MB) exceeds maximum allowed size ({max_size}MB)",
                field_name="file_size",
                field_value=f"{file_size_mb:.1f}MB"
            )
        with error_context("pdf_extraction", pdf_path=str(pdf_path)):
            return graceful_degradation(
                self._extract_with_pymupdf,
                self._extract_with_pdfplumber,
                pdf_path
            )

    @retry_on_error(max_retries=2, delay=0.5, exceptions=(OCRError, RuntimeError))
    def _apply_ocr_to_page(self, page: fitz.Page) -> str:
        """Apply OCR to a single page using Tesseract.

        Args:
            page: PyMuPDF page object

        Returns:
            OCR extracted text

        Raises:
            OCRError: If OCR processing fails
        """
        try:
            # Convert page to image with configured DPI
            pix = page.get_pixmap(dpi=self.ocr_dpi)
            img_data = pix.tobytes("png")
            # Convert to PIL Image and apply OCR
            img = Image.open(io.BytesIO(img_data))
            # Configure OCR with language and confidence settings
            ocr_config = f'--psm 6 -l {self.ocr_language}'
            text = pytesseract.image_to_string(img, config=ocr_config)
            # Validate OCR result
            if not text or len(text.strip()) < 5:
                raise OCRError(
                    "OCR produced insufficient text output",
                    confidence=0.0
                )
            return text.strip()
        except pytesseract.TesseractError as e:
            raise OCRError(f"Tesseract OCR failed: {e}") from e
        except Exception as e:
            raise OCRError(f"OCR processing failed: {e}") from e

    @handle_exceptions(reraise=True)
    @performance_profile("pdf_extraction_pymupdf")
    def _extract_with_pymupdf(self, pdf_path: Path) -> list[PageContent]:
        """Primary extraction method using PyMuPDF.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of PageContent objects with extracted text

        Raises:
            PDFProcessingError: If extraction fails
        """
        pages = []
        optimizer = get_processing_optimizer()
        try:
            with fitz.open(pdf_path) as doc:
                total_pages = doc.page_count
                with performance_context("pdf_page_processing", {"total_pages": total_pages}) as perf:
                    # Process pages in batches if there are many
                    if total_pages > 50:
                        # Use batch processing for large documents
                        batch_size = optimizer.optimize_batch_size(total_pages, item_size_estimate=2.0)
                        for batch_start in range(0, total_pages, batch_size):
                            batch_end = min(batch_start + batch_size, total_pages)
                            batch_pages = []
                            for page_num in range(batch_start, batch_end):
                                page_content = self._process_single_page(doc, page_num)
                                if page_content:
                                    batch_pages.append(page_content)
                            pages.extend(batch_pages)
                            perf.add_items(len(batch_pages))
                            # Check memory usage after each batch
                            optimizer.memory_optimizer.check_memory_usage()
                    else:
                        # Process normally for smaller documents
                        for page_num in range(total_pages):
                            page_content = self._process_single_page(doc, page_num)
                            if page_content:
                                pages.append(page_content)
                                perf.add_items(1)
        except Exception as e:
            raise PDFProcessingError(
                f"PyMuPDF extraction failed: {e}",
                pdf_path=str(pdf_path)
            ) from e
        if not pages:
            raise PDFProcessingError(
                "No pages were successfully extracted from PDF",
                pdf_path=str(pdf_path)
            )
        return pages

    def _process_single_page(self, doc: fitz.Document, page_num: int) -> PageContent | None:
        """Process a single page with optimizations.

        Args:
            doc: PyMuPDF document object
            page_num: Page number to process

        Returns:
            PageContent object or None if page should be skipped
        """
        try:
            page = doc[page_num]
            text = page.get_text()
            # Check if OCR is needed
            word_count = len(text.split())
            needs_ocr = self.ocr_enabled and word_count < self.ocr_threshold
            if needs_ocr:
                try:
                    # Apply OCR to the page
                    ocr_text = self._apply_ocr_to_page(page)
                    if len(ocr_text.split()) > word_count:
                        text = ocr_text
                        needs_ocr = True
                    else:
                        needs_ocr = False
                except OCRError as e:
                    logger.warning(f"OCR failed for page {page_num + 1}: {e}")
                    needs_ocr = False
            # Apply text normalization if configured
            if self.normalize_whitespace:
                text = self._normalize_whitespace(text)
            # Skip pages with insufficient text
            if len(text.strip()) < self.min_text_length:
                logger.debug(f"Skipping page {page_num + 1} - insufficient text length")
                return None
            return PageContent(
                page_number=page_num + 1,
                raw_text=text,
                is_ocr_applied=needs_ocr
            )
        except Exception as e:
            logger.error(f"Failed to process page {page_num + 1}: {e}")
            return None

    @handle_exceptions(reraise=True)
    def _extract_with_pdfplumber(self, pdf_path: Path) -> list[PageContent]:
        """Fallback extraction using pdfplumber.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of PageContent objects

        Raises:
            PDFProcessingError: If extraction fails
        """
        pages = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    try:
                        text = page.extract_text() or ""
                        # Apply text normalization if configured
                        if self.normalize_whitespace:
                            text = self._normalize_whitespace(text)
                        # Skip pages with insufficient text
                        if len(text.strip()) < self.min_text_length:
                            logger.debug(f"Skipping page {page_num + 1} - insufficient text length")
                            continue
                        pages.append(PageContent(
                            page_number=page_num + 1,
                            raw_text=text,
                            is_ocr_applied=False
                        ))
                    except Exception as e:
                        logger.error(f"Failed to process page {page_num + 1} with pdfplumber: {e}")
                        # Continue with next page instead of failing completely
                        continue
        except Exception as e:
            raise PDFProcessingError(
                f"pdfplumber extraction failed: {e}",
                pdf_path=str(pdf_path)
            ) from e
        if not pages:
            raise PDFProcessingError(
                "No pages were successfully extracted from PDF using pdfplumber",
                pdf_path=str(pdf_path)
            )
        return pages

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text.

        Args:
            text: Input text

        Returns:
            Text with normalized whitespace
        """
        import re
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        # Remove empty lines
        lines = [line for line in lines if line]
        return '\n'.join(lines)


# Register the processor
register_processor(PDFExtractor)
