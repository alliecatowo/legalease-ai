"""Transcription API endpoints."""

import logging
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Path
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.core.database import get_db
from app.schemas.transcription import (
    TranscriptionResponse,
    TranscriptionListResponse,
    TranscriptionListItem,
    TranscriptionDeleteResponse,
    TranscriptionUploadResponse,
    TranscriptionFormat,
)
from app.services.transcription_service import TranscriptionService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/cases/{case_id}/transcriptions",
    response_model=TranscriptionUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload audio/video for transcription",
    description="Upload an audio or video file to a case for transcription processing. "
    "Supported formats: MP3, WAV, AAC, M4A, FLAC, OGG, WebM (audio) and MP4, MPEG, MOV, AVI, WebM, MKV (video).",
)
async def upload_audio_for_transcription(
    case_id: int = Path(..., description="ID of the case"),
    file: UploadFile = File(..., description="Audio or video file to transcribe"),
    db: Session = Depends(get_db),
):
    """
    Upload audio/video file for transcription.

    Args:
        case_id: ID of the case to upload to
        file: Audio/video file to transcribe
        db: Database session

    Returns:
        TranscriptionUploadResponse: Upload confirmation with document ID
    """
    logger.info(f"Uploading audio/video for transcription to case {case_id}: {file.filename}")

    document = await TranscriptionService.upload_audio_for_transcription(
        case_id=case_id,
        file=file,
        db=db,
    )

    return TranscriptionUploadResponse(
        message=f"Audio/video file '{file.filename}' uploaded successfully. Transcription processing has been queued.",
        document_id=document.id,
        transcription_id=None,  # Will be created by background processing
        status="processing",
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
