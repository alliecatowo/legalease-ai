"""Document model and related enums."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Enum, BigInteger, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class DocumentStatus(str, PyEnum):
    """Document processing status enumeration."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Document(Base):
    """
    Document model representing an uploaded file in a case.

    Documents are associated with cases and can be processed to extract
    text, entities, and other information.
    """

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id = Column(
        Integer,
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    mime_type = Column(String(100), nullable=True)
    size = Column(BigInteger, nullable=False)  # File size in bytes
    status = Column(
        Enum(DocumentStatus, native_enum=True, create_constraint=True),
        nullable=False,
        default=DocumentStatus.PENDING,
        index=True
    )
    meta_data = Column(JSON, nullable=True)  # Additional metadata as JSON
    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    case = relationship("Case", back_populates="documents")
    chunks = relationship(
        "Chunk",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    entities = relationship(
        "Entity",
        secondary="document_entities",
        back_populates="documents",
        lazy="selectin"
    )
    transcription = relationship(
        "Transcription",
        back_populates="document",
        uselist=False,  # One-to-one relationship
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename='{self.filename}', status='{self.status.value}')>"
