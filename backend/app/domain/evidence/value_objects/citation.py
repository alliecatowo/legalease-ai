"""
Citation value object for the Evidence domain.

Represents a reference to a specific location within evidence,
including source identification, location, and context.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union
from uuid import UUID

from .locator import Locator, PageLocator, TimecodeLocator, MessageLocator, BoundingBox


class SourceType(str, Enum):
    """Type of evidence source."""

    DOCUMENT = "DOCUMENT"
    TRANSCRIPT = "TRANSCRIPT"
    COMMUNICATION = "COMMUNICATION"
    FORENSIC_REPORT = "FORENSIC_REPORT"
    CHUNK = "CHUNK"
    OTHER = "OTHER"


@dataclass(frozen=True)
class Citation:
    """
    Immutable citation value object.

    A citation pinpoints a specific piece of evidence within a source,
    including the source identifier, type, location, and optional excerpt.

    Attributes:
        source_id: UUID of the source document/transcript/communication
        source_type: Type of the source
        locator: Specific location within the source
        excerpt: Optional text excerpt from the location
        confidence: Optional confidence score for the citation (0.0-1.0)

    Example:
        >>> from uuid import UUID
        >>>
        >>> citation = Citation(
        ...     source_id=UUID('12345678-1234-1234-1234-123456789abc'),
        ...     source_type=SourceType.DOCUMENT,
        ...     locator=PageLocator(page=5, paragraph=2),
        ...     excerpt="The defendant signed the agreement on March 15, 2024.",
        ...     confidence=0.95,
        ... )
        >>> citation.source_type
        <SourceType.DOCUMENT: 'DOCUMENT'>
        >>> citation.is_high_confidence()
        True

    Invariants:
        - source_id must be a valid UUID
        - confidence, if provided, must be between 0.0 and 1.0
        - excerpt should not exceed reasonable length (enforced by application logic)
    """

    source_id: UUID
    source_type: SourceType
    locator: Union[PageLocator, TimecodeLocator, MessageLocator, BoundingBox]
    excerpt: Optional[str] = None
    confidence: Optional[float] = None

    def __post_init__(self) -> None:
        """Validate citation invariants."""
        if self.confidence is not None:
            if not 0.0 <= self.confidence <= 1.0:
                raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """
        Check if citation has high confidence.

        Args:
            threshold: Minimum confidence threshold (default: 0.8)

        Returns:
            True if confidence is above threshold, False otherwise
        """
        return self.confidence is not None and self.confidence >= threshold

    def has_excerpt(self) -> bool:
        """Check if citation includes an excerpt."""
        return self.excerpt is not None and len(self.excerpt.strip()) > 0

    def get_short_excerpt(self, max_length: int = 100) -> Optional[str]:
        """
        Get a shortened version of the excerpt.

        Args:
            max_length: Maximum length of the excerpt

        Returns:
            Shortened excerpt with ellipsis if truncated, or None if no excerpt
        """
        if not self.has_excerpt():
            return None

        assert self.excerpt is not None  # Type narrowing
        if len(self.excerpt) <= max_length:
            return self.excerpt

        return self.excerpt[:max_length - 3] + "..."

    def is_document_citation(self) -> bool:
        """Check if citation references a document."""
        return self.source_type == SourceType.DOCUMENT

    def is_transcript_citation(self) -> bool:
        """Check if citation references a transcript."""
        return self.source_type == SourceType.TRANSCRIPT

    def is_communication_citation(self) -> bool:
        """Check if citation references a communication."""
        return self.source_type == SourceType.COMMUNICATION

    def describe(self) -> str:
        """
        Get a human-readable description of the citation.

        Returns:
            Description including source type and location
        """
        return f"{self.source_type.value} - {self.locator.describe()}"
