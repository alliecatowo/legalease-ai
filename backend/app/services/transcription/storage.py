"""MinIO storage operations for transcription service."""

import io
from typing import Optional, Tuple
from datetime import datetime
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from minio.error import S3Error

from app.models.transcription import Transcription
from app.models.document import DocumentStatus
from app.models.case import Case
from app.core.minio_client import minio_client
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class TranscriptionStorageService:
    """MinIO storage operations for transcriptions."""

    # Supported audio/video formats
    SUPPORTED_FORMATS = {
        # Audio formats
        "audio/mpeg",
        "audio/mp3",
        "audio/mp4",  # M4A files (MPEG-4 audio)
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "audio/vnd.wave",  # Alternative MIME type for WAV files
        "audio/aac",
        "audio/m4a",
        "audio/x-m4a",
        "audio/flac",
        "audio/ogg",
        "audio/webm",
        # Video formats
        "video/mp4",
        "video/mpeg",
        "video/quicktime",
        "video/x-msvideo",
        "video/webm",
        "video/x-matroska",
    }

    @staticmethod
    async def upload_audio_for_transcription(
        case_gid: str,
        file: UploadFile,
        db: Session,
        options: Optional["TranscriptionOptions"] = None,
    ) -> Transcription:
        """
        Upload an audio/video file for transcription.

        Args:
            case_gid: GID of the case
            file: Uploaded audio/video file
            db: Database session
            options: Optional transcription configuration options

        Returns:
            Transcription: Created transcription record

        Raises:
            HTTPException: If validation fails or upload fails
        """
        # Validate case exists
        case = db.query(Case).filter(Case.gid == case_gid).first()
        if not case:
            logger.error(f"Case {case_gid} not found")
            raise HTTPException(status_code=404, detail=f"Case {case_gid} not found")

        # Validate file type
        if file.content_type not in TranscriptionStorageService.SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {file.content_type}. "
                f"Supported formats: audio (mp3, wav, aac, m4a, flac, ogg, webm) "
                f"and video (mp4, mpeg, mov, avi, webm, mkv)",
            )

        filename = file.filename or "unknown"

        # Read file content and get size
        file_content = await file.read()
        file_size = len(file_content)

        # Extract format from content type (e.g., "audio/mp3" -> "mp3")
        file_format = file.content_type.split("/")[-1] if file.content_type else None

        # Create Transcription record first to get GID
        transcription = Transcription(
            case_id=case.id,
            filename=filename,
            file_path="",  # Will be set after upload
            mime_type=file.content_type,
            size=file_size,
            status=DocumentStatus.PENDING,
            uploaded_at=datetime.utcnow(),
            format=file_format,
            segments=[],
            speakers=[],
        )

        db.add(transcription)
        db.flush()  # Get the transcription ID and GID

        # Create MinIO path: cases/{case_gid}/transcripts/{trans_gid}_{filename}
        object_name = f"cases/{case.gid}/transcripts/{transcription.gid}_{filename}"

        # Upload to MinIO
        try:
            minio_client.upload_file(
                file_data=io.BytesIO(file_content),
                object_name=object_name,
                content_type=file.content_type,
                length=file_size,
            )
            logger.info(f"Uploaded file to MinIO: {object_name}")
        except S3Error as e:
            logger.error(f"Failed to upload file to MinIO: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file to storage: {str(e)}",
            )

        # Update file path
        transcription.file_path = object_name
        db.commit()
        db.refresh(transcription)

        # Queue transcription task with options
        from app.workers.tasks.transcription import transcribe_audio

        options_dict = options.model_dump() if options else {}
        transcribe_audio.delay(transcription.gid, options=options_dict)

        logger.info(f"Created transcription {transcription.gid} and queued task with options: {options_dict}")

        return transcription

    @staticmethod
    def download_audio(transcription_gid: str, db: Session) -> Tuple[bytes, str, str]:
        """
        Download the original audio/video file from MinIO.

        WARNING: This loads the entire file into memory. Use get_media_info() and
        stream_media_range() for large files to support streaming and Range requests.

        Args:
            transcription_gid: GID of the transcription
            db: Database session

        Returns:
            tuple: (file_content, filename, content_type)

        Raises:
            HTTPException: If transcription not found or download fails
        """
        from app.services.transcription.core import TranscriptionCoreService

        # Get transcription from database
        transcription = TranscriptionCoreService.get_transcription(transcription_gid, db)

        try:
            # Download from MinIO
            logger.info(f"Downloading audio for transcription {transcription_gid} from MinIO: {transcription.file_path}")
            content = minio_client.download_file(transcription.file_path)

            return content, transcription.filename, transcription.mime_type or "application/octet-stream"

        except S3Error as e:
            logger.error(f"MinIO error downloading audio for transcription {transcription_gid}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download audio from storage: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Error downloading audio for transcription {transcription_gid}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download audio: {str(e)}",
            )

    @staticmethod
    def get_media_info(transcription_gid: str, db: Session) -> Tuple[str, int, str, str]:
        """
        Get media file information for streaming without downloading the file.

        This enables efficient Range request support by getting file metadata
        without loading the entire file into memory.

        Args:
            transcription_gid: GID of the transcription
            db: Database session

        Returns:
            tuple: (file_path, file_size, content_type, filename)

        Raises:
            HTTPException: If transcription not found or file info unavailable
        """
        from app.services.transcription.core import TranscriptionCoreService

        transcription = TranscriptionCoreService.get_transcription(transcription_gid, db)

        try:
            file_size = minio_client.get_object_size(transcription.file_path)
            logger.info(
                f"Retrieved media info for transcription {transcription_gid}: "
                f"{transcription.filename} ({file_size} bytes)"
            )

            return (
                transcription.file_path,
                file_size,
                transcription.mime_type or "application/octet-stream",
                transcription.filename,
            )

        except S3Error as e:
            logger.error(
                f"MinIO error getting media info for transcription {transcription_gid}: {str(e)}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get media information from storage: {str(e)}",
            )
        except Exception as e:
            logger.error(
                f"Error getting media info for transcription {transcription_gid}: {str(e)}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get media information: {str(e)}",
            )

    @staticmethod
    def stream_media_range(file_path: str, offset: int, length: int) -> bytes:
        """
        Stream a specific byte range from a media file without loading the entire file.

        This enables true HTTP Range request support for video/audio streaming,
        allowing instant playback start and efficient seeking.

        Args:
            file_path: MinIO object path
            offset: Starting byte position
            length: Number of bytes to read

        Returns:
            bytes: Requested byte range

        Raises:
            HTTPException: If range request fails
        """
        try:
            logger.debug(
                f"Streaming media range from {file_path}: offset={offset}, length={length}"
            )
            return minio_client.get_object_range(file_path, offset, length)

        except S3Error as e:
            logger.error(f"MinIO error streaming media range from {file_path}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to stream media range from storage: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Error streaming media range from {file_path}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to stream media range: {str(e)}",
            )
