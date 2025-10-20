"""Knowledge domain repository interfaces."""

from .graph_repository import (
    EntityRepository,
    EventRepository,
    RelationshipRepository,
    GraphRepository,
)

__all__ = [
    "EntityRepository",
    "EventRepository",
    "RelationshipRepository",
    "GraphRepository",
]
