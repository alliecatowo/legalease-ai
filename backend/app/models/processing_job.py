"""Processing job model for tracking async tasks."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.base import UUIDMixin


class ProcessingJob(UUIDMixin, Base):
    """
    ProcessingJob model for tracking asynchronous processing tasks.

    Jobs track the status and results of various processing operations
    such as document parsing, entity extraction, transcription, etc.
    """

    __tablename__ = "processing_jobs"

    job_type = Column(String(100), nullable=False, index=True)  # e.g., 'transcription', 'entity_extraction', 'ocr'
    status = Column(String(50), nullable=False, index=True)  # e.g., 'pending', 'running', 'completed', 'failed'
    entity_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)  # Generic ID for the entity being processed (document_id, case_id, etc.)
    result = Column(JSON, nullable=True)  # Job results as JSON
    error = Column(Text, nullable=True)  # Error message if job failed
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<ProcessingJob(id={self.id}, type='{self.job_type}', status='{self.status}', entity_id={self.entity_id})>"
