"""Call log model for phone call discovery items."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base


class CallType(str, PyEnum):
    """Call type enumeration."""

    INCOMING = "INCOMING"
    OUTGOING = "OUTGOING"
    MISSED = "MISSED"
    VOICEMAIL = "VOICEMAIL"


class CallLog(Base):
    """
    CallLog model for storing phone call records.

    This model stores call log entries with caller/recipient information,
    duration, and type. Can optionally link to an associated audio recording.
    One-to-one relationship with DiscoveryItem for CALL_LOG type items.
    """

    __tablename__ = "call_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    discovery_item_id = Column(
        Integer,
        ForeignKey("discovery_items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One-to-one relationship
        index=True
    )
    caller = Column(String(255), nullable=False, index=True)  # Caller phone number or ID
    recipient = Column(String(255), nullable=False, index=True)  # Recipient phone number or ID
    duration = Column(Integer, nullable=False, default=0)  # Call duration in seconds
    timestamp = Column(DateTime, nullable=False, index=True)  # When call occurred
    call_type = Column(
        Enum(CallType, native_enum=True, create_constraint=True),
        nullable=False,
        index=True
    )
    associated_audio_id = Column(
        Integer,
        ForeignKey("discovery_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )  # Link to associated audio recording if available
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    discovery_item = relationship(
        "DiscoveryItem",
        back_populates="call_log",
        foreign_keys=[discovery_item_id]
    )
    associated_audio = relationship(
        "DiscoveryItem",
        foreign_keys=[associated_audio_id]
    )

    def __repr__(self) -> str:
        return f"<CallLog(id={self.id}, caller='{self.caller}', recipient='{self.recipient}', type='{self.call_type.value}')>"
