"""Entity model and document-entity association."""

from typing import Optional, List
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Table, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


# Association table for many-to-many relationship between Document and Entity
document_entities = Table(
    "document_entities",
    Base.metadata,
    Column(
        "document_id",
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "entity_id",
        Integer,
        ForeignKey("entities.id", ondelete="CASCADE"),
        primary_key=True
    )
)


class Entity(Base):
    """
    Entity model representing a named entity extracted from documents.

    Entities are extracted through NLP processing and can be associated
    with multiple documents (e.g., a person name appearing in multiple files).
    """

    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    text = Column(String(255), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False, index=True)  # e.g., 'PERSON', 'ORG', 'DATE', 'LOCATION'
    confidence = Column(Float, nullable=True)  # NLP model confidence score
    meta_data = Column(JSON, nullable=True)  # Additional metadata

    # Relationships
    documents = relationship(
        "Document",
        secondary=document_entities,
        back_populates="entities",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Entity(id={self.id}, text='{self.text}', type='{self.entity_type}')>"
