"""
Infrastructure layer exceptions.

Custom exceptions for infrastructure operations (database, storage, etc.)
to maintain clean boundaries in hexagonal architecture.
"""

from typing import Optional, Any


class InfrastructureException(Exception):
    """Base exception for all infrastructure layer errors."""

    def __init__(
        self,
        message: str,
        *,
        cause: Optional[Exception] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Initialize infrastructure exception.

        Args:
            message: Human-readable error message
            cause: Original exception that caused this error
            context: Additional context about the error
        """
        super().__init__(message)
        self.message = message
        self.cause = cause
        self.context = context or {}

    def __str__(self) -> str:
        """String representation of the exception."""
        parts = [self.message]
        if self.cause:
            parts.append(f"Caused by: {type(self.cause).__name__}: {str(self.cause)}")
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"Context: {context_str}")
        return " | ".join(parts)


class VectorStoreException(InfrastructureException):
    """Exception for vector store operations (Qdrant)."""

    pass


class ConnectionException(InfrastructureException):
    """Exception for connection-related errors."""

    pass


class CollectionException(VectorStoreException):
    """Exception for collection management errors."""

    pass


class IndexingException(VectorStoreException):
    """Exception for vector indexing errors."""

    pass


class SearchException(VectorStoreException):
    """Exception for vector search errors."""

    pass


class DeletionException(VectorStoreException):
    """Exception for deletion errors."""

    pass
