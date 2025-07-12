"""Streaming processing utilities for large documents."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from .exceptions import ResourceExhaustedError
from .performance import get_processing_optimizer, performance_context

logger = logging.getLogger(__name__)

T = TypeVar("T")
U = TypeVar("U")


@dataclass
class StreamingConfig:
    """Configuration for streaming processing."""

    chunk_size: int = 1000
    max_memory_mb: float = 256.0
    buffer_size: int = 10
    enable_progress_tracking: bool = True
    checkpoint_interval: int = 100


class StreamingProcessor:
    """Base class for streaming document processing."""

    def __init__(self, config: StreamingConfig | None = None):
        """Initialize streaming processor.

        Args:
            config: Optional streaming configuration
        """
        self.config = config or StreamingConfig()
        self.optimizer = get_processing_optimizer()
        self.processed_count = 0
        self.checkpoints: list[dict[str, Any]] = []

    def stream_process(
        self, items: Iterator[T], processor: Callable[[T], U]
    ) -> Iterator[U]:
        """Process items in streaming fashion.

        Args:
            items: Iterator of items to process
            processor: Function to process each item

        Yields:
            Processed items
        """
        buffer = []
        with performance_context("streaming_process") as perf:
            for item in items:
                # Check memory usage
                try:
                    self.optimizer.memory_optimizer.check_memory_usage()
                except ResourceExhaustedError:
                    logger.warning("Memory limit reached, optimizing...")
                    self.optimizer.memory_optimizer.optimize_memory()
                # Process item
                try:
                    processed_item = processor(item)
                    buffer.append(processed_item)
                    self.processed_count += 1
                    # Yield buffered items when buffer is full
                    if len(buffer) >= self.config.buffer_size:
                        yield from buffer
                        perf.add_items(len(buffer))
                        buffer.clear()
                    # Create checkpoint periodically
                    if self.processed_count % self.config.checkpoint_interval == 0:
                        self._create_checkpoint()
                except Exception as e:
                    logger.error(f"Error processing item {self.processed_count}: {e}")
                    continue
            # Yield remaining buffered items
            yield from buffer
            if buffer:
                perf.add_items(len(buffer))

    def _create_checkpoint(self) -> None:
        """Create a processing checkpoint."""
        checkpoint = {
            "processed_count": self.processed_count,
            "timestamp": time.time(),
            "memory_usage": self.optimizer.memory_optimizer.check_memory_usage(),
        }
        self.checkpoints.append(checkpoint)
        # Keep only recent checkpoints
        if len(self.checkpoints) > 10:
            self.checkpoints = self.checkpoints[-10:]
        logger.debug(f"Created checkpoint at {self.processed_count} items")


class ChunkedFileProcessor:
    """Process large files in chunks to manage memory."""

    def __init__(self, chunk_size: int = 1024 * 1024):  # 1MB chunks
        """Initialize chunked file processor.

        Args:
            chunk_size: Size of each chunk in bytes
        """
        self.chunk_size = chunk_size
        self.optimizer = get_processing_optimizer()

    def process_file_chunks(
        self, file_path: Path, processor: Callable[[bytes], Any]
    ) -> Iterator[Any]:
        """Process file in chunks.

        Args:
            file_path: Path to file to process
            processor: Function to process each chunk

        Yields:
            Processed chunks
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        file_size = file_path.stat().st_size
        chunks_total = (file_size + self.chunk_size - 1) // self.chunk_size
        with performance_context(
            "chunked_file_processing", {"file_size": file_size, "chunks": chunks_total}
        ) as perf:
            with open(file_path, "rb") as f:
                chunk_num = 0
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    chunk_num += 1
                    # Check memory usage
                    self.optimizer.memory_optimizer.check_memory_usage()
                    # Process chunk
                    try:
                        result = processor(chunk)
                        yield result
                        perf.add_items(1)
                        if chunk_num % 10 == 0:
                            logger.debug(f"Processed chunk {chunk_num}/{chunks_total}")
                    except Exception as e:
                        logger.error(f"Error processing chunk {chunk_num}: {e}")
                        continue


class MemoryEfficientProcessor:
    """Memory-efficient processor for large datasets."""

    def __init__(self, max_memory_mb: float = 256.0):
        """Initialize memory-efficient processor.

        Args:
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_memory_mb = max_memory_mb
        self.optimizer = get_processing_optimizer()

    def process_with_memory_limit(
        self, items: list[T], processor: Callable[[T], U]
    ) -> Iterator[U]:
        """Process items with memory limit enforcement.

        Args:
            items: Items to process
            processor: Processing function

        Yields:
            Processed items
        """
        if not items:
            return
        # Calculate optimal batch size
        batch_size = self.optimizer.optimize_batch_size(
            len(items), item_size_estimate=1.0
        )
        with performance_context(
            "memory_efficient_processing", {"total_items": len(items)}
        ) as perf:
            for i in range(0, len(items), batch_size):
                batch = items[i : i + batch_size]
                # Process batch
                with self.optimizer.memory_optimizer.memory_limit_context(
                    self.max_memory_mb
                ):
                    for item in batch:
                        try:
                            result = processor(item)
                            yield result
                            perf.add_items(1)
                        except Exception as e:
                            logger.error(f"Error processing item: {e}")
                            continue
                # Clean up memory after each batch
                self.optimizer.memory_optimizer.optimize_memory()


class ProgressTrackingProcessor:
    """Processor with progress tracking capabilities."""

    def __init__(self, enable_logging: bool = True):
        """Initialize progress tracking processor.

        Args:
            enable_logging: Whether to enable progress logging
        """
        self.enable_logging = enable_logging
        self.start_time = None
        self.processed_items = 0
        self.total_items = 0

    def process_with_progress(
        self,
        items: list[T],
        processor: Callable[[T], U],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> Iterator[U]:
        """Process items with progress tracking.

        Args:
            items: Items to process
            processor: Processing function
            progress_callback: Optional callback for progress updates

        Yields:
            Processed items
        """
        self.total_items = len(items)
        self.processed_items = 0
        self.start_time = time.time()
        if self.enable_logging:
            logger.info(f"Starting processing of {self.total_items} items")
        with performance_context(
            "progress_tracking_processing", {"total_items": self.total_items}
        ) as perf:
            for i, item in enumerate(items):
                try:
                    result = processor(item)
                    yield result
                    self.processed_items += 1
                    perf.add_items(1)
                    # Update progress
                    if progress_callback:
                        progress_callback(self.processed_items, self.total_items)
                    # Log progress periodically
                    if self.enable_logging and self.processed_items % 100 == 0:
                        self._log_progress()
                except Exception as e:
                    logger.error(f"Error processing item {i}: {e}")
                    continue
        if self.enable_logging:
            self._log_completion()

    def _log_progress(self) -> None:
        """Log current progress."""
        if self.start_time is None:
            return
        elapsed = time.time() - self.start_time
        progress_percent = (self.processed_items / self.total_items) * 100
        if elapsed > 0:
            items_per_second = self.processed_items / elapsed
            eta_seconds = (self.total_items - self.processed_items) / items_per_second
            logger.info(
                f"Progress: {self.processed_items}/{self.total_items} ({progress_percent:.1f}%) "
                f"- {items_per_second:.1f} items/s - ETA: {eta_seconds:.0f}s"
            )

    def _log_completion(self) -> None:
        """Log completion statistics."""
        if self.start_time is None:
            return
        elapsed = time.time() - self.start_time
        items_per_second = self.processed_items / elapsed if elapsed > 0 else 0
        logger.info(
            f"Processing completed: {self.processed_items} items in {elapsed:.1f}s "
            f"({items_per_second:.1f} items/s)"
        )


class StreamingPDFProcessor:
    """Streaming processor specifically for PDF documents."""

    def __init__(self, config: StreamingConfig | None = None):
        """Initialize streaming PDF processor.

        Args:
            config: Optional streaming configuration
        """
        self.config = config or StreamingConfig()
        self.streaming_processor = StreamingProcessor(self.config)
        self.memory_processor = MemoryEfficientProcessor(self.config.max_memory_mb)

    def process_pdf_pages_streaming(
        self, pdf_path: Path, page_processor: Callable[[Any], Any]
    ) -> Iterator[Any]:
        """Process PDF pages in streaming fashion.

        Args:
            pdf_path: Path to PDF file
            page_processor: Function to process each page

        Yields:
            Processed pages
        """
        import fitz  # PyMuPDF

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        with fitz.open(pdf_path) as doc:
            total_pages = doc.page_count
            logger.info(f"Processing {total_pages} pages from {pdf_path.name}")

            # Create page iterator
            def page_iterator():
                for page_num in range(total_pages):
                    yield doc[page_num]

            # Process pages in streaming fashion
            yield from self.streaming_processor.stream_process(
                page_iterator(), page_processor
            )

    def process_multiple_pdfs_streaming(
        self, pdf_paths: list[Path], pdf_processor: Callable[[Path], Any]
    ) -> Iterator[Any]:
        """Process multiple PDF files in streaming fashion.

        Args:
            pdf_paths: List of PDF file paths
            pdf_processor: Function to process each PDF

        Yields:
            Processed PDF results
        """
        logger.info(f"Processing {len(pdf_paths)} PDF files")
        # Use memory-efficient processing for multiple files
        yield from self.memory_processor.process_with_memory_limit(
            pdf_paths, pdf_processor
        )


def create_streaming_iterator(  # noqa: UP047
    items: list[T], chunk_size: int = 100
) -> Iterator[list[T]]:
    """Create a streaming iterator that yields chunks of items.

    Args:
        items: Items to iterate over
        chunk_size: Size of each chunk

    Yields:
        Chunks of items
    """
    for i in range(0, len(items), chunk_size):
        yield items[i : i + chunk_size]


def streaming_map(func: Callable[[T], U], items: Iterator[T]) -> Iterator[U]:
    """Apply function to items in streaming fashion.

    Args:
        func: Function to apply
        items: Iterator of items

    Yields:
        Mapped items
    """
    for item in items:
        yield func(item)


def streaming_filter(predicate: Callable[[T], bool], items: Iterator[T]) -> Iterator[T]:
    """Filter items in streaming fashion.

    Args:
        predicate: Filter predicate
        items: Iterator of items

    Yields:
        Filtered items
    """
    for item in items:
        if predicate(item):
            yield item


def streaming_reduce(func: Callable[[T, U], T], items: Iterator[U], initial: T) -> T:
    """Reduce items in streaming fashion.

    Args:
        func: Reduction function
        items: Iterator of items
        initial: Initial value

    Returns:
        Reduced value
    """
    result = initial
    for item in items:
        result = func(result, item)
    return result
