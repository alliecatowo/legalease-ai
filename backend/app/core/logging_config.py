"""
Structured Logging Configuration using structlog

This module provides a simple, drop-in replacement for standard Python logging
with structured logging capabilities via structlog.

Usage:
    # At application startup (FastAPI main.py, Celery worker, etc.):
    from app.core.logging_config import setup_logging
    setup_logging()  # Auto-detects environment from ENV var
    # OR
    setup_logging(env="production")  # Explicit environment

    # In your modules (drop-in replacement):
    from app.core.logging_config import get_logger
    logger = get_logger(__name__)

    # Traditional logging still works:
    logger.info("User logged in")
    logger.error("Database connection failed")

    # Enhanced structured logging with context:
    logger.info("document_processed", document_id="doc_123", duration_ms=342)
    logger.error("upload_failed", document_id="doc_456", error="S3Error", bucket="uploads")

Environment Detection:
    - Checks ENV environment variable (production, development, staging, test)
    - Defaults to "development" if not set
    - Development: Pretty console output with colors
    - Production: JSON output for log aggregation systems

Features:
    - JSON logs in production (for Elasticsearch, CloudWatch, etc.)
    - Pretty colored console in development
    - Preserves standard logging compatibility (gradual migration)
    - Automatic timestamp and log level
    - Exception formatting with stack traces
    - Thread-safe and async-safe
"""

import logging
import sys
import os
from typing import Optional

import structlog


def setup_logging(env: Optional[str] = None) -> None:
    """
    Configure structlog globally for the application.

    This function should be called once at application startup, before any
    logging occurs. It configures both structlog and the standard library
    logging to work together seamlessly.

    Args:
        env: Environment name ("production", "development", "staging", "test").
             If None, reads from ENV environment variable.
             Defaults to "development" if not specified.

    Example:
        >>> setup_logging()  # Auto-detect from ENV
        >>> setup_logging(env="production")  # Force production mode
    """
    # Determine environment
    if env is None:
        env = os.getenv("ENV", "development").lower()
    else:
        env = env.lower()

    # Determine if we're in production mode
    is_production = env in ("production", "prod", "staging")

    # Configure standard library logging
    # This ensures compatibility with existing logging.getLogger() calls
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    # Common processors for all environments
    # These run in order - each transforms the log event
    shared_processors = [
        # Add log level to event dict
        structlog.stdlib.add_log_level,
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Include stack info if available
        structlog.processors.StackInfoRenderer(),
        # Format exceptions with traceback
        structlog.processors.format_exc_info,
        # Unicode handling
        structlog.processors.UnicodeDecoder(),
    ]

    # Production: JSON output for log aggregation
    if is_production:
        processors = shared_processors + [
            # Render as JSON
            structlog.processors.JSONRenderer(),
        ]
    # Development: Pretty console output
    else:
        processors = shared_processors + [
            # Colored, indented console output
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.rich_traceback,
            ),
        ]

    # Configure structlog
    structlog.configure(
        # Processor chain
        processors=processors,
        # Wrapper class - integrates with stdlib logging
        wrapper_class=structlog.stdlib.BoundLogger,
        # Context class - holds log context (thread-safe)
        context_class=dict,
        # Logger factory - creates stdlib loggers under the hood
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Cache logger instances for performance
        cache_logger_on_first_use=True,
    )


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structlog logger instance.

    This is a drop-in replacement for logging.getLogger(__name__).
    The returned logger is compatible with standard logging calls
    but also supports structured logging with key-value pairs.

    Args:
        name: Logger name, typically __name__ of the calling module.
              If None, returns the root logger.

    Returns:
        A structlog BoundLogger instance that works with both:
        - Standard calls: logger.info("message")
        - Structured calls: logger.info("event", key1=value1, key2=value2)

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("server_started", port=8000, workers=4)
        >>> logger.error("connection_failed", host="db.example.com", error="timeout")
    """
    return structlog.get_logger(name)
