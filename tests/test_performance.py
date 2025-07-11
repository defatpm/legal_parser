"""Tests for performance monitoring and optimization."""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pytest

from src.utils.exceptions import ProcessingTimeoutError
from src.utils.performance import (
    MemoryOptimizer,
    PerformanceMetrics,
    PerformanceMonitor,
    ProcessingOptimizer,
    get_performance_monitor,
    get_processing_optimizer,
    performance_context,
    performance_profile,
    timeout_handler,
)
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


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics class."""

    def test_metrics_creation(self):
        """Test creating performance metrics."""
        metrics = PerformanceMetrics(
            operation_name="test_operation",
            start_time=time.time(),
            items_processed=100,
            metadata={"key": "value"}
        )

        assert metrics.operation_name == "test_operation"
        assert metrics.items_processed == 100
        assert metrics.metadata == {"key": "value"}
        assert metrics.duration is None
        assert metrics.throughput is None

    def test_metrics_finalization(self):
        """Test metrics finalization."""
        start_time = time.time()
        metrics = PerformanceMetrics(
            operation_name="test_operation",
            start_time=start_time,
            items_processed=100
        )

        # Simulate some processing time
        time.sleep(0.1)
        metrics.finalize()

        assert metrics.end_time is not None
        assert metrics.duration is not None
        assert metrics.duration > 0
        assert metrics.throughput is not None
        assert metrics.throughput > 0

    def test_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = PerformanceMetrics(
            operation_name="test_operation",
            start_time=time.time(),
            items_processed=50
        )
        metrics.finalize()

        metrics_dict = metrics.to_dict()

        assert metrics_dict["operation_name"] == "test_operation"
        assert metrics_dict["items_processed"] == 50
        assert "duration" in metrics_dict
        assert "throughput" in metrics_dict


class TestPerformanceMonitor:
    """Tests for PerformanceMonitor class."""

    def test_monitor_initialization(self):
        """Test monitor initialization."""
        monitor = PerformanceMonitor()

        assert monitor.metrics_history == []
        assert monitor.active_operations == {}

    def test_start_end_operation(self):
        """Test starting and ending operations."""
        monitor = PerformanceMonitor()

        # Start operation
        operation_id = monitor.start_operation("test_op", {"key": "value"})
        assert operation_id.startswith("test_op_")
        assert operation_id in monitor.active_operations

        # End operation
        metrics = monitor.end_operation(operation_id, items_processed=10)

        assert metrics.operation_name == "test_op"
        assert metrics.items_processed == 10
        assert metrics.duration is not None
        assert operation_id not in monitor.active_operations
        assert len(monitor.metrics_history) == 1

    def test_metrics_summary(self):
        """Test getting metrics summary."""
        monitor = PerformanceMonitor()

        # Process some operations
        for i in range(3):
            op_id = monitor.start_operation(f"op_{i}", {"test": True})
            time.sleep(0.01)  # Small delay
            monitor.end_operation(op_id, items_processed=i + 1)

        summary = monitor.get_metrics_summary()

        assert summary["total_operations"] == 3
        assert summary["average_duration"] > 0
        assert len(summary["operations"]) >= 1
        assert len(summary["recent_metrics"]) == 3

    def test_clear_metrics(self):
        """Test clearing metrics."""
        monitor = PerformanceMonitor()

        # Add some metrics
        op_id = monitor.start_operation("test_op")
        monitor.end_operation(op_id)

        assert len(monitor.metrics_history) == 1

        monitor.clear_metrics()

        assert len(monitor.metrics_history) == 0
        assert len(monitor.active_operations) == 0


class TestMemoryOptimizer:
    """Tests for MemoryOptimizer class."""

    def test_optimizer_initialization(self):
        """Test optimizer initialization."""
        optimizer = MemoryOptimizer()

        assert optimizer.max_memory_mb > 0
        assert isinstance(optimizer.monitoring_enabled, bool)

    def test_check_memory_usage(self):
        """Test checking memory usage."""
        optimizer = MemoryOptimizer()

        # Should not raise under normal conditions
        memory_usage = optimizer.check_memory_usage()
        assert memory_usage >= 0

    def test_optimize_memory(self):
        """Test memory optimization."""
        optimizer = MemoryOptimizer()

        # Should not raise
        optimizer.optimize_memory()

    def test_memory_limit_context(self):
        """Test memory limit context manager."""
        optimizer = MemoryOptimizer()
        original_limit = optimizer.max_memory_mb

        with optimizer.memory_limit_context(100.0):
            assert optimizer.max_memory_mb == 100.0

        assert optimizer.max_memory_mb == original_limit


class TestProcessingOptimizer:
    """Tests for ProcessingOptimizer class."""

    def test_optimizer_initialization(self):
        """Test optimizer initialization."""
        optimizer = ProcessingOptimizer()

        assert optimizer.memory_optimizer is not None
        assert optimizer.performance_monitor is not None

    def test_optimize_batch_size(self):
        """Test batch size optimization."""
        optimizer = ProcessingOptimizer()

        # Test with small number of items
        batch_size = optimizer.optimize_batch_size(10, item_size_estimate=1.0)
        assert 1 <= batch_size <= 10

        # Test with large number of items
        batch_size = optimizer.optimize_batch_size(10000, item_size_estimate=0.1)
        assert 1 <= batch_size <= 1000

    def test_process_in_batches(self):
        """Test batch processing."""
        optimizer = ProcessingOptimizer()

        # Simple processor that doubles values
        def processor(batch):
            return [x * 2 for x in batch]

        items = list(range(10))
        results = optimizer.process_in_batches(items, processor, batch_size=3)

        assert len(results) == 10
        assert results == [x * 2 for x in range(10)]

    def test_parallel_process(self):
        """Test parallel processing."""
        optimizer = ProcessingOptimizer()

        # Simple processor that squares values
        def processor(item):
            return item ** 2

        items = list(range(5))
        results = optimizer.parallel_process(items, processor, max_workers=2)

        assert len(results) == 5
        assert sorted(results) == [x ** 2 for x in range(5)]


class TestPerformanceDecorators:
    """Tests for performance decorators."""

    def test_performance_context(self):
        """Test performance context manager."""
        with performance_context("test_operation") as ctx:
            ctx.add_items(5)
            time.sleep(0.01)

        monitor = get_performance_monitor()
        assert len(monitor.metrics_history) >= 1

        # Find our operation
        test_metrics = [m for m in monitor.metrics_history if m.operation_name == "test_operation"]
        assert len(test_metrics) >= 1
        assert test_metrics[-1].items_processed == 5

    def test_performance_profile_decorator(self):
        """Test performance profile decorator."""
        @performance_profile("test_function")
        def test_function(items):
            time.sleep(0.01)
            return items

        result = test_function([1, 2, 3])

        assert result == [1, 2, 3]

        monitor = get_performance_monitor()
        test_metrics = [m for m in monitor.metrics_history if m.operation_name == "test_function"]
        assert len(test_metrics) >= 1
        assert test_metrics[-1].duration > 0

    def test_timeout_handler(self):
        """Test timeout handler decorator."""
        @timeout_handler(0.1)
        def slow_function():
            time.sleep(0.2)
            return "completed"

        with pytest.raises(ProcessingTimeoutError):
            slow_function()

    def test_timeout_handler_success(self):
        """Test timeout handler with successful completion."""
        @timeout_handler(0.2)
        def fast_function():
            time.sleep(0.05)
            return "completed"

        result = fast_function()
        assert result == "completed"


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


class TestChunkedFileProcessor:
    """Tests for ChunkedFileProcessor class."""

    def test_chunked_file_processor_initialization(self):
        """Test chunked file processor initialization."""
        processor = ChunkedFileProcessor(chunk_size=1024)

        assert processor.chunk_size == 1024

    def test_process_file_chunks(self):
        """Test processing file in chunks."""
        processor = ChunkedFileProcessor(chunk_size=10)

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp.write("Hello, World! This is a test file.")
            tmp_path = Path(tmp.name)

        try:
            # Simple processor that counts bytes
            def chunk_processor(chunk):
                return len(chunk)

            results = list(processor.process_file_chunks(tmp_path, chunk_processor))

            assert len(results) > 0
            assert sum(results) > 0  # Total bytes processed

        finally:
            tmp_path.unlink()

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
            return item ** 2

        items = list(range(10))
        results = list(processor.process_with_memory_limit(items, item_processor))

        assert len(results) == 10
        assert results == [x ** 2 for x in range(10)]


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
        results = list(processor.process_with_progress(items, item_processor, progress_callback))

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


class TestGlobalInstances:
    """Tests for global instances."""

    def test_get_performance_monitor(self):
        """Test getting global performance monitor."""
        monitor1 = get_performance_monitor()
        monitor2 = get_performance_monitor()

        assert monitor1 is monitor2  # Should be same instance
        assert isinstance(monitor1, PerformanceMonitor)

    def test_get_processing_optimizer(self):
        """Test getting global processing optimizer."""
        optimizer1 = get_processing_optimizer()
        optimizer2 = get_processing_optimizer()

        assert optimizer1 is optimizer2  # Should be same instance
        assert isinstance(optimizer1, ProcessingOptimizer)
