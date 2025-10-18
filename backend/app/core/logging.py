"""Logging configuration for the application."""

import logging
import sys
from typing import Optional

from app.core.config import settings


def setup_logging(
    level: Optional[str] = None,
    format_string: Optional[str] = None,
) -> None:
    """Configure application-wide logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Defaults to settings.LOG_LEVEL if available, otherwise INFO.
        format_string: Custom format string for log messages.
                      Defaults to a structured format with timestamp, logger name, level, and message.
    """
    log_level = level or getattr(settings, "LOG_LEVEL", "INFO")

    # Default format: timestamp - logger name - level - message
    default_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_format = format_string or default_format

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
    )

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("authlib").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name.

    Args:
        name: The name for the logger (typically __name__ from the calling module).

    Returns:
        A configured logger instance.
    """
    return logging.getLogger(name)
