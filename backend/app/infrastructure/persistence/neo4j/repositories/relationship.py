"""
Neo4j implementation of RelationshipRepository.

This module provides relationship persistence operations using Neo4j graph database.
Relationships are stored as edges between Entity nodes.
"""

import logging
from typing import List, Optional
from uuid import UUID

from app.domain.knowledge.entities import Relationship
from app.domain.knowledge.entities.relationship import RelationshipType
from app.domain.knowledge.repositories.graph_repository import RelationshipRepository
from app.shared.exceptions.domain_exceptions import RepositoryException

from ..client import Neo4jClient
from ..mappers import RelationshipMapper

logger = logging.getLogger(__name__)


class Neo4jRelationshipRepository(RelationshipRepository):
    """
    Neo4j implementation of RelationshipRepository.

    Provides CRUD operations for Relationship entities.
    Relationships are stored as Neo4j edges with properties.
    """

    def __init__(self, client: Neo4jClient):
        """
        Initialize relationship repository.

        Args:
            client: Neo4jClient instance
        """
        self.client = client
        self.mapper = RelationshipMapper()

    async def save(self, relationship: Relationship) -> Relationship:
        """
        Save or update a relationship.

        Creates a relationship edge between two entities.

        Args:
            relationship: Relationship to save

        Returns:
            Saved relationship

        Raises:
            RepositoryException: If save fails
        """
        try:
            props = self.mapper.to_edge_properties(relationship)

            # Use the relationship type from the relationship object
            rel_type = relationship.relationship_type.value

            query = f"""
            MATCH (from:Entity {{id: $from_entity_id}})
            MATCH (to:Entity {{id: $to_entity_id}})
            MERGE (from)-[r:{rel_type}]->(to)
            SET r.id = $id,
                r.relationship_type = $relationship_type,
                r.strength = $strength,
                r.source_citations = $source_citations,
                r.metadata = $metadata
            """

            # Add optional temporal properties
            if "temporal_start" in props:
                query += ", r.temporal_start = $temporal_start"
            if "temporal_end" in props:
                query += ", r.temporal_end = $temporal_end"

            query += "\nRETURN r"

            params = {
                **props,
                "from_entity_id": str(relationship.from_entity_id),
                "to_entity_id": str(relationship.to_entity_id),
            }

            result = await self.client.execute_write(query, params)

            if not result:
                raise RepositoryException(
                    "Failed to save relationship: no result returned",
                    context={"relationship_id": str(relationship.id)}
                )

            logger.debug(
                f"Saved relationship: {relationship.id} "
                f"({relationship.from_entity_id} -> {relationship.to_entity_id})"
            )
            return relationship

        except Exception as e:
            logger.error(f"Failed to save relationship {relationship.id}: {e}")
            raise RepositoryException(
                f"Failed to save relationship",
                context={"relationship_id": str(relationship.id)},
                original_exception=e,
            )

    async def get_by_id(self, id: UUID) -> Optional[Relationship]:
        """
        Get relationship by ID.

        Args:
            id: Relationship UUID

        Returns:
            Relationship if found, None otherwise

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = """
            MATCH (from:Entity)-[r]->(to:Entity)
            WHERE r.id = $id
            RETURN r, from.id as from_id, to.id as to_id
            """

            params = {"id": str(id)}
            result = await self.client.execute_read(query, params)

            if not result:
                return None

            record = result[0]
            rel_data = record["r"]
            from_id = UUID(record["from_id"])
            to_id = UUID(record["to_id"])

            return self.mapper.from_dict(rel_data, from_id, to_id)

        except Exception as e:
            logger.error(f"Failed to get relationship {id}: {e}")
            raise RepositoryException(
                f"Failed to get relationship by ID",
                context={"relationship_id": str(id)},
                original_exception=e,
            )

    async def find_by_entity(self, entity_id: UUID) -> List[Relationship]:
        """
        Find all relationships involving an entity.

        Returns both incoming and outgoing relationships.

        Args:
            entity_id: Entity UUID

        Returns:
            List of relationships

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = """
            MATCH (from:Entity)-[r]->(to:Entity)
            WHERE from.id = $entity_id OR to.id = $entity_id
            RETURN r, from.id as from_id, to.id as to_id
            ORDER BY r.strength DESC
            """

            params = {"entity_id": str(entity_id)}
            result = await self.client.execute_read(query, params)

            relationships = []
            for record in result:
                rel_data = record["r"]
                from_id = UUID(record["from_id"])
                to_id = UUID(record["to_id"])
                relationships.append(self.mapper.from_dict(rel_data, from_id, to_id))

            logger.debug(
                f"Found {len(relationships)} relationships for entity {entity_id}"
            )
            return relationships

        except Exception as e:
            logger.error(f"Failed to find relationships for entity {entity_id}: {e}")
            raise RepositoryException(
                f"Failed to find relationships by entity",
                context={"entity_id": str(entity_id)},
                original_exception=e,
            )

    async def find_by_type(self, relationship_type: str) -> List[Relationship]:
        """
        Find relationships by type.

        Args:
            relationship_type: Relationship type to filter by

        Returns:
            List of relationships of the specified type

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = f"""
            MATCH (from:Entity)-[r:{relationship_type}]->(to:Entity)
            RETURN r, from.id as from_id, to.id as to_id
            ORDER BY r.strength DESC
            """

            result = await self.client.execute_read(query)

            relationships = []
            for record in result:
                rel_data = record["r"]
                from_id = UUID(record["from_id"])
                to_id = UUID(record["to_id"])
                relationships.append(self.mapper.from_dict(rel_data, from_id, to_id))

            logger.debug(
                f"Found {len(relationships)} relationships of type '{relationship_type}'"
            )
            return relationships

        except Exception as e:
            logger.error(f"Failed to find relationships by type '{relationship_type}': {e}")
            raise RepositoryException(
                f"Failed to find relationships by type",
                context={"relationship_type": relationship_type},
                original_exception=e,
            )

    async def find_between(
        self,
        from_entity_id: UUID,
        to_entity_id: UUID
    ) -> List[Relationship]:
        """
        Find relationships between two entities.

        Returns relationships in the specified direction.

        Args:
            from_entity_id: Source entity UUID
            to_entity_id: Target entity UUID

        Returns:
            List of relationships from source to target

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = """
            MATCH (from:Entity {id: $from_entity_id})-[r]->(to:Entity {id: $to_entity_id})
            RETURN r, from.id as from_id, to.id as to_id
            ORDER BY r.strength DESC
            """

            params = {
                "from_entity_id": str(from_entity_id),
                "to_entity_id": str(to_entity_id),
            }

            result = await self.client.execute_read(query, params)

            relationships = []
            for record in result:
                rel_data = record["r"]
                from_id = UUID(record["from_id"])
                to_id = UUID(record["to_id"])
                relationships.append(self.mapper.from_dict(rel_data, from_id, to_id))

            logger.debug(
                f"Found {len(relationships)} relationships "
                f"from {from_entity_id} to {to_entity_id}"
            )
            return relationships

        except Exception as e:
            logger.error(
                f"Failed to find relationships between "
                f"{from_entity_id} and {to_entity_id}: {e}"
            )
            raise RepositoryException(
                f"Failed to find relationships between entities",
                context={
                    "from_entity_id": str(from_entity_id),
                    "to_entity_id": str(to_entity_id),
                },
                original_exception=e,
            )

    async def delete(self, id: UUID) -> bool:
        """
        Delete a relationship.

        Args:
            id: Relationship UUID

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryException: If delete fails
        """
        try:
            query = """
            MATCH ()-[r]->()
            WHERE r.id = $id
            DELETE r
            RETURN count(r) as deleted_count
            """

            params = {"id": str(id)}
            result = await self.client.execute_write(query, params)

            deleted_count = result[0]["deleted_count"] if result else 0
            success = deleted_count > 0

            if success:
                logger.debug(f"Deleted relationship: {id}")
            else:
                logger.debug(f"Relationship not found for deletion: {id}")

            return success

        except Exception as e:
            logger.error(f"Failed to delete relationship {id}: {e}")
            raise RepositoryException(
                f"Failed to delete relationship",
                context={"relationship_id": str(id)},
                original_exception=e,
            )

    async def find_outgoing(self, entity_id: UUID) -> List[Relationship]:
        """
        Find all outgoing relationships from an entity.

        Args:
            entity_id: Entity UUID

        Returns:
            List of outgoing relationships

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = """
            MATCH (from:Entity {id: $entity_id})-[r]->(to:Entity)
            RETURN r, from.id as from_id, to.id as to_id
            ORDER BY r.strength DESC
            """

            params = {"entity_id": str(entity_id)}
            result = await self.client.execute_read(query, params)

            relationships = []
            for record in result:
                rel_data = record["r"]
                from_id = UUID(record["from_id"])
                to_id = UUID(record["to_id"])
                relationships.append(self.mapper.from_dict(rel_data, from_id, to_id))

            logger.debug(
                f"Found {len(relationships)} outgoing relationships for {entity_id}"
            )
            return relationships

        except Exception as e:
            logger.error(f"Failed to find outgoing relationships for {entity_id}: {e}")
            raise RepositoryException(
                f"Failed to find outgoing relationships",
                context={"entity_id": str(entity_id)},
                original_exception=e,
            )

    async def find_incoming(self, entity_id: UUID) -> List[Relationship]:
        """
        Find all incoming relationships to an entity.

        Args:
            entity_id: Entity UUID

        Returns:
            List of incoming relationships

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = """
            MATCH (from:Entity)-[r]->(to:Entity {id: $entity_id})
            RETURN r, from.id as from_id, to.id as to_id
            ORDER BY r.strength DESC
            """

            params = {"entity_id": str(entity_id)}
            result = await self.client.execute_read(query, params)

            relationships = []
            for record in result:
                rel_data = record["r"]
                from_id = UUID(record["from_id"])
                to_id = UUID(record["to_id"])
                relationships.append(self.mapper.from_dict(rel_data, from_id, to_id))

            logger.debug(
                f"Found {len(relationships)} incoming relationships for {entity_id}"
            )
            return relationships

        except Exception as e:
            logger.error(f"Failed to find incoming relationships for {entity_id}: {e}")
            raise RepositoryException(
                f"Failed to find incoming relationships",
                context={"entity_id": str(entity_id)},
                original_exception=e,
            )

    async def find_strong_relationships(
        self,
        threshold: float = 0.7,
        limit: int = 100
    ) -> List[Relationship]:
        """
        Find relationships with strength above a threshold.

        Args:
            threshold: Minimum relationship strength (0.0-1.0)
            limit: Maximum results to return

        Returns:
            List of strong relationships ordered by strength desc

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = """
            MATCH (from:Entity)-[r]->(to:Entity)
            WHERE r.strength >= $threshold
            RETURN r, from.id as from_id, to.id as to_id
            ORDER BY r.strength DESC
            LIMIT $limit
            """

            params = {"threshold": threshold, "limit": limit}
            result = await self.client.execute_read(query, params)

            relationships = []
            for record in result:
                rel_data = record["r"]
                from_id = UUID(record["from_id"])
                to_id = UUID(record["to_id"])
                relationships.append(self.mapper.from_dict(rel_data, from_id, to_id))

            logger.debug(
                f"Found {len(relationships)} strong relationships (threshold={threshold})"
            )
            return relationships

        except Exception as e:
            logger.error(f"Failed to find strong relationships: {e}")
            raise RepositoryException(
                f"Failed to find strong relationships",
                context={"threshold": threshold},
                original_exception=e,
            )

    async def find_by_case_id(self, case_id: UUID) -> List[Relationship]:
        """
        Find all relationships for a case.

        Note: This requires relationships to have a case_id in metadata.

        Args:
            case_id: Case UUID

        Returns:
            List of relationships for the case

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = """
            MATCH (from:Entity)-[r]->(to:Entity)
            WHERE r.metadata.case_id = $case_id
            RETURN r, from.id as from_id, to.id as to_id
            ORDER BY r.strength DESC
            """

            params = {"case_id": str(case_id)}
            result = await self.client.execute_read(query, params)

            relationships = []
            for record in result:
                rel_data = record["r"]
                from_id = UUID(record["from_id"])
                to_id = UUID(record["to_id"])
                relationships.append(self.mapper.from_dict(rel_data, from_id, to_id))

            logger.debug(f"Found {len(relationships)} relationships for case {case_id}")
            return relationships

        except Exception as e:
            logger.error(f"Failed to find relationships for case {case_id}: {e}")
            raise RepositoryException(
                f"Failed to find relationships by case ID",
                context={"case_id": str(case_id)},
                original_exception=e,
            )
