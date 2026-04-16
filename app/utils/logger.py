"""Structured logging configuration with request ID tracking."""

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any, Optional


# Context variable for request ID tracking
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    """Logging filter that injects request_id into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "-"
        return True


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        log_obj: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "asctime",
                "message",
                "request_id",
            }:
                log_obj[key] = value

        return json.dumps(log_obj)


def setup_logging(
    level: int = logging.INFO,
    use_json: bool = False,
    format_string: Optional[str] = None,
) -> None:
    """Configure root logger with request ID support.

    Args:
        level: Logging level (default: INFO).
        use_json: Whether to output structured JSON logs.
        format_string: Custom format string (overrides JSON mode).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Apply filter for request ID
    handler.addFilter(RequestIdFilter())

    # Set formatter
    if format_string:
        formatter = logging.Formatter(format_string)
    elif use_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(request_id)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)


def set_request_id(request_id: Optional[str] = None) -> str:
    """Set the request ID for the current context.

    Args:
        request_id: Request ID to set. If None, generates a new UUID.

    Returns:
        The request ID that was set.
    """
    if request_id is None:
        request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    return request_id


def get_request_id() -> Optional[str]:
    """Get the current request ID from context.

    Returns:
        Current request ID or None if not set.
    """
    return request_id_var.get()


def clear_request_id() -> None:
    """Clear the request ID from the current context."""
    request_id_var.set(None)


class RequestIdMiddleware:
    """Middleware/decorator for automatic request ID management."""

    def __init__(self, generate_for_missing: bool = True):
        """Initialize middleware.

        Args:
            generate_for_missing: Auto-generate request ID if not provided.
        """
        self.generate_for_missing = generate_for_missing

    async def __call__(self, request_id: Optional[str] = None) -> "RequestIdContext":
        """Enter request ID context.

        Args:
            request_id: Request ID to use. If None and generate_for_missing is True,
                       a new UUID will be generated.

        Returns:
            RequestIdContext manager.
        """
        return RequestIdContext(request_id, self.generate_for_missing)


class RequestIdContext:
    """Async context manager for request ID scoping."""

    def __init__(
        self,
        request_id: Optional[str] = None,
        auto_generate: bool = True,
    ):
        self.request_id = request_id
        self.auto_generate = auto_generate
        self._token: Optional[Any] = None

    async def __aenter__(self) -> str:
        """Enter context and set request ID.

        Returns:
            The active request ID.
        """
        if self.request_id is None and self.auto_generate:
            self.request_id = str(uuid.uuid4())
        self._token = request_id_var.set(self.request_id)
        return self.request_id  # type: ignore

    async def __aexit__(self, *args: Any) -> None:
        """Exit context and clear request ID."""
        if self._token is not None:
            request_id_var.reset(self._token)
