"""
Parser Factory

Factory for creating document parsers with appropriate configuration.
Supports strategy pattern for easy parser switching and testing.
"""

import logging
from typing import Dict, Any, Optional

from app.workers.parsers.base import DocumentParser, ParserType
from app.workers.parsers.marker_parser import MarkerParser

logger = logging.getLogger(__name__)


class ParserFactory:
    """
    Factory for creating document parsers.

    Provides a centralized way to create parsers with proper configuration.
    Currently supports Marker parser for legal document processing.
    """

    @staticmethod
    def create_parser(
        parser_type: ParserType = ParserType.MARKER,
        config: Optional[Dict[str, Any]] = None,
    ) -> DocumentParser:
        """
        Create and configure a parser instance.

        Args:
            parser_type: Type of parser to create
            config: Parser-specific configuration dictionary

        Returns:
            Configured DocumentParser instance

        Raises:
            ValueError: If parser type is unknown

        Example:
            >>> factory = ParserFactory()
            >>> parser = factory.create_parser(
            ...     ParserType.MARKER,
            ...     config={
            ...         "use_llm": True,
            ...         "batch_multiplier": 2,
            ...     }
            ... )
        """
        config = config or {}

        if parser_type == ParserType.MARKER:
            return ParserFactory._create_marker_parser(config)
        else:
            raise ValueError(f"Unknown parser type: {parser_type}")

    @staticmethod
    def _create_marker_parser(config: Dict[str, Any]) -> MarkerParser:
        """
        Create Marker parser with configuration.

        Default configuration for legal documents:
        - use_llm: True (for complex tables/forms)
        - batch_multiplier: 2 (safe for 8GB GPU)
        - output_format: json (for structured data)
        - debug: False

        Args:
            config: Configuration dictionary

        Returns:
            Configured MarkerParser instance
        """
        # Default configuration for legal documents
        default_config = {
            "use_llm": True,  # Critical for legal doc accuracy
            "batch_multiplier": 2,  # Safe for RTX 3070 Ti (8GB)
            "output_format": "json",  # Best for structured extraction
            "debug": False,
        }

        # Merge with provided config (provided config takes precedence)
        final_config = {**default_config, **config}

        logger.info(f"Creating MarkerParser with config: {final_config}")

        return MarkerParser(**final_config)


    @staticmethod
    def create_auto_parser(
        filename: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> DocumentParser:
        """
        Create parser automatically based on file type and requirements.

        Decision logic:
        - PDF: Marker (best for legal documents)
        - DOCX: Docling (when available)
        - Other: Fallback to Marker

        Args:
            filename: Name of file to parse
            config: Parser configuration

        Returns:
            Appropriate DocumentParser instance
        """
        from pathlib import Path

        file_ext = Path(filename).suffix.lower()

        # For now, always use Marker for PDFs (best quality)
        if file_ext == '.pdf':
            parser_type = ParserType.MARKER
            logger.info(f"Auto-selected Marker parser for {filename}")
        else:
            # Default to Marker for unsupported formats
            parser_type = ParserType.MARKER
            logger.warning(
                f"No specific parser for {file_ext}, defaulting to Marker"
            )

        return ParserFactory.create_parser(parser_type, config)

    @staticmethod
    def get_available_parsers() -> Dict[str, bool]:
        """
        Get list of available parsers and their availability.

        Returns:
            Dictionary mapping parser names to availability status
        """
        available = {
            "marker": True,  # Always available (required dependency)
        }

        return available

    @staticmethod
    def get_recommended_parser(
        document_type: str = "legal"
    ) -> ParserType:
        """
        Get recommended parser for a specific document type.

        Args:
            document_type: Type of document (legal/financial/general)

        Returns:
            Recommended ParserType
        """
        recommendations = {
            "legal": ParserType.MARKER,  # Best for legal docs
            "financial": ParserType.MARKER,  # Good for tables
            "general": ParserType.MARKER,  # Default
        }

        return recommendations.get(document_type, ParserType.MARKER)


# Convenience function for quick parser creation
def create_parser(
    parser_type: Optional[ParserType] = None,
    filename: Optional[str] = None,
    **kwargs
) -> DocumentParser:
    """
    Convenience function to create a parser.

    Args:
        parser_type: Specific parser type (optional)
        filename: Filename for auto-detection (optional)
        **kwargs: Parser configuration

    Returns:
        Configured DocumentParser instance

    Example:
        >>> # Create Marker parser with defaults
        >>> parser = create_parser()
        >>>
        >>> # Create Marker parser with custom config
        >>> parser = create_parser(use_llm=False, batch_multiplier=1)
        >>>
        >>> # Auto-detect parser from filename
        >>> parser = create_parser(filename="contract.pdf")
    """
    factory = ParserFactory()

    if parser_type:
        return factory.create_parser(parser_type, kwargs)
    elif filename:
        return factory.create_auto_parser(filename, kwargs)
    else:
        # Default to Marker
        return factory.create_parser(ParserType.MARKER, kwargs)
