"""Error handling utilities for the medical record processor."""

import functools
import logging
import time
import traceback
from collections.abc import Callable
from typing import Any, TypeVar

from .exceptions import (
    CriticalError,
    MedicalProcessorError,
    ResourceExhaustedError,
    RetryableError,
)
from .logging import get_audit_logger

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()

T = TypeVar("T")


class ErrorHandler:
    """Centralized error handler for the application."""

    def __init__(self) -> None:
        self.error_counts: dict[str, int] = {}
        self.critical_errors: list[dict[str, Any]] = []
        self.max_retries: int = 3

    def handle_error(
        self,
        error: Exception,
        context: dict[str, Any] | None = None,
        raise_on_exceed: bool = True,
    ) -> dict[str, Any]:
        """Handle and log errors appropriately."""
        error_type = type(error).__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

        error_info = {
            "error_type": error_type,
            "error_message": str(error),
            "context": context,
            "timestamp": time.time(),
            "traceback": traceback.format_exc(),
        }

        if isinstance(error, MedicalProcessorError):
            error_dict = error.to_dict()
            error_dict.pop("message", None)
            error_info.update(error_dict)

        logger.error(
            f"Error occurred: {str(error)}",
            exc_info=True,
            extra={"context": context},
        )

        audit_logger.error(
            "Processing error",
            extra=error_info,
        )

        if isinstance(error, CriticalError):
            self.critical_errors.append(error_info)

        if raise_on_exceed and self.error_counts.get(error_type, 0) > self.max_retries:
            raise CriticalError(f"Exceeded max retries for {error_type}")

        return error_info

    def get_error_summary(self) -> dict[str, Any]:
        """Get summary of error counts."""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_counts": self.error_counts.copy(),
            "critical_errors": len(self.critical_errors),
            "critical_error_details": self.critical_errors.copy(),
        }

    def reset_error_counts(self) -> None:
        """Reset error counts."""
        self.error_counts.clear()
        self.critical_errors.clear()


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _error_handler
    if not _error_handler:
        _error_handler = ErrorHandler()
    return _error_handler


_error_handler: ErrorHandler | None = None


def retry_on_error(
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    retryable_exceptions: tuple = (RetryableError,),
) -> Callable:
    """Decorator for retrying on errors."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        if isinstance(e, RetryableError) and not e.can_retry():
                            raise
                        if isinstance(e, RetryableError):
                            e.increment_retry()

                        sleep_time = backoff_factor * (2**attempt)
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} after {sleep_time:.2f}s due to {type(e).__name__}"
                        )
                        time.sleep(sleep_time)

            raise MedicalProcessorError(
                f"Max retries {max_retries} exceeded"
            ) from last_exception

        return wrapper

    return decorator


def handle_exceptions(
    default_return: Any = None,
    raise_critical: bool = False,
) -> Callable:
    """Decorator for handling exceptions gracefully."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except MedicalProcessorError as e:
                get_error_handler().handle_error(e, {"function": func.__name__})
                if raise_critical:
                    raise
                return default_return
            except Exception as e:
                get_error_handler().handle_error(e, {"function": func.__name__})
                if raise_critical:
                    raise CriticalError(str(e)) from e
                return default_return

        return wrapper

    return decorator


class error_context:
    """Context manager for error handling with additional context."""

    def __init__(self, context: dict[str, Any]) -> None:
        self.context = context

    def __enter__(self) -> None:
        pass

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        if exc_value:
            get_error_handler().handle_error(exc_value, self.context)
            return False  # Re-raise the exception
        return True


def safe_execute(  # noqa: UP047
    func: Callable[..., T],
    *args,
    default_return: Any | None = None,
    max_retries: int = 0,
    **kwargs,
) -> T | Any:
    """Safely execute a function with optional retries."""
    error_handler = get_error_handler()
    retries = 0

    while True:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if isinstance(e, CriticalError):
                raise

            error_handler.handle_error(e, raise_on_exceed=False)
            if isinstance(e, RetryableError) and retries < max_retries:
                retries += 1
                time.sleep(1 * retries)  # Exponential backoff
                continue
            if default_return is not None:
                return default_return
            raise


def validate_input(validator: Callable) -> Callable:
    """Decorator for input validation."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            validator(*args, **kwargs)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def check_resource_limits(
    memory_threshold: float = 0.8,
    cpu_threshold: float = 0.9,
) -> None:
    """Check system resource limits."""
    import psutil

    memory = psutil.virtual_memory().percent / 100
    cpu = psutil.cpu_percent() / 100

    if memory > memory_threshold:
        raise ResourceExhaustedError(
            f"Memory usage {memory*100:.1f}% exceeds threshold",
            resource_type="memory",
            limit=memory_threshold,
        )
    if cpu > cpu_threshold:
        raise ResourceExhaustedError(
            f"CPU usage {cpu*100:.1f}% exceeds threshold",
            resource_type="cpu",
            limit=cpu_threshold,
        )


def graceful_degradation(fallback_func: Callable) -> Callable:
    """Decorator for graceful degradation."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Graceful degradation: {str(e)}")
                return fallback_func(*args, **kwargs)

        return wrapper

    return decorator
