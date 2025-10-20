"""
Neo4j implementation of EventRepository.

This module provides event persistence operations using Neo4j graph database,
including temporal queries and participant relationships.
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from app.domain.knowledge.entities import Event
from app.domain.knowledge.entities.event import EventType
from app.domain.knowledge.repositories.graph_repository import EventRepository
from app.shared.exceptions.domain_exceptions import RepositoryException

from ..client import Neo4jClient
from ..mappers import EventMapper
from ..query_builder import CypherQueryBuilder, OrderDirection

logger = logging.getLogger(__name__)


class Neo4jEventRepository(EventRepository):
    """
    Neo4j implementation of EventRepository.

    Provides CRUD operations and temporal queries for Event entities.
    Events are stored as nodes with PARTICIPATED_IN relationships to Entity nodes.
    """

    def __init__(self, client: Neo4jClient):
        """
        Initialize event repository.

        Args:
            client: Neo4jClient instance
        """
        self.client = client
        self.mapper = EventMapper()

    async def save(self, event: Event) -> Event:
        """
        Save or update an event.

        Creates event node and PARTICIPATED_IN relationships to participant entities.

        Args:
            event: Event to save

        Returns:
            Saved event

        Raises:
            RepositoryException: If save fails
        """
        try:
            props = self.mapper.to_node_properties(event)

            # Create/update event node and participant relationships
            query = """
            MERGE (e:Event {id: $id})
            SET e.event_type = $event_type,
                e.description = $description,
                e.timestamp = $timestamp,
                e.source_citations = $source_citations,
                e.metadata = $metadata,
                e.participants = $participants
            """

            # Add optional properties
            if "location" in props:
                query += ", e.location = $location"
            if "duration" in props:
                query += ", e.duration = $duration"

            # Create participant relationships
            query += """
            WITH e
            UNWIND $participants as participant_id
            MATCH (entity:Entity {id: participant_id})
            MERGE (entity)-[:PARTICIPATED_IN]->(e)
            RETURN e
            """

            result = await self.client.execute_write(query, props)

            if not result:
                raise RepositoryException(
                    "Failed to save event: no result returned",
                    context={"event_id": str(event.id)}
                )

            logger.debug(
                f"Saved event: {event.id} with {len(event.participants)} participants"
            )
            return event

        except Exception as e:
            logger.error(f"Failed to save event {event.id}: {e}")
            raise RepositoryException(
                f"Failed to save event",
                context={"event_id": str(event.id)},
                original_exception=e,
            )

    async def get_by_id(self, id: UUID) -> Optional[Event]:
        """
        Get event by ID.

        Args:
            id: Event UUID

        Returns:
            Event if found, None otherwise

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = (
                CypherQueryBuilder()
                .match("(e:Event)")
                .where("e.id = $id")
                .return_("e")
                .build()
            )

            params = {"id": str(id)}
            result = await self.client.execute_read(query, params)

            if not result:
                return None

            event_data = result[0]["e"]
            return self.mapper.from_dict(event_data)

        except Exception as e:
            logger.error(f"Failed to get event {id}: {e}")
            raise RepositoryException(
                f"Failed to get event by ID",
                context={"event_id": str(id)},
                original_exception=e,
            )

    async def find_by_time_range(
        self,
        start: datetime,
        end: datetime
    ) -> List[Event]:
        """
        Find events within a time range.

        Args:
            start: Start datetime (inclusive)
            end: End datetime (inclusive)

        Returns:
            List of events in the time range, ordered by timestamp

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = """
            MATCH (e:Event)
            WHERE datetime(e.timestamp) >= datetime($start)
              AND datetime(e.timestamp) <= datetime($end)
            RETURN e
            ORDER BY e.timestamp ASC
            """

            params = {
                "start": start.isoformat(),
                "end": end.isoformat(),
            }

            result = await self.client.execute_read(query, params)

            events = []
            for record in result:
                event_data = record["e"]
                events.append(self.mapper.from_dict(event_data))

            logger.debug(
                f"Found {len(events)} events between {start} and {end}"
            )
            return events

        except Exception as e:
            logger.error(f"Failed to find events in time range: {e}")
            raise RepositoryException(
                f"Failed to find events by time range",
                context={"start": start.isoformat(), "end": end.isoformat()},
                original_exception=e,
            )

    async def find_by_participant(self, entity_id: UUID) -> List[Event]:
        """
        Find events involving a participant.

        Args:
            entity_id: Entity UUID of the participant

        Returns:
            List of events involving the entity, ordered by timestamp

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = """
            MATCH (entity:Entity {id: $entity_id})-[:PARTICIPATED_IN]->(e:Event)
            RETURN e
            ORDER BY e.timestamp ASC
            """

            params = {"entity_id": str(entity_id)}
            result = await self.client.execute_read(query, params)

            events = []
            for record in result:
                event_data = record["e"]
                events.append(self.mapper.from_dict(event_data))

            logger.debug(
                f"Found {len(events)} events for participant {entity_id}"
            )
            return events

        except Exception as e:
            logger.error(f"Failed to find events for participant {entity_id}: {e}")
            raise RepositoryException(
                f"Failed to find events by participant",
                context={"entity_id": str(entity_id)},
                original_exception=e,
            )

    async def find_by_type(self, event_type: str) -> List[Event]:
        """
        Find events by type.

        Args:
            event_type: Event type to filter by

        Returns:
            List of events of the specified type, ordered by timestamp

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = (
                CypherQueryBuilder()
                .match("(e:Event)")
                .where("e.event_type = $event_type")
                .return_("e")
                .order_by("e.timestamp", OrderDirection.ASC)
                .build()
            )

            params = {"event_type": event_type}
            result = await self.client.execute_read(query, params)

            events = []
            for record in result:
                event_data = record["e"]
                events.append(self.mapper.from_dict(event_data))

            logger.debug(f"Found {len(events)} events of type '{event_type}'")
            return events

        except Exception as e:
            logger.error(f"Failed to find events by type '{event_type}': {e}")
            raise RepositoryException(
                f"Failed to find events by type",
                context={"event_type": event_type},
                original_exception=e,
            )

    async def delete(self, id: UUID) -> bool:
        """
        Delete an event.

        Note: This uses DETACH DELETE to also remove all relationships.

        Args:
            id: Event UUID

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryException: If delete fails
        """
        try:
            query = """
            MATCH (e:Event {id: $id})
            DETACH DELETE e
            RETURN count(e) as deleted_count
            """

            params = {"id": str(id)}
            result = await self.client.execute_write(query, params)

            deleted_count = result[0]["deleted_count"] if result else 0
            success = deleted_count > 0

            if success:
                logger.debug(f"Deleted event: {id}")
            else:
                logger.debug(f"Event not found for deletion: {id}")

            return success

        except Exception as e:
            logger.error(f"Failed to delete event {id}: {e}")
            raise RepositoryException(
                f"Failed to delete event",
                context={"event_id": str(id)},
                original_exception=e,
            )

    async def find_by_case_id(self, case_id: UUID) -> List[Event]:
        """
        Find all events for a case.

        Note: This requires events to have a case_id in metadata.

        Args:
            case_id: Case UUID

        Returns:
            List of events for the case, ordered by timestamp

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = """
            MATCH (e:Event)
            WHERE e.metadata.case_id = $case_id
            RETURN e
            ORDER BY e.timestamp ASC
            """

            params = {"case_id": str(case_id)}
            result = await self.client.execute_read(query, params)

            events = []
            for record in result:
                event_data = record["e"]
                events.append(self.mapper.from_dict(event_data))

            logger.debug(f"Found {len(events)} events for case {case_id}")
            return events

        except Exception as e:
            logger.error(f"Failed to find events for case {case_id}: {e}")
            raise RepositoryException(
                f"Failed to find events by case ID",
                context={"case_id": str(case_id)},
                original_exception=e,
            )

    async def find_event_sequence(self, entity_id: UUID) -> List[Event]:
        """
        Find chronological event sequence for an entity.

        Returns all events involving the entity in chronological order.

        Args:
            entity_id: Entity UUID

        Returns:
            List of events in chronological order

        Raises:
            RepositoryException: If query fails
        """
        try:
            # Same as find_by_participant, but explicitly ordered
            return await self.find_by_participant(entity_id)

        except Exception as e:
            logger.error(f"Failed to find event sequence for {entity_id}: {e}")
            raise RepositoryException(
                f"Failed to find event sequence",
                context={"entity_id": str(entity_id)},
                original_exception=e,
            )

    async def find_co_participants(
        self,
        entity_id: UUID,
        limit: int = 50
    ) -> List[tuple[UUID, int]]:
        """
        Find entities that frequently participate in events with the given entity.

        Args:
            entity_id: Entity UUID
            limit: Maximum results to return

        Returns:
            List of tuples (entity_id, co_occurrence_count) ordered by count desc

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = """
            MATCH (entity:Entity {id: $entity_id})-[:PARTICIPATED_IN]->(e:Event)<-[:PARTICIPATED_IN]-(other:Entity)
            WHERE entity <> other
            RETURN other.id as co_participant_id, count(e) as event_count
            ORDER BY event_count DESC
            LIMIT $limit
            """

            params = {"entity_id": str(entity_id), "limit": limit}
            result = await self.client.execute_read(query, params)

            co_participants = [
                (UUID(record["co_participant_id"]), record["event_count"])
                for record in result
            ]

            logger.debug(
                f"Found {len(co_participants)} co-participants for {entity_id}"
            )
            return co_participants

        except Exception as e:
            logger.error(f"Failed to find co-participants for {entity_id}: {e}")
            raise RepositoryException(
                f"Failed to find co-participants",
                context={"entity_id": str(entity_id)},
                original_exception=e,
            )

    async def find_events_between_entities(
        self,
        entity_id1: UUID,
        entity_id2: UUID
    ) -> List[Event]:
        """
        Find events where both entities participated.

        Args:
            entity_id1: First entity UUID
            entity_id2: Second entity UUID

        Returns:
            List of events involving both entities, ordered by timestamp

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = """
            MATCH (e1:Entity {id: $entity_id1})-[:PARTICIPATED_IN]->(event:Event)<-[:PARTICIPATED_IN]-(e2:Entity {id: $entity_id2})
            RETURN event as e
            ORDER BY event.timestamp ASC
            """

            params = {
                "entity_id1": str(entity_id1),
                "entity_id2": str(entity_id2),
            }

            result = await self.client.execute_read(query, params)

            events = []
            for record in result:
                event_data = record["e"]
                events.append(self.mapper.from_dict(event_data))

            logger.debug(
                f"Found {len(events)} events between {entity_id1} and {entity_id2}"
            )
            return events

        except Exception as e:
            logger.error(
                f"Failed to find events between {entity_id1} and {entity_id2}: {e}"
            )
            raise RepositoryException(
                f"Failed to find events between entities",
                context={
                    "entity_id1": str(entity_id1),
                    "entity_id2": str(entity_id2),
                },
                original_exception=e,
            )

    async def search(
        self,
        query: str,
        event_types: Optional[List[EventType]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Event]:
        """
        Search events by description with optional filters.

        Args:
            query: Search query string
            event_types: Optional list of event types to filter by
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum results to return

        Returns:
            List of matching events ordered by timestamp

        Raises:
            RepositoryException: If search fails
        """
        try:
            cypher_builder = CypherQueryBuilder().match("(e:Event)")

            # Text search on description
            cypher_builder.where("toLower(e.description) CONTAINS toLower($query)")

            # Type filter
            if event_types:
                cypher_builder.where_in("e.event_type", "event_types")

            # Date range filter
            if start_date:
                cypher_builder.where("datetime(e.timestamp) >= datetime($start_date)")
            if end_date:
                cypher_builder.where("datetime(e.timestamp) <= datetime($end_date)")

            cypher = (
                cypher_builder
                .return_("e")
                .order_by("e.timestamp", OrderDirection.ASC)
                .limit(limit)
                .build()
            )

            params = {"query": query}
            if event_types:
                params["event_types"] = [t.value for t in event_types]
            if start_date:
                params["start_date"] = start_date.isoformat()
            if end_date:
                params["end_date"] = end_date.isoformat()

            result = await self.client.execute_read(cypher, params)

            events = []
            for record in result:
                event_data = record["e"]
                events.append(self.mapper.from_dict(event_data))

            logger.debug(f"Search '{query}' found {len(events)} events")
            return events

        except Exception as e:
            logger.error(f"Event search failed for query '{query}': {e}")
            raise RepositoryException(
                f"Event search failed",
                context={"query": query},
                original_exception=e,
            )
