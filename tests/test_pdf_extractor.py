"""Tests for PDF extraction functionality."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.models.document import PageContent
from src.utils.exceptions import FileSystemError
from tests.test_utils import ConcretePDFExtractor


class TestPDFExtractor:
    """Test suite for PDFExtractor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = ConcretePDFExtractor()
        self.sample_pdf_path = Path("data/sample/sample_medical_record.pdf")

    def test_init(self):
        """Test PDFExtractor initialization."""
        extractor = ConcretePDFExtractor(ocr_threshold=100)
        assert extractor.ocr_threshold == 100

        # Test default threshold
        default_extractor = ConcretePDFExtractor()
        assert default_extractor.ocr_threshold is not None

    def test_extract_pages_file_not_found(self):
        """Test extract_pages with non-existent file."""
        non_existent_path = Path("does_not_exist.pdf")

        with pytest.raises(FileSystemError):
            self.extractor.extract_pages(non_existent_path)


    @pytest.mark.skipif(
        not Path("data/sample/sample_medical_record.pdf").exists(),
        reason="Sample PDF not found",
    )
    def test_extract_pages_success(self):
        """Test successful PDF extraction."""
        pages = self.extractor.extract_pages(self.sample_pdf_path)

        assert isinstance(pages, list)
        assert len(pages) > 0

        for page in pages:
            assert isinstance(page, PageContent)
            assert page.page_number > 0
            assert isinstance(page.raw_text, str)
            assert isinstance(page.is_ocr_applied, bool)

    @patch("fitz.open")
    @patch("pathlib.Path.stat")
    @patch("pathlib.Path.is_file")
    @patch("pathlib.Path.exists")
    def test_extract_pages_with_mock(self, mock_exists, mock_is_file, mock_stat, mock_fitz_open):
        """Test extract_pages with mocked PyMuPDF."""
        # Mock file existence
        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_stat.return_value = Mock(st_size=1024)

        # Mock the fitz document
        mock_doc = Mock()
        mock_doc.page_count = 2
        mock_doc.__enter__ = Mock(return_value=mock_doc)
        mock_doc.__exit__ = Mock(return_value=None)

        # Mock pages
        mock_page1 = Mock()
        mock_page1.get_text.return_value = "Sample text from page 1"
        mock_page2 = Mock()
        mock_page2.get_text.return_value = "Sample text from page 2"

        mock_doc.__getitem__ = Mock(side_effect=[mock_page1, mock_page2])
        mock_fitz_open.return_value = mock_doc

        # Test extraction
        pages = self.extractor.extract_pages(Path("test.pdf"))

        assert len(pages) == 2
        assert pages[0].page_number == 1
        assert pages[0].raw_text == "Sample text from page 1"
        assert pages[1].page_number == 2
        assert pages[1].raw_text == "Sample text from page 2"

    def test_ocr_threshold_logic(self):
        """Test OCR threshold logic."""
        # Test with high threshold (should not trigger OCR)
        high_threshold_extractor = ConcretePDFExtractor(ocr_threshold=1000)
        assert high_threshold_extractor.ocr_threshold == 1000

        # Test with low threshold (should trigger OCR more often)
        low_threshold_extractor = ConcretePDFExtractor(ocr_threshold=1)
        assert low_threshold_extractor.ocr_threshold == 1
