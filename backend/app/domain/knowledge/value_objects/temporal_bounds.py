"""
TemporalBounds value object for the Knowledge domain.

Represents temporal boundaries with precision and approximation indicators.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class TemporalPrecision(str, Enum):
    """Precision level of temporal information."""

    EXACT = "EXACT"  # Precise to the second
    MINUTE = "MINUTE"  # Precise to the minute
    HOUR = "HOUR"  # Precise to the hour
    DAY = "DAY"  # Precise to the day
    MONTH = "MONTH"  # Precise to the month
    YEAR = "YEAR"  # Precise to the year
    APPROXIMATE = "APPROXIMATE"  # Rough estimate


@dataclass(frozen=True)
class TemporalBounds:
    """
    Immutable temporal bounds value object.

    Represents a time range with precision and approximation indicators.

    Attributes:
        start: Start datetime
        end: Optional end datetime
        precision: Precision level
        is_approximate: Whether bounds are approximate

    Example:
        >>> bounds = TemporalBounds(
        ...     start=datetime(2024, 3, 1),
        ...     end=datetime(2024, 3, 31),
        ...     precision=TemporalPrecision.DAY,
        ...     is_approximate=False,
        ... )
        >>> bounds.duration_days()
        30
    """

    start: datetime
    end: Optional[datetime] = None
    precision: TemporalPrecision = TemporalPrecision.EXACT
    is_approximate: bool = False

    def __post_init__(self) -> None:
        """Validate temporal bounds invariants."""
        if self.end and self.end < self.start:
            raise ValueError("End must be >= start")

    def duration_seconds(self) -> Optional[float]:
        """Calculate duration in seconds."""
        if self.end:
            return (self.end - self.start).total_seconds()
        return None

    def duration_days(self) -> Optional[int]:
        """Calculate duration in days."""
        if self.end:
            return (self.end - self.start).days
        return None

    def is_instant(self) -> bool:
        """Check if bounds represent an instant (no duration)."""
        return self.end is None or self.end == self.start

    def contains(self, timestamp: datetime) -> bool:
        """
        Check if timestamp falls within bounds.

        Args:
            timestamp: Timestamp to check

        Returns:
            True if timestamp is within bounds
        """
        if timestamp < self.start:
            return False
        if self.end and timestamp > self.end:
            return False
        return True

    def overlaps(self, other: "TemporalBounds") -> bool:
        """
        Check if bounds overlap with another temporal bounds.

        Args:
            other: Other temporal bounds to check

        Returns:
            True if bounds overlap
        """
        if self.end and other.start > self.end:
            return False
        if other.end and self.start > other.end:
            return False
        return True
