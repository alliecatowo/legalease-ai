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

__all__ = [
    "process_document",
    "generate_document",
    "process_uploaded_document",
    "transcribe_audio",
    "process_transcription",
]
