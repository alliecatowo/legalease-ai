"""
Finding entity for the Research domain.

Represents a discovered fact, pattern, or insight from evidence analysis.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from uuid import UUID


class FindingType(str, Enum):
    """Type of finding."""

    FACT = "FACT"
    PATTERN = "PATTERN"
    ANOMALY = "ANOMALY"
    RELATIONSHIP = "RELATIONSHIP"
    TIMELINE_EVENT = "TIMELINE_EVENT"
    CONTRADICTION = "CONTRADICTION"
    CORROBORATION = "CORROBORATION"
    GAP = "GAP"


@dataclass
class Finding:
    """
    Finding entity representing a discovered insight.

    Findings are atomic units of discovery during research, backed by
    citations to evidence and scored for confidence and relevance.

    Attributes:
        id: Unique identifier
        research_run_id: ID of the research run that discovered this finding
        finding_type: Type of finding
        text: Human-readable description of the finding
        entities: List of entity IDs referenced in this finding
        citations: List of citation IDs supporting this finding
        confidence: Confidence score (0.0-1.0)
        relevance: Relevance score to research query (0.0-1.0)
        tags: Categorical tags for organization
        metadata: Additional metadata

    Example:
        >>> finding = Finding(
        ...     id=uuid4(),
        ...     research_run_id=uuid4(),
        ...     finding_type=FindingType.FACT,
        ...     text="John Doe signed the contract on 2024-03-15",
        ...     entities=[person_id, document_id],
        ...     citations=[citation_id],
        ...     confidence=0.95,
        ...     relevance=0.88,
        ...     tags=["contract", "signature"],
        ... )
    """

    id: UUID
    research_run_id: UUID
    finding_type: FindingType
    text: str
    entities: List[UUID]
    citations: List[UUID]
    confidence: float
    relevance: float
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate finding invariants."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")
        if not 0.0 <= self.relevance <= 1.0:
            raise ValueError(f"Relevance must be 0.0-1.0, got {self.relevance}")

    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if finding has high confidence."""
        return self.confidence >= threshold

    def is_relevant(self, threshold: float = 0.7) -> bool:
        """Check if finding is relevant."""
        return self.relevance >= threshold

    def has_tag(self, tag: str) -> bool:
        """Check if finding has a specific tag."""
        return tag in self.tags

    def add_citation(self, citation_id: UUID) -> None:
        """Add a citation to the finding."""
        if citation_id not in self.citations:
            self.citations.append(citation_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Finding):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
