"""
Relationship entity for the Knowledge domain.

Represents connections between entities in the knowledge graph.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
from uuid import UUID


class RelationshipType(str, Enum):
    """Type of relationship between entities."""

    WORKS_FOR = "WORKS_FOR"
    EMPLOYED_BY = "EMPLOYED_BY"
    OWNS = "OWNS"
    PARTNER_OF = "PARTNER_OF"
    FAMILY_OF = "FAMILY_OF"
    KNOWS = "KNOWS"
    LOCATED_AT = "LOCATED_AT"
    PARTY_TO = "PARTY_TO"
    SIGNED = "SIGNED"
    COMMUNICATED_WITH = "COMMUNICATED_WITH"
    ATTENDED = "ATTENDED"
    OTHER = "OTHER"


@dataclass
class Relationship:
    """
    Relationship entity representing a connection between entities.

    Relationships are edges in the knowledge graph with temporal bounds
    and strength indicators.

    Attributes:
        id: Unique identifier
        from_entity_id: Source entity ID
        to_entity_id: Target entity ID
        relationship_type: Type of relationship
        strength: Relationship strength (0.0-1.0)
        source_citations: Citations supporting this relationship
        temporal_start: Optional start of relationship
        temporal_end: Optional end of relationship
        metadata: Additional metadata

    Example:
        >>> relationship = Relationship(
        ...     id=uuid4(),
        ...     from_entity_id=person_id,
        ...     to_entity_id=org_id,
        ...     relationship_type=RelationshipType.WORKS_FOR,
        ...     strength=0.95,
        ...     source_citations=[citation1_id, citation2_id],
        ...     temporal_start=datetime(2020, 1, 1),
        ... )
    """

    id: UUID
    from_entity_id: UUID
    to_entity_id: UUID
    relationship_type: RelationshipType
    strength: float
    source_citations: List[UUID]
    temporal_start: Optional[datetime] = None
    temporal_end: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate relationship invariants."""
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError(f"Strength must be 0.0-1.0, got {self.strength}")
        if self.temporal_start and self.temporal_end:
            if self.temporal_end < self.temporal_start:
                raise ValueError("Temporal end must be >= temporal start")

    def add_citation(self, citation_id: UUID) -> None:
        """Add a source citation."""
        if citation_id not in self.source_citations:
            self.source_citations.append(citation_id)

    def is_active(self, at_time: Optional[datetime] = None) -> bool:
        """
        Check if relationship is active at a given time.

        Args:
            at_time: Time to check (default: now)

        Returns:
            True if relationship is active
        """
        check_time = at_time or datetime.utcnow()

        if self.temporal_start and check_time < self.temporal_start:
            return False
        if self.temporal_end and check_time > self.temporal_end:
            return False
        return True

    def is_strong(self, threshold: float = 0.7) -> bool:
        """Check if relationship is strong."""
        return self.strength >= threshold

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Relationship):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
