"""Email message model for email discovery items."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class EmailMessage(Base):
    """
    EmailMessage model for storing email content.

    This model stores email messages with sender, recipients, subject, body,
    and attachment information. Supports email threading.
    One-to-one relationship with DiscoveryItem for EMAIL type items.
    """

    __tablename__ = "email_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    discovery_item_id = Column(
        Integer,
        ForeignKey("discovery_items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One-to-one relationship
        index=True
    )
    sender = Column(String(255), nullable=False, index=True)  # Email sender address
    recipients = Column(JSON, nullable=False)  # Array of recipient email addresses (to, cc, bcc)
    subject = Column(String(512), nullable=True, index=True)  # Email subject line
    body_text = Column(Text, nullable=True)  # Email body content
    timestamp = Column(DateTime, nullable=False, index=True)  # When email was sent
    attachments = Column(JSON, nullable=True)  # Array of attachment metadata
    thread_id = Column(String(255), nullable=True, index=True)  # ID for grouping email threads
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    discovery_item = relationship("DiscoveryItem", back_populates="email")

    def __repr__(self) -> str:
        return f"<EmailMessage(id={self.id}, sender='{self.sender}', subject='{self.subject}')>"
