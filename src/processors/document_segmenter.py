"""Document segmentation and noise filtering."""

from __future__ import annotations

import logging
import re
from re import Pattern
from uuid import uuid4

from ..models.document import DocumentSegment, PageContent

logger = logging.getLogger(__name__)


class DocumentSegmenter:
    """Segments medical documents into logical sections."""

    def __init__(self):
        """Initialize segmenter with default patterns."""
        # Add config attribute for test compatibility
        try:
            from ..utils.config import get_config

            self.config = get_config()
        except ImportError:
            # Fallback for test environments
            self.config = type("Config", (), {})()

        self.segment_patterns = self._build_segment_patterns()
        self.noise_patterns = self._build_noise_patterns()

    def segment_document(self, pages: list[PageContent]) -> list[DocumentSegment]:
        """Segment document pages into logical sections.

        Args:
            pages: List of extracted page content

        Returns:
            List of document segments
        """
        # Combine all text with page markers
        full_text = self._combine_pages_with_markers(pages)
        # Remove noise
        cleaned_text = self._filter_noise(full_text)
        # Find segment boundaries
        segments = self._find_segments(cleaned_text, pages)
        return segments

    def _combine_pages_with_markers(self, pages: list[PageContent]) -> str:
        """Combine page texts with page boundary markers.

        Args:
            pages: List of page content

        Returns:
            Combined text with page markers
        """
        combined = []
        for page in pages:
            combined.append(f"[PAGE_{page.page_number}]")
            combined.append(page.raw_text)
        return "\n".join(combined)

    def _filter_noise(self, text: str) -> str:
        """Remove common noise patterns from text.

        Args:
            text: Raw text to clean

        Returns:
            Cleaned text
        """
        cleaned = text
        for pattern in self.noise_patterns:
            cleaned = pattern.sub("", cleaned)
        # Remove excessive whitespace
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = re.sub(r" {2,}", " ", cleaned)
        return cleaned.strip()

    def _find_segments(
        self, text: str, pages: list[PageContent]
    ) -> list[DocumentSegment]:
        """Find document segments using pattern matching.

        Args:
            text: Cleaned combined text
            pages: Original page content for reference

        Returns:
            List of document segments
        """
        segments = []
        # Find all potential segment boundaries
        boundaries = []
        for pattern in self.segment_patterns:
            for match in pattern.finditer(text):
                boundaries.append((match.start(), match.group()))
        # Sort boundaries by position
        boundaries.sort(key=lambda x: x[0])
        # Create segments between boundaries
        for i, (start_pos, header) in enumerate(boundaries):
            # Determine end position
            end_pos = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
            # Extract segment text
            segment_text = text[start_pos:end_pos].strip()
            if len(segment_text) > 50:  # Minimum segment length
                # Determine page range
                page_start, page_end = self._find_page_range(segment_text)
                segment = DocumentSegment(
                    segment_id=str(uuid4()),
                    text_content=segment_text,
                    page_start=page_start,
                    page_end=page_end,
                    metadata={"detected_header": header},
                )
                segments.append(segment)

        # If no segments found, create page-based segments as fallback
        if not segments:
            logger.warning(
                "No segments found using patterns, creating page-based segments"
            )
            segments = self._create_page_based_segments(pages)

        return segments

    def _find_page_range(self, segment_text: str) -> tuple[int, int]:
        """Find the page range for a segment.

        Args:
            segment_text: Text content of the segment

        Returns:
            Tuple of (start_page, end_page)
        """
        # Find page markers in the segment
        page_markers = re.findall(r"\[PAGE_(\d+)\]", segment_text)
        if page_markers:
            page_numbers = [int(p) for p in page_markers]
            return min(page_numbers), max(page_numbers)
        return 1, 1  # Default fallback

    def _create_page_based_segments(
        self, pages: list[PageContent]
    ) -> list[DocumentSegment]:
        """Create segments based on pages when pattern matching fails.

        Args:
            pages: List of page content

        Returns:
            List of page-based segments
        """
        segments = []
        for page in pages:
            if (
                page.raw_text and len(page.raw_text.strip()) > 20
            ):  # Only create segments for pages with content
                segment = DocumentSegment(
                    segment_id=str(uuid4()),
                    text_content=page.raw_text.strip(),
                    page_start=page.page_number,
                    page_end=page.page_number,
                    metadata={"segment_type": "page_based", "source": "fallback"},
                )
                segments.append(segment)
        return segments

    def _build_segment_patterns(self) -> list[Pattern[str]]:
        """Build regex patterns for segment detection.

        Returns:
            List of compiled regex patterns
        """
        patterns = [
            # Date of service patterns
            re.compile(
                r"Date of Service:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", re.IGNORECASE
            ),
            re.compile(
                r"Service Date:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", re.IGNORECASE
            ),
            re.compile(r"DOS:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", re.IGNORECASE),
            # Document type headers
            re.compile(r"^[A-Z\s]{5,}$", re.MULTILINE),  # All-caps headers
            re.compile(r"DISCHARGE SUMMARY", re.IGNORECASE),
            re.compile(r"ADMISSION NOTE", re.IGNORECASE),
            re.compile(r"PROGRESS NOTE", re.IGNORECASE),
            re.compile(r"CONSULTATION", re.IGNORECASE),
            re.compile(r"OPERATIVE REPORT", re.IGNORECASE),
            re.compile(r"LABORATORY RESULTS?", re.IGNORECASE),
            re.compile(r"RADIOLOGY REPORT", re.IGNORECASE),
            re.compile(r"PATHOLOGY REPORT", re.IGNORECASE),
            # Provider/facility headers
            re.compile(r"Provider:\s*(.+)", re.IGNORECASE),
            re.compile(r"Physician:\s*(.+)", re.IGNORECASE),
            re.compile(r"Facility:\s*(.+)", re.IGNORECASE),
        ]
        return patterns

    def _build_noise_patterns(self) -> list[Pattern[str]]:
        """Build regex patterns for noise removal.

        Returns:
            List of compiled regex patterns
        """
        patterns = [
            # Common noise phrases
            re.compile(r"fax cover sheet", re.IGNORECASE),
            re.compile(r"confidentiality notice", re.IGNORECASE),
            re.compile(r"this document contains", re.IGNORECASE),
            re.compile(r"page \d+ of \d+", re.IGNORECASE),
            re.compile(r"printed on \d{1,2}[/-]\d{1,2}[/-]\d{2,4}", re.IGNORECASE),
            # Headers and footers
            re.compile(r"^[-=_]{3,}$", re.MULTILINE),  # Separator lines
            re.compile(r"^\s*\d+\s*$", re.MULTILINE),  # Standalone page numbers
            # Billing/administrative codes
            re.compile(r"CPT:\s*\d+", re.IGNORECASE),
            re.compile(r"ICD[- ]?\d*:\s*[\d.]+", re.IGNORECASE),
        ]
        return patterns
