"""
Qdrant collection management utilities.

Provides schema definitions and utilities for creating and managing
Qdrant collections across the application.
"""

import logging
from typing import Dict, Optional
from enum import Enum

from qdrant_client.models import (
    VectorParams,
    Distance,
    SparseVectorParams,
    SparseIndexParams,
)

from app.infrastructure.persistence.qdrant.client import get_qdrant_client
from app.infrastructure.exceptions import CollectionException

logger = logging.getLogger(__name__)


class CollectionName(str, Enum):
    """Enum of all Qdrant collections used in the application."""

    DOCUMENTS = "legalease_documents"
    TRANSCRIPTS = "legalease_transcripts"
    COMMUNICATIONS = "legalease_communications"
    FINDINGS = "legalease_findings"


# Vector dimension constants
DENSE_VECTOR_DIM = 768  # all-MiniLM-L6-v2 and similar models


class CollectionManager:
    """
    Manager for Qdrant collection schemas and operations.

    Provides centralized collection configuration and schema management.
    """

    @staticmethod
    def get_document_schema() -> tuple[
        Dict[str, VectorParams],
        Dict[str, SparseVectorParams],
    ]:
        """
        Get schema for document collection.

        Supports hierarchical chunks: summary, section, microblock vectors
        following RAGFlow pattern.

        Returns:
            Tuple of (dense_vector_configs, sparse_vector_configs)
        """
        dense_vectors = {
            "summary": VectorParams(
                size=DENSE_VECTOR_DIM,
                distance=Distance.COSINE,
            ),
            "section": VectorParams(
                size=DENSE_VECTOR_DIM,
                distance=Distance.COSINE,
            ),
            "microblock": VectorParams(
                size=DENSE_VECTOR_DIM,
                distance=Distance.COSINE,
            ),
        }

        sparse_vectors = {
            "bm25": SparseVectorParams(
                index=SparseIndexParams(
                    on_disk=False,
                )
            )
        }

        return dense_vectors, sparse_vectors

    @staticmethod
    def get_transcript_schema() -> tuple[
        Dict[str, VectorParams],
        Dict[str, SparseVectorParams],
    ]:
        """
        Get schema for transcript collection.

        Supports dense embeddings of transcript segments with BM25 sparse
        vectors for keyword search.

        Returns:
            Tuple of (dense_vector_configs, sparse_vector_configs)
        """
        dense_vectors = {
            "dense": VectorParams(
                size=DENSE_VECTOR_DIM,
                distance=Distance.COSINE,
            ),
        }

        sparse_vectors = {
            "bm25": SparseVectorParams(
                index=SparseIndexParams(
                    on_disk=False,
                )
            )
        }

        return dense_vectors, sparse_vectors

    @staticmethod
    def get_communication_schema() -> tuple[
        Dict[str, VectorParams],
        Dict[str, SparseVectorParams],
    ]:
        """
        Get schema for communication collection.

        For Cellebrite messages, emails, chats with dense + sparse vectors.

        Returns:
            Tuple of (dense_vector_configs, sparse_vector_configs)
        """
        dense_vectors = {
            "dense": VectorParams(
                size=DENSE_VECTOR_DIM,
                distance=Distance.COSINE,
            ),
        }

        sparse_vectors = {
            "bm25": SparseVectorParams(
                index=SparseIndexParams(
                    on_disk=False,
                )
            )
        }

        return dense_vectors, sparse_vectors

    @staticmethod
    def get_finding_schema() -> tuple[
        Dict[str, VectorParams],
        Dict[str, SparseVectorParams],
    ]:
        """
        Get schema for finding collection.

        For research findings with semantic similarity search.

        Returns:
            Tuple of (dense_vector_configs, sparse_vector_configs)
        """
        dense_vectors = {
            "dense": VectorParams(
                size=DENSE_VECTOR_DIM,
                distance=Distance.COSINE,
            ),
        }

        sparse_vectors = {
            "bm25": SparseVectorParams(
                index=SparseIndexParams(
                    on_disk=False,
                )
            )
        }

        return dense_vectors, sparse_vectors

    @staticmethod
    async def create_document_collection(recreate: bool = False) -> bool:
        """
        Create document collection with hierarchical vector schema.

        Args:
            recreate: Whether to recreate if collection exists

        Returns:
            True if successful

        Raises:
            CollectionException: If creation fails
        """
        client = get_qdrant_client()
        dense, sparse = CollectionManager.get_document_schema()

        try:
            return await client.create_collection(
                collection_name=CollectionName.DOCUMENTS,
                vector_configs=dense,
                sparse_vector_configs=sparse,
                recreate=recreate,
            )
        except Exception as e:
            raise CollectionException(
                f"Failed to create {CollectionName.DOCUMENTS} collection",
                cause=e,
            )

    @staticmethod
    async def create_transcript_collection(recreate: bool = False) -> bool:
        """
        Create transcript collection.

        Args:
            recreate: Whether to recreate if collection exists

        Returns:
            True if successful

        Raises:
            CollectionException: If creation fails
        """
        client = get_qdrant_client()
        dense, sparse = CollectionManager.get_transcript_schema()

        try:
            return await client.create_collection(
                collection_name=CollectionName.TRANSCRIPTS,
                vector_configs=dense,
                sparse_vector_configs=sparse,
                recreate=recreate,
            )
        except Exception as e:
            raise CollectionException(
                f"Failed to create {CollectionName.TRANSCRIPTS} collection",
                cause=e,
            )

    @staticmethod
    async def create_communication_collection(recreate: bool = False) -> bool:
        """
        Create communication collection for Cellebrite messages.

        Args:
            recreate: Whether to recreate if collection exists

        Returns:
            True if successful

        Raises:
            CollectionException: If creation fails
        """
        client = get_qdrant_client()
        dense, sparse = CollectionManager.get_communication_schema()

        try:
            return await client.create_collection(
                collection_name=CollectionName.COMMUNICATIONS,
                vector_configs=dense,
                sparse_vector_configs=sparse,
                recreate=recreate,
            )
        except Exception as e:
            raise CollectionException(
                f"Failed to create {CollectionName.COMMUNICATIONS} collection",
                cause=e,
            )

    @staticmethod
    async def create_finding_collection(recreate: bool = False) -> bool:
        """
        Create finding collection for research findings.

        Args:
            recreate: Whether to recreate if collection exists

        Returns:
            True if successful

        Raises:
            CollectionException: If creation fails
        """
        client = get_qdrant_client()
        dense, sparse = CollectionManager.get_finding_schema()

        try:
            return await client.create_collection(
                collection_name=CollectionName.FINDINGS,
                vector_configs=dense,
                sparse_vector_configs=sparse,
                recreate=recreate,
            )
        except Exception as e:
            raise CollectionException(
                f"Failed to create {CollectionName.FINDINGS} collection",
                cause=e,
            )

    @staticmethod
    async def create_all_collections(recreate: bool = False) -> None:
        """
        Create all application collections.

        Args:
            recreate: Whether to recreate existing collections

        Raises:
            CollectionException: If any collection creation fails
        """
        logger.info("Creating all Qdrant collections...")

        await CollectionManager.create_document_collection(recreate=recreate)
        await CollectionManager.create_transcript_collection(recreate=recreate)
        await CollectionManager.create_communication_collection(recreate=recreate)
        await CollectionManager.create_finding_collection(recreate=recreate)

        logger.info("All Qdrant collections created successfully")

    @staticmethod
    async def get_collection_stats() -> Dict[str, dict]:
        """
        Get statistics for all collections.

        Returns:
            Dictionary mapping collection names to their statistics
        """
        client = get_qdrant_client()
        stats = {}

        for collection_name in CollectionName:
            try:
                if await client.collection_exists(collection_name.value):
                    info = await client.get_collection_info(collection_name.value)
                    stats[collection_name.value] = {
                        "points_count": info.points_count,
                        "status": info.status.value,
                        "vectors": list(info.config.params.vectors.keys()),
                        "sparse_vectors": (
                            list(info.config.params.sparse_vectors.keys())
                            if info.config.params.sparse_vectors
                            else []
                        ),
                    }
                else:
                    stats[collection_name.value] = {"exists": False}
            except Exception as e:
                logger.error(f"Error getting stats for {collection_name.value}: {e}")
                stats[collection_name.value] = {"error": str(e)}

        return stats
