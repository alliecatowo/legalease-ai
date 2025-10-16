"""
Celery Tasks Module

Import all task modules here to ensure they are discovered by Celery.
"""
from app.workers.tasks.document_processing import (
    process_document,
    generate_document,
    process_uploaded_document,
)
from app.workers.tasks.transcription import (
    transcribe_audio,
    process_transcription,
)
from app.workers.tasks.discovery_processing import (
    process_discovery_photo,
    process_discovery_video,
    extract_video_frames,
    analyze_video_frame,
)

__all__ = [
    "process_document",
    "generate_document",
    "process_uploaded_document",
    "transcribe_audio",
    "process_transcription",
    "process_discovery_photo",
    "process_discovery_video",
    "extract_video_frames",
    "analyze_video_frame",
]
