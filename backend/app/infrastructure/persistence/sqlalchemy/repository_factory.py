"""
Repository factory for dependency injection.

Provides factory functions to create repository instances with proper
configuration for use in application services and API endpoints.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
from .unit_of_work import SQLAlchemyUnitOfWork, SQLAlchemyUnitOfWorkFactory


class RepositoryFactory:
    """
    Factory for creating repository instances.

    This factory provides a centralized way to create repositories with
    proper session management and configuration.

    Example:
        >>> from app.core.database import AsyncSessionLocal
        >>> factory = RepositoryFactory(AsyncSessionLocal)
        >>>
        >>> # Get a Unit of Work
        >>> async with factory.create_unit_of_work() as uow:
        ...     research_run = await uow.research_runs.get_by_id(run_id)
        ...     await uow.commit()
        >>>
        >>> # Or create individual repositories
        >>> async with AsyncSessionLocal() as session:
        ...     repo = factory.create_research_run_repository(session)
        ...     research_run = await repo.get_by_id(run_id)
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        """
        Initialize factory with session factory.

        Args:
            session_factory: Async session factory from SQLAlchemy
        """
        self._session_factory = session_factory
        self._uow_factory = SQLAlchemyUnitOfWorkFactory(session_factory)

    # ========================================================================
    # Unit of Work
    # ========================================================================

    def create_unit_of_work(self) -> SQLAlchemyUnitOfWork:
        """
        Create a new Unit of Work instance.

        Returns:
            SQLAlchemyUnitOfWork instance ready to use with async context manager

        Example:
            >>> async with factory.create_unit_of_work() as uow:
            ...     # Use repositories
            ...     await uow.commit()
        """
        return self._uow_factory.create()

    # ========================================================================
    # Research Repositories
    # ========================================================================

    def create_research_run_repository(
        self, session: AsyncSession
    ) -> SQLAlchemyResearchRunRepository:
        """
        Create a ResearchRun repository.

        Args:
            session: Async SQLAlchemy session

        Returns:
            SQLAlchemyResearchRunRepository instance
        """
        return SQLAlchemyResearchRunRepository(session)

    def create_finding_repository(
        self, session: AsyncSession
    ) -> SQLAlchemyFindingRepository:
        """
        Create a Finding repository.

        Args:
            session: Async SQLAlchemy session

        Returns:
            SQLAlchemyFindingRepository instance
        """
        return SQLAlchemyFindingRepository(session)

    def create_hypothesis_repository(
        self, session: AsyncSession
    ) -> SQLAlchemyHypothesisRepository:
        """
        Create a Hypothesis repository.

        Args:
            session: Async SQLAlchemy session

        Returns:
            SQLAlchemyHypothesisRepository instance
        """
        return SQLAlchemyHypothesisRepository(session)

    def create_dossier_repository(
        self, session: AsyncSession
    ) -> SQLAlchemyDossierRepository:
        """
        Create a Dossier repository.

        Args:
            session: Async SQLAlchemy session

        Returns:
            SQLAlchemyDossierRepository instance
        """
        return SQLAlchemyDossierRepository(session)

    # ========================================================================
    # Knowledge Graph Repositories
    # ========================================================================

    def create_entity_repository(
        self, session: AsyncSession
    ) -> SQLAlchemyEntityRepository:
        """
        Create an Entity repository.

        Args:
            session: Async SQLAlchemy session

        Returns:
            SQLAlchemyEntityRepository instance
        """
        return SQLAlchemyEntityRepository(session)

    def create_event_repository(
        self, session: AsyncSession
    ) -> SQLAlchemyEventRepository:
        """
        Create an Event repository.

        Args:
            session: Async SQLAlchemy session

        Returns:
            SQLAlchemyEventRepository instance
        """
        return SQLAlchemyEventRepository(session)

    def create_relationship_repository(
        self, session: AsyncSession
    ) -> SQLAlchemyRelationshipRepository:
        """
        Create a Relationship repository.

        Args:
            session: Async SQLAlchemy session

        Returns:
            SQLAlchemyRelationshipRepository instance
        """
        return SQLAlchemyRelationshipRepository(session)

    def create_graph_repository(
        self, session: AsyncSession
    ) -> SQLAlchemyGraphRepository:
        """
        Create a Graph repository with all dependencies.

        Args:
            session: Async SQLAlchemy session

        Returns:
            SQLAlchemyGraphRepository instance with all sub-repositories

        Note:
            This creates instances of entity, event, and relationship repositories
            internally to satisfy the graph repository's dependencies.
        """
        entity_repo = self.create_entity_repository(session)
        event_repo = self.create_event_repository(session)
        relationship_repo = self.create_relationship_repository(session)

        return SQLAlchemyGraphRepository(
            session,
            entity_repo,
            event_repo,
            relationship_repo,
        )


# Singleton factory instance (will be initialized with session factory)
_factory: RepositoryFactory | None = None


def init_repository_factory(
    session_factory: async_sessionmaker[AsyncSession]
) -> RepositoryFactory:
    """
    Initialize the global repository factory.

    This should be called once during application startup.

    Args:
        session_factory: Async session factory from SQLAlchemy

    Returns:
        Initialized RepositoryFactory instance

    Example:
        >>> from app.core.database import AsyncSessionLocal
        >>> factory = init_repository_factory(AsyncSessionLocal)
    """
    global _factory
    _factory = RepositoryFactory(session_factory)
    return _factory


def get_repository_factory() -> RepositoryFactory:
    """
    Get the global repository factory instance.

    Returns:
        RepositoryFactory instance

    Raises:
        RuntimeError: If factory has not been initialized

    Example:
        >>> factory = get_repository_factory()
        >>> async with factory.create_unit_of_work() as uow:
        ...     # Use repositories
        ...     pass
    """
    if _factory is None:
        raise RuntimeError(
            "Repository factory not initialized. "
            "Call init_repository_factory() first."
        )
    return _factory


# Dependency injection helper for FastAPI
async def get_unit_of_work() -> SQLAlchemyUnitOfWork:
    """
    FastAPI dependency for getting a Unit of Work.

    This is a convenience function for use with FastAPI's Depends().

    Example:
        >>> from fastapi import Depends
        >>>
        >>> @app.post("/research/runs")
        >>> async def create_research_run(
        ...     uow: SQLAlchemyUnitOfWork = Depends(get_unit_of_work)
        ... ):
        ...     async with uow:
        ...         # Use repositories
        ...         await uow.commit()
    """
    factory = get_repository_factory()
    return factory.create_unit_of_work()
