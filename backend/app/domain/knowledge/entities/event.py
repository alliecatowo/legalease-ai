"""
Event entity for the Knowledge domain.

Represents temporal events extracted from evidence.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
from uuid import UUID


class EventType(str, Enum):
    """Type of event."""

    MEETING = "MEETING"
    COMMUNICATION = "COMMUNICATION"
    TRANSACTION = "TRANSACTION"
    AGREEMENT = "AGREEMENT"
    LEGAL_ACTION = "LEGAL_ACTION"
    INCIDENT = "INCIDENT"
    DEADLINE = "DEADLINE"
    OTHER = "OTHER"


@dataclass
class Event:
    """
    Event entity representing a temporal occurrence.

    Events are timeline nodes in the knowledge graph with participants,
    location, and temporal bounds.

    Attributes:
        id: Unique identifier
        event_type: Type of event
        description: Human-readable description
        participants: Entity IDs of participants
        location: Location entity ID or string
        timestamp: Primary timestamp
        duration: Optional duration in seconds
        source_citations: Citations to evidence
        metadata: Additional metadata

    Example:
        >>> event = Event(
        ...     id=uuid4(),
        ...     event_type=EventType.MEETING,
        ...     description="Contract negotiation meeting at Acme Corp headquarters",
        ...     participants=[person1_id, person2_id],
        ...     location=location_id,
        ...     timestamp=datetime(2024, 3, 15, 14, 30),
        ...     duration=3600,
        ...     source_citations=[citation_id],
        ... )
    """

    id: UUID
    event_type: EventType
    description: str
    participants: List[UUID]
    timestamp: datetime
    source_citations: List[UUID]
    location: Optional[UUID | str] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_participant(self, entity_id: UUID) -> None:
        """Add a participant entity."""
        if entity_id not in self.participants:
            self.participants.append(entity_id)

    def add_citation(self, citation_id: UUID) -> None:
        """Add a source citation."""
        if citation_id not in self.source_citations:
            self.source_citations.append(citation_id)

    def get_end_time(self) -> Optional[datetime]:
        """Calculate end time if duration is known."""
        if self.duration:
            from datetime import timedelta
            return self.timestamp + timedelta(seconds=self.duration)
        return None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Event):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
