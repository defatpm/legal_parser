from __future__ import annotations

from datetime import datetime

import pytest

from src.models.document import DocumentSegment
from src.processors.metadata_extractor import MetadataExtractor


@pytest.fixture
def sample_text():
    """Return a sample text for metadata extraction."""
    return """
    Date of Service: 01/01/2023
    Patient: Jane Doe
    Provider: Dr. John Smith, MD
    Facility: General Hospital

    This is a test segment.
    """


@pytest.fixture
def metadata_extractor():
    """Return a MetadataExtractor instance."""
    return MetadataExtractor()


class TestMetadataExtractor:
    """Tests for the MetadataExtractor class."""

    def test_extract_date(self, metadata_extractor, sample_text):
        """Test date extraction."""
        date = metadata_extractor._extract_date(sample_text)
        assert date == datetime(2023, 1, 1)

    def test_extract_document_type(self, metadata_extractor):
        """Test document type extraction."""
        text = "ADMISSION NOTE"
        doc_type = metadata_extractor._extract_document_type(text)
        assert doc_type == "Admission Note"

    def test_extract_providers(self, metadata_extractor, sample_text):
        """Test provider and facility extraction."""
        providers = metadata_extractor._extract_providers(sample_text)
        assert providers["provider"] == "Dr. John Smith, MD"
        assert providers["facility"] == "General Hospital"

    def test_extract_keywords(self, metadata_extractor, sample_text):
        """Test keyword extraction."""
        keywords = metadata_extractor._extract_keywords(sample_text)
        assert "Jane Doe" in keywords
        assert "Dr. John Smith" in keywords
        assert "General Hospital" in keywords

    def test_extract_metadata(self, metadata_extractor, sample_text):
        """Test the main metadata extraction process."""
        segment = DocumentSegment(
            segment_id="seg1", text_content=sample_text, page_start=1, page_end=1
        )
        enriched_segments = metadata_extractor.extract_metadata([segment])

        assert len(enriched_segments) == 1
        enriched_segment = enriched_segments[0]

        assert enriched_segment.date_of_service == datetime(2023, 1, 1)
        assert enriched_segment.provider_name == "Dr. John Smith, MD"
        assert enriched_segment.facility_name == "General Hospital"
        assert "Jane Doe" in enriched_segment.keywords
