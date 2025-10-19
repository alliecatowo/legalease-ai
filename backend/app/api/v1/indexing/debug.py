"""Debug endpoints for Qdrant indexing inspection."""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.core.qdrant import get_qdrant_client
from qdrant_client.models import Filter, FieldCondition, MatchValue

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/debug/chunk-types",
    status_code=status.HTTP_200_OK,
    summary="[DEBUG] Check chunk types in Qdrant",
    description="Debug endpoint to check what chunk_types exist in Qdrant and their counts.",
)
async def debug_chunk_types(
    case_gid: Optional[str] = Query(None, description="Filter by case GID"),
):
    """
    Debug endpoint to check chunk types in Qdrant.

    This endpoint scrolls through points in Qdrant and counts how many
    of each chunk_type exist. Useful for debugging search issues.

    Args:
        case_gid: Optional case GID to filter by

    Returns:
        Dictionary with chunk type statistics
    """
    try:
        from app.core.config import settings

        client = get_qdrant_client()
        collection_name = settings.QDRANT_COLLECTION

        # Build filter if case_gid provided
        scroll_filter = None
        if case_gid:
            scroll_filter = Filter(
                must=[
                    FieldCondition(
                        key="case_gid",
                        match=MatchValue(value=case_gid),
                    )
                ]
            )

        # Scroll through all points and count chunk types
        chunk_type_counts = {}
        offset = None
        batch_size = 100
        total_points = 0

        while True:
            response = client.scroll(
                collection_name=collection_name,
                scroll_filter=scroll_filter,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            points, next_offset = response

            if not points:
                break

            for point in points:
                total_points += 1
                chunk_type = point.payload.get("chunk_type", "MISSING")
                chunk_type_counts[chunk_type] = chunk_type_counts.get(chunk_type, 0) + 1

            if next_offset is None:
                break

            offset = next_offset

        logger.info(f"Debug chunk types: {chunk_type_counts} (total: {total_points}, case_gid: {case_gid})")

        return {
            "total_points": total_points,
            "chunk_type_counts": chunk_type_counts,
            "case_gid_filter": case_gid,
            "collection": collection_name,
        }

    except Exception as e:
        logger.error(f"Error in debug chunk types: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check chunk types: {str(e)}",
        )


@router.get(
    "/debug/transcript-segments",
    status_code=status.HTTP_200_OK,
    summary="[DEBUG] Check transcript segments in Qdrant",
    description="Debug endpoint to check transcript_segment points in Qdrant.",
)
async def debug_transcript_segments(
    case_gid: Optional[str] = Query(None, description="Filter by case GID"),
    limit: int = Query(10, ge=1, le=100, description="Number of samples to return"),
):
    """
    Debug endpoint to check transcript segments in Qdrant.

    Returns sample transcript_segment points from Qdrant to verify
    they're indexed correctly.

    Args:
        case_gid: Optional case GID to filter by
        limit: Number of sample points to return

    Returns:
        Dictionary with transcript segment samples and statistics
    """
    try:
        from app.core.config import settings

        client = get_qdrant_client()
        collection_name = settings.QDRANT_COLLECTION

        # Build filter for transcript segments
        conditions = [
            FieldCondition(
                key="chunk_type",
                match=MatchValue(value="transcript_segment"),
            )
        ]

        if case_gid:
            conditions.append(
                FieldCondition(
                    key="case_gid",
                    match=MatchValue(value=case_gid),
                )
            )

        scroll_filter = Filter(must=conditions)

        # Scroll to get samples
        response = client.scroll(
            collection_name=collection_name,
            scroll_filter=scroll_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        points, _ = response

        # Format samples
        samples = []
        for point in points:
            samples.append({
                "id": str(point.id),
                "transcription_id": point.payload.get("transcription_id"),
                "document_id": point.payload.get("document_id"),
                "case_id": point.payload.get("case_id"),
                "speaker": point.payload.get("speaker"),
                "text_preview": point.payload.get("text", "")[:100] + "..." if point.payload.get("text") else None,
                "start_time": point.payload.get("start_time"),
                "end_time": point.payload.get("end_time"),
            })

        logger.info(f"Debug transcript segments: found {len(samples)} samples (case_gid: {case_gid})")

        return {
            "total_samples": len(samples),
            "case_gid_filter": case_gid,
            "collection": collection_name,
            "samples": samples,
        }

    except Exception as e:
        logger.error(f"Error in debug transcript segments: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check transcript segments: {str(e)}",
        )
