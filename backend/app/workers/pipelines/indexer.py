"""
Qdrant Indexer

Handles indexing of document chunks with embeddings into Qdrant vector database.
Supports multi-vector (summary, section, microblock) and hybrid (dense + sparse) indexing.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import uuid
from qdrant_client.models import PointStruct, SparseVector

from app.core.qdrant import get_qdrant_client, upsert_points
from app.core.config import settings

logger = logging.getLogger(__name__)


class QdrantIndexer:
    """
    Qdrant indexer for storing document embeddings.

    Features:
    - Multi-vector support (summary, section, microblock)
    - Hybrid indexing (dense + sparse vectors)
    - Batch processing
    - Metadata storage
    """

    def __init__(
        self,
        collection_name: Optional[str] = None,
        batch_size: int = 100,
    ):
        """
        Initialize the Qdrant indexer.

        Args:
            collection_name: Name of the Qdrant collection
            batch_size: Number of points to upsert in each batch
        """
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.batch_size = batch_size
        self.client = get_qdrant_client()

        logger.info(f"Initialized QdrantIndexer (collection={self.collection_name}, batch_size={batch_size})")

    def index_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: Dict[str, List[List[float]]],
        sparse_vectors: Optional[List[Tuple[List[int], List[float]]]] = None,
        document_id: int = None,
        case_id: int = None,
    ) -> bool:
        """
        Index document chunks with embeddings into Qdrant.

        Args:
            chunks: List of chunk dictionaries with text and metadata
            embeddings: Dictionary mapping vector types to embedding lists
                       e.g., {"summary": [...], "section": [...], "microblock": [...]}
            sparse_vectors: Optional list of sparse vectors (indices, values) for BM25
            document_id: Database document ID
            case_id: Database case ID

        Returns:
            True if indexing successful
        """
        logger.info(f"Indexing {len(chunks)} chunks for document {document_id}")

        try:
            points = self._prepare_points(
                chunks=chunks,
                embeddings=embeddings,
                sparse_vectors=sparse_vectors,
                document_id=document_id,
                case_id=case_id,
            )

            # Upsert points in batches
            success = upsert_points(
                points=points,
                collection_name=self.collection_name,
                batch_size=self.batch_size,
            )

            if success:
                logger.info(f"Successfully indexed {len(points)} points for document {document_id}")
            else:
                logger.error(f"Failed to index points for document {document_id}")

            return success

        except Exception as e:
            logger.error(f"Error indexing chunks: {e}")
            raise

    def _prepare_points(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: Dict[str, List[List[float]]],
        sparse_vectors: Optional[List[Tuple[List[int], List[float]]]] = None,
        document_id: int = None,
        case_id: int = None,
    ) -> List[PointStruct]:
        """
        Prepare Qdrant points from chunks and embeddings.

        Args:
            chunks: List of chunk dictionaries
            embeddings: Dictionary of embeddings by type
            sparse_vectors: Optional sparse vectors
            document_id: Database document ID
            case_id: Database case ID

        Returns:
            List of PointStruct objects
        """
        points = []

        # Group chunks by type
        chunks_by_type = {}
        for chunk in chunks:
            chunk_type = chunk.get("chunk_type", "section")
            if chunk_type not in chunks_by_type:
                chunks_by_type[chunk_type] = []
            chunks_by_type[chunk_type].append(chunk)

        # Create points for each chunk type
        for chunk_type, type_chunks in chunks_by_type.items():
            if chunk_type not in embeddings:
                logger.warning(f"No embeddings found for chunk type: {chunk_type}")
                continue

            type_embeddings = embeddings[chunk_type]

            if len(type_chunks) != len(type_embeddings):
                logger.warning(
                    f"Chunk count mismatch for {chunk_type}: "
                    f"{len(type_chunks)} chunks vs {len(type_embeddings)} embeddings"
                )
                # Use minimum to avoid index errors
                count = min(len(type_chunks), len(type_embeddings))
                type_chunks = type_chunks[:count]
                type_embeddings = type_embeddings[:count]

            for i, (chunk, embedding) in enumerate(zip(type_chunks, type_embeddings)):
                point = self._create_point(
                    chunk=chunk,
                    embedding=embedding,
                    chunk_type=chunk_type,
                    sparse_vector=sparse_vectors[i] if sparse_vectors and i < len(sparse_vectors) else None,
                    document_id=document_id,
                    case_id=case_id,
                )
                points.append(point)

        return points

    def _create_point(
        self,
        chunk: Dict[str, Any],
        embedding: List[float],
        chunk_type: str,
        sparse_vector: Optional[Tuple[List[int], List[float]]] = None,
        document_id: int = None,
        case_id: int = None,
    ) -> PointStruct:
        """
        Create a single Qdrant point.

        Args:
            chunk: Chunk dictionary
            embedding: Dense embedding vector
            chunk_type: Type of chunk (summary, section, microblock)
            sparse_vector: Optional sparse vector (indices, values)
            document_id: Database document ID
            case_id: Database case ID

        Returns:
            PointStruct object
        """
        # Generate unique point ID
        point_id = str(uuid.uuid4())

        # Build payload with metadata
        payload = {
            "text": chunk.get("text", ""),
            "chunk_type": chunk_type,
            "position": chunk.get("position", 0),
            "page_number": chunk.get("page_number"),
            "document_id": document_id,
            "case_id": case_id,
            "char_count": chunk.get("char_count", len(chunk.get("text", ""))),
            "word_count": chunk.get("word_count", len(chunk.get("text", "").split())),
        }

        # Add any additional metadata
        if chunk.get("metadata"):
            payload.update(chunk["metadata"])

        # Build vectors dictionary
        vectors = {
            chunk_type: embedding  # Named vector based on chunk type
        }

        # Add sparse vector if provided
        if sparse_vector:
            indices, values = sparse_vector
            vectors["bm25"] = SparseVector(
                indices=indices,
                values=values,
            )

        # Create point
        point = PointStruct(
            id=point_id,
            vector=vectors,
            payload=payload,
        )

        return point

    def index_single_chunk(
        self,
        text: str,
        embedding: List[float],
        chunk_type: str = "section",
        sparse_vector: Optional[Tuple[List[int], List[float]]] = None,
        document_id: int = None,
        case_id: int = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Index a single chunk.

        Args:
            text: Chunk text
            embedding: Dense embedding vector
            chunk_type: Type of chunk
            sparse_vector: Optional sparse vector
            document_id: Database document ID
            case_id: Database case ID
            metadata: Optional additional metadata

        Returns:
            True if indexing successful
        """
        chunk = {
            "text": text,
            "chunk_type": chunk_type,
            "position": 0,
            "metadata": metadata or {},
        }

        return self.index_chunks(
            chunks=[chunk],
            embeddings={chunk_type: [embedding]},
            sparse_vectors=[sparse_vector] if sparse_vector else None,
            document_id=document_id,
            case_id=case_id,
        )

    def delete_document_chunks(
        self,
        document_id: int,
    ) -> bool:
        """
        Delete all chunks for a document from Qdrant.

        Args:
            document_id: Database document ID

        Returns:
            True if deletion successful
        """
        from app.core.qdrant import delete_by_filter, build_filter

        try:
            logger.info(f"Deleting chunks for document {document_id}")

            filters = build_filter(document_ids=[document_id])
            success = delete_by_filter(
                filters=filters,
                collection_name=self.collection_name,
            )

            if success:
                logger.info(f"Successfully deleted chunks for document {document_id}")
            else:
                logger.error(f"Failed to delete chunks for document {document_id}")

            return success

        except Exception as e:
            logger.error(f"Error deleting chunks: {e}")
            raise

    def delete_case_chunks(
        self,
        case_id: int,
    ) -> bool:
        """
        Delete all chunks for a case from Qdrant.

        Args:
            case_id: Database case ID

        Returns:
            True if deletion successful
        """
        from app.core.qdrant import delete_by_filter, build_filter

        try:
            logger.info(f"Deleting chunks for case {case_id}")

            filters = build_filter(case_ids=[case_id])
            success = delete_by_filter(
                filters=filters,
                collection_name=self.collection_name,
            )

            if success:
                logger.info(f"Successfully deleted chunks for case {case_id}")
            else:
                logger.error(f"Failed to delete chunks for case {case_id}")

            return success

        except Exception as e:
            logger.error(f"Error deleting chunks: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """
        Get indexer statistics.

        Returns:
            Dictionary with stats
        """
        from app.core.qdrant import get_collection_info

        try:
            collection_info = get_collection_info(self.collection_name)
            return {
                "collection_name": self.collection_name,
                "batch_size": self.batch_size,
                "collection_info": collection_info,
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                "collection_name": self.collection_name,
                "batch_size": self.batch_size,
                "error": str(e),
            }


# Convenience function for quick indexing
def index_documents(
    chunks: List[Dict[str, Any]],
    embeddings: Dict[str, List[List[float]]],
    document_id: int,
    case_id: int,
    sparse_vectors: Optional[List[Tuple[List[int], List[float]]]] = None,
    collection_name: Optional[str] = None,
) -> bool:
    """
    Convenience function to index documents.

    Args:
        chunks: List of chunk dictionaries
        embeddings: Dictionary of embeddings by type
        document_id: Database document ID
        case_id: Database case ID
        sparse_vectors: Optional sparse vectors
        collection_name: Optional collection name

    Returns:
        True if indexing successful
    """
    indexer = QdrantIndexer(collection_name=collection_name)
    return indexer.index_chunks(
        chunks=chunks,
        embeddings=embeddings,
        sparse_vectors=sparse_vectors,
        document_id=document_id,
        case_id=case_id,
    )
