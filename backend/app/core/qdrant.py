"""
Qdrant vector database client and helper functions.

This module provides a singleton Qdrant client and helper functions for
managing vector collections and performing hybrid search operations on
legal documents.
"""

from typing import List, Dict, Any, Optional, Tuple
from functools import lru_cache
import logging

from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
    SearchRequest,
    NamedVector,
    SparseVector,
    SparseVectorParams,
    SparseIndexParams,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache()
def get_qdrant_client() -> QdrantClient:
    """
    Get or create a singleton Qdrant client instance.

    Returns:
        QdrantClient: Configured Qdrant client connected to the specified host and port.
    """
    client = QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        timeout=30.0,
    )
    logger.info(f"Qdrant client initialized: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
    return client


def create_collection(
    collection_name: Optional[str] = None,
    summary_vector_size: int = 768,
    section_vector_size: int = 768,
    microblock_vector_size: int = 768,
    recreate: bool = False,
) -> bool:
    """
    Create a Qdrant collection for legal documents with multi-vector configuration.

    This creates a collection that supports:
    - Dense vectors: summary, section, and microblock embeddings
    - Sparse vectors: BM25 keyword matching

    Args:
        collection_name: Name of the collection (default: from settings)
        summary_vector_size: Dimension of summary embeddings (default: 768 for all-MiniLM-L6-v2)
        section_vector_size: Dimension of section embeddings (default: 768)
        microblock_vector_size: Dimension of microblock embeddings (default: 768)
        recreate: If True, delete existing collection before creating

    Returns:
        bool: True if collection was created successfully
    """
    client = get_qdrant_client()
    collection_name = collection_name or settings.QDRANT_COLLECTION

    try:
        # Check if collection exists
        collections = client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)

        if exists:
            if recreate:
                logger.warning(f"Deleting existing collection: {collection_name}")
                client.delete_collection(collection_name=collection_name)
            else:
                logger.info(f"Collection already exists: {collection_name}")
                return True

        # Create collection with multiple named vectors
        # Following RAGFlow pattern: summary, section, microblock vectors
        client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "summary": VectorParams(
                    size=summary_vector_size,
                    distance=Distance.COSINE,
                ),
                "section": VectorParams(
                    size=section_vector_size,
                    distance=Distance.COSINE,
                ),
                "microblock": VectorParams(
                    size=microblock_vector_size,
                    distance=Distance.COSINE,
                ),
            },
            sparse_vectors_config={
                "bm25": SparseVectorParams(
                    index=SparseIndexParams(
                        on_disk=False,
                    )
                )
            },
        )

        logger.info(f"Collection created successfully: {collection_name}")
        logger.info(f"Dense vectors: summary({summary_vector_size}), section({section_vector_size}), microblock({microblock_vector_size})")
        logger.info("Sparse vectors: bm25")

        return True

    except Exception as e:
        logger.error(f"Error creating collection {collection_name}: {e}")
        raise


def upsert_points(
    points: List[PointStruct],
    collection_name: Optional[str] = None,
    batch_size: int = 100,
) -> bool:
    """
    Upsert points (document chunks) into the Qdrant collection.

    Args:
        points: List of PointStruct objects containing vectors and metadata
        collection_name: Name of the collection (default: from settings)
        batch_size: Number of points to upload in each batch

    Returns:
        bool: True if all points were upserted successfully
    """
    client = get_qdrant_client()
    collection_name = collection_name or settings.QDRANT_COLLECTION

    try:
        # Upload in batches
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            client.upsert(
                collection_name=collection_name,
                points=batch,
                wait=True,
            )
            logger.info(f"Upserted batch {i // batch_size + 1}: {len(batch)} points")

        logger.info(f"Successfully upserted {len(points)} points to {collection_name}")
        return True

    except Exception as e:
        logger.error(f"Error upserting points to {collection_name}: {e}")
        raise


def search_hybrid(
    query_vector: Dict[str, List[float]],
    query_sparse_vector: Optional[SparseVector] = None,
    collection_name: Optional[str] = None,
    limit: int = 10,
    filters: Optional[Filter] = None,
    score_threshold: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Perform hybrid search combining dense and sparse vectors.

    This function searches across multiple named vectors (summary, section, microblock)
    and optionally includes BM25 sparse vector search.

    Args:
        query_vector: Dict mapping vector names to embedding lists
                     e.g., {"summary": [...], "section": [...], "microblock": [...]}
        query_sparse_vector: Optional BM25 sparse vector for keyword matching
        collection_name: Name of the collection (default: from settings)
        limit: Maximum number of results to return
        filters: Optional Qdrant filter conditions
        score_threshold: Minimum score threshold for results

    Returns:
        List of search results with scores, payloads, and vectors
    """
    client = get_qdrant_client()
    collection_name = collection_name or settings.QDRANT_COLLECTION

    try:
        results = []

        # Search with each named vector
        for vector_name, vector_values in query_vector.items():
            search_results = client.search(
                collection_name=collection_name,
                query_vector=(vector_name, vector_values),
                query_filter=filters,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=False,
            )

            # Convert to dict format
            for hit in search_results:
                results.append({
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload,
                    "vector_type": vector_name,
                })

        # If sparse vector provided, also search with BM25
        if query_sparse_vector:
            sparse_results = client.search(
                collection_name=collection_name,
                query_vector=("bm25", query_sparse_vector),
                query_filter=filters,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )

            for hit in sparse_results:
                results.append({
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload,
                    "vector_type": "bm25",
                })

        logger.info(f"Hybrid search returned {len(results)} total results from {len(query_vector)} vectors")
        return results

    except Exception as e:
        logger.error(f"Error performing hybrid search: {e}")
        raise


def delete_points(
    point_ids: List[int],
    collection_name: Optional[str] = None,
) -> bool:
    """
    Delete points from the collection by their IDs.

    Args:
        point_ids: List of point IDs to delete
        collection_name: Name of the collection (default: from settings)

    Returns:
        bool: True if deletion was successful
    """
    client = get_qdrant_client()
    collection_name = collection_name or settings.QDRANT_COLLECTION

    try:
        client.delete(
            collection_name=collection_name,
            points_selector=point_ids,
            wait=True,
        )
        logger.info(f"Deleted {len(point_ids)} points from {collection_name}")
        return True

    except Exception as e:
        logger.error(f"Error deleting points: {e}")
        raise


def delete_by_filter(
    filters: Filter,
    collection_name: Optional[str] = None,
) -> bool:
    """
    Delete points from the collection matching a filter.

    Useful for deleting all chunks belonging to a specific document or case.

    Args:
        filters: Qdrant filter conditions
        collection_name: Name of the collection (default: from settings)

    Returns:
        bool: True if deletion was successful
    """
    client = get_qdrant_client()
    collection_name = collection_name or settings.QDRANT_COLLECTION

    try:
        client.delete(
            collection_name=collection_name,
            points_selector=filters,
            wait=True,
        )
        logger.info(f"Deleted points matching filter from {collection_name}")
        return True

    except Exception as e:
        logger.error(f"Error deleting points by filter: {e}")
        raise


def get_collection_info(
    collection_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get information about the collection.

    Args:
        collection_name: Name of the collection (default: from settings)

    Returns:
        Dictionary containing collection statistics and configuration
    """
    client = get_qdrant_client()
    collection_name = collection_name or settings.QDRANT_COLLECTION

    try:
        info = client.get_collection(collection_name=collection_name)
        return {
            "name": collection_name,
            "vectors_count": info.points_count,
            "status": info.status,
            "vectors_config": info.config.params.vectors,
            "sparse_vectors_config": info.config.params.sparse_vectors,
        }

    except Exception as e:
        logger.error(f"Error getting collection info: {e}")
        raise


def build_filter(
    case_ids: Optional[List[int]] = None,
    document_ids: Optional[List[int]] = None,
    chunk_types: Optional[List[str]] = None,
    additional_conditions: Optional[List[FieldCondition]] = None,
) -> Optional[Filter]:
    """
    Build a Qdrant filter from common query parameters.

    Args:
        case_ids: Filter by case IDs
        document_ids: Filter by document IDs
        chunk_types: Filter by chunk types (e.g., 'summary', 'section', 'microblock')
        additional_conditions: Additional custom filter conditions

    Returns:
        Qdrant Filter object or None if no conditions specified
    """
    conditions = []

    if case_ids:
        # Handle single vs multiple case_ids properly
        if len(case_ids) == 1:
            conditions.append(
                FieldCondition(
                    key="case_id",
                    match=MatchValue(value=case_ids[0]),
                )
            )
        else:
            conditions.append(
                FieldCondition(
                    key="case_id",
                    match=MatchAny(any=case_ids),
                )
            )

    if document_ids:
        # Handle single vs multiple document_ids properly
        if len(document_ids) == 1:
            conditions.append(
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_ids[0]),
                )
            )
        else:
            conditions.append(
                FieldCondition(
                    key="document_id",
                    match=MatchAny(any=document_ids),
                )
            )

    if chunk_types:
        # Handle single vs multiple chunk_types properly
        if len(chunk_types) == 1:
            # Single chunk_type: use MatchValue with a string
            conditions.append(
                FieldCondition(
                    key="chunk_type",
                    match=MatchValue(value=chunk_types[0]),
                )
            )
        else:
            # Multiple chunk_types: use MatchAny with a list
            conditions.append(
                FieldCondition(
                    key="chunk_type",
                    match=MatchAny(any=chunk_types),
                )
            )

    if additional_conditions:
        conditions.extend(additional_conditions)

    if not conditions:
        return None

    return Filter(must=conditions)
