"""
Pydantic schemas for knowledge graph API requests and responses.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field

from app.shared.types.enums import EntityType, RelationshipType


class EntityResponse(BaseModel):
    """
    Schema for entity in the knowledge graph.
    """

    id: UUID = Field(..., description="Unique entity identifier")
    entity_type: EntityType = Field(..., description="Type of entity")
    name: str = Field(..., description="Primary entity name")
    aliases: List[str] = Field(default_factory=list, description="Alternative names")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for entity extraction"
    )
    attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Entity attributes (role, title, etc.)"
    )
    first_seen: Optional[datetime] = Field(None, description="First mention timestamp")
    last_seen: Optional[datetime] = Field(None, description="Last mention timestamp")
    mention_count: int = Field(0, ge=0, description="Number of mentions in evidence")

    @classmethod
    def from_dto(cls, dto: Any) -> "EntityResponse":
        """Create schema from DTO."""
        return cls(
            id=dto.id,
            entity_type=dto.entity_type,
            name=dto.name,
            aliases=dto.aliases,
            confidence=getattr(dto, "confidence", 1.0),
            attributes=dto.attributes,
            first_seen=dto.first_seen,
            last_seen=dto.last_seen,
            mention_count=getattr(dto, "mention_count", 0),
        )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "entity_type": "PERSON",
                "name": "John Doe",
                "aliases": ["J. Doe", "Jonathan Doe"],
                "confidence": 0.95,
                "attributes": {
                    "role": "CEO",
                    "company": "Acme Corp"
                },
                "first_seen": "2024-01-15T10:00:00Z",
                "last_seen": "2024-03-20T14:30:00Z",
                "mention_count": 42
            }
        }
    }


class RelationshipResponse(BaseModel):
    """
    Schema for relationship between entities.
    """

    id: UUID = Field(..., description="Unique relationship identifier")
    from_entity_id: UUID = Field(..., description="Source entity ID")
    to_entity_id: UUID = Field(..., description="Target entity ID")
    relationship_type: RelationshipType = Field(..., description="Type of relationship")
    strength: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relationship strength (0.0-1.0)"
    )
    temporal_start: Optional[datetime] = Field(
        None,
        description="Relationship start time"
    )
    temporal_end: Optional[datetime] = Field(
        None,
        description="Relationship end time"
    )
    source_count: int = Field(
        0,
        ge=0,
        description="Number of sources supporting relationship"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional relationship metadata"
    )

    @classmethod
    def from_dto(cls, dto: Any) -> "RelationshipResponse":
        """Create schema from DTO."""
        return cls(
            id=dto.id,
            from_entity_id=dto.from_entity_id,
            to_entity_id=dto.to_entity_id,
            relationship_type=dto.relationship_type,
            strength=dto.strength,
            temporal_start=dto.temporal_start,
            temporal_end=dto.temporal_end,
            source_count=len(dto.source_citations) if hasattr(dto, "source_citations") else 0,
            metadata=dto.metadata,
        )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "from_entity_id": "123e4567-e89b-12d3-a456-426614174000",
                "to_entity_id": "123e4567-e89b-12d3-a456-426614174002",
                "relationship_type": "WORKS_FOR",
                "strength": 0.95,
                "temporal_start": "2020-01-01T00:00:00Z",
                "temporal_end": None,
                "source_count": 5,
                "metadata": {
                    "position": "CEO",
                    "department": "Executive"
                }
            }
        }
    }


class EntitiesResponse(BaseModel):
    """
    Response schema for list of entities.
    """

    entities: List[EntityResponse] = Field(
        default_factory=list,
        description="List of entities"
    )
    total: int = Field(..., ge=0, description="Total number of entities")
    filters_applied: Dict[str, Any] = Field(
        default_factory=dict,
        description="Filters that were applied"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "entities": [],
                "total": 150,
                "filters_applied": {
                    "entity_types": ["PERSON", "ORGANIZATION"],
                    "case_id": "123e4567-e89b-12d3-a456-426614174099"
                }
            }
        }
    }


class EntityDetailResponse(BaseModel):
    """
    Detailed entity response with relationships.
    """

    entity: EntityResponse = Field(..., description="The entity")
    relationships: List[RelationshipResponse] = Field(
        default_factory=list,
        description="Direct relationships"
    )
    related_entities: List[EntityResponse] = Field(
        default_factory=list,
        description="Entities connected via relationships"
    )
    total_relationships: int = Field(
        0,
        ge=0,
        description="Total relationship count"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "entity": {},
                "relationships": [],
                "related_entities": [],
                "total_relationships": 12
            }
        }
    }


class PathResponse(BaseModel):
    """
    Response schema for path between entities.
    """

    path_exists: bool = Field(..., description="Whether a path exists")
    entities: List[EntityResponse] = Field(
        default_factory=list,
        description="Entities in the path (ordered)"
    )
    relationships: List[RelationshipResponse] = Field(
        default_factory=list,
        description="Relationships connecting the path"
    )
    path_length: int = Field(0, ge=0, description="Number of hops in path")
    total_strength: float = Field(
        0.0,
        ge=0.0,
        description="Combined strength of path"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "path_exists": True,
                "entities": [],
                "relationships": [],
                "path_length": 3,
                "total_strength": 0.85
            }
        }
    }


class TimelineEventResponse(BaseModel):
    """
    Schema for timeline event.
    """

    id: UUID = Field(..., description="Event identifier")
    event_type: str = Field(..., description="Type of event")
    description: str = Field(..., description="Event description")
    timestamp: datetime = Field(..., description="Event timestamp")
    participants: List[EntityResponse] = Field(
        default_factory=list,
        description="Entities participating in event"
    )
    location: Optional[str] = Field(None, description="Event location")
    duration: Optional[float] = Field(None, description="Duration in seconds")
    source_citations: List[UUID] = Field(
        default_factory=list,
        description="Evidence sources for event"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event metadata"
    )

    @classmethod
    def from_dto(cls, dto: Any) -> "TimelineEventResponse":
        """Create schema from DTO."""
        return cls(
            id=dto.id,
            event_type=dto.event_type,
            description=dto.description,
            timestamp=dto.timestamp,
            participants=[EntityResponse.from_dto(p) for p in getattr(dto, "participants", [])],
            location=dto.location if isinstance(dto.location, str) else None,
            duration=dto.duration,
            source_citations=dto.source_citations,
            metadata=dto.metadata,
        )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "event_type": "MEETING",
                "description": "Contract negotiation meeting at Acme Corp headquarters",
                "timestamp": "2024-03-15T14:30:00Z",
                "participants": [],
                "location": "Acme Corp HQ",
                "duration": 3600.0,
                "source_citations": [
                    "123e4567-e89b-12d3-a456-426614174001"
                ],
                "metadata": {
                    "room": "Conference Room A",
                    "attendees_count": 5
                }
            }
        }
    }


class TimelineResponse(BaseModel):
    """
    Response schema for case timeline.
    """

    events: List[TimelineEventResponse] = Field(
        default_factory=list,
        description="Timeline events (chronologically ordered)"
    )
    start_date: Optional[datetime] = Field(
        None,
        description="Timeline start date"
    )
    end_date: Optional[datetime] = Field(
        None,
        description="Timeline end date"
    )
    total_events: int = Field(0, ge=0, description="Total number of events")
    filters_applied: Dict[str, Any] = Field(
        default_factory=dict,
        description="Filters that were applied"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "events": [],
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-12-31T23:59:59Z",
                "total_events": 45,
                "filters_applied": {
                    "case_id": "123e4567-e89b-12d3-a456-426614174099",
                    "entity_id": "123e4567-e89b-12d3-a456-426614174000"
                }
            }
        }
    }


class GraphNodeSchema(BaseModel):
    """
    Schema for graph visualization node.
    """

    id: str = Field(..., description="Node identifier (string for viz)")
    label: str = Field(..., description="Node display label")
    type: str = Field(..., description="Node type")
    size: int = Field(10, ge=1, description="Visual size")
    color: Optional[str] = Field(None, description="Node color")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional node data"
    )


class GraphEdgeSchema(BaseModel):
    """
    Schema for graph visualization edge.
    """

    id: str = Field(..., description="Edge identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    label: str = Field(..., description="Edge display label")
    strength: float = Field(1.0, ge=0.0, le=1.0, description="Edge strength/weight")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional edge data"
    )


class SubgraphResponse(BaseModel):
    """
    Response schema for entity subgraph (for visualization).
    """

    nodes: List[GraphNodeSchema] = Field(
        default_factory=list,
        description="Graph nodes"
    )
    edges: List[GraphEdgeSchema] = Field(
        default_factory=list,
        description="Graph edges"
    )
    center_entity_id: UUID = Field(..., description="Central entity ID")
    depth: int = Field(..., ge=1, description="Traversal depth")
    node_count: int = Field(0, ge=0, description="Total nodes")
    edge_count: int = Field(0, ge=0, description="Total edges")

    model_config = {
        "json_schema_extra": {
            "example": {
                "nodes": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "label": "John Doe",
                        "type": "PERSON",
                        "size": 15,
                        "color": "#4A90E2"
                    }
                ],
                "edges": [
                    {
                        "id": "edge-1",
                        "source": "123e4567-e89b-12d3-a456-426614174000",
                        "target": "123e4567-e89b-12d3-a456-426614174001",
                        "label": "WORKS_FOR",
                        "strength": 0.95
                    }
                ],
                "center_entity_id": "123e4567-e89b-12d3-a456-426614174000",
                "depth": 2,
                "node_count": 25,
                "edge_count": 38
            }
        }
    }


class GraphStatsResponse(BaseModel):
    """
    Response schema for graph statistics.
    """

    entity_count: int = Field(0, ge=0, description="Total entities")
    relationship_count: int = Field(0, ge=0, description="Total relationships")
    event_count: int = Field(0, ge=0, description="Total events")
    entity_type_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Count by entity type"
    )
    relationship_type_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Count by relationship type"
    )
    most_connected_entities: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Entities with most connections"
    )
    average_connections: float = Field(
        0.0,
        ge=0.0,
        description="Average connections per entity"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional statistics"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "entity_count": 150,
                "relationship_count": 320,
                "event_count": 45,
                "entity_type_distribution": {
                    "PERSON": 85,
                    "ORGANIZATION": 40,
                    "LOCATION": 25
                },
                "relationship_type_distribution": {
                    "WORKS_FOR": 50,
                    "KNOWS": 120,
                    "LOCATED_AT": 30
                },
                "most_connected_entities": [
                    {
                        "entity_id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "John Doe",
                        "connection_count": 42
                    }
                ],
                "average_connections": 4.27,
                "metadata": {
                    "graph_density": 0.15,
                    "clustering_coefficient": 0.42
                }
            }
        }
    }
