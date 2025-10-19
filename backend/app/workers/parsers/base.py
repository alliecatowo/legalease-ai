"""
Base Document Parser Interface

Defines abstract base classes and data structures for document parsing.
All parsers (Marker, Docling, etc.) must implement the DocumentParser interface.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ParserType(str, Enum):
    """Supported parser backends."""
    MARKER = "marker"


class ParsingError(Exception):
    """Custom exception for parsing errors."""
    pass


@dataclass
class ParsedPage:
    """
    Represents a single parsed page from a document.

    Attributes:
        page_number: 1-indexed page number
        text: Full text content of the page
        blocks: List of content blocks (paragraphs, tables, images, etc.)
                Format varies by parser but includes bbox and type info
        bboxes: List of bounding boxes for visual highlighting
        metadata: Page-specific metadata (dimensions, rotation, etc.)
    """
    page_number: int
    text: str
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    bboxes: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate page data after initialization."""
        if self.page_number < 1:
            raise ValueError(f"Page number must be >= 1, got {self.page_number}")

    @property
    def char_count(self) -> int:
        """Get character count for this page."""
        return len(self.text)

    @property
    def word_count(self) -> int:
        """Get word count for this page."""
        return len(self.text.split())

    @property
    def has_content(self) -> bool:
        """Check if page has meaningful content."""
        return bool(self.text.strip())


@dataclass
class ParsedDocument:
    """
    Complete parsed document result.

    Attributes:
        text: Full document text (all pages concatenated)
        pages: List of parsed pages
        metadata: Document-level metadata
        parser_type: Which parser was used
        processing_time: Time taken to parse (seconds)
        errors: List of non-fatal errors encountered
    """
    text: str
    pages: List[ParsedPage]
    metadata: Dict[str, Any]
    parser_type: ParserType
    processing_time: float = 0.0
    errors: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate document data after initialization."""
        if not self.pages:
            raise ValueError("Document must have at least one page")

    @property
    def page_count(self) -> int:
        """Get total number of pages."""
        return len(self.pages)

    @property
    def total_char_count(self) -> int:
        """Get total character count across all pages."""
        return sum(page.char_count for page in self.pages)

    @property
    def total_word_count(self) -> int:
        """Get total word count across all pages."""
        return sum(page.word_count for page in self.pages)

    @property
    def pages_with_content(self) -> List[ParsedPage]:
        """Get only pages that have content."""
        return [page for page in self.pages if page.has_content]

    @property
    def content_page_count(self) -> int:
        """Get number of pages with actual content."""
        return len(self.pages_with_content)

    def get_page(self, page_number: int) -> Optional[ParsedPage]:
        """
        Get a specific page by number (1-indexed).

        Args:
            page_number: Page number (1-indexed)

        Returns:
            ParsedPage or None if not found
        """
        for page in self.pages:
            if page.page_number == page_number:
                return page
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "page_count": self.page_count,
            "content_page_count": self.content_page_count,
            "total_char_count": self.total_char_count,
            "total_word_count": self.total_word_count,
            "parser_type": self.parser_type.value,
            "processing_time": self.processing_time,
            "metadata": self.metadata,
            "errors": self.errors,
            "pages": [
                {
                    "page_number": page.page_number,
                    "text": page.text,
                    "char_count": page.char_count,
                    "word_count": page.word_count,
                    "has_content": page.has_content,
                    "block_count": len(page.blocks),
                    "bbox_count": len(page.bboxes),
                }
                for page in self.pages
            ],
        }


class DocumentParser(ABC):
    """
    Abstract base class for document parsers.

    All parser implementations (Marker, Docling, etc.) must inherit from this class
    and implement the required methods.
    """

    @abstractmethod
    def parse(
        self,
        file_content: bytes,
        filename: str,
        **kwargs
    ) -> ParsedDocument:
        """
        Parse a document and return structured result.

        Args:
            file_content: Raw bytes of the document
            filename: Original filename (used to determine format)
            **kwargs: Additional parser-specific options

        Returns:
            ParsedDocument with complete parsing results

        Raises:
            ParsingError: If parsing fails
            ValueError: If input is invalid
        """
        pass

    @abstractmethod
    def validate(self, file_content: bytes, filename: str) -> bool:
        """
        Validate if this parser can handle the document.

        Args:
            file_content: Raw bytes of the document
            filename: Original filename

        Returns:
            True if parser can handle this document
        """
        pass

    @abstractmethod
    def supports_format(self, format: str) -> bool:
        """
        Check if parser supports a specific file format.

        Args:
            format: File extension (e.g., '.pdf', '.docx')

        Returns:
            True if format is supported
        """
        pass

    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported file formats.

        Returns:
            List of file extensions (e.g., ['.pdf', '.docx'])
        """
        return []

    def get_parser_info(self) -> Dict[str, Any]:
        """
        Get information about this parser.

        Returns:
            Dictionary with parser metadata
        """
        return {
            "parser_type": self.__class__.__name__,
            "supported_formats": self.get_supported_formats(),
        }

    @staticmethod
    def _get_file_extension(filename: str) -> str:
        """
        Extract file extension from filename.

        Args:
            filename: Name of the file

        Returns:
            Lowercase file extension with dot (e.g., '.pdf')
        """
        return Path(filename).suffix.lower()

    @staticmethod
    def _validate_file_content(file_content: bytes) -> None:
        """
        Validate that file content is not empty.

        Args:
            file_content: File bytes

        Raises:
            ValueError: If file content is empty
        """
        if not file_content:
            raise ValueError("File content is empty")
        if len(file_content) == 0:
            raise ValueError("File size is 0 bytes")
