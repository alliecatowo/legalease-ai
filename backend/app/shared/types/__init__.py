"""Shared type definitions for the application."""

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

__all__ = [
    "CaseId",
    "DocumentId",
    "ResearchRunId",
    "FindingId",
    "EntityId",
    "GID",
    "generate_id",
    "parse_gid",
    "is_valid_gid",
    "EvidenceType",
    "ResearchPhase",
    "ResearchStatus",
    "FindingType",
    "EntityType",
    "RelationshipType",
    "ChunkType",
    "ConfidenceLevel",
]
