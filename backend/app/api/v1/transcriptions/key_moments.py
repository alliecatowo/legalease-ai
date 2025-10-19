"""Key moments management endpoints for transcriptions."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.services.transcription import TranscriptionService
from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


# Request/response models
class KeyMomentToggleRequest(BaseModel):
    """Request model for toggling key moment status."""
    is_key_moment: bool = Field(..., description="Whether to mark as key moment")


class KeyMomentToggleResponse(BaseModel):
    """Response model for key moment toggle."""
    segment_id: str = Field(..., description="Segment UUID")
    is_key_moment: bool = Field(..., description="Current key moment status")
    updated_at: str = Field(..., description="Last update timestamp")


class KeyMomentSegment(BaseModel):
    """Schema for a key moment segment."""
    segment_id: str = Field(..., description="Segment UUID")
    text: str = Field(..., description="Segment text")
    speaker: Optional[str] = Field(None, description="Speaker identifier")
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    confidence: Optional[float] = Field(None, description="Transcription confidence")


class KeyMomentsResponse(BaseModel):
    """Response model for key moments list."""
    transcription_id: int = Field(..., description="Transcription ID")
    key_moments: List[KeyMomentSegment] = Field(..., description="List of key moments")
    total: int = Field(..., description="Total number of key moments")


@router.patch(
    "/transcriptions/{transcription_gid}/segments/{segment_id}/key-moment",
    response_model=KeyMomentToggleResponse,
    summary="Toggle key moment status",
    description="Mark or unmark a transcript segment as a key moment. "
    "Key moments are important segments that users want to highlight for quick reference.",
)
def toggle_key_moment(
    transcription_gid: str = Path(..., description="GID of the transcription"),
    segment_id: str = Path(..., description="UUID of the segment"),
    request: KeyMomentToggleRequest = Body(...),
    db: Session = Depends(get_db),
):
    """
    Toggle key moment status for a transcript segment.

    Args:
        transcription_gid: GID of the transcription
        segment_id: UUID of the segment
        request: Toggle request with is_key_moment status
        db: Database session

    Returns:
        KeyMomentToggleResponse: Updated segment metadata
    """
    logger.info(
        f"Toggling key moment for segment {segment_id} in transcription {transcription_gid}: {request.is_key_moment}"
    )

    result = TranscriptionService.toggle_key_moment(
        transcription_gid=transcription_gid,
        segment_id=segment_id,
        is_key_moment=request.is_key_moment,
        db=db,
    )

    return KeyMomentToggleResponse(**result)


@router.get(
    "/transcriptions/{transcription_gid}/key-moments",
    response_model=KeyMomentsResponse,
    summary="Get all key moments",
    description="Retrieve all segments marked as key moments for a transcription, "
    "including full segment data (text, speaker, timing, confidence).",
)
def get_key_moments(
    transcription_gid: str = Path(..., description="GID of the transcription"),
    db: Session = Depends(get_db),
):
    """
    Get all key moments for a transcription.

    Args:
        transcription_gid: GID of the transcription
        db: Database session

    Returns:
        KeyMomentsResponse: List of key moments with full segment data
    """
    logger.info(f"Getting key moments for transcription {transcription_gid}")

    result = TranscriptionService.get_key_moments(
        transcription_gid=transcription_gid, db=db
    )

    return KeyMomentsResponse(**result)
