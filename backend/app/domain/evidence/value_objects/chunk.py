"""
Chunk value object for the Evidence domain.

Represents a segmented piece of text with position, type,
and embeddings metadata for retrieval and analysis.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any


class ChunkType(str, Enum):
    """Type of content chunk."""

    PARAGRAPH = "PARAGRAPH"
    PAGE = "PAGE"
    SECTION = "SECTION"
    HEADING = "HEADING"
    TABLE = "TABLE"
    LIST = "LIST"
    CAPTION = "CAPTION"
    FOOTNOTE = "FOOTNOTE"
    SEGMENT = "SEGMENT"  # For transcript segments
    MESSAGE = "MESSAGE"  # For communication messages
    OTHER = "OTHER"


@dataclass(frozen=True)
class EmbeddingsMetadata:
    """
    Immutable metadata about chunk embeddings.

    Attributes:
        model: Name of the embeddings model used
        dimension: Dimensionality of the embedding vector
        indexed: Whether chunk has been indexed in vector store
        collection_name: Optional name of the vector store collection
    """

    model: str
    dimension: int
    indexed: bool = False
    collection_name: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate embeddings metadata invariants."""
        if self.dimension < 1:
            raise ValueError(f"Dimension must be >= 1, got {self.dimension}")


@dataclass(frozen=True)
class Chunk:
    """
    Immutable chunk value object.

    Represents a segmented piece of text from a document, transcript,
    or communication with positioning and metadata for retrieval.

    Attributes:
        text: The text content of the chunk
        chunk_type: Type of chunk (paragraph, page, etc.)
        position: Sequential position in the source (0-indexed)
        metadata: Additional metadata (e.g., page number, timestamps)
        embeddings_metadata: Optional metadata about embeddings

    Example:
        >>> chunk = Chunk(
        ...     text="The contract was signed on March 15, 2024 by both parties.",
        ...     chunk_type=ChunkType.PARAGRAPH,
        ...     position=42,
        ...     metadata={"page": 5, "paragraph": 2},
        ...     embeddings_metadata=EmbeddingsMetadata(
        ...         model="sentence-transformers/all-MiniLM-L6-v2",
        ...         dimension=384,
        ...         indexed=True,
        ...         collection_name="case_documents",
        ...     ),
        ... )
        >>> chunk.chunk_type
        <ChunkType.PARAGRAPH: 'PARAGRAPH'>
        >>> chunk.is_indexed()
        True
        >>> chunk.word_count()
        12

    Invariants:
        - text must not be empty
        - position must be >= 0
        - metadata keys should follow naming conventions
    """

    text: str
    chunk_type: ChunkType
    position: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    embeddings_metadata: Optional[EmbeddingsMetadata] = None

    def __post_init__(self) -> None:
        """Validate chunk invariants."""
        if not self.text or not self.text.strip():
            raise ValueError("Chunk text cannot be empty")
        if self.position < 0:
            raise ValueError(f"Position must be >= 0, got {self.position}")

    def word_count(self) -> int:
        """
        Calculate the number of words in the chunk.

        Returns:
            Word count
        """
        return len(self.text.split())

    def char_count(self) -> int:
        """
        Calculate the number of characters in the chunk.

        Returns:
            Character count
        """
        return len(self.text)

    def is_indexed(self) -> bool:
        """
        Check if chunk has been indexed in a vector store.

        Returns:
            True if indexed, False otherwise
        """
        return (
            self.embeddings_metadata is not None
            and self.embeddings_metadata.indexed
        )

    def has_metadata(self, key: str) -> bool:
        """
        Check if chunk has a specific metadata field.

        Args:
            key: Metadata key to check

        Returns:
            True if key exists in metadata
        """
        return key in self.metadata

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get a metadata value.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)

    def get_page_number(self) -> Optional[int]:
        """
        Get the page number if available in metadata.

        Returns:
            Page number or None
        """
        return self.metadata.get("page")

    def get_preview(self, max_length: int = 100) -> str:
        """
        Get a preview of the chunk text.

        Args:
            max_length: Maximum length of preview

        Returns:
            Shortened text with ellipsis if truncated
        """
        if len(self.text) <= max_length:
            return self.text
        return self.text[:max_length - 3] + "..."
