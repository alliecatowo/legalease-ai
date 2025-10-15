"""
Transcript indexing service for Qdrant vector database.

This module provides the TranscriptIndexingService class for indexing
transcription segments into Qdrant for semantic search alongside documents.
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
)
from app.core.config import settings
from app.models.transcription import Transcription
from app.models.document import Document
from app.models.case import Case

logger = logging.getLogger(__name__)


class TranscriptIndexingService:
    """
    Service for indexing transcription segments into Qdrant vector database.

    This service handles:
    - Transcript segment indexing with speaker information
    - Semantic search across transcription text
    - Speaker-based filtering
    - Timestamp-based retrieval
    - Integration with existing document search

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
        Initialize the transcript indexing service.

        Args:
            embedding_model_name: Name of the SentenceTransformer model to use
            collection_name: Qdrant collection name (default: from settings)
        """
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.client = get_qdrant_client()
        logger.info(
            f"TranscriptIndexingService initialized with model: {embedding_model_name}, "
            f"collection: {self.collection_name}"
        )

    def _generate_embeddings(self, text: str) -> Dict[str, List[float]]:
        """
        Generate embeddings for transcript segment.

        Args:
            text: Input text to embed

        Returns:
            Dictionary mapping vector names to embedding lists
        """
        try:
            # Generate base embedding
            embedding = self.embedding_model.encode(text, convert_to_tensor=False)
            embedding_list = embedding.tolist()

            # Use same embedding for all vector types
            # Transcripts are typically shorter segments, so microblock is most appropriate
            return {
                "summary": embedding_list,
                "section": embedding_list,
                "microblock": embedding_list,
            }
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise

    def _create_bm25_vector(self, text: str) -> Dict[str, Any]:
        """
        Create BM25 sparse vector from text for keyword matching.

        Args:
            text: Input text

        Returns:
            Dictionary with indices and values for sparse vector
        """
        import re

        # Simple tokenization
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = text.split()

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
        segment: Dict[str, Any],
        segment_index: int,
        transcription_id: int,
        document_id: int,
        case_id: int,
        embeddings: Optional[Dict[str, List[float]]] = None,
    ) -> PointStruct:
        """
        Create a Qdrant PointStruct from a transcript segment.

        Args:
            segment: Segment dictionary from transcription
            segment_index: Index of this segment in the transcript
            transcription_id: Associated transcription ID
            document_id: Associated document ID
            case_id: Associated case ID
            embeddings: Pre-computed embeddings (will generate if None)

        Returns:
            PointStruct ready for upsertion to Qdrant
        """
        text = segment.get('text', '').strip()

        # Generate embeddings if not provided
        if embeddings is None:
            embeddings = self._generate_embeddings(text)

        # Create BM25 sparse vector
        bm25_vector = self._create_bm25_vector(text)

        # Build payload with metadata
        payload = {
            "transcription_id": transcription_id,
            "document_id": document_id,
            "case_id": case_id,
            "text": text,
            "chunk_type": "transcript_segment",  # Distinguish from document chunks
            "position": segment_index,
            "segment_index": segment_index,

            # Transcript-specific fields
            "speaker": segment.get('speaker', 'UNKNOWN'),
            "start_time": segment.get('start', 0.0),
            "end_time": segment.get('end', 0.0),
            "duration": segment.get('end', 0.0) - segment.get('start', 0.0),

            # Word-level data if available
            "has_word_timestamps": bool(segment.get('words')),
            "word_count": len(segment.get('words', [])) if segment.get('words') else len(text.split()),
        }

        # Generate unique point ID: use negative transcription_id * 10000 + segment_index
        # This ensures no collision with document chunk IDs (which are positive)
        point_id = -(transcription_id * 100000 + segment_index)

        # Create point with both dense and sparse vectors
        point = PointStruct(
            id=point_id,
            vector={
                "summary": embeddings["summary"],
                "section": embeddings["section"],
                "microblock": embeddings["microblock"],
                "bm25": bm25_vector,
            },
            payload=payload,
        )

        return point

    def index_transcription(
        self,
        transcription_id: int,
        db: Session,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Index a transcription's segments into Qdrant.

        This method:
        1. Retrieves the transcription with segments
        2. Generates embeddings for each segment
        3. Creates Qdrant points with multi-vector embeddings
        4. Upserts points to the collection

        Args:
            transcription_id: ID of the transcription to index
            db: Database session
            batch_size: Number of points to upload per batch

        Returns:
            Dictionary with indexing statistics

        Raises:
            ValueError: If transcription not found
            Exception: For indexing errors
        """
        logger.info(f"Starting indexing for transcription {transcription_id}")

        try:
            # Fetch transcription
            transcription = db.query(Transcription).filter(
                Transcription.id == transcription_id
            ).first()

            if not transcription:
                raise ValueError(f"Transcription {transcription_id} not found")

            # Get document and case info
            document = db.query(Document).filter(
                Document.id == transcription.document_id
            ).first()

            if not document:
                raise ValueError(f"Document {transcription.document_id} not found for transcription {transcription_id}")

            # Get segments
            segments = transcription.segments

            if not segments:
                logger.warning(f"No segments found for transcription {transcription_id}")
                return {
                    "transcription_id": transcription_id,
                    "indexed_count": 0,
                    "failed_count": 0,
                    "message": "No segments to index",
                }

            # Create points for all segments
            points = []
            failed_segments = []

            for idx, segment in enumerate(segments):
                try:
                    point = self._create_point(
                        segment=segment,
                        segment_index=idx,
                        transcription_id=transcription.id,
                        document_id=document.id,
                        case_id=document.case_id,
                    )
                    points.append(point)
                except Exception as e:
                    logger.error(f"Failed to create point for segment {idx}: {e}")
                    failed_segments.append(idx)

            # Upsert points to Qdrant
            if points:
                upsert_points(
                    points=points,
                    collection_name=self.collection_name,
                    batch_size=batch_size,
                )

            result = {
                "transcription_id": transcription_id,
                "document_id": document.id,
                "case_id": document.case_id,
                "indexed_count": len(points),
                "failed_count": len(failed_segments),
                "total_segments": len(segments),
                "timestamp": datetime.utcnow().isoformat(),
            }

            if failed_segments:
                result["failed_segment_indices"] = failed_segments

            logger.info(
                f"Indexed transcription {transcription_id}: {len(points)} segments "
                f"({len(failed_segments)} failed)"
            )

            return result

        except Exception as e:
            logger.error(f"Error indexing transcription {transcription_id}: {e}", exc_info=True)
            raise

    def batch_index(
        self,
        transcription_ids: List[int],
        db: Session,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Index multiple transcriptions in batch.

        Args:
            transcription_ids: List of transcription IDs to index
            db: Database session
            batch_size: Number of points to upload per batch

        Returns:
            Dictionary with aggregated indexing statistics
        """
        logger.info(f"Starting batch indexing for {len(transcription_ids)} transcriptions")

        results = {
            "total_transcriptions": len(transcription_ids),
            "successful_transcriptions": 0,
            "failed_transcriptions": 0,
            "total_segments_indexed": 0,
            "total_segments_failed": 0,
            "transcription_results": [],
            "timestamp": datetime.utcnow().isoformat(),
        }

        for trans_id in transcription_ids:
            try:
                trans_result = self.index_transcription(
                    transcription_id=trans_id,
                    db=db,
                    batch_size=batch_size,
                )

                results["successful_transcriptions"] += 1
                results["total_segments_indexed"] += trans_result.get("indexed_count", 0)
                results["total_segments_failed"] += trans_result.get("failed_count", 0)
                results["transcription_results"].append(trans_result)

            except Exception as e:
                logger.error(f"Failed to index transcription {trans_id}: {e}")
                results["failed_transcriptions"] += 1
                results["transcription_results"].append({
                    "transcription_id": trans_id,
                    "error": str(e),
                    "indexed_count": 0,
                    "failed_count": 0,
                })

        logger.info(
            f"Batch indexing completed: {results['successful_transcriptions']}/{len(transcription_ids)} "
            f"transcriptions successful, {results['total_segments_indexed']} segments indexed"
        )

        return results

    def update_index(
        self,
        transcription_id: int,
        db: Session,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Update the index for a transcription.

        This is essentially a re-index operation that:
        1. Deletes existing points for the transcription
        2. Indexes the current segments

        Args:
            transcription_id: ID of the transcription to update
            db: Database session
            batch_size: Number of points to upload per batch

        Returns:
            Dictionary with update statistics
        """
        logger.info(f"Updating index for transcription {transcription_id}")

        try:
            # First, delete existing entries
            delete_result = self.delete_from_index(transcription_id=transcription_id)

            # Then, re-index
            index_result = self.index_transcription(
                transcription_id=transcription_id,
                db=db,
                batch_size=batch_size,
            )

            result = {
                "transcription_id": transcription_id,
                "deleted": delete_result.get("deleted", False),
                "indexed_count": index_result.get("indexed_count", 0),
                "failed_count": index_result.get("failed_count", 0),
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info(f"Updated index for transcription {transcription_id}: {result}")
            return result

        except Exception as e:
            logger.error(f"Error updating index for transcription {transcription_id}: {e}")
            raise

    def delete_from_index(
        self,
        transcription_id: int,
    ) -> Dict[str, Any]:
        """
        Delete all segments of a transcription from the index.

        Uses Qdrant's filter-based deletion to remove all points
        associated with the transcription.

        Args:
            transcription_id: ID of the transcription to remove

        Returns:
            Dictionary with deletion status
        """
        logger.info(f"Deleting transcription {transcription_id} from index")

        try:
            # Build filter for transcription
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="transcription_id",
                        match=MatchValue(value=transcription_id),
                    )
                ]
            )

            # Delete points matching filter
            success = delete_by_filter(
                filters=filter_condition,
                collection_name=self.collection_name,
            )

            result = {
                "transcription_id": transcription_id,
                "deleted": success,
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info(f"Deleted transcription {transcription_id} from index: {success}")
            return result

        except Exception as e:
            logger.error(f"Error deleting transcription {transcription_id} from index: {e}")
            raise

    def index_case_transcriptions(
        self,
        case_id: int,
        db: Session,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Index all transcriptions in a case.

        Retrieves all transcriptions for a case and indexes them in batch.

        Args:
            case_id: ID of the case to index
            db: Database session
            batch_size: Number of points to upload per batch

        Returns:
            Dictionary with case indexing statistics

        Raises:
            ValueError: If case not found
        """
        logger.info(f"Starting transcription indexing for case {case_id}")

        try:
            # Fetch case
            case = db.query(Case).filter(Case.id == case_id).first()
            if not case:
                raise ValueError(f"Case {case_id} not found")

            # Get all documents for the case
            documents = db.query(Document).filter(
                Document.case_id == case_id
            ).all()

            # Get all transcriptions for these documents
            document_ids = [doc.id for doc in documents]
            transcriptions = db.query(Transcription).filter(
                Transcription.document_id.in_(document_ids)
            ).all()

            transcription_ids = [trans.id for trans in transcriptions]

            if not transcription_ids:
                logger.warning(f"No transcriptions found for case {case_id}")
                return {
                    "case_id": case_id,
                    "total_transcriptions": 0,
                    "indexed_count": 0,
                    "message": "No transcriptions to index",
                }

            # Batch index all transcriptions
            result = self.batch_index(
                transcription_ids=transcription_ids,
                db=db,
                batch_size=batch_size,
            )

            # Add case information
            result["case_id"] = case_id
            result["case_number"] = case.case_number
            result["case_name"] = case.name

            logger.info(
                f"Indexed transcriptions for case {case_id}: {result['successful_transcriptions']} transcriptions, "
                f"{result['total_segments_indexed']} segments"
            )

            return result

        except Exception as e:
            logger.error(f"Error indexing transcriptions for case {case_id}: {e}", exc_info=True)
            raise

    def delete_case_transcriptions_from_index(
        self,
        case_id: int,
    ) -> Dict[str, Any]:
        """
        Delete all transcriptions of a case from the index.

        Args:
            case_id: ID of the case to remove

        Returns:
            Dictionary with deletion status
        """
        logger.info(f"Deleting transcriptions for case {case_id} from index")

        try:
            # Build filter for case (transcript segments have case_id in payload)
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="case_id",
                        match=MatchValue(value=case_id),
                    ),
                    FieldCondition(
                        key="chunk_type",
                        match=MatchValue(value="transcript_segment"),
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

            logger.info(f"Deleted transcriptions for case {case_id} from index: {success}")
            return result

        except Exception as e:
            logger.error(f"Error deleting transcriptions for case {case_id} from index: {e}")
            raise


# Singleton instance for reuse
_transcript_indexing_service_instance: Optional[TranscriptIndexingService] = None


def get_transcript_indexing_service() -> TranscriptIndexingService:
    """
    Get or create singleton TranscriptIndexingService instance.

    Returns:
        TranscriptIndexingService instance
    """
    global _transcript_indexing_service_instance

    if _transcript_indexing_service_instance is None:
        _transcript_indexing_service_instance = TranscriptIndexingService()
        logger.info("Created new TranscriptIndexingService singleton instance")

    return _transcript_indexing_service_instance
