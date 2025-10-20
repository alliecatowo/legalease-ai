"""
QueryBus for CQRS query dispatching.

Central dispatcher that routes queries to their handlers.
Follows the Command Query Responsibility Segregation (CQRS) pattern.
"""

import logging
from typing import Any, Dict, Type, TypeVar, Generic


logger = logging.getLogger(__name__)


# Type variables for generic query/result typing
TQuery = TypeVar("TQuery")
TResult = TypeVar("TResult")


class QueryHandler(Generic[TQuery, TResult]):
    """
    Base interface for query handlers.

    All query handlers should implement this interface.
    """

    async def handle(self, query: TQuery) -> TResult:
        """
        Handle the query and return result.

        Args:
            query: The query to handle

        Returns:
            Query result

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Query handler must implement handle() method")


class QueryBus:
    """
    Central dispatcher for all queries.

    Routes queries to their registered handlers and executes them.
    Provides middleware support for cross-cutting concerns like
    logging, validation, caching, etc.

    Example:
        >>> # Setup
        >>> bus = QueryBus()
        >>> bus.register(SearchEvidenceQuery, search_handler)
        >>> bus.register(GetFindingsQuery, findings_handler)
        >>>
        >>> # Usage
        >>> query = SearchEvidenceQuery(query="contract terms")
        >>> result = await bus.execute(query)
    """

    def __init__(self):
        """Initialize the query bus."""
        self._handlers: Dict[Type, QueryHandler] = {}
        self._middleware: list = []
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def register(self, query_type: Type[TQuery], handler: QueryHandler[TQuery, TResult]) -> None:
        """
        Register a query handler for a query type.

        Args:
            query_type: The query class type
            handler: The handler instance

        Raises:
            ValueError: If query type already registered

        Example:
            >>> bus.register(SearchEvidenceQuery, SearchEvidenceQueryHandler(...))
        """
        if query_type in self._handlers:
            raise ValueError(f"Handler already registered for {query_type.__name__}")

        self._handlers[query_type] = handler
        self.logger.info(
            f"Registered handler for query type: {query_type.__name__}",
            extra={"query_type": query_type.__name__}
        )

    def add_middleware(self, middleware: Any) -> None:
        """
        Add middleware to the query pipeline.

        Middleware is executed before the query handler.

        Args:
            middleware: Middleware callable or object

        Example:
            >>> bus.add_middleware(LoggingMiddleware())
            >>> bus.add_middleware(ValidationMiddleware())
        """
        self._middleware.append(middleware)
        self.logger.info(f"Added middleware: {middleware.__class__.__name__}")

    async def execute(self, query: TQuery) -> TResult:
        """
        Execute a query and return the result.

        Steps:
        1. Find registered handler for query type
        2. Execute middleware pipeline
        3. Execute query handler
        4. Return result

        Args:
            query: The query to execute

        Returns:
            Query result from handler

        Raises:
            ValueError: If no handler registered for query type
            RuntimeError: If query execution fails

        Example:
            >>> query = GetFindingsQuery(research_run_id=uuid)
            >>> result = await bus.execute(query)
        """
        query_type = type(query)

        # Find handler
        handler = self._handlers.get(query_type)
        if not handler:
            raise ValueError(
                f"No handler registered for query type: {query_type.__name__}. "
                f"Available handlers: {list(self._handlers.keys())}"
            )

        self.logger.debug(
            f"Executing query: {query_type.__name__}",
            extra={"query_type": query_type.__name__}
        )

        try:
            # Execute middleware
            for middleware in self._middleware:
                if hasattr(middleware, "before_query"):
                    await middleware.before_query(query)

            # Execute handler
            result = await handler.handle(query)

            # Execute middleware (after)
            for middleware in reversed(self._middleware):
                if hasattr(middleware, "after_query"):
                    await middleware.after_query(query, result)

            self.logger.debug(
                f"Query executed successfully: {query_type.__name__}",
                extra={"query_type": query_type.__name__}
            )

            return result

        except Exception as e:
            self.logger.error(
                f"Query execution failed: {query_type.__name__}: {e}",
                extra={"query_type": query_type.__name__},
                exc_info=True
            )

            # Execute middleware (on error)
            for middleware in reversed(self._middleware):
                if hasattr(middleware, "on_error"):
                    await middleware.on_error(query, e)

            raise RuntimeError(f"Query execution failed: {e}") from e

    def is_registered(self, query_type: Type) -> bool:
        """
        Check if a handler is registered for a query type.

        Args:
            query_type: The query class type

        Returns:
            True if handler is registered, False otherwise
        """
        return query_type in self._handlers

    def get_registered_queries(self) -> list[Type]:
        """
        Get list of all registered query types.

        Returns:
            List of query class types
        """
        return list(self._handlers.keys())


class LoggingMiddleware:
    """
    Middleware for query logging.

    Logs query execution with timing information.
    """

    def __init__(self):
        """Initialize logging middleware."""
        self.logger = logging.getLogger(f"{__name__}.LoggingMiddleware")

    async def before_query(self, query: Any) -> None:
        """Log before query execution."""
        import time
        query._start_time = time.time()
        self.logger.info(
            f"Query started: {type(query).__name__}",
            extra={"query_type": type(query).__name__}
        )

    async def after_query(self, query: Any, result: Any) -> None:
        """Log after query execution."""
        import time
        if hasattr(query, "_start_time"):
            duration = time.time() - query._start_time
            self.logger.info(
                f"Query completed: {type(query).__name__} in {duration:.3f}s",
                extra={
                    "query_type": type(query).__name__,
                    "duration_seconds": duration,
                }
            )

    async def on_error(self, query: Any, error: Exception) -> None:
        """Log query errors."""
        self.logger.error(
            f"Query failed: {type(query).__name__}: {error}",
            extra={"query_type": type(query).__name__},
            exc_info=True
        )


class ValidationMiddleware:
    """
    Middleware for query validation.

    Validates queries before execution using __post_init__ validation.
    """

    def __init__(self):
        """Initialize validation middleware."""
        self.logger = logging.getLogger(f"{__name__}.ValidationMiddleware")

    async def before_query(self, query: Any) -> None:
        """Validate query before execution."""
        # Query validation happens in __post_init__
        # This middleware can add additional validation logic
        if hasattr(query, "validate"):
            query.validate()
