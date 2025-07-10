"""Integration tests for the complete PDF processing pipeline."""

import json
from pathlib import Path

import pytest

from src.process_pdf import PDFProcessor


class TestPDFProcessingIntegration:
    """Integration test suite for the complete PDF processing pipeline."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = PDFProcessor()
        self.sample_pdf_path = Path("data/sample/sample_medical_record.pdf")
        self.test_output_path = Path("data/output/test_output.json")

    def teardown_method(self):
        """Clean up test files."""
        if self.test_output_path.exists():
            self.test_output_path.unlink()

    @pytest.mark.skipif(
        not Path("data/sample/sample_medical_record.pdf").exists(),
        reason="Sample PDF not found",
    )
    def test_complete_pipeline(self):
        """Test the complete PDF processing pipeline."""
        # Process the PDF
        output_path = self.processor.process_pdf(
            self.sample_pdf_path, self.test_output_path
        )

        # Verify output file was created
        assert output_path.exists()
        assert output_path == self.test_output_path

        # Verify output content
        with open(output_path) as f:
            result = json.load(f)

        # Check required fields
        assert "document_id" in result
        assert "original_filename" in result
        assert "total_pages" in result
        assert "processing_date" in result
        assert "timeline" in result
        assert "total_segments" in result

        # Check timeline structure
        assert isinstance(result["timeline"], list)
        assert len(result["timeline"]) > 0

        # Check segment structure
        for segment in result["timeline"]:
            assert "segment_id" in segment
            assert "text_content" in segment
            assert "page_start" in segment
            assert "page_end" in segment
            assert "date_of_service" in segment
            assert "document_type" in segment
            assert "provider_name" in segment
            assert "facility_name" in segment
            assert "keywords" in segment
            assert "chunks" in segment

    def test_processor_initialization(self):
        """Test that PDFProcessor initializes correctly."""
        processor = PDFProcessor()

        assert processor.extractor is not None
        assert processor.segmenter is not None
        assert processor.metadata_extractor is not None
        assert processor.timeline_builder is not None

    def test_file_not_found_error(self):
        """Test that appropriate error is raised for non-existent files."""
        non_existent_path = Path("does_not_exist.pdf")

        with pytest.raises(FileNotFoundError):
            self.processor.process_pdf(non_existent_path)
