"""Main PDF processing pipeline."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional
from uuid import uuid4

from .processors.metadata_extractor import MetadataExtractor
from .processors.pdf_extractor import PDFExtractor
from .processors.document_segmenter import DocumentSegmenter
from .processors.timeline_builder import TimelineBuilder

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Main PDF processing pipeline."""
    
    def __init__(self):
        """Initialize PDF processor with default components."""
        self.extractor = PDFExtractor()
        self.segmenter = DocumentSegmenter()
        self.metadata_extractor = MetadataExtractor()
        self.timeline_builder = TimelineBuilder()
    
    def process_pdf(self, 
                   pdf_path: Path, 
                   output_path: Optional[Path] = None) -> Path:
        """Process a PDF file through the complete pipeline.
        
        Args:
            pdf_path: Path to input PDF file
            output_path: Optional output path for JSON result
            
        Returns:
            Path to the output JSON file
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: For processing errors
        """
        logger.info(f"Starting PDF processing: {pdf_path}")
        
        # Step 1: Extract text from PDF pages
        logger.info("Step 1: Extracting text from PDF pages...")
        pages = self.extractor.extract_pages(pdf_path)
        logger.info(f"Extracted {len(pages)} pages")
        
        # Step 2: Segment document into logical sections
        logger.info("Step 2: Segmenting document...")
        segments = self.segmenter.segment_document(pages)
        logger.info(f"Created {len(segments)} segments")
        
        # Step 3: Extract metadata from segments
        logger.info("Step 3: Extracting metadata...")
        enriched_segments = self.metadata_extractor.extract_metadata(segments)
        logger.info(f"Enriched {len(enriched_segments)} segments with metadata")
        
        # Step 4: Build chronological timeline
        logger.info("Step 4: Building chronological timeline...")
        document_id = str(uuid4())
        processed_doc = self.timeline_builder.build_timeline(
            enriched_segments,
            document_id,
            pdf_path.name,
            len(pages)
        )
        
        # Step 5: Save results
        if output_path is None:
            output_path = pdf_path.parent / f"{pdf_path.stem}_processed.json"
        
        logger.info(f"Step 5: Saving results to {output_path}")
        self._save_results(processed_doc, output_path)
        
        logger.info("PDF processing completed successfully")
        return output_path
    
    def _save_results(self, processed_doc, output_path: Path) -> None:
        """Save processing results to JSON file.
        
        Args:
            processed_doc: ProcessedDocument object
            output_path: Path to save JSON file
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_doc.to_dict(), f, indent=2, ensure_ascii=False)


def main() -> None:
    """Main entry point for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Process medical record PDFs into structured JSON"
    )
    parser.add_argument(
        "--input", 
        type=Path, 
        required=True,
        help="Path to input PDF file"
    )
    parser.add_argument(
        "--output", 
        type=Path,
        help="Path to output JSON file (optional)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Process PDF
    try:
        processor = PDFProcessor()
        output_path = processor.process_pdf(args.input, args.output)
        print(f"Processing completed! Output saved to: {output_path}")
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise


if __name__ == "__main__":
    main()