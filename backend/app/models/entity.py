"""Entity model and document-entity association."""

from typing import Optional, List
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Table, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.core.database import Base
from app.models.base import UUIDMixin


# Association table for many-to-many relationship between Document and Entity
document_entities = Table(
    "document_entities",
    Base.metadata,
    Column(
        "document_id",
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "entity_id",
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        primary_key=True
    )
)


class Entity(UUIDMixin, Base):
    """
    Entity model representing a named entity extracted from documents.

    Entities are extracted through NLP processing and can be associated
    with multiple documents (e.g., a person name appearing in multiple files).
    """

    __tablename__ = "entities"
    text = Column(String(255), nullable=False, index=True)
    type = Column(String(100), nullable=False, index=True)  # e.g., 'PERSON', 'ORG', 'DATE', 'LOCATION'
    source = Column(String(50), nullable=True)  # Extraction source: 'gliner', 'lexnlp', 'regex'
    confidence = Column(Float, nullable=True)  # NLP model confidence score
    meta_data = Column(JSON, nullable=True)  # Additional metadata

    # Relationships
    documents = relationship(
        "Document",
        secondary=document_entities,
        back_populates="entities",
        lazy="selectin"
    )

    mentions = relationship(
        "EntityMention",
        back_populates="entity",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Entity(id={self.id}, text='{self.text}', type='{self.type}')>"


class EntityMention(UUIDMixin, Base):
    """
    EntityMention model representing a specific occurrence of an entity in a document.

    This allows tracking where an entity appears in a document, with position
    information, context, and mention-specific confidence scores.
    """

    __tablename__ = "entity_mentions"

    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    entity_id = Column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    start_position = Column(Integer, nullable=True)  # Character position where entity starts
    end_position = Column(Integer, nullable=True)  # Character position where entity ends
    context = Column(String(500), nullable=True)  # Surrounding text for context
    confidence = Column(Float, nullable=True)  # Confidence score for this specific mention

    # Relationships
    entity = relationship("Entity", back_populates="mentions")
    document = relationship("Document", back_populates="entity_mentions")

    def __repr__(self) -> str:
        return f"<EntityMention(id={self.id}, document_id={self.document_id}, entity_id={self.entity_id})>"
