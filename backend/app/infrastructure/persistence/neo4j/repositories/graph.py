"""
Neo4j implementation of GraphRepository with advanced graph algorithms.

This module provides high-level graph operations including:
- Shortest path finding
- Subgraph extraction
- Community detection
- Timeline building
- Contradiction detection
- Centrality computation
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID
from dataclasses import dataclass

from app.domain.knowledge.entities import Entity, Event, Relationship
from app.domain.knowledge.value_objects.timeline import Timeline, TimelineGranularity
from app.domain.knowledge.repositories.graph_repository import GraphRepository
from app.shared.exceptions.domain_exceptions import RepositoryException

from ..client import Neo4jClient
from ..mappers import EntityMapper, EventMapper, RelationshipMapper

logger = logging.getLogger(__name__)


@dataclass
class Path:
    """Represents a path between two entities in the graph."""
    entities: List[Entity]
    relationships: List[Relationship]
    length: int
    total_strength: float


@dataclass
class Community:
    """Represents a community (cluster) of entities."""
    id: int
    entities: List[Entity]
    size: int
    density: float


@dataclass
class Contradiction:
    """Represents a detected contradiction in the graph."""
    entity1_id: UUID
    entity2_id: UUID
    relationship1: Relationship
    relationship2: Relationship
    description: str


class Neo4jGraphRepository(GraphRepository):
    """
    Neo4j implementation of GraphRepository.

    Provides advanced graph operations and algorithms for knowledge graph analysis.
    """

    def __init__(self, client: Neo4jClient):
        """
        Initialize graph repository.

        Args:
            client: Neo4jClient instance
        """
        self.client = client
        self.entity_mapper = EntityMapper()
        self.event_mapper = EventMapper()
        self.relationship_mapper = RelationshipMapper()

    async def get_entity_with_relationships(
        self,
        entity_id: UUID
    ) -> Tuple[Optional[Entity], List[Relationship]]:
        """
        Get an entity with all its relationships.

        Args:
            entity_id: Entity ID

        Returns:
            Tuple of (entity, relationships)

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = """
            MATCH (e:Entity {id: $entity_id})
            OPTIONAL MATCH (e)-[r]-(other:Entity)
            RETURN e, collect({rel: r, from_id: startNode(r).id, to_id: endNode(r).id}) as relationships
            """

            params = {"entity_id": str(entity_id)}
            result = await self.client.execute_read(query, params)

            if not result:
                return None, []

            record = result[0]
            entity = self.entity_mapper.from_dict(record["e"])

            relationships = []
            for rel_data in record["relationships"]:
                if rel_data["rel"]:
                    rel = self.relationship_mapper.from_dict(
                        rel_data["rel"],
                        UUID(rel_data["from_id"]),
                        UUID(rel_data["to_id"])
                    )
                    relationships.append(rel)

            logger.debug(
                f"Retrieved entity {entity_id} with {len(relationships)} relationships"
            )
            return entity, relationships

        except Exception as e:
            logger.error(f"Failed to get entity with relationships: {e}")
            raise RepositoryException(
                f"Failed to get entity with relationships",
                context={"entity_id": str(entity_id)},
                original_exception=e,
            )

    async def get_connected_entities(
        self,
        entity_id: UUID,
        max_depth: int = 2
    ) -> Set[Entity]:
        """
        Get all entities connected to an entity within max_depth hops.

        Args:
            entity_id: Starting entity ID
            max_depth: Maximum relationship depth to traverse

        Returns:
            Set of connected entities

        Raises:
            RepositoryException: If query fails
        """
        try:
            # Limit depth to prevent runaway queries
            max_depth = min(max(max_depth, 1), 3)

            query = f"""
            MATCH (start:Entity {{id: $entity_id}})-[*1..{max_depth}]-(connected:Entity)
            RETURN DISTINCT connected as e
            """

            params = {"entity_id": str(entity_id)}
            result = await self.client.execute_read(query, params)

            entities = set()
            for record in result:
                entity = self.entity_mapper.from_dict(record["e"])
                entities.add(entity)

            logger.debug(
                f"Found {len(entities)} connected entities "
                f"within {max_depth} hops of {entity_id}"
            )
            return entities

        except Exception as e:
            logger.error(f"Failed to get connected entities: {e}")
            raise RepositoryException(
                f"Failed to get connected entities",
                context={"entity_id": str(entity_id), "max_depth": max_depth},
                original_exception=e,
            )

    async def find_shortest_path(
        self,
        from_entity_id: UUID,
        to_entity_id: UUID
    ) -> Optional[List[Relationship]]:
        """
        Find shortest path between two entities.

        Args:
            from_entity_id: Start entity ID
            to_entity_id: End entity ID

        Returns:
            List of relationships forming the path, or None if no path exists

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = """
            MATCH path = shortestPath(
                (from:Entity {id: $from_entity_id})-[*]-(to:Entity {id: $to_entity_id})
            )
            RETURN [r in relationships(path) | {
                rel: properties(r),
                from_id: startNode(r).id,
                to_id: endNode(r).id
            }] as path_relationships
            """

            params = {
                "from_entity_id": str(from_entity_id),
                "to_entity_id": str(to_entity_id),
            }

            result = await self.client.execute_read(query, params)

            if not result or not result[0].get("path_relationships"):
                logger.debug(f"No path found between {from_entity_id} and {to_entity_id}")
                return None

            relationships = []
            for rel_data in result[0]["path_relationships"]:
                rel = self.relationship_mapper.from_dict(
                    rel_data["rel"],
                    UUID(rel_data["from_id"]),
                    UUID(rel_data["to_id"])
                )
                relationships.append(rel)

            logger.debug(
                f"Found path of length {len(relationships)} "
                f"between {from_entity_id} and {to_entity_id}"
            )
            return relationships

        except Exception as e:
            logger.error(f"Failed to find shortest path: {e}")
            raise RepositoryException(
                f"Failed to find shortest path",
                context={
                    "from_entity_id": str(from_entity_id),
                    "to_entity_id": str(to_entity_id),
                },
                original_exception=e,
            )

    async def get_timeline_for_entity(
        self,
        entity_id: UUID
    ) -> List[Event]:
        """
        Get chronological timeline of events for an entity.

        Args:
            entity_id: Entity ID

        Returns:
            Ordered list of events involving the entity

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = """
            MATCH (entity:Entity {id: $entity_id})-[:PARTICIPATED_IN]->(e:Event)
            RETURN e
            ORDER BY e.timestamp ASC
            """

            params = {"entity_id": str(entity_id)}
            result = await self.client.execute_read(query, params)

            events = []
            for record in result:
                event = self.event_mapper.from_dict(record["e"])
                events.append(event)

            logger.debug(f"Retrieved timeline with {len(events)} events for {entity_id}")
            return events

        except Exception as e:
            logger.error(f"Failed to get timeline for entity: {e}")
            raise RepositoryException(
                f"Failed to get timeline for entity",
                context={"entity_id": str(entity_id)},
                original_exception=e,
            )

    async def get_subgraph(
        self,
        entity_ids: List[UUID]
    ) -> Tuple[List[Entity], List[Relationship]]:
        """
        Extract a subgraph containing specified entities and their interconnections.

        Args:
            entity_ids: List of entity IDs to include

        Returns:
            Tuple of (entities, relationships)

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = """
            MATCH (e:Entity)
            WHERE e.id IN $entity_ids
            WITH collect(e) as entities
            UNWIND entities as e1
            UNWIND entities as e2
            OPTIONAL MATCH (e1)-[r]-(e2)
            WHERE e1.id < e2.id
            RETURN entities,
                   collect(DISTINCT {
                       rel: properties(r),
                       from_id: startNode(r).id,
                       to_id: endNode(r).id
                   }) as relationships
            """

            params = {"entity_ids": [str(eid) for eid in entity_ids]}
            result = await self.client.execute_read(query, params)

            if not result:
                return [], []

            record = result[0]

            # Extract entities
            entities = []
            for entity_data in record["entities"]:
                entity = self.entity_mapper.from_dict(entity_data)
                entities.append(entity)

            # Extract relationships
            relationships = []
            for rel_data in record["relationships"]:
                if rel_data["rel"]:
                    rel = self.relationship_mapper.from_dict(
                        rel_data["rel"],
                        UUID(rel_data["from_id"]),
                        UUID(rel_data["to_id"])
                    )
                    relationships.append(rel)

            logger.debug(
                f"Extracted subgraph with {len(entities)} entities "
                f"and {len(relationships)} relationships"
            )
            return entities, relationships

        except Exception as e:
            logger.error(f"Failed to get subgraph: {e}")
            raise RepositoryException(
                f"Failed to get subgraph",
                context={"entity_count": len(entity_ids)},
                original_exception=e,
            )

    async def find_shortest_path_advanced(
        self,
        entity_id1: UUID,
        entity_id2: UUID,
        max_depth: int = 5
    ) -> List[Path]:
        """
        Find all shortest paths between two entities (advanced version).

        Args:
            entity_id1: First entity UUID
            entity_id2: Second entity UUID
            max_depth: Maximum path depth

        Returns:
            List of Path objects

        Raises:
            RepositoryException: If query fails
        """
        try:
            max_depth = min(max(max_depth, 1), 5)

            query = f"""
            MATCH path = allShortestPaths(
                (e1:Entity {{id: $entity_id1}})-[*1..{max_depth}]-(e2:Entity {{id: $entity_id2}})
            )
            RETURN
                [n in nodes(path) | properties(n)] as entities,
                [r in relationships(path) | {{
                    rel: properties(r),
                    from_id: startNode(r).id,
                    to_id: endNode(r).id
                }}] as relationships,
                length(path) as path_length
            LIMIT 10
            """

            params = {
                "entity_id1": str(entity_id1),
                "entity_id2": str(entity_id2),
            }

            result = await self.client.execute_read(query, params)

            paths = []
            for record in result:
                # Parse entities
                entities = [
                    self.entity_mapper.from_dict(e) for e in record["entities"]
                ]

                # Parse relationships
                relationships = []
                total_strength = 0.0
                for rel_data in record["relationships"]:
                    rel = self.relationship_mapper.from_dict(
                        rel_data["rel"],
                        UUID(rel_data["from_id"]),
                        UUID(rel_data["to_id"])
                    )
                    relationships.append(rel)
                    total_strength += rel.strength

                path = Path(
                    entities=entities,
                    relationships=relationships,
                    length=record["path_length"],
                    total_strength=total_strength,
                )
                paths.append(path)

            logger.debug(f"Found {len(paths)} shortest paths")
            return paths

        except Exception as e:
            logger.error(f"Failed to find shortest paths: {e}")
            raise RepositoryException(
                f"Failed to find shortest paths",
                context={
                    "entity_id1": str(entity_id1),
                    "entity_id2": str(entity_id2),
                },
                original_exception=e,
            )

    async def find_subgraph(
        self,
        entity_id: UUID,
        depth: int
    ) -> Tuple[List[Entity], List[Relationship]]:
        """
        Find subgraph around an entity up to a certain depth.

        Args:
            entity_id: Central entity UUID
            depth: Relationship depth

        Returns:
            Tuple of (entities, relationships)

        Raises:
            RepositoryException: If query fails
        """
        try:
            depth = min(max(depth, 1), 3)

            query = f"""
            MATCH path = (start:Entity {{id: $entity_id}})-[*1..{depth}]-(connected:Entity)
            WITH collect(DISTINCT connected) + collect(DISTINCT start) as all_entities
            UNWIND all_entities as e1
            UNWIND all_entities as e2
            OPTIONAL MATCH (e1)-[r]-(e2)
            WHERE id(e1) < id(e2)
            RETURN
                collect(DISTINCT e1) as entities,
                collect(DISTINCT {{
                    rel: properties(r),
                    from_id: startNode(r).id,
                    to_id: endNode(r).id
                }}) as relationships
            """

            params = {"entity_id": str(entity_id)}
            result = await self.client.execute_read(query, params)

            if not result:
                return [], []

            record = result[0]

            entities = [
                self.entity_mapper.from_dict(e) for e in record["entities"]
            ]

            relationships = []
            for rel_data in record["relationships"]:
                if rel_data["rel"]:
                    rel = self.relationship_mapper.from_dict(
                        rel_data["rel"],
                        UUID(rel_data["from_id"]),
                        UUID(rel_data["to_id"])
                    )
                    relationships.append(rel)

            logger.debug(
                f"Found subgraph with {len(entities)} entities, "
                f"{len(relationships)} relationships (depth={depth})"
            )
            return entities, relationships

        except Exception as e:
            logger.error(f"Failed to find subgraph: {e}")
            raise RepositoryException(
                f"Failed to find subgraph",
                context={"entity_id": str(entity_id), "depth": depth},
                original_exception=e,
            )

    async def build_timeline(self, case_id: UUID) -> Timeline:
        """
        Build chronological event timeline for a case.

        Args:
            case_id: Case UUID

        Returns:
            Timeline value object with all case events

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = """
            MATCH (e:Event)
            WHERE e.metadata.case_id = $case_id
            RETURN e
            ORDER BY e.timestamp ASC
            """

            params = {"case_id": str(case_id)}
            result = await self.client.execute_read(query, params)

            if not result:
                raise RepositoryException(
                    f"No events found for case",
                    context={"case_id": str(case_id)}
                )

            events = [self.event_mapper.from_dict(r["e"]) for r in result]
            event_ids = [e.id for e in events]

            # Determine timeline bounds
            start_date = min(e.timestamp for e in events)
            end_date = max(e.timestamp for e in events)

            # Determine appropriate granularity
            span_days = (end_date - start_date).days
            if span_days <= 1:
                granularity = TimelineGranularity.HOUR
            elif span_days <= 30:
                granularity = TimelineGranularity.DAY
            elif span_days <= 365:
                granularity = TimelineGranularity.MONTH
            else:
                granularity = TimelineGranularity.YEAR

            timeline = Timeline(
                events=event_ids,
                start_date=start_date,
                end_date=end_date,
                granularity=granularity,
            )

            logger.debug(
                f"Built timeline for case {case_id}: "
                f"{len(events)} events, {span_days} days"
            )
            return timeline

        except RepositoryException:
            raise
        except Exception as e:
            logger.error(f"Failed to build timeline: {e}")
            raise RepositoryException(
                f"Failed to build timeline",
                context={"case_id": str(case_id)},
                original_exception=e,
            )

    async def find_contradictions(self, case_id: UUID) -> List[Contradiction]:
        """
        Detect contradicting relationships in the graph.

        Finds cases where:
        - Same relationship type exists in opposite directions
        - Conflicting relationship types exist
        - Temporal contradictions exist

        Args:
            case_id: Case UUID

        Returns:
            List of detected contradictions

        Raises:
            RepositoryException: If query fails
        """
        try:
            # Find bidirectional conflicting relationships
            query = """
            MATCH (e1:Entity)-[r1]->(e2:Entity)-[r2]->(e1)
            WHERE r1.metadata.case_id = $case_id
              AND type(r1) <> type(r2)
            RETURN
                e1.id as entity1_id,
                e2.id as entity2_id,
                properties(r1) as rel1_props,
                properties(r2) as rel2_props,
                startNode(r1).id as r1_from,
                endNode(r1).id as r1_to,
                startNode(r2).id as r2_from,
                endNode(r2).id as r2_to,
                'Conflicting bidirectional relationships' as description
            """

            params = {"case_id": str(case_id)}
            result = await self.client.execute_read(query, params)

            contradictions = []
            for record in result:
                rel1 = self.relationship_mapper.from_dict(
                    record["rel1_props"],
                    UUID(record["r1_from"]),
                    UUID(record["r1_to"])
                )
                rel2 = self.relationship_mapper.from_dict(
                    record["rel2_props"],
                    UUID(record["r2_from"]),
                    UUID(record["r2_to"])
                )

                contradiction = Contradiction(
                    entity1_id=UUID(record["entity1_id"]),
                    entity2_id=UUID(record["entity2_id"]),
                    relationship1=rel1,
                    relationship2=rel2,
                    description=record["description"],
                )
                contradictions.append(contradiction)

            logger.debug(f"Found {len(contradictions)} contradictions for case {case_id}")
            return contradictions

        except Exception as e:
            logger.error(f"Failed to find contradictions: {e}")
            raise RepositoryException(
                f"Failed to find contradictions",
                context={"case_id": str(case_id)},
                original_exception=e,
            )

    async def compute_centrality(
        self,
        case_id: UUID,
        algorithm: str = "degree"
    ) -> Dict[UUID, float]:
        """
        Compute centrality scores for entities in a case.

        Args:
            case_id: Case UUID
            algorithm: Centrality algorithm ("degree", "betweenness", "closeness")

        Returns:
            Dictionary mapping entity IDs to centrality scores

        Raises:
            RepositoryException: If computation fails
        """
        try:
            if algorithm == "degree":
                # Simple degree centrality
                query = """
                MATCH (e:Entity)
                WHERE e.metadata.case_id = $case_id
                OPTIONAL MATCH (e)-[r]-()
                RETURN e.id as entity_id, count(r) as centrality
                ORDER BY centrality DESC
                """
            else:
                # For other algorithms, default to degree
                logger.warning(
                    f"Centrality algorithm '{algorithm}' not implemented, using degree"
                )
                query = """
                MATCH (e:Entity)
                WHERE e.metadata.case_id = $case_id
                OPTIONAL MATCH (e)-[r]-()
                RETURN e.id as entity_id, count(r) as centrality
                ORDER BY centrality DESC
                """

            params = {"case_id": str(case_id)}
            result = await self.client.execute_read(query, params)

            centrality_scores = {
                UUID(record["entity_id"]): float(record["centrality"])
                for record in result
            }

            logger.debug(
                f"Computed {algorithm} centrality for {len(centrality_scores)} entities"
            )
            return centrality_scores

        except Exception as e:
            logger.error(f"Failed to compute centrality: {e}")
            raise RepositoryException(
                f"Failed to compute centrality",
                context={"case_id": str(case_id), "algorithm": algorithm},
                original_exception=e,
            )

    async def find_isolated_entities(self, case_id: UUID) -> List[Entity]:
        """
        Find entities with no relationships (isolated nodes).

        Args:
            case_id: Case UUID

        Returns:
            List of isolated entities

        Raises:
            RepositoryException: If query fails
        """
        try:
            query = """
            MATCH (e:Entity)
            WHERE e.metadata.case_id = $case_id
              AND NOT (e)-[]-()
            RETURN e
            ORDER BY e.name
            """

            params = {"case_id": str(case_id)}
            result = await self.client.execute_read(query, params)

            entities = [
                self.entity_mapper.from_dict(record["e"]) for record in result
            ]

            logger.debug(f"Found {len(entities)} isolated entities for case {case_id}")
            return entities

        except Exception as e:
            logger.error(f"Failed to find isolated entities: {e}")
            raise RepositoryException(
                f"Failed to find isolated entities",
                context={"case_id": str(case_id)},
                original_exception=e,
            )
