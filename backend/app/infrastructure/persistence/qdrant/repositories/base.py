"""
Base repository for Qdrant vector operations.

Provides abstract base class with common operations for all Qdrant repositories,
implementing reciprocal rank fusion for hybrid search.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

from qdrant_client.models import (
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
    SparseVector,
)

from app.infrastructure.persistence.qdrant.client import get_qdrant_client
from app.infrastructure.exceptions import (
    IndexingException,
    SearchException,
    DeletionException,
)
from app.domain.evidence.value_objects.chunk import Chunk

logger = logging.getLogger(__name__)


class BaseQdrantRepository(ABC):
    """
    Abstract base class for Qdrant repositories.

    Provides common operations:
    - Upsert vectors with batching
    - Hybrid search with reciprocal rank fusion
    - Delete operations (by ID and by filter)
    - Filter building utilities
    """

    def __init__(self, collection_name: str):
        """
        Initialize base repository.

        Args:
            collection_name: Name of the Qdrant collection
        """
        self.collection_name = collection_name
        self.client = get_qdrant_client()

    async def upsert_points(
        self,
        points: List[PointStruct],
        batch_size: int = 100,
    ) -> bool:
        """
        Upsert points (vectors) into the collection with batching.

        Args:
            points: List of PointStruct objects to upsert
            batch_size: Number of points per batch

        Returns:
            True if successful

        Raises:
            IndexingException: If upsert fails
        """
        try:
            async with self.client.get_client() as qdrant:
                total_batches = (len(points) + batch_size - 1) // batch_size

                for i in range(0, len(points), batch_size):
                    batch = points[i : i + batch_size]
                    batch_num = (i // batch_size) + 1

                    try:
                        await qdrant.upsert(
                            collection_name=self.collection_name,
                            points=batch,
                            wait=True,
                        )
                        logger.info(
                            f"Upserted batch {batch_num}/{total_batches}: "
                            f"{len(batch)} points to {self.collection_name}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to upsert batch {batch_num}/{total_batches}: {e}"
                        )
                        raise IndexingException(
                            f"Failed to upsert batch {batch_num}",
                            cause=e,
                            context={
                                "collection": self.collection_name,
                                "batch_num": batch_num,
                                "batch_size": len(batch),
                            },
                        )

                logger.info(
                    f"Successfully upserted {len(points)} points to {self.collection_name}"
                )
                return True

        except Exception as e:
            if not isinstance(e, IndexingException):
                raise IndexingException(
                    f"Failed to upsert points to {self.collection_name}",
                    cause=e,
                    context={"collection": self.collection_name, "points": len(points)},
                )
            raise

    async def search_hybrid(
        self,
        query_vectors: Dict[str, List[float]],
        query_sparse_vector: Optional[SparseVector] = None,
        filters: Optional[Filter] = None,
        top_k: int = 10,
        score_threshold: Optional[float] = None,
        rrf_k: int = 60,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search with reciprocal rank fusion (RRF).

        Combines results from multiple vector searches (dense + sparse)
        using RRF algorithm to merge rankings.

        Args:
            query_vectors: Dict mapping vector names to embeddings
            query_sparse_vector: Optional BM25 sparse vector
            filters: Optional Qdrant filter conditions
            top_k: Number of results to return
            score_threshold: Minimum score threshold
            rrf_k: RRF constant (typically 60)

        Returns:
            List of search results with scores and payloads

        Raises:
            SearchException: If search fails
        """
        try:
            async with self.client.get_client() as qdrant:
                all_results = []

                # Search with each dense vector
                for vector_name, vector_values in query_vectors.items():
                    results = await qdrant.search(
                        collection_name=self.collection_name,
                        query_vector=(vector_name, vector_values),
                        query_filter=filters,
                        limit=top_k * 2,  # Get more results for RRF
                        score_threshold=score_threshold,
                        with_payload=True,
                        with_vectors=False,
                    )

                    for rank, hit in enumerate(results, start=1):
                        all_results.append({
                            "id": str(hit.id),
                            "score": hit.score,
                            "payload": hit.payload,
                            "vector_type": vector_name,
                            "rank": rank,
                        })

                # Search with sparse vector if provided
                if query_sparse_vector:
                    results = await qdrant.search(
                        collection_name=self.collection_name,
                        query_vector=("bm25", query_sparse_vector),
                        query_filter=filters,
                        limit=top_k * 2,
                        with_payload=True,
                        with_vectors=False,
                    )

                    for rank, hit in enumerate(results, start=1):
                        all_results.append({
                            "id": str(hit.id),
                            "score": hit.score,
                            "payload": hit.payload,
                            "vector_type": "bm25",
                            "rank": rank,
                        })

                # Apply reciprocal rank fusion
                fused_results = self._reciprocal_rank_fusion(all_results, k=rrf_k)

                # Return top_k results
                return fused_results[:top_k]

        except Exception as e:
            raise SearchException(
                f"Hybrid search failed in {self.collection_name}",
                cause=e,
                context={
                    "collection": self.collection_name,
                    "top_k": top_k,
                },
            )

    def _reciprocal_rank_fusion(
        self,
        results: List[Dict[str, Any]],
        k: int = 60,
    ) -> List[Dict[str, Any]]:
        """
        Apply reciprocal rank fusion to merge search results.

        RRF score = sum(1 / (k + rank)) for each occurrence

        Args:
            results: List of search results with ranks
            k: RRF constant (typically 60)

        Returns:
            Sorted list of fused results
        """
        # Group results by ID
        id_to_results = {}
        for result in results:
            result_id = result["id"]
            if result_id not in id_to_results:
                id_to_results[result_id] = {
                    "id": result_id,
                    "payload": result["payload"],
                    "rrf_score": 0.0,
                    "sources": [],
                }

            # Add RRF score contribution
            rrf_contribution = 1.0 / (k + result["rank"])
            id_to_results[result_id]["rrf_score"] += rrf_contribution
            id_to_results[result_id]["sources"].append({
                "vector_type": result["vector_type"],
                "rank": result["rank"],
                "score": result["score"],
            })

        # Sort by RRF score
        fused = sorted(
            id_to_results.values(),
            key=lambda x: x["rrf_score"],
            reverse=True,
        )

        return fused

    async def delete_by_ids(self, point_ids: List[UUID]) -> bool:
        """
        Delete points by their IDs.

        Args:
            point_ids: List of point UUIDs to delete

        Returns:
            True if successful

        Raises:
            DeletionException: If deletion fails
        """
        try:
            async with self.client.get_client() as qdrant:
                # Convert UUIDs to strings for Qdrant
                ids_str = [str(pid) for pid in point_ids]

                await qdrant.delete(
                    collection_name=self.collection_name,
                    points_selector=ids_str,
                    wait=True,
                )

                logger.info(
                    f"Deleted {len(point_ids)} points from {self.collection_name}"
                )
                return True

        except Exception as e:
            raise DeletionException(
                f"Failed to delete points from {self.collection_name}",
                cause=e,
                context={
                    "collection": self.collection_name,
                    "count": len(point_ids),
                },
            )

    async def delete_by_filter(self, filter_conditions: Filter) -> bool:
        """
        Delete points matching a filter.

        Args:
            filter_conditions: Qdrant filter conditions

        Returns:
            True if successful

        Raises:
            DeletionException: If deletion fails
        """
        try:
            async with self.client.get_client() as qdrant:
                await qdrant.delete(
                    collection_name=self.collection_name,
                    points_selector=filter_conditions,
                    wait=True,
                )

                logger.info(
                    f"Deleted points matching filter from {self.collection_name}"
                )
                return True

        except Exception as e:
            raise DeletionException(
                f"Failed to delete by filter from {self.collection_name}",
                cause=e,
                context={"collection": self.collection_name},
            )

    def build_filter(
        self,
        case_ids: Optional[List[UUID]] = None,
        document_ids: Optional[List[UUID]] = None,
        additional_conditions: Optional[List[FieldCondition]] = None,
    ) -> Optional[Filter]:
        """
        Build a Qdrant filter from common parameters.

        Args:
            case_ids: Filter by case UUIDs
            document_ids: Filter by document UUIDs
            additional_conditions: Additional custom conditions

        Returns:
            Qdrant Filter or None if no conditions
        """
        conditions = []

        if case_ids:
            case_ids_str = [str(cid) for cid in case_ids]
            if len(case_ids_str) == 1:
                conditions.append(
                    FieldCondition(
                        key="case_id",
                        match=MatchValue(value=case_ids_str[0]),
                    )
                )
            else:
                conditions.append(
                    FieldCondition(
                        key="case_id",
                        match=MatchAny(any=case_ids_str),
                    )
                )

        if document_ids:
            doc_ids_str = [str(did) for did in document_ids]
            if len(doc_ids_str) == 1:
                conditions.append(
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=doc_ids_str[0]),
                    )
                )
            else:
                conditions.append(
                    FieldCondition(
                        key="document_id",
                        match=MatchAny(any=doc_ids_str),
                    )
                )

        if additional_conditions:
            conditions.extend(additional_conditions)

        if not conditions:
            return None

        return Filter(must=conditions)
