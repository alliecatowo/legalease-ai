"""
Document Parsers

Modular, class-based document parsing interfaces and implementations.
Supports multiple parser backends (Marker, Docling) with a unified interface.
"""

from app.workers.parsers.base import (
    DocumentParser,
    ParsedDocument,
    ParsedPage,
    ParserType,
    ParsingError,
)
from app.workers.parsers.marker_parser import MarkerParser

__all__ = [
    "DocumentParser",
    "ParsedDocument",
    "ParsedPage",
    "ParserType",
    "ParsingError",
    "MarkerParser",
]
