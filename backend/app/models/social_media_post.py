"""Social media post model for social media discovery items."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class SocialMediaPost(Base):
    """
    SocialMediaPost model for storing social media content.

    This model stores social media posts extracted from various platforms
    (Snapchat, Instagram, Facebook, etc.) with metadata about the post,
    author, and engagement metrics.
    One-to-one relationship with DiscoveryItem for SOCIAL_POST type items.
    """

    __tablename__ = "social_media_posts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    discovery_item_id = Column(
        Integer,
        ForeignKey("discovery_items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One-to-one relationship
        index=True
    )
    platform = Column(String(100), nullable=False, index=True)  # snapchat, instagram, facebook, twitter, tiktok, etc.
    author = Column(String(255), nullable=True, index=True)  # Username or display name
    post_text = Column(Text, nullable=True)  # Text content of the post
    post_timestamp = Column(DateTime, nullable=True, index=True)  # When the post was created
    engagement_metrics = Column(JSON, nullable=True)  # likes, shares, comments, views, etc.
    thread_id = Column(String(255), nullable=True, index=True)  # ID for grouping related posts/comments
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    discovery_item = relationship("DiscoveryItem", back_populates="social_post")

    def __repr__(self) -> str:
        return f"<SocialMediaPost(id={self.id}, platform='{self.platform}', author='{self.author}')>"
