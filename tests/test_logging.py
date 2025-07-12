import logging

from src.utils.logging import JSONFormatter, get_audit_logger


def test_get_audit_logger():
    """Test that get_audit_logger returns a logger instance."""
    logger = get_audit_logger()
    assert isinstance(logger, logging.Logger)
    assert logger.name == "audit"


def test_json_formatter():
    """Test that the JSONFormatter formats log records correctly."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=15,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    log_output = formatter.format(record)
    import json

    log_data = json.loads(log_output)
    assert log_data["level"] == "INFO"
    assert log_data["message"] == "Test message"
    assert log_data["logger_name"] == "test_logger"

    try:
        raise ZeroDivisionError()  # noqa: B018
    except ZeroDivisionError:
        record_with_exc = logging.LogRecord(
            name="test_logger_exc",
            level=logging.ERROR,
            pathname=__file__,
            lineno=35,
            msg="Error message",
            args=(),
            exc_info=True,
        )
        # Manually attach exception info
        import sys

        record_with_exc.exc_info = sys.exc_info()
        log_output_with_exc = formatter.format(record_with_exc)
        log_data_with_exc = json.loads(log_output_with_exc)
        assert log_data_with_exc["level"] == "ERROR"
        assert "exception" in log_data_with_exc
