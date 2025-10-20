"""
API v2 routes for knowledge graph operations.

This module provides FastAPI routes for:
- Querying entities and relationships in the knowledge graph
- Finding paths between entities
- Retrieving case timelines
- Generating subgraphs for visualization
- Graph statistics
"""

import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status

from app.api.v2.schemas.graph import (
    EntityResponse,
    EntitiesResponse,
    EntityDetailResponse,
    RelationshipResponse,
    PathResponse,
    TimelineResponse,
    TimelineEventResponse,
    SubgraphResponse,
    GraphStatsResponse,
    GraphNodeSchema,
    GraphEdgeSchema,
)
from app.shared.types.enums import EntityType, RelationshipType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["knowledge-graph"])


# Dependency injection functions (to be implemented)
async def get_query_graph_handler():
    """
    Get QueryGraphQueryHandler instance.

    This will be implemented to return the actual handler from the application layer.
    For now, raises NotImplementedError.
    """
    raise NotImplementedError("QueryGraphQueryHandler not yet implemented")


async def get_timeline_handler():
    """
    Get GetTimelineQueryHandler instance.

    This will be implemented to return the actual handler from the application layer.
    For now, raises NotImplementedError.
    """
    raise NotImplementedError("GetTimelineQueryHandler not yet implemented")


async def get_graph_service():
    """
    Get GraphService instance.

    This will be implemented to return the actual service from the domain layer.
    For now, raises NotImplementedError.
    """
    raise NotImplementedError("GraphService not yet implemented")


@router.get("/entities", response_model=EntitiesResponse)
async def list_entities(
    case_id: UUID = Query(..., description="Case ID to filter entities"),
    entity_types: Optional[List[str]] = Query(None, description="Filter by entity types"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    query_handler=Depends(get_query_graph_handler),
):
    """
    List entities in the knowledge graph for a case.

    Args:
        case_id: UUID of the case
        entity_types: Optional filter for entity types
        limit: Maximum number of results
        offset: Pagination offset
        query_handler: QueryGraphQueryHandler from dependency injection

    Returns:
        EntitiesResponse with list of entities

    Example:
        GET /api/v2/graph/entities?case_id=123e4567-e89b-12d3-a456-426614174000&entity_types=PERSON&entity_types=ORGANIZATION
    """
    try:
        logger.info(f"Listing entities for case {case_id}")

        # Convert string types to enums if provided
        entity_type_enums = None
        if entity_types:
            entity_type_enums = [EntityType(et) for et in entity_types]

        from app.application.queries.query_graph import QueryGraphQuery

        query = QueryGraphQuery(
            case_id=case_id,
            query_type="entity",
            entity_types=entity_type_enums,
            limit=limit,
            offset=offset,
        )

        result = await query_handler.handle(query)

        return EntitiesResponse(
            entities=[EntityResponse.from_dto(e) for e in result.entities],
            total=len(result.entities),
            filters_applied={
                "case_id": str(case_id),
                "entity_types": entity_types or [],
            },
        )

    except ValueError as e:
        logger.error(f"Validation error listing entities: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error listing entities: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving entities: {str(e)}",
        )


@router.get("/entities/{entity_id}", response_model=EntityDetailResponse)
async def get_entity_details(
    entity_id: UUID,
    include_relationships: bool = Query(True, description="Include relationships"),
    relationship_depth: int = Query(1, ge=1, le=3, description="Relationship depth"),
    query_handler=Depends(get_query_graph_handler),
):
    """
    Get detailed entity information with related entities.

    Args:
        entity_id: UUID of the entity
        include_relationships: Whether to include relationships
        relationship_depth: How many hops to traverse (1-3)
        query_handler: QueryGraphQueryHandler from dependency injection

    Returns:
        EntityDetailResponse with entity, relationships, and related entities

    Example:
        GET /api/v2/graph/entities/123e4567-e89b-12d3-a456-426614174000?include_relationships=true&relationship_depth=2
    """
    try:
        logger.info(f"Getting entity details: id={entity_id}, depth={relationship_depth}")

        from app.application.queries.query_graph import QueryGraphQuery

        query = QueryGraphQuery(
            query_type="related",
            entity_id=entity_id,
            depth=relationship_depth if include_relationships else 0,
        )

        result = await query_handler.handle(query)

        if not result.entities:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity {entity_id} not found",
            )

        # First entity is the requested one, rest are related
        main_entity = result.entities[0]
        related_entities = result.entities[1:] if len(result.entities) > 1 else []

        return EntityDetailResponse(
            entity=EntityResponse.from_dto(main_entity),
            relationships=[RelationshipResponse.from_dto(r) for r in result.relationships],
            related_entities=[EntityResponse.from_dto(e) for e in related_entities],
            total_relationships=len(result.relationships),
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error getting entity details: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting entity details: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving entity: {str(e)}",
        )


@router.get("/path", response_model=PathResponse)
async def find_path_between_entities(
    entity1_id: UUID = Query(..., description="First entity ID"),
    entity2_id: UUID = Query(..., description="Second entity ID"),
    max_depth: int = Query(5, ge=1, le=10, description="Maximum path depth"),
    query_handler=Depends(get_query_graph_handler),
):
    """
    Find shortest path between two entities.

    Args:
        entity1_id: UUID of first entity
        entity2_id: UUID of second entity
        max_depth: Maximum search depth (1-10)
        query_handler: QueryGraphQueryHandler from dependency injection

    Returns:
        PathResponse with path entities and relationships

    Example:
        GET /api/v2/graph/path?entity1_id=123e4567-e89b-12d3-a456-426614174000&entity2_id=123e4567-e89b-12d3-a456-426614174001&max_depth=5
    """
    try:
        logger.info(f"Finding path between {entity1_id} and {entity2_id}")

        from app.application.queries.query_graph import QueryGraphQuery

        query = QueryGraphQuery(
            query_type="path",
            entity1_id=entity1_id,
            entity2_id=entity2_id,
            depth=max_depth,
        )

        result = await query_handler.handle(query)

        # Calculate total strength of path
        total_strength = sum(r.strength for r in result.relationships) / len(result.relationships) if result.relationships else 0.0

        return PathResponse(
            path_exists=len(result.relationships) > 0,
            entities=[EntityResponse.from_dto(e) for e in result.entities],
            relationships=[RelationshipResponse.from_dto(r) for r in result.relationships],
            path_length=len(result.relationships),
            total_strength=total_strength,
        )

    except ValueError as e:
        logger.error(f"Validation error finding path: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error finding path: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error finding path: {str(e)}",
        )


@router.get("/timeline", response_model=TimelineResponse)
async def get_case_timeline(
    case_id: UUID = Query(..., description="Case ID"),
    start_date: Optional[datetime] = Query(None, description="Filter start date"),
    end_date: Optional[datetime] = Query(None, description="Filter end date"),
    entity_id: Optional[UUID] = Query(None, description="Filter by entity participant"),
    query_handler=Depends(get_timeline_handler),
):
    """
    Get chronological timeline of events for a case.

    Args:
        case_id: UUID of the case
        start_date: Optional start date filter
        end_date: Optional end date filter
        entity_id: Optional filter for events with specific entity
        query_handler: GetTimelineQueryHandler from dependency injection

    Returns:
        TimelineResponse with chronologically ordered events

    Example:
        GET /api/v2/graph/timeline?case_id=123e4567-e89b-12d3-a456-426614174000&start_date=2024-01-01T00:00:00Z
    """
    try:
        logger.info(f"Getting timeline for case {case_id}")

        from app.application.queries.get_timeline import GetTimelineQuery

        query = GetTimelineQuery(
            case_id=case_id,
            start_date=start_date.isoformat() if start_date else None,
            end_date=end_date.isoformat() if end_date else None,
            entity_id=entity_id,
        )

        result = await query_handler.handle(query)

        return TimelineResponse(
            events=[TimelineEventResponse.from_dto(e) for e in result.events],
            start_date=result.start_date,
            end_date=result.end_date,
            total_events=result.total_events,
            filters_applied={
                "case_id": str(case_id),
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "entity_id": str(entity_id) if entity_id else None,
            },
        )

    except ValueError as e:
        logger.error(f"Validation error getting timeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting timeline: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving timeline: {str(e)}",
        )


@router.get("/subgraph/{entity_id}", response_model=SubgraphResponse)
async def get_entity_subgraph(
    entity_id: UUID,
    depth: int = Query(2, ge=1, le=3, description="Traversal depth"),
    query_handler=Depends(get_query_graph_handler),
):
    """
    Get subgraph around an entity (for visualization).

    Returns nodes and edges formatted for graph visualization libraries.

    Args:
        entity_id: UUID of the center entity
        depth: How many hops to traverse (1-3)
        query_handler: QueryGraphQueryHandler from dependency injection

    Returns:
        SubgraphResponse with nodes and edges for visualization

    Example:
        GET /api/v2/graph/subgraph/123e4567-e89b-12d3-a456-426614174000?depth=2
    """
    try:
        logger.info(f"Getting subgraph for entity {entity_id}, depth={depth}")

        from app.application.queries.query_graph import QueryGraphQuery

        query = QueryGraphQuery(
            query_type="subgraph",
            entity_id=entity_id,
            depth=depth,
        )

        result = await query_handler.handle(query)

        if not result.entities:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity {entity_id} not found",
            )

        # Format for graph visualization
        nodes = [
            GraphNodeSchema(
                id=str(e.id),
                label=e.name,
                type=e.entity_type.value,
                size=15 if e.id == entity_id else 10,  # Center node is larger
                metadata={
                    "confidence": getattr(e, "confidence", 1.0),
                    "mention_count": getattr(e, "mention_count", 0),
                },
            )
            for e in result.entities
        ]

        edges = [
            GraphEdgeSchema(
                id=str(r.id),
                source=str(r.from_entity_id),
                target=str(r.to_entity_id),
                label=r.relationship_type.value,
                strength=r.strength,
                metadata={
                    "source_count": len(r.source_citations) if hasattr(r, "source_citations") else 0,
                },
            )
            for r in result.relationships
        ]

        return SubgraphResponse(
            nodes=nodes,
            edges=edges,
            center_entity_id=entity_id,
            depth=depth,
            node_count=len(nodes),
            edge_count=len(edges),
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error getting subgraph: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting subgraph: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving subgraph: {str(e)}",
        )


@router.get("/stats", response_model=GraphStatsResponse)
async def get_graph_stats(
    case_id: UUID = Query(..., description="Case ID"),
    graph_service=Depends(get_graph_service),
):
    """
    Get statistics about the knowledge graph.

    Provides counts, distributions, and centrality metrics.

    Args:
        case_id: UUID of the case
        graph_service: GraphService from dependency injection

    Returns:
        GraphStatsResponse with comprehensive graph statistics

    Example:
        GET /api/v2/graph/stats?case_id=123e4567-e89b-12d3-a456-426614174000
    """
    try:
        logger.info(f"Getting graph stats for case {case_id}")

        stats = await graph_service.get_graph_statistics(case_id)

        return GraphStatsResponse(
            entity_count=stats.get("entity_count", 0),
            relationship_count=stats.get("relationship_count", 0),
            event_count=stats.get("event_count", 0),
            entity_type_distribution=stats.get("entity_type_distribution", {}),
            relationship_type_distribution=stats.get("relationship_type_distribution", {}),
            most_connected_entities=stats.get("most_connected_entities", []),
            average_connections=stats.get("average_connections", 0.0),
            metadata=stats.get("metadata", {}),
        )

    except ValueError as e:
        logger.error(f"Validation error getting graph stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting graph stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving graph statistics: {str(e)}",
        )
