"""
Unit of Work pattern implementation for SQLAlchemy.

Manages database transactions and coordinates repository operations
within a single business transaction using async SQLAlchemy sessions.
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from app.shared.contracts.unit_of_work import AsyncUnitOfWork
from .repositories import (
    SQLAlchemyResearchRunRepository,
    SQLAlchemyFindingRepository,
    SQLAlchemyHypothesisRepository,
    SQLAlchemyDossierRepository,
    SQLAlchemyEntityRepository,
    SQLAlchemyEventRepository,
    SQLAlchemyRelationshipRepository,
    SQLAlchemyGraphRepository,
)


class UnitOfWorkException(Exception):
    """Exception raised for Unit of Work errors."""
    pass


class SQLAlchemyUnitOfWork(AsyncUnitOfWork):
    """
    SQLAlchemy implementation of AsyncUnitOfWork.

    Manages async database transactions and provides access to all repositories.
    Uses context manager protocol to ensure proper resource cleanup.

    Example:
        >>> async with uow:
        ...     research_run = await uow.research_runs.get_by_id(run_id)
        ...     research_run.mark_completed("path/to/dossier")
        ...     await uow.research_runs.save(research_run)
        ...     await uow.commit()
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        """
        Initialize Unit of Work with session factory.

        Args:
            session_factory: Async session factory from SQLAlchemy
        """
        self._session_factory = session_factory
        self._session: Optional[AsyncSession] = None

        # Repository instances (initialized on context entry)
        self.research_runs: Optional[SQLAlchemyResearchRunRepository] = None
        self.findings: Optional[SQLAlchemyFindingRepository] = None
        self.hypotheses: Optional[SQLAlchemyHypothesisRepository] = None
        self.dossiers: Optional[SQLAlchemyDossierRepository] = None
        self.entities: Optional[SQLAlchemyEntityRepository] = None
        self.events: Optional[SQLAlchemyEventRepository] = None
        self.relationships: Optional[SQLAlchemyRelationshipRepository] = None
        self.graph: Optional[SQLAlchemyGraphRepository] = None

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        """
        Enter async context manager and initialize session and repositories.

        Returns:
            Self for context manager protocol

        Raises:
            UnitOfWorkException: If session creation fails
        """
        try:
            # Create new session
            self._session = self._session_factory()

            # Initialize research repositories
            self.research_runs = SQLAlchemyResearchRunRepository(self._session)
            self.findings = SQLAlchemyFindingRepository(self._session)
            self.hypotheses = SQLAlchemyHypothesisRepository(self._session)
            self.dossiers = SQLAlchemyDossierRepository(self._session)

            # Initialize knowledge graph repositories
            self.entities = SQLAlchemyEntityRepository(self._session)
            self.events = SQLAlchemyEventRepository(self._session)
            self.relationships = SQLAlchemyRelationshipRepository(self._session)

            # Initialize graph repository with dependencies
            self.graph = SQLAlchemyGraphRepository(
                self._session,
                self.entities,
                self.events,
                self.relationships,
            )

            return self
        except Exception as e:
            raise UnitOfWorkException(f"Failed to initialize Unit of Work: {e}") from e

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit async context manager and clean up resources.

        Automatically rolls back if an exception occurred, then closes the session.

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred
        """
        if self._session is None:
            return

        try:
            # Rollback if there was an exception
            if exc_type is not None:
                await self.rollback()
        finally:
            # Always close the session
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        """
        Commit all changes made within this unit of work.

        Persists all repository operations to the database in a single transaction.

        Raises:
            UnitOfWorkException: If commit fails or session is not initialized
        """
        if self._session is None:
            raise UnitOfWorkException("Cannot commit: session not initialized")

        try:
            await self._session.commit()
        except SQLAlchemyError as e:
            # Rollback on error
            await self.rollback()
            raise UnitOfWorkException(f"Failed to commit transaction: {e}") from e

    async def rollback(self) -> None:
        """
        Rollback all changes made within this unit of work.

        Discards all repository operations and reverts to the state before
        the unit of work began.

        Raises:
            UnitOfWorkException: If rollback fails or session is not initialized
        """
        if self._session is None:
            raise UnitOfWorkException("Cannot rollback: session not initialized")

        try:
            await self._session.rollback()
        except SQLAlchemyError as e:
            raise UnitOfWorkException(f"Failed to rollback transaction: {e}") from e

    async def flush(self) -> None:
        """
        Flush pending changes to the database without committing.

        This is useful to get database-generated IDs or to verify constraints
        before committing.

        Raises:
            UnitOfWorkException: If flush fails or session is not initialized
        """
        if self._session is None:
            raise UnitOfWorkException("Cannot flush: session not initialized")

        try:
            await self._session.flush()
        except SQLAlchemyError as e:
            raise UnitOfWorkException(f"Failed to flush session: {e}") from e


class SQLAlchemyUnitOfWorkFactory:
    """
    Factory for creating SQLAlchemy Unit of Work instances.

    This factory encapsulates the session factory and provides a clean
    interface for dependency injection.

    Example:
        >>> from app.core.database import AsyncSessionLocal
        >>> factory = SQLAlchemyUnitOfWorkFactory(AsyncSessionLocal)
        >>> async with factory.create() as uow:
        ...     # Use repositories
        ...     await uow.commit()
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        """
        Initialize factory with session factory.

        Args:
            session_factory: Async session factory from SQLAlchemy
        """
        self._session_factory = session_factory

    def create(self) -> SQLAlchemyUnitOfWork:
        """
        Create a new Unit of Work instance.

        Returns:
            New SQLAlchemyUnitOfWork instance ready to use with async context manager
        """
        return SQLAlchemyUnitOfWork(self._session_factory)
