"""Audio/video streaming and waveform endpoints for transcriptions."""

import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Path, Header
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.transcription import TranscriptionService
from app.models.transcription import Transcription
from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/transcriptions/{transcription_gid}/audio",
    summary="Stream/download original audio file",
    description="Stream the original audio/video file from storage with true HTTP Range request support. "
    "Enables instant playback start and efficient seeking without loading entire file into memory. "
    "Memory-efficient even for multi-GB video files.",
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
    Stream audio/video file with HTTP Range support (RFC 7233).

    This endpoint implements true streaming by fetching only requested byte ranges
    from MinIO storage, enabling:
    - Instant playback start (no buffering entire file)
    - Efficient seeking in video/audio players
    - Memory-efficient handling of large files (2GB+)
    - Support for concurrent streams

    Args:
        transcription_gid: GID of the transcription
        range_header: Optional Range header (e.g., "bytes=0-1023")
        db: Database session

    Returns:
        Response: Full file (200) or partial content (206) with proper headers
    """
    logger.info(f"Streaming media for transcription {transcription_gid}, range: {range_header}")

    # Get file metadata WITHOUT downloading the file
    file_path, file_size, content_type, filename = TranscriptionService.get_media_info(
        transcription_gid=transcription_gid, db=db
    )

    # Parse Range header if present
    if range_header:
        # Parse range header format: "bytes=start-end"
        range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)

        if not range_match:
            # Invalid range format
            logger.warning(f"Invalid Range header format: {range_header}")
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
            logger.warning(
                f"Range not satisfiable: {start}-{end} for file size {file_size}"
            )
            return Response(
                content=f"Requested range not satisfiable (file size: {file_size} bytes)",
                status_code=416,
                headers={
                    "Content-Range": f"bytes */{file_size}",
                }
            )

        # Ensure end doesn't exceed file size
        end = min(end, file_size - 1)

        # Calculate length of range to fetch
        length = end - start + 1

        # Fetch ONLY the requested byte range from MinIO (no full file download)
        chunk = TranscriptionService.stream_media_range(
            file_path=file_path, offset=start, length=length
        )

        chunk_size = len(chunk)

        logger.info(
            f"Served range {start}-{end}/{file_size} ({chunk_size} bytes) "
            f"for {filename}"
        )

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
                "Cache-Control": "public, max-age=3600",
            }
        )

    # No range requested - stream full file from MinIO
    # For large files, avoid loading into memory by using iterator
    logger.info(f"Streaming full file ({file_size} bytes) for {filename}")

    # Create a generator that streams the file in chunks from MinIO
    def generate_chunks():
        """Stream file in 1MB chunks from MinIO without loading into memory."""
        chunk_size = 1024 * 1024  # 1MB chunks
        offset = 0

        while offset < file_size:
            length = min(chunk_size, file_size - offset)
            chunk = TranscriptionService.stream_media_range(
                file_path=file_path, offset=offset, length=length
            )
            yield chunk
            offset += length

    return StreamingResponse(
        generate_chunks(),
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600",
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
