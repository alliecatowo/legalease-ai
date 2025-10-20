"""
SQLAlchemy repository implementations for Knowledge domain.

These repositories implement the abstract repository interfaces from the
domain layer, handling all database operations for knowledge graph entities.
"""

from typing import List, Optional, Set, Tuple
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.domain.knowledge.entities import Entity, Event, Relationship
from app.domain.knowledge.repositories.graph_repository import (
    EntityRepository,
    EventRepository,
    RelationshipRepository,
    GraphRepository,
)
from ..models import (
    EntityModel,
    EventModel,
    RelationshipModel,
)
from ..mappers import (
    to_domain_entity,
    to_model_entity,
    to_domain_event,
    to_model_event,
    to_domain_relationship,
    to_model_relationship,
)


class RepositoryException(Exception):
    """Base exception for repository operations."""
    pass


class SQLAlchemyEntityRepository(EntityRepository):
    """SQLAlchemy implementation of EntityRepository."""

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with async session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def get_by_id(self, id: UUID) -> Optional[Entity]:
        """Get entity by ID."""
        try:
            stmt = select(EntityModel).where(EntityModel.id == id)
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()
            return to_domain_entity(model) if model else None
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to get entity {id}: {e}") from e

    async def find_by_name(self, name: str) -> List[Entity]:
        """Find entities by name (including aliases)."""
        try:
            # Search in both name and aliases (JSONB array)
            stmt = select(EntityModel).where(
                or_(
                    EntityModel.name.ilike(f"%{name}%"),
                    EntityModel.aliases.contains([name]),
                )
            ).order_by(EntityModel.name)
            result = await self._session.execute(stmt)
            models = result.scalars().all()
            return [to_domain_entity(m) for m in models]
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to find entities by name {name}: {e}") from e

    async def find_by_type(self, entity_type: str) -> List[Entity]:
        """Find entities by type."""
        try:
            stmt = select(EntityModel).where(
                EntityModel.entity_type == entity_type
            ).order_by(EntityModel.name)
            result = await self._session.execute(stmt)
            models = result.scalars().all()
            return [to_domain_entity(m) for m in models]
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to find entities by type {entity_type}: {e}") from e

    async def find_by_case_id(self, case_id: UUID) -> List[Entity]:
        """Find all entities for a case."""
        try:
            # This would require a join with cases if we track case_id in entities
            # For now, we'll search in metadata
            stmt = select(EntityModel).where(
                EntityModel.metadata["case_id"].astext == str(case_id)
            ).order_by(EntityModel.name)
            result = await self._session.execute(stmt)
            models = result.scalars().all()
            return [to_domain_entity(m) for m in models]
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to find entities for case {case_id}: {e}") from e

    async def save(self, entity: Entity) -> Entity:
        """Save or update an entity."""
        try:
            existing = await self._session.get(EntityModel, entity.id)

            if existing:
                # Update existing
                existing.entity_type = entity.entity_type.value
                existing.name = entity.name
                existing.aliases = entity.aliases
                existing.attributes = entity.attributes
                existing.first_seen = entity.first_seen
                existing.last_seen = entity.last_seen
                existing.source_citations = [str(c) for c in entity.source_citations]
                existing.metadata = entity.metadata
                model = existing
            else:
                # Create new
                model = to_model_entity(entity)
                self._session.add(model)

            await self._session.flush()
            return to_domain_entity(model)
        except IntegrityError as e:
            raise RepositoryException(f"Integrity error saving entity: {e}") from e
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to save entity: {e}") from e

    async def delete(self, id: UUID) -> bool:
        """Delete an entity."""
        try:
            stmt = delete(EntityModel).where(EntityModel.id == id)
            result = await self._session.execute(stmt)
            await self._session.flush()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to delete entity {id}: {e}") from e


class SQLAlchemyEventRepository(EventRepository):
    """SQLAlchemy implementation of EventRepository."""

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with async session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def get_by_id(self, id: UUID) -> Optional[Event]:
        """Get event by ID."""
        try:
            stmt = select(EventModel).where(EventModel.id == id)
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()
            return to_domain_event(model) if model else None
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to get event {id}: {e}") from e

    async def find_by_time_range(
        self, start: datetime, end: datetime
    ) -> List[Event]:
        """Find events within a time range."""
        try:
            stmt = select(EventModel).where(
                and_(
                    EventModel.timestamp >= start,
                    EventModel.timestamp <= end,
                )
            ).order_by(EventModel.timestamp)
            result = await self._session.execute(stmt)
            models = result.scalars().all()
            return [to_domain_event(m) for m in models]
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to find events by time range: {e}") from e

    async def find_by_participant(self, entity_id: UUID) -> List[Event]:
        """Find events involving a participant."""
        try:
            # Search in participants JSONB array
            stmt = select(EventModel).where(
                EventModel.participants.contains([str(entity_id)])
            ).order_by(EventModel.timestamp)
            result = await self._session.execute(stmt)
            models = result.scalars().all()
            return [to_domain_event(m) for m in models]
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to find events by participant {entity_id}: {e}") from e

    async def find_by_type(self, event_type: str) -> List[Event]:
        """Find events by type."""
        try:
            stmt = select(EventModel).where(
                EventModel.event_type == event_type
            ).order_by(EventModel.timestamp)
            result = await self._session.execute(stmt)
            models = result.scalars().all()
            return [to_domain_event(m) for m in models]
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to find events by type {event_type}: {e}") from e

    async def save(self, event: Event) -> Event:
        """Save or update an event."""
        try:
            existing = await self._session.get(EventModel, event.id)

            if existing:
                # Update existing
                existing.event_type = event.event_type.value
                existing.description = event.description
                existing.participants = [str(p) for p in event.participants]
                existing.timestamp = event.timestamp
                existing.duration = event.duration
                existing.location = str(event.location) if event.location else None
                existing.source_citations = [str(c) for c in event.source_citations]
                existing.metadata = event.metadata
                model = existing
            else:
                # Create new
                model = to_model_event(event)
                self._session.add(model)

            await self._session.flush()
            return to_domain_event(model)
        except IntegrityError as e:
            raise RepositoryException(f"Integrity error saving event: {e}") from e
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to save event: {e}") from e

    async def delete(self, id: UUID) -> bool:
        """Delete an event."""
        try:
            stmt = delete(EventModel).where(EventModel.id == id)
            result = await self._session.execute(stmt)
            await self._session.flush()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to delete event {id}: {e}") from e


class SQLAlchemyRelationshipRepository(RelationshipRepository):
    """SQLAlchemy implementation of RelationshipRepository."""

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with async session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def get_by_id(self, id: UUID) -> Optional[Relationship]:
        """Get relationship by ID."""
        try:
            stmt = select(RelationshipModel).where(RelationshipModel.id == id)
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()
            return to_domain_relationship(model) if model else None
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to get relationship {id}: {e}") from e

    async def find_by_entity(self, entity_id: UUID) -> List[Relationship]:
        """Find all relationships involving an entity."""
        try:
            stmt = select(RelationshipModel).where(
                or_(
                    RelationshipModel.from_entity_id == entity_id,
                    RelationshipModel.to_entity_id == entity_id,
                )
            ).order_by(RelationshipModel.strength.desc())
            result = await self._session.execute(stmt)
            models = result.scalars().all()
            return [to_domain_relationship(m) for m in models]
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to find relationships for entity {entity_id}: {e}") from e

    async def find_by_type(self, relationship_type: str) -> List[Relationship]:
        """Find relationships by type."""
        try:
            stmt = select(RelationshipModel).where(
                RelationshipModel.relationship_type == relationship_type
            ).order_by(RelationshipModel.strength.desc())
            result = await self._session.execute(stmt)
            models = result.scalars().all()
            return [to_domain_relationship(m) for m in models]
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to find relationships by type {relationship_type}: {e}") from e

    async def find_between(
        self, from_entity_id: UUID, to_entity_id: UUID
    ) -> List[Relationship]:
        """Find relationships between two entities."""
        try:
            stmt = select(RelationshipModel).where(
                or_(
                    and_(
                        RelationshipModel.from_entity_id == from_entity_id,
                        RelationshipModel.to_entity_id == to_entity_id,
                    ),
                    and_(
                        RelationshipModel.from_entity_id == to_entity_id,
                        RelationshipModel.to_entity_id == from_entity_id,
                    ),
                )
            ).order_by(RelationshipModel.strength.desc())
            result = await self._session.execute(stmt)
            models = result.scalars().all()
            return [to_domain_relationship(m) for m in models]
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to find relationships between entities: {e}") from e

    async def save(self, relationship: Relationship) -> Relationship:
        """Save or update a relationship."""
        try:
            existing = await self._session.get(RelationshipModel, relationship.id)

            if existing:
                # Update existing
                existing.from_entity_id = relationship.from_entity_id
                existing.to_entity_id = relationship.to_entity_id
                existing.relationship_type = relationship.relationship_type.value
                existing.strength = relationship.strength
                existing.temporal_start = relationship.temporal_start
                existing.temporal_end = relationship.temporal_end
                existing.source_citations = [str(c) for c in relationship.source_citations]
                existing.metadata = relationship.metadata
                model = existing
            else:
                # Create new
                model = to_model_relationship(relationship)
                self._session.add(model)

            await self._session.flush()
            return to_domain_relationship(model)
        except IntegrityError as e:
            raise RepositoryException(f"Integrity error saving relationship: {e}") from e
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to save relationship: {e}") from e

    async def delete(self, id: UUID) -> bool:
        """Delete a relationship."""
        try:
            stmt = delete(RelationshipModel).where(RelationshipModel.id == id)
            result = await self._session.execute(stmt)
            await self._session.flush()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            raise RepositoryException(f"Failed to delete relationship {id}: {e}") from e


class SQLAlchemyGraphRepository(GraphRepository):
    """
    SQLAlchemy implementation of GraphRepository.

    Provides high-level graph operations that span multiple entity types.
    """

    def __init__(
        self,
        session: AsyncSession,
        entity_repo: SQLAlchemyEntityRepository,
        event_repo: SQLAlchemyEventRepository,
        relationship_repo: SQLAlchemyRelationshipRepository,
    ):
        """
        Initialize graph repository with async session and sub-repositories.

        Args:
            session: SQLAlchemy async session
            entity_repo: Entity repository
            event_repo: Event repository
            relationship_repo: Relationship repository
        """
        self._session = session
        self._entity_repo = entity_repo
        self._event_repo = event_repo
        self._relationship_repo = relationship_repo

    async def get_entity_with_relationships(
        self, entity_id: UUID
    ) -> Tuple[Optional[Entity], List[Relationship]]:
        """
        Get an entity with all its relationships.

        Args:
            entity_id: Entity ID

        Returns:
            Tuple of (entity, relationships)
        """
        try:
            entity = await self._entity_repo.get_by_id(entity_id)
            relationships = await self._relationship_repo.find_by_entity(entity_id)
            return (entity, relationships)
        except RepositoryException:
            raise
        except Exception as e:
            raise RepositoryException(f"Failed to get entity with relationships: {e}") from e

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
        try:
            visited: Set[UUID] = set()
            entities: Set[Entity] = set()
            queue: List[Tuple[UUID, int]] = [(entity_id, 0)]

            while queue:
                current_id, depth = queue.pop(0)

                if current_id in visited or depth > max_depth:
                    continue

                visited.add(current_id)

                # Get entity
                entity = await self._entity_repo.get_by_id(current_id)
                if entity:
                    entities.add(entity)

                # Get relationships and add connected entities to queue
                if depth < max_depth:
                    relationships = await self._relationship_repo.find_by_entity(current_id)
                    for rel in relationships:
                        # Add the other entity in the relationship
                        other_id = (
                            rel.to_entity_id
                            if rel.from_entity_id == current_id
                            else rel.from_entity_id
                        )
                        if other_id not in visited:
                            queue.append((other_id, depth + 1))

            return entities
        except RepositoryException:
            raise
        except Exception as e:
            raise RepositoryException(f"Failed to get connected entities: {e}") from e

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
        try:
            # BFS to find shortest path
            visited: Set[UUID] = set()
            queue: List[Tuple[UUID, List[Relationship]]] = [(from_entity_id, [])]

            while queue:
                current_id, path = queue.pop(0)

                if current_id == to_entity_id:
                    return path

                if current_id in visited:
                    continue

                visited.add(current_id)

                # Get relationships
                relationships = await self._relationship_repo.find_by_entity(current_id)
                for rel in relationships:
                    # Get the other entity
                    other_id = (
                        rel.to_entity_id
                        if rel.from_entity_id == current_id
                        else rel.from_entity_id
                    )

                    if other_id not in visited:
                        queue.append((other_id, path + [rel]))

            return None
        except RepositoryException:
            raise
        except Exception as e:
            raise RepositoryException(f"Failed to find shortest path: {e}") from e

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
        try:
            return await self._event_repo.find_by_participant(entity_id)
        except RepositoryException:
            raise
        except Exception as e:
            raise RepositoryException(f"Failed to get timeline for entity: {e}") from e

    async def get_subgraph(
        self, entity_ids: List[UUID]
    ) -> Tuple[List[Entity], List[Relationship]]:
        """
        Extract a subgraph containing specified entities and their interconnections.

        Args:
            entity_ids: List of entity IDs to include

        Returns:
            Tuple of (entities, relationships)
        """
        try:
            # Get all entities
            entities = []
            for entity_id in entity_ids:
                entity = await self._entity_repo.get_by_id(entity_id)
                if entity:
                    entities.append(entity)

            # Get all relationships between these entities
            entity_id_set = set(entity_ids)
            relationships = []

            for entity_id in entity_ids:
                rels = await self._relationship_repo.find_by_entity(entity_id)
                for rel in rels:
                    # Only include if both entities are in our set
                    if (
                        rel.from_entity_id in entity_id_set
                        and rel.to_entity_id in entity_id_set
                        and rel not in relationships
                    ):
                        relationships.append(rel)

            return (entities, relationships)
        except RepositoryException:
            raise
        except Exception as e:
            raise RepositoryException(f"Failed to get subgraph: {e}") from e
