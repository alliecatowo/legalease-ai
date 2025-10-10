"""Database models for LegalEase."""

from app.core.database import Base
from app.models.case import Case, CaseStatus
from app.models.document import Document, DocumentStatus
from app.models.chunk import Chunk
from app.models.entity import Entity, document_entities
from app.models.transcription import Transcription
from app.models.processing_job import ProcessingJob

# Export all models for easier imports
__all__ = [
    "Base",
    "Case",
    "CaseStatus",
    "Document",
    "DocumentStatus",
    "Chunk",
    "Entity",
    "document_entities",
    "Transcription",
    "ProcessingJob",
]
