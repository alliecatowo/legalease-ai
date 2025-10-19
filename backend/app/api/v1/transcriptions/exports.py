"""Export and download endpoints for transcriptions in various formats."""

import logging
import io
from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.transcription import TranscriptionFormat
from app.services.transcription import TranscriptionService

logger = logging.getLogger(__name__)

router = APIRouter()


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
