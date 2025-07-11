"""Custom exceptions for the medical record processor."""
from __future__ import annotations

from typing import Any


class MedicalProcessorError(Exception):
    """Base exception for medical record processor errors."""

    def __init__(self, message: str, error_code: str | None = None, details: dict[str, Any] | None = None):
        """Initialize processor error.

        Args:
            message: Error message
            error_code: Optional error code for categorization
            details: Optional additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging/serialization.

        Returns:
            Dictionary representation of the exception
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


class ConfigurationError(MedicalProcessorError):
    """Configuration-related errors."""

    def __init__(self, message: str, config_path: str | None = None, **kwargs):
        """Initialize configuration error.

        Args:
            message: Error message
            config_path: Path to configuration file that caused the error
            **kwargs: Additional keyword arguments
        """
        super().__init__(message, error_code="CONFIG_ERROR", **kwargs)
        if config_path:
            self.details["config_path"] = config_path


class PDFProcessingError(MedicalProcessorError):
    """PDF processing-related errors."""

    def __init__(self, message: str, pdf_path: str | None = None, page_number: int | None = None, **kwargs):
        """Initialize PDF processing error.

        Args:
            message: Error message
            pdf_path: Path to PDF file that caused the error
            page_number: Page number where error occurred
            **kwargs: Additional keyword arguments
        """
        super().__init__(message, error_code="PDF_ERROR", **kwargs)
        if pdf_path:
            self.details["pdf_path"] = pdf_path
        if page_number:
            self.details["page_number"] = page_number


class OCRError(PDFProcessingError):
    """OCR-specific errors."""

    def __init__(self, message: str, confidence: float | None = None, **kwargs):
        """Initialize OCR error.

        Args:
            message: Error message
            confidence: OCR confidence score if available
            **kwargs: Additional keyword arguments
        """
        # Remove error_code from kwargs to avoid duplicate
        kwargs.pop('error_code', None)
        super().__init__(message, **kwargs)
        self.error_code = "OCR_ERROR"
        if confidence is not None:
            self.details["confidence"] = confidence


class SegmentationError(MedicalProcessorError):
    """Document segmentation errors."""

    def __init__(self, message: str, segment_count: int | None = None, **kwargs):
        """Initialize segmentation error.

        Args:
            message: Error message
            segment_count: Number of segments processed when error occurred
            **kwargs: Additional keyword arguments
        """
        super().__init__(message, error_code="SEGMENTATION_ERROR", **kwargs)
        if segment_count is not None:
            self.details["segment_count"] = segment_count


class MetadataExtractionError(MedicalProcessorError):
    """Metadata extraction errors."""

    def __init__(self, message: str, entity_type: str | None = None, **kwargs):
        """Initialize metadata extraction error.

        Args:
            message: Error message
            entity_type: Type of entity being extracted when error occurred
            **kwargs: Additional keyword arguments
        """
        super().__init__(message, error_code="METADATA_ERROR", **kwargs)
        if entity_type:
            self.details["entity_type"] = entity_type


class TimelineError(MedicalProcessorError):
    """Timeline building errors."""

    def __init__(self, message: str, event_count: int | None = None, **kwargs):
        """Initialize timeline error.

        Args:
            message: Error message
            event_count: Number of events processed when error occurred
            **kwargs: Additional keyword arguments
        """
        super().__init__(message, error_code="TIMELINE_ERROR", **kwargs)
        if event_count is not None:
            self.details["event_count"] = event_count


class ValidationError(MedicalProcessorError):
    """Input validation errors."""

    def __init__(self, message: str, field_name: str | None = None, field_value: str | None = None, **kwargs):
        """Initialize validation error.

        Args:
            message: Error message
            field_name: Name of field that failed validation
            field_value: Value that failed validation
            **kwargs: Additional keyword arguments
        """
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)
        if field_name:
            self.details["field_name"] = field_name
        if field_value:
            self.details["field_value"] = field_value


class FileSystemError(MedicalProcessorError):
    """File system operation errors."""

    def __init__(self, message: str, file_path: str | None = None, operation: str | None = None, **kwargs):
        """Initialize file system error.

        Args:
            message: Error message
            file_path: Path to file that caused the error
            operation: File operation that failed (read, write, delete, etc.)
            **kwargs: Additional keyword arguments
        """
        super().__init__(message, error_code="FILESYSTEM_ERROR", **kwargs)
        if file_path:
            self.details["file_path"] = file_path
        if operation:
            self.details["operation"] = operation


class ProcessingTimeoutError(MedicalProcessorError):
    """Processing timeout errors."""

    def __init__(self, message: str, timeout_seconds: int | None = None, operation: str | None = None, **kwargs):
        """Initialize timeout error.

        Args:
            message: Error message
            timeout_seconds: Timeout duration in seconds
            operation: Operation that timed out
            **kwargs: Additional keyword arguments
        """
        super().__init__(message, error_code="TIMEOUT_ERROR", **kwargs)
        if timeout_seconds is not None:
            self.details["timeout_seconds"] = timeout_seconds
        if operation:
            self.details["operation"] = operation


class ResourceExhaustedError(MedicalProcessorError):
    """Resource exhaustion errors (memory, disk space, etc.)."""

    def __init__(self, message: str, resource_type: str | None = None, limit: float | None = None, **kwargs):
        """Initialize resource exhaustion error.

        Args:
            message: Error message
            resource_type: Type of resource that was exhausted (memory, disk, etc.)
            limit: Resource limit that was exceeded
            **kwargs: Additional keyword arguments
        """
        super().__init__(message, error_code="RESOURCE_ERROR", **kwargs)
        if resource_type:
            self.details["resource_type"] = resource_type
        if limit is not None:
            self.details["limit"] = limit


class RetryableError(MedicalProcessorError):
    """Errors that can be retried."""

    def __init__(self, message: str, retry_count: int = 0, max_retries: int = 3, **kwargs):
        """Initialize retryable error.

        Args:
            message: Error message
            retry_count: Current retry attempt
            max_retries: Maximum number of retries allowed
            **kwargs: Additional keyword arguments
        """
        super().__init__(message, error_code="RETRYABLE_ERROR", **kwargs)
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.details["retry_count"] = retry_count
        self.details["max_retries"] = max_retries

    def can_retry(self) -> bool:
        """Check if this error can be retried.

        Returns:
            True if retry is possible, False otherwise
        """
        return self.retry_count < self.max_retries

    def increment_retry(self) -> None:
        """Increment retry count."""
        self.retry_count += 1
        self.details["retry_count"] = self.retry_count


class CriticalError(MedicalProcessorError):
    """Critical errors that require immediate attention."""

    def __init__(self, message: str, **kwargs):
        """Initialize critical error.

        Args:
            message: Error message
            **kwargs: Additional keyword arguments
        """
        super().__init__(message, error_code="CRITICAL_ERROR", **kwargs)
