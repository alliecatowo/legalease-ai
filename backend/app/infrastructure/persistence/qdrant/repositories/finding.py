"""
Finding vector repository for Qdrant operations.

Handles indexing and searching of research findings with support for
deduplication and entity-based retrieval.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

from qdrant_client.models import (
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
)

from app.infrastructure.persistence.qdrant.repositories.base import BaseQdrantRepository
from app.infrastructure.persistence.qdrant.collection_manager import CollectionName
from app.infrastructure.exceptions import IndexingException, SearchException
from app.domain.research.entities.finding import Finding

logger = logging.getLogger(__name__)


class QdrantFindingRepository(BaseQdrantRepository):
    """
    Repository for finding vector operations in Qdrant.

    Manages research finding embeddings with support for:
    - Similarity search for deduplication
    - Entity-based retrieval
    - Research run filtering
    - Confidence and relevance filtering
    """

    def __init__(self):
        """Initialize finding vector repository."""
        super().__init__(collection_name=CollectionName.FINDINGS.value)

    async def index_findings(
        self,
        findings: List[Finding],
        embeddings: List[List[float]],
        sparse_vectors: Optional[List[Any]] = None,
    ) -> bool:
        """
        Index findings with embeddings.

        Args:
            findings: List of Finding entities
            embeddings: List of dense embeddings (one per finding)
            sparse_vectors: Optional BM25 sparse vectors

        Returns:
            True if indexing successful

        Raises:
            IndexingException: If indexing fails
        """
        if len(findings) == 0:
            logger.warning("No findings to index")
            return True

        if len(embeddings) != len(findings):
            raise IndexingException(
                "Embedding count mismatch with findings",
                context={
                    "findings": len(findings),
                    "embeddings": len(embeddings),
                },
            )

        # Build points
        points = []
        for i, finding in enumerate(findings):
            # Build vector dict
            vector_dict = {"dense": embeddings[i]}

            # Add sparse vector if provided
            if sparse_vectors and i < len(sparse_vectors):
                vector_dict["bm25"] = sparse_vectors[i]

            # Build payload
            payload = {
                "finding_id": str(finding.id),
                "research_run_id": str(finding.research_run_id),
                "finding_type": finding.finding_type.value,
                "text": finding.text,
                "entity_ids": [str(eid) for eid in finding.entities],
                "citation_ids": [str(cid) for cid in finding.citations],
                "confidence": finding.confidence,
                "relevance": finding.relevance,
                "tags": finding.tags,
            }

            # Add metadata
            payload.update(finding.metadata)

            # Create point with finding ID
            point_id = str(finding.id)

            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector_dict,
                    payload=payload,
                )
            )

        # Upsert points
        logger.info(f"Indexing {len(points)} findings")
        return await self.upsert_points(points)

    async def search_similar_findings(
        self,
        query_embedding: List[float],
        research_run_id: Optional[UUID] = None,
        finding_types: Optional[List[str]] = None,
        min_confidence: Optional[float] = None,
        min_relevance: Optional[float] = None,
        tags: Optional[List[str]] = None,
        top_k: int = 10,
        score_threshold: Optional[float] = 0.8,
        sparse_vector: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar findings (useful for deduplication).

        Args:
            query_embedding: Dense query embedding of a finding
            research_run_id: Optional filter by research run
            finding_types: Optional filter by finding types
            min_confidence: Optional minimum confidence threshold
            min_relevance: Optional minimum relevance threshold
            tags: Optional filter by tags (must have at least one)
            top_k: Number of results to return
            score_threshold: Minimum similarity score (default 0.8 for dedup)
            sparse_vector: Optional BM25 sparse vector

        Returns:
            List of similar findings with scores

        Raises:
            SearchException: If search fails
        """
        # Build filters
        filter_conditions = []

        # Research run filter
        if research_run_id:
            filter_conditions.append(
                FieldCondition(
                    key="research_run_id",
                    match=MatchValue(value=str(research_run_id)),
                )
            )

        # Finding type filter
        if finding_types:
            if len(finding_types) == 1:
                filter_conditions.append(
                    FieldCondition(
                        key="finding_type",
                        match=MatchValue(value=finding_types[0]),
                    )
                )
            else:
                filter_conditions.append(
                    FieldCondition(
                        key="finding_type",
                        match=MatchAny(any=finding_types),
                    )
                )

        # Confidence filter
        if min_confidence is not None:
            filter_conditions.append(
                FieldCondition(
                    key="confidence",
                    range={"gte": min_confidence},
                )
            )

        # Relevance filter
        if min_relevance is not None:
            filter_conditions.append(
                FieldCondition(
                    key="relevance",
                    range={"gte": min_relevance},
                )
            )

        # Tag filter (at least one tag matches)
        if tags:
            if len(tags) == 1:
                filter_conditions.append(
                    FieldCondition(
                        key="tags",
                        match=MatchValue(value=tags[0]),
                    )
                )
            else:
                filter_conditions.append(
                    FieldCondition(
                        key="tags",
                        match=MatchAny(any=tags),
                    )
                )

        filters = Filter(must=filter_conditions) if filter_conditions else None

        # Perform hybrid search
        query_vectors = {"dense": query_embedding}

        return await self.search_hybrid(
            query_vectors=query_vectors,
            query_sparse_vector=sparse_vector,
            filters=filters,
            top_k=top_k,
            score_threshold=score_threshold,
        )

    async def search_by_entity(
        self,
        entity_id: UUID,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search findings that reference a specific entity.

        Args:
            entity_id: UUID of the entity
            top_k: Maximum number of findings to return

        Returns:
            List of findings referencing the entity

        Raises:
            SearchException: If search fails
        """
        try:
            async with self.client.get_client() as qdrant:
                filters = Filter(
                    must=[
                        FieldCondition(
                            key="entity_ids",
                            match=MatchValue(value=str(entity_id)),
                        )
                    ]
                )

                results = []
                offset = None
                scroll_limit = min(top_k, 100) if top_k else 100

                while True:
                    scroll_result = await qdrant.scroll(
                        collection_name=self.collection_name,
                        scroll_filter=filters,
                        limit=scroll_limit,
                        offset=offset,
                        with_payload=True,
                        with_vectors=False,
                    )

                    points, next_offset = scroll_result

                    for point in points:
                        results.append({
                            "id": point.id,
                            "payload": point.payload,
                        })

                    if top_k and len(results) >= top_k:
                        results = results[:top_k]
                        break

                    if next_offset is None:
                        break

                    offset = next_offset

                # Sort by relevance (descending)
                results.sort(
                    key=lambda x: x["payload"].get("relevance", 0),
                    reverse=True,
                )

                return results

        except Exception as e:
            raise SearchException(
                f"Failed to search findings by entity {entity_id}",
                cause=e,
                context={"entity_id": str(entity_id)},
            )

    async def delete_research_run_findings(self, research_run_id: UUID) -> bool:
        """
        Delete all findings for a research run.

        Args:
            research_run_id: UUID of the research run

        Returns:
            True if successful

        Raises:
            DeletionException: If deletion fails
        """
        filter_conditions = Filter(
            must=[
                FieldCondition(
                    key="research_run_id",
                    match=MatchValue(value=str(research_run_id)),
                )
            ]
        )

        logger.info(
            f"Deleting all findings for research run {research_run_id} from vector store"
        )
        return await self.delete_by_filter(filter_conditions)

    async def get_research_run_findings(
        self,
        research_run_id: UUID,
        finding_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
        min_relevance: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all findings for a research run with optional filtering.

        Args:
            research_run_id: UUID of the research run
            finding_type: Optional filter by finding type
            min_confidence: Optional minimum confidence threshold
            min_relevance: Optional minimum relevance threshold

        Returns:
            List of finding payloads sorted by relevance

        Raises:
            SearchException: If retrieval fails
        """
        try:
            async with self.client.get_client() as qdrant:
                # Build filter
                filter_conditions = [
                    FieldCondition(
                        key="research_run_id",
                        match=MatchValue(value=str(research_run_id)),
                    )
                ]

                if finding_type:
                    filter_conditions.append(
                        FieldCondition(
                            key="finding_type",
                            match=MatchValue(value=finding_type),
                        )
                    )

                if min_confidence is not None:
                    filter_conditions.append(
                        FieldCondition(
                            key="confidence",
                            range={"gte": min_confidence},
                        )
                    )

                if min_relevance is not None:
                    filter_conditions.append(
                        FieldCondition(
                            key="relevance",
                            range={"gte": min_relevance},
                        )
                    )

                filters = Filter(must=filter_conditions)

                # Scroll through all matching points
                results = []
                offset = None

                while True:
                    scroll_result = await qdrant.scroll(
                        collection_name=self.collection_name,
                        scroll_filter=filters,
                        limit=100,
                        offset=offset,
                        with_payload=True,
                        with_vectors=False,
                    )

                    points, next_offset = scroll_result

                    for point in points:
                        results.append({
                            "id": point.id,
                            "payload": point.payload,
                        })

                    if next_offset is None:
                        break

                    offset = next_offset

                # Sort by relevance (descending), then confidence
                results.sort(
                    key=lambda x: (
                        -x["payload"].get("relevance", 0),
                        -x["payload"].get("confidence", 0),
                    )
                )

                return results

        except Exception as e:
            raise SearchException(
                f"Failed to get findings for research run {research_run_id}",
                cause=e,
                context={"research_run_id": str(research_run_id)},
            )

    async def check_duplicate_finding(
        self,
        finding_text: str,
        finding_embedding: List[float],
        research_run_id: UUID,
        similarity_threshold: float = 0.9,
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a similar finding already exists (for deduplication).

        Args:
            finding_text: Text of the finding to check
            finding_embedding: Embedding of the finding
            research_run_id: Research run to check within
            similarity_threshold: Threshold for considering findings duplicates

        Returns:
            Existing finding if duplicate found, None otherwise

        Raises:
            SearchException: If search fails
        """
        results = await self.search_similar_findings(
            query_embedding=finding_embedding,
            research_run_id=research_run_id,
            top_k=1,
            score_threshold=similarity_threshold,
        )

        if results and len(results) > 0:
            return results[0]

        return None
