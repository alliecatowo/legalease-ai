"""Transcription API endpoints."""

import logging
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Path, Form, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import io

from app.core.database import get_db
from app.schemas.transcription import (
    TranscriptionResponse,
    TranscriptionListResponse,
    TranscriptionListItem,
    TranscriptionDeleteResponse,
    TranscriptionUploadResponse,
    TranscriptionFormat,
    TranscriptionOptions,
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

logger = logging.getLogger(__name__)

router = APIRouter()


# Summarization request/response models
class SummarizeRequest(BaseModel):
    """Request model for summarization."""
    components: Optional[List[str]] = None
    model: Optional[str] = None
    regenerate: bool = False


class BatchSummarizeRequest(BaseModel):
    """Request model for batch summarization."""
    transcription_ids: List[int]
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


@router.post(
    "/cases/{case_id}/transcriptions",
    response_model=TranscriptionUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload audio/video for transcription",
    description="Upload an audio or video file to a case for transcription processing with configurable options. "
    "Supported formats: MP3, WAV, AAC, M4A, FLAC, OGG, WebM (audio) and MP4, MPEG, MOV, AVI, WebM, MKV (video).",
)
async def upload_audio_for_transcription(
    case_id: int = Path(..., description="ID of the case"),
    file: UploadFile = File(..., description="Audio or video file to transcribe"),
    options: Optional[str] = Form(None, description="JSON string of transcription options"),
    db: Session = Depends(get_db),
):
    """
    Upload audio/video file for transcription with configurable options.

    Args:
        case_id: ID of the case to upload to
        file: Audio/video file to transcribe
        options: Optional JSON string containing TranscriptionOptions
        db: Database session

    Returns:
        TranscriptionUploadResponse: Upload confirmation with document ID
    """
    logger.info(f"Uploading audio/video for transcription to case {case_id}: {file.filename}")

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

    document = await TranscriptionService.upload_audio_for_transcription(
        case_id=case_id,
        file=file,
        db=db,
        options=transcription_options,
    )

    # Create transcription record immediately with empty data
    transcription = Transcription(
        document_id=document.id,
        format=file.content_type.split('/')[-1] if file.content_type else None,
        duration=None,  # Will be filled by worker
        speakers=[],
        segments=[]
    )
    db.add(transcription)
    db.commit()
    db.refresh(transcription)

    logger.info(f"Created transcription record {transcription.id} for document {document.id}")

    return TranscriptionUploadResponse(
        message=f"Audio/video file '{file.filename}' uploaded successfully. Transcription queued.",
        document_id=document.id,
        transcription_id=transcription.id,
        status="queued",
    )


@router.get(
    "/cases/{case_id}/transcriptions",
    response_model=TranscriptionListResponse,
    summary="List transcriptions in a case",
    description="Get all transcriptions associated with a case.",
)
def list_case_transcriptions(
    case_id: int = Path(..., description="ID of the case"),
    db: Session = Depends(get_db),
):
    """
    List all transcriptions for a case.

    Args:
        case_id: ID of the case
        db: Database session

    Returns:
        TranscriptionListResponse: List of transcriptions and total count
    """
    logger.info(f"Listing transcriptions for case {case_id}")

    transcriptions_data = TranscriptionService.list_case_transcriptions(
        case_id=case_id, db=db
    )

    # Convert to list items
    transcriptions = [
        TranscriptionListItem(**trans_data) for trans_data in transcriptions_data
    ]

    return TranscriptionListResponse(
        transcriptions=transcriptions,
        total=len(transcriptions),
        case_id=case_id,
    )


@router.get(
    "/transcriptions/{transcription_id}",
    response_model=TranscriptionResponse,
    summary="Get transcription details",
    description="Get detailed information about a specific transcription including all segments, speakers, and timestamps.",
)
def get_transcription_details(
    transcription_id: int = Path(..., description="ID of the transcription"),
    db: Session = Depends(get_db),
):
    """
    Get transcription details by ID.

    Args:
        transcription_id: ID of the transcription
        db: Database session

    Returns:
        TranscriptionResponse: Detailed transcription data
    """
    logger.info(f"Getting transcription {transcription_id}")

    transcription_data = TranscriptionService.get_transcription_details(
        transcription_id=transcription_id, db=db
    )

    return TranscriptionResponse(**transcription_data)


@router.get(
    "/transcriptions/{transcription_id}/download/{format}",
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
    transcription_id: int = Path(..., description="ID of the transcription"),
    format: TranscriptionFormat = Path(..., description="Export format (json, docx, srt, vtt, txt)"),
    db: Session = Depends(get_db),
):
    """
    Download transcription in specified format.

    Args:
        transcription_id: ID of the transcription
        format: Export format (json, docx, srt, vtt, txt)
        db: Database session

    Returns:
        StreamingResponse: File content in requested format
    """
    logger.info(f"Downloading transcription {transcription_id} as {format}")

    transcription = TranscriptionService.get_transcription(transcription_id, db)

    # Get document for filename
    from app.models.document import Document

    document = db.query(Document).filter(Document.id == transcription.document_id).first()
    base_filename = document.filename.rsplit(".", 1)[0] if document else "transcription"

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
    "/transcriptions/{transcription_id}",
    response_model=TranscriptionDeleteResponse,
    summary="Delete a transcription",
    description="Delete a transcription from the database. This action cannot be undone. The associated audio/video file will remain.",
)
def delete_transcription(
    transcription_id: int = Path(..., description="ID of the transcription"),
    db: Session = Depends(get_db),
):
    """
    Delete a transcription.

    Args:
        transcription_id: ID of the transcription
        db: Database session

    Returns:
        TranscriptionDeleteResponse: Deletion confirmation
    """
    logger.info(f"Deleting transcription {transcription_id}")

    transcription = TranscriptionService.delete_transcription(
        transcription_id=transcription_id, db=db
    )

    # Get document info for response
    from app.models.document import Document

    document = db.query(Document).filter(Document.id == transcription.document_id).first()

    return TranscriptionDeleteResponse(
        id=transcription.id,
        document_id=transcription.document_id,
        filename=document.filename if document else "Unknown",
        message=f"Transcription deleted successfully",
    )


# ===== Summarization Endpoints =====


@router.post(
    "/transcriptions/{transcription_id}/summarize",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate transcript summary",
    description="Generate comprehensive AI-powered summary and analysis for a transcript using local Ollama LLM. "
    "Includes executive summary, key moments, timeline, speaker statistics, action items, and entity extraction.",
)
def start_summarization(
    transcription_id: int = Path(..., description="ID of the transcription"),
    request: SummarizeRequest = Body(default=SummarizeRequest()),
    db: Session = Depends(get_db),
):
    """
    Start summarization task for a transcription.

    Args:
        transcription_id: ID of the transcription
        request: Summarization options
        db: Database session

    Returns:
        Task ID and status
    """
    logger.info(f"Starting summarization for transcription {transcription_id}")

    # Verify transcription exists
    transcription = TranscriptionService.get_transcription(transcription_id, db)

    # Queue summarization task
    task = summarize_transcript.delay(
        transcription_id,
        options={
            'components': request.components,
            'model': request.model,
            'regenerate': request.regenerate,
        }
    )

    return {
        "message": "Summarization task started",
        "transcription_id": transcription_id,
        "task_id": task.id,
        "status": "processing",
        "status_url": f"/api/v1/transcriptions/{transcription_id}/summary/status/{task.id}",
    }


@router.get(
    "/transcriptions/{transcription_id}/summary",
    response_model=SummaryResponse,
    summary="Get transcript summary",
    description="Retrieve the AI-generated summary and analysis for a transcript. Returns all analysis components if available.",
)
def get_summary(
    transcription_id: int = Path(..., description="ID of the transcription"),
    db: Session = Depends(get_db),
):
    """
    Get summary for a transcription.

    Args:
        transcription_id: ID of the transcription
        db: Database session

    Returns:
        SummaryResponse: Summary data
    """
    logger.info(f"Getting summary for transcription {transcription_id}")

    transcription = TranscriptionService.get_transcription(transcription_id, db)

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
    "/transcriptions/{transcription_id}/summary/regenerate",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Regenerate transcript summary",
    description="Force regeneration of the transcript summary, optionally regenerating only specific components.",
)
def regenerate_transcript_summary(
    transcription_id: int = Path(..., description="ID of the transcription"),
    components: Optional[List[str]] = Body(None, description="Specific components to regenerate"),
    db: Session = Depends(get_db),
):
    """
    Regenerate summary for a transcription.

    Args:
        transcription_id: ID of the transcription
        components: Optional list of components to regenerate
        db: Database session

    Returns:
        Task ID and status
    """
    logger.info(f"Regenerating summary for transcription {transcription_id}")

    # Verify transcription exists
    transcription = TranscriptionService.get_transcription(transcription_id, db)

    # Queue regeneration task
    task = regenerate_summary.delay(transcription_id, components)

    return {
        "message": "Summary regeneration task started",
        "transcription_id": transcription_id,
        "task_id": task.id,
        "status": "processing",
        "components": components or "all",
        "status_url": f"/api/v1/transcriptions/{transcription_id}/summary/status/{task.id}",
    }


@router.get(
    "/transcriptions/{transcription_id}/summary/status/{task_id}",
    response_model=TaskStatusResponse,
    summary="Get summarization task status",
    description="Check the status of a running summarization task.",
)
def get_summarization_status(
    transcription_id: int = Path(..., description="ID of the transcription"),
    task_id: str = Path(..., description="ID of the Celery task"),
):
    """
    Get status of a summarization task.

    Args:
        transcription_id: ID of the transcription
        task_id: ID of the Celery task

    Returns:
        TaskStatusResponse: Task status and progress
    """
    logger.info(f"Checking status for task {task_id} (transcription {transcription_id})")

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
    "/transcriptions/{transcription_id}/summary/quick",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate quick summary",
    description="Generate just the executive summary (fast, no full analysis). Useful for quick overviews.",
)
def start_quick_summary(
    transcription_id: int = Path(..., description="ID of the transcription"),
    db: Session = Depends(get_db),
):
    """
    Start quick summary task (executive summary only).

    Args:
        transcription_id: ID of the transcription
        db: Database session

    Returns:
        Task ID and status
    """
    logger.info(f"Starting quick summary for transcription {transcription_id}")

    # Verify transcription exists
    transcription = TranscriptionService.get_transcription(transcription_id, db)

    # Queue quick summary task
    task = quick_summary.delay(transcription_id)

    return {
        "message": "Quick summary task started",
        "transcription_id": transcription_id,
        "task_id": task.id,
        "status": "processing",
        "status_url": f"/api/v1/transcriptions/{transcription_id}/summary/status/{task.id}",
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
    logger.info(f"Starting batch summarization for {len(request.transcription_ids)} transcriptions")

    # Verify all transcriptions exist
    for transcription_id in request.transcription_ids:
        TranscriptionService.get_transcription(transcription_id, db)

    # Queue batch summarization task
    task = batch_summarize_transcripts.delay(request.transcription_ids, request.options)

    return {
        "message": f"Batch summarization task started for {len(request.transcription_ids)} transcriptions",
        "transcription_ids": request.transcription_ids,
        "task_id": task.id,
        "status": "processing",
    }


# ===== Key Moments Endpoints =====


@router.patch(
    "/transcriptions/{transcription_id}/segments/{segment_id}/key-moment",
    response_model=KeyMomentToggleResponse,
    summary="Toggle key moment status",
    description="Mark or unmark a transcript segment as a key moment. "
    "Key moments are important segments that users want to highlight for quick reference.",
)
def toggle_key_moment(
    transcription_id: int = Path(..., description="ID of the transcription"),
    segment_id: str = Path(..., description="UUID of the segment"),
    request: KeyMomentToggleRequest = Body(...),
    db: Session = Depends(get_db),
):
    """
    Toggle key moment status for a transcript segment.

    Args:
        transcription_id: ID of the transcription
        segment_id: UUID of the segment
        request: Toggle request with is_key_moment status
        db: Database session

    Returns:
        KeyMomentToggleResponse: Updated segment metadata
    """
    logger.info(
        f"Toggling key moment for segment {segment_id} in transcription {transcription_id}: {request.is_key_moment}"
    )

    result = TranscriptionService.toggle_key_moment(
        transcription_id=transcription_id,
        segment_id=segment_id,
        is_key_moment=request.is_key_moment,
        db=db,
    )

    return KeyMomentToggleResponse(**result)


@router.get(
    "/transcriptions/{transcription_id}/key-moments",
    response_model=KeyMomentsResponse,
    summary="Get all key moments",
    description="Retrieve all segments marked as key moments for a transcription, "
    "including full segment data (text, speaker, timing, confidence).",
)
def get_key_moments(
    transcription_id: int = Path(..., description="ID of the transcription"),
    db: Session = Depends(get_db),
):
    """
    Get all key moments for a transcription.

    Args:
        transcription_id: ID of the transcription
        db: Database session

    Returns:
        KeyMomentsResponse: List of key moments with full segment data
    """
    logger.info(f"Getting key moments for transcription {transcription_id}")

    result = TranscriptionService.get_key_moments(
        transcription_id=transcription_id, db=db
    )

    return KeyMomentsResponse(**result)
