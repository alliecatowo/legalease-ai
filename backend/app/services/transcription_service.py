"""Transcription service for managing audio/video transcription operations."""

import io
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from minio.error import S3Error
from docx import Document as DocxDocument
from docx.shared import Pt, Inches

from app.models.transcription import Transcription
from app.models.document import Document, DocumentStatus
from app.models.case import Case
from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Service class for transcription operations."""

    # Supported audio/video formats
    SUPPORTED_FORMATS = {
        # Audio formats
        "audio/mpeg",
        "audio/mp3",
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
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
        case_id: int,
        file: UploadFile,
        db: Session,
        options: Optional["TranscriptionOptions"] = None,
    ) -> Document:
        """
        Upload an audio/video file for transcription.

        Args:
            case_id: ID of the case
            file: Uploaded audio/video file
            db: Database session
            options: Optional transcription configuration options

        Returns:
            Document: Created document record

        Raises:
            HTTPException: If validation fails or upload fails
        """
        # Validate file type
        if file.content_type not in TranscriptionService.SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {file.content_type}. "
                f"Supported formats: audio (mp3, wav, aac, m4a, flac, ogg, webm) "
                f"and video (mp4, mpeg, mov, avi, webm, mkv)",
            )

        # Upload using document service
        documents = await DocumentService.upload_documents(
            case_id=case_id,
            files=[file],
            db=db,
        )

        document = documents[0]

        # Queue transcription task with options
        from app.workers.tasks.transcription import transcribe_audio

        options_dict = options.model_dump() if options else {}
        transcribe_audio.delay(document.id, options=options_dict)

        logger.info(f"Queued transcription task for document {document.id} with options: {options_dict}")

        # Return the first (and only) document
        return document

    @staticmethod
    def get_transcription(transcription_id: int, db: Session) -> Transcription:
        """
        Get a transcription by ID.

        Args:
            transcription_id: ID of the transcription
            db: Database session

        Returns:
            Transcription: Transcription record

        Raises:
            HTTPException: If transcription not found
        """
        transcription = (
            db.query(Transcription)
            .filter(Transcription.id == transcription_id)
            .first()
        )
        if not transcription:
            logger.error(f"Transcription {transcription_id} not found")
            raise HTTPException(
                status_code=404, detail=f"Transcription {transcription_id} not found"
            )

        return transcription

    @staticmethod
    def list_case_transcriptions(case_id: int, db: Session) -> List[Dict[str, Any]]:
        """
        List all transcriptions for a case.

        Args:
            case_id: ID of the case
            db: Database session

        Returns:
            List[Dict]: List of transcription summaries

        Raises:
            HTTPException: If case not found
        """
        # Validate case exists
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            logger.error(f"Case {case_id} not found")
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

        # Get all transcriptions for the case through documents
        transcriptions = (
            db.query(Transcription)
            .join(Document, Transcription.document_id == Document.id)
            .filter(Document.case_id == case_id)
            .all()
        )

        logger.info(f"Found {len(transcriptions)} transcriptions for case {case_id}")

        # Build summary list
        result = []
        for trans in transcriptions:
            doc = db.query(Document).filter(Document.id == trans.document_id).first()
            result.append(
                {
                    "id": trans.id,
                    "document_id": trans.document_id,
                    "case_id": doc.case_id if doc else None,
                    "filename": doc.filename if doc else "Unknown",
                    "format": trans.format,
                    "duration": trans.duration,
                    "segment_count": len(trans.segments) if trans.segments else 0,
                    "speaker_count": len(trans.speakers) if trans.speakers else 0,
                    "created_at": trans.created_at,
                }
            )

        return result

    @staticmethod
    def get_transcription_details(transcription_id: int, db: Session) -> Dict[str, Any]:
        """
        Get detailed transcription information.

        Args:
            transcription_id: ID of the transcription
            db: Database session

        Returns:
            Dict: Detailed transcription data

        Raises:
            HTTPException: If transcription not found
        """
        transcription = TranscriptionService.get_transcription(transcription_id, db)
        document = (
            db.query(Document)
            .filter(Document.id == transcription.document_id)
            .first()
        )

        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"Document {transcription.document_id} not found",
            )

        return {
            "id": transcription.id,
            "document_id": transcription.document_id,
            "case_id": document.case_id,
            "filename": document.filename,
            "format": transcription.format,
            "duration": transcription.duration,
            "speakers": transcription.speakers,
            "segments": transcription.segments,
            "created_at": transcription.created_at,
        }

    @staticmethod
    def export_as_json(transcription: Transcription, db: Session) -> bytes:
        """Export transcription as JSON."""
        document = (
            db.query(Document)
            .filter(Document.id == transcription.document_id)
            .first()
        )

        data = {
            "transcription_id": transcription.id,
            "document_id": transcription.document_id,
            "filename": document.filename if document else "Unknown",
            "format": transcription.format,
            "duration": transcription.duration,
            "speakers": transcription.speakers,
            "segments": transcription.segments,
            "created_at": transcription.created_at.isoformat(),
        }

        return json.dumps(data, indent=2).encode("utf-8")

    @staticmethod
    def export_as_docx(transcription: Transcription, db: Session) -> bytes:
        """Export transcription as DOCX with formatting."""
        document_db = (
            db.query(Document)
            .filter(Document.id == transcription.document_id)
            .first()
        )

        doc = DocxDocument()

        # Add title
        title = doc.add_heading(
            f"Transcription: {document_db.filename if document_db else 'Unknown'}", 0
        )

        # Add metadata
        doc.add_paragraph(f"Document ID: {transcription.document_id}")
        doc.add_paragraph(f"Format: {transcription.format or 'Unknown'}")
        if transcription.duration:
            minutes = int(transcription.duration // 60)
            seconds = int(transcription.duration % 60)
            doc.add_paragraph(f"Duration: {minutes}m {seconds}s")
        doc.add_paragraph(f"Created: {transcription.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        doc.add_paragraph()

        # Add speakers section if available
        if transcription.speakers:
            doc.add_heading("Speakers", level=1)
            for speaker in transcription.speakers:
                speaker_text = f"• {speaker.get('speaker_id', 'Unknown')}"
                if speaker.get("label"):
                    speaker_text += f" - {speaker['label']}"
                doc.add_paragraph(speaker_text)
            doc.add_paragraph()

        # Add transcription content
        doc.add_heading("Transcription", level=1)

        segments = transcription.segments or []
        for segment in segments:
            # Format timestamp
            start_time = TranscriptionService._format_timestamp(segment.get("start", 0))
            end_time = TranscriptionService._format_timestamp(segment.get("end", 0))
            timestamp = f"[{start_time} - {end_time}]"

            # Create paragraph with speaker and timestamp
            p = doc.add_paragraph()
            if segment.get("speaker"):
                p.add_run(f"{segment['speaker']}: ").bold = True
            p.add_run(f"{timestamp} ")
            p.add_run(segment.get("text", ""))
            p.add_run("\n")

        # Save to bytes
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.read()

    @staticmethod
    def export_as_srt(transcription: Transcription) -> bytes:
        """Export transcription as SRT subtitle format."""
        srt_content = []
        segments = transcription.segments or []

        for idx, segment in enumerate(segments, 1):
            start = TranscriptionService._format_srt_timestamp(segment.get("start", 0))
            end = TranscriptionService._format_srt_timestamp(segment.get("end", 0))
            text = segment.get("text", "")

            # Add speaker label if available
            if segment.get("speaker"):
                text = f"[{segment['speaker']}] {text}"

            srt_content.append(f"{idx}")
            srt_content.append(f"{start} --> {end}")
            srt_content.append(text)
            srt_content.append("")  # Empty line between subtitles

        return "\n".join(srt_content).encode("utf-8")

    @staticmethod
    def export_as_vtt(transcription: Transcription) -> bytes:
        """Export transcription as VTT subtitle format."""
        vtt_content = ["WEBVTT", ""]
        segments = transcription.segments or []

        for segment in segments:
            start = TranscriptionService._format_vtt_timestamp(segment.get("start", 0))
            end = TranscriptionService._format_vtt_timestamp(segment.get("end", 0))
            text = segment.get("text", "")

            # Add speaker label if available
            if segment.get("speaker"):
                text = f"<v {segment['speaker']}>{text}"

            vtt_content.append(f"{start} --> {end}")
            vtt_content.append(text)
            vtt_content.append("")  # Empty line between subtitles

        return "\n".join(vtt_content).encode("utf-8")

    @staticmethod
    def export_as_txt(transcription: Transcription) -> bytes:
        """Export transcription as plain text."""
        txt_content = []
        segments = transcription.segments or []

        for segment in segments:
            start_time = TranscriptionService._format_timestamp(segment.get("start", 0))
            text = segment.get("text", "")

            # Add speaker and timestamp
            line = f"[{start_time}]"
            if segment.get("speaker"):
                line += f" {segment['speaker']}:"
            line += f" {text}"

            txt_content.append(line)

        return "\n".join(txt_content).encode("utf-8")

    @staticmethod
    def delete_transcription(transcription_id: int, db: Session) -> Transcription:
        """
        Delete a transcription.

        Args:
            transcription_id: ID of the transcription
            db: Database session

        Returns:
            Transcription: Deleted transcription record

        Raises:
            HTTPException: If transcription not found or deletion fails
        """
        transcription = TranscriptionService.get_transcription(transcription_id, db)

        try:
            # Delete from database (cascade will handle related records)
            db.delete(transcription)
            db.commit()

            logger.info(f"Successfully deleted transcription {transcription_id}")
            return transcription

        except Exception as e:
            logger.error(f"Error deleting transcription {transcription_id}: {str(e)}")
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete transcription: {str(e)}",
            )

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Format seconds as HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @staticmethod
    def _format_srt_timestamp(seconds: float) -> str:
        """Format seconds as SRT timestamp (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def _format_vtt_timestamp(seconds: float) -> str:
        """Format seconds as VTT timestamp (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
