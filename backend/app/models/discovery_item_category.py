"""Discovery item category association model."""

from datetime import datetime
from sqlalchemy import Column, Integer, Float, ForeignKey, Boolean, DateTime, Table, CheckConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class DiscoveryItemCategory(Base):
    """
    DiscoveryItemCategory association model for many-to-many relationship.

    This model links discovery items to categories with additional metadata
    about the classification, including confidence scores and whether it was
    auto-generated or manually assigned.
    """

    __tablename__ = "discovery_item_categories"

    discovery_item_id = Column(
        Integer,
        ForeignKey("discovery_items.id", ondelete="CASCADE"),
        primary_key=True,
        index=True
    )
    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
        index=True
    )
    confidence_score = Column(Float, nullable=True)  # Confidence score 0.0-1.0 for auto-generated
    auto_generated = Column(Boolean, nullable=False, default=False, index=True)  # Whether classification was auto-generated
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Add constraint for confidence_score range
    __table_args__ = (
        CheckConstraint(
            'confidence_score IS NULL OR (confidence_score >= 0.0 AND confidence_score <= 1.0)',
            name='check_category_confidence_score_range'
        ),
    )

    def __repr__(self) -> str:
        return f"<DiscoveryItemCategory(discovery_item_id={self.discovery_item_id}, category_id={self.category_id}, confidence={self.confidence_score})>"
