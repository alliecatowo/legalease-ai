"""
Transcript vector repository for Qdrant operations.

Handles indexing and searching of transcript segments with speaker
identification and temporal filtering.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

from qdrant_client.models import (
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
    Range,
)

from app.infrastructure.persistence.qdrant.repositories.base import BaseQdrantRepository
from app.infrastructure.persistence.qdrant.collection_manager import CollectionName
from app.infrastructure.exceptions import IndexingException, SearchException
from app.domain.evidence.entities.transcript import TranscriptSegment

logger = logging.getLogger(__name__)


class QdrantTranscriptRepository(BaseQdrantRepository):
    """
    Repository for transcript vector operations in Qdrant.

    Manages transcript segment embeddings with support for:
    - Speaker identification filtering
    - Temporal range queries
    - Segment-level semantic search
    """

    def __init__(self):
        """Initialize transcript vector repository."""
        super().__init__(collection_name=CollectionName.TRANSCRIPTS.value)

    async def index_transcript(
        self,
        transcript_id: UUID,
        case_id: UUID,
        segments: List[TranscriptSegment],
        embeddings: List[List[float]],
        sparse_vectors: Optional[List[Any]] = None,
    ) -> bool:
        """
        Index a transcript with its segments and embeddings.

        Args:
            transcript_id: UUID of the transcript
            case_id: UUID of the case
            segments: List of TranscriptSegment value objects
            embeddings: List of dense embeddings (one per segment)
            sparse_vectors: Optional BM25 sparse vectors

        Returns:
            True if indexing successful

        Raises:
            IndexingException: If indexing fails
        """
        if len(segments) == 0:
            logger.warning(f"No segments to index for transcript {transcript_id}")
            return True

        if len(embeddings) != len(segments):
            raise IndexingException(
                "Embedding count mismatch with segments",
                context={
                    "transcript_id": str(transcript_id),
                    "segments": len(segments),
                    "embeddings": len(embeddings),
                },
            )

        # Build points
        points = []
        for i, segment in enumerate(segments):
            # Build vector dict
            vector_dict = {"dense": embeddings[i]}

            # Add sparse vector if provided
            if sparse_vectors and i < len(sparse_vectors):
                vector_dict["bm25"] = sparse_vectors[i]

            # Build payload
            payload = {
                "case_id": str(case_id),
                "transcript_id": str(transcript_id),
                "segment_id": segment.id,
                "start_time": segment.start,
                "end_time": segment.end,
                "duration": segment.duration,
                "text": segment.text,
                "segment_type": segment.segment_type.value,
            }

            # Add speaker information if available
            if segment.speaker:
                payload["speaker_id"] = segment.speaker.id
                payload["speaker_name"] = segment.speaker.name
                if segment.speaker.confidence:
                    payload["speaker_confidence"] = segment.speaker.confidence

            # Add confidence if available
            if segment.confidence:
                payload["transcription_confidence"] = segment.confidence

            # Create point with segment ID
            point_id = f"{transcript_id}_{segment.id}"

            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector_dict,
                    payload=payload,
                )
            )

        # Upsert points
        logger.info(
            f"Indexing transcript {transcript_id}: {len(points)} segments"
        )
        return await self.upsert_points(points)

    async def search_transcripts(
        self,
        query_embedding: List[float],
        case_ids: Optional[List[UUID]] = None,
        transcript_ids: Optional[List[UUID]] = None,
        speaker_ids: Optional[List[str]] = None,
        time_range: Optional[Tuple[float, float]] = None,
        top_k: int = 10,
        score_threshold: Optional[float] = None,
        sparse_vector: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search transcripts using hybrid search with filters.

        Args:
            query_embedding: Dense query embedding
            case_ids: Optional filter by case IDs
            transcript_ids: Optional filter by transcript IDs
            speaker_ids: Optional filter by speaker IDs
            time_range: Optional (start, end) time range in seconds
            top_k: Number of results to return
            score_threshold: Minimum score threshold
            sparse_vector: Optional BM25 sparse vector

        Returns:
            List of search results with segments and scores

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

        # Transcript filter
        if transcript_ids:
            transcript_ids_str = [str(tid) for tid in transcript_ids]
            if len(transcript_ids_str) == 1:
                filter_conditions.append(
                    FieldCondition(
                        key="transcript_id",
                        match=MatchValue(value=transcript_ids_str[0]),
                    )
                )
            else:
                filter_conditions.append(
                    FieldCondition(
                        key="transcript_id",
                        match=MatchAny(any=transcript_ids_str),
                    )
                )

        # Speaker filter
        if speaker_ids:
            if len(speaker_ids) == 1:
                filter_conditions.append(
                    FieldCondition(
                        key="speaker_id",
                        match=MatchValue(value=speaker_ids[0]),
                    )
                )
            else:
                filter_conditions.append(
                    FieldCondition(
                        key="speaker_id",
                        match=MatchAny(any=speaker_ids),
                    )
                )

        # Time range filter
        if time_range:
            start_time, end_time = time_range
            # Filter segments that overlap with the time range
            filter_conditions.append(
                FieldCondition(
                    key="start_time",
                    range=Range(
                        lte=end_time,  # Segment starts before range ends
                    ),
                )
            )
            filter_conditions.append(
                FieldCondition(
                    key="end_time",
                    range=Range(
                        gte=start_time,  # Segment ends after range starts
                    ),
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

    async def delete_transcript(self, transcript_id: UUID) -> bool:
        """
        Delete all segments for a transcript.

        Args:
            transcript_id: UUID of the transcript to delete

        Returns:
            True if successful

        Raises:
            DeletionException: If deletion fails
        """
        filter_conditions = Filter(
            must=[
                FieldCondition(
                    key="transcript_id",
                    match=MatchValue(value=str(transcript_id)),
                )
            ]
        )

        logger.info(f"Deleting transcript {transcript_id} from vector store")
        return await self.delete_by_filter(filter_conditions)

    async def delete_case_transcripts(self, case_id: UUID) -> bool:
        """
        Delete all transcripts for a case.

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

        logger.info(f"Deleting all transcripts for case {case_id} from vector store")
        return await self.delete_by_filter(filter_conditions)

    async def get_transcript_segments(
        self,
        transcript_id: UUID,
        speaker_id: Optional[str] = None,
        time_range: Optional[Tuple[float, float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all segments for a transcript with optional filtering.

        Args:
            transcript_id: UUID of the transcript
            speaker_id: Optional filter by speaker ID
            time_range: Optional (start, end) time range

        Returns:
            List of segment payloads sorted by time

        Raises:
            SearchException: If retrieval fails
        """
        try:
            async with self.client.get_client() as qdrant:
                # Build filter
                filter_conditions = [
                    FieldCondition(
                        key="transcript_id",
                        match=MatchValue(value=str(transcript_id)),
                    )
                ]

                if speaker_id:
                    filter_conditions.append(
                        FieldCondition(
                            key="speaker_id",
                            match=MatchValue(value=speaker_id),
                        )
                    )

                if time_range:
                    start_time, end_time = time_range
                    filter_conditions.append(
                        FieldCondition(
                            key="start_time",
                            range=Range(lte=end_time),
                        )
                    )
                    filter_conditions.append(
                        FieldCondition(
                            key="end_time",
                            range=Range(gte=start_time),
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

                # Sort by start time
                results.sort(key=lambda x: x["payload"].get("start_time", 0))

                return results

        except Exception as e:
            raise SearchException(
                f"Failed to get segments for transcript {transcript_id}",
                cause=e,
                context={"transcript_id": str(transcript_id)},
            )

    async def get_speaker_segments(
        self,
        case_id: UUID,
        speaker_id: str,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all segments for a specific speaker across all transcripts.

        Args:
            case_id: UUID of the case
            speaker_id: Speaker identifier
            top_k: Optional limit on number of segments

        Returns:
            List of segment payloads

        Raises:
            SearchException: If retrieval fails
        """
        try:
            async with self.client.get_client() as qdrant:
                filters = Filter(
                    must=[
                        FieldCondition(
                            key="case_id",
                            match=MatchValue(value=str(case_id)),
                        ),
                        FieldCondition(
                            key="speaker_id",
                            match=MatchValue(value=speaker_id),
                        ),
                    ]
                )

                results = []
                offset = None
                limit = 100 if top_k is None else min(top_k, 100)

                while True:
                    scroll_result = await qdrant.scroll(
                        collection_name=self.collection_name,
                        scroll_filter=filters,
                        limit=limit,
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

                return results

        except Exception as e:
            raise SearchException(
                f"Failed to get segments for speaker {speaker_id}",
                cause=e,
                context={"case_id": str(case_id), "speaker_id": speaker_id},
            )
