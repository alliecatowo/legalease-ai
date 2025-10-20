"""
Hypothesis entity for the Research domain.

Represents a testable theory or explanation generated from findings.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from uuid import UUID


@dataclass
class Hypothesis:
    """
    Hypothesis entity representing a generated theory.

    Hypotheses are higher-level interpretations synthesized from findings,
    supported or contradicted by evidence.

    Attributes:
        id: Unique identifier
        research_run_id: ID of the research run
        hypothesis_text: The hypothesis statement
        supporting_findings: Findings that support this hypothesis
        contradicting_findings: Findings that contradict this hypothesis
        confidence: Overall confidence in the hypothesis (0.0-1.0)
        metadata: Additional metadata

    Example:
        >>> hypothesis = Hypothesis(
        ...     id=uuid4(),
        ...     research_run_id=uuid4(),
        ...     hypothesis_text="Contract was modified after initial signing",
        ...     supporting_findings=[finding1_id, finding2_id],
        ...     contradicting_findings=[],
        ...     confidence=0.82,
        ... )
    """

    id: UUID
    research_run_id: UUID
    hypothesis_text: str
    supporting_findings: List[UUID]
    contradicting_findings: List[UUID]
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate hypothesis invariants."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")

    def get_support_ratio(self) -> float:
        """Calculate ratio of supporting to total findings."""
        total = len(self.supporting_findings) + len(self.contradicting_findings)
        if total == 0:
            return 0.0
        return len(self.supporting_findings) / total

    def is_well_supported(self, min_ratio: float = 0.7) -> bool:
        """Check if hypothesis is well-supported."""
        return self.get_support_ratio() >= min_ratio

    def add_supporting_finding(self, finding_id: UUID) -> None:
        """Add a supporting finding."""
        if finding_id not in self.supporting_findings:
            self.supporting_findings.append(finding_id)

    def add_contradicting_finding(self, finding_id: UUID) -> None:
        """Add a contradicting finding."""
        if finding_id not in self.contradicting_findings:
            self.contradicting_findings.append(finding_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Hypothesis):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
