"""
SQLAlchemy ORM models for Knowledge domain.

These models map knowledge graph entities to database tables using
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


class EntityModel(Base):
    """
    ORM model for Entity entity.

    Represents people, organizations, and locations in the knowledge graph.
    """

    __tablename__ = "kg_entities"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Core fields
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Timestamps
    first_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # JSON fields
    aliases: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )
    attributes: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    source_citations: Mapped[List[str]] = mapped_column(
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
    outgoing_relationships: Mapped[List["RelationshipModel"]] = relationship(
        "RelationshipModel",
        foreign_keys="RelationshipModel.from_entity_id",
        back_populates="from_entity",
        cascade="all, delete-orphan",
    )
    incoming_relationships: Mapped[List["RelationshipModel"]] = relationship(
        "RelationshipModel",
        foreign_keys="RelationshipModel.to_entity_id",
        back_populates="to_entity",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_kg_entities_type_name", "entity_type", "name"),
        Index("ix_kg_entities_first_seen", "first_seen"),
        Index("ix_kg_entities_last_seen", "last_seen"),
    )


class EventModel(Base):
    """
    ORM model for Event entity.

    Represents temporal events extracted from evidence.
    """

    __tablename__ = "kg_events"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Core fields
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Temporal fields
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Location (can be UUID or string)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # JSON fields
    participants: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )
    source_citations: Mapped[List[str]] = mapped_column(
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

    __table_args__ = (
        Index("ix_kg_events_type_timestamp", "event_type", "timestamp"),
        Index("ix_kg_events_timestamp", "timestamp"),
    )


class RelationshipModel(Base):
    """
    ORM model for Relationship entity.

    Represents connections between entities in the knowledge graph.
    """

    __tablename__ = "kg_relationships"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    from_entity_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("kg_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    to_entity_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("kg_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Core fields
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    strength: Mapped[float] = mapped_column(Float, nullable=False)

    # Temporal bounds
    temporal_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    temporal_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # JSON fields
    source_citations: Mapped[List[str]] = mapped_column(
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
    from_entity: Mapped["EntityModel"] = relationship(
        "EntityModel",
        foreign_keys=[from_entity_id],
        back_populates="outgoing_relationships",
    )
    to_entity: Mapped["EntityModel"] = relationship(
        "EntityModel",
        foreign_keys=[to_entity_id],
        back_populates="incoming_relationships",
    )

    __table_args__ = (
        Index("ix_kg_relationships_from_to", "from_entity_id", "to_entity_id"),
        Index("ix_kg_relationships_type", "relationship_type"),
        Index("ix_kg_relationships_strength", "strength"),
    )
