from __future__ import annotations

from datetime import datetime

import pytest

from src.models.document import DocumentSegment
from src.processors.timeline_builder import TimelineBuilder


@pytest.fixture
def sample_segments():
    """Return a list of sample document segments."""
    return [
        DocumentSegment(
            segment_id="seg1",
            text_content="This is a segment from page 1.",
            page_start=1,
            page_end=1,
            date_of_service=datetime(2023, 1, 15),
        ),
        DocumentSegment(
            segment_id="seg2",
            text_content="This is another segment from page 2.",
            page_start=2,
            page_end=2,
            date_of_service=datetime(2023, 1, 10),
        ),
        DocumentSegment(
            segment_id="seg3",
            text_content="This segment has no date.",
            page_start=3,
            page_end=3,
        ),
    ]


class TestTimelineBuilder:
    """Tests for the TimelineBuilder class."""

    def test_sort_segments_chronologically(self, sample_segments):
        """Test that segments are sorted correctly by date."""
        builder = TimelineBuilder()
        sorted_segments = builder._sort_segments_chronologically(sample_segments)

        assert sorted_segments[0].segment_id == "seg2"
        assert sorted_segments[1].segment_id == "seg1"
        assert sorted_segments[2].segment_id == "seg3"

    def test_create_chunks(self):
        """Test that long segments are chunked correctly."""
        builder = TimelineBuilder(max_chunk_tokens=50)
        long_text = "This is a long sentence. " * 10
        segment = DocumentSegment(
            segment_id="long_seg",
            text_content=long_text,
            page_start=1,
            page_end=1,
        )
        chunked_segments = builder._create_chunks([segment])

        assert len(chunked_segments) == 1
        assert len(chunked_segments[0].chunks) > 1
        assert chunked_segments[0].chunks[0].token_count <= 50

    def test_calculate_date_range(self, sample_segments):
        """Test that the date range is calculated correctly."""
        builder = TimelineBuilder()
        date_range = builder._calculate_date_range(sample_segments)

        assert date_range is not None
        assert date_range[0] == datetime(2023, 1, 10)
        assert date_range[1] == datetime(2023, 1, 15)

    def test_build_timeline(self, sample_segments):
        """Test the main timeline building process."""
        builder = TimelineBuilder()
        processed_doc = builder.build_timeline(
            segments=sample_segments,
            document_id="doc1",
            original_filename="test.pdf",
            total_pages=3,
        )

        assert processed_doc.document_id == "doc1"
        assert processed_doc.total_segments == 3
        assert processed_doc.date_range is not None
        assert processed_doc.segments[0].segment_id == "seg2"
        assert processed_doc.segments[1].segment_id == "seg1"
        assert processed_doc.segments[2].segment_id == "seg3"
