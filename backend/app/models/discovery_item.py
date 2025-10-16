"""Discovery item model and related enums."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Enum, Float, Boolean, ForeignKey, JSON, Text, CheckConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class DiscoveryItemType(str, PyEnum):
    """Discovery item type enumeration."""

    PHOTO = "PHOTO"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    SOCIAL_POST = "SOCIAL_POST"
    EMAIL = "EMAIL"
    CALL_LOG = "CALL_LOG"
    SMS = "SMS"


class DiscoveryItemSource(str, PyEnum):
    """Discovery item source enumeration."""

    CELLEBRITE = "CELLEBRITE"
    PROSECUTOR = "PROSECUTOR"
    EVIDENCE = "EVIDENCE"
    SURVEILLANCE = "SURVEILLANCE"
    BODY_CAM = "BODY_CAM"


class DiscoveryItemFormFactor(str, PyEnum):
    """Discovery item form factor enumeration."""

    SHORT_FORM = "SHORT_FORM"  # Short-form content (e.g., TikTok, Reels)
    LONG_FORM = "LONG_FORM"    # Long-form content (e.g., full videos)
    SINGLE_ITEM = "SINGLE_ITEM"  # Single items (e.g., photos, emails)


class DiscoveryItem(Base):
    """
    DiscoveryItem model representing evidence and discovery materials.

    Discovery items are various types of digital evidence associated with cases,
    including photos, videos, social media posts, emails, and communication logs.
    """

    __tablename__ = "discovery_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id = Column(
        Integer,
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    type = Column(
        Enum(DiscoveryItemType, native_enum=True, create_constraint=True),
        nullable=False,
        index=True
    )
    source = Column(
        Enum(DiscoveryItemSource, native_enum=True, create_constraint=True),
        nullable=False,
        index=True
    )
    form_factor = Column(
        Enum(DiscoveryItemFormFactor, native_enum=True, create_constraint=True),
        nullable=False,
        index=True
    )
    original_filename = Column(String(512), nullable=False)
    file_path = Column(String(1024), nullable=False)
    item_metadata = Column(JSON, nullable=True)  # Additional metadata as JSON
    processed = Column(Boolean, nullable=False, default=False, index=True)
    importance_score = Column(
        Float,
        nullable=True,
        index=True
    )  # Score between 0.0 and 1.0
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Add constraint for importance_score range
    __table_args__ = (
        CheckConstraint(
            'importance_score IS NULL OR (importance_score >= 0.0 AND importance_score <= 1.0)',
            name='check_importance_score_range'
        ),
    )

    # Relationships
    case = relationship("Case", back_populates="discovery_items")
    visual_content = relationship(
        "VisualContent",
        back_populates="discovery_item",
        cascade="all, delete-orphan"
    )
    video_summary = relationship(
        "VideoSummary",
        back_populates="discovery_item",
        uselist=False,  # One-to-one relationship
        cascade="all, delete-orphan"
    )
    social_post = relationship(
        "SocialMediaPost",
        back_populates="discovery_item",
        uselist=False,  # One-to-one relationship
        cascade="all, delete-orphan"
    )
    email = relationship(
        "EmailMessage",
        back_populates="discovery_item",
        uselist=False,  # One-to-one relationship
        cascade="all, delete-orphan"
    )
    call_log = relationship(
        "CallLog",
        back_populates="discovery_item",
        uselist=False,  # One-to-one relationship
        cascade="all, delete-orphan"
    )
    categories = relationship(
        "Category",
        secondary="discovery_item_categories",
        back_populates="discovery_items"
    )

    def __repr__(self) -> str:
        return f"<DiscoveryItem(id={self.id}, type='{self.type.value}', source='{self.source.value}', filename='{self.original_filename}')>"
