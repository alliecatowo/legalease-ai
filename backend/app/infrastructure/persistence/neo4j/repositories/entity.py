"""
Neo4j implementation of EntityRepository.

This module provides entity persistence operations using Neo4j graph database.
"""

import logging
from typing import List, Optional
from uuid import UUID

from app.domain.knowledge.entities import Entity
from app.domain.knowledge.entities.entity import EntityType
from app.domain.knowledge.repositories.graph_repository import EntityRepository
from app.shared.exceptions.domain_exceptions import RepositoryException

from ..client import Neo4jClient
from ..mappers import EntityMapper
from ..query_builder import CypherQueryBuilder, OrderDirection

logger = logging.getLogger(__name__)


class Neo4jEntityRepository(EntityRepository):
    """
    Neo4j implementation of EntityRepository.

    Provides CRUD operations and graph queries for Entity entities.
    """

    def __init__(self, client: Neo4jClient):
        """
        Initialize entity repository.

        Args:
            client: Neo4jClient instance
        """
        self.client = client
        self.mapper = EntityMapper()

    async def save(self, entity: Entity) -> Entity:
        """
        Save or update an entity.

        Uses MERGE to avoid duplicates based on entity ID.

        Args:
            entity: Entity to save

        Returns:
            Saved entity

        Raises:
            RepositoryException: If save fails
        """
        try:
            props = self.mapper.to_node_properties(entity)

            query = """
            MERGE (e:Entity {id: $id})
            SET e.entity_type = $entity_type,
                e.name = $name,
                e.aliases = $aliases,
                e.attributes = $attributes,
                e.first_seen = $first_seen,
                e.last_seen = $last_seen,
                e.source_citations = $source_citations,
                e.metadata = $metadata
            RETURN e
            """

            result = await self.client.execute_write(query, props)

            if not result:
                raise RepositoryException(
                    "Failed to save entity: no result returned",
                    context={"entity_id": str(entity.id)}
                )

            logger.debug(f"Saved entity: {entity.id}")
            return entity

        except Exception as e:
            logger.error(f"Failed to save entity {entity.id}: {e}")
            raise RepositoryException(
                f"Failed to save entity",
                context={"entity_id": str(entity.id)},
                original_exception=e,
            )

    async def get_by_id(self, id: UUID) -> Optional[Entity]:
        """
        Get entity by ID.

        Args:
            id: Entity UUID

        Returns:
            Entity if found, None otherwise

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = (
                CypherQueryBuilder()
                .match("(e:Entity)")
                .where("e.id = $id")
                .return_("e")
                .build()
            )

            params = {"id": str(id)}
            result = await self.client.execute_read(query, params)

            if not result:
                return None

            entity_data = result[0]["e"]
            return self.mapper.from_dict(entity_data)

        except Exception as e:
            logger.error(f"Failed to get entity {id}: {e}")
            raise RepositoryException(
                f"Failed to get entity by ID",
                context={"entity_id": str(id)},
                original_exception=e,
            )

    async def find_by_name(self, name: str) -> List[Entity]:
        """
        Find entities by name (including aliases).

        Performs case-insensitive search on both name and aliases.

        Args:
            name: Entity name to search for

        Returns:
            List of matching entities

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = """
            MATCH (e:Entity)
            WHERE toLower(e.name) = toLower($name)
               OR any(alias IN e.aliases WHERE toLower(alias) = toLower($name))
            RETURN e
            ORDER BY e.name
            """

            params = {"name": name}
            result = await self.client.execute_read(query, params)

            entities = []
            for record in result:
                entity_data = record["e"]
                entities.append(self.mapper.from_dict(entity_data))

            logger.debug(f"Found {len(entities)} entities with name '{name}'")
            return entities

        except Exception as e:
            logger.error(f"Failed to find entities by name '{name}': {e}")
            raise RepositoryException(
                f"Failed to find entities by name",
                context={"name": name},
                original_exception=e,
            )

    async def find_by_type(self, entity_type: str) -> List[Entity]:
        """
        Find entities by type.

        Args:
            entity_type: Entity type to filter by

        Returns:
            List of entities of the specified type

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = (
                CypherQueryBuilder()
                .match("(e:Entity)")
                .where("e.entity_type = $entity_type")
                .return_("e")
                .order_by("e.name", OrderDirection.ASC)
                .build()
            )

            params = {"entity_type": entity_type}
            result = await self.client.execute_read(query, params)

            entities = []
            for record in result:
                entity_data = record["e"]
                entities.append(self.mapper.from_dict(entity_data))

            logger.debug(f"Found {len(entities)} entities of type '{entity_type}'")
            return entities

        except Exception as e:
            logger.error(f"Failed to find entities by type '{entity_type}': {e}")
            raise RepositoryException(
                f"Failed to find entities by type",
                context={"entity_type": entity_type},
                original_exception=e,
            )

    async def find_by_case_id(self, case_id: UUID) -> List[Entity]:
        """
        Find all entities for a case.

        Note: This requires entities to have a case_id attribute.

        Args:
            case_id: Case UUID

        Returns:
            List of entities for the case

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = """
            MATCH (e:Entity)
            WHERE e.metadata.case_id = $case_id
               OR e.attributes.case_id = $case_id
            RETURN e
            ORDER BY e.name
            """

            params = {"case_id": str(case_id)}
            result = await self.client.execute_read(query, params)

            entities = []
            for record in result:
                entity_data = record["e"]
                entities.append(self.mapper.from_dict(entity_data))

            logger.debug(f"Found {len(entities)} entities for case {case_id}")
            return entities

        except Exception as e:
            logger.error(f"Failed to find entities for case {case_id}: {e}")
            raise RepositoryException(
                f"Failed to find entities by case ID",
                context={"case_id": str(case_id)},
                original_exception=e,
            )

    async def delete(self, id: UUID) -> bool:
        """
        Delete an entity.

        Note: This uses DETACH DELETE to also remove all relationships.

        Args:
            id: Entity UUID

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryException: If delete fails
        """
        try:
            query = """
            MATCH (e:Entity {id: $id})
            DETACH DELETE e
            RETURN count(e) as deleted_count
            """

            params = {"id": str(id)}
            result = await self.client.execute_write(query, params)

            deleted_count = result[0]["deleted_count"] if result else 0
            success = deleted_count > 0

            if success:
                logger.debug(f"Deleted entity: {id}")
            else:
                logger.debug(f"Entity not found for deletion: {id}")

            return success

        except Exception as e:
            logger.error(f"Failed to delete entity {id}: {e}")
            raise RepositoryException(
                f"Failed to delete entity",
                context={"entity_id": str(id)},
                original_exception=e,
            )

    async def find_related_entities(
        self,
        entity_id: UUID,
        relationship_type: Optional[str] = None,
        depth: int = 1
    ) -> List[Entity]:
        """
        Find entities related to the given entity.

        Args:
            entity_id: Source entity UUID
            relationship_type: Optional relationship type to filter by
            depth: Relationship depth (1-3)

        Returns:
            List of related entities

        Raises:
            RepositoryException: If query fails
        """
        try:
            # Limit depth to prevent runaway queries
            depth = min(max(depth, 1), 3)

            if relationship_type:
                # Specific relationship type
                query = f"""
                MATCH (e:Entity {{id: $entity_id}})-[r:{relationship_type}*1..{depth}]-(related:Entity)
                RETURN DISTINCT related as e
                ORDER BY related.name
                """
            else:
                # Any relationship type
                query = f"""
                MATCH (e:Entity {{id: $entity_id}})-[*1..{depth}]-(related:Entity)
                RETURN DISTINCT related as e
                ORDER BY related.name
                """

            params = {"entity_id": str(entity_id)}
            result = await self.client.execute_read(query, params)

            entities = []
            for record in result:
                entity_data = record["e"]
                entities.append(self.mapper.from_dict(entity_data))

            logger.debug(
                f"Found {len(entities)} related entities for {entity_id} "
                f"(depth={depth}, type={relationship_type})"
            )
            return entities

        except Exception as e:
            logger.error(f"Failed to find related entities for {entity_id}: {e}")
            raise RepositoryException(
                f"Failed to find related entities",
                context={
                    "entity_id": str(entity_id),
                    "relationship_type": relationship_type,
                    "depth": depth,
                },
                original_exception=e,
            )

    async def merge_entities(self, entity_id1: UUID, entity_id2: UUID) -> Entity:
        """
        Merge two entities into one, resolving duplicates.

        Keeps entity_id1 and merges data from entity_id2 into it.
        All relationships from entity_id2 are transferred to entity_id1.

        Args:
            entity_id1: Primary entity UUID (will be kept)
            entity_id2: Secondary entity UUID (will be deleted)

        Returns:
            Merged entity

        Raises:
            RepositoryException: If merge fails
        """
        try:
            # First, get both entities
            entity1 = await self.get_by_id(entity_id1)
            entity2 = await self.get_by_id(entity_id2)

            if not entity1:
                raise RepositoryException(
                    f"Primary entity not found",
                    context={"entity_id": str(entity_id1)}
                )

            if not entity2:
                raise RepositoryException(
                    f"Secondary entity not found",
                    context={"entity_id": str(entity_id2)}
                )

            # Merge aliases
            for alias in entity2.aliases:
                entity1.add_alias(alias)

            # Merge attributes (entity2 values don't override entity1)
            for key, value in entity2.attributes.items():
                if key not in entity1.attributes:
                    entity1.attributes[key] = value

            # Merge citations
            for citation in entity2.source_citations:
                entity1.add_citation(citation)

            # Update temporal bounds
            if entity2.first_seen < entity1.first_seen:
                entity1.first_seen = entity2.first_seen
            if entity2.last_seen > entity1.last_seen:
                entity1.last_seen = entity2.last_seen

            # Transfer all relationships from entity2 to entity1
            query = """
            MATCH (e1:Entity {id: $entity_id1})
            MATCH (e2:Entity {id: $entity_id2})
            MATCH (e2)-[r]->(other)
            WHERE other.id <> $entity_id1
            MERGE (e1)-[r2:RELATED_TO]->(other)
            SET r2 += properties(r)
            WITH e1, e2, count(r) as outgoing_rels
            MATCH (other)-[r]->(e2)
            WHERE other.id <> $entity_id1
            MERGE (other)-[r2:RELATED_TO]->(e1)
            SET r2 += properties(r)
            WITH e1, e2, outgoing_rels, count(r) as incoming_rels
            DETACH DELETE e2
            RETURN e1, outgoing_rels + incoming_rels as transferred_rels
            """

            params = {
                "entity_id1": str(entity_id1),
                "entity_id2": str(entity_id2),
            }

            result = await self.client.execute_write(query, params)

            # Save the merged entity
            merged_entity = await self.save(entity1)

            logger.info(
                f"Merged entities {entity_id2} into {entity_id1}, "
                f"transferred {result[0]['transferred_rels']} relationships"
            )

            return merged_entity

        except RepositoryException:
            raise
        except Exception as e:
            logger.error(f"Failed to merge entities {entity_id1} and {entity_id2}: {e}")
            raise RepositoryException(
                f"Failed to merge entities",
                context={
                    "entity_id1": str(entity_id1),
                    "entity_id2": str(entity_id2),
                },
                original_exception=e,
            )

    async def search(
        self,
        query: str,
        entity_types: Optional[List[EntityType]] = None,
        limit: int = 50
    ) -> List[Entity]:
        """
        Full-text search for entities.

        Args:
            query: Search query string
            entity_types: Optional list of entity types to filter by
            limit: Maximum results to return

        Returns:
            List of matching entities

        Raises:
            RepositoryException: If search fails
        """
        try:
            # Build query with optional type filter
            cypher_builder = CypherQueryBuilder().match("(e:Entity)")

            # Add type filter if specified
            if entity_types:
                type_values = [t.value for t in entity_types]
                cypher_builder.where_in("e.entity_type", "entity_types")

            # Text search on name and aliases
            cypher_builder.where(
                "toLower(e.name) CONTAINS toLower($query) OR "
                "any(alias IN e.aliases WHERE toLower(alias) CONTAINS toLower($query))"
            )

            cypher = (
                cypher_builder
                .return_("e")
                .order_by("e.name", OrderDirection.ASC)
                .limit(limit)
                .build()
            )

            params = {"query": query}
            if entity_types:
                params["entity_types"] = [t.value for t in entity_types]

            result = await self.client.execute_read(cypher, params)

            entities = []
            for record in result:
                entity_data = record["e"]
                entities.append(self.mapper.from_dict(entity_data))

            logger.debug(f"Search '{query}' found {len(entities)} entities")
            return entities

        except Exception as e:
            logger.error(f"Entity search failed for query '{query}': {e}")
            raise RepositoryException(
                f"Entity search failed",
                context={"query": query, "entity_types": entity_types},
                original_exception=e,
            )
