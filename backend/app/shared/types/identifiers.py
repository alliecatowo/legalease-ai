"""
Type-safe identifier definitions for domain entities.

This module provides NewType wrappers for UUID-based identifiers to ensure
type safety across the application. It also includes the GID (Global Identifier)
class that combines entity type with a unique identifier.

Example:
    >>> case_id = CaseId(uuid.uuid4())
    >>> doc_id = DocumentId(uuid.uuid4())
    >>> # Type checker will catch this error:
    >>> # case = get_case(doc_id)  # Error: Expected CaseId, got DocumentId

    >>> gid = GID.create("case", uuid.uuid4())
    >>> print(gid)
    case:550e8400-e29b-41d4-a716-446655440000
    >>> parsed = GID.parse("case:550e8400-e29b-41d4-a716-446655440000")
    >>> assert parsed.entity_type == "case"
"""

from typing import NewType, Optional, Tuple
from uuid import UUID, uuid4
import re

# Domain entity identifiers using NewType for type safety
# These are still UUIDs at runtime but provide compile-time type checking

CaseId = NewType("CaseId", UUID)
"""Type-safe identifier for Case entities."""

DocumentId = NewType("DocumentId", UUID)
"""Type-safe identifier for Document entities."""

ResearchRunId = NewType("ResearchRunId", UUID)
"""Type-safe identifier for ResearchRun entities."""

FindingId = NewType("FindingId", UUID)
"""Type-safe identifier for Finding entities."""

EntityId = NewType("EntityId", UUID)
"""Type-safe identifier for Entity entities."""

TranscriptionId = NewType("TranscriptionId", UUID)
"""Type-safe identifier for Transcription entities."""

ChunkId = NewType("ChunkId", UUID)
"""Type-safe identifier for Chunk entities."""


class GID:
    """
    Global Identifier combining entity type with a unique ID.

    Format: {entity_type}:{uuid}
    Example: case:550e8400-e29b-41d4-a716-446655440000

    This is useful for:
    - Multi-tenant systems where IDs need context
    - API responses that include entity type
    - Event sourcing and message queues
    - Cross-service references

    Attributes:
        entity_type: The type of entity (e.g., "case", "document")
        id: The unique identifier (UUID)

    Example:
        >>> gid = GID.create("case", uuid.uuid4())
        >>> print(gid)
        case:550e8400-e29b-41d4-a716-446655440000

        >>> gid_str = str(gid)
        >>> parsed = GID.parse(gid_str)
        >>> assert parsed.entity_type == "case"
        >>> assert isinstance(parsed.id, UUID)

        >>> # Validate format
        >>> GID.is_valid("case:550e8400-e29b-41d4-a716-446655440000")
        True
        >>> GID.is_valid("invalid-format")
        False
    """

    # Pattern: lowercase entity type, colon, standard UUID format
    _PATTERN = re.compile(
        r"^([a-z_]+):([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$",
        re.IGNORECASE
    )

    def __init__(self, entity_type: str, id: UUID):
        """
        Initialize a GID.

        Args:
            entity_type: The entity type (lowercase, underscores allowed)
            id: The unique identifier

        Raises:
            ValueError: If entity_type contains invalid characters
        """
        if not re.match(r"^[a-z_]+$", entity_type):
            raise ValueError(
                f"Invalid entity_type '{entity_type}'. "
                "Must contain only lowercase letters and underscores."
            )
        self.entity_type = entity_type
        self.id = id

    def __str__(self) -> str:
        """Return string representation: entity_type:uuid"""
        return f"{self.entity_type}:{self.id}"

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"GID(entity_type='{self.entity_type}', id={self.id})"

    def __eq__(self, other: object) -> bool:
        """Check equality with another GID."""
        if not isinstance(other, GID):
            return NotImplemented
        return self.entity_type == other.entity_type and self.id == other.id

    def __hash__(self) -> int:
        """Make GID hashable for use in sets and dicts."""
        return hash((self.entity_type, self.id))

    @classmethod
    def create(cls, entity_type: str, id: Optional[UUID] = None) -> "GID":
        """
        Create a new GID, generating a UUID if not provided.

        Args:
            entity_type: The entity type
            id: Optional UUID (generates new one if None)

        Returns:
            New GID instance

        Example:
            >>> gid = GID.create("case")  # Auto-generates UUID
            >>> gid = GID.create("document", existing_uuid)
        """
        if id is None:
            id = uuid4()
        return cls(entity_type, id)

    @classmethod
    def parse(cls, gid_str: str) -> "GID":
        """
        Parse a GID string into a GID object.

        Args:
            gid_str: String in format "entity_type:uuid"

        Returns:
            Parsed GID instance

        Raises:
            ValueError: If string format is invalid

        Example:
            >>> gid = GID.parse("case:550e8400-e29b-41d4-a716-446655440000")
            >>> assert gid.entity_type == "case"
        """
        match = cls._PATTERN.match(gid_str)
        if not match:
            raise ValueError(
                f"Invalid GID format: '{gid_str}'. "
                "Expected format: entity_type:uuid (e.g., case:550e8400-e29b-41d4-a716-446655440000)"
            )

        entity_type, uuid_str = match.groups()
        try:
            uuid_obj = UUID(uuid_str)
        except ValueError as e:
            raise ValueError(f"Invalid UUID in GID '{gid_str}': {e}")

        return cls(entity_type.lower(), uuid_obj)

    @classmethod
    def is_valid(cls, gid_str: str) -> bool:
        """
        Check if a string is a valid GID format.

        Args:
            gid_str: String to validate

        Returns:
            True if valid GID format, False otherwise

        Example:
            >>> GID.is_valid("case:550e8400-e29b-41d4-a716-446655440000")
            True
            >>> GID.is_valid("invalid")
            False
        """
        if not isinstance(gid_str, str):
            return False
        return cls._PATTERN.match(gid_str) is not None


def generate_id() -> UUID:
    """
    Generate a new UUID v4 identifier.

    Returns:
        New UUID v4

    Example:
        >>> case_id = CaseId(generate_id())
        >>> doc_id = DocumentId(generate_id())
    """
    return uuid4()


def parse_gid(gid_str: str) -> Tuple[str, UUID]:
    """
    Parse a GID string and return entity type and UUID.

    This is a convenience function that wraps GID.parse() for
    cases where you need the components directly.

    Args:
        gid_str: String in format "entity_type:uuid"

    Returns:
        Tuple of (entity_type, uuid)

    Raises:
        ValueError: If string format is invalid

    Example:
        >>> entity_type, uuid = parse_gid("case:550e8400-e29b-41d4-a716-446655440000")
        >>> assert entity_type == "case"
        >>> assert isinstance(uuid, UUID)
    """
    gid = GID.parse(gid_str)
    return gid.entity_type, gid.id


def is_valid_gid(gid_str: str) -> bool:
    """
    Check if a string is a valid GID format.

    Convenience function that wraps GID.is_valid().

    Args:
        gid_str: String to validate

    Returns:
        True if valid GID format, False otherwise

    Example:
        >>> is_valid_gid("case:550e8400-e29b-41d4-a716-446655440000")
        True
        >>> is_valid_gid("invalid")
        False
    """
    return GID.is_valid(gid_str)
