"""Chunk model for document text segmentation."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class Chunk(Base):
    """
    Chunk model representing a segmented piece of a document.

    Chunks are created when documents are processed and split into
    manageable pieces for indexing, embedding, and retrieval.
    """

    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    text = Column(Text, nullable=False)
    chunk_type = Column(String(50), nullable=True)  # e.g., 'paragraph', 'page', 'section'
    position = Column(Integer, nullable=False)  # Position/order in the document
    page_number = Column(Integer, nullable=True)  # Source page number if applicable
    meta_data = Column(JSON, nullable=True)  # Additional metadata (e.g., embeddings, confidence)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        text_preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"<Chunk(id={self.id}, document_id={self.document_id}, position={self.position}, text='{text_preview}')>"
