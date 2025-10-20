"""
Mappers for converting between Neo4j nodes/relationships and domain objects.

This module handles the conversion between:
- Neo4j Node <-> Entity
- Neo4j Node <-> Event
- Neo4j Relationship <-> Relationship
- Value objects (Timeline, TemporalBounds)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from neo4j.graph import Node, Relationship as Neo4jRelationship

from app.domain.knowledge.entities import Entity, Event, Relationship
from app.domain.knowledge.entities.entity import EntityType
from app.domain.knowledge.entities.event import EventType
from app.domain.knowledge.entities.relationship import RelationshipType
from app.domain.knowledge.value_objects.timeline import Timeline, TimelineGranularity
from app.domain.knowledge.value_objects.temporal_bounds import (
    TemporalBounds,
    TemporalPrecision,
)


class EntityMapper:
    """Mapper for Entity domain objects and Neo4j nodes."""

    @staticmethod
    def to_node_properties(entity: Entity) -> Dict[str, Any]:
        """
        Convert Entity to Neo4j node properties.

        Args:
            entity: Entity domain object

        Returns:
            Dictionary of node properties

        Example:
            >>> props = EntityMapper.to_node_properties(entity)
            >>> # Use in Cypher: CREATE (e:Entity $props)
        """
        return {
            "id": str(entity.id),
            "entity_type": entity.entity_type.value,
            "name": entity.name,
            "aliases": entity.aliases,
            "attributes": entity.attributes,
            "first_seen": entity.first_seen.isoformat(),
            "last_seen": entity.last_seen.isoformat(),
            "source_citations": [str(cit) for cit in entity.source_citations],
            "metadata": entity.metadata,
        }

    @staticmethod
    def from_node(node: Node) -> Entity:
        """
        Convert Neo4j node to Entity domain object.

        Args:
            node: Neo4j Node object

        Returns:
            Entity domain object

        Raises:
            ValueError: If node has invalid data
        """
        props = dict(node.items())

        return Entity(
            id=UUID(props["id"]),
            entity_type=EntityType(props["entity_type"]),
            name=props["name"],
            aliases=props.get("aliases", []),
            attributes=props.get("attributes", {}),
            first_seen=datetime.fromisoformat(props["first_seen"]),
            last_seen=datetime.fromisoformat(props["last_seen"]),
            source_citations=[UUID(cit) for cit in props.get("source_citations", [])],
            metadata=props.get("metadata", {}),
        )

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Entity:
        """
        Convert dictionary (from query result) to Entity.

        Args:
            data: Dictionary with entity data

        Returns:
            Entity domain object
        """
        return Entity(
            id=UUID(data["id"]),
            entity_type=EntityType(data["entity_type"]),
            name=data["name"],
            aliases=data.get("aliases", []),
            attributes=data.get("attributes", {}),
            first_seen=datetime.fromisoformat(data["first_seen"]),
            last_seen=datetime.fromisoformat(data["last_seen"]),
            source_citations=[UUID(cit) for cit in data.get("source_citations", [])],
            metadata=data.get("metadata", {}),
        )


class EventMapper:
    """Mapper for Event domain objects and Neo4j nodes."""

    @staticmethod
    def to_node_properties(event: Event) -> Dict[str, Any]:
        """
        Convert Event to Neo4j node properties.

        Args:
            event: Event domain object

        Returns:
            Dictionary of node properties
        """
        props = {
            "id": str(event.id),
            "event_type": event.event_type.value,
            "description": event.description,
            "participants": [str(p) for p in event.participants],
            "timestamp": event.timestamp.isoformat(),
            "source_citations": [str(cit) for cit in event.source_citations],
            "metadata": event.metadata,
        }

        if event.location:
            props["location"] = str(event.location) if isinstance(event.location, UUID) else event.location

        if event.duration:
            props["duration"] = event.duration

        return props

    @staticmethod
    def from_node(node: Node) -> Event:
        """
        Convert Neo4j node to Event domain object.

        Args:
            node: Neo4j Node object

        Returns:
            Event domain object

        Raises:
            ValueError: If node has invalid data
        """
        props = dict(node.items())

        location = props.get("location")
        if location:
            try:
                location = UUID(location)
            except (ValueError, AttributeError):
                # Keep as string if not a valid UUID
                pass

        return Event(
            id=UUID(props["id"]),
            event_type=EventType(props["event_type"]),
            description=props["description"],
            participants=[UUID(p) for p in props.get("participants", [])],
            timestamp=datetime.fromisoformat(props["timestamp"]),
            source_citations=[UUID(cit) for cit in props.get("source_citations", [])],
            location=location,
            duration=props.get("duration"),
            metadata=props.get("metadata", {}),
        )

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Event:
        """
        Convert dictionary (from query result) to Event.

        Args:
            data: Dictionary with event data

        Returns:
            Event domain object
        """
        location = data.get("location")
        if location:
            try:
                location = UUID(location)
            except (ValueError, AttributeError):
                pass

        return Event(
            id=UUID(data["id"]),
            event_type=EventType(data["event_type"]),
            description=data["description"],
            participants=[UUID(p) for p in data.get("participants", [])],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source_citations=[UUID(cit) for cit in data.get("source_citations", [])],
            location=location,
            duration=data.get("duration"),
            metadata=data.get("metadata", {}),
        )


class RelationshipMapper:
    """Mapper for Relationship domain objects and Neo4j relationships."""

    @staticmethod
    def to_edge_properties(relationship: Relationship) -> Dict[str, Any]:
        """
        Convert Relationship to Neo4j edge properties.

        Args:
            relationship: Relationship domain object

        Returns:
            Dictionary of edge properties
        """
        props = {
            "id": str(relationship.id),
            "relationship_type": relationship.relationship_type.value,
            "strength": relationship.strength,
            "source_citations": [str(cit) for cit in relationship.source_citations],
            "metadata": relationship.metadata,
        }

        if relationship.temporal_start:
            props["temporal_start"] = relationship.temporal_start.isoformat()

        if relationship.temporal_end:
            props["temporal_end"] = relationship.temporal_end.isoformat()

        return props

    @staticmethod
    def from_neo4j_relationship(rel: Neo4jRelationship) -> Relationship:
        """
        Convert Neo4j relationship to Relationship domain object.

        Args:
            rel: Neo4j Relationship object

        Returns:
            Relationship domain object

        Raises:
            ValueError: If relationship has invalid data
        """
        props = dict(rel.items())

        temporal_start = None
        if "temporal_start" in props:
            temporal_start = datetime.fromisoformat(props["temporal_start"])

        temporal_end = None
        if "temporal_end" in props:
            temporal_end = datetime.fromisoformat(props["temporal_end"])

        return Relationship(
            id=UUID(props["id"]),
            from_entity_id=UUID(str(rel.start_node.id)),  # Use Neo4j internal ID
            to_entity_id=UUID(str(rel.end_node.id)),      # Use Neo4j internal ID
            relationship_type=RelationshipType(props["relationship_type"]),
            strength=props["strength"],
            source_citations=[UUID(cit) for cit in props.get("source_citations", [])],
            temporal_start=temporal_start,
            temporal_end=temporal_end,
            metadata=props.get("metadata", {}),
        )

    @staticmethod
    def from_dict(
        data: Dict[str, Any],
        from_entity_id: UUID,
        to_entity_id: UUID
    ) -> Relationship:
        """
        Convert dictionary (from query result) to Relationship.

        Args:
            data: Dictionary with relationship data
            from_entity_id: Source entity UUID
            to_entity_id: Target entity UUID

        Returns:
            Relationship domain object
        """
        temporal_start = None
        if "temporal_start" in data:
            temporal_start = datetime.fromisoformat(data["temporal_start"])

        temporal_end = None
        if "temporal_end" in data:
            temporal_end = datetime.fromisoformat(data["temporal_end"])

        return Relationship(
            id=UUID(data["id"]),
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            relationship_type=RelationshipType(data["relationship_type"]),
            strength=data["strength"],
            source_citations=[UUID(cit) for cit in data.get("source_citations", [])],
            temporal_start=temporal_start,
            temporal_end=temporal_end,
            metadata=data.get("metadata", {}),
        )


class TimelineMapper:
    """Mapper for Timeline value objects."""

    @staticmethod
    def to_dict(timeline: Timeline) -> Dict[str, Any]:
        """
        Convert Timeline to dictionary for storage.

        Args:
            timeline: Timeline value object

        Returns:
            Dictionary representation
        """
        return {
            "events": [str(event_id) for event_id in timeline.events],
            "start_date": timeline.start_date.isoformat(),
            "end_date": timeline.end_date.isoformat(),
            "granularity": timeline.granularity.value,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Timeline:
        """
        Convert dictionary to Timeline.

        Args:
            data: Dictionary with timeline data

        Returns:
            Timeline value object
        """
        return Timeline(
            events=[UUID(event_id) for event_id in data["events"]],
            start_date=datetime.fromisoformat(data["start_date"]),
            end_date=datetime.fromisoformat(data["end_date"]),
            granularity=TimelineGranularity(data.get("granularity", "DAY")),
        )


class TemporalBoundsMapper:
    """Mapper for TemporalBounds value objects."""

    @staticmethod
    def to_dict(bounds: TemporalBounds) -> Dict[str, Any]:
        """
        Convert TemporalBounds to dictionary.

        Args:
            bounds: TemporalBounds value object

        Returns:
            Dictionary representation
        """
        result = {
            "start": bounds.start.isoformat(),
            "precision": bounds.precision.value,
            "is_approximate": bounds.is_approximate,
        }

        if bounds.end:
            result["end"] = bounds.end.isoformat()

        return result

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> TemporalBounds:
        """
        Convert dictionary to TemporalBounds.

        Args:
            data: Dictionary with temporal bounds data

        Returns:
            TemporalBounds value object
        """
        end = None
        if "end" in data and data["end"]:
            end = datetime.fromisoformat(data["end"])

        return TemporalBounds(
            start=datetime.fromisoformat(data["start"]),
            end=end,
            precision=TemporalPrecision(data.get("precision", "EXACT")),
            is_approximate=data.get("is_approximate", False),
        )


def extract_node_from_result(record: Dict[str, Any], key: str) -> Optional[Node]:
    """
    Extract a Neo4j Node from a query result record.

    Args:
        record: Query result record
        key: Key to extract node from

    Returns:
        Node object or None if not found
    """
    value = record.get(key)
    if isinstance(value, Node):
        return value
    return None


def extract_relationship_from_result(
    record: Dict[str, Any],
    key: str
) -> Optional[Neo4jRelationship]:
    """
    Extract a Neo4j Relationship from a query result record.

    Args:
        record: Query result record
        key: Key to extract relationship from

    Returns:
        Neo4jRelationship object or None if not found
    """
    value = record.get(key)
    if isinstance(value, Neo4jRelationship):
        return value
    return None
