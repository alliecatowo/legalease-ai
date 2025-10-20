"""
Timeline value object for the Knowledge domain.

Represents a chronological sequence of events.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List
from uuid import UUID


class TimelineGranularity(str, Enum):
    """Granularity of timeline presentation."""

    YEAR = "YEAR"
    MONTH = "MONTH"
    DAY = "DAY"
    HOUR = "HOUR"
    MINUTE = "MINUTE"
    SECOND = "SECOND"


@dataclass(frozen=True)
class Timeline:
    """
    Immutable timeline value object.

    Represents a chronological sequence of events with temporal bounds.

    Attributes:
        events: Ordered list of event IDs
        start_date: Timeline start date
        end_date: Timeline end date
        granularity: Display granularity

    Example:
        >>> timeline = Timeline(
        ...     events=[event1_id, event2_id, event3_id],
        ...     start_date=datetime(2024, 1, 1),
        ...     end_date=datetime(2024, 12, 31),
        ...     granularity=TimelineGranularity.DAY,
        ... )
        >>> timeline.span_days()
        365
    """

    events: List[UUID]
    start_date: datetime
    end_date: datetime
    granularity: TimelineGranularity = TimelineGranularity.DAY

    def __post_init__(self) -> None:
        """Validate timeline invariants."""
        if self.end_date < self.start_date:
            raise ValueError("End date must be >= start date")

    def span_days(self) -> int:
        """Calculate timeline span in days."""
        return (self.end_date - self.start_date).days

    def span_hours(self) -> float:
        """Calculate timeline span in hours."""
        return (self.end_date - self.start_date).total_seconds() / 3600

    def event_count(self) -> int:
        """Get number of events in timeline."""
        return len(self.events)

    def is_single_day(self) -> bool:
        """Check if timeline spans a single day."""
        return self.span_days() == 0
