"""Performance monitoring and optimization utilities."""
from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, TypeVar

import psutil

from .config import get_config
from .exceptions import ProcessingTimeoutError, ResourceExhaustedError

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class PerformanceMetrics:
    """Performance metrics for a processing operation."""
    operation_name: str
    start_time: float
    end_time: float | None = None
    duration: float | None = None
    memory_usage_mb: float | None = None
    peak_memory_mb: float | None = None
    cpu_percent: float | None = None
    items_processed: int | None = None
    throughput: float | None = None  # items per second
    metadata: dict[str, Any] = field(default_factory=dict)

    def finalize(self) -> None:
        """Finalize metrics calculation."""
        if self.end_time is None:
            self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        if self.items_processed is not None and self.duration > 0:
            self.throughput = self.items_processed / self.duration

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "operation_name": self.operation_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "memory_usage_mb": self.memory_usage_mb,
            "peak_memory_mb": self.peak_memory_mb,
            "cpu_percent": self.cpu_percent,
            "items_processed": self.items_processed,
            "throughput": self.throughput,
            "metadata": self.metadata
        }


class PerformanceMonitor:
    """Monitor and track performance metrics."""

    def __init__(self):
        """Initialize performance monitor."""
        self.config = get_config()
        self.metrics_history: list[PerformanceMetrics] = []
        self.active_operations: dict[str, PerformanceMetrics] = {}
        self._lock = threading.Lock()
        self._monitoring_enabled = self.config.performance.cache["enabled"]

    def start_operation(self, operation_name: str, metadata: dict[str, Any] | None = None) -> str:
        """Start monitoring an operation.

        Args:
            operation_name: Name of the operation
            metadata: Optional metadata

        Returns:
            Operation ID for tracking
        """
        if not self._monitoring_enabled:
            return operation_name
        operation_id = f"{operation_name}_{int(time.time() * 1000)}"
        metrics = PerformanceMetrics(
            operation_name=operation_name,
            start_time=time.time(),
            metadata=metadata or {}
        )
        # Get initial memory usage
        try:
            process = psutil.Process()
            metrics.memory_usage_mb = process.memory_info().rss / 1024 / 1024
        except Exception as e:
            logger.debug(f"Failed to get memory info: {e}")
        with self._lock:
            self.active_operations[operation_id] = metrics
        return operation_id

    def end_operation(self, operation_id: str, items_processed: int | None = None) -> PerformanceMetrics:
        """End monitoring an operation.

        Args:
            operation_id: Operation ID from start_operation
            items_processed: Number of items processed

        Returns:
            Final performance metrics
        """
        if not self._monitoring_enabled:
            return PerformanceMetrics(operation_name="disabled", start_time=time.time())
        with self._lock:
            if operation_id not in self.active_operations:
                logger.warning(f"Operation {operation_id} not found in active operations")
                return PerformanceMetrics(operation_name="unknown", start_time=time.time())
            metrics = self.active_operations.pop(operation_id)
        # Finalize metrics
        metrics.end_time = time.time()
        metrics.items_processed = items_processed
        # Get final memory and CPU usage
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            metrics.peak_memory_mb = memory_info.rss / 1024 / 1024
            metrics.cpu_percent = process.cpu_percent()
        except Exception as e:
            logger.debug(f"Failed to get final system info: {e}")
        metrics.finalize()
        # Store in history
        with self._lock:
            self.metrics_history.append(metrics)
            # Keep only recent metrics to avoid memory bloat
            max_history = 1000
            if len(self.metrics_history) > max_history:
                self.metrics_history = self.metrics_history[-max_history:]
        logger.info(f"Operation {metrics.operation_name} completed in {metrics.duration:.2f}s")
        return metrics

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get summary of all metrics.

        Returns:
            Summary of performance metrics
        """
        with self._lock:
            if not self.metrics_history:
                return {"total_operations": 0, "average_duration": 0, "operations": []}
            total_ops = len(self.metrics_history)
            avg_duration = sum(m.duration or 0 for m in self.metrics_history) / total_ops
            avg_memory = sum(m.peak_memory_mb or 0 for m in self.metrics_history) / total_ops
            # Group by operation name
            operation_stats = {}
            for metric in self.metrics_history:
                name = metric.operation_name
                if name not in operation_stats:
                    operation_stats[name] = {
                        "count": 0,
                        "total_duration": 0,
                        "total_items": 0,
                        "avg_throughput": 0
                    }
                stats = operation_stats[name]
                stats["count"] += 1
                stats["total_duration"] += metric.duration or 0
                stats["total_items"] += metric.items_processed or 0
                if metric.throughput:
                    stats["avg_throughput"] += metric.throughput
            # Calculate averages
            for stats in operation_stats.values():
                if stats["count"] > 0:
                    stats["avg_duration"] = stats["total_duration"] / stats["count"]
                    stats["avg_throughput"] = stats["avg_throughput"] / stats["count"]
            return {
                "total_operations": total_ops,
                "average_duration": avg_duration,
                "average_memory_mb": avg_memory,
                "operations": operation_stats,
                "recent_metrics": [m.to_dict() for m in self.metrics_history[-10:]]
            }

    def clear_metrics(self) -> None:
        """Clear all stored metrics."""
        with self._lock:
            self.metrics_history.clear()
            self.active_operations.clear()


# Global performance monitor
_performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor.

    Returns:
        Global performance monitor instance
    """
    return _performance_monitor


@contextmanager
def performance_context(operation_name: str, metadata: dict[str, Any] | None = None):
    """Context manager for performance monitoring.

    Args:
        operation_name: Name of the operation
        metadata: Optional metadata

    Yields:
        Performance metrics object
    """
    monitor = get_performance_monitor()
    operation_id = monitor.start_operation(operation_name, metadata)
    try:
        # Create a simple object to track items
        class Context:
            def __init__(self):
                self.items_processed = 0

            def add_items(self, count: int) -> None:
                self.items_processed += count
        context = Context()
        yield context
    finally:
        monitor.end_operation(operation_id, context.items_processed)


def performance_profile(operation_name: str | None = None, track_memory: bool = True):
    """Decorator for performance profiling.

    Args:
        operation_name: Optional operation name (defaults to function name)
        track_memory: Whether to track memory usage

    Returns:
        Decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            name = operation_name or func.__name__
            metadata = {
                "function": func.__name__,
                "module": func.__module__,
                "track_memory": track_memory
            }
            monitor = get_performance_monitor()
            operation_id = monitor.start_operation(name, metadata)
            try:
                result = func(*args, **kwargs)
                # Try to determine items processed from result
                items_processed = None
                if hasattr(result, '__len__'):
                    try:
                        items_processed = len(result)
                    except (TypeError, AttributeError):
                        pass
                return result
            finally:
                monitor.end_operation(operation_id, items_processed)
        return wrapper
    return decorator


class MemoryOptimizer:
    """Memory optimization utilities."""

    def __init__(self):
        """Initialize memory optimizer."""
        self.config = get_config()
        self.max_memory_mb = self.config.processing.memory["max_memory_per_doc_mb"]
        self.monitoring_enabled = self.config.processing.memory["enable_monitoring"]

    def check_memory_usage(self) -> float:
        """Check current memory usage.

        Returns:
            Current memory usage in MB

        Raises:
            ResourceExhaustedError: If memory limit exceeded
        """
        if not self.monitoring_enabled:
            return 0.0
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            if memory_mb > self.max_memory_mb:
                raise ResourceExhaustedError(
                    f"Memory usage ({memory_mb:.1f}MB) exceeds limit ({self.max_memory_mb}MB)",
                    resource_type="memory",
                    limit=self.max_memory_mb
                )
            return memory_mb
        except psutil.Error as e:
            logger.warning(f"Failed to check memory usage: {e}")
            return 0.0

    def optimize_memory(self) -> None:
        """Trigger memory optimization."""
        import gc
        # Force garbage collection
        collected = gc.collect()
        if collected > 0:
            logger.debug(f"Garbage collected {collected} objects")

    @contextmanager
    def memory_limit_context(self, custom_limit_mb: float | None = None):
        """Context manager for memory limit checking.

        Args:
            custom_limit_mb: Optional custom memory limit
        """
        original_limit = self.max_memory_mb
        if custom_limit_mb is not None:
            self.max_memory_mb = custom_limit_mb
        try:
            yield self
        finally:
            self.max_memory_mb = original_limit


class ProcessingOptimizer:
    """Processing optimization utilities."""

    def __init__(self):
        """Initialize processing optimizer."""
        self.config = get_config()
        self.memory_optimizer = MemoryOptimizer()
        self.performance_monitor = get_performance_monitor()

    def optimize_batch_size(self, total_items: int, item_size_estimate: float = 1.0) -> int:
        """Calculate optimal batch size for processing.

        Args:
            total_items: Total number of items to process
            item_size_estimate: Estimated size per item in MB

        Returns:
            Optimal batch size
        """
        max_memory_mb = self.memory_optimizer.max_memory_mb
        # Reserve 50% of memory for overhead
        available_memory = max_memory_mb * 0.5
        # Calculate batch size based on memory
        memory_based_batch = int(available_memory / item_size_estimate)
        # Apply reasonable limits
        min_batch = 1
        max_batch = min(1000, total_items)  # Cap at 1000 or total items
        optimal_batch = max(min_batch, min(memory_based_batch, max_batch))
        logger.debug(f"Calculated optimal batch size: {optimal_batch} for {total_items} items")
        return optimal_batch

    def process_in_batches(self, items: list[Any], processor: Callable[[list[Any]], Any],
                          batch_size: int | None = None) -> list[Any]:
        """Process items in optimized batches.

        Args:
            items: List of items to process
            processor: Function to process each batch
            batch_size: Optional custom batch size

        Returns:
            List of processed results
        """
        if not items:
            return []
        # Calculate optimal batch size if not provided
        if batch_size is None:
            batch_size = self.optimize_batch_size(len(items))
        results = []
        total_batches = (len(items) + batch_size - 1) // batch_size
        with performance_context("batch_processing", {"total_items": len(items), "batch_size": batch_size}) as perf:
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                batch_num = i // batch_size + 1
                logger.debug(f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)")
                # Check memory before processing batch
                self.memory_optimizer.check_memory_usage()
                # Process batch
                try:
                    batch_result = processor(batch)
                    results.extend(batch_result if isinstance(batch_result, list) else [batch_result])
                    # Update performance tracking
                    perf.add_items(len(batch))
                except Exception as e:
                    logger.error(f"Error processing batch {batch_num}: {e}")
                    raise
                # Optimize memory after each batch
                if batch_num % 10 == 0:  # Every 10 batches
                    self.memory_optimizer.optimize_memory()
        return results

    def parallel_process(self, items: list[Any], processor: Callable[[Any], Any],
                        max_workers: int | None = None) -> list[Any]:
        """Process items in parallel with optimization.

        Args:
            items: List of items to process
            processor: Function to process each item
            max_workers: Maximum number of worker threads

        Returns:
            List of processed results
        """
        if not items:
            return []
        # Determine optimal number of workers
        if max_workers is None:
            max_workers = min(4, len(items))  # Cap at 4 workers
        # Use thread pool for I/O bound tasks
        from concurrent.futures import ThreadPoolExecutor, as_completed
        results = []
        with performance_context("parallel_processing", {"total_items": len(items), "max_workers": max_workers}) as perf:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_item = {executor.submit(processor, item): item for item in items}
                # Collect results as they complete
                for future in as_completed(future_to_item):
                    try:
                        result = future.result()
                        results.append(result)
                        perf.add_items(1)
                        # Check memory periodically
                        if len(results) % 10 == 0:
                            self.memory_optimizer.check_memory_usage()
                    except Exception as e:
                        item = future_to_item[future]
                        logger.error(f"Error processing item {item}: {e}")
                        raise
        return results


# Global processing optimizer
_processing_optimizer = ProcessingOptimizer()


def get_processing_optimizer() -> ProcessingOptimizer:
    """Get the global processing optimizer.

    Returns:
        Global processing optimizer instance
    """
    return _processing_optimizer


def timeout_handler(timeout_seconds: float):
    """Decorator for handling operation timeouts.

    Args:
        timeout_seconds: Timeout in seconds

    Returns:
        Decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            import threading
            result = [None]
            exception = [None]
            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout_seconds)
            if thread.is_alive():
                # Timeout occurred
                raise ProcessingTimeoutError(
                    f"Operation {func.__name__} timed out after {timeout_seconds}s",
                    timeout_seconds=int(timeout_seconds),
                    operation=func.__name__
                )
            if exception[0]:
                raise exception[0]
            return result[0]
        return wrapper
    return decorator
