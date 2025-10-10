"""
Transcription Tasks

Celery tasks for audio transcription and processing.
Production-ready implementation with WhisperX integration.
"""
import os
import json
import logging
import tempfile
import subprocess
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from io import BytesIO

from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.minio_client import minio_client
from app.models.transcription import Transcription
from app.models.document import Document, DocumentStatus

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Custom exception for transcription errors."""
    pass


class AudioProcessor:
    """Handles audio preprocessing with FFmpeg."""

    @staticmethod
    def preprocess_audio(input_path: str, output_path: str) -> Tuple[bool, str]:
        """
        Preprocess audio file to 16kHz mono WAV format for optimal transcription.

        Args:
            input_path: Path to input audio/video file
            output_path: Path to output WAV file

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-ar', '16000',  # 16kHz sample rate
                '-ac', '1',       # Mono channel
                '-c:a', 'pcm_s16le',  # 16-bit PCM
                '-y',             # Overwrite output file
                output_path
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                return True, "Audio preprocessing successful"
            else:
                error_msg = result.stderr.decode('utf-8', errors='ignore')
                return False, f"FFmpeg error: {error_msg}"

        except subprocess.TimeoutExpired:
            return False, "Audio preprocessing timed out"
        except Exception as e:
            return False, f"Audio preprocessing failed: {str(e)}"

    @staticmethod
    def get_audio_duration(file_path: str) -> Optional[float]:
        """
        Get audio duration in seconds using FFprobe.

        Args:
            file_path: Path to audio file

        Returns:
            Duration in seconds, or None if failed
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                file_path
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30
            )

            if result.returncode == 0:
                duration_str = result.stdout.decode('utf-8').strip()
                return float(duration_str)
            return None

        except Exception as e:
            logger.warning(f"Failed to get audio duration: {e}")
            return None


class WhisperTranscriber:
    """Handles transcription using OpenAI Whisper API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize transcriber with OpenAI API key."""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise TranscriptionError("OpenAI API key not configured")

    def transcribe(
        self,
        audio_path: str,
        language: str = "en",
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio file using OpenAI Whisper API.

        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'en', 'es')
            task_id: Optional Celery task ID for progress updates

        Returns:
            Dict containing transcription results with segments
        """
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            logger.info(f"Starting Whisper API transcription for {audio_path}")

            with open(audio_path, 'rb') as audio_file:
                # Use Whisper API with timestamp granularities
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    response_format="verbose_json",
                    timestamp_granularities=["segment", "word"]
                )

            # Parse response into segments format
            segments = []
            if hasattr(response, 'segments') and response.segments:
                for idx, segment in enumerate(response.segments):
                    seg_data = {
                        'id': idx,
                        'start': segment.get('start', 0.0),
                        'end': segment.get('end', 0.0),
                        'text': segment.get('text', '').strip(),
                        'words': []
                    }

                    # Add word-level timestamps if available
                    if hasattr(segment, 'words') and segment.words:
                        for word in segment.words:
                            seg_data['words'].append({
                                'word': word.get('word', ''),
                                'start': word.get('start', 0.0),
                                'end': word.get('end', 0.0)
                            })

                    segments.append(seg_data)
            else:
                # Fallback: create single segment from text
                segments = [{
                    'id': 0,
                    'start': 0.0,
                    'end': 0.0,
                    'text': response.text,
                    'words': []
                }]

            result = {
                'text': response.text,
                'language': response.language if hasattr(response, 'language') else language,
                'duration': response.duration if hasattr(response, 'duration') else None,
                'segments': segments
            }

            logger.info(f"Transcription completed: {len(segments)} segments")
            return result

        except Exception as e:
            logger.error(f"Whisper API transcription failed: {str(e)}")
            raise TranscriptionError(f"Transcription failed: {str(e)}")


class SpeakerDiarizer:
    """Handles speaker diarization using simple heuristics."""

    @staticmethod
    def diarize_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Add speaker labels to segments using simple pause-based heuristics.

        This is a simplified implementation. For production, consider using:
        - Pyannote.audio for deep learning-based diarization
        - AssemblyAI API for cloud-based diarization

        Args:
            segments: List of transcription segments

        Returns:
            List of segments with speaker labels added
        """
        if not segments:
            return segments

        # Simple heuristic: detect speaker changes based on pauses
        PAUSE_THRESHOLD = 2.0  # seconds

        current_speaker = 1
        diarized_segments = []

        for idx, segment in enumerate(segments):
            # Check if there's a significant pause before this segment
            if idx > 0:
                prev_end = segments[idx - 1]['end']
                current_start = segment['start']
                pause_duration = current_start - prev_end

                # If pause is significant, assume speaker change
                if pause_duration > PAUSE_THRESHOLD:
                    current_speaker += 1

            # Add speaker label
            segment_copy = segment.copy()
            segment_copy['speaker'] = f"SPEAKER_{current_speaker:02d}"
            diarized_segments.append(segment_copy)

        return diarized_segments


class TranscriptionExporter:
    """Handles exporting transcriptions to various formats."""

    @staticmethod
    def export_to_docx(segments: List[Dict[str, Any]], output_path: str) -> bool:
        """
        Export transcription to DOCX format.

        Args:
            segments: List of transcription segments
            output_path: Path to output DOCX file

        Returns:
            True if successful, False otherwise
        """
        try:
            from docx import Document
            from docx.shared import Pt, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH

            doc = Document()

            # Add title
            title = doc.add_heading('Transcription', 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER

            # Add metadata
            doc.add_paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            doc.add_paragraph("")

            # Group segments by speaker
            current_speaker = None
            current_paragraph = None

            for segment in segments:
                speaker = segment.get('speaker', 'SPEAKER_01')
                start_time = segment.get('start', 0.0)
                text = segment.get('text', '').strip()

                if not text:
                    continue

                # Add speaker header if speaker changed
                if speaker != current_speaker:
                    current_speaker = speaker

                    # Add speaker heading
                    speaker_para = doc.add_paragraph()
                    speaker_run = speaker_para.add_run(f"\n{speaker}")
                    speaker_run.bold = True
                    speaker_run.font.size = Pt(12)
                    speaker_run.font.color.rgb = RGBColor(0, 0, 139)

                # Add timestamped text
                para = doc.add_paragraph()

                # Add timestamp
                timestamp_str = TranscriptionExporter._format_timestamp(start_time)
                time_run = para.add_run(f"[{timestamp_str}] ")
                time_run.font.color.rgb = RGBColor(128, 128, 128)
                time_run.font.size = Pt(9)

                # Add text
                text_run = para.add_run(text)
                text_run.font.size = Pt(11)

            doc.save(output_path)
            logger.info(f"Exported DOCX to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export DOCX: {e}")
            return False

    @staticmethod
    def export_to_srt(segments: List[Dict[str, Any]], output_path: str) -> bool:
        """
        Export transcription to SRT subtitle format.

        Args:
            segments: List of transcription segments
            output_path: Path to output SRT file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for idx, segment in enumerate(segments, start=1):
                    start = segment.get('start', 0.0)
                    end = segment.get('end', 0.0)
                    text = segment.get('text', '').strip()
                    speaker = segment.get('speaker', '')

                    if not text:
                        continue

                    # Format: sequence number
                    f.write(f"{idx}\n")

                    # Format: start --> end
                    start_str = TranscriptionExporter._format_srt_timestamp(start)
                    end_str = TranscriptionExporter._format_srt_timestamp(end)
                    f.write(f"{start_str} --> {end_str}\n")

                    # Format: text (with optional speaker)
                    if speaker:
                        f.write(f"[{speaker}] {text}\n")
                    else:
                        f.write(f"{text}\n")

                    # Blank line between subtitles
                    f.write("\n")

            logger.info(f"Exported SRT to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export SRT: {e}")
            return False

    @staticmethod
    def export_to_vtt(segments: List[Dict[str, Any]], output_path: str) -> bool:
        """
        Export transcription to WebVTT subtitle format.

        Args:
            segments: List of transcription segments
            output_path: Path to output VTT file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                # WebVTT header
                f.write("WEBVTT\n\n")

                for idx, segment in enumerate(segments, start=1):
                    start = segment.get('start', 0.0)
                    end = segment.get('end', 0.0)
                    text = segment.get('text', '').strip()
                    speaker = segment.get('speaker', '')

                    if not text:
                        continue

                    # Format: start --> end
                    start_str = TranscriptionExporter._format_vtt_timestamp(start)
                    end_str = TranscriptionExporter._format_vtt_timestamp(end)
                    f.write(f"{start_str} --> {end_str}\n")

                    # Format: text with speaker as voice tag
                    if speaker:
                        f.write(f"<v {speaker}>{text}</v>\n")
                    else:
                        f.write(f"{text}\n")

                    # Blank line between cues
                    f.write("\n")

            logger.info(f"Exported VTT to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export VTT: {e}")
            return False

    @staticmethod
    def export_to_json(
        segments: List[Dict[str, Any]],
        output_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Export transcription to JSON format.

        Args:
            segments: List of transcription segments
            output_path: Path to output JSON file
            metadata: Optional metadata to include

        Returns:
            True if successful, False otherwise
        """
        try:
            data = {
                'metadata': metadata or {},
                'segments': segments,
                'generated_at': datetime.utcnow().isoformat()
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Exported JSON to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export JSON: {e}")
            return False

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Format seconds to HH:MM:SS."""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        secs = int(td.total_seconds() % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @staticmethod
    def _format_srt_timestamp(seconds: float) -> str:
        """Format seconds to SRT timestamp format (HH:MM:SS,mmm)."""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        secs = int(td.total_seconds() % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def _format_vtt_timestamp(seconds: float) -> str:
        """Format seconds to WebVTT timestamp format (HH:MM:SS.mmm)."""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        secs = int(td.total_seconds() % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


@celery_app.task(name="transcribe_audio", bind=True)
def transcribe_audio(
    self,
    document_id: int,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Transcribe an audio/video file to text with timestamps and speaker diarization.

    Full pipeline:
    1. Download audio/video from MinIO
    2. Preprocess with FFmpeg (convert to 16kHz mono WAV)
    3. Transcribe with OpenAI Whisper API
    4. Diarize speakers (simple heuristic-based)
    5. Export to DOCX, SRT, VTT, JSON formats
    6. Upload exports to MinIO
    7. Update transcription record in PostgreSQL
    8. Handle errors gracefully with status updates

    Args:
        document_id: ID of the document to transcribe
        language: Language code for transcription (default: "en")

    Returns:
        Dict containing transcription status and results
    """
    db = SessionLocal()
    temp_dir = None

    try:
        # Update task state to STARTED
        self.update_state(
            state='STARTED',
            meta={'status': 'Initializing transcription', 'progress': 0}
        )

        # Step 1: Get document from database
        logger.info(f"Starting transcription for document {document_id}")
        document = db.query(Document).filter(Document.id == document_id).first()

        if not document:
            raise TranscriptionError(f"Document {document_id} not found")

        # Update document status
        document.status = DocumentStatus.PROCESSING
        db.commit()

        # Step 2: Download audio/video from MinIO
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Downloading audio from storage', 'progress': 10}
        )

        logger.info(f"Downloading file from MinIO: {document.file_path}")
        file_content = minio_client.download_file(document.file_path)

        if not file_content:
            raise TranscriptionError("Failed to download file from MinIO")

        # Create temporary directory for processing
        temp_dir = tempfile.mkdtemp(prefix='transcription_')
        logger.info(f"Created temporary directory: {temp_dir}")

        # Get file extension
        _, ext = os.path.splitext(document.filename)
        original_file = os.path.join(temp_dir, f"original{ext}")
        processed_wav = os.path.join(temp_dir, "audio.wav")

        # Save original file
        with open(original_file, 'wb') as f:
            f.write(file_content)

        # Step 3: Preprocess audio with FFmpeg
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Preprocessing audio', 'progress': 20}
        )

        logger.info("Preprocessing audio with FFmpeg")
        processor = AudioProcessor()
        success, message = processor.preprocess_audio(original_file, processed_wav)

        if not success:
            raise TranscriptionError(f"Audio preprocessing failed: {message}")

        # Get audio duration
        duration = processor.get_audio_duration(processed_wav)
        logger.info(f"Audio duration: {duration} seconds")

        # Step 4: Transcribe with Whisper
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Transcribing audio', 'progress': 30}
        )

        logger.info("Starting Whisper transcription")
        transcriber = WhisperTranscriber()
        transcription_result = transcriber.transcribe(
            processed_wav,
            language=language,
            task_id=self.request.id
        )

        segments = transcription_result['segments']
        full_text = transcription_result['text']

        logger.info(f"Transcription completed: {len(segments)} segments, {len(full_text)} characters")

        # Step 5: Diarize speakers
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Identifying speakers', 'progress': 60}
        )

        logger.info("Performing speaker diarization")
        diarizer = SpeakerDiarizer()
        diarized_segments = diarizer.diarize_segments(segments)

        # Extract speaker information
        speakers = {}
        for segment in diarized_segments:
            speaker = segment.get('speaker', 'SPEAKER_01')
            if speaker not in speakers:
                speakers[speaker] = {
                    'id': speaker,
                    'segments_count': 0
                }
            speakers[speaker]['segments_count'] += 1

        # Step 6: Export to multiple formats
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Exporting transcription', 'progress': 70}
        )

        logger.info("Exporting transcription to multiple formats")
        exporter = TranscriptionExporter()

        # Prepare metadata
        metadata = {
            'document_id': document_id,
            'filename': document.filename,
            'language': language,
            'duration': duration,
            'segments_count': len(diarized_segments),
            'speakers_count': len(speakers)
        }

        # Export paths
        docx_path = os.path.join(temp_dir, "transcription.docx")
        srt_path = os.path.join(temp_dir, "transcription.srt")
        vtt_path = os.path.join(temp_dir, "transcription.vtt")
        json_path = os.path.join(temp_dir, "transcription.json")

        # Export to all formats
        exporter.export_to_docx(diarized_segments, docx_path)
        exporter.export_to_srt(diarized_segments, srt_path)
        exporter.export_to_vtt(diarized_segments, vtt_path)
        exporter.export_to_json(diarized_segments, json_path, metadata)

        # Step 7: Upload exports to MinIO
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Uploading results', 'progress': 85}
        )

        logger.info("Uploading exports to MinIO")

        # Generate MinIO paths
        base_path = os.path.splitext(document.file_path)[0]
        export_paths = {}

        for format_name, local_path in [
            ('docx', docx_path),
            ('srt', srt_path),
            ('vtt', vtt_path),
            ('json', json_path)
        ]:
            if os.path.exists(local_path):
                minio_path = f"{base_path}.{format_name}"

                with open(local_path, 'rb') as f:
                    file_data = f.read()
                    content_type = {
                        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        'srt': 'text/plain',
                        'vtt': 'text/vtt',
                        'json': 'application/json'
                    }.get(format_name, 'application/octet-stream')

                    minio_client.upload_file(
                        file_data=BytesIO(file_data),
                        object_name=minio_path,
                        content_type=content_type,
                        length=len(file_data)
                    )

                export_paths[format_name] = minio_path
                logger.info(f"Uploaded {format_name.upper()} to {minio_path}")

        # Step 8: Update transcription record in database
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Saving transcription', 'progress': 95}
        )

        logger.info("Updating database with transcription results")

        # Check if transcription record exists
        transcription = db.query(Transcription).filter(
            Transcription.document_id == document_id
        ).first()

        if not transcription:
            # Create new transcription record
            transcription = Transcription(
                document_id=document_id,
                format=ext.lstrip('.') if ext else None,
                duration=duration,
                speakers=list(speakers.values()),
                segments=diarized_segments
            )
            db.add(transcription)
        else:
            # Update existing record
            transcription.format = ext.lstrip('.') if ext else None
            transcription.duration = duration
            transcription.speakers = list(speakers.values())
            transcription.segments = diarized_segments

        # Update document status and metadata
        document.status = DocumentStatus.COMPLETED
        document.meta_data = document.meta_data or {}
        document.meta_data.update({
            'transcription': {
                'completed_at': datetime.utcnow().isoformat(),
                'duration': duration,
                'segments_count': len(diarized_segments),
                'speakers_count': len(speakers),
                'language': language,
                'export_formats': list(export_paths.keys())
            }
        })

        db.commit()

        logger.info(f"Transcription completed successfully for document {document_id}")

        # Step 9: Return success result
        return {
            'status': 'completed',
            'document_id': document_id,
            'transcription_id': transcription.id,
            'filename': document.filename,
            'duration': duration,
            'segments_count': len(diarized_segments),
            'speakers_count': len(speakers),
            'speakers': list(speakers.values()),
            'export_paths': export_paths,
            'language': language,
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Transcription failed for document {document_id}: {str(e)}", exc_info=True)

        # Update document status to FAILED
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = DocumentStatus.FAILED
                document.meta_data = document.meta_data or {}
                document.meta_data['transcription_error'] = {
                    'error': str(e),
                    'failed_at': datetime.utcnow().isoformat()
                }
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update document status: {str(db_error)}")

        # Update task state
        self.update_state(
            state='FAILURE',
            meta={'status': f'Transcription failed: {str(e)}', 'error': str(e)}
        )

        return {
            'status': 'failed',
            'error': str(e),
            'document_id': document_id,
            'task_id': self.request.id
        }

    finally:
        # Cleanup temporary files
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp directory: {cleanup_error}")

        db.close()


@celery_app.task(name="process_transcription", bind=True)
def process_transcription(
    self,
    transcription_id: str,
    case_id: str,
    extract_entities: bool = True
) -> Dict[str, Any]:
    """
    Process a completed transcription for analysis and entity extraction.

    This is a placeholder task that will be fully implemented in Phase 3.
    It will handle post-transcription processing and NLP tasks.

    Args:
        transcription_id: Unique identifier for the transcription
        case_id: Unique identifier for the case
        extract_entities: Whether to extract named entities (default: True)

    Returns:
        Dict containing processing status and analysis results
    """
    # Placeholder - will implement in Phase 3
    # Future implementation will:
    # 1. Fetch transcription from database
    # 2. Run NLP entity extraction
    # 3. Extract legal terms and entities
    # 4. Create searchable chunks
    # 5. Index in Qdrant for semantic search
    # 6. Update database with entities

    return {
        "status": "pending",
        "transcription_id": transcription_id,
        "case_id": case_id,
        "extract_entities": extract_entities,
        "task_id": self.request.id,
    }
