"""
QueryGraphQuery for exploring the knowledge graph.

This module implements CQRS query pattern for querying the knowledge graph
with support for various query types (entity lookup, path finding, etc.).
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.domain.knowledge.entities.entity import EntityType
from app.domain.knowledge.entities.relationship import RelationshipType
from app.domain.knowledge.repositories.graph_repository import GraphRepository


logger = logging.getLogger(__name__)


@dataclass
class QueryGraphQuery:
    """
    Query for exploring the knowledge graph.

    Supports various query types:
    - "entity": Get entity with relationships
    - "path": Find shortest path between entities
    - "timeline": Build timeline for entity
    - "subgraph": Extract subgraph of related entities
    - "related": Find related entities within depth

    Attributes:
        case_id: Case ID to scope query
        query_type: Type of graph query
        entity_id: Single entity ID (for "entity", "timeline", "related")
        entity1_id: First entity ID (for "path")
        entity2_id: Second entity ID (for "path")
        entity_ids: Multiple entity IDs (for "subgraph")
        depth: Relationship depth to traverse
        limit: Maximum results to return

    Example:
        >>> query = QueryGraphQuery(
        ...     case_id=case_uuid,
        ...     query_type="entity",
        ...     entity_id=entity_uuid,
        ...     depth=2,
        ... )
    """

    case_id: UUID
    query_type: str
    entity_id: Optional[UUID] = None
    entity1_id: Optional[UUID] = None
    entity2_id: Optional[UUID] = None
    entity_ids: Optional[List[UUID]] = None
    depth: int = 2
    limit: int = 100

    def __post_init__(self) -> None:
        """Validate query parameters."""
        valid_types = ("entity", "path", "timeline", "subgraph", "related")
        if self.query_type not in valid_types:
            raise ValueError(f"query_type must be one of {valid_types}, got {self.query_type}")

        if self.depth < 1 or self.depth > 5:
            raise ValueError(f"depth must be between 1 and 5, got {self.depth}")

        if self.limit < 1 or self.limit > 1000:
            raise ValueError(f"limit must be between 1 and 1000, got {self.limit}")

        # Validate required parameters for each query type
        if self.query_type in ("entity", "timeline", "related") and not self.entity_id:
            raise ValueError(f"entity_id required for query_type={self.query_type}")

        if self.query_type == "path" and (not self.entity1_id or not self.entity2_id):
            raise ValueError("entity1_id and entity2_id required for query_type=path")

        if self.query_type == "subgraph" and not self.entity_ids:
            raise ValueError("entity_ids required for query_type=subgraph")


@dataclass
class EntityDTO:
    """
    Data Transfer Object for Entity.

    Attributes:
        id: Entity ID
        entity_type: Type of entity
        name: Primary name
        aliases: Alternative names
        attributes: Key-value attributes
        confidence: Extraction confidence (if available)
        first_seen: First mention timestamp
        last_seen: Last mention timestamp
        citation_count: Number of source citations
    """

    id: UUID
    entity_type: EntityType
    name: str
    aliases: List[str]
    attributes: Dict[str, Any]
    confidence: float
    first_seen: str
    last_seen: str
    citation_count: int = 0


@dataclass
class RelationshipDTO:
    """
    Data Transfer Object for Relationship.

    Attributes:
        id: Relationship ID
        from_entity: Source entity DTO
        to_entity: Target entity DTO
        relationship_type: Type of relationship
        strength: Relationship strength (0.0-1.0)
        temporal_start: Optional start timestamp
        temporal_end: Optional end timestamp
        citation_count: Number of source citations
    """

    id: UUID
    from_entity: EntityDTO
    to_entity: EntityDTO
    relationship_type: RelationshipType
    strength: float
    temporal_start: Optional[str] = None
    temporal_end: Optional[str] = None
    citation_count: int = 0


@dataclass
class EventDTO:
    """
    Data Transfer Object for Event.

    Attributes:
        id: Event ID
        event_type: Type of event
        description: Event description
        timestamp: Event timestamp
        participants: Participant entity DTOs
        location: Location (entity ID or string)
        duration: Duration in seconds
        citation_count: Number of source citations
    """

    id: UUID
    event_type: str
    description: str
    timestamp: str
    participants: List[EntityDTO]
    location: Optional[str] = None
    duration: Optional[float] = None
    citation_count: int = 0


@dataclass
class QueryGraphResult:
    """
    Result of QueryGraphQuery.

    Attributes:
        entities: List of entity DTOs
        relationships: List of relationship DTOs
        events: List of event DTOs (for timeline queries)
        metadata: Query execution metadata
    """

    entities: List[EntityDTO]
    relationships: List[RelationshipDTO]
    events: List[EventDTO] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class QueryGraphQueryHandler:
    """
    Handler for knowledge graph queries.

    Routes queries to appropriate graph operations and converts
    domain entities to DTOs.
    """

    def __init__(self, graph_repo: GraphRepository):
        """
        Initialize handler with dependencies.

        Args:
            graph_repo: Repository for graph operations
        """
        self.repo = graph_repo
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def handle(self, query: QueryGraphQuery) -> QueryGraphResult:
        """
        Execute the graph query and return results.

        Routes to specific handler based on query_type.

        Args:
            query: The query to execute

        Returns:
            QueryGraphResult with entities and relationships

        Raises:
            ValueError: If query is invalid
            RuntimeError: If graph query fails
        """
        self.logger.info(
            "Executing graph query",
            extra={
                "query_type": query.query_type,
                "case_id": query.case_id,
            }
        )

        try:
            if query.query_type == "entity":
                result = await self._handle_entity_query(query)
            elif query.query_type == "path":
                result = await self._handle_path_query(query)
            elif query.query_type == "timeline":
                result = await self._handle_timeline_query(query)
            elif query.query_type == "subgraph":
                result = await self._handle_subgraph_query(query)
            elif query.query_type == "related":
                result = await self._handle_related_query(query)
            else:
                raise ValueError(f"Unsupported query_type: {query.query_type}")

            self.logger.info(
                "Graph query completed successfully",
                extra={
                    "query_type": query.query_type,
                    "entities_count": len(result.entities),
                    "relationships_count": len(result.relationships),
                }
            )

            return result

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(
                f"Graph query failed: {e}",
                extra={"query_type": query.query_type},
                exc_info=True
            )
            raise RuntimeError(f"Graph query failed: {e}") from e

    async def _handle_entity_query(self, query: QueryGraphQuery) -> QueryGraphResult:
        """Handle entity lookup query."""
        entity, relationships = await self.repo.get_entity_with_relationships(query.entity_id)

        if not entity:
            return QueryGraphResult(entities=[], relationships=[])

        # Convert to DTOs
        entity_dto = self._entity_to_dto(entity)
        relationship_dtos = [self._relationship_to_dto(r, entity) for r in relationships]

        # Extract related entities from relationships
        related_entity_ids = set()
        for r in relationships:
            if r.from_entity_id != query.entity_id:
                related_entity_ids.add(r.from_entity_id)
            if r.to_entity_id != query.entity_id:
                related_entity_ids.add(r.to_entity_id)

        # Fetch related entities (simplified - in real impl would batch fetch)
        related_entities = []
        # TODO: Implement batch entity fetching

        return QueryGraphResult(
            entities=[entity_dto] + related_entities,
            relationships=relationship_dtos,
            metadata={"query_type": "entity", "central_entity_id": str(query.entity_id)},
        )

    async def _handle_path_query(self, query: QueryGraphQuery) -> QueryGraphResult:
        """Handle shortest path query."""
        path = await self.repo.find_shortest_path(query.entity1_id, query.entity2_id)

        if not path:
            return QueryGraphResult(entities=[], relationships=[])

        # Convert relationships to DTOs
        relationship_dtos = []
        # TODO: Convert path relationships to DTOs with entities

        return QueryGraphResult(
            entities=[],
            relationships=relationship_dtos,
            metadata={
                "query_type": "path",
                "from_entity_id": str(query.entity1_id),
                "to_entity_id": str(query.entity2_id),
                "path_length": len(path),
            },
        )

    async def _handle_timeline_query(self, query: QueryGraphQuery) -> QueryGraphResult:
        """Handle timeline query."""
        events = await self.repo.get_timeline_for_entity(query.entity_id)

        # Convert events to DTOs
        event_dtos = []
        # TODO: Convert events to DTOs

        return QueryGraphResult(
            entities=[],
            relationships=[],
            events=event_dtos,
            metadata={"query_type": "timeline", "entity_id": str(query.entity_id)},
        )

    async def _handle_subgraph_query(self, query: QueryGraphQuery) -> QueryGraphResult:
        """Handle subgraph extraction query."""
        entities, relationships = await self.repo.get_subgraph(query.entity_ids)

        # Convert to DTOs
        entity_dtos = [self._entity_to_dto(e) for e in entities]
        relationship_dtos = []
        # TODO: Convert relationships to DTOs

        return QueryGraphResult(
            entities=entity_dtos,
            relationships=relationship_dtos,
            metadata={"query_type": "subgraph", "entity_count": len(entities)},
        )

    async def _handle_related_query(self, query: QueryGraphQuery) -> QueryGraphResult:
        """Handle related entities query."""
        entities = await self.repo.get_connected_entities(query.entity_id, query.depth)

        # Convert to DTOs
        entity_dtos = [self._entity_to_dto(e) for e in entities]

        return QueryGraphResult(
            entities=entity_dtos,
            relationships=[],
            metadata={
                "query_type": "related",
                "central_entity_id": str(query.entity_id),
                "depth": query.depth,
            },
        )

    def _entity_to_dto(self, entity: Any) -> EntityDTO:
        """Convert Entity domain object to DTO."""
        return EntityDTO(
            id=entity.id,
            entity_type=entity.entity_type,
            name=entity.name,
            aliases=entity.aliases.copy(),
            attributes=entity.attributes.copy(),
            confidence=entity.metadata.get("confidence", 1.0),
            first_seen=entity.first_seen.isoformat() if entity.first_seen else "",
            last_seen=entity.last_seen.isoformat() if entity.last_seen else "",
            citation_count=len(entity.source_citations),
        )

    def _relationship_to_dto(self, relationship: Any, entity: Any) -> RelationshipDTO:
        """Convert Relationship domain object to DTO."""
        # TODO: Fetch related entities to populate from_entity and to_entity
        # For now, create placeholder DTOs
        from_dto = EntityDTO(
            id=relationship.from_entity_id,
            entity_type=EntityType.PERSON,
            name="",
            aliases=[],
            attributes={},
            confidence=1.0,
            first_seen="",
            last_seen="",
        )

        to_dto = EntityDTO(
            id=relationship.to_entity_id,
            entity_type=EntityType.PERSON,
            name="",
            aliases=[],
            attributes={},
            confidence=1.0,
            first_seen="",
            last_seen="",
        )

        return RelationshipDTO(
            id=relationship.id,
            from_entity=from_dto,
            to_entity=to_dto,
            relationship_type=relationship.relationship_type,
            strength=relationship.strength,
            temporal_start=relationship.temporal_start.isoformat() if relationship.temporal_start else None,
            temporal_end=relationship.temporal_end.isoformat() if relationship.temporal_end else None,
            citation_count=len(relationship.source_citations),
        )
