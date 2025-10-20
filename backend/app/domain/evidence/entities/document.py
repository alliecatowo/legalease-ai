"""
Document entity for the Evidence domain.

Represents a legal document within a case, including uploaded files,
exhibits, pleadings, and other evidence materials.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID


class DocumentStatus(str, Enum):
    """Document processing status."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DocumentType(str, Enum):
    """Type of document in the legal context."""

    PLEADING = "PLEADING"
    EXHIBIT = "EXHIBIT"
    CORRESPONDENCE = "CORRESPONDENCE"
    DISCOVERY = "DISCOVERY"
    COURT_ORDER = "COURT_ORDER"
    BRIEF = "BRIEF"
    MOTION = "MOTION"
    DEPOSITION = "DEPOSITION"
    CONTRACT = "CONTRACT"
    EVIDENCE = "EVIDENCE"
    OTHER = "OTHER"


@dataclass
class Document:
    """
    Document entity representing an uploaded file in a case.

    This is a domain entity with identity (id) and business logic.
    Documents can be processed to extract text, entities, and metadata.

    Attributes:
        id: Unique identifier for the document
        case_id: ID of the case this document belongs to
        filename: Original filename of the uploaded document
        file_type: Classification of document type (pleading, exhibit, etc.)
        mime_type: MIME type of the file (e.g., 'application/pdf')
        size: File size in bytes
        status: Current processing status
        metadata: Additional metadata extracted during processing
        created_at: When the document was uploaded
        updated_at: When the document was last modified
        file_path: Storage path or object key
        page_count: Number of pages (for paginated documents)
        checksum: SHA-256 checksum for integrity verification

    Example:
        >>> doc = Document(
        ...     id=UUID('...'),
        ...     case_id=UUID('...'),
        ...     filename="complaint.pdf",
        ...     file_type=DocumentType.PLEADING,
        ...     mime_type="application/pdf",
        ...     size=1024000,
        ...     status=DocumentStatus.PENDING,
        ... )
        >>> doc.mark_processing()
        >>> assert doc.status == DocumentStatus.PROCESSING
    """

    id: UUID
    case_id: UUID
    filename: str
    file_type: DocumentType
    mime_type: str
    size: int
    status: DocumentStatus
    created_at: datetime
    file_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    updated_at: Optional[datetime] = None
    page_count: Optional[int] = None
    checksum: Optional[str] = None

    def mark_processing(self) -> None:
        """Mark document as currently being processed."""
        self.status = DocumentStatus.PROCESSING
        self.updated_at = datetime.utcnow()

    def mark_completed(self, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Mark document as successfully processed.

        Args:
            metadata: Optional metadata to merge with existing metadata
        """
        self.status = DocumentStatus.COMPLETED
        self.updated_at = datetime.utcnow()
        if metadata:
            self.metadata.update(metadata)

    def mark_failed(self, error: str) -> None:
        """
        Mark document processing as failed.

        Args:
            error: Error message describing the failure
        """
        self.status = DocumentStatus.FAILED
        self.updated_at = datetime.utcnow()
        self.metadata["error"] = error
        self.metadata["failed_at"] = datetime.utcnow().isoformat()

    def is_processed(self) -> bool:
        """Check if document has been successfully processed."""
        return self.status == DocumentStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if document processing failed."""
        return self.status == DocumentStatus.FAILED

    def add_metadata(self, key: str, value: Any) -> None:
        """
        Add or update a metadata field.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
        self.updated_at = datetime.utcnow()

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a metadata field.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)

    def __eq__(self, other: object) -> bool:
        """Documents are equal if they have the same ID."""
        if not isinstance(other, Document):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on document ID."""
        return hash(self.id)
