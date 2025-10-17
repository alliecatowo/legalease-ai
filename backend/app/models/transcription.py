"""Transcription model for audio/video document processing."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.core.database import Base
import uuid


class TranscriptSegment(Base):
    """
    TranscriptSegment model for individual transcript segments.

    Stores metadata about transcript segments including key moment status.
    The actual segment data (text, timing, etc.) is still stored in the
    Transcription.segments JSON field, with segment_id as the linkage.
    """

    __tablename__ = "transcript_segments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    transcription_id = Column(
        Integer,
        ForeignKey("transcriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    segment_id = Column(String(36), nullable=False, unique=True, index=True)  # UUID from JSON
    is_key_moment = Column(Boolean, nullable=False, default=False)
    highlights: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Array of {start: int, end: int, text: str, type: str}
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    transcription = relationship("Transcription", back_populates="segment_metadata")

    def __repr__(self) -> str:
        return f"<TranscriptSegment(id={self.id}, transcription_id={self.transcription_id}, segment_id='{self.segment_id}', is_key_moment={self.is_key_moment})>"


class Transcription(Base):
    """
    Transcription model representing audio/video transcription results.

    Transcriptions are generated for audio and video documents and include
    timing information, speaker identification, and segmented text.
    Also includes AI-generated summaries and analysis.
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

    # AI-generated summary fields
    executive_summary = Column(Text, nullable=True)  # 200-300 word summary
    key_moments = Column(JSON, nullable=True)  # Top 10-15 important moments with timestamps
    timeline = Column(JSON, nullable=True)  # Chronological events mentioned
    speaker_stats = Column(JSON, nullable=True)  # Detailed speaker statistics
    action_items = Column(JSON, nullable=True)  # Decisions, agreements, follow-ups
    topics = Column(JSON, nullable=True)  # Main topics discussed
    entities = Column(JSON, nullable=True)  # Parties, dates, legal terms, citations
    summary_generated_at = Column(DateTime, nullable=True)  # When summary was generated

    # Relationships
    document = relationship("Document", back_populates="transcription")
    segment_metadata = relationship(
        "TranscriptSegment",
        back_populates="transcription",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Transcription(id={self.id}, document_id={self.document_id}, format='{self.format}', duration={self.duration})>"
