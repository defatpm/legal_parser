from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from uuid import uuid4

from .processors.document_segmenter import DocumentSegmenter
from .processors.metadata_extractor import MetadataExtractor
from .processors.pdf_extractor import PDFExtractor
from .processors.timeline_builder import TimelineBuilder
from .utils.config import get_config

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Main PDF processing pipeline."""

    def __init__(self, extractor: PDFExtractor | None = None):
        """Initialize PDF processor with configured components."""
        self.config = get_config()
        self.extractor = extractor or PDFExtractor()
        self.segmenter = DocumentSegmenter()
        self.metadata_extractor = MetadataExtractor()
        self.timeline_builder = TimelineBuilder()

    def process_pdf(self, pdf_path: Path, output_path: Path | None = None) -> Path:
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
            enriched_segments, document_id, pdf_path.name, len(pages)
        )
        # Step 5: Save results
        if output_path is None:
            # Use configured naming template
            template = self.config.output.naming["template"]
            filename = template.format(stem=pdf_path.stem)
            if self.config.output.naming["include_timestamp"]:
                from datetime import datetime

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{filename}_{timestamp}"
            output_path = pdf_path.parent / f"{filename}.json"
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
        # Use configured JSON output settings
        json_config = self.config.output.json
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                processed_doc.to_dict(),
                f,
                indent=json_config["indent"] if json_config["pretty_print"] else None,
                ensure_ascii=json_config["ensure_ascii"],
            )


def main() -> None:
    """Main entry point for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Process medical record PDFs into structured JSON"
    )
    # Input arguments
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", type=Path, help="Path to input PDF file")
    group.add_argument(
        "--input-dir",
        type=Path,
        help="Directory containing PDF files for batch processing",
    )
    # Output arguments
    parser.add_argument(
        "--output",
        type=Path,
        help="Path to output JSON file (single file) or directory (batch)",
    )
    parser.add_argument(
        "--csv-output", type=Path, help="Path to output CSV files (batch mode only)"
    )
    parser.add_argument(
        "--excel-output", type=Path, help="Path to output Excel files (batch mode only)"
    )
    # Batch processing arguments
    parser.add_argument(
        "--batch", action="store_true", help="Enable batch processing mode"
    )
    parser.add_argument(
        "--workers", type=int, help="Number of concurrent workers for batch processing"
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Search subdirectories recursively (batch mode)",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="*.pdf",
        help="File pattern to match (default: *.pdf)",
    )
    parser.add_argument(
        "--resume", action="store_true", help="Resume interrupted batch processing"
    )
    parser.add_argument(
        "--resume-file",
        type=Path,
        help="Path to resume file (default: .batch_resume.json)",
    )
    # Other arguments
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--progress",
        action="store_true",
        help="Show progress bar during batch processing",
    )
    args = parser.parse_args()
    # Setup logging with configuration
    config = get_config()
    level = logging.DEBUG if args.verbose else getattr(logging, config.logging.level)
    logging.basicConfig(level=level, format=config.logging.format)
    try:
        if args.batch or args.input_dir:
            # Batch processing mode
            _process_batch(args)
        else:
            # Single file processing mode
            _process_single_file(args)
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        sys.exit(1)
    sys.exit(0)


def _process_single_file(args) -> None:
    """Process a single PDF file."""
    processor = PDFProcessor()
    output_path = processor.process_pdf(args.input, args.output)
    print(f"Processing completed! Output saved to: {output_path}")


def _process_batch(args) -> None:
    """Process multiple PDF files in batch mode."""
    from .batch_processor import BatchProcessor

    # Determine input directory
    input_dir = args.input_dir or args.input.parent if args.input else None
    if not input_dir:
        raise ValueError("Input directory required for batch processing")
    # Determine output directory
    output_dir = args.output or (input_dir / "output")
    output_dir.mkdir(parents=True, exist_ok=True)
    # Setup progress callback
    progress_callback = None
    if args.progress:
        progress_callback = _print_progress
    # Create batch processor
    batch_processor = BatchProcessor(
        max_workers=args.workers, progress_callback=progress_callback
    )
    # Setup resume file
    resume_file = args.resume_file or (input_dir / ".batch_resume.json")
    batch_processor.set_resume_file(resume_file)
    # Add files to batch
    if args.input:
        # Single file specified with batch flag
        output_path = output_dir / f"{args.input.stem}.json"
        batch_processor.add_file(args.input, output_path)
    else:
        # Directory-based batch processing
        batch_processor.add_directory(
            input_dir=input_dir,
            output_dir=output_dir,
            pattern=args.pattern,
            recursive=args.recursive,
        )
    print(f"Starting batch processing of {len(batch_processor.jobs)} files...")
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Workers: {batch_processor.max_workers}")
    # Process batch
    start_time = time.time()
    statistics = batch_processor.process_batch(resume=args.resume)
    end_time = time.time()
    # Print results
    print("\n" + "=" * 60)
    print("BATCH PROCESSING RESULTS")
    print("=" * 60)
    print(f"Total files: {statistics.total_jobs}")
    print(f"Successful: {statistics.successful_jobs}")
    print(f"Failed: {statistics.failed_jobs}")
    print(f"Total duration: {end_time - start_time:.2f} seconds")
    print(f"Average duration per file: {statistics.average_duration:.2f} seconds")
    print(f"Fastest file: {statistics.fastest_job:.2f} seconds")
    print(f"Slowest file: {statistics.slowest_job:.2f} seconds")
    print(f"Total pages processed: {statistics.total_pages_processed}")
    print(f"Throughput: {statistics.throughput_jobs_per_minute:.1f} files/minute")
    print(f"Throughput: {statistics.throughput_pages_per_minute:.1f} pages/minute")
    print(f"Memory usage: {statistics.memory_usage_mb:.1f} MB")
    if statistics.errors:
        print("\nErrors encountered:")
        for i, error in enumerate(statistics.errors[:5], 1):  # Show first 5 errors
            print(f"  {i}. {error}")
        if len(statistics.errors) > 5:
            print(f"  ... and {len(statistics.errors) - 5} more errors")
    # Export to CSV if requested
    if args.csv_output:
        print(f"\nExporting CSV files to: {args.csv_output}")
        args.csv_output.mkdir(parents=True, exist_ok=True)
        from .models.document import DocumentSegment
        from .utils.output_formatter import to_csv_string

        for job in batch_processor.jobs:
            if job.status == "completed":
                try:
                    with open(job.output_path, encoding="utf-8") as f:
                        data = json.load(f)
                    segments_data = data.get("segments", [])
                    if segments_data:
                        segments = [DocumentSegment(**s) for s in segments_data]
                        csv_str = to_csv_string(segments)
                        csv_path = (
                            args.csv_output / f"{job.input_path.stem}_segments.csv"
                        )
                        with open(csv_path, "w", encoding="utf-8") as f:
                            f.write(csv_str)
                except Exception as e:
                    logger.error(
                        f"Failed to generate CSV for {job.input_path.name}: {e}"
                    )
    # Export to Excel if requested
    if args.excel_output:
        print(f"\nExporting Excel files to: {args.excel_output}")
        args.excel_output.mkdir(parents=True, exist_ok=True)
        from .models.document import DocumentSegment
        from .utils.output_formatter import to_excel

        for job in batch_processor.jobs:
            if job.status == "completed":
                try:
                    with open(job.output_path, encoding="utf-8") as f:
                        data = json.load(f)
                    segments_data = data.get("segments", [])
                    if segments_data:
                        segments = [DocumentSegment(**s) for s in segments_data]
                        excel_data = to_excel(segments)
                        excel_path = (
                            args.excel_output / f"{job.input_path.stem}_segments.xlsx"
                        )
                        with open(excel_path, "wb") as f:
                            f.write(excel_data)
                except Exception as e:
                    logger.error(
                        f"Failed to generate Excel for {job.input_path.name}: {e}"
                    )
    # Clean up resume file if processing completed successfully
    if statistics.failed_jobs == 0 and resume_file.exists():
        resume_file.unlink()
        print(f"\nResume file cleaned up: {resume_file}")
    elif statistics.failed_jobs > 0:
        print(
            f"\nFailed jobs can be retried using: --resume --resume-file {resume_file}"
        )
    print("=" * 60)


def _print_progress(progress) -> None:
    """Print progress information."""
    percentage = progress.completion_rate
    bar_length = 50
    filled_length = int(bar_length * percentage / 100)
    bar = "█" * filled_length + "-" * (bar_length - filled_length)
    eta_str = ""
    if progress.eta_seconds:
        eta_minutes = int(progress.eta_seconds / 60)
        eta_seconds = int(progress.eta_seconds % 60)
        eta_str = f" ETA: {eta_minutes:02d}:{eta_seconds:02d}"
    print(
        f"\rProgress: |{bar}| {percentage:.1f}% "
        f"({progress.completed_jobs}/{progress.total_jobs})"
        f"{eta_str}",
        end="",
        flush=True,
    )


if __name__ == "__main__":
    main()
