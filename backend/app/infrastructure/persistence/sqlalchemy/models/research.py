"""
SQLAlchemy ORM models for Research domain.

These models map research domain entities to database tables using
SQLAlchemy 2.0 declarative style with proper typing.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    String,
    Text,
    Float,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ResearchRunModel(Base):
    """
    ORM model for ResearchRun entity.

    Represents an AI-powered deep research session analyzing case evidence.
    """

    __tablename__ = "research_runs"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    case_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Core fields
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    phase: Mapped[str] = mapped_column(String(50), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Results
    dossier_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # JSON fields
    findings: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )
    config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # Relationships
    finding_entities: Mapped[List["FindingModel"]] = relationship(
        "FindingModel",
        back_populates="research_run",
        cascade="all, delete-orphan",
    )
    hypotheses: Mapped[List["HypothesisModel"]] = relationship(
        "HypothesisModel",
        back_populates="research_run",
        cascade="all, delete-orphan",
    )
    dossier: Mapped[Optional["DossierModel"]] = relationship(
        "DossierModel",
        back_populates="research_run",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_research_runs_case_id_status", "case_id", "status"),
        Index("ix_research_runs_started_at", "started_at"),
    )


class FindingModel(Base):
    """
    ORM model for Finding entity.

    Represents a discovered fact, pattern, or insight from evidence analysis.
    """

    __tablename__ = "findings"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    research_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("research_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Core fields
    finding_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    # Scores
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    relevance: Mapped[float] = mapped_column(Float, nullable=False)

    # JSON fields
    entities: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )
    citations: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )
    tags: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )
    metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # Relationships
    research_run: Mapped["ResearchRunModel"] = relationship(
        "ResearchRunModel",
        back_populates="finding_entities",
    )

    __table_args__ = (
        Index("ix_findings_research_run_type", "research_run_id", "finding_type"),
        Index("ix_findings_confidence", "confidence"),
    )


class HypothesisModel(Base):
    """
    ORM model for Hypothesis entity.

    Represents a testable theory or explanation generated from findings.
    """

    __tablename__ = "hypotheses"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    research_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("research_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Core fields
    hypothesis_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # JSON fields
    supporting_findings: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )
    contradicting_findings: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )
    metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # Relationships
    research_run: Mapped["ResearchRunModel"] = relationship(
        "ResearchRunModel",
        back_populates="hypotheses",
    )

    __table_args__ = (
        Index("ix_hypotheses_confidence", "confidence"),
    )


class DossierModel(Base):
    """
    ORM model for Dossier entity.

    Represents the final research output document with executive summary,
    findings, hypotheses, and citations.
    """

    __tablename__ = "dossiers"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    research_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("research_runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Core fields
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    citations_appendix: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # JSON fields
    sections: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )
    metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # Relationships
    research_run: Mapped["ResearchRunModel"] = relationship(
        "ResearchRunModel",
        back_populates="dossier",
    )
