"""
Communication entity for the Evidence domain.

Represents digital communications extracted from forensic exports
(e.g., Cellebrite AXIOM), including messages, emails, and chat logs.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID


class CommunicationType(str, Enum):
    """Type of digital communication."""

    SMS = "SMS"
    MMS = "MMS"
    EMAIL = "EMAIL"
    CHAT = "CHAT"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    VOICE_CALL = "VOICE_CALL"
    VIDEO_CALL = "VIDEO_CALL"
    OTHER = "OTHER"


class CommunicationPlatform(str, Enum):
    """Platform where the communication originated."""

    WHATSAPP = "WHATSAPP"
    IMESSAGE = "IMESSAGE"
    TELEGRAM = "TELEGRAM"
    SIGNAL = "SIGNAL"
    FACEBOOK = "FACEBOOK"
    INSTAGRAM = "INSTAGRAM"
    TWITTER = "TWITTER"
    SNAPCHAT = "SNAPCHAT"
    SMS_NATIVE = "SMS_NATIVE"
    EMAIL_NATIVE = "EMAIL_NATIVE"
    SKYPE = "SKYPE"
    SLACK = "SLACK"
    TEAMS = "TEAMS"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Participant:
    """
    Immutable participant in a communication.

    Attributes:
        identifier: Phone number, email, username, or user ID
        name: Display name or contact name
        role: Role in the communication (sender, recipient, etc.)
        metadata: Additional participant metadata
    """

    identifier: str
    name: Optional[str] = None
    role: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Attachment:
    """
    Immutable attachment to a communication.

    Attributes:
        id: Unique attachment identifier
        filename: Original filename
        mime_type: MIME type of the attachment
        size: File size in bytes
        file_path: Storage path or object key
        thumbnail_path: Optional path to thumbnail/preview
        metadata: Additional attachment metadata
    """

    id: str
    filename: str
    mime_type: str
    size: int
    file_path: str
    thumbnail_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Communication:
    """
    Communication entity for digital messages from forensic exports.

    Represents messages, emails, chats, and other digital communications
    extracted from mobile devices or computer systems.

    Attributes:
        id: Unique identifier for the communication
        case_id: ID of the case this communication belongs to
        thread_id: Thread or conversation identifier
        sender: Participant who sent the communication
        participants: All participants in the communication
        timestamp: When the communication was sent/received
        body: Text content of the communication
        attachments: Files attached to the communication
        device_id: Source device identifier
        platform: Platform where communication originated
        communication_type: Type of communication
        created_at: When this record was created
        updated_at: When this record was last modified
        metadata: Additional metadata from forensic export

    Example:
        >>> comm = Communication(
        ...     id=UUID('...'),
        ...     case_id=UUID('...'),
        ...     thread_id="thread_12345",
        ...     sender=Participant(identifier="+1234567890", name="John Doe"),
        ...     participants=[
        ...         Participant(identifier="+1234567890", name="John Doe"),
        ...         Participant(identifier="+0987654321", name="Jane Smith"),
        ...     ],
        ...     timestamp=datetime(2024, 1, 15, 10, 30),
        ...     body="We need to discuss the contract terms.",
        ...     attachments=[],
        ...     device_id="device_001",
        ...     platform=CommunicationPlatform.IMESSAGE,
        ...     communication_type=CommunicationType.SMS,
        ... )
        >>> comm.is_from_sender("+1234567890")
        True
        >>> comm.has_attachments()
        False
    """

    id: UUID
    case_id: UUID
    thread_id: str
    sender: Participant
    participants: List[Participant]
    timestamp: datetime
    body: str
    attachments: List[Attachment]
    device_id: str
    platform: CommunicationPlatform
    communication_type: CommunicationType
    created_at: datetime
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def has_attachments(self) -> bool:
        """Check if communication has attachments."""
        return len(self.attachments) > 0

    def get_attachment_count(self) -> int:
        """Get the number of attachments."""
        return len(self.attachments)

    def is_from_sender(self, identifier: str) -> bool:
        """
        Check if communication is from a specific sender.

        Args:
            identifier: Phone number, email, or username to check

        Returns:
            True if sender matches the identifier
        """
        return self.sender.identifier == identifier

    def has_participant(self, identifier: str) -> bool:
        """
        Check if a specific identifier is a participant.

        Args:
            identifier: Phone number, email, or username to check

        Returns:
            True if identifier is in participants list
        """
        return any(p.identifier == identifier for p in self.participants)

    def get_participant_names(self) -> List[str]:
        """Get list of participant names (excluding None)."""
        return [p.name for p in self.participants if p.name]

    def get_other_participants(self, exclude_identifier: str) -> List[Participant]:
        """
        Get all participants except the specified identifier.

        Args:
            exclude_identifier: Identifier to exclude

        Returns:
            List of participants excluding the specified identifier
        """
        return [p for p in self.participants if p.identifier != exclude_identifier]

    def add_metadata(self, key: str, value: Any) -> None:
        """
        Add or update a metadata field.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
        self.updated_at = datetime.utcnow()

    def __eq__(self, other: object) -> bool:
        """Communications are equal if they have the same ID."""
        if not isinstance(other, Communication):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on communication ID."""
        return hash(self.id)
