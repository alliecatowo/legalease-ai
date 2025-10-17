"""
Document indexing service for Qdrant vector database.

This module provides the IndexingService class for managing document indexing,
including batch operations, updates, and deletions from the Qdrant collection.
It handles multi-vector embeddings (summary, section, microblock) and maintains
proper metadata for legal document retrieval.
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from collections import defaultdict

from sqlalchemy.orm import Session
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

from app.core.qdrant import (
    get_qdrant_client,
    upsert_points,
    delete_by_filter,
    build_filter,
)
from app.core.config import settings
from app.models.document import Document
from app.models.chunk import Chunk
from app.models.case import Case

logger = logging.getLogger(__name__)


class IndexingService:
    """
    Service for indexing legal documents into Qdrant vector database.

    This service handles:
    - Single document indexing
    - Batch document indexing
    - Index updates for existing documents
    - Deletion from index
    - Multi-vector embedding generation (summary, section, microblock)
    - Metadata enrichment with case and document information

    Attributes:
        embedding_model: SentenceTransformer model for generating embeddings
        collection_name: Qdrant collection name for storing vectors
    """

    def __init__(
        self,
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        collection_name: Optional[str] = None,
    ):
        """
        Initialize the indexing service.

        Args:
            embedding_model_name: Name of the SentenceTransformer model to use
            collection_name: Qdrant collection name (default: from settings)
        """
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.client = get_qdrant_client()
        logger.info(
            f"IndexingService initialized with model: {embedding_model_name}, "
            f"collection: {self.collection_name}"
        )

    def _generate_embeddings(self, text: str) -> Dict[str, List[float]]:
        """
        Generate embeddings for all vector types.

        Creates dense embeddings for summary, section, and microblock vectors.
        In this implementation, we use the same base embedding for all types,
        but in production you might use different models or text preprocessing
        for each vector type.

        Args:
            text: Input text to embed

        Returns:
            Dictionary mapping vector names to embedding lists
        """
        try:
            # Generate base embedding
            embedding = self.embedding_model.encode(text, convert_to_tensor=False)
            embedding_list = embedding.tolist()

            # For now, use the same embedding for all vector types
            # In production, you might want different processing per type:
            # - summary: embed the full document summary
            # - section: embed section-level text
            # - microblock: embed paragraph/sentence-level text
            return {
                "summary": embedding_list,
                "section": embedding_list,
                "microblock": embedding_list,
            }
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise

    def _create_bm25_vector(self, text: str, metadata_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Create BM25 sparse vector from text and optional metadata.

        This is a simplified implementation for keyword matching.

        Args:
            text: Input text
            metadata_text: Optional metadata text to include in search

        Returns:
            Dictionary with indices and values for sparse vector
        """
        import re

        # Combine text and metadata for BM25 indexing
        combined_text = text
        if metadata_text:
            combined_text = f"{metadata_text}\n{text}"

        # Simple tokenization
        combined_text = combined_text.lower()
        combined_text = re.sub(r'[^\w\s]', ' ', combined_text)
        tokens = combined_text.split()

        # Count token frequencies
        token_counts = defaultdict(int)
        for token in tokens:
            token_counts[token] += 1

        # Create sparse vector representation
        indices = []
        values = []

        for token, count in token_counts.items():
            # Use hash for token->index mapping
            token_idx = hash(token) % (2**31)  # Keep positive
            indices.append(token_idx)
            values.append(float(count))

        return {"indices": indices, "values": values}

    def _create_point(
        self,
        chunk: Chunk,
        case_id: int,
        embeddings: Optional[Dict[str, List[float]]] = None,
        document_metadata: Optional[Dict[str, Any]] = None,
    ) -> PointStruct:
        """
        Create a Qdrant PointStruct from a chunk.

        Args:
            chunk: Chunk object from database
            case_id: Associated case ID
            embeddings: Pre-computed embeddings (will generate if None)
            document_metadata: Optional document metadata (filename, etc.)

        Returns:
            PointStruct ready for upsertion to Qdrant
        """
        # Generate embeddings if not provided
        if embeddings is None:
            embeddings = self._generate_embeddings(chunk.text)

        # Build searchable metadata text from document metadata
        metadata_parts = []
        if document_metadata:
            # Include filename (most important for search)
            if document_metadata.get('filename'):
                filename = document_metadata['filename']
                # Add filename with and without extension for better matching
                metadata_parts.append(filename)
                # Also add filename without extension
                import os
                filename_without_ext = os.path.splitext(filename)[0]
                if filename_without_ext != filename:
                    metadata_parts.append(filename_without_ext)

            # Include document type if available
            if document_metadata.get('document_type'):
                metadata_parts.append(document_metadata['document_type'])

            # Include title if available
            if document_metadata.get('title'):
                metadata_parts.append(document_metadata['title'])

            # Include tags if available
            if document_metadata.get('tags'):
                tags = document_metadata['tags']
                if isinstance(tags, list):
                    metadata_parts.extend(tags)
                elif isinstance(tags, str):
                    metadata_parts.append(tags)

        # Combine metadata into searchable text
        metadata_text = " ".join(metadata_parts) if metadata_parts else None

        # Create BM25 sparse vector with metadata included
        bm25_vector = self._create_bm25_vector(chunk.text, metadata_text=metadata_text)

        # Build payload with metadata
        payload = {
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "case_id": case_id,
            "text": chunk.text,
            "chunk_type": chunk.chunk_type or "unknown",
            "position": chunk.position,
            "page_number": chunk.page_number,
            "created_at": chunk.created_at.isoformat() if chunk.created_at else None,
        }

        # Add document metadata to payload for display in search results
        if document_metadata:
            if document_metadata.get('filename'):
                payload["filename"] = document_metadata['filename']
            if document_metadata.get('document_type'):
                payload["document_type"] = document_metadata['document_type']
            if document_metadata.get('title'):
                payload["title"] = document_metadata['title']
            if document_metadata.get('tags'):
                payload["tags"] = document_metadata['tags']

        # Add any additional metadata from chunk
        if chunk.meta_data:
            payload["additional_metadata"] = chunk.meta_data
        if hasattr(chunk, "bboxes") and chunk.meta_data is not None:
            # Ensure bboxes are nested into metadata for viewer
            if "bboxes" in chunk.meta_data:
                payload["bboxes"] = chunk.meta_data["bboxes"]

        # Create point with both dense and sparse vectors
        point = PointStruct(
            id=chunk.id,  # Use chunk ID as point ID
            vector={
                "summary": embeddings["summary"],
                "section": embeddings["section"],
                "microblock": embeddings["microblock"],
                "bm25": bm25_vector,
            },
            payload=payload,
        )

        return point

    def index_document(
        self,
        document_id: int,
        db: Session,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Index a single document's chunks into Qdrant.

        This method:
        1. Retrieves all chunks for the document
        2. Generates embeddings for each chunk
        3. Creates Qdrant points with multi-vector embeddings
        4. Upserts points to the collection

        Args:
            document_id: ID of the document to index
            db: Database session
            batch_size: Number of points to upload per batch

        Returns:
            Dictionary with indexing statistics

        Raises:
            ValueError: If document not found
            Exception: For indexing errors
        """
        logger.info(f"Starting indexing for document {document_id}")

        try:
            # Fetch document with chunks
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError(f"Document {document_id} not found")

            # Get chunks
            chunks = db.query(Chunk).filter(
                Chunk.document_id == document_id
            ).order_by(Chunk.position).all()

            if not chunks:
                logger.warning(f"No chunks found for document {document_id}")
                return {
                    "document_id": document_id,
                    "indexed_count": 0,
                    "failed_count": 0,
                    "message": "No chunks to index",
                }

            # Build document metadata for searchable indexing
            doc_metadata = {
                'filename': document.filename,
                'document_type': None,
                'title': None,
                'tags': None,
            }

            # Extract additional metadata from document.meta_data JSON field
            if document.meta_data:
                doc_metadata['document_type'] = document.meta_data.get('document_type')
                doc_metadata['title'] = document.meta_data.get('title')
                doc_metadata['tags'] = document.meta_data.get('tags')

            # Create points for all chunks
            points = []
            failed_chunks = []

            for chunk in chunks:
                try:
                    point = self._create_point(
                        chunk=chunk,
                        case_id=document.case_id,
                        document_metadata=doc_metadata,
                    )
                    points.append(point)
                except Exception as e:
                    logger.error(f"Failed to create point for chunk {chunk.id}: {e}")
                    failed_chunks.append(chunk.id)

            # Upsert points to Qdrant
            if points:
                upsert_points(
                    points=points,
                    collection_name=self.collection_name,
                    batch_size=batch_size,
                )

            result = {
                "document_id": document_id,
                "case_id": document.case_id,
                "indexed_count": len(points),
                "failed_count": len(failed_chunks),
                "total_chunks": len(chunks),
                "timestamp": datetime.utcnow().isoformat(),
            }

            if failed_chunks:
                result["failed_chunk_ids"] = failed_chunks

            logger.info(
                f"Indexed document {document_id}: {len(points)} chunks "
                f"({len(failed_chunks)} failed)"
            )

            return result

        except Exception as e:
            logger.error(f"Error indexing document {document_id}: {e}", exc_info=True)
            raise

    def batch_index(
        self,
        documents: List[int],
        db: Session,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Index multiple documents in batch.

        This method processes multiple documents sequentially and aggregates results.
        For large batch operations, consider using async processing or task queues.

        Args:
            documents: List of document IDs to index
            db: Database session
            batch_size: Number of points to upload per batch

        Returns:
            Dictionary with aggregated indexing statistics
        """
        logger.info(f"Starting batch indexing for {len(documents)} documents")

        results = {
            "total_documents": len(documents),
            "successful_documents": 0,
            "failed_documents": 0,
            "total_chunks_indexed": 0,
            "total_chunks_failed": 0,
            "document_results": [],
            "timestamp": datetime.utcnow().isoformat(),
        }

        for doc_id in documents:
            try:
                doc_result = self.index_document(
                    document_id=doc_id,
                    db=db,
                    batch_size=batch_size,
                )

                results["successful_documents"] += 1
                results["total_chunks_indexed"] += doc_result.get("indexed_count", 0)
                results["total_chunks_failed"] += doc_result.get("failed_count", 0)
                results["document_results"].append(doc_result)

            except Exception as e:
                logger.error(f"Failed to index document {doc_id}: {e}")
                results["failed_documents"] += 1
                results["document_results"].append({
                    "document_id": doc_id,
                    "error": str(e),
                    "indexed_count": 0,
                    "failed_count": 0,
                })

        logger.info(
            f"Batch indexing completed: {results['successful_documents']}/{len(documents)} "
            f"documents successful, {results['total_chunks_indexed']} chunks indexed"
        )

        return results

    def update_index(
        self,
        document_id: int,
        db: Session,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Update the index for a document.

        This is essentially a re-index operation that:
        1. Deletes existing points for the document
        2. Indexes the current chunks

        Useful when document content has been modified or re-processed.

        Args:
            document_id: ID of the document to update
            db: Database session
            batch_size: Number of points to upload per batch

        Returns:
            Dictionary with update statistics
        """
        logger.info(f"Updating index for document {document_id}")

        try:
            # First, delete existing entries
            delete_result = self.delete_from_index(document_id=document_id)

            # Then, re-index
            index_result = self.index_document(
                document_id=document_id,
                db=db,
                batch_size=batch_size,
            )

            result = {
                "document_id": document_id,
                "deleted": delete_result.get("deleted", False),
                "indexed_count": index_result.get("indexed_count", 0),
                "failed_count": index_result.get("failed_count", 0),
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info(f"Updated index for document {document_id}: {result}")
            return result

        except Exception as e:
            logger.error(f"Error updating index for document {document_id}: {e}")
            raise

    def delete_from_index(
        self,
        document_id: int,
    ) -> Dict[str, Any]:
        """
        Delete all chunks of a document from the index.

        Uses Qdrant's filter-based deletion to remove all points
        associated with the document.

        Args:
            document_id: ID of the document to remove

        Returns:
            Dictionary with deletion status
        """
        logger.info(f"Deleting document {document_id} from index")

        try:
            # Build filter for document
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            )

            # Delete points matching filter
            success = delete_by_filter(
                filters=filter_condition,
                collection_name=self.collection_name,
            )

            result = {
                "document_id": document_id,
                "deleted": success,
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info(f"Deleted document {document_id} from index: {success}")
            return result

        except Exception as e:
            logger.error(f"Error deleting document {document_id} from index: {e}")
            raise

    def index_case(
        self,
        case_id: int,
        db: Session,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Index all documents in a case.

        Retrieves all documents for a case and indexes them in batch.

        Args:
            case_id: ID of the case to index
            db: Database session
            batch_size: Number of points to upload per batch

        Returns:
            Dictionary with case indexing statistics

        Raises:
            ValueError: If case not found
        """
        logger.info(f"Starting indexing for case {case_id}")

        try:
            # Fetch case with documents
            case = db.query(Case).filter(Case.id == case_id).first()
            if not case:
                raise ValueError(f"Case {case_id} not found")

            # Get all document IDs for the case
            documents = db.query(Document).filter(
                Document.case_id == case_id
            ).all()

            document_ids = [doc.id for doc in documents]

            if not document_ids:
                logger.warning(f"No documents found for case {case_id}")
                return {
                    "case_id": case_id,
                    "total_documents": 0,
                    "indexed_count": 0,
                    "message": "No documents to index",
                }

            # Batch index all documents
            result = self.batch_index(
                documents=document_ids,
                db=db,
                batch_size=batch_size,
            )

            # Add case information
            result["case_id"] = case_id
            result["case_number"] = case.case_number
            result["case_name"] = case.name

            logger.info(
                f"Indexed case {case_id}: {result['successful_documents']} documents, "
                f"{result['total_chunks_indexed']} chunks"
            )

            return result

        except Exception as e:
            logger.error(f"Error indexing case {case_id}: {e}", exc_info=True)
            raise

    def delete_case_from_index(
        self,
        case_id: int,
    ) -> Dict[str, Any]:
        """
        Delete all documents of a case from the index.

        Uses Qdrant's filter-based deletion to remove all points
        associated with the case.

        Args:
            case_id: ID of the case to remove

        Returns:
            Dictionary with deletion status
        """
        logger.info(f"Deleting case {case_id} from index")

        try:
            # Build filter for case
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="case_id",
                        match=MatchValue(value=case_id),
                    )
                ]
            )

            # Delete points matching filter
            success = delete_by_filter(
                filters=filter_condition,
                collection_name=self.collection_name,
            )

            result = {
                "case_id": case_id,
                "deleted": success,
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info(f"Deleted case {case_id} from index: {success}")
            return result

        except Exception as e:
            logger.error(f"Error deleting case {case_id} from index: {e}")
            raise


# Singleton instance for reuse
_indexing_service_instance: Optional[IndexingService] = None


def get_indexing_service() -> IndexingService:
    """
    Get or create singleton IndexingService instance.

    Returns:
        IndexingService instance
    """
    global _indexing_service_instance

    if _indexing_service_instance is None:
        _indexing_service_instance = IndexingService()
        logger.info("Created new IndexingService singleton instance")

    return _indexing_service_instance
