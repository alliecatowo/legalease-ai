"""
GetTimelineQuery for retrieving chronological event timeline.

This module implements CQRS query pattern for fetching timeline
of events from the knowledge graph.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.domain.knowledge.repositories.graph_repository import GraphRepository
from app.application.queries.query_graph import EntityDTO


logger = logging.getLogger(__name__)


@dataclass
class GetTimelineQuery:
    """
    Query for retrieving chronological timeline.

    Attributes:
        case_id: Case ID to filter by
        start_date: Optional start date filter (ISO format)
        end_date: Optional end date filter (ISO format)
        entity_id: Optional entity filter (events involving entity)
        event_types: Optional event type filter
        limit: Maximum events to return

    Example:
        >>> query = GetTimelineQuery(
        ...     case_id=case_uuid,
        ...     start_date="2024-01-01",
        ...     end_date="2024-12-31",
        ... )
    """

    case_id: UUID
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    entity_id: Optional[UUID] = None
    event_types: Optional[List[str]] = None
    limit: int = 100

    def __post_init__(self) -> None:
        """Validate query parameters."""
        if self.limit < 1 or self.limit > 1000:
            raise ValueError(f"limit must be between 1 and 1000, got {self.limit}")

        # Validate date formats
        if self.start_date:
            try:
                datetime.fromisoformat(self.start_date)
            except ValueError as e:
                raise ValueError(f"Invalid start_date format: {e}")

        if self.end_date:
            try:
                datetime.fromisoformat(self.end_date)
            except ValueError as e:
                raise ValueError(f"Invalid end_date format: {e}")


@dataclass
class TimelineEventDTO:
    """
    Data Transfer Object for timeline event.

    Attributes:
        id: Event ID
        event_type: Type of event
        description: Event description
        timestamp: Event timestamp (ISO format)
        participants: List of participating entities
        location: Event location
        source_citations: Citation IDs
        metadata: Additional metadata
    """

    id: UUID
    event_type: str
    description: str
    timestamp: str
    participants: List[EntityDTO]
    location: Optional[str] = None
    source_citations: List[UUID] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GetTimelineResult:
    """
    Result of GetTimelineQuery.

    Attributes:
        events: List of timeline events (chronologically sorted)
        start_date: Actual start date of timeline
        end_date: Actual end date of timeline
        total_events: Total event count
    """

    events: List[TimelineEventDTO]
    start_date: str
    end_date: str
    total_events: int


class GetTimelineQueryHandler:
    """
    Handler for timeline queries.

    Queries the knowledge graph for events and converts to timeline DTOs.
    """

    def __init__(self, graph_repo: GraphRepository):
        """
        Initialize handler with dependencies.

        Args:
            graph_repo: Repository for graph operations
        """
        self.repo = graph_repo
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def handle(self, query: GetTimelineQuery) -> GetTimelineResult:
        """
        Execute the query and return timeline.

        Steps:
        1. Fetch events from graph based on filters
        2. Sort chronologically
        3. Convert to DTOs
        4. Return result

        Args:
            query: The query to execute

        Returns:
            GetTimelineResult with sorted events

        Raises:
            ValueError: If query is invalid
            RuntimeError: If query fails
        """
        self.logger.info(
            "Fetching timeline",
            extra={
                "case_id": query.case_id,
                "start_date": query.start_date,
                "end_date": query.end_date,
            }
        )

        try:
            # 1. Fetch events
            if query.entity_id:
                # Get timeline for specific entity
                events = await self.repo.get_timeline_for_entity(query.entity_id)
            else:
                # Get all events in time range
                # This would require a new repository method
                # For now, we'll use entity-based query
                events = []

            # 2. Apply filters
            filtered_events = self._apply_filters(events, query)

            # 3. Sort chronologically
            sorted_events = sorted(
                filtered_events,
                key=lambda e: e.timestamp
            )

            # 4. Apply limit
            limited_events = sorted_events[:query.limit]

            # 5. Convert to DTOs
            event_dtos = []
            for event in limited_events:
                dto = await self._to_dto(event)
                event_dtos.append(dto)

            # 6. Calculate date range
            if event_dtos:
                start_date = event_dtos[0].timestamp
                end_date = event_dtos[-1].timestamp
            else:
                start_date = query.start_date or ""
                end_date = query.end_date or ""

            self.logger.info(
                "Timeline retrieved successfully",
                extra={
                    "total_events": len(event_dtos),
                    "date_range": f"{start_date} to {end_date}",
                }
            )

            return GetTimelineResult(
                events=event_dtos,
                start_date=start_date,
                end_date=end_date,
                total_events=len(filtered_events),
            )

        except Exception as e:
            self.logger.error(
                f"Failed to retrieve timeline: {e}",
                extra={"case_id": query.case_id},
                exc_info=True
            )
            raise RuntimeError(f"Failed to retrieve timeline: {e}") from e

    def _apply_filters(self, events: List[Any], query: GetTimelineQuery) -> List[Any]:
        """Apply filters to events list."""
        filtered = events

        # Filter by date range
        if query.start_date:
            start_dt = datetime.fromisoformat(query.start_date)
            filtered = [e for e in filtered if e.timestamp >= start_dt]

        if query.end_date:
            end_dt = datetime.fromisoformat(query.end_date)
            filtered = [e for e in filtered if e.timestamp <= end_dt]

        # Filter by event type
        if query.event_types:
            filtered = [
                e for e in filtered
                if e.event_type.value in query.event_types
            ]

        return filtered

    async def _to_dto(self, event: Any) -> TimelineEventDTO:
        """
        Convert domain Event entity to DTO.

        Args:
            event: Domain event entity

        Returns:
            TimelineEventDTO
        """
        # Fetch participant entities
        participant_dtos = []
        # TODO: Implement batch entity fetching for participants
        # For now, create placeholder DTOs
        for participant_id in event.participants:
            # In real implementation, would fetch entity details
            participant_dtos.append(
                EntityDTO(
                    id=participant_id,
                    entity_type="PERSON",  # Would be fetched from DB
                    name="",  # Would be fetched from DB
                    aliases=[],
                    attributes={},
                    confidence=1.0,
                    first_seen="",
                    last_seen="",
                    citation_count=0,
                )
            )

        return TimelineEventDTO(
            id=event.id,
            event_type=event.event_type.value,
            description=event.description,
            timestamp=event.timestamp.isoformat() if event.timestamp else "",
            participants=participant_dtos,
            location=str(event.location) if event.location else None,
            source_citations=event.source_citations.copy(),
            metadata=event.metadata.copy() if event.metadata else {},
        )
