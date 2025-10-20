"""
Repository interfaces for Knowledge domain.

Abstract interfaces for knowledge graph persistence following hexagonal architecture.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Set
from uuid import UUID
from datetime import datetime

from ..entities import Entity, Event, Relationship


class EntityRepository(ABC):
    """Repository interface for Entity entities."""

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[Entity]:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def find_by_name(self, name: str) -> List[Entity]:
        """Find entities by name (including aliases)."""
        pass

    @abstractmethod
    async def find_by_type(self, entity_type: str) -> List[Entity]:
        """Find entities by type."""
        pass

    @abstractmethod
    async def find_by_case_id(self, case_id: UUID) -> List[Entity]:
        """Find all entities for a case."""
        pass

    @abstractmethod
    async def save(self, entity: Entity) -> Entity:
        """Save or update an entity."""
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete an entity."""
        pass


class EventRepository(ABC):
    """Repository interface for Event entities."""

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[Event]:
        """Get event by ID."""
        pass

    @abstractmethod
    async def find_by_time_range(
        self, start: datetime, end: datetime
    ) -> List[Event]:
        """Find events within a time range."""
        pass

    @abstractmethod
    async def find_by_participant(self, entity_id: UUID) -> List[Event]:
        """Find events involving a participant."""
        pass

    @abstractmethod
    async def find_by_type(self, event_type: str) -> List[Event]:
        """Find events by type."""
        pass

    @abstractmethod
    async def save(self, event: Event) -> Event:
        """Save or update an event."""
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete an event."""
        pass


class RelationshipRepository(ABC):
    """Repository interface for Relationship entities."""

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[Relationship]:
        """Get relationship by ID."""
        pass

    @abstractmethod
    async def find_by_entity(self, entity_id: UUID) -> List[Relationship]:
        """Find all relationships involving an entity."""
        pass

    @abstractmethod
    async def find_by_type(self, relationship_type: str) -> List[Relationship]:
        """Find relationships by type."""
        pass

    @abstractmethod
    async def find_between(
        self, from_entity_id: UUID, to_entity_id: UUID
    ) -> List[Relationship]:
        """Find relationships between two entities."""
        pass

    @abstractmethod
    async def save(self, relationship: Relationship) -> Relationship:
        """Save or update a relationship."""
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete a relationship."""
        pass


class GraphRepository(ABC):
    """
    High-level repository interface for graph operations.

    Provides operations that span multiple entity types for complex queries.
    """

    @abstractmethod
    async def get_entity_with_relationships(
        self, entity_id: UUID
    ) -> tuple[Optional[Entity], List[Relationship]]:
        """
        Get an entity with all its relationships.

        Args:
            entity_id: Entity ID

        Returns:
            Tuple of (entity, relationships)
        """
        pass

    @abstractmethod
    async def get_connected_entities(
        self, entity_id: UUID, max_depth: int = 2
    ) -> Set[Entity]:
        """
        Get all entities connected to an entity within max_depth hops.

        Args:
            entity_id: Starting entity ID
            max_depth: Maximum relationship depth to traverse

        Returns:
            Set of connected entities
        """
        pass

    @abstractmethod
    async def find_shortest_path(
        self, from_entity_id: UUID, to_entity_id: UUID
    ) -> Optional[List[Relationship]]:
        """
        Find shortest path between two entities.

        Args:
            from_entity_id: Start entity ID
            to_entity_id: End entity ID

        Returns:
            List of relationships forming the path, or None if no path exists
        """
        pass

    @abstractmethod
    async def get_timeline_for_entity(
        self, entity_id: UUID
    ) -> List[Event]:
        """
        Get chronological timeline of events for an entity.

        Args:
            entity_id: Entity ID

        Returns:
            Ordered list of events involving the entity
        """
        pass

    @abstractmethod
    async def get_subgraph(
        self, entity_ids: List[UUID]
    ) -> tuple[List[Entity], List[Relationship]]:
        """
        Extract a subgraph containing specified entities and their interconnections.

        Args:
            entity_ids: List of entity IDs to include

        Returns:
            Tuple of (entities, relationships)
        """
        pass
