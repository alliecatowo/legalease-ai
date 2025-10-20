"""
Confidence value object for the Research domain.

Represents confidence level with reasoning and evidence count.
"""

from dataclasses import dataclass
from enum import Enum


class ConfidenceLevel(str, Enum):
    """Categorical confidence level."""

    VERY_HIGH = "VERY_HIGH"  # 0.9-1.0
    HIGH = "HIGH"  # 0.7-0.89
    MEDIUM = "MEDIUM"  # 0.5-0.69
    LOW = "LOW"  # 0.3-0.49
    VERY_LOW = "VERY_LOW"  # 0.0-0.29


@dataclass(frozen=True)
class Confidence:
    """
    Immutable confidence value object.

    Represents confidence in a finding or hypothesis with reasoning.

    Attributes:
        level: Categorical confidence level
        reasoning: Explanation for the confidence level
        supporting_evidence_count: Number of supporting evidence items

    Example:
        >>> confidence = Confidence(
        ...     level=ConfidenceLevel.HIGH,
        ...     reasoning="Supported by 3 independent document citations with timestamp corroboration",
        ...     supporting_evidence_count=3,
        ... )
    """

    level: ConfidenceLevel
    reasoning: str
    supporting_evidence_count: int

    def __post_init__(self) -> None:
        """Validate confidence invariants."""
        if self.supporting_evidence_count < 0:
            raise ValueError("Supporting evidence count must be >= 0")

    def to_numeric(self) -> float:
        """Convert categorical level to numeric score (0.0-1.0)."""
        mapping = {
            ConfidenceLevel.VERY_HIGH: 0.95,
            ConfidenceLevel.HIGH: 0.8,
            ConfidenceLevel.MEDIUM: 0.6,
            ConfidenceLevel.LOW: 0.4,
            ConfidenceLevel.VERY_LOW: 0.2,
        }
        return mapping[self.level]

    def is_actionable(self) -> bool:
        """Check if confidence is high enough for action (HIGH or VERY_HIGH)."""
        return self.level in (ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH)
