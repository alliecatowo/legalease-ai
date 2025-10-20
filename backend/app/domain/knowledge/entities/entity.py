"""
Entity entity for the Knowledge domain.

Represents people, organizations, and locations in the knowledge graph.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
from uuid import UUID


class EntityType(str, Enum):
    """Type of entity in the knowledge graph."""

    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    LOCATION = "LOCATION"
    EVENT = "EVENT"
    DATE = "DATE"
    MONEY = "MONEY"
    LEGAL_TERM = "LEGAL_TERM"
    CASE_NUMBER = "CASE_NUMBER"
    STATUTE = "STATUTE"
    OTHER = "OTHER"


@dataclass
class Entity:
    """
    Entity representing a person, organization, or location.

    Entities are nodes in the knowledge graph extracted from evidence
    and linked through relationships.

    Attributes:
        id: Unique identifier
        entity_type: Type of entity
        name: Primary name
        aliases: Alternative names or spellings
        attributes: Key-value attributes (e.g., title, role, address)
        first_seen: First mention in evidence
        last_seen: Last mention in evidence
        source_citations: Citations to evidence where entity appears
        metadata: Additional metadata

    Example:
        >>> entity = Entity(
        ...     id=uuid4(),
        ...     entity_type=EntityType.PERSON,
        ...     name="John Doe",
        ...     aliases=["J. Doe", "Jonathan Doe"],
        ...     attributes={"role": "CEO", "company": "Acme Corp"},
        ...     first_seen=datetime(2024, 1, 15),
        ...     last_seen=datetime(2024, 3, 20),
        ...     source_citations=[citation1_id, citation2_id],
        ... )
    """

    id: UUID
    entity_type: EntityType
    name: str
    aliases: List[str]
    attributes: Dict[str, Any]
    first_seen: datetime
    last_seen: datetime
    source_citations: List[UUID] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_alias(self, alias: str) -> None:
        """Add an alias if not already present."""
        if alias not in self.aliases and alias != self.name:
            self.aliases.append(alias)

    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute value."""
        self.attributes[key] = value

    def get_attribute(self, key: str, default: Any = None) -> Any:
        """Get an attribute value."""
        return self.attributes.get(key, default)

    def add_citation(self, citation_id: UUID) -> None:
        """Add a source citation."""
        if citation_id not in self.source_citations:
            self.source_citations.append(citation_id)

    def update_last_seen(self, timestamp: datetime) -> None:
        """Update last seen timestamp."""
        if timestamp > self.last_seen:
            self.last_seen = timestamp

    def is_person(self) -> bool:
        """Check if entity is a person."""
        return self.entity_type == EntityType.PERSON

    def is_organization(self) -> bool:
        """Check if entity is an organization."""
        return self.entity_type == EntityType.ORGANIZATION

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
