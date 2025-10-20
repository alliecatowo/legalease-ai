"""
Domain and infrastructure exception classes.

This module defines a hierarchy of exceptions for domain logic errors,
validation failures, and infrastructure problems. All exceptions include
helpful error messages and context for debugging.

Example:
    >>> raise EntityNotFoundException("Case", "123")
    EntityNotFoundException: Case with identifier '123' not found

    >>> raise ValidationException("Invalid email format", {"field": "email"})
    ValidationException: Invalid email format

    >>> try:
    ...     repository.save(entity)
    ... except ConcurrencyException as e:
    ...     print(f"Conflict: {e}")
"""

from typing import Any, Dict, Optional


class DomainException(Exception):
    """
    Base exception for all domain-related errors.

    All custom exceptions in the domain layer should inherit from this
    to enable consistent error handling and logging.

    Attributes:
        message: Human-readable error message
        context: Additional context about the error
        code: Optional error code for API responses
    """

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        code: Optional[str] = None
    ):
        """
        Initialize domain exception.

        Args:
            message: Human-readable error message
            context: Additional context dictionary
            code: Optional error code for categorization
        """
        self.message = message
        self.context = context or {}
        self.code = code
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation with context."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} ({context_str})"
        return self.message

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"{self.__class__.__name__}("
            f"message='{self.message}', "
            f"context={self.context}, "
            f"code='{self.code}')"
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for serialization.

        Returns:
            Dictionary with error details

        Example:
            >>> exc = DomainException("Error occurred", {"field": "name"})
            >>> exc.to_dict()
            {'type': 'DomainException', 'message': 'Error occurred', 'context': {'field': 'name'}}
        """
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "context": self.context,
            "code": self.code,
        }


class EntityNotFoundException(DomainException):
    """
    Raised when a requested entity cannot be found.

    This is typically raised by repositories when querying for
    an entity by ID or other unique identifier.

    Example:
        >>> raise EntityNotFoundException("Case", "abc123")
        EntityNotFoundException: Case with identifier 'abc123' not found

        >>> raise EntityNotFoundException(
        ...     "Document",
        ...     "doc456",
        ...     context={"case_id": "case123"}
        ... )
    """

    def __init__(
        self,
        entity_type: str,
        identifier: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize entity not found exception.

        Args:
            entity_type: Type of entity (e.g., "Case", "Document")
            identifier: The identifier that was not found
            context: Additional context about the search
        """
        message = f"{entity_type} with identifier '{identifier}' not found"
        context = context or {}
        context.update({"entity_type": entity_type, "identifier": identifier})
        super().__init__(message, context, code="ENTITY_NOT_FOUND")


class InvalidOperationException(DomainException):
    """
    Raised when an operation is invalid for the current state.

    This represents business rule violations or operations that
    cannot be performed given the current entity state.

    Example:
        >>> raise InvalidOperationException(
        ...     "Cannot archive an active case",
        ...     context={"case_id": "123", "status": "ACTIVE"}
        ... )

        >>> raise InvalidOperationException(
        ...     "Document must be processed before indexing",
        ...     context={"document_id": "doc456", "status": "PENDING"}
        ... )
    """

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize invalid operation exception.

        Args:
            message: Description of why the operation is invalid
            context: Additional context about the entity state
        """
        super().__init__(message, context, code="INVALID_OPERATION")


class ValidationException(DomainException):
    """
    Raised when entity validation fails.

    This represents validation errors in domain entities, value objects,
    or command/query parameters.

    Example:
        >>> raise ValidationException(
        ...     "Case name is required",
        ...     context={"field": "name"}
        ... )

        >>> raise ValidationException(
        ...     "Email format is invalid",
        ...     context={"field": "email", "value": "invalid-email"}
        ... )

        >>> # Multiple validation errors
        >>> raise ValidationException(
        ...     "Multiple validation errors",
        ...     context={
        ...         "errors": [
        ...             {"field": "name", "error": "required"},
        ...             {"field": "email", "error": "invalid_format"}
        ...         ]
        ...     }
        ... )
    """

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        field: Optional[str] = None,
    ):
        """
        Initialize validation exception.

        Args:
            message: Validation error message
            context: Additional context about the validation failure
            field: Optional field name that failed validation
        """
        context = context or {}
        if field:
            context["field"] = field
        super().__init__(message, context, code="VALIDATION_ERROR")


class ConcurrencyException(DomainException):
    """
    Raised when a concurrency conflict is detected.

    This typically occurs with optimistic locking when an entity
    has been modified by another process since it was loaded.

    Example:
        >>> raise ConcurrencyException(
        ...     "Case",
        ...     "123",
        ...     expected_version=5,
        ...     actual_version=6
        ... )
    """

    def __init__(
        self,
        entity_type: str,
        identifier: str,
        expected_version: Optional[int] = None,
        actual_version: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize concurrency exception.

        Args:
            entity_type: Type of entity
            identifier: Entity identifier
            expected_version: Expected version number
            actual_version: Actual version number in database
            context: Additional context
        """
        message = (
            f"Concurrency conflict updating {entity_type} '{identifier}'. "
            "Entity has been modified by another process."
        )
        context = context or {}
        context.update({
            "entity_type": entity_type,
            "identifier": identifier,
            "expected_version": expected_version,
            "actual_version": actual_version,
        })
        super().__init__(message, context, code="CONCURRENCY_CONFLICT")


class InfrastructureException(Exception):
    """
    Base exception for infrastructure-related errors.

    This covers database errors, external service failures, and
    other infrastructure problems. These are separate from domain
    exceptions to distinguish business logic errors from technical failures.

    Attributes:
        message: Human-readable error message
        context: Additional context about the error
        original_exception: The underlying exception if any
    """

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        Initialize infrastructure exception.

        Args:
            message: Human-readable error message
            context: Additional context dictionary
            original_exception: The underlying exception that was caught
        """
        self.message = message
        self.context = context or {}
        self.original_exception = original_exception
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation with context."""
        result = self.message
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            result = f"{result} ({context_str})"
        if self.original_exception:
            result = f"{result}. Caused by: {self.original_exception}"
        return result

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"{self.__class__.__name__}("
            f"message='{self.message}', "
            f"context={self.context}, "
            f"original_exception={self.original_exception})"
        )


class RepositoryException(InfrastructureException):
    """
    Raised when a repository operation fails.

    This covers database errors, connection issues, and other
    persistence-layer problems.

    Example:
        >>> raise RepositoryException(
        ...     "Failed to save case",
        ...     context={"case_id": "123"},
        ...     original_exception=db_error
        ... )

        >>> raise RepositoryException(
        ...     "Database connection failed",
        ...     context={"host": "localhost", "port": 5432}
        ... )
    """

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        Initialize repository exception.

        Args:
            message: Description of the repository error
            context: Additional context about the operation
            original_exception: The underlying database exception
        """
        super().__init__(message, context, original_exception)


class ExternalServiceException(InfrastructureException):
    """
    Raised when an external service call fails.

    This covers API calls, message queue operations, and other
    external service interactions.

    Example:
        >>> raise ExternalServiceException(
        ...     "Ollama API request failed",
        ...     context={
        ...         "service": "ollama",
        ...         "endpoint": "/api/generate",
        ...         "status_code": 503
        ...     }
        ... )

        >>> raise ExternalServiceException(
        ...     "Qdrant vector store unavailable",
        ...     context={"service": "qdrant", "operation": "search"}
        ... )
    """

    def __init__(
        self,
        message: str,
        service_name: str,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        Initialize external service exception.

        Args:
            message: Description of the service error
            service_name: Name of the external service
            context: Additional context about the operation
            original_exception: The underlying exception from the service client
        """
        context = context or {}
        context["service"] = service_name
        super().__init__(message, context, original_exception)
