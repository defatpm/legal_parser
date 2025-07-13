"""Pydantic models for the REST API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProcessingStatus(str, Enum):
    """Status of a processing request."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingRequest(BaseModel):
    """Request model for document processing."""

    ocr_enabled: bool = Field(
        True, description="Enable OCR processing for scanned documents"
    )
    ocr_language: str = Field("eng", description="OCR language code")
    normalize_whitespace: bool = Field(
        True, description="Normalize whitespace in extracted text"
    )
    min_text_length: int = Field(10, description="Minimum text length per page")
    output_format: str = Field("json", description="Output format (json, csv, excel)")
    include_metadata: bool = Field(True, description="Include processing metadata")

    @field_validator("ocr_language")
    @classmethod
    def validate_ocr_language(cls, v):
        """Validate OCR language code."""
        valid_languages = [
            "eng",
            "spa",
            "fra",
            "deu",
            "ita",
            "por",
            "rus",
            "jpn",
            "chi_sim",
            "chi_tra",
        ]
        if v not in valid_languages:
            raise ValueError(f"Invalid OCR language. Must be one of: {valid_languages}")
        return v

    @field_validator("output_format")
    @classmethod
    def validate_output_format(cls, v):
        """Validate output format."""
        valid_formats = ["json", "csv", "excel"]
        if v not in valid_formats:
            raise ValueError(f"Invalid output format. Must be one of: {valid_formats}")
        return v


class ProcessingResponse(BaseModel):
    """Response model for processing requests."""

    task_id: str = Field(..., description="Unique task identifier")
    status: ProcessingStatus = Field(..., description="Current processing status")
    message: str = Field(..., description="Status message")
    created_at: datetime = Field(..., description="Task creation timestamp")

    model_config = ConfigDict(use_enum_values=True)


class ProcessingResult(BaseModel):
    """Model for processing results."""

    task_id: str = Field(..., description="Task identifier")
    status: ProcessingStatus = Field(..., description="Processing status")
    filename: str = Field(..., description="Original filename")
    pages_processed: int = Field(..., description="Number of pages processed")
    ocr_pages: int = Field(0, description="Number of pages that used OCR")
    processing_time: float = Field(..., description="Processing time in seconds")
    file_size_mb: float = Field(..., description="File size in MB")
    created_at: datetime = Field(..., description="Task creation timestamp")
    completed_at: datetime | None = Field(None, description="Task completion timestamp")
    error_message: str | None = Field(None, description="Error message if failed")

    model_config = ConfigDict(use_enum_values=True)


class PageContent(BaseModel):
    """Model for page content."""

    page_number: int = Field(..., description="Page number")
    text: str = Field(..., description="Extracted text")
    word_count: int = Field(..., description="Number of words")
    character_count: int = Field(..., description="Number of characters")
    is_ocr_applied: bool = Field(False, description="Whether OCR was applied")


class DocumentContent(BaseModel):
    """Model for complete document content."""

    task_id: str = Field(..., description="Task identifier")
    filename: str = Field(..., description="Original filename")
    total_pages: int = Field(..., description="Total number of pages")
    pages: list[PageContent] = Field(..., description="Page contents")
    processing_metadata: dict[str, Any] = Field(..., description="Processing metadata")


class ProcessingStats(BaseModel):
    """Model for processing statistics."""

    total_requests: int = Field(..., description="Total number of requests")
    completed_requests: int = Field(..., description="Number of completed requests")
    failed_requests: int = Field(..., description="Number of failed requests")
    average_processing_time: float = Field(
        ..., description="Average processing time in seconds"
    )
    average_file_size_mb: float = Field(..., description="Average file size in MB")
    average_pages_per_document: float = Field(
        ..., description="Average pages per document"
    )
    total_pages_processed: int = Field(..., description="Total pages processed")
    total_ocr_pages: int = Field(..., description="Total OCR pages processed")


class ErrorResponse(BaseModel):
    """Model for error responses."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: dict[str, Any] | None = Field(None, description="Additional error details")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Error timestamp"
    )


class HealthResponse(BaseModel):
    """Model for health check responses."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    uptime: float = Field(..., description="Uptime in seconds")
    memory_usage_mb: float = Field(..., description="Memory usage in MB")
    active_tasks: int = Field(..., description="Number of active tasks")
    total_processed: int = Field(..., description="Total documents processed")


class ProcessorInfo(BaseModel):
    """Model for processor information."""

    name: str = Field(..., description="Processor name")
    version: str = Field(..., description="Processor version")
    description: str = Field(..., description="Processor description")
    input_types: list[str] = Field(..., description="Supported input types")
    output_types: list[str] = Field(..., description="Supported output types")
    capabilities: list[str] = Field(..., description="Processor capabilities")
    dependencies: list[str] = Field(..., description="Required dependencies")


class BatchProcessingRequest(BaseModel):
    """Request model for batch processing."""

    files: list[str] = Field(..., description="List of file paths or URLs")
    processing_options: ProcessingRequest = Field(..., description="Processing options")
    max_concurrent: int = Field(4, description="Maximum concurrent processing tasks")

    @field_validator("max_concurrent")
    @classmethod
    def validate_max_concurrent(cls, v):
        """Validate maximum concurrent tasks."""
        if v < 1 or v > 10:
            raise ValueError("max_concurrent must be between 1 and 10")
        return v


class BatchProcessingResponse(BaseModel):
    """Response model for batch processing."""

    batch_id: str = Field(..., description="Unique batch identifier")
    total_files: int = Field(..., description="Total number of files in batch")
    status: ProcessingStatus = Field(..., description="Batch processing status")
    progress: float = Field(0.0, description="Processing progress (0.0 to 1.0)")
    completed_files: int = Field(0, description="Number of completed files")
    failed_files: int = Field(0, description="Number of failed files")
    created_at: datetime = Field(..., description="Batch creation timestamp")
    estimated_completion: datetime | None = Field(
        None, description="Estimated completion time"
    )

    model_config = ConfigDict(use_enum_values=True)


class ConfigurationModel(BaseModel):
    """Model for configuration settings."""

    max_file_size_mb: int = Field(100, description="Maximum file size in MB")
    max_pages_per_document: int = Field(1000, description="Maximum pages per document")
    ocr_enabled: bool = Field(True, description="Enable OCR processing")
    ocr_languages: list[str] = Field(["eng"], description="Supported OCR languages")
    supported_formats: list[str] = Field(["pdf"], description="Supported file formats")
    rate_limit_per_minute: int = Field(60, description="Rate limit per minute")
    max_concurrent_tasks: int = Field(
        10, description="Maximum concurrent processing tasks"
    )


class SystemMetrics(BaseModel):
    """Model for system metrics."""

    cpu_usage_percent: float = Field(..., description="CPU usage percentage")
    memory_usage_mb: float = Field(..., description="Memory usage in MB")
    memory_available_mb: float = Field(..., description="Available memory in MB")
    disk_usage_percent: float = Field(..., description="Disk usage percentage")
    active_connections: int = Field(..., description="Number of active connections")
    queue_size: int = Field(..., description="Processing queue size")
    uptime_seconds: float = Field(..., description="System uptime in seconds")


class TaskStatusUpdate(BaseModel):
    """Model for task status updates."""

    task_id: str = Field(..., description="Task identifier")
    status: ProcessingStatus = Field(..., description="Updated status")
    progress: float = Field(0.0, description="Progress percentage (0.0 to 1.0)")
    message: str = Field("", description="Status message")
    current_page: int | None = Field(None, description="Current page being processed")
    total_pages: int | None = Field(None, description="Total pages in document")
    estimated_completion: datetime | None = Field(
        None, description="Estimated completion time"
    )

    model_config = ConfigDict(use_enum_values=True)


class BatchRequest(BaseModel):
    """Simple batch request model for compatibility."""

    max_workers: int = Field(4, description="Maximum number of worker threads")
    output_format: str = Field("json", description="Output format (json, csv, excel)")

    @field_validator("max_workers")
    @classmethod
    def validate_max_workers(cls, v):
        """Validate maximum workers."""
        if v < 1 or v > 10:
            raise ValueError("max_workers must be between 1 and 10")
        return v


class APIVersion(BaseModel):
    """Model for API version information."""

    version: str = Field(..., description="API version")
    build_date: str = Field(..., description="Build date")
    git_commit: str | None = Field(None, description="Git commit hash")
    features: list[str] = Field(..., description="Available features")
    endpoints: dict[str, str] = Field(..., description="Available endpoints")


class FileUploadResponse(BaseModel):
    """Response model for file uploads."""

    filename: str = Field(..., description="Uploaded filename")
    size_bytes: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="File content type")
    upload_id: str = Field(..., description="Upload identifier")
    expires_at: datetime = Field(..., description="Upload expiration time")


class ProcessingQueue(BaseModel):
    """Model for processing queue status."""

    queue_size: int = Field(..., description="Number of tasks in queue")
    processing_tasks: int = Field(
        ..., description="Number of tasks currently processing"
    )
    completed_today: int = Field(..., description="Number of tasks completed today")
    average_wait_time: float = Field(..., description="Average wait time in seconds")
    estimated_processing_time: float = Field(
        ..., description="Estimated processing time in seconds"
    )
    active_workers: int = Field(..., description="Number of active workers")
    max_workers: int = Field(..., description="Maximum number of workers")


# Utility functions for model conversion
def convert_page_content(page_content) -> PageContent:
    """Convert internal PageContent to API model."""
    return PageContent(
        page_number=page_content.page_number,
        text=page_content.raw_text,
        word_count=len(page_content.raw_text.split()),
        character_count=len(page_content.raw_text),
        is_ocr_applied=page_content.is_ocr_applied,
    )


def convert_processing_result(result, task_id: str, filename: str) -> ProcessingResult:
    """Convert internal processing result to API model."""
    return ProcessingResult(
        task_id=task_id,
        status=(
            ProcessingStatus.COMPLETED
            if result.status.value == "completed"
            else ProcessingStatus.FAILED
        ),
        filename=filename,
        pages_processed=len(result.output) if result.output else 0,
        ocr_pages=(
            sum(1 for page in result.output if page.is_ocr_applied)
            if result.output
            else 0
        ),
        processing_time=result.processing_time or 0.0,
        file_size_mb=result.metadata.get("file_size_mb", 0.0),
        created_at=datetime.now(),
        completed_at=datetime.now(),
        error_message=str(result.error) if result.error else None,
    )


def convert_document_content(result, task_id: str, filename: str) -> DocumentContent:
    """Convert internal result to document content model."""
    pages = (
        [convert_page_content(page) for page in result.output] if result.output else []
    )
    return DocumentContent(
        task_id=task_id,
        filename=filename,
        total_pages=len(pages),
        pages=pages,
        processing_metadata=result.metadata,
    )
