"""Main CRUD endpoints for transcriptions."""

import logging
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Path, Form, Body, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.schemas.transcription import (
    TranscriptionResponse,
    TranscriptionListResponse,
    TranscriptionListItem,
    TranscriptionDeleteResponse,
    TranscriptionUploadResponse,
    TranscriptionOptions,
    TranscriptionReprocessResponse,
    UpdateSpeakerRequest,
    SpeakerResponse,
)
from app.services.transcription import TranscriptionService
from app.models.transcription import Transcription
from app.models.case import Case

logger = logging.getLogger(__name__)

router = APIRouter()


# Paginated list response model
class PaginatedTranscriptionListResponse(BaseModel):
    """Response model for paginated transcription lists."""
    transcriptions: List[TranscriptionListItem]
    total: int = Field(..., description="Total number of transcriptions")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")


@router.get(
    "/transcriptions",
    response_model=PaginatedTranscriptionListResponse,
    summary="List all transcriptions with pagination",
    description="Get all transcriptions across all cases with pagination support. "
    "This endpoint efficiently retrieves transcriptions in a single query to avoid N+1 query problems.",
)
def list_all_transcriptions(
    page: int = Query(1, ge=1, description="Page number (starting from 1)"),
    page_size: int = Query(50, ge=1, le=100, description="Number of items per page (max 100)"),
    case_gid: Optional[str] = Query(None, description="Optional case GID to filter transcriptions"),
    db: Session = Depends(get_db),
):
    """
    List all transcriptions with pagination.

    Args:
        page: Page number (starting from 1)
        page_size: Number of items per page (max 100)
        case_gid: Optional case GID to filter transcriptions
        db: Database session

    Returns:
        PaginatedTranscriptionListResponse: Paginated list of transcriptions with metadata
    """
    logger.info(f"Listing all transcriptions: page={page}, page_size={page_size}, case_gid={case_gid}")

    # Build base query with join to Case table to get case name and gid
    query = db.query(Transcription, Case.name.label('case_name'), Case.gid.label('case_gid')).join(
        Case, Transcription.case_id == Case.id
    )

    # Apply case filter if provided
    if case_gid is not None:
        query = query.filter(Case.gid == case_gid)

    # Get total count before pagination
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    results = query.order_by(Transcription.created_at.desc()).offset(offset).limit(page_size).all()

    logger.info(f"Found {total} total transcriptions, returning {len(results)} for page {page}")

    # Convert to list items with case_name and case_gid
    # Note: Using dict to avoid Pydantic validation issues with extra field case_name
    transcription_items = [
        {
            "id": trans.id,
            "gid": trans.gid,
            "case_id": trans.case_id,
            "case_gid": case_gid_val,
            "case_name": case_name,
            "filename": trans.filename,
            "format": trans.format,
            "duration": trans.duration,
            "segment_count": len(trans.segments) if trans.segments else 0,
            "speaker_count": len(trans.speakers) if trans.speakers else 0,
            "status": trans.status.value if trans.status else "unknown",
            "created_at": trans.created_at,
            "uploaded_at": trans.uploaded_at,
        }
        for trans, case_name, case_gid_val in results
    ]

    return PaginatedTranscriptionListResponse(
        transcriptions=transcription_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/cases/{case_gid}/transcriptions",
    response_model=TranscriptionUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload audio/video for transcription",
    description="Upload an audio or video file to a case for transcription processing with configurable options. "
    "Supported formats: MP3, WAV, AAC, M4A, FLAC, OGG, WebM (audio) and MP4, MPEG, MOV, AVI, WebM, MKV (video).",
)
async def upload_audio_for_transcription(
    case_gid: str = Path(..., description="GID of the case"),
    file: UploadFile = File(..., description="Audio or video file to transcribe"),
    options: Optional[str] = Form(None, description="JSON string of transcription options"),
    db: Session = Depends(get_db),
):
    """
    Upload audio/video file for transcription with configurable options.

    Args:
        case_gid: GID of the case to upload to
        file: Audio/video file to transcribe
        options: Optional JSON string containing TranscriptionOptions
        db: Database session

    Returns:
        TranscriptionUploadResponse: Upload confirmation with document ID
    """
    logger.info(f"Uploading audio/video for transcription to case {case_gid}: {file.filename}")

    # Parse transcription options if provided
    transcription_options = None
    if options:
        try:
            options_dict = json.loads(options)
            transcription_options = TranscriptionOptions(**options_dict)
            logger.info(f"Transcription options: {transcription_options}")
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Invalid transcription options, using defaults: {e}")
            transcription_options = TranscriptionOptions()
    else:
        transcription_options = TranscriptionOptions()

    transcription = await TranscriptionService.upload_audio_for_transcription(
        case_gid=case_gid,
        file=file,
        db=db,
        options=transcription_options,
    )

    logger.info(f"Created transcription record {transcription.id} for case {case_gid}")

    return TranscriptionUploadResponse(
        message=f"Audio/video file '{file.filename}' uploaded successfully. Transcription queued.",
        transcription_gid=transcription.gid,
        transcription_id=str(transcription.id),
        status="queued",
    )


@router.get(
    "/cases/{case_gid}/transcriptions",
    response_model=TranscriptionListResponse,
    summary="List transcriptions in a case",
    description="Get all transcriptions associated with a case.",
)
def list_case_transcriptions(
    case_gid: str = Path(..., description="GID of the case"),
    db: Session = Depends(get_db),
):
    """
    List all transcriptions for a case.

    Args:
        case_gid: GID of the case
        db: Database session

    Returns:
        TranscriptionListResponse: List of transcriptions and total count
    """
    logger.info(f"Listing transcriptions for case {case_gid}")

    transcriptions_data = TranscriptionService.list_case_transcriptions(
        case_gid=case_gid, db=db
    )

    # Convert to list items
    transcriptions = [
        TranscriptionListItem(**trans_data) for trans_data in transcriptions_data
    ]

    return TranscriptionListResponse(
        transcriptions=transcriptions,
        total=len(transcriptions),
        case_gid=case_gid,
    )


@router.get(
    "/transcriptions/{transcription_gid}",
    response_model=TranscriptionResponse,
    summary="Get transcription details",
    description="Get detailed information about a specific transcription including all segments, speakers, and timestamps.",
)
def get_transcription_details(
    transcription_gid: str = Path(..., description="GID of the transcription"),
    db: Session = Depends(get_db),
):
    """
    Get transcription details by GID.

    Args:
        transcription_gid: GID of the transcription
        db: Database session

    Returns:
        TranscriptionResponse: Detailed transcription data
    """
    logger.info(f"Getting transcription {transcription_gid}")

    transcription_data = TranscriptionService.get_transcription_details(
        transcription_gid=transcription_gid, db=db
    )

    return TranscriptionResponse(**transcription_data)


@router.post(
    "/transcriptions/{transcription_gid}/reprocess",
    response_model=TranscriptionReprocessResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Reprocess a transcription",
    description="Reset the transcription data and re-queue processing in the background.",
)
def reprocess_transcription_endpoint(
    transcription_gid: str = Path(..., description="GID of the transcription to reprocess"),
    options: Optional[dict] = Body(None, description="Optional transcription worker options"),
    db: Session = Depends(get_db),
):
    """
    Reprocess an existing transcription by resetting its state and re-queueing the worker.
    """
    logger.info("API request: reprocess transcription %s", transcription_gid)
    transcription = TranscriptionService.reprocess_transcription(
        transcription_gid=transcription_gid,
        db=db,
        options=options,
    )

    return TranscriptionReprocessResponse(
        message="Transcription reprocessing queued",
        transcription_gid=transcription.gid,
        status=transcription.status.value.lower() if transcription.status else "pending",
    )


@router.delete(
    "/transcriptions/{transcription_gid}",
    response_model=TranscriptionDeleteResponse,
    summary="Delete a transcription",
    description="Delete a transcription from the database. This action cannot be undone. The associated audio/video file will remain.",
)
def delete_transcription(
    transcription_gid: str = Path(..., description="GID of the transcription"),
    db: Session = Depends(get_db),
):
    """
    Delete a transcription.

    Args:
        transcription_gid: GID of the transcription
        db: Database session

    Returns:
        TranscriptionDeleteResponse: Deletion confirmation
    """
    logger.info(f"Deleting transcription {transcription_gid}")

    transcription = TranscriptionService.delete_transcription(
        transcription_gid=transcription_gid, db=db
    )

    return TranscriptionDeleteResponse(
        id=transcription.id,
        filename=transcription.filename or "Unknown",
        message=f"Transcription deleted successfully",
    )


@router.patch(
    "/transcriptions/{transcription_gid}/speakers/{speaker_id}",
    response_model=SpeakerResponse,
    summary="Update speaker information",
    description="Update speaker name and role. Changes are reflected across all segments using this speaker.",
)
def update_speaker(
    transcription_gid: str = Path(..., description="GID of the transcription"),
    speaker_id: str = Path(..., description="Speaker identifier (e.g., SPEAKER_00)"),
    request: UpdateSpeakerRequest = Body(...),
    db: Session = Depends(get_db),
):
    """
    Update speaker information (name and role).

    Args:
        transcription_gid: GID of the transcription
        speaker_id: Speaker identifier
        request: Update request with name and role
        db: Database session

    Returns:
        SpeakerResponse: Updated speaker information
    """
    logger.info(f"Updating speaker {speaker_id} in transcription {transcription_gid}")

    # Get transcription
    transcription = TranscriptionService.get_transcription(transcription_gid, db)

    # Find speaker in speakers list
    speaker_found = False
    for speaker in transcription.speakers:
        if speaker.get('id') == speaker_id:
            speaker['name'] = request.name
            if request.role is not None:
                speaker['role'] = request.role
            speaker_found = True
            break

    if not speaker_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Speaker {speaker_id} not found in transcription {transcription_gid}"
        )

    # Mark as modified and commit
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(transcription, "speakers")
    db.commit()
    db.refresh(transcription)

    logger.info(f"Successfully updated speaker {speaker_id}")

    # Return updated speaker
    updated_speaker = next(s for s in transcription.speakers if s.get('id') == speaker_id)
    return SpeakerResponse(
        speaker_id=updated_speaker.get('id'),
        name=updated_speaker.get('name'),
        role=updated_speaker.get('role'),
        color=updated_speaker.get('color')
    )
