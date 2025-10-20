"""
Score value object for the Research domain.

Represents scoring information with components and methodology.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class ScoreComponent:
    """
    Immutable component of a score.

    Attributes:
        name: Component name (e.g., 'relevance', 'accuracy', 'completeness')
        value: Component score (0.0-1.0)
        weight: Weight of this component in final score (0.0-1.0)
    """

    name: str
    value: float
    weight: float

    def __post_init__(self) -> None:
        """Validate score component invariants."""
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(f"Value must be 0.0-1.0, got {self.value}")
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"Weight must be 0.0-1.0, got {self.weight}")


@dataclass(frozen=True)
class Score:
    """
    Immutable score value object.

    Represents a composite score with breakdown of components.

    Attributes:
        value: Overall score (0.0-1.0)
        method: Scoring method used (e.g., 'weighted_average', 'max', 'min')
        components: Individual score components

    Example:
        >>> score = Score(
        ...     value=0.85,
        ...     method="weighted_average",
        ...     components=[
        ...         ScoreComponent("relevance", 0.9, 0.5),
        ...         ScoreComponent("confidence", 0.8, 0.5),
        ...     ],
        ... )
        >>> score.value
        0.85
    """

    value: float
    method: str
    components: List[ScoreComponent] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate score invariants."""
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(f"Value must be 0.0-1.0, got {self.value}")

    def get_component(self, name: str) -> ScoreComponent | None:
        """Get a specific score component."""
        for component in self.components:
            if component.name == name:
                return component
        return None

    def is_high_score(self, threshold: float = 0.8) -> bool:
        """Check if score is above threshold."""
        return self.value >= threshold
