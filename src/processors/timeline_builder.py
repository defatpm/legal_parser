"""Timeline building and intelligent chunking."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

import nltk
from nltk.tokenize import sent_tokenize

from ..models.document import DocumentChunk, DocumentSegment, ProcessedDocument

logger = logging.getLogger(__name__)


class TimelineBuilder:
    """Builds chronological timeline and creates AI-friendly chunks."""
    
    def __init__(self, max_chunk_tokens: int = 4000):
        """Initialize timeline builder.
        
        Args:
            max_chunk_tokens: Maximum tokens per chunk
        """
        self.max_chunk_tokens = max_chunk_tokens
        self._ensure_nltk_data()
    
    def build_timeline(self, 
                      segments: List[DocumentSegment],
                      document_id: str,
                      original_filename: str,
                      total_pages: int) -> ProcessedDocument:
        """Build chronological timeline from segments.
        
        Args:
            segments: List of document segments
            document_id: Unique document identifier
            original_filename: Original PDF filename
            total_pages: Total number of pages
            
        Returns:
            ProcessedDocument with sorted timeline
        """
        # Sort segments chronologically
        sorted_segments = self._sort_segments_chronologically(segments)
        
        # Create chunks for large segments
        chunked_segments = self._create_chunks(sorted_segments)
        
        # Calculate date range
        date_range = self._calculate_date_range(chunked_segments)
        
        # Create processed document
        processed_doc = ProcessedDocument(
            document_id=document_id,
            original_filename=original_filename,
            total_pages=total_pages,
            processing_date=datetime.now(),
            segments=chunked_segments,
            date_range=date_range,
            total_segments=len(chunked_segments)
        )
        
        return processed_doc
    
    def _sort_segments_chronologically(self, segments: List[DocumentSegment]) -> List[DocumentSegment]:
        """Sort segments by date of service.
        
        Args:
            segments: List of document segments
            
        Returns:
            Sorted list of segments
        """
        # Separate segments with and without dates
        dated_segments = [s for s in segments if s.date_of_service is not None]
        undated_segments = [s for s in segments if s.date_of_service is None]
        
        # Sort dated segments by date
        dated_segments.sort(key=lambda s: s.date_of_service)
        
        # For undated segments, estimate dates based on page order
        undated_segments.sort(key=lambda s: s.page_start)
        
        # Combine: dated segments first, then undated
        return dated_segments + undated_segments
    
    def _create_chunks(self, segments: List[DocumentSegment]) -> List[DocumentSegment]:
        """Create chunks for segments that exceed token limit.
        
        Args:
            segments: List of document segments
            
        Returns:
            List of segments with chunks created
        """
        chunked_segments = []
        
        for segment in segments:
            # Estimate token count (rough approximation: 1 token ≈ 4 characters)
            estimated_tokens = len(segment.text_content) // 4
            
            if estimated_tokens > self.max_chunk_tokens:
                # Create chunks for this segment
                chunks = self._split_segment_into_chunks(segment)
                segment.chunks = chunks
            
            chunked_segments.append(segment)
        
        return chunked_segments
    
    def _split_segment_into_chunks(self, segment: DocumentSegment) -> List[DocumentChunk]:
        """Split a segment into smaller chunks.
        
        Args:
            segment: Document segment to split
            
        Returns:
            List of document chunks
        """
        chunks = []
        
        # Split by sentences to maintain context
        sentences = sent_tokenize(segment.text_content)
        
        current_chunk = []
        current_tokens = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_tokens = len(sentence) // 4  # Rough token estimation
            
            if current_tokens + sentence_tokens > self.max_chunk_tokens and current_chunk:
                # Create chunk from current sentences
                chunk_text = " ".join(current_chunk)
                chunk = DocumentChunk(
                    chunk_id=f"{segment.segment_id}_chunk_{chunk_index}",
                    parent_segment_id=segment.segment_id,
                    text_content=chunk_text,
                    token_count=current_tokens,
                    chunk_index=chunk_index
                )
                chunks.append(chunk)
                
                # Start new chunk
                current_chunk = [sentence]
                current_tokens = sentence_tokens
                chunk_index += 1
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
        
        # Add remaining sentences as final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunk = DocumentChunk(
                chunk_id=f"{segment.segment_id}_chunk_{chunk_index}",
                parent_segment_id=segment.segment_id,
                text_content=chunk_text,
                token_count=current_tokens,
                chunk_index=chunk_index
            )
            chunks.append(chunk)
        
        return chunks
    
    def _calculate_date_range(self, segments: List[DocumentSegment]) -> Optional[tuple[datetime, datetime]]:
        """Calculate date range for the document.
        
        Args:
            segments: List of document segments
            
        Returns:
            Tuple of (earliest_date, latest_date) or None
        """
        dates = [s.date_of_service for s in segments if s.date_of_service is not None]
        
        if not dates:
            return None
        
        return min(dates), max(dates)
    
    def _ensure_nltk_data(self) -> None:
        """Ensure required NLTK data is available."""
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            logger.info("Downloading NLTK punkt tokenizer...")
            nltk.download('punkt', quiet=True)