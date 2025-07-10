"""Tests for document segmentation functionality."""

from src.models.document import DocumentSegment, PageContent
from src.processors.document_segmenter import DocumentSegmenter


class TestDocumentSegmenter:
    """Test suite for DocumentSegmenter class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.segmenter = DocumentSegmenter()
        self.sample_pages = [
            PageContent(
                page_number=1,
                raw_text="Date of Service: 03/15/2023\nPatient: John Doe\nADMISSION NOTE\nChief complaint: Chest pain",
                is_ocr_applied=False,
            ),
            PageContent(
                page_number=2,
                raw_text="LABORATORY RESULTS\nDate of Service: 03/15/2023\nTroponin: 0.8 ng/mL\nCBC: Normal",
                is_ocr_applied=False,
            ),
        ]

    def test_init(self):
        """Test DocumentSegmenter initialization."""
        segmenter = DocumentSegmenter()
        assert segmenter.segment_patterns is not None
        assert segmenter.noise_patterns is not None
        assert len(segmenter.segment_patterns) > 0
        assert len(segmenter.noise_patterns) > 0

    def test_combine_pages_with_markers(self):
        """Test page combination with markers."""
        combined = self.segmenter._combine_pages_with_markers(self.sample_pages)

        assert "[PAGE_1]" in combined
        assert "[PAGE_2]" in combined
        assert "Date of Service: 03/15/2023" in combined
        assert "LABORATORY RESULTS" in combined

    def test_filter_noise(self):
        """Test noise filtering."""
        noisy_text = (
            "fax cover sheet\nImportant content\nconfidentiality notice\nMore content"
        )
        cleaned = self.segmenter._filter_noise(noisy_text)

        assert "fax cover sheet" not in cleaned
        assert "confidentiality notice" not in cleaned
        assert "Important content" in cleaned
        assert "More content" in cleaned

    def test_segment_document(self):
        """Test document segmentation."""
        segments = self.segmenter.segment_document(self.sample_pages)

        assert isinstance(segments, list)
        for segment in segments:
            assert isinstance(segment, DocumentSegment)
            assert segment.segment_id is not None
            assert segment.text_content is not None
            assert segment.page_start > 0
            assert segment.page_end > 0

    def test_find_page_range(self):
        """Test page range detection."""
        segment_text = "[PAGE_1]Some content[PAGE_2]More content"
        page_start, page_end = self.segmenter._find_page_range(segment_text)

        assert page_start == 1
        assert page_end == 2

    def test_find_page_range_single_page(self):
        """Test page range detection for single page."""
        segment_text = "[PAGE_3]Single page content"
        page_start, page_end = self.segmenter._find_page_range(segment_text)

        assert page_start == 3
        assert page_end == 3

    def test_find_page_range_no_markers(self):
        """Test page range detection with no markers."""
        segment_text = "Content without page markers"
        page_start, page_end = self.segmenter._find_page_range(segment_text)

        assert page_start == 1
        assert page_end == 1

    def test_build_segment_patterns(self):
        """Test segment pattern building."""
        patterns = self.segmenter._build_segment_patterns()

        assert len(patterns) > 0

        # Test that patterns are compiled regex objects
        for pattern in patterns:
            assert hasattr(pattern, "search")
            assert hasattr(pattern, "finditer")

    def test_build_noise_patterns(self):
        """Test noise pattern building."""
        patterns = self.segmenter._build_noise_patterns()

        assert len(patterns) > 0

        # Test that patterns are compiled regex objects
        for pattern in patterns:
            assert hasattr(pattern, "sub")
            assert hasattr(pattern, "search")
