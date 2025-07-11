"""Tests for error handling and recovery mechanisms."""

from __future__ import annotations

import pytest

from src.utils.error_handler import (
    ErrorHandler,
    check_resource_limits,
    error_context,
    get_error_handler,
    graceful_degradation,
    handle_exceptions,
    retry_on_error,
    safe_execute,
    validate_input,
)
from src.utils.exceptions import (
    CriticalError,
    MedicalProcessorError,
    OCRError,
    PDFProcessingError,
    ProcessingTimeoutError,
    ResourceExhaustedError,
    RetryableError,
    ValidationError,
)


class TestCustomExceptions:
    """Tests for custom exception classes."""

    def test_medical_processor_error_base(self):
        """Test base MedicalProcessorError."""
        error = MedicalProcessorError(
            "Test error", error_code="TEST_ERROR", details={"key": "value"}
        )

        assert str(error) == "Test error"
        assert error.error_code == "TEST_ERROR"
        assert error.details == {"key": "value"}

        error_dict = error.to_dict()
        assert error_dict["error_type"] == "MedicalProcessorError"
        assert error_dict["message"] == "Test error"
        assert error_dict["error_code"] == "TEST_ERROR"
        assert error_dict["details"] == {"key": "value"}

    def test_pdf_processing_error(self):
        """Test PDFProcessingError with specific details."""
        error = PDFProcessingError(
            "PDF processing failed", pdf_path="/path/to/file.pdf", page_number=5
        )

        assert error.error_code == "PDF_ERROR"
        assert error.details["pdf_path"] == "/path/to/file.pdf"
        assert error.details["page_number"] == 5

    def test_ocr_error(self):
        """Test OCRError with confidence information."""
        error = OCRError("OCR failed", confidence=0.3, pdf_path="/path/to/file.pdf")

        assert error.error_code == "OCR_ERROR"
        assert error.details["confidence"] == 0.3
        assert error.details["pdf_path"] == "/path/to/file.pdf"

    def test_validation_error(self):
        """Test ValidationError with field information."""
        error = ValidationError(
            "Invalid input", field_name="file_size", field_value="too_large"
        )

        assert error.error_code == "VALIDATION_ERROR"
        assert error.details["field_name"] == "file_size"
        assert error.details["field_value"] == "too_large"

    def test_retryable_error(self):
        """Test RetryableError retry logic."""
        error = RetryableError("Temporary failure", retry_count=1, max_retries=3)

        assert error.can_retry() is True
        assert error.retry_count == 1
        assert error.max_retries == 3

        error.increment_retry()
        assert error.retry_count == 2
        assert error.details["retry_count"] == 2

        # Test when max retries reached
        error.retry_count = 3
        assert error.can_retry() is False


class TestErrorHandler:
    """Tests for ErrorHandler class."""

    def test_error_handler_initialization(self):
        """Test ErrorHandler initialization."""
        handler = ErrorHandler()

        assert handler.error_counts == {}
        assert handler.critical_errors == []

    def test_handle_error_basic(self):
        """Test basic error handling."""
        handler = ErrorHandler()
        error = ValueError("Test error")

        error_info = handler.handle_error(error, {"context": "test"})

        assert error_info["error_type"] == "ValueError"
        assert error_info["message"] == "Test error"
        assert error_info["context"] == {"context": "test"}
        assert "timestamp" in error_info
        assert "traceback" in error_info

        # Check error counts
        assert handler.error_counts["ValueError"] == 1

    def test_handle_medical_processor_error(self):
        """Test handling of MedicalProcessorError."""
        handler = ErrorHandler()
        error = PDFProcessingError("PDF error", pdf_path="/test.pdf")

        error_info = handler.handle_error(error)

        assert error_info["error_code"] == "PDF_ERROR"
        assert error_info["details"]["pdf_path"] == "/test.pdf"

    def test_handle_critical_error(self):
        """Test handling of critical errors."""
        handler = ErrorHandler()
        error = CriticalError("Critical failure")

        error_info = handler.handle_error(error)

        assert len(handler.critical_errors) == 1
        assert handler.critical_errors[0] == error_info

    def test_error_summary(self):
        """Test error summary generation."""
        handler = ErrorHandler()

        # Generate some errors
        handler.handle_error(ValueError("Error 1"))
        handler.handle_error(ValueError("Error 2"))
        handler.handle_error(TypeError("Error 3"))
        handler.handle_error(CriticalError("Critical error"))

        summary = handler.get_error_summary()

        assert summary["total_errors"] == 4
        assert summary["error_counts"]["ValueError"] == 2
        assert summary["error_counts"]["TypeError"] == 1
        assert summary["error_counts"]["CriticalError"] == 1
        assert summary["critical_errors"] == 1
        assert len(summary["critical_error_details"]) == 1

    def test_reset_error_counts(self):
        """Test resetting error counts."""
        handler = ErrorHandler()

        handler.handle_error(ValueError("Error"))
        handler.handle_error(CriticalError("Critical"))

        assert handler.error_counts["ValueError"] == 1
        assert len(handler.critical_errors) == 1

        handler.reset_error_counts()

        assert handler.error_counts == {}
        assert handler.critical_errors == []


class TestRetryDecorator:
    """Tests for retry_on_error decorator."""

    def test_retry_success_on_first_attempt(self):
        """Test successful execution on first attempt."""
        call_count = 0

        @retry_on_error(max_retries=3)
        def test_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_success_after_failures(self):
        """Test successful execution after some failures."""
        call_count = 0

        @retry_on_error(max_retries=3, delay=0.1)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 3

    def test_retry_exhausted(self):
        """Test when all retries are exhausted."""
        call_count = 0

        @retry_on_error(max_retries=2, delay=0.1)
        def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent failure")

        with pytest.raises(RetryableError) as exc_info:
            test_func()

        assert call_count == 3  # Initial + 2 retries
        assert "failed after 2 retries" in str(exc_info.value)

    def test_retry_with_specific_exceptions(self):
        """Test retry with specific exception types."""
        call_count = 0

        @retry_on_error(max_retries=2, exceptions=(ValueError,))
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Retryable")
            elif call_count == 2:
                raise TypeError("Not retryable")
            return "success"

        with pytest.raises(TypeError):
            test_func()

        assert call_count == 2

    def test_retry_with_custom_check(self):
        """Test retry with custom retryable check."""
        call_count = 0

        def is_retryable(error):
            return "can_retry" in str(error).lower()

        @retry_on_error(max_retries=2, retryable_check=is_retryable)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Error can_retry")
            elif call_count == 2:
                raise ValueError("Final error")
            return "success"

        with pytest.raises(ValueError):
            test_func()

        assert call_count == 2


class TestHandleExceptionsDecorator:
    """Tests for handle_exceptions decorator."""

    def test_handle_exceptions_with_default_return(self):
        """Test exception handling with default return value."""

        @handle_exceptions(default_return="fallback", reraise=False)
        def test_func():
            raise ValueError("Test error")

        result = test_func()
        assert result == "fallback"

    def test_handle_exceptions_with_reraise(self):
        """Test exception handling with reraise."""

        @handle_exceptions(default_return="fallback", reraise=True)
        def test_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            test_func()

    def test_handle_exceptions_success(self):
        """Test successful execution with exception handler."""

        @handle_exceptions(default_return="fallback")
        def test_func():
            return "success"

        result = test_func()
        assert result == "success"


class TestErrorContext:
    """Tests for error_context context manager."""

    def test_error_context_success(self):
        """Test error context with successful execution."""
        with error_context("test_operation", param1="value1"):
            result = "success"

        assert result == "success"

    def test_error_context_with_error(self):
        """Test error context with exception."""
        with pytest.raises(ValueError):
            with error_context("test_operation", param1="value1"):
                raise ValueError("Test error")

        # Check that error was handled by global error handler
        handler = get_error_handler()
        assert "ValueError" in handler.error_counts


class TestSafeExecute:
    """Tests for safe_execute function."""

    def test_safe_execute_success(self):
        """Test safe_execute with successful function."""

        def test_func(x, y):
            return x + y

        result = safe_execute(test_func, 2, 3)
        assert result == 5

    def test_safe_execute_with_error(self):
        """Test safe_execute with error and default return."""

        def test_func():
            raise ValueError("Test error")

        result = safe_execute(test_func, default_return="fallback")
        assert result == "fallback"

    def test_safe_execute_with_retries(self):
        """Test safe_execute with retry logic."""
        call_count = 0

        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = safe_execute(test_func, max_retries=2)
        assert result == "success"
        assert call_count == 3


class TestValidateInput:
    """Tests for validate_input function."""

    def test_validate_input_success(self):
        """Test successful input validation."""

        def is_positive(x):
            return x > 0

        # Should not raise
        validate_input(5, is_positive, "Must be positive")

    def test_validate_input_failure(self):
        """Test failed input validation."""

        def is_positive(x):
            return x > 0

        with pytest.raises(ValidationError) as exc_info:
            validate_input(-5, is_positive, "Must be positive", field_name="number")

        assert "Must be positive" in str(exc_info.value)
        assert exc_info.value.details["field_name"] == "number"
        assert exc_info.value.details["field_value"] == "-5"


class TestCheckResourceLimits:
    """Tests for check_resource_limits function."""

    def test_check_memory_limit_success(self):
        """Test memory limit check within bounds."""
        # Should not raise
        check_resource_limits(memory_mb=50)

    def test_check_memory_limit_exceeded(self):
        """Test memory limit exceeded."""
        with pytest.raises(ResourceExhaustedError) as exc_info:
            check_resource_limits(memory_mb=1000)  # Exceeds default 512MB limit

        assert "Memory usage" in str(exc_info.value)
        assert exc_info.value.details["resource_type"] == "memory"

    def test_check_timeout_limit_exceeded(self):
        """Test timeout limit exceeded."""
        with pytest.raises(ProcessingTimeoutError) as exc_info:
            check_resource_limits(timeout_seconds=400)  # Exceeds default 300s limit

        assert "Operation timeout" in str(exc_info.value)
        assert exc_info.value.details["operation"] == "pdf_extraction"


class TestGracefulDegradation:
    """Tests for graceful_degradation function."""

    def test_graceful_degradation_primary_success(self):
        """Test successful primary function execution."""

        def primary_func(x):
            return x * 2

        def fallback_func(x):
            return x * 3

        result = graceful_degradation(primary_func, fallback_func, 5)
        assert result == 10

    def test_graceful_degradation_fallback_success(self):
        """Test fallback function execution after primary fails."""

        def primary_func(x):
            raise ValueError("Primary failed")

        def fallback_func(x):
            return x * 3

        result = graceful_degradation(primary_func, fallback_func, 5)
        assert result == 15

    def test_graceful_degradation_both_fail(self):
        """Test when both primary and fallback fail."""

        def primary_func(x):
            raise ValueError("Primary failed")

        def fallback_func(x):
            raise ValueError("Fallback failed")

        with pytest.raises(CriticalError) as exc_info:
            graceful_degradation(primary_func, fallback_func, 5)

        assert "Both primary" in str(exc_info.value)
        assert "primary_error" in exc_info.value.details
        assert "fallback_error" in exc_info.value.details
