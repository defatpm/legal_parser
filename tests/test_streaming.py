from pathlib import Path

import pytest

from src.utils.streaming import (
    ChunkedFileProcessor,
    MemoryEfficientProcessor,
    ProgressTrackingProcessor,
    StreamingProcessor,
    create_streaming_iterator,
    streaming_filter,
    streaming_map,
    streaming_reduce,
)


class TestStreamingProcessor:
    """Tests for StreamingProcessor class."""

    def test_streaming_processor_initialization(self):
        """Test streaming processor initialization."""
        processor = StreamingProcessor()

        assert processor.processed_count == 0
        assert processor.checkpoints == []

    def test_stream_process(self):
        """Test streaming processing."""
        processor = StreamingProcessor()

        # Simple processor that doubles values
        def item_processor(item):
            return item * 2

        items = iter(range(10))
        results = list(processor.stream_process(items, item_processor))

        assert len(results) == 10
        assert results == [x * 2 for x in range(10)]
        assert processor.processed_count == 10

    def test_stream_process_with_error(self):
        """Test streaming processing with an error."""
        processor = StreamingProcessor()

        def item_processor(item):
            if item == 5:
                raise ValueError("Test error")
            return item * 2

        items = iter(range(10))
        results = list(processor.stream_process(items, item_processor))

        assert len(results) == 9
        assert results == [0, 2, 4, 6, 8, 12, 14, 16, 18]
        assert processor.processed_count == 9


class TestChunkedFileProcessor:
    """Tests for ChunkedFileProcessor class."""

    def test_chunked_file_processor_initialization(self):
        """Test chunked file processor initialization."""
        processor = ChunkedFileProcessor(chunk_size=1024)

        assert processor.chunk_size == 1024

    def test_process_file_chunks(self, tmp_path):
        """Test processing file in chunks."""
        processor = ChunkedFileProcessor(chunk_size=10)

        # Create a temporary file
        file_path = tmp_path / "test.txt"
        file_path.write_text("Hello, World! This is a test file.")

        # Simple processor that counts bytes
        def chunk_processor(chunk):
            return len(chunk)

        results = list(processor.process_file_chunks(file_path, chunk_processor))

        assert len(results) > 0
        assert sum(results) > 0  # Total bytes processed

    def test_process_file_chunks_with_error(self, tmp_path):
        """Test processing file in chunks with an error."""
        processor = ChunkedFileProcessor(chunk_size=10)

        file_path = tmp_path / "test.txt"
        file_path.write_text("Hello, World! This is a test file.")

        def chunk_processor(chunk):
            if b"This" in chunk:
                raise ValueError("Test error")
            return len(chunk)

        results = list(processor.process_file_chunks(file_path, chunk_processor))

        assert len(results) > 0

    def test_process_nonexistent_file(self):
        """Test processing non-existent file."""
        processor = ChunkedFileProcessor()

        with pytest.raises(FileNotFoundError):
            list(processor.process_file_chunks(Path("nonexistent.txt"), lambda x: x))


class TestMemoryEfficientProcessor:
    """Tests for MemoryEfficientProcessor class."""

    def test_memory_efficient_processor_initialization(self):
        """Test memory efficient processor initialization."""
        processor = MemoryEfficientProcessor(max_memory_mb=128.0)

        assert processor.max_memory_mb == 128.0

    def test_process_with_memory_limit(self):
        """Test processing with memory limit."""
        processor = MemoryEfficientProcessor(max_memory_mb=512.0)

        # Simple processor that squares values
        def item_processor(item):
            return item**2

        items = list(range(10))
        results = list(processor.process_with_memory_limit(items, item_processor))

        assert len(results) == 10
        assert results == [x**2 for x in range(10)]


class TestProgressTrackingProcessor:
    """Tests for ProgressTrackingProcessor class."""

    def test_progress_tracking_processor_initialization(self):
        """Test progress tracking processor initialization."""
        processor = ProgressTrackingProcessor(enable_logging=False)

        assert processor.enable_logging is False
        assert processor.processed_items == 0

    def test_process_with_progress(self):
        """Test processing with progress tracking."""
        processor = ProgressTrackingProcessor(enable_logging=False)

        # Simple processor that doubles values
        def item_processor(item):
            return item * 2

        # Progress callback
        progress_updates = []

        def progress_callback(processed, total):
            progress_updates.append((processed, total))

        items = list(range(5))
        results = list(
            processor.process_with_progress(items, item_processor, progress_callback)
        )

        assert len(results) == 5
        assert results == [x * 2 for x in range(5)]
        assert processor.processed_items == 5
        assert processor.total_items == 5
        assert len(progress_updates) == 5


class TestStreamingUtilities:
    """Tests for streaming utility functions."""

    def test_create_streaming_iterator(self):
        """Test creating streaming iterator."""
        items = list(range(10))
        chunks = list(create_streaming_iterator(items, chunk_size=3))

        assert len(chunks) == 4  # 3 + 3 + 3 + 1
        assert chunks[0] == [0, 1, 2]
        assert chunks[1] == [3, 4, 5]
        assert chunks[2] == [6, 7, 8]
        assert chunks[3] == [9]

    def test_streaming_map(self):
        """Test streaming map function."""
        items = iter(range(5))
        results = list(streaming_map(lambda x: x * 2, items))

        assert results == [0, 2, 4, 6, 8]

    def test_streaming_filter(self):
        """Test streaming filter function."""
        items = iter(range(10))
        results = list(streaming_filter(lambda x: x % 2 == 0, items))

        assert results == [0, 2, 4, 6, 8]

    def test_streaming_reduce(self):
        """Test streaming reduce function."""
        items = iter(range(1, 6))  # 1, 2, 3, 4, 5
        result = streaming_reduce(lambda acc, x: acc + x, items, 0)

        assert result == 15  # Sum of 1+2+3+4+5
