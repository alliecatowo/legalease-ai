"""
Shared module containing types, exceptions, and contracts.

This module provides common types, enums, exceptions, and protocols
used throughout the application for consistency and type safety.
"""

from app.shared.types.identifiers import (
    CaseId,
    DocumentId,
    ResearchRunId,
    FindingId,
    EntityId,
    GID,
    generate_id,
    parse_gid,
    is_valid_gid,
)
from app.shared.types.enums import (
    EvidenceType,
    ResearchPhase,
    ResearchStatus,
    FindingType,
    EntityType,
    RelationshipType,
    ChunkType,
    ConfidenceLevel,
)
from app.shared.exceptions.domain_exceptions import (
    DomainException,
    EntityNotFoundException,
    InvalidOperationException,
    ValidationException,
    ConcurrencyException,
    InfrastructureException,
    RepositoryException,
    ExternalServiceException,
)
from app.shared.contracts.repository import Repository
from app.shared.contracts.unit_of_work import UnitOfWork
from app.shared.contracts.event_dispatcher import EventDispatcher

__all__ = [
    # Identifiers
    "CaseId",
    "DocumentId",
    "ResearchRunId",
    "FindingId",
    "EntityId",
    "GID",
    "generate_id",
    "parse_gid",
    "is_valid_gid",
    # Enums
    "EvidenceType",
    "ResearchPhase",
    "ResearchStatus",
    "FindingType",
    "EntityType",
    "RelationshipType",
    "ChunkType",
    "ConfidenceLevel",
    # Exceptions
    "DomainException",
    "EntityNotFoundException",
    "InvalidOperationException",
    "ValidationException",
    "ConcurrencyException",
    "InfrastructureException",
    "RepositoryException",
    "ExternalServiceException",
    # Contracts
    "Repository",
    "UnitOfWork",
    "EventDispatcher",
]
