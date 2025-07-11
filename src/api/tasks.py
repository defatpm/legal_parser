"""Task management for async processing."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ..processors.pdf_extractor import PDFExtractor
from ..utils.error_handler import get_error_handler
from ..utils.performance import get_performance_monitor
from .models import (
    ProcessingRequest,
    ProcessingStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class TaskInfo:
    """Information about a processing task."""

    task_id: str
    filename: str
    file_path: Path
    request: ProcessingRequest
    status: ProcessingStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    progress: float = 0.0
    current_page: int | None = None
    total_pages: int | None = None
    result: Any | None = None
    error: str | None = None
    processing_time: float | None = None
    file_size_mb: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert task info to dictionary."""
        return {
            "task_id": self.task_id,
            "filename": self.filename,
            "file_path": str(self.file_path),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "progress": self.progress,
            "current_page": self.current_page,
            "total_pages": self.total_pages,
            "error": self.error,
            "processing_time": self.processing_time,
            "file_size_mb": self.file_size_mb,
        }


class TaskManager:
    """Manages processing tasks and their lifecycle."""

    def __init__(self, max_concurrent_tasks: int = 4):
        """Initialize task manager.

        Args:
            max_concurrent_tasks: Maximum number of concurrent tasks
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self.tasks: dict[str, TaskInfo] = {}
        self.processing_queue: asyncio.Queue = asyncio.Queue()
        self.active_tasks: dict[str, asyncio.Task] = {}
        self.workers: list[asyncio.Task] = []
        self.running = False
        self.performance_monitor = get_performance_monitor()
        self.error_handler = get_error_handler()
        # Statistics
        self.total_processed = 0
        self.total_failed = 0
        self.start_time = datetime.now()

    async def start(self):
        """Start the task manager and workers."""
        if self.running:
            return
        self.running = True
        # Start worker tasks
        for i in range(self.max_concurrent_tasks):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)

        logger.info(f"Started task manager with {self.max_concurrent_tasks} workers")

    async def stop(self):
        """Stop the task manager and workers."""
        if not self.running:
            return
        self.running = False
        # Cancel all active tasks
        for task in self.active_tasks.values():
            task.cancel()

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        self.active_tasks.clear()
        logger.info("Stopped task manager")

    async def submit_task(
        self, filename: str, file_path: Path, request: ProcessingRequest
    ) -> str:
        """Submit a new processing task.

        Args:
            filename: Original filename
            file_path: Path to the file
            request: Processing request parameters

        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        # Get file size
        file_size_mb = (
            file_path.stat().st_size / (1024 * 1024) if file_path.exists() else 0
        )
        task_info = TaskInfo(
            task_id=task_id,
            filename=filename,
            file_path=file_path,
            request=request,
            status=ProcessingStatus.PENDING,
            created_at=datetime.now(),
            file_size_mb=file_size_mb,
        )
        self.tasks[task_id] = task_info
        await self.processing_queue.put(task_id)
        logger.info(f"Submitted task {task_id} for file {filename}")
        return task_id

    async def get_task_status(self, task_id: str) -> TaskInfo | None:
        """Get the status of a task.

        Args:
            task_id: Task ID

        Returns:
            Task information or None if not found
        """
        return self.tasks.get(task_id)

    async def get_task_result(self, task_id: str) -> Any | None:
        """Get the result of a completed task.

        Args:
            task_id: Task ID

        Returns:
            Task result or None if not available
        """
        task_info = self.tasks.get(task_id)
        if task_info and task_info.status == ProcessingStatus.COMPLETED:
            return task_info.result
        return None

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task.

        Args:
            task_id: Task ID

        Returns:
            True if task was cancelled, False otherwise
        """
        task_info = self.tasks.get(task_id)
        if not task_info:
            return False
        if task_info.status in [
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED,
            ProcessingStatus.CANCELLED,
        ]:
            return False
        # Cancel active task
        if task_id in self.active_tasks:
            self.active_tasks[task_id].cancel()
            del self.active_tasks[task_id]
        # Update task status
        task_info.status = ProcessingStatus.CANCELLED
        task_info.completed_at = datetime.now()
        logger.info(f"Cancelled task {task_id}")
        return True

    async def get_queue_status(self) -> dict[str, Any]:
        """Get processing queue status.

        Returns:
            Queue status information
        """
        pending_tasks = [
            t for t in self.tasks.values() if t.status == ProcessingStatus.PENDING
        ]
        processing_tasks = [
            t for t in self.tasks.values() if t.status == ProcessingStatus.PROCESSING
        ]
        completed_tasks = [
            t for t in self.tasks.values() if t.status == ProcessingStatus.COMPLETED
        ]
        failed_tasks = [
            t for t in self.tasks.values() if t.status == ProcessingStatus.FAILED
        ]
        return {
            "queue_size": len(pending_tasks),
            "processing_tasks": len(processing_tasks),
            "completed_tasks": len(completed_tasks),
            "failed_tasks": len(failed_tasks),
            "active_workers": len(self.active_tasks),
            "max_workers": self.max_concurrent_tasks,
            "total_processed": self.total_processed,
            "total_failed": self.total_failed,
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
        }

    async def get_statistics(self) -> dict[str, Any]:
        """Get processing statistics.

        Returns:
            Processing statistics
        """
        completed_tasks = [
            t for t in self.tasks.values() if t.status == ProcessingStatus.COMPLETED
        ]
        if not completed_tasks:
            return {
                "total_requests": len(self.tasks),
                "completed_requests": 0,
                "failed_requests": self.total_failed,
                "average_processing_time": 0.0,
                "average_file_size_mb": 0.0,
                "average_pages_per_document": 0.0,
                "total_pages_processed": 0,
                "total_ocr_pages": 0,
            }
        total_processing_time = sum(
            t.processing_time for t in completed_tasks if t.processing_time
        )
        total_file_size = sum(t.file_size_mb for t in completed_tasks if t.file_size_mb)
        # Calculate page statistics from results
        total_pages = 0
        total_ocr_pages = 0
        for task in completed_tasks:
            if task.result and hasattr(task.result, "output"):
                pages = task.result.output
                if pages:
                    total_pages += len(pages)
                    total_ocr_pages += sum(
                        1
                        for page in pages
                        if hasattr(page, "is_ocr_applied") and page.is_ocr_applied
                    )
        return {
            "total_requests": len(self.tasks),
            "completed_requests": len(completed_tasks),
            "failed_requests": self.total_failed,
            "average_processing_time": total_processing_time / len(completed_tasks)
            if completed_tasks
            else 0.0,
            "average_file_size_mb": total_file_size / len(completed_tasks)
            if completed_tasks
            else 0.0,
            "average_pages_per_document": total_pages / len(completed_tasks)
            if completed_tasks
            else 0.0,
            "total_pages_processed": total_pages,
            "total_ocr_pages": total_ocr_pages,
        }

    async def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Clean up old completed tasks.

        Args:
            max_age_hours: Maximum age of tasks to keep in hours
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        tasks_to_remove = []
        for task_id, task_info in self.tasks.items():
            if (
                task_info.status
                in [
                    ProcessingStatus.COMPLETED,
                    ProcessingStatus.FAILED,
                    ProcessingStatus.CANCELLED,
                ]
                and task_info.completed_at
                and task_info.completed_at < cutoff_time
            ):
                tasks_to_remove.append(task_id)
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
        if tasks_to_remove:
            logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")

    async def _worker(self, worker_name: str):
        """Worker coroutine for processing tasks.

        Args:
            worker_name: Name of the worker
        """
        logger.info(f"Started worker {worker_name}")
        try:
            while self.running:
                try:
                    # Get next task from queue
                    task_id = await asyncio.wait_for(
                        self.processing_queue.get(), timeout=1.0
                    )
                    # Process the task
                    await self._process_task(task_id, worker_name)
                except TimeoutError:
                    # Continue to check if we should stop
                    continue
                except Exception as e:
                    logger.error(f"Worker {worker_name} error: {e}")
                    continue
        except asyncio.CancelledError:
            pass
        logger.info(f"Stopped worker {worker_name}")

    async def _process_task(self, task_id: str, worker_name: str):
        """Process a single task.

        Args:
            task_id: Task ID
            worker_name: Name of the processing worker
        """
        task_info = self.tasks.get(task_id)
        if not task_info:
            logger.warning(f"Task {task_id} not found")
            return
        logger.info(f"Worker {worker_name} processing task {task_id}")
        # Update task status
        task_info.status = ProcessingStatus.PROCESSING
        task_info.started_at = datetime.now()
        try:
            # Create processor with custom config
            processor_config = {
                "ocr_enabled": task_info.request.ocr_enabled,
                "ocr_language": task_info.request.ocr_language,
                "normalize_whitespace": task_info.request.normalize_whitespace,
                "min_text_length": task_info.request.min_text_length,
            }
            processor = PDFExtractor(config=processor_config)
            # Process the file
            start_time = datetime.now()
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: processor.process(task_info.file_path)
            )
            processing_time = (datetime.now() - start_time).total_seconds()
            # Update task with result
            task_info.result = result
            task_info.status = ProcessingStatus.COMPLETED
            task_info.completed_at = datetime.now()
            task_info.processing_time = processing_time
            task_info.progress = 1.0
            if result.output:
                task_info.total_pages = len(result.output)
            self.total_processed += 1
            logger.info(
                f"Task {task_id} completed successfully in {processing_time:.2f}s"
            )
        except Exception as e:
            # Handle processing error
            task_info.status = ProcessingStatus.FAILED
            task_info.error = str(e)
            task_info.completed_at = datetime.now()
            task_info.progress = 0.0
            self.total_failed += 1
            self.error_handler.handle_error(
                e, {"task_id": task_id, "filename": task_info.filename}
            )
            logger.error(f"Task {task_id} failed: {e}")
        finally:
            # Remove from active tasks
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]


# Global task manager instance
_task_manager: TaskManager | None = None


async def get_task_manager() -> TaskManager:
    """Get the global task manager instance.

    Returns:
        Task manager instance
    """
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
        await _task_manager.start()
    return _task_manager


async def shutdown_task_manager():
    """Shutdown the global task manager."""
    global _task_manager
    if _task_manager:
        await _task_manager.stop()
        _task_manager = None
