"""
Neo4j infrastructure module.

This module provides Neo4j integration for the knowledge graph including:
- Enhanced async client with connection pooling and retry logic
- Schema management with constraints and indexes
- Cypher query builder for type-safe query construction
- Domain object mappers
- Repository implementations for Entity, Event, Relationship, and Graph operations
"""

from .client import (
    Neo4jClient,
    get_neo4j_client,
    init_neo4j,
    close_neo4j,
)
from .schema import GraphSchema, initialize_schema
from .query_builder import CypherQueryBuilder, OrderDirection, build_property_map
from .mappers import (
    EntityMapper,
    EventMapper,
    RelationshipMapper,
    TimelineMapper,
    TemporalBoundsMapper,
)
from .repositories import (
    Neo4jEntityRepository,
    Neo4jEventRepository,
    Neo4jRelationshipRepository,
    Neo4jGraphRepository,
    Path,
    Community,
    Contradiction,
)

__all__ = [
    # Client
    "Neo4jClient",
    "get_neo4j_client",
    "init_neo4j",
    "close_neo4j",
    # Schema
    "GraphSchema",
    "initialize_schema",
    # Query Builder
    "CypherQueryBuilder",
    "OrderDirection",
    "build_property_map",
    # Mappers
    "EntityMapper",
    "EventMapper",
    "RelationshipMapper",
    "TimelineMapper",
    "TemporalBoundsMapper",
    # Repositories
    "Neo4jEntityRepository",
    "Neo4jEventRepository",
    "Neo4jRelationshipRepository",
    "Neo4jGraphRepository",
    # Graph Types
    "Path",
    "Community",
    "Contradiction",
]
