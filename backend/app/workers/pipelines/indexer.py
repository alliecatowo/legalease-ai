"""
Qdrant Indexer

Handles indexing of document chunks with embeddings into Qdrant vector database.
Supports multi-vector (summary, section, microblock) and hybrid (dense + sparse) indexing.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union
import uuid
from qdrant_client.models import PointStruct, SparseVector

from app.core.qdrant import get_qdrant_client, upsert_points
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_gid_from_uuid(model_class, uuid_id: uuid.UUID) -> Optional[str]:
    """
    Get GID from UUID by querying the database.

    Since NanoIDs are independent from UUIDs, we need to query the database
    to get the GID for a given UUID.

    Args:
        model_class: SQLAlchemy model class (Case, Document, etc.)
        uuid_id: UUID to look up

    Returns:
        GID string or None if not found
    """
    from app.core.database import SessionLocal

    try:
        db = SessionLocal()
        record = db.query(model_class).filter(model_class.id == uuid_id).first()
        if record and hasattr(record, 'gid'):
            return record.gid
        return None
    except Exception as e:
        logger.error(f"Error getting GID for UUID {uuid_id}: {e}")
        return None
    finally:
        db.close()


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
        document_id: Union[int, uuid.UUID] = None,
        case_id: Union[int, uuid.UUID] = None,
    ) -> bool:
        """
        Index document chunks with embeddings into Qdrant.

        Args:
            chunks: List of chunk dictionaries with text and metadata
            embeddings: Dictionary mapping vector types to embedding lists
                       e.g., {"summary": [...], "section": [...], "microblock": [...]}
            sparse_vectors: Optional list of sparse vectors (indices, values) for BM25
            document_id: Database document ID (UUID or legacy int)
            case_id: Database case ID (UUID or legacy int)

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
        document_id: Union[int, uuid.UUID] = None,
        case_id: Union[int, uuid.UUID] = None,
    ) -> List[PointStruct]:
        """
        Prepare Qdrant points from chunks and embeddings.

        Args:
            chunks: List of chunk dictionaries
            embeddings: Dictionary of embeddings by type
            sparse_vectors: Optional sparse vectors
            document_id: Database document ID (UUID or legacy int)
            case_id: Database case ID (UUID or legacy int)

        Returns:
            List of PointStruct objects
        """
        # Look up GIDs ONCE before the loop to avoid N+1 queries
        document_gid = None
        case_gid = None

        if isinstance(document_id, uuid.UUID):
            from app.models.document import Document
            document_gid = get_gid_from_uuid(Document, document_id)

        if isinstance(case_id, uuid.UUID):
            from app.models.case import Case
            case_gid = get_gid_from_uuid(Case, case_id)

        points = []

        # Group chunks by type, preserving original indices for sparse vector lookup
        chunks_by_type = {}
        for original_idx, chunk in enumerate(chunks):
            chunk_type = chunk.get("chunk_type", "section")
            if chunk_type not in chunks_by_type:
                chunks_by_type[chunk_type] = []
            # Store tuple of (original_index, chunk) to maintain sparse vector alignment
            chunks_by_type[chunk_type].append((original_idx, chunk))

        # Create points for each chunk type
        for chunk_type, type_chunks_with_idx in chunks_by_type.items():
            if chunk_type not in embeddings:
                logger.warning(f"No embeddings found for chunk type: {chunk_type}")
                continue

            type_embeddings = embeddings[chunk_type]

            if len(type_chunks_with_idx) != len(type_embeddings):
                logger.warning(
                    f"Chunk count mismatch for {chunk_type}: "
                    f"{len(type_chunks_with_idx)} chunks vs {len(type_embeddings)} embeddings"
                )
                # Use minimum to avoid index errors
                count = min(len(type_chunks_with_idx), len(type_embeddings))
                type_chunks_with_idx = type_chunks_with_idx[:count]
                type_embeddings = type_embeddings[:count]

            for i, ((original_idx, chunk), embedding) in enumerate(zip(type_chunks_with_idx, type_embeddings)):
                # Use original_idx to get correct sparse vector from flat list
                sparse_vec = None
                if sparse_vectors and original_idx < len(sparse_vectors):
                    sparse_vec = sparse_vectors[original_idx]

                point = self._create_point(
                    chunk=chunk,
                    embedding=embedding,
                    chunk_type=chunk_type,
                    sparse_vector=sparse_vec,
                    document_id=document_id,
                    case_id=case_id,
                    document_gid=document_gid,
                    case_gid=case_gid,
                )
                points.append(point)

        return points

    def _create_point(
        self,
        chunk: Dict[str, Any],
        embedding: List[float],
        chunk_type: str,
        sparse_vector: Optional[Tuple[List[int], List[float]]] = None,
        document_id: Union[int, uuid.UUID] = None,
        case_id: Union[int, uuid.UUID] = None,
        document_gid: Optional[str] = None,
        case_gid: Optional[str] = None,
    ) -> PointStruct:
        """
        Create a single Qdrant point.

        Args:
            chunk: Chunk dictionary
            embedding: Dense embedding vector
            chunk_type: Type of chunk (summary, section, microblock)
            sparse_vector: Optional sparse vector (indices, values)
            document_id: Database document ID (UUID or legacy int)
            case_id: Database case ID (UUID or legacy int)
            document_gid: Pre-computed document GID (avoids N+1 queries)
            case_gid: Pre-computed case GID (avoids N+1 queries)

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
            "char_count": chunk.get("char_count", len(chunk.get("text", ""))),
            "word_count": chunk.get("word_count", len(chunk.get("text", "").split())),
            "bboxes": chunk.get("bboxes", []),  # Store bounding boxes
        }

        # Add both legacy ID fields and new GID fields
        # Handle document_id (can be UUID or int)
        if document_id is not None:
            if isinstance(document_id, uuid.UUID):
                payload["document_id"] = str(document_id)  # Store UUID as string for backwards compat
                # Use pre-computed GID passed from _prepare_points() to avoid N+1 queries
                if document_gid:
                    payload["document_gid"] = document_gid
            else:
                payload["document_id"] = document_id  # Legacy int support

        # Handle case_id (can be UUID or int)
        if case_id is not None:
            if isinstance(case_id, uuid.UUID):
                payload["case_id"] = str(case_id)  # Store UUID as string for backwards compat
                # Use pre-computed GID passed from _prepare_points() to avoid N+1 queries
                if case_gid:
                    payload["case_gid"] = case_gid
            else:
                payload["case_id"] = case_id  # Legacy int support

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
        document_id: Union[int, uuid.UUID] = None,
        case_id: Union[int, uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Index a single chunk.

        Args:
            text: Chunk text
            embedding: Dense embedding vector
            chunk_type: Type of chunk
            sparse_vector: Optional sparse vector
            document_id: Database document ID (UUID or legacy int)
            case_id: Database case ID (UUID or legacy int)
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
        document_id: Union[int, uuid.UUID, str],
    ) -> bool:
        """
        Delete all chunks for a document from Qdrant.

        Args:
            document_id: Database document ID (UUID, GID string, or legacy int)

        Returns:
            True if deletion successful
        """
        from app.core.qdrant import delete_by_filter
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        try:
            logger.info(f"Deleting chunks for document {document_id}")

            # Build filter based on ID type
            filter_key = None
            filter_value = None

            if isinstance(document_id, uuid.UUID):
                # Use GID filter for UUID
                from app.models.document import Document
                filter_key = "document_gid"
                filter_value = get_gid_from_uuid(Document, document_id)
            elif isinstance(document_id, str):
                # Assume string is GID
                filter_key = "document_gid"
                filter_value = document_id
            else:
                # Legacy int support
                filter_key = "document_id"
                filter_value = document_id

            filters = Filter(
                must=[
                    FieldCondition(
                        key=filter_key,
                        match=MatchValue(value=filter_value),
                    )
                ]
            )

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
        case_id: Union[int, uuid.UUID, str],
    ) -> bool:
        """
        Delete all chunks for a case from Qdrant.

        Args:
            case_id: Database case ID (UUID, GID string, or legacy int)

        Returns:
            True if deletion successful
        """
        from app.core.qdrant import delete_by_filter
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        try:
            logger.info(f"Deleting chunks for case {case_id}")

            # Build filter based on ID type
            filter_key = None
            filter_value = None

            if isinstance(case_id, uuid.UUID):
                # Use GID filter for UUID
                from app.models.case import Case
                filter_key = "case_gid"
                filter_value = get_gid_from_uuid(Case, case_id)
            elif isinstance(case_id, str):
                # Assume string is GID
                filter_key = "case_gid"
                filter_value = case_id
            else:
                # Legacy int support
                filter_key = "case_id"
                filter_value = case_id

            filters = Filter(
                must=[
                    FieldCondition(
                        key=filter_key,
                        match=MatchValue(value=filter_value),
                    )
                ]
            )

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
    document_id: Union[int, uuid.UUID],
    case_id: Union[int, uuid.UUID],
    sparse_vectors: Optional[List[Tuple[List[int], List[float]]]] = None,
    collection_name: Optional[str] = None,
) -> bool:
    """
    Convenience function to index documents.

    Args:
        chunks: List of chunk dictionaries
        embeddings: Dictionary of embeddings by type
        document_id: Database document ID (UUID or legacy int)
        case_id: Database case ID (UUID or legacy int)
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
