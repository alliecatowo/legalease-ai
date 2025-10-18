"""Transcription API endpoints."""

import logging
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Path, Form, Body, Query, Header, Request
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import io
import re

from app.core.database import get_db
from app.schemas.transcription import (
    TranscriptionResponse,
    TranscriptionListResponse,
    TranscriptionListItem,
    TranscriptionDeleteResponse,
    TranscriptionUploadResponse,
    TranscriptionFormat,
    TranscriptionOptions,
    UpdateSpeakerRequest,
    SpeakerResponse,
)
from app.services.transcription_service import TranscriptionService
from app.workers.tasks.summarization import (
    summarize_transcript,
    regenerate_summary,
    batch_summarize_transcripts,
    quick_summary,
)
from app.workers.celery_app import celery_app
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


# Summarization request/response models
class SummarizeRequest(BaseModel):
    """Request model for summarization."""
    components: Optional[List[str]] = None
    model: Optional[str] = None
    regenerate: bool = False


class BatchSummarizeRequest(BaseModel):
    """Request model for batch summarization."""
    transcription_gids: List[str]
    options: Optional[dict] = None


class SummaryResponse(BaseModel):
    """Response model for summary retrieval."""
    transcription_id: int
    executive_summary: Optional[str]
    key_moments: Optional[List[dict]]
    timeline: Optional[List[dict]]
    speaker_stats: Optional[dict]
    action_items: Optional[List[dict]]
    topics: Optional[List[str]]
    entities: Optional[dict]
    summary_generated_at: Optional[str]


class TaskStatusResponse(BaseModel):
    """Response model for task status."""
    task_id: str
    status: str
    progress: Optional[int] = None
    message: Optional[str] = None
    result: Optional[dict] = None


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
        transcription_id=transcription.id,
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


@router.get(
    "/transcriptions/{transcription_gid}/audio",
    summary="Stream/download original audio file",
    description="Download the original audio/video file from storage. Supports HTTP Range requests for efficient seeking in media players.",
    responses={
        200: {
            "description": "Full audio/video file",
            "content": {
                "audio/mpeg": {},
                "audio/wav": {},
                "audio/mp4": {},
                "video/mp4": {},
                "application/octet-stream": {},
            },
        },
        206: {
            "description": "Partial audio/video content (range request)",
            "content": {
                "audio/mpeg": {},
                "audio/wav": {},
                "audio/mp4": {},
                "video/mp4": {},
                "application/octet-stream": {},
            },
        },
        416: {
            "description": "Range not satisfiable",
        }
    },
)
def download_audio(
    transcription_gid: str = Path(..., description="GID of the transcription"),
    range_header: Optional[str] = Header(None, alias="Range"),
    db: Session = Depends(get_db),
):
    """
    Download or stream the original audio/video file with HTTP Range support.

    This endpoint supports HTTP Range requests (RFC 7233) for efficient audio/video
    streaming and seeking. Media players can request specific byte ranges without
    downloading the entire file.

    Args:
        transcription_gid: GID of the transcription
        range_header: Optional Range header (e.g., "bytes=0-1023")
        db: Database session

    Returns:
        Response: Full file (200) or partial content (206) with proper headers
    """
    logger.info(f"Streaming audio for transcription {transcription_gid}, range: {range_header}")

    # Get file content and metadata
    content, filename, content_type = TranscriptionService.download_audio(
        transcription_gid=transcription_gid, db=db
    )

    file_size = len(content)

    # Parse Range header if present
    if range_header:
        # Parse range header format: "bytes=start-end"
        range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)

        if not range_match:
            # Invalid range format
            return Response(
                content="Invalid Range header format",
                status_code=416,
                headers={
                    "Content-Range": f"bytes */{file_size}",
                }
            )

        start = int(range_match.group(1))
        end = int(range_match.group(2)) if range_match.group(2) else file_size - 1

        # Validate range
        if start >= file_size or start > end:
            # Range not satisfiable
            return Response(
                content=f"Requested range not satisfiable (file size: {file_size} bytes)",
                status_code=416,
                headers={
                    "Content-Range": f"bytes */{file_size}",
                }
            )

        # Ensure end doesn't exceed file size
        end = min(end, file_size - 1)

        # Extract the requested byte range
        chunk = content[start:end + 1]
        chunk_size = len(chunk)

        logger.info(f"Serving range {start}-{end}/{file_size} ({chunk_size} bytes)")

        # Return 206 Partial Content
        return Response(
            content=chunk,
            status_code=206,
            media_type=content_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(chunk_size),
                "Accept-Ranges": "bytes",
                "Content-Disposition": f'inline; filename="{filename}"',
            }
        )

    # No range requested - return full file with 200 OK
    logger.info(f"Serving full file ({file_size} bytes)")

    return StreamingResponse(
        io.BytesIO(content),
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
        },
    )


@router.get(
    "/transcriptions/{transcription_gid}/waveform",
    summary="Get pre-computed waveform data",
    description="Get pre-computed waveform visualization data for instant rendering. "
    "Returns normalized peak values that can be directly used by WaveSurfer or other waveform visualizers. "
    "Falls back to 404 if waveform data is not available (e.g., for old transcriptions).",
    responses={
        200: {
            "description": "Waveform data with peaks array",
            "content": {
                "application/json": {
                    "example": {
                        "peaks": [0.5, 0.8, 0.3, 0.6],
                        "duration": 120.5,
                        "sample_rate": 16000
                    }
                }
            },
        },
        404: {
            "description": "Waveform data not available"
        }
    },
)
def get_waveform_data(
    transcription_gid: str = Path(..., description="GID of the transcription"),
    db: Session = Depends(get_db),
):
    """
    Get pre-computed waveform data for instant visualization.

    Args:
        transcription_gid: GID of the transcription
        db: Database session

    Returns:
        Dict containing waveform peaks, duration, and sample_rate

    Raises:
        HTTPException: 404 if transcription not found or waveform data not available
    """
    logger.info(f"Getting waveform data for transcription {transcription_gid}")

    # Get transcription
    transcription = db.query(Transcription).filter(Transcription.gid == transcription_gid).first()

    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcription {transcription_gid} not found"
        )

    # Check if waveform data is available
    if not transcription.waveform_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waveform data not available for this transcription. "
            "This may be an older transcription created before waveform pre-computation was implemented."
        )

    return transcription.waveform_data


@router.get(
    "/transcriptions/{transcription_gid}/download/{format}",
    summary="Download transcription in specified format",
    description="Download transcription in JSON, DOCX, SRT, VTT, or TXT format. "
    "JSON includes all metadata, DOCX is formatted for documents, SRT/VTT are subtitle formats, and TXT is plain text.",
    responses={
        200: {
            "description": "Transcription file in requested format",
            "content": {
                "application/json": {},
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {},
                "text/plain": {},
            },
        }
    },
)
def download_transcription(
    transcription_gid: str = Path(..., description="GID of the transcription"),
    format: TranscriptionFormat = Path(..., description="Export format (json, docx, srt, vtt, txt)"),
    db: Session = Depends(get_db),
):
    """
    Download transcription in specified format.

    Args:
        transcription_gid: GID of the transcription
        format: Export format (json, docx, srt, vtt, txt)
        db: Database session

    Returns:
        StreamingResponse: File content in requested format
    """
    logger.info(f"Downloading transcription {transcription_gid} as {format}")

    transcription = TranscriptionService.get_transcription(transcription_gid, db)

    # Use transcription filename directly (no document needed)
    base_filename = transcription.filename.rsplit(".", 1)[0] if transcription.filename else "transcription"

    # Export in requested format
    if format == TranscriptionFormat.JSON:
        content = TranscriptionService.export_as_json(transcription, db)
        media_type = "application/json"
        filename = f"{base_filename}_transcription.json"

    elif format == TranscriptionFormat.DOCX:
        content = TranscriptionService.export_as_docx(transcription, db)
        media_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        filename = f"{base_filename}_transcription.docx"

    elif format == TranscriptionFormat.SRT:
        content = TranscriptionService.export_as_srt(transcription)
        media_type = "text/plain"
        filename = f"{base_filename}_transcription.srt"

    elif format == TranscriptionFormat.VTT:
        content = TranscriptionService.export_as_vtt(transcription)
        media_type = "text/plain"
        filename = f"{base_filename}_transcription.vtt"

    elif format == TranscriptionFormat.TXT:
        content = TranscriptionService.export_as_txt(transcription)
        media_type = "text/plain"
        filename = f"{base_filename}_transcription.txt"

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {format}. Supported formats: json, docx, srt, vtt, txt",
        )

    # Return as streaming response with proper headers
    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
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


# ===== Summarization Endpoints =====


@router.post(
    "/transcriptions/{transcription_gid}/summarize",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate transcript summary",
    description="Generate comprehensive AI-powered summary and analysis for a transcript using local Ollama LLM. "
    "Includes executive summary, key moments, timeline, speaker statistics, action items, and entity extraction.",
)
def start_summarization(
    transcription_gid: str = Path(..., description="GID of the transcription"),
    request: SummarizeRequest = Body(default=SummarizeRequest()),
    db: Session = Depends(get_db),
):
    """
    Start summarization task for a transcription.

    Args:
        transcription_gid: GID of the transcription
        request: Summarization options
        db: Database session

    Returns:
        Task ID and status
    """
    logger.info(f"Starting summarization for transcription {transcription_gid}")

    # Verify transcription exists
    transcription = TranscriptionService.get_transcription(transcription_gid, db)

    # Queue summarization task
    task = summarize_transcript.delay(
        transcription_gid,
        options={
            'components': request.components,
            'model': request.model,
            'regenerate': request.regenerate,
        }
    )

    return {
        "message": "Summarization task started",
        "transcription_gid": transcription_gid,
        "task_id": task.id,
        "status": "processing",
        "status_url": f"/api/v1/transcriptions/{transcription_gid}/summary/status/{task.id}",
    }


@router.get(
    "/transcriptions/{transcription_gid}/summary",
    response_model=SummaryResponse,
    summary="Get transcript summary",
    description="Retrieve the AI-generated summary and analysis for a transcript. Returns all analysis components if available.",
)
def get_summary(
    transcription_gid: str = Path(..., description="GID of the transcription"),
    db: Session = Depends(get_db),
):
    """
    Get summary for a transcription.

    Args:
        transcription_gid: GID of the transcription
        db: Database session

    Returns:
        SummaryResponse: Summary data
    """
    logger.info(f"Getting summary for transcription {transcription_gid}")

    transcription = TranscriptionService.get_transcription(transcription_gid, db)

    return SummaryResponse(
        transcription_id=transcription.id,
        executive_summary=transcription.executive_summary,
        key_moments=transcription.key_moments,
        timeline=transcription.timeline,
        speaker_stats=transcription.speaker_stats,
        action_items=transcription.action_items,
        topics=transcription.topics,
        entities=transcription.entities,
        summary_generated_at=transcription.summary_generated_at.isoformat() if transcription.summary_generated_at else None,
    )


@router.post(
    "/transcriptions/{transcription_gid}/summary/regenerate",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Regenerate transcript summary",
    description="Force regeneration of the transcript summary, optionally regenerating only specific components.",
)
def regenerate_transcript_summary(
    transcription_gid: str = Path(..., description="GID of the transcription"),
    components: Optional[List[str]] = Body(None, description="Specific components to regenerate"),
    db: Session = Depends(get_db),
):
    """
    Regenerate summary for a transcription.

    Args:
        transcription_gid: GID of the transcription
        components: Optional list of components to regenerate
        db: Database session

    Returns:
        Task ID and status
    """
    logger.info(f"Regenerating summary for transcription {transcription_gid}")

    # Verify transcription exists
    transcription = TranscriptionService.get_transcription(transcription_gid, db)

    # Queue regeneration task
    task = regenerate_summary.delay(transcription_gid, components)

    return {
        "message": "Summary regeneration task started",
        "transcription_gid": transcription_gid,
        "task_id": task.id,
        "status": "processing",
        "components": components or "all",
        "status_url": f"/api/v1/transcriptions/{transcription_gid}/summary/status/{task.id}",
    }


@router.get(
    "/transcriptions/{transcription_gid}/summary/status/{task_id}",
    response_model=TaskStatusResponse,
    summary="Get summarization task status",
    description="Check the status of a running summarization task.",
)
def get_summarization_status(
    transcription_gid: str = Path(..., description="GID of the transcription"),
    task_id: str = Path(..., description="ID of the Celery task"),
):
    """
    Get status of a summarization task.

    Args:
        transcription_gid: GID of the transcription
        task_id: ID of the Celery task

    Returns:
        TaskStatusResponse: Task status and progress
    """
    logger.info(f"Checking status for task {task_id} (transcription {transcription_gid})")

    # Get task result from Celery
    task = celery_app.AsyncResult(task_id)

    response = TaskStatusResponse(
        task_id=task_id,
        status=task.state.lower(),
    )

    # Add progress info if available
    if task.state == 'PENDING':
        response.message = "Task is waiting to start"
    elif task.state == 'STARTED':
        response.message = "Task is running"
        if task.info:
            response.progress = task.info.get('progress', 0)
            response.message = task.info.get('status', 'Processing')
    elif task.state == 'PROCESSING':
        if task.info:
            response.progress = task.info.get('progress', 0)
            response.message = task.info.get('status', 'Processing')
    elif task.state == 'SUCCESS':
        response.message = "Summarization completed successfully"
        response.progress = 100
        response.result = task.result
    elif task.state == 'FAILURE':
        response.message = "Summarization failed"
        response.result = {'error': str(task.info)}

    return response


@router.post(
    "/transcriptions/{transcription_gid}/summary/quick",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate quick summary",
    description="Generate just the executive summary (fast, no full analysis). Useful for quick overviews.",
)
def start_quick_summary(
    transcription_gid: str = Path(..., description="GID of the transcription"),
    db: Session = Depends(get_db),
):
    """
    Start quick summary task (executive summary only).

    Args:
        transcription_gid: GID of the transcription
        db: Database session

    Returns:
        Task ID and status
    """
    logger.info(f"Starting quick summary for transcription {transcription_gid}")

    # Verify transcription exists
    transcription = TranscriptionService.get_transcription(transcription_gid, db)

    # Queue quick summary task
    task = quick_summary.delay(transcription_gid)

    return {
        "message": "Quick summary task started",
        "transcription_gid": transcription_gid,
        "task_id": task.id,
        "status": "processing",
        "status_url": f"/api/v1/transcriptions/{transcription_gid}/summary/status/{task.id}",
    }


@router.post(
    "/transcriptions/batch/summarize",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Batch summarize transcriptions",
    description="Generate summaries for multiple transcriptions in one request.",
)
def start_batch_summarization(
    request: BatchSummarizeRequest = Body(...),
    db: Session = Depends(get_db),
):
    """
    Start batch summarization for multiple transcriptions.

    Args:
        request: Batch summarization request
        db: Database session

    Returns:
        Task ID and status
    """
    logger.info(f"Starting batch summarization for {len(request.transcription_gids)} transcriptions")

    # Verify all transcriptions exist
    for transcription_gid in request.transcription_gids:
        TranscriptionService.get_transcription(transcription_gid, db)

    # Queue batch summarization task
    task = batch_summarize_transcripts.delay(request.transcription_gids, request.options)

    return {
        "message": f"Batch summarization task started for {len(request.transcription_gids)} transcriptions",
        "transcription_gids": request.transcription_gids,
        "task_id": task.id,
        "status": "processing",
    }


# ===== Key Moments Endpoints =====


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


# ===== Speaker Management Endpoints =====


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
