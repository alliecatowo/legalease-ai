"""Transcription model for audio/video document processing."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class Transcription(Base):
    """
    Transcription model representing audio/video transcription results.

    Transcriptions are generated for audio and video documents and include
    timing information, speaker identification, and segmented text.
    """

    __tablename__ = "transcriptions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One-to-one relationship with Document
        index=True
    )
    format = Column(String(50), nullable=True)  # e.g., 'mp3', 'wav', 'mp4'
    duration = Column(Float, nullable=True)  # Duration in seconds
    speakers = Column(JSON, nullable=True)  # Speaker identification data
    segments = Column(JSON, nullable=False)  # Transcription segments with timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="transcription")

    def __repr__(self) -> str:
        return f"<Transcription(id={self.id}, document_id={self.document_id}, format='{self.format}', duration={self.duration})>"
