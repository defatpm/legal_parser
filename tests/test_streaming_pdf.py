from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.utils.streaming import StreamingPDFProcessor


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a dummy PDF file for testing."""
    pdf_path = tmp_path / "sample.pdf"
    # Create a simple PDF using reportlab
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        for i in range(3):
            c.drawString(100, 750 - i * 50, f"This is page {i + 1}.")
            c.showPage()
        c.save()
    except ImportError:
        # If reportlab is not installed, create a dummy file
        pdf_path.write_text("dummy pdf content")
    return pdf_path


class TestStreamingPDFProcessor:
    """Tests for StreamingPDFProcessor class."""

    def test_process_pdf_pages_streaming(self, sample_pdf):
        """Test processing PDF pages in a streaming fashion."""
        processor = StreamingPDFProcessor()

        # Mock the page processor
        page_processor = MagicMock(side_effect=lambda page: f"processed_{page.number}")

        with patch("fitz.open") as mock_fitz_open:
            # Mock the fitz document and pages
            mock_doc = MagicMock()
            mock_doc.page_count = 3
            mock_pages = [MagicMock(number=i) for i in range(3)]
            mock_doc.__getitem__.side_effect = lambda i: mock_pages[i]
            mock_doc.__enter__.return_value = mock_doc
            mock_fitz_open.return_value = mock_doc

            results = list(
                processor.process_pdf_pages_streaming(sample_pdf, page_processor)
            )

            assert len(results) == 3
            assert results == ["processed_0", "processed_1", "processed_2"]
            assert page_processor.call_count == 3

    def test_process_multiple_pdfs_streaming(self, sample_pdf):
        """Test processing multiple PDF files in a streaming fashion."""
        processor = StreamingPDFProcessor()

        # Mock the PDF processor
        pdf_processor = MagicMock(side_effect=lambda path: f"processed_{path.name}")

        pdf_paths = [sample_pdf, sample_pdf]  # Process the same PDF twice
        results = list(
            processor.process_multiple_pdfs_streaming(pdf_paths, pdf_processor)
        )

        assert len(results) == 2
        assert results == [
            f"processed_{sample_pdf.name}",
            f"processed_{sample_pdf.name}",
        ]
        assert pdf_processor.call_count == 2

    def test_process_pdf_pages_streaming_file_not_found(self):
        """Test processing a non-existent PDF file."""
        processor = StreamingPDFProcessor()

        with pytest.raises(FileNotFoundError):
            list(
                processor.process_pdf_pages_streaming(
                    Path("nonexistent.pdf"), lambda x: x
                )
            )
