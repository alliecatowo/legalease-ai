"""Database session utilities for managing database connections.

This module provides utilities to eliminate database session pattern duplication
across the application, particularly in background workers and async tasks.
"""

from contextlib import contextmanager
from functools import wraps
from typing import Generator

from sqlalchemy.orm import Session

from app.core.database import SessionLocal


@contextmanager
def database_session() -> Generator[Session, None, None]:
    """Context manager for database sessions in workers.

    Provides a database session that is automatically closed after use,
    ensuring proper cleanup and connection management.

    Yields:
        Session: SQLAlchemy database session

    Example:
        >>> with database_session() as db:
        ...     documents = db.query(Document).all()
        ...     # Session automatically closed after block
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def with_database_session(func):
    """Decorator that injects db session as first argument.

    Wraps a function to automatically provide a database session as the
    first argument. The session is properly managed and closed after
    the function completes.

    Args:
        func: Function to wrap. Must accept db session as first parameter.

    Returns:
        Wrapped function with automatic session management

    Example:
        >>> @with_database_session
        ... def process_document(db: Session, document_id: int):
        ...     return db.query(Document).get(document_id)
        ...
        >>> # Call without passing db
        >>> doc = process_document(document_id=123)
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        with database_session() as db:
            return func(db, *args, **kwargs)
    return wrapper
