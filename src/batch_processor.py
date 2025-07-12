"""Batch processing module for handling multiple PDFs concurrently."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .process_pdf import PDFProcessor
from .utils.config import get_config
from .utils.performance import PerformanceMonitor

logger = logging.getLogger(__name__)


@dataclass
class BatchJob:
    """Represents a single PDF processing job in a batch."""

    id: str
    input_path: Path
    output_path: Path
    status: str = "pending"  # pending, processing, completed, failed
    start_time: datetime | None = None
    end_time: datetime | None = None
    error: str | None = None
    result: dict[str, Any] | None = None

    @property
    def duration(self) -> float | None:
        """Calculate job duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


@dataclass
class BatchProgress:
    """Tracks progress of a batch processing operation."""

    total_jobs: int
    completed_jobs: int = 0
    failed_jobs: int = 0
    processing_jobs: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None

    @property
    def pending_jobs(self) -> int:
        """Calculate number of pending jobs."""
        return (
            self.total_jobs
            - self.completed_jobs
            - self.failed_jobs
            - self.processing_jobs
        )

    @property
    def completion_rate(self) -> float:
        """Calculate completion rate as percentage."""
        return (
            (self.completed_jobs / self.total_jobs) * 100 if self.total_jobs > 0 else 0
        )

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate as percentage."""
        return (self.failed_jobs / self.total_jobs) * 100 if self.total_jobs > 0 else 0

    @property
    def eta_seconds(self) -> float | None:
        """Estimate time to completion in seconds."""
        if self.completed_jobs == 0:
            return None
        elapsed = (datetime.now() - self.start_time).total_seconds()
        avg_time_per_job = elapsed / self.completed_jobs
        remaining_jobs = self.total_jobs - self.completed_jobs - self.failed_jobs
        return remaining_jobs * avg_time_per_job

    @property
    def is_complete(self) -> bool:
        """Check if batch processing is complete."""
        return self.completed_jobs + self.failed_jobs == self.total_jobs


@dataclass
class BatchStatistics:
    """Comprehensive statistics for batch processing."""

    total_jobs: int
    successful_jobs: int
    failed_jobs: int
    total_duration: float
    average_duration: float
    fastest_job: float
    slowest_job: float
    total_pages_processed: int
    average_pages_per_job: float
    throughput_jobs_per_minute: float
    throughput_pages_per_minute: float
    memory_usage_mb: float
    errors: list[str] = field(default_factory=list)


class BatchProcessor:
    """Handles batch processing of multiple PDF files."""

    def __init__(
        self,
        max_workers: int | None = None,
        progress_callback: Callable[[BatchProgress], None] | None = None,
    ):
        """Initialize batch processor.

        Args:
            max_workers: Maximum number of concurrent workers
            progress_callback: Optional callback for progress updates
        """
        self.config = get_config()
        self.max_workers = (
            max_workers or self.config.performance.parallel["workers"] or os.cpu_count()
        )
        self.progress_callback = progress_callback
        self.performance_monitor = PerformanceMonitor()
        # Batch state
        self.batch_id = str(uuid4())
        self.jobs: list[BatchJob] = []
        self.progress = BatchProgress(0)
        self.resume_file: Path | None = None
        logger.info(f"Initialized batch processor with {self.max_workers} workers")

    def add_directory(
        self,
        input_dir: Path,
        output_dir: Path,
        pattern: str = "*.pdf",
        recursive: bool = True,
    ) -> None:
        """Add all PDF files from a directory to the batch.

        Args:
            input_dir: Directory containing PDF files
            output_dir: Directory for output files
            pattern: File pattern to match (default: "*.pdf")
            recursive: Whether to search subdirectories
        """
        if not input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)
        # Find all matching files
        if recursive:
            pdf_files = list(input_dir.rglob(pattern))
        else:
            pdf_files = list(input_dir.glob(pattern))
        # Create jobs for each file
        for pdf_file in pdf_files:
            relative_path = pdf_file.relative_to(input_dir)
            output_path = output_dir / f"{relative_path.stem}.json"
            # Create output subdirectory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)
            job = BatchJob(
                id=str(uuid4()), input_path=pdf_file, output_path=output_path
            )
            self.jobs.append(job)
        self.progress.total_jobs = len(self.jobs)
        logger.info(f"Added {len(pdf_files)} PDF files to batch from {input_dir}")

    def add_file(self, input_path: Path, output_path: Path) -> None:
        """Add a single PDF file to the batch.

        Args:
            input_path: Path to PDF file
            output_path: Path for output JSON file
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)
        job = BatchJob(id=str(uuid4()), input_path=input_path, output_path=output_path)
        self.jobs.append(job)
        self.progress.total_jobs = len(self.jobs)
        logger.info(f"Added {input_path} to batch")

    def process_batch(self, resume: bool = False) -> BatchStatistics:
        """Process all jobs in the batch concurrently.

        Args:
            resume: Whether to resume from a previous run

        Returns:
            BatchStatistics with processing results
        """
        if not self.jobs:
            raise ValueError("No jobs to process")
        # Setup resume functionality
        if resume and self.resume_file and self.resume_file.exists():
            self._load_resume_state()
        # Filter jobs to process
        jobs_to_process = [
            job for job in self.jobs if job.status in ["pending", "failed"]
        ]
        if not jobs_to_process:
            logger.info("No jobs to process")
            return self._calculate_statistics()
        logger.info(
            f"Processing {len(jobs_to_process)} jobs with {self.max_workers} workers"
        )
        # Start performance monitoring
        operation_id = self.performance_monitor.start_batch_processing()
        # Process jobs concurrently
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all jobs
            future_to_job = {
                executor.submit(self._process_job, job): job for job in jobs_to_process
            }
            # Process completed jobs
            for future in as_completed(future_to_job):
                job = future_to_job[future]
                try:
                    result = future.result()
                    job.result = result
                    job.status = "completed"
                    self.progress.completed_jobs += 1
                    logger.info(f"Job {job.id} completed: {job.input_path}")
                except Exception as e:
                    job.error = str(e)
                    job.status = "failed"
                    self.progress.failed_jobs += 1
                    logger.error(f"Job {job.id} failed: {job.input_path} - {e}")
                finally:
                    if job.status == "processing":
                        self.progress.processing_jobs -= 1
                    # Update progress
                    if self.progress_callback:
                        self.progress_callback(self.progress)
                    # Save resume state
                    if self.resume_file:
                        self._save_resume_state()
        self.progress.end_time = datetime.now()
        # Stop performance monitoring
        self.performance_monitor.stop_batch_processing(operation_id)
        logger.info(
            f"Batch processing completed: {self.progress.completed_jobs} successful, "
            f"{self.progress.failed_jobs} failed"
        )
        return self._calculate_statistics()

    def _process_job(self, job: BatchJob) -> dict[str, Any]:
        """Process a single job.

        Args:
            job: Job to process

        Returns:
            Processing result dictionary
        """
        job.start_time = datetime.now()
        job.status = "processing"
        self.progress.processing_jobs += 1
        try:
            # Process the PDF
            processor = PDFProcessor()
            output_path = processor.process_pdf(job.input_path, job.output_path)
            # Read the result
            with open(output_path, encoding="utf-8") as f:
                result = json.load(f)
            job.end_time = datetime.now()
            return {
                "input_path": str(job.input_path),
                "output_path": str(output_path),
                "duration": job.duration,
                "pages": result.get("page_count", 0),
                "segments": len(result.get("segments", [])),
                "timeline_events": len(result.get("timeline", [])),
            }
        except Exception:
            job.end_time = datetime.now()
            raise

    def _calculate_statistics(self) -> BatchStatistics:
        """Calculate comprehensive batch statistics."""
        successful_jobs = [job for job in self.jobs if job.status == "completed"]
        failed_jobs = [job for job in self.jobs if job.status == "failed"]
        if not successful_jobs:
            # No successful jobs
            return BatchStatistics(
                total_jobs=len(self.jobs),
                successful_jobs=0,
                failed_jobs=len(failed_jobs),
                total_duration=0.0,
                average_duration=0.0,
                fastest_job=0.0,
                slowest_job=0.0,
                total_pages_processed=0,
                average_pages_per_job=0.0,
                throughput_jobs_per_minute=0.0,
                throughput_pages_per_minute=0.0,
                memory_usage_mb=0.0,
                errors=[job.error for job in failed_jobs if job.error],
            )
        # Calculate timing statistics
        durations = [job.duration for job in successful_jobs if job.duration]
        total_duration = sum(durations) if durations else 0.0
        average_duration = total_duration / len(durations) if durations else 0.0
        fastest_job = min(durations) if durations else 0.0
        slowest_job = max(durations) if durations else 0.0
        # Calculate page statistics
        total_pages = sum(
            job.result.get("pages", 0) for job in successful_jobs if job.result
        )
        average_pages = total_pages / len(successful_jobs) if successful_jobs else 0.0
        # Calculate throughput
        batch_duration = (
            self.progress.end_time - self.progress.start_time
        ).total_seconds()
        if batch_duration > 0:
            throughput_jobs = (
                len(successful_jobs) / batch_duration
            ) * 60  # jobs per minute
            throughput_pages = (total_pages / batch_duration) * 60  # pages per minute
        else:
            throughput_jobs = 0.0
            throughput_pages = 0.0
        # Get memory usage
        memory_usage = self.performance_monitor.get_memory_usage()
        return BatchStatistics(
            total_jobs=len(self.jobs),
            successful_jobs=len(successful_jobs),
            failed_jobs=len(failed_jobs),
            total_duration=total_duration,
            average_duration=average_duration,
            fastest_job=fastest_job,
            slowest_job=slowest_job,
            total_pages_processed=total_pages,
            average_pages_per_job=average_pages,
            throughput_jobs_per_minute=throughput_jobs,
            throughput_pages_per_minute=throughput_pages,
            memory_usage_mb=memory_usage,
            errors=[job.error for job in failed_jobs if job.error],
        )

    def set_resume_file(self, resume_file: Path) -> None:
        """Set the resume file for batch processing.

        Args:
            resume_file: Path to resume file
        """
        self.resume_file = resume_file
        self.resume_file.parent.mkdir(parents=True, exist_ok=True)

    def _save_resume_state(self) -> None:
        """Save current batch state for resume functionality."""
        if not self.resume_file:
            return
        state = {
            "batch_id": self.batch_id,
            "jobs": [
                {
                    "id": job.id,
                    "input_path": str(job.input_path),
                    "output_path": str(job.output_path),
                    "status": job.status,
                    "start_time": (
                        job.start_time.isoformat() if job.start_time else None
                    ),
                    "end_time": job.end_time.isoformat() if job.end_time else None,
                    "error": job.error,
                    "result": job.result,
                }
                for job in self.jobs
            ],
            "progress": {
                "total_jobs": self.progress.total_jobs,
                "completed_jobs": self.progress.completed_jobs,
                "failed_jobs": self.progress.failed_jobs,
                "processing_jobs": self.progress.processing_jobs,
                "start_time": self.progress.start_time.isoformat(),
            },
        }
        with open(self.resume_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def _load_resume_state(self) -> None:
        """Load batch state from resume file."""
        if not self.resume_file or not self.resume_file.exists():
            return
        with open(self.resume_file, encoding="utf-8") as f:
            state = json.load(f)
        self.batch_id = state["batch_id"]
        # Restore jobs
        self.jobs = []
        for job_data in state["jobs"]:
            job = BatchJob(
                id=job_data["id"],
                input_path=Path(job_data["input_path"]),
                output_path=Path(job_data["output_path"]),
                status=job_data["status"],
                start_time=(
                    datetime.fromisoformat(job_data["start_time"])
                    if job_data["start_time"]
                    else None
                ),
                end_time=(
                    datetime.fromisoformat(job_data["end_time"])
                    if job_data["end_time"]
                    else None
                ),
                error=job_data["error"],
                result=job_data["result"],
            )
            self.jobs.append(job)
        # Restore progress
        progress_data = state["progress"]
        self.progress = BatchProgress(
            total_jobs=progress_data["total_jobs"],
            completed_jobs=progress_data["completed_jobs"],
            failed_jobs=progress_data["failed_jobs"],
            processing_jobs=0,  # Reset processing jobs
            start_time=datetime.fromisoformat(progress_data["start_time"]),
        )
        logger.info(f"Resumed batch {self.batch_id} with {len(self.jobs)} jobs")

    def get_job_status(self, job_id: str) -> BatchJob | None:
        """Get status of a specific job.

        Args:
            job_id: ID of the job

        Returns:
            BatchJob if found, None otherwise
        """
        for job in self.jobs:
            if job.id == job_id:
                return job
        return None

    def get_failed_jobs(self) -> list[BatchJob]:
        """Get all failed jobs.

        Returns:
            List of failed jobs
        """
        return [job for job in self.jobs if job.status == "failed"]

    def retry_failed_jobs(self) -> BatchStatistics:
        """Retry all failed jobs.

        Returns:
            BatchStatistics with retry results
        """
        failed_jobs = self.get_failed_jobs()
        if not failed_jobs:
            logger.info("No failed jobs to retry")
            return self._calculate_statistics()
        # Reset failed jobs to pending
        for job in failed_jobs:
            job.status = "pending"
            job.error = None
            job.start_time = None
            job.end_time = None
            job.result = None
        # Reset progress counters
        self.progress.failed_jobs = 0
        self.progress.processing_jobs = 0
        logger.info(f"Retrying {len(failed_jobs)} failed jobs")
        return self.process_batch()
