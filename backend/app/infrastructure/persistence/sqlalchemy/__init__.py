"""
SQLAlchemy persistence layer.

This module provides SQLAlchemy-based implementations of repositories
and the Unit of Work pattern for the research and knowledge domains.

Example:
    >>> from app.infrastructure.persistence.sqlalchemy import (
    ...     init_repository_factory,
    ...     get_repository_factory,
    ... )
    >>> from app.core.database import AsyncSessionLocal
    >>>
    >>> # Initialize factory at startup
    >>> factory = init_repository_factory(AsyncSessionLocal)
    >>>
    >>> # Use in application
    >>> async with factory.create_unit_of_work() as uow:
    ...     research_run = await uow.research_runs.get_by_id(run_id)
    ...     await uow.commit()
"""

from .models import (
    ResearchRunModel,
    FindingModel,
    HypothesisModel,
    DossierModel,
    EntityModel,
    EventModel,
    RelationshipModel,
)
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
from .unit_of_work import (
    SQLAlchemyUnitOfWork,
    SQLAlchemyUnitOfWorkFactory,
    UnitOfWorkException,
)
from .repository_factory import (
    RepositoryFactory,
    init_repository_factory,
    get_repository_factory,
    get_unit_of_work,
)

__all__ = [
    # Models
    "ResearchRunModel",
    "FindingModel",
    "HypothesisModel",
    "DossierModel",
    "EntityModel",
    "EventModel",
    "RelationshipModel",
    # Repositories
    "SQLAlchemyResearchRunRepository",
    "SQLAlchemyFindingRepository",
    "SQLAlchemyHypothesisRepository",
    "SQLAlchemyDossierRepository",
    "SQLAlchemyEntityRepository",
    "SQLAlchemyEventRepository",
    "SQLAlchemyRelationshipRepository",
    "SQLAlchemyGraphRepository",
    # Unit of Work
    "SQLAlchemyUnitOfWork",
    "SQLAlchemyUnitOfWorkFactory",
    "UnitOfWorkException",
    # Factory
    "RepositoryFactory",
    "init_repository_factory",
    "get_repository_factory",
    "get_unit_of_work",
]
