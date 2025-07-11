"""Error handling utilities with retry mechanisms and graceful degradation."""

from __future__ import annotations

import logging
import time
import traceback
from collections.abc import Callable
from contextlib import contextmanager
from functools import wraps
from typing import Any, TypeVar

from .config import get_config
from .exceptions import (
    CriticalError,
    MedicalProcessorError,
    ProcessingTimeoutError,
    ResourceExhaustedError,
    RetryableError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorHandler:
    """Centralized error handling with retry logic and graceful degradation."""

    def __init__(self):
        """Initialize error handler with configuration."""
        self.config = get_config()
        self.error_counts: dict[str, int] = {}
        self.critical_errors: list[dict[str, Any]] = []

    def handle_error(
        self, error: Exception, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle an error with appropriate logging and categorization.

        Args:
            error: The exception that occurred
            context: Additional context about the error

        Returns:
            Dictionary containing error information
        """
        context = context or {}
        # Create error info
        error_info = {
            "error_type": error.__class__.__name__,
            "message": str(error),
            "context": context,
            "timestamp": time.time(),
            "traceback": traceback.format_exc(),
        }
        # Add processor-specific details if available
        if isinstance(error, MedicalProcessorError):
            error_dict = error.to_dict()
            # Merge without overwriting existing keys
            for key, value in error_dict.items():
                if key not in error_info:
                    error_info[key] = value
        # Create a clean extra dict for logging (avoid key conflicts)
        log_extra = {
            k: v for k, v in error_info.items() if k not in ["message", "asctime"]
        }
        # Log error based on severity
        if isinstance(error, CriticalError):
            logger.critical(f"Critical error occurred: {error}", extra=log_extra)
            self.critical_errors.append(error_info)
        elif isinstance(error, ProcessingTimeoutError | ResourceExhaustedError):
            logger.error(f"Resource error occurred: {error}", extra=log_extra)
        elif isinstance(error, RetryableError):
            logger.warning(f"Retryable error occurred: {error}", extra=log_extra)
        else:
            logger.error(f"Error occurred: {error}", extra=log_extra)
        # Update error counts
        error_type = error.__class__.__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        return error_info

    def get_error_summary(self) -> dict[str, Any]:
        """Get summary of all errors encountered.

        Returns:
            Dictionary containing error statistics
        """
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_counts": self.error_counts.copy(),
            "critical_errors": len(self.critical_errors),
            "critical_error_details": self.critical_errors.copy(),
        }

    def reset_error_counts(self) -> None:
        """Reset error counters."""
        self.error_counts.clear()
        self.critical_errors.clear()


# Global error handler instance
_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance.

    Returns:
        Global error handler
    """
    return _error_handler


def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    retryable_check: Callable[[Exception], bool] | None = None,
) -> Callable:
    """Decorator for retrying functions on specific exceptions.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for delay
        exceptions: Tuple of exceptions to catch and retry on
        retryable_check: Optional function to check if exception is retryable

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            current_delay = delay
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    # Check if this is a retryable error
                    if retryable_check and not retryable_check(e):
                        logger.warning(f"Non-retryable error in {func.__name__}: {e}")
                        raise
                    # Don't retry on the last attempt
                    if attempt == max_retries:
                        break
                    # Log retry attempt
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )
                    # Wait before retry
                    time.sleep(current_delay)
                    current_delay *= backoff
            # All retries exhausted
            logger.error(f"All {max_retries} retries exhausted for {func.__name__}")
            if isinstance(last_exception, MedicalProcessorError):
                raise last_exception
            else:
                raise RetryableError(
                    f"Function {func.__name__} failed after {max_retries} retries: {last_exception}",
                    retry_count=max_retries,
                    max_retries=max_retries,
                ) from last_exception

        return wrapper

    return decorator


def handle_exceptions(
    default_return: Any | None = None,
    exceptions: tuple = (Exception,),
    log_level: str = "ERROR",
    reraise: bool = True,
) -> Callable:
    """Decorator for handling exceptions with optional default return.

    Args:
        default_return: Default value to return if exception occurs
        exceptions: Tuple of exceptions to catch
        log_level: Log level for caught exceptions
        reraise: Whether to reraise the exception after handling

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T | Any]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T | Any:
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                error_handler = get_error_handler()
                context = {
                    "function": func.__name__,
                    "args": str(args)[:100] if args else None,
                    "kwargs": str(kwargs)[:100] if kwargs else None,
                }
                error_info = error_handler.handle_error(e, context)
                # Log at specified level (clean extra dict)
                log_extra = {
                    k: v
                    for k, v in error_info.items()
                    if k not in ["message", "asctime"]
                }
                log_func = getattr(logger, log_level.lower())
                log_func(f"Exception in {func.__name__}: {e}", extra=log_extra)
                if reraise:
                    raise
                else:
                    return default_return

        return wrapper

    return decorator


@contextmanager
def error_context(operation: str, **context):
    """Context manager for handling errors with additional context.

    Args:
        operation: Name of the operation being performed
        **context: Additional context information

    Yields:
        Error handler instance
    """
    error_handler = get_error_handler()
    try:
        yield error_handler
    except Exception as e:
        error_context_info = {"operation": operation, **context}
        error_handler.handle_error(e, error_context_info)
        raise


def safe_execute[T](
    func: Callable[..., T],
    *args,
    default_return: Any | None = None,
    max_retries: int = 0,
    **kwargs,
) -> T | Any:
    """Safely execute a function with error handling and optional retries.

    Args:
        func: Function to execute
        *args: Arguments to pass to function
        default_return: Default value to return on error
        max_retries: Maximum number of retries
        **kwargs: Keyword arguments to pass to function

    Returns:
        Function result or default_return on error
    """
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_handler = get_error_handler()
            context = {
                "function": func.__name__,
                "attempt": attempt + 1,
                "max_retries": max_retries,
            }
            error_handler.handle_error(e, context)
            if attempt < max_retries:
                logger.info(
                    f"Retrying {func.__name__} (attempt {attempt + 2}/{max_retries + 1})"
                )
                time.sleep(1.0)  # Simple delay between retries
            else:
                logger.error(
                    f"Failed to execute {func.__name__} after {max_retries + 1} attempts"
                )
                break
    return default_return


def validate_input(
    value: Any,
    validator: Callable[[Any], bool],
    error_message: str,
    field_name: str | None = None,
) -> None:
    """Validate input value with custom validator.

    Args:
        value: Value to validate
        validator: Function that returns True if value is valid
        error_message: Error message to raise if validation fails
        field_name: Optional field name for error context

    Raises:
        ValidationError: If validation fails
    """
    from .exceptions import ValidationError

    if not validator(value):
        raise ValidationError(
            error_message,
            field_name=field_name,
            field_value=str(value)[:100] if value else None,
        )


def check_resource_limits(
    memory_mb: float | None = None,
    disk_space_mb: float | None = None,
    timeout_seconds: float | None = None,
) -> None:
    """Check resource limits and raise appropriate errors.

    Args:
        memory_mb: Memory usage in MB
        disk_space_mb: Disk space usage in MB
        timeout_seconds: Time elapsed in seconds

    Raises:
        ResourceExhaustedError: If resource limits are exceeded
        ProcessingTimeoutError: If timeout is exceeded
    """
    config = get_config()
    # Check memory limit
    if memory_mb is not None:
        memory_limit = config.processing.memory["max_memory_per_doc_mb"]
        if memory_mb > memory_limit:
            raise ResourceExhaustedError(
                f"Memory usage ({memory_mb:.1f}MB) exceeds limit ({memory_limit}MB)",
                resource_type="memory",
                limit=memory_limit,
            )
    # Check timeout
    if timeout_seconds is not None:
        # Check against various timeout configurations
        for operation, limit in config.processing.timeout.items():
            if timeout_seconds > limit:
                raise ProcessingTimeoutError(
                    f"Operation timeout ({timeout_seconds:.1f}s) exceeds limit ({limit}s)",
                    timeout_seconds=int(timeout_seconds),
                    operation=operation,
                )


def graceful_degradation(
    primary_func: Callable[..., T], fallback_func: Callable[..., T], *args, **kwargs
) -> T:
    """Execute primary function with fallback on error.

    Args:
        primary_func: Primary function to try first
        fallback_func: Fallback function to try if primary fails
        *args: Arguments to pass to both functions
        **kwargs: Keyword arguments to pass to both functions

    Returns:
        Result from primary or fallback function

    Raises:
        Exception: If both primary and fallback functions fail
    """
    try:
        return primary_func(*args, **kwargs)
    except Exception as e:
        logger.warning(f"Primary function {primary_func.__name__} failed: {e}")
        logger.info(f"Trying fallback function {fallback_func.__name__}")
        try:
            return fallback_func(*args, **kwargs)
        except Exception as fallback_error:
            logger.error(
                f"Fallback function {fallback_func.__name__} also failed: {fallback_error}"
            )
            raise CriticalError(
                f"Both primary ({primary_func.__name__}) and fallback ({fallback_func.__name__}) functions failed",
                details={
                    "primary_error": str(e),
                    "fallback_error": str(fallback_error),
                },
            ) from fallback_error
