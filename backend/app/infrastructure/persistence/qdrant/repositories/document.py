"""
Document vector repository for Qdrant operations.

Handles indexing and searching of document chunks with hierarchical
embeddings (summary, section, microblock).
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
from app.domain.evidence.value_objects.chunk import Chunk

logger = logging.getLogger(__name__)


class QdrantDocumentRepository(BaseQdrantRepository):
    """
    Repository for document vector operations in Qdrant.

    Manages hierarchical document embeddings:
    - Summary vectors: High-level document understanding
    - Section vectors: Section-level semantic search
    - Microblock vectors: Fine-grained passage retrieval
    """

    def __init__(self):
        """Initialize document vector repository."""
        super().__init__(collection_name=CollectionName.DOCUMENTS.value)

    async def index_document(
        self,
        document_id: UUID,
        case_id: UUID,
        chunks: List[Chunk],
        embeddings: Dict[str, List[List[float]]],
        sparse_vectors: Optional[List[Any]] = None,
    ) -> bool:
        """
        Index a document with its chunks and embeddings.

        Args:
            document_id: UUID of the document
            case_id: UUID of the case
            chunks: List of Chunk value objects
            embeddings: Dict mapping vector types to embedding lists
                       e.g., {"summary": [...], "section": [...], "microblock": [...]}
            sparse_vectors: Optional BM25 sparse vectors for each chunk

        Returns:
            True if indexing successful

        Raises:
            IndexingException: If indexing fails
        """
        if len(chunks) == 0:
            logger.warning(f"No chunks to index for document {document_id}")
            return True

        # Validate embeddings
        for vector_type in ["summary", "section", "microblock"]:
            if vector_type not in embeddings:
                raise IndexingException(
                    f"Missing {vector_type} embeddings for document",
                    context={
                        "document_id": str(document_id),
                        "vector_type": vector_type,
                    },
                )
            if len(embeddings[vector_type]) != len(chunks):
                raise IndexingException(
                    f"Embedding count mismatch for {vector_type}",
                    context={
                        "document_id": str(document_id),
                        "chunks": len(chunks),
                        "embeddings": len(embeddings[vector_type]),
                    },
                )

        # Build points
        points = []
        for i, chunk in enumerate(chunks):
            # Build vector dict for this point
            vector_dict = {
                "summary": embeddings["summary"][i],
                "section": embeddings["section"][i],
                "microblock": embeddings["microblock"][i],
            }

            # Add sparse vector if provided
            if sparse_vectors and i < len(sparse_vectors):
                vector_dict["bm25"] = sparse_vectors[i]

            # Build payload
            payload = {
                "case_id": str(case_id),
                "document_id": str(document_id),
                "chunk_type": chunk.chunk_type.value,
                "position": chunk.position,
                "text": chunk.text,
                "word_count": chunk.word_count(),
                "char_count": chunk.char_count(),
                **chunk.metadata,  # Include all chunk metadata
            }

            # Create point with chunk position as unique ID
            point_id = f"{document_id}_{chunk.position}"

            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector_dict,
                    payload=payload,
                )
            )

        # Upsert points
        logger.info(
            f"Indexing document {document_id}: {len(points)} chunks"
        )
        return await self.upsert_points(points)

    async def search_documents(
        self,
        query_embeddings: Dict[str, List[float]],
        case_ids: Optional[List[UUID]] = None,
        document_ids: Optional[List[UUID]] = None,
        chunk_types: Optional[List[str]] = None,
        top_k: int = 10,
        score_threshold: Optional[float] = None,
        sparse_vector: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search documents using hybrid search.

        Args:
            query_embeddings: Dict of query embeddings for each vector type
            case_ids: Optional filter by case IDs
            document_ids: Optional filter by document IDs
            chunk_types: Optional filter by chunk types
            top_k: Number of results to return
            score_threshold: Minimum score threshold
            sparse_vector: Optional BM25 sparse vector

        Returns:
            List of search results with chunks and scores

        Raises:
            SearchException: If search fails
        """
        # Build filters
        filter_conditions = []

        # Case filter
        if case_ids:
            case_ids_str = [str(cid) for cid in case_ids]
            if len(case_ids_str) == 1:
                filter_conditions.append(
                    FieldCondition(
                        key="case_id",
                        match=MatchValue(value=case_ids_str[0]),
                    )
                )
            else:
                filter_conditions.append(
                    FieldCondition(
                        key="case_id",
                        match=MatchAny(any=case_ids_str),
                    )
                )

        # Document filter
        if document_ids:
            doc_ids_str = [str(did) for did in document_ids]
            if len(doc_ids_str) == 1:
                filter_conditions.append(
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=doc_ids_str[0]),
                    )
                )
            else:
                filter_conditions.append(
                    FieldCondition(
                        key="document_id",
                        match=MatchAny(any=doc_ids_str),
                    )
                )

        # Chunk type filter
        if chunk_types:
            if len(chunk_types) == 1:
                filter_conditions.append(
                    FieldCondition(
                        key="chunk_type",
                        match=MatchValue(value=chunk_types[0]),
                    )
                )
            else:
                filter_conditions.append(
                    FieldCondition(
                        key="chunk_type",
                        match=MatchAny(any=chunk_types),
                    )
                )

        filters = Filter(must=filter_conditions) if filter_conditions else None

        # Perform hybrid search
        return await self.search_hybrid(
            query_vectors=query_embeddings,
            query_sparse_vector=sparse_vector,
            filters=filters,
            top_k=top_k,
            score_threshold=score_threshold,
        )

    async def delete_document(self, document_id: UUID) -> bool:
        """
        Delete all chunks for a document.

        Args:
            document_id: UUID of the document to delete

        Returns:
            True if successful

        Raises:
            DeletionException: If deletion fails
        """
        filter_conditions = Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=str(document_id)),
                )
            ]
        )

        logger.info(f"Deleting document {document_id} from vector store")
        return await self.delete_by_filter(filter_conditions)

    async def delete_case_documents(self, case_id: UUID) -> bool:
        """
        Delete all documents for a case.

        Args:
            case_id: UUID of the case

        Returns:
            True if successful

        Raises:
            DeletionException: If deletion fails
        """
        filter_conditions = Filter(
            must=[
                FieldCondition(
                    key="case_id",
                    match=MatchValue(value=str(case_id)),
                )
            ]
        )

        logger.info(f"Deleting all documents for case {case_id} from vector store")
        return await self.delete_by_filter(filter_conditions)

    async def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific chunk by its ID.

        Args:
            chunk_id: Chunk ID (format: "document_id_position")

        Returns:
            Chunk payload or None if not found

        Raises:
            SearchException: If retrieval fails
        """
        try:
            async with self.client.get_client() as qdrant:
                result = await qdrant.retrieve(
                    collection_name=self.collection_name,
                    ids=[chunk_id],
                    with_payload=True,
                    with_vectors=False,
                )

                if result and len(result) > 0:
                    return {
                        "id": result[0].id,
                        "payload": result[0].payload,
                    }
                return None

        except Exception as e:
            raise SearchException(
                f"Failed to retrieve chunk {chunk_id}",
                cause=e,
                context={"chunk_id": chunk_id},
            )

    async def get_document_chunks(
        self,
        document_id: UUID,
        chunk_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all chunks for a document.

        Args:
            document_id: UUID of the document
            chunk_types: Optional filter by chunk types

        Returns:
            List of chunk payloads

        Raises:
            SearchException: If retrieval fails
        """
        try:
            async with self.client.get_client() as qdrant:
                # Build filter
                filter_conditions = [
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=str(document_id)),
                    )
                ]

                if chunk_types:
                    if len(chunk_types) == 1:
                        filter_conditions.append(
                            FieldCondition(
                                key="chunk_type",
                                match=MatchValue(value=chunk_types[0]),
                            )
                        )
                    else:
                        filter_conditions.append(
                            FieldCondition(
                                key="chunk_type",
                                match=MatchAny(any=chunk_types),
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

                # Sort by position
                results.sort(key=lambda x: x["payload"].get("position", 0))

                return results

        except Exception as e:
            raise SearchException(
                f"Failed to get chunks for document {document_id}",
                cause=e,
                context={"document_id": str(document_id)},
            )
