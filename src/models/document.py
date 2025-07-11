"""Document models for medical record processing."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class PageContent:
    """Represents extracted content from a single PDF page."""
    page_number: int
    raw_text: str
    is_ocr_applied: bool = False
    confidence_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentSegment:
    """Represents a logical segment of a medical document."""
    segment_id: str
    text_content: str
    page_start: int
    page_end: int
    date_of_service: datetime | None = None
    document_type: str | None = None
    provider_name: str | None = None
    facility_name: str | None = None
    keywords: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    chunks: list[DocumentChunk] = field(default_factory=list)


@dataclass
class DocumentChunk:
    """Represents a sub-chunk of a document segment for AI processing."""
    chunk_id: str
    parent_segment_id: str
    text_content: str
    token_count: int
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessedDocument:
    """Represents the final processed medical record document."""
    document_id: str
    original_filename: str
    total_pages: int
    processing_date: datetime
    segments: list[DocumentSegment] = field(default_factory=list)
    date_range: tuple[datetime, datetime] | None = None
    total_segments: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "document_id": self.document_id,
            "original_filename": self.original_filename,
            "total_pages": self.total_pages,
            "processing_date": self.processing_date.isoformat(),
            "total_segments": len(self.segments),
            "date_range": {
                "start": self.date_range[0].isoformat() if self.date_range else None,
                "end": self.date_range[1].isoformat() if self.date_range else None,
            },
            "timeline": [
                {
                    "segment_id": seg.segment_id,
                    "text_content": seg.text_content,
                    "page_start": seg.page_start,
                    "page_end": seg.page_end,
                    "date_of_service": seg.date_of_service.isoformat() if seg.date_of_service else None,
                    "document_type": seg.document_type,
                    "provider_name": seg.provider_name,
                    "facility_name": seg.facility_name,
                    "keywords": seg.keywords,
                    "chunks": [
                        {
                            "chunk_id": chunk.chunk_id,
                            "text_content": chunk.text_content,
                            "token_count": chunk.token_count,
                            "chunk_index": chunk.chunk_index,
                        }
                        for chunk in seg.chunks
                    ],
                }
                for seg in self.segments
            ],
            "metadata": self.metadata,
        }
