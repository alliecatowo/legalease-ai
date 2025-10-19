"""AI-powered summarization endpoints for transcriptions."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Path, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.services.transcription import TranscriptionService
from app.workers.tasks.summarization import (
    summarize_transcript,
    regenerate_summary,
    batch_summarize_transcripts,
    quick_summary,
)
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/response models
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
