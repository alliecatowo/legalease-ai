"""Visual content model for image and video frame analysis."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class VisualContent(Base):
    """
    VisualContent model for storing VLM (Vision Language Model) analysis results.

    This model stores analysis results for images and video frames, including
    captions, detected objects, scenes, activities, and content flags.
    For photos, frame_number and timestamp_in_video are NULL.
    """

    __tablename__ = "visual_content"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    discovery_item_id = Column(
        Integer,
        ForeignKey("discovery_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    frame_number = Column(Integer, nullable=True)  # NULL for photos, frame number for video frames
    timestamp_in_video = Column(Float, nullable=True)  # NULL for photos, timestamp in seconds for video frames
    vlm_caption = Column(Text, nullable=True)  # VLM-generated caption/description
    detected_objects = Column(JSON, nullable=True)  # Array of detected objects
    detected_scenes = Column(JSON, nullable=True)  # Array of detected scenes
    detected_activities = Column(JSON, nullable=True)  # Array of detected activities
    sensitive_flags = Column(JSON, nullable=True)  # Flags for sensitive/explicit content
    is_meme = Column(Boolean, nullable=False, default=False)  # Whether content is identified as a meme
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    discovery_item = relationship("DiscoveryItem", back_populates="visual_content")

    def __repr__(self) -> str:
        frame_info = f"frame={self.frame_number}" if self.frame_number is not None else "photo"
        return f"<VisualContent(id={self.id}, discovery_item_id={self.discovery_item_id}, {frame_info})>"
