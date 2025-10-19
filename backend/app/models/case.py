"""Case model and related enums."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Enum, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.core.database import Base
from app.models.base import UUIDMixin


class CaseStatus(str, PyEnum):
    """Case status enumeration."""

    ACTIVE = "ACTIVE"      # Case is open and being worked on
    CLOSED = "CLOSED"      # Case is complete but searchable
    ARCHIVED = "ARCHIVED"  # Case is archived (hidden by default)


class Case(UUIDMixin, Base):
    """
    Case model representing a legal case.

    A case is the primary container for legal documents and related information.
    Cases progress through various statuses from staging to archival.
    """

    __tablename__ = "cases"
    name = Column(String(255), nullable=False, index=True)
    case_number = Column(String(100), unique=True, nullable=False, index=True)
    client = Column(String(255), nullable=False, index=True)
    matter_type = Column(String(100), nullable=True)
    status = Column(
        Enum(CaseStatus, native_enum=True, create_constraint=True),
        nullable=False,
        default=CaseStatus.ACTIVE,
        index=True
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    archived_at = Column(DateTime, nullable=True)

    # Relationships
    documents = relationship(
        "Document",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    transcriptions = relationship(
        "Transcription",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    forensic_exports = relationship(
        "ForensicExport",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Case(id={self.id}, case_number='{self.case_number}', name='{self.name}', status='{self.status.value}')>"
