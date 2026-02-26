"""Structured logging configuration for production-ready logging."""
import logging
import sys
from typing import Any

from app.config import get_settings


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs JSON-like structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured data."""
        # Base log data
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "event_id"):
            log_data["event_id"] = record.event_id

        # Format as key=value pairs for easy parsing
        pairs = [f"{k}={v}" for k, v in log_data.items()]
        return " ".join(pairs)


def setup_logging() -> None:
    """Configure application logging based on environment."""
    settings = get_settings()

    # Determine log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Create formatter
    if settings.log_format == "json":
        formatter = StructuredFormatter(
            fmt="%(asctime)s",
            datefmt="%Y-%m-%dT%H:%M:%S"
        )
    else:
        # Human-readable format for development
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Log startup message
    logging.info(
        "Logging configured",
        extra={
            "log_level": settings.log_level,
            "log_format": settings.log_format,
        }
    )
