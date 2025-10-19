"""Core CRUD operations for transcription service."""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.transcription import Transcription, TranscriptSegment
from app.models.case import Case

logger = logging.getLogger(__name__)


class TranscriptionCoreService:
    """Core CRUD operations for transcriptions."""

    @staticmethod
    def get_transcription(transcription_gid: str, db: Session) -> Transcription:
        """
        Get a transcription by GID.

        Args:
            transcription_gid: GID of the transcription
            db: Database session

        Returns:
            Transcription: Transcription record

        Raises:
            HTTPException: If transcription not found
        """
        transcription = (
            db.query(Transcription)
            .filter(Transcription.gid == transcription_gid)
            .first()
        )
        if not transcription:
            logger.error(f"Transcription {transcription_gid} not found")
            raise HTTPException(
                status_code=404, detail=f"Transcription {transcription_gid} not found"
            )

        return transcription

    @staticmethod
    def list_case_transcriptions(case_gid: str, db: Session) -> List[Dict[str, Any]]:
        """
        List all transcriptions for a case.

        Args:
            case_gid: GID of the case
            db: Database session

        Returns:
            List[Dict]: List of transcription summaries

        Raises:
            HTTPException: If case not found
        """
        # Validate case exists
        case = db.query(Case).filter(Case.gid == case_gid).first()
        if not case:
            logger.error(f"Case {case_gid} not found")
            raise HTTPException(status_code=404, detail=f"Case {case_gid} not found")

        # Get all transcriptions for the case directly
        transcriptions = (
            db.query(Transcription)
            .filter(Transcription.case_id == case.id)
            .all()
        )

        logger.info(f"Found {len(transcriptions)} transcriptions for case {case_gid}")

        # Build summary list
        result = []
        for trans in transcriptions:
            result.append(
                {
                    "id": trans.id,
                    "gid": trans.gid,
                    "case_id": trans.case_id,
                    "case_gid": case.gid,
                    "filename": trans.filename,
                    "format": trans.format,
                    "duration": trans.duration,
                    "segment_count": len(trans.segments) if trans.segments else 0,
                    "speaker_count": len(trans.speakers) if trans.speakers else 0,
                    "status": trans.status.value if trans.status else "unknown",
                    "created_at": trans.created_at,
                    "uploaded_at": trans.uploaded_at,
                }
            )

        return result

    @staticmethod
    def get_transcription_details(transcription_gid: str, db: Session) -> Dict[str, Any]:
        """
        Get detailed transcription information.

        Args:
            transcription_gid: GID of the transcription
            db: Database session

        Returns:
            Dict: Detailed transcription data

        Raises:
            HTTPException: If transcription not found
        """
        transcription = TranscriptionCoreService.get_transcription(transcription_gid, db)

        # Get key moment metadata for segments
        key_moment_metadata = (
            db.query(TranscriptSegment)
            .filter(TranscriptSegment.transcript_id == transcription.id)
            .all()
        )

        # Build a dict of segment_id -> is_key_moment for quick lookup
        key_moments_map = {meta.segment_id: meta.is_key_moment for meta in key_moment_metadata}

        # Merge key moment status into segments
        segments_with_metadata = []
        for segment in (transcription.segments or []):
            segment_copy = segment.copy()
            segment_id = segment.get('id')
            # Add isKeyMoment field (camelCase for frontend)
            segment_copy['isKeyMoment'] = key_moments_map.get(segment_id, False)
            segments_with_metadata.append(segment_copy)

        return {
            "gid": transcription.gid,
            "id": transcription.id,
            "case_id": transcription.case_id,
            "case_gid": transcription.case.gid if transcription.case else None,
            "document_gid": transcription.document.gid if transcription.document else None,
            "filename": transcription.filename,
            "format": transcription.format,
            "duration": transcription.duration,
            "speakers": transcription.speakers,
            "segments": segments_with_metadata,
            "status": transcription.status.value if transcription.status else "unknown",
            "created_at": transcription.created_at,
            "uploaded_at": transcription.uploaded_at,
            "audio_url": f"/api/v1/transcriptions/{transcription.gid}/audio",
        }

    @staticmethod
    def reprocess_transcription(
        transcription_gid: str,
        db: Session,
        options: Optional[Dict[str, Any]] = None,
    ) -> Transcription:
        """
        Reset and re-queue a transcription for processing.

        Args:
            transcription_gid: GID of the transcription
            db: Database session
            options: Optional dict of transcription options to pass to the worker

        Returns:
            Transcription: Updated transcription record queued for processing
        """
        from app.models.document import DocumentStatus
        import json

        transcription = TranscriptionCoreService.get_transcription(transcription_gid, db)

        logger.info("Reprocessing transcription %s", transcription_gid)

        # Clear existing metadata so the UI reflects processing state immediately
        transcription.status = DocumentStatus.PENDING
        transcription.duration = None
        transcription.segments = []
        transcription.speakers = []
        transcription.waveform_data = None
        transcription.executive_summary = None
        transcription.key_moments = None
        transcription.timeline = None
        transcription.speaker_stats = None
        transcription.action_items = None
        transcription.topics = None
        transcription.entities = None
        transcription.summary_generated_at = None

        # Remove persisted segment metadata
        db.query(TranscriptSegment).filter(
            TranscriptSegment.transcript_id == transcription.id
        ).delete(synchronize_session=False)

        db.commit()
        db.refresh(transcription)

        # Queue worker
        from app.workers.tasks.transcription import transcribe_audio

        worker_options = options or {}
        transcribe_audio.delay(transcription.gid, options=worker_options)

        logger.info(
            "Queued reprocessing task for transcription %s with options: %s",
            transcription_gid,
            json.dumps(worker_options),
        )

        return transcription

    @staticmethod
    def delete_transcription(transcription_gid: str, db: Session) -> Transcription:
        """
        Delete a transcription.

        Args:
            transcription_gid: GID of the transcription
            db: Database session

        Returns:
            Transcription: Deleted transcription record

        Raises:
            HTTPException: If transcription not found or deletion fails
        """
        transcription = TranscriptionCoreService.get_transcription(transcription_gid, db)

        try:
            # Delete from database (cascade will handle related records)
            db.delete(transcription)
            db.commit()

            logger.info(f"Successfully deleted transcription {transcription_gid}")
            return transcription

        except Exception as e:
            logger.error(f"Error deleting transcription {transcription_gid}: {str(e)}")
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete transcription: {str(e)}",
            )

    @staticmethod
    def toggle_key_moment(
        transcription_gid: str, segment_id: str, is_key_moment: bool, db: Session
    ) -> Dict[str, Any]:
        """
        Toggle key moment status for a transcript segment.

        Args:
            transcription_gid: GID of the transcription
            segment_id: UUID of the segment (from JSON segments)
            is_key_moment: New key moment status
            db: Database session

        Returns:
            Dict: Updated segment metadata

        Raises:
            HTTPException: If transcription or segment not found
        """
        # Verify transcription exists
        transcription = TranscriptionCoreService.get_transcription(transcription_gid, db)

        # Verify segment exists in the transcription's JSON segments
        segment_exists = False
        if transcription.segments:
            for seg in transcription.segments:
                if seg.get("id") == segment_id:
                    segment_exists = True
                    break

        if not segment_exists:
            logger.error(
                f"Segment {segment_id} not found in transcription {transcription_gid}"
            )
            raise HTTPException(
                status_code=404,
                detail=f"Segment {segment_id} not found in transcription {transcription_gid}",
            )

        # Check if segment metadata already exists
        segment_metadata = (
            db.query(TranscriptSegment)
            .filter(
                TranscriptSegment.transcript_id == transcription.id,
                TranscriptSegment.segment_id == segment_id,
            )
            .first()
        )

        if segment_metadata:
            # Update existing metadata
            segment_metadata.is_key_moment = is_key_moment
            segment_metadata.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(segment_metadata)
        else:
            # Create new metadata
            segment_metadata = TranscriptSegment(
                transcript_id=transcription.id,
                segment_id=segment_id,
                is_key_moment=is_key_moment,
            )
            db.add(segment_metadata)
            db.commit()
            db.refresh(segment_metadata)

        logger.info(
            f"Toggled key moment for segment {segment_id} in transcription {transcription_gid}: {is_key_moment}"
        )

        return {
            "segment_id": segment_metadata.segment_id,
            "is_key_moment": segment_metadata.is_key_moment,
            "updated_at": segment_metadata.updated_at.isoformat(),
        }

    @staticmethod
    def get_key_moments(transcription_gid: str, db: Session) -> Dict[str, Any]:
        """
        Get all key moments for a transcription.

        Args:
            transcription_gid: GID of the transcription
            db: Database session

        Returns:
            Dict: Key moments data with full segment information

        Raises:
            HTTPException: If transcription not found
        """
        # Verify transcription exists
        transcription = TranscriptionCoreService.get_transcription(transcription_gid, db)

        # Get all key moment segment metadata
        key_moment_metadata = (
            db.query(TranscriptSegment)
            .filter(
                TranscriptSegment.transcript_id == transcription.id,
                TranscriptSegment.is_key_moment == True,
            )
            .all()
        )

        # Build a set of key moment segment IDs for efficient lookup
        key_moment_ids = {meta.segment_id for meta in key_moment_metadata}

        # Filter segments from JSON to get full segment data
        key_moments = []
        if transcription.segments:
            for seg in transcription.segments:
                if seg.get("id") in key_moment_ids:
                    key_moments.append(
                        {
                            "segment_id": seg.get("id"),
                            "text": seg.get("text", ""),
                            "speaker": seg.get("speaker"),
                            "start_time": seg.get("start"),
                            "end_time": seg.get("end"),
                            "confidence": seg.get("confidence"),
                        }
                    )

        # Sort by start time
        key_moments.sort(key=lambda x: x.get("start_time", 0))

        logger.info(
            f"Retrieved {len(key_moments)} key moments for transcription {transcription.id}"
        )

        return {
            "transcription_id": transcription.id,
            "key_moments": key_moments,
            "total": len(key_moments),
        }

    @staticmethod
    def update_speaker(
        transcription_gid: str,
        speaker_id: str,
        name: str,
        role: Optional[str],
        db: Session,
    ) -> Dict[str, Any]:
        """
        Update speaker information in a transcription.

        Args:
            transcription_gid: GID of the transcription
            speaker_id: ID of the speaker to update
            name: New speaker name
            role: Optional speaker role
            db: Database session

        Returns:
            Dict: Updated speaker information

        Raises:
            HTTPException: If transcription or speaker not found
        """
        # Verify transcription exists
        transcription = TranscriptionCoreService.get_transcription(transcription_gid, db)

        # Verify speakers array exists
        if not transcription.speakers or not isinstance(transcription.speakers, list):
            logger.error(
                f"No speakers found in transcription {transcription_gid}"
            )
            raise HTTPException(
                status_code=404,
                detail=f"No speakers found in transcription {transcription_gid}",
            )

        # Find the speaker by ID
        speaker_found = False
        updated_speaker = None
        for speaker in transcription.speakers:
            if speaker.get("speaker_id") == speaker_id:
                # Update speaker information
                speaker["name"] = name
                if role is not None:
                    speaker["role"] = role
                speaker_found = True
                updated_speaker = speaker.copy()
                break

        if not speaker_found:
            logger.error(
                f"Speaker {speaker_id} not found in transcription {transcription_gid}"
            )
            raise HTTPException(
                status_code=404,
                detail=f"Speaker {speaker_id} not found in transcription {transcription_gid}",
            )

        # Mark the speakers column as modified for SQLAlchemy to detect the change
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(transcription, "speakers")

        # Commit the changes
        db.commit()
        db.refresh(transcription)

        logger.info(
            f"Updated speaker {speaker_id} in transcription {transcription_gid}: name='{name}', role='{role}'"
        )

        return {
            "speaker_id": updated_speaker.get("speaker_id"),
            "name": updated_speaker.get("name"),
            "role": updated_speaker.get("role"),
            "color": updated_speaker.get("color"),
        }
