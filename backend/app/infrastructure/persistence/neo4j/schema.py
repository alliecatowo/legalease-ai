"""
Neo4j graph schema definition and initialization.

This module defines the knowledge graph schema including:
- Node labels and properties
- Relationship types
- Constraints for data integrity
- Indexes for query performance
"""

import logging
from typing import List

from .client import Neo4jClient, get_neo4j_client
from app.shared.exceptions.domain_exceptions import RepositoryException

logger = logging.getLogger(__name__)


class GraphSchema:
    """
    Knowledge graph schema manager.

    Defines and creates constraints, indexes, and schema structure
    for the knowledge graph.
    """

    # Node labels
    NODE_ENTITY = "Entity"
    NODE_EVENT = "Event"
    NODE_CASE = "Case"

    # Relationship types
    REL_PARTICIPATED_IN = "PARTICIPATED_IN"
    REL_RELATED_TO = "RELATED_TO"
    REL_LOCATED_AT = "LOCATED_AT"
    REL_CITED_IN = "CITED_IN"

    def __init__(self, client: Neo4jClient):
        """
        Initialize schema manager.

        Args:
            client: Neo4jClient instance
        """
        self.client = client

    async def create_constraints(self) -> None:
        """
        Create uniqueness constraints for graph integrity.

        Constraints ensure data quality and enable efficient lookups.
        They also automatically create an index on the constrained property.

        Raises:
            RepositoryException: If constraint creation fails
        """
        constraints = [
            # Entity constraints
            f"CREATE CONSTRAINT {self.NODE_ENTITY.lower()}_id IF NOT EXISTS "
            f"FOR (e:{self.NODE_ENTITY}) REQUIRE e.id IS UNIQUE",

            # Event constraints
            f"CREATE CONSTRAINT {self.NODE_EVENT.lower()}_id IF NOT EXISTS "
            f"FOR (e:{self.NODE_EVENT}) REQUIRE e.id IS UNIQUE",

            # Case constraints
            f"CREATE CONSTRAINT {self.NODE_CASE.lower()}_id IF NOT EXISTS "
            f"FOR (c:{self.NODE_CASE}) REQUIRE c.id IS UNIQUE",
        ]

        logger.info("Creating Neo4j constraints...")

        for constraint in constraints:
            try:
                await self.client.execute_write(constraint)
                logger.debug(f"Created constraint: {constraint}")
            except Exception as e:
                # Some constraint errors are acceptable (e.g., already exists)
                logger.warning(f"Constraint creation warning: {e}")

        logger.info("Neo4j constraints created successfully")

    async def create_indexes(self) -> None:
        """
        Create indexes for query performance.

        Indexes speed up common query patterns without enforcing uniqueness.

        Raises:
            RepositoryException: If index creation fails
        """
        indexes = [
            # Entity indexes
            f"CREATE INDEX {self.NODE_ENTITY.lower()}_name IF NOT EXISTS "
            f"FOR (e:{self.NODE_ENTITY}) ON (e.name)",

            f"CREATE INDEX {self.NODE_ENTITY.lower()}_type IF NOT EXISTS "
            f"FOR (e:{self.NODE_ENTITY}) ON (e.entity_type)",

            f"CREATE INDEX {self.NODE_ENTITY.lower()}_case_id IF NOT EXISTS "
            f"FOR (e:{self.NODE_ENTITY}) ON (e.case_id)",

            # Composite index for common query pattern
            f"CREATE INDEX {self.NODE_ENTITY.lower()}_case_type IF NOT EXISTS "
            f"FOR (e:{self.NODE_ENTITY}) ON (e.case_id, e.entity_type)",

            # Event indexes
            f"CREATE INDEX {self.NODE_EVENT.lower()}_timestamp IF NOT EXISTS "
            f"FOR (e:{self.NODE_EVENT}) ON (e.timestamp)",

            f"CREATE INDEX {self.NODE_EVENT.lower()}_type IF NOT EXISTS "
            f"FOR (e:{self.NODE_EVENT}) ON (e.event_type)",

            f"CREATE INDEX {self.NODE_EVENT.lower()}_case_id IF NOT EXISTS "
            f"FOR (e:{self.NODE_EVENT}) ON (e.case_id)",

            # Composite index for timeline queries
            f"CREATE INDEX {self.NODE_EVENT.lower()}_case_time IF NOT EXISTS "
            f"FOR (e:{self.NODE_EVENT}) ON (e.case_id, e.timestamp)",

            # Case indexes
            f"CREATE INDEX {self.NODE_CASE.lower()}_name IF NOT EXISTS "
            f"FOR (c:{self.NODE_CASE}) ON (c.name)",
        ]

        logger.info("Creating Neo4j indexes...")

        for index in indexes:
            try:
                await self.client.execute_write(index)
                logger.debug(f"Created index: {index}")
            except Exception as e:
                # Some index errors are acceptable (e.g., already exists)
                logger.warning(f"Index creation warning: {e}")

        logger.info("Neo4j indexes created successfully")

    async def get_schema_info(self) -> dict:
        """
        Get information about the current schema.

        Returns:
            Dictionary with schema information including constraints and indexes
        """
        # Get constraints
        constraints_query = "SHOW CONSTRAINTS"
        constraints_result = await self.client.execute_read(constraints_query)

        # Get indexes
        indexes_query = "SHOW INDEXES"
        indexes_result = await self.client.execute_read(indexes_query)

        # Get node labels
        labels_query = "CALL db.labels()"
        labels_result = await self.client.execute_read(labels_query)

        # Get relationship types
        rel_types_query = "CALL db.relationshipTypes()"
        rel_types_result = await self.client.execute_read(rel_types_query)

        return {
            "constraints": constraints_result,
            "indexes": indexes_result,
            "node_labels": labels_result,
            "relationship_types": rel_types_result,
        }

    async def drop_all_constraints(self) -> None:
        """
        Drop all constraints (for testing/development only).

        WARNING: This should only be used in development/testing environments.

        Raises:
            RepositoryException: If dropping constraints fails
        """
        logger.warning("Dropping all Neo4j constraints - this should only be done in development!")

        # Get all constraints
        constraints_query = "SHOW CONSTRAINTS"
        constraints = await self.client.execute_read(constraints_query)

        # Drop each constraint
        for constraint in constraints:
            constraint_name = constraint.get("name")
            if constraint_name:
                drop_query = f"DROP CONSTRAINT {constraint_name} IF EXISTS"
                try:
                    await self.client.execute_write(drop_query)
                    logger.debug(f"Dropped constraint: {constraint_name}")
                except Exception as e:
                    logger.warning(f"Failed to drop constraint {constraint_name}: {e}")

    async def drop_all_indexes(self) -> None:
        """
        Drop all indexes (for testing/development only).

        WARNING: This should only be used in development/testing environments.

        Raises:
            RepositoryException: If dropping indexes fails
        """
        logger.warning("Dropping all Neo4j indexes - this should only be done in development!")

        # Get all indexes
        indexes_query = "SHOW INDEXES"
        indexes = await self.client.execute_read(indexes_query)

        # Drop each index (except constraint-backed indexes)
        for index in indexes:
            index_name = index.get("name")
            # Skip constraint-backed indexes
            if index_name and index.get("type") != "LOOKUP":
                drop_query = f"DROP INDEX {index_name} IF EXISTS"
                try:
                    await self.client.execute_write(drop_query)
                    logger.debug(f"Dropped index: {index_name}")
                except Exception as e:
                    logger.warning(f"Failed to drop index {index_name}: {e}")

    async def clear_all_data(self) -> None:
        """
        Delete all nodes and relationships (for testing only).

        WARNING: This permanently deletes all data. Only use in development/testing.

        Raises:
            RepositoryException: If clearing data fails
        """
        logger.warning("Clearing all Neo4j data - this should only be done in testing!")

        query = "MATCH (n) DETACH DELETE n"
        await self.client.execute_write(query)

        logger.info("All Neo4j data cleared")

    async def get_statistics(self) -> dict:
        """
        Get database statistics.

        Returns:
            Dictionary with node counts, relationship counts, etc.
        """
        stats = {}

        # Count all nodes
        query = "MATCH (n) RETURN count(n) as total_nodes"
        result = await self.client.execute_read(query)
        stats["total_nodes"] = result[0]["total_nodes"] if result else 0

        # Count nodes by label
        for label in [self.NODE_ENTITY, self.NODE_EVENT, self.NODE_CASE]:
            query = f"MATCH (n:{label}) RETURN count(n) as count"
            result = await self.client.execute_read(query)
            stats[f"{label.lower()}_count"] = result[0]["count"] if result else 0

        # Count all relationships
        query = "MATCH ()-[r]->() RETURN count(r) as total_relationships"
        result = await self.client.execute_read(query)
        stats["total_relationships"] = result[0]["total_relationships"] if result else 0

        # Count relationships by type
        query = "MATCH ()-[r]->() RETURN type(r) as rel_type, count(r) as count"
        result = await self.client.execute_read(query)
        stats["relationships_by_type"] = {
            r["rel_type"]: r["count"] for r in result
        }

        return stats


async def initialize_schema(client: Optional[Neo4jClient] = None) -> GraphSchema:
    """
    Initialize the Neo4j graph schema.

    This creates all necessary constraints and indexes.
    Should be called during application startup.

    Args:
        client: Optional Neo4jClient instance (uses global client if not provided)

    Returns:
        GraphSchema instance

    Raises:
        RepositoryException: If schema initialization fails
    """
    if client is None:
        client = get_neo4j_client()

    schema = GraphSchema(client)

    try:
        await schema.create_constraints()
        await schema.create_indexes()

        logger.info("Neo4j schema initialized successfully")

        # Log statistics
        stats = await schema.get_statistics()
        logger.info(f"Neo4j database statistics: {stats}")

        return schema

    except Exception as e:
        logger.error(f"Failed to initialize Neo4j schema: {e}")
        raise RepositoryException(
            "Failed to initialize Neo4j schema",
            original_exception=e,
        )
