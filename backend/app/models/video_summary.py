"""Video summary model for comprehensive video understanding."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, Float, Text, ForeignKey, DateTime, JSON, CheckConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class VideoSummary(Base):
    """
    VideoSummary model for storing comprehensive video analysis results.

    This model stores high-level summaries and analysis of video content,
    including visual and audio summaries, key moments, and flagged content.
    One-to-one relationship with DiscoveryItem for VIDEO type items.
    """

    __tablename__ = "video_summaries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    discovery_item_id = Column(
        Integer,
        ForeignKey("discovery_items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One-to-one relationship
        index=True
    )
    comprehensive_summary = Column(Text, nullable=True)  # Overall video summary
    key_moments = Column(JSON, nullable=True)  # Array of important moments with timestamps
    visual_summary = Column(Text, nullable=True)  # Summary of visual content
    audio_summary = Column(Text, nullable=True)  # Summary of audio content
    importance_score = Column(
        Float,
        nullable=True,
        index=True
    )  # Overall importance score 0.0-1.0
    flagged_content = Column(JSON, nullable=True)  # Array of flagged content with reasons
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Add constraint for importance_score range
    __table_args__ = (
        CheckConstraint(
            'importance_score IS NULL OR (importance_score >= 0.0 AND importance_score <= 1.0)',
            name='check_video_importance_score_range'
        ),
    )

    # Relationships
    discovery_item = relationship("DiscoveryItem", back_populates="video_summary")

    def __repr__(self) -> str:
        return f"<VideoSummary(id={self.id}, discovery_item_id={self.discovery_item_id}, importance_score={self.importance_score})>"
