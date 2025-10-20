"""
Unit of Work protocol for transaction management.

This module defines the UnitOfWork protocol that manages transactions
and coordinates multiple repository operations within a single business transaction.

Example:
    >>> async with uow:
    ...     case = await uow.cases.get(case_id)
    ...     case.status = CaseStatus.CLOSED
    ...     await uow.cases.save(case)
    ...     await uow.commit()
"""

from typing import Protocol, runtime_checkable
from contextlib import AbstractContextManager


@runtime_checkable
class UnitOfWork(Protocol):
    """
    Unit of Work protocol for managing transactions.

    The Unit of Work pattern maintains a list of objects affected by a
    business transaction and coordinates writing out changes and resolving
    concurrency problems.

    This protocol ensures that all repository operations within a unit of work
    are committed or rolled back together, maintaining data consistency.

    Example:
        >>> class SqlAlchemyUnitOfWork(UnitOfWork):
        ...     def __init__(self, session_factory):
        ...         self.session_factory = session_factory
        ...         self.session = None
        ...
        ...     def __enter__(self):
        ...         self.session = self.session_factory()
        ...         self.cases = CaseRepository(self.session)
        ...         self.documents = DocumentRepository(self.session)
        ...         return self
        ...
        ...     def __exit__(self, exc_type, exc_val, exc_tb):
        ...         if exc_type is not None:
        ...             self.rollback()
        ...         self.session.close()
        ...
        ...     def commit(self):
        ...         self.session.commit()
        ...
        ...     def rollback(self):
        ...         self.session.rollback()

        >>> # Usage
        >>> with uow:
        ...     case = uow.cases.get(case_id)
        ...     case.name = "Updated Name"
        ...     uow.cases.save(case)
        ...     uow.commit()
    """

    def __enter__(self) -> "UnitOfWork":
        """
        Enter the context manager and initialize the unit of work.

        This should create a database session/transaction and
        initialize all repositories.

        Returns:
            Self for context manager protocol

        Example:
            >>> with uow:
            ...     # Work with repositories
            ...     pass
        """
        ...

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the context manager and clean up resources.

        This should rollback if there was an exception, and always
        close the database session.

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred

        Example:
            >>> with uow:
            ...     raise ValueError("Error")
            ... # Automatically rolls back on exception
        """
        ...

    def commit(self) -> None:
        """
        Commit all changes made within this unit of work.

        This persists all repository operations to the database
        in a single transaction.

        Raises:
            RepositoryException: If commit fails
            ConcurrencyException: If optimistic locking detects conflicts

        Example:
            >>> with uow:
            ...     uow.cases.add(case)
            ...     uow.documents.add(document)
            ...     uow.commit()  # Both saved together
        """
        ...

    def rollback(self) -> None:
        """
        Rollback all changes made within this unit of work.

        This discards all repository operations and reverts to
        the state before the unit of work began.

        Example:
            >>> with uow:
            ...     uow.cases.add(case)
            ...     if validation_fails:
            ...         uow.rollback()
            ...         return
            ...     uow.commit()
        """
        ...

    def flush(self) -> None:
        """
        Flush pending changes to the database without committing.

        This is useful to get database-generated IDs or to verify
        constraints before committing.

        Example:
            >>> with uow:
            ...     uow.cases.add(case)
            ...     uow.flush()  # Get auto-generated ID
            ...     print(f"Generated ID: {case.id}")
            ...     uow.commit()
        """
        ...


@runtime_checkable
class AsyncUnitOfWork(Protocol):
    """
    Async Unit of Work protocol for managing async transactions.

    This is the async version of UnitOfWork for use with async/await
    database operations.

    Example:
        >>> class AsyncSqlAlchemyUnitOfWork(AsyncUnitOfWork):
        ...     def __init__(self, session_factory):
        ...         self.session_factory = session_factory
        ...         self.session = None
        ...
        ...     async def __aenter__(self):
        ...         self.session = self.session_factory()
        ...         self.cases = CaseRepository(self.session)
        ...         self.documents = DocumentRepository(self.session)
        ...         return self
        ...
        ...     async def __aexit__(self, exc_type, exc_val, exc_tb):
        ...         if exc_type is not None:
        ...             await self.rollback()
        ...         await self.session.close()
        ...
        ...     async def commit(self):
        ...         await self.session.commit()
        ...
        ...     async def rollback(self):
        ...         await self.session.rollback()

        >>> # Usage
        >>> async with uow:
        ...     case = await uow.cases.get(case_id)
        ...     case.name = "Updated Name"
        ...     await uow.cases.save(case)
        ...     await uow.commit()
    """

    async def __aenter__(self) -> "AsyncUnitOfWork":
        """
        Enter the async context manager and initialize the unit of work.

        Returns:
            Self for async context manager protocol
        """
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the async context manager and clean up resources.

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred
        """
        ...

    async def commit(self) -> None:
        """
        Commit all changes made within this unit of work.

        Raises:
            RepositoryException: If commit fails
            ConcurrencyException: If optimistic locking detects conflicts
        """
        ...

    async def rollback(self) -> None:
        """Rollback all changes made within this unit of work."""
        ...

    async def flush(self) -> None:
        """Flush pending changes to the database without committing."""
        ...


class UnitOfWorkFactory(Protocol):
    """
    Factory protocol for creating Unit of Work instances.

    This enables dependency injection of UoW creation logic.

    Example:
        >>> class SqlAlchemyUnitOfWorkFactory(UnitOfWorkFactory):
        ...     def __init__(self, session_factory):
        ...         self.session_factory = session_factory
        ...
        ...     def create(self) -> UnitOfWork:
        ...         return SqlAlchemyUnitOfWork(self.session_factory)

        >>> # Usage with dependency injection
        >>> def process_case(case_id: str, uow_factory: UnitOfWorkFactory):
        ...     with uow_factory.create() as uow:
        ...         case = uow.cases.get(case_id)
        ...         # Process case...
        ...         uow.commit()
    """

    def create(self) -> UnitOfWork:
        """
        Create a new Unit of Work instance.

        Returns:
            New UnitOfWork instance

        Example:
            >>> uow = factory.create()
            >>> with uow:
            ...     # Work with repositories
            ...     uow.commit()
        """
        ...


class AsyncUnitOfWorkFactory(Protocol):
    """
    Factory protocol for creating Async Unit of Work instances.

    Example:
        >>> class AsyncSqlAlchemyUnitOfWorkFactory(AsyncUnitOfWorkFactory):
        ...     def __init__(self, session_factory):
        ...         self.session_factory = session_factory
        ...
        ...     def create(self) -> AsyncUnitOfWork:
        ...         return AsyncSqlAlchemyUnitOfWork(self.session_factory)
    """

    def create(self) -> AsyncUnitOfWork:
        """
        Create a new Async Unit of Work instance.

        Returns:
            New AsyncUnitOfWork instance
        """
        ...
