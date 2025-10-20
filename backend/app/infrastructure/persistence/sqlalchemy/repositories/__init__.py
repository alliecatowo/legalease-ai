"""
SQLAlchemy repository implementations.

Exports all repository implementations for research and knowledge domains.
"""

from .research import (
    SQLAlchemyResearchRunRepository,
    SQLAlchemyFindingRepository,
    SQLAlchemyHypothesisRepository,
    SQLAlchemyDossierRepository,
    RepositoryException as ResearchRepositoryException,
)
from .knowledge import (
    SQLAlchemyEntityRepository,
    SQLAlchemyEventRepository,
    SQLAlchemyRelationshipRepository,
    SQLAlchemyGraphRepository,
    RepositoryException as KnowledgeRepositoryException,
)

__all__ = [
    # Research repositories
    "SQLAlchemyResearchRunRepository",
    "SQLAlchemyFindingRepository",
    "SQLAlchemyHypothesisRepository",
    "SQLAlchemyDossierRepository",
    "ResearchRepositoryException",
    # Knowledge repositories
    "SQLAlchemyEntityRepository",
    "SQLAlchemyEventRepository",
    "SQLAlchemyRelationshipRepository",
    "SQLAlchemyGraphRepository",
    "KnowledgeRepositoryException",
]