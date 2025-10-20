"""
Communication vector repository for Qdrant operations.

Handles indexing and searching of communications (messages, emails, chats)
from forensic exports like Cellebrite AXIOM.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

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
from app.domain.evidence.entities.communication import Communication

logger = logging.getLogger(__name__)


class QdrantCommunicationRepository(BaseQdrantRepository):
    """
    Repository for communication vector operations in Qdrant.

    Manages communication embeddings with support for:
    - Thread grouping
    - Participant filtering
    - Platform filtering
    - Temporal filtering
    """

    def __init__(self):
        """Initialize communication vector repository."""
        super().__init__(collection_name=CollectionName.COMMUNICATIONS.value)

    async def index_communications(
        self,
        case_id: UUID,
        communications: List[Communication],
        embeddings: List[List[float]],
        sparse_vectors: Optional[List[Any]] = None,
    ) -> bool:
        """
        Index communications with embeddings.

        Args:
            case_id: UUID of the case
            communications: List of Communication entities
            embeddings: List of dense embeddings (one per communication)
            sparse_vectors: Optional BM25 sparse vectors

        Returns:
            True if indexing successful

        Raises:
            IndexingException: If indexing fails
        """
        if len(communications) == 0:
            logger.warning(f"No communications to index for case {case_id}")
            return True

        if len(embeddings) != len(communications):
            raise IndexingException(
                "Embedding count mismatch with communications",
                context={
                    "case_id": str(case_id),
                    "communications": len(communications),
                    "embeddings": len(embeddings),
                },
            )

        # Build points
        points = []
        for i, comm in enumerate(communications):
            # Build vector dict
            vector_dict = {"dense": embeddings[i]}

            # Add sparse vector if provided
            if sparse_vectors and i < len(sparse_vectors):
                vector_dict["bm25"] = sparse_vectors[i]

            # Build payload
            payload = {
                "case_id": str(case_id),
                "communication_id": str(comm.id),
                "thread_id": comm.thread_id,
                "sender_id": comm.sender.identifier,
                "sender_name": comm.sender.name,
                "participant_ids": [p.identifier for p in comm.participants],
                "participant_names": [p.name for p in comm.participants if p.name],
                "timestamp": comm.timestamp.isoformat(),
                "timestamp_unix": comm.timestamp.timestamp(),
                "body": comm.body,
                "platform": comm.platform.value,
                "communication_type": comm.communication_type.value,
                "device_id": comm.device_id,
                "has_attachments": comm.has_attachments(),
                "attachment_count": comm.get_attachment_count(),
            }

            # Add metadata
            payload.update(comm.metadata)

            # Create point with communication ID
            point_id = str(comm.id)

            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector_dict,
                    payload=payload,
                )
            )

        # Upsert points
        logger.info(
            f"Indexing {len(points)} communications for case {case_id}"
        )
        return await self.upsert_points(points)

    async def search_communications(
        self,
        query_embedding: List[float],
        case_ids: Optional[List[UUID]] = None,
        thread_ids: Optional[List[str]] = None,
        participant_ids: Optional[List[str]] = None,
        platforms: Optional[List[str]] = None,
        communication_types: Optional[List[str]] = None,
        date_range: Optional[tuple[datetime, datetime]] = None,
        top_k: int = 10,
        score_threshold: Optional[float] = None,
        sparse_vector: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search communications using hybrid search with filters.

        Args:
            query_embedding: Dense query embedding
            case_ids: Optional filter by case IDs
            thread_ids: Optional filter by thread IDs
            participant_ids: Optional filter by participant identifiers
            platforms: Optional filter by platforms
            communication_types: Optional filter by communication types
            date_range: Optional (start, end) datetime range
            top_k: Number of results to return
            score_threshold: Minimum score threshold
            sparse_vector: Optional BM25 sparse vector

        Returns:
            List of search results with communications and scores

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

        # Thread filter
        if thread_ids:
            if len(thread_ids) == 1:
                filter_conditions.append(
                    FieldCondition(
                        key="thread_id",
                        match=MatchValue(value=thread_ids[0]),
                    )
                )
            else:
                filter_conditions.append(
                    FieldCondition(
                        key="thread_id",
                        match=MatchAny(any=thread_ids),
                    )
                )

        # Participant filter (check if any participant matches)
        if participant_ids:
            if len(participant_ids) == 1:
                filter_conditions.append(
                    FieldCondition(
                        key="participant_ids",
                        match=MatchValue(value=participant_ids[0]),
                    )
                )
            else:
                filter_conditions.append(
                    FieldCondition(
                        key="participant_ids",
                        match=MatchAny(any=participant_ids),
                    )
                )

        # Platform filter
        if platforms:
            if len(platforms) == 1:
                filter_conditions.append(
                    FieldCondition(
                        key="platform",
                        match=MatchValue(value=platforms[0]),
                    )
                )
            else:
                filter_conditions.append(
                    FieldCondition(
                        key="platform",
                        match=MatchAny(any=platforms),
                    )
                )

        # Communication type filter
        if communication_types:
            if len(communication_types) == 1:
                filter_conditions.append(
                    FieldCondition(
                        key="communication_type",
                        match=MatchValue(value=communication_types[0]),
                    )
                )
            else:
                filter_conditions.append(
                    FieldCondition(
                        key="communication_type",
                        match=MatchAny(any=communication_types),
                    )
                )

        # Date range filter
        if date_range:
            start_date, end_date = date_range
            filter_conditions.append(
                FieldCondition(
                    key="timestamp_unix",
                    range=Range(
                        gte=start_date.timestamp(),
                        lte=end_date.timestamp(),
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

    async def delete_communications(self, case_id: UUID) -> bool:
        """
        Delete all communications for a case.

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

        logger.info(f"Deleting all communications for case {case_id} from vector store")
        return await self.delete_by_filter(filter_conditions)

    async def delete_thread(self, thread_id: str) -> bool:
        """
        Delete all communications in a thread.

        Args:
            thread_id: Thread identifier

        Returns:
            True if successful

        Raises:
            DeletionException: If deletion fails
        """
        filter_conditions = Filter(
            must=[
                FieldCondition(
                    key="thread_id",
                    match=MatchValue(value=thread_id),
                )
            ]
        )

        logger.info(f"Deleting thread {thread_id} from vector store")
        return await self.delete_by_filter(filter_conditions)

    async def get_thread_communications(
        self,
        thread_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all communications in a thread, ordered by timestamp.

        Args:
            thread_id: Thread identifier
            limit: Optional limit on number of communications

        Returns:
            List of communication payloads sorted by timestamp

        Raises:
            SearchException: If retrieval fails
        """
        try:
            async with self.client.get_client() as qdrant:
                filters = Filter(
                    must=[
                        FieldCondition(
                            key="thread_id",
                            match=MatchValue(value=thread_id),
                        )
                    ]
                )

                results = []
                offset = None
                scroll_limit = 100 if limit is None else min(limit, 100)

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

                    if limit and len(results) >= limit:
                        results = results[:limit]
                        break

                    if next_offset is None:
                        break

                    offset = next_offset

                # Sort by timestamp
                results.sort(key=lambda x: x["payload"].get("timestamp_unix", 0))

                return results

        except Exception as e:
            raise SearchException(
                f"Failed to get communications for thread {thread_id}",
                cause=e,
                context={"thread_id": thread_id},
            )

    async def get_participant_communications(
        self,
        case_id: UUID,
        participant_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all communications involving a participant.

        Args:
            case_id: UUID of the case
            participant_id: Participant identifier
            limit: Optional limit on number of communications

        Returns:
            List of communication payloads

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
                            key="participant_ids",
                            match=MatchValue(value=participant_id),
                        ),
                    ]
                )

                results = []
                offset = None
                scroll_limit = 100 if limit is None else min(limit, 100)

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

                    if limit and len(results) >= limit:
                        results = results[:limit]
                        break

                    if next_offset is None:
                        break

                    offset = next_offset

                return results

        except Exception as e:
            raise SearchException(
                f"Failed to get communications for participant {participant_id}",
                cause=e,
                context={"case_id": str(case_id), "participant_id": participant_id},
            )
