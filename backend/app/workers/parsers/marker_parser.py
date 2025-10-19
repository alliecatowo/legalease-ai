"""
Marker PDF Parser

Modern PDF parser using marker-pdf with VLM support for highest accuracy.
Optimized for legal documents with complex tables, forms, and multi-column layouts.

Key Features:
- Gemini 2.0 VLM integration for superior table/form handling
- Hierarchical block structure (24 block types)
- Character-level bbox support
- GPU acceleration (CUDA)
- Progress tracking
"""

import logging
import os
import time
import tempfile
import gc
from typing import Dict, Any, List, Optional
from pathlib import Path

from app.workers.parsers.base import (
    DocumentParser,
    ParsedDocument,
    ParsedPage,
    ParserType,
    ParsingError,
)
from app.core.retry import retry_gemini

logger = logging.getLogger(__name__)


class MarkerParser(DocumentParser):
    """
    Marker-based PDF parser with VLM support.

    Uses the modern Marker API (v1.10+) with PdfConverter class.
    Supports GPU acceleration and LLM enhancement for maximum accuracy.

    Configuration (via environment variables):
        GOOGLE_API_KEY: Gemini API key for VLM mode
        TORCH_DEVICE: cuda/cpu/mps (auto-detected if not set)
        INFERENCE_RAM: Available GPU VRAM in GB (default: 8)
        VRAM_PER_TASK: VRAM per conversion task (default: 4.5)

    For RTX 3070 Ti (8GB):
        - batch_multiplier: 2 (default, safe)
        - Expected time: ~10s per 250 pages without LLM
        - Expected time: ~2-5 min per 250 pages with LLM
    """

    def __init__(
        self,
        use_llm: bool = True,
        gemini_api_key: Optional[str] = None,
        gemini_model_name: str = "gemini-2.0-flash",
        batch_multiplier: int = 2,
        output_format: str = "json",
        debug: bool = False,
    ):
        """
        Initialize Marker parser with VLM configuration.

        Args:
            use_llm: Enable LLM enhancement for tables/forms (highly recommended for legal docs)
            gemini_api_key: Gemini API key (or set GOOGLE_API_KEY env var)
            gemini_model_name: Gemini model (default: gemini-2.0-flash)
            batch_multiplier: Batch size multiplier (1-2 for 8GB GPU, 3-4 for 16GB+)
            output_format: Output format (json/markdown/html/chunks)
            debug: Enable debug mode with intermediate outputs
        """
        self.use_llm = use_llm
        self.gemini_api_key = gemini_api_key or os.getenv("GOOGLE_API_KEY")
        self.gemini_model_name = gemini_model_name
        self.batch_multiplier = batch_multiplier
        self.output_format = output_format
        self.debug = debug

        # Validate configuration
        if use_llm and not self.gemini_api_key:
            raise ValueError(
                "Gemini API key required for LLM mode. "
                "Set GOOGLE_API_KEY environment variable or pass gemini_api_key parameter."
            )

        # Configure GPU
        self._configure_gpu()

        # Initialize converter (lazy-loaded)
        self._converter = None
        self._model_dict = None

        logger.info(
            f"Initialized MarkerParser (LLM={use_llm}, batch_multiplier={batch_multiplier}, "
            f"format={output_format})"
        )

    def _configure_gpu(self):
        """Configure GPU settings for optimal performance."""
        import torch

        # Auto-detect GPU
        if not os.getenv("TORCH_DEVICE"):
            if torch.cuda.is_available():
                os.environ["TORCH_DEVICE"] = "cuda"
                device_name = torch.cuda.get_device_name(0)
                vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
                logger.info(f"GPU detected: {device_name} ({vram_gb:.1f}GB VRAM)")

                # Set VRAM limits if not already set
                if not os.getenv("INFERENCE_RAM"):
                    os.environ["INFERENCE_RAM"] = str(int(vram_gb))
                if not os.getenv("VRAM_PER_TASK"):
                    os.environ["VRAM_PER_TASK"] = "4.5"  # Conservative default
            else:
                os.environ["TORCH_DEVICE"] = "cpu"
                logger.info("No GPU detected - using CPU")

    def _get_converter(self):
        """
        Get or create Marker converter with proper configuration.

        Lazy-loads the converter to avoid loading heavy models until needed.
        Uses the modern Marker API (PdfConverter) introduced in v1.0+.
        """
        if self._converter is not None:
            return self._converter

        try:
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict
            from marker.config.parser import ConfigParser
        except ImportError as e:
            raise ImportError(
                f"Failed to import marker-pdf: {e}. "
                "Install with: uv add marker-pdf"
            ) from e

        # Build configuration
        config = {
            "output_format": self.output_format,
            "batch_multiplier": self.batch_multiplier,
        }

        if self.use_llm:
            config.update({
                "use_llm": True,
                "llm_service": "marker.services.gemini.GoogleGeminiService",
                "gemini_api_key": self.gemini_api_key,
                "gemini_model_name": self.gemini_model_name,
            })

        if self.debug:
            config["debug"] = True

        # Load models (heavy operation - only once)
        logger.info("Loading Marker models (this may take a minute)...")
        self._model_dict = create_model_dict()
        logger.info("Marker models loaded successfully")

        # Create converter
        config_parser = ConfigParser(config)

        self._converter = PdfConverter(
            config=config_parser.generate_config_dict(),
            artifact_dict=self._model_dict,
            llm_service=config_parser.get_llm_service() if self.use_llm else None,
        )

        return self._converter

    @retry_gemini
    def parse(
        self,
        file_content: bytes,
        filename: str,
        **kwargs
    ) -> ParsedDocument:
        """
        Parse PDF document using Marker with VLM.

        Args:
            file_content: Raw PDF bytes
            filename: Original filename
            **kwargs: Additional options (ignored for now)

        Returns:
            ParsedDocument with complete parsing results

        Raises:
            ParsingError: If parsing fails
            ValueError: If input is invalid
        """
        start_time = time.time()
        tmp_path = None

        try:
            # Validate input
            self._validate_file_content(file_content)
            file_ext = self._get_file_extension(filename)

            if not self.supports_format(file_ext):
                raise ValueError(f"Unsupported file format: {file_ext}")

            # Log GPU memory before processing
            self._log_gpu_memory("Before parsing")

            # Write to temporary file (Marker requires file path)
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name

            logger.info(f"Parsing {filename} ({len(file_content)/1024:.1f}KB)")

            # Get converter
            converter = self._get_converter()

            # Convert document
            rendered = converter(tmp_path)

            # Extract structured data
            pages = self._extract_pages(rendered)
            full_text = self._extract_full_text(rendered)
            metadata = self._extract_metadata(rendered, filename)

            processing_time = time.time() - start_time

            # Log GPU memory after processing
            self._log_gpu_memory("After parsing")

            # Create result
            result = ParsedDocument(
                text=full_text,
                pages=pages,
                metadata=metadata,
                parser_type=ParserType.MARKER,
                processing_time=processing_time,
            )

            logger.info(
                f"Successfully parsed {filename}: "
                f"{result.page_count} pages, {result.content_page_count} with content "
                f"({processing_time:.2f}s)"
            )

            return result

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Failed to parse {filename} after {processing_time:.2f}s: {e}", exc_info=True)

            # Wrap in ParsingError for consistent error handling
            if isinstance(e, ParsingError):
                raise
            raise ParsingError(f"Marker parsing failed: {e}") from e

        finally:
            # Cleanup temporary file
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {tmp_path}: {e}")

            # GPU memory cleanup
            self._cleanup_gpu_memory()

    def _extract_pages(self, rendered: Any) -> List[ParsedPage]:
        """
        Extract pages from Marker's rendered output.

        Marker returns a hierarchical block structure. Pages are blocks with
        block_type="Page" containing child blocks (Text, Table, Figure, etc.).

        Args:
            rendered: Marker rendered output

        Returns:
            List of ParsedPage objects
        """
        pages = []

        # Handle different output formats
        if self.output_format == "json":
            pages = self._extract_pages_from_json(rendered)
        elif self.output_format == "markdown":
            pages = self._extract_pages_from_markdown(rendered)
        else:
            # Default: treat as JSON structure
            pages = self._extract_pages_from_json(rendered)

        return pages

    def _extract_pages_from_json(self, rendered: Any) -> List[ParsedPage]:
        """
        Extract pages from JSON output format.

        JSON format is a tree with leaf nodes as blocks.
        Pages are top-level blocks with block_type="Page".
        """
        from marker.schema import BlockTypes

        pages = []
        page_num = 1

        # Rendered is the document tree
        if not hasattr(rendered, 'children'):
            logger.warning("Rendered document has no children - returning empty pages")
            return pages

        # Iterate through top-level pages
        for page_block in rendered.children:
            # Skip if not a page block
            if not hasattr(page_block, 'block_type'):
                continue

            # Extract page data
            page_text = self._extract_block_text(page_block)
            blocks = self._extract_blocks(page_block)
            bboxes = self._extract_bboxes(page_block)

            # Create ParsedPage
            parsed_page = ParsedPage(
                page_number=page_num,
                text=page_text,
                blocks=blocks,
                bboxes=bboxes,
                metadata={
                    "block_type": str(page_block.block_type) if hasattr(page_block, 'block_type') else "Page",
                    "block_count": len(blocks),
                    "bbox_count": len(bboxes),
                }
            )

            pages.append(parsed_page)
            page_num += 1

        return pages

    def _extract_pages_from_markdown(self, rendered: Any) -> List[ParsedPage]:
        """
        Extract pages from markdown output format.

        Markdown format includes text with metadata.
        Use metadata to reconstruct page boundaries.
        """
        try:
            from marker.output import text_from_rendered

            # Extract text and metadata
            text, metadata, images = text_from_rendered(rendered)

            # Try to extract page statistics from metadata
            page_stats = metadata.get("page_stats", [])

            if not page_stats:
                # Fallback: create single page
                logger.warning("No page stats in metadata - creating single page")
                return [
                    ParsedPage(
                        page_number=1,
                        text=text,
                        blocks=[],
                        bboxes=[],
                        metadata=metadata,
                    )
                ]

            # Create pages from stats
            pages = []
            for idx, stats in enumerate(page_stats):
                page_num = idx + 1
                # Text segmentation would require more metadata
                # For now, store reference to full text
                pages.append(
                    ParsedPage(
                        page_number=page_num,
                        text="",  # Would need text offsets from Marker
                        blocks=[],
                        bboxes=[],
                        metadata=stats,
                    )
                )

            return pages

        except Exception as e:
            logger.error(f"Failed to extract pages from markdown: {e}")
            return []

    def _extract_block_text(self, block: Any) -> str:
        """
        Recursively extract text from a block and its children.

        Args:
            block: Marker block object

        Returns:
            Combined text string
        """
        text_parts = []

        # Get block's own text
        if hasattr(block, 'text') and block.text:
            text_parts.append(block.text)

        # Get children's text recursively
        if hasattr(block, 'children') and block.children:
            for child in block.children:
                child_text = self._extract_block_text(child)
                if child_text:
                    text_parts.append(child_text)

        return "\n".join(text_parts)

    def _extract_blocks(self, page_block: Any) -> List[Dict[str, Any]]:
        """
        Extract all blocks from a page.

        Args:
            page_block: Page block object

        Returns:
            List of block dictionaries
        """
        blocks = []

        if not hasattr(page_block, 'children'):
            return blocks

        for child in page_block.children:
            block_dict = {
                "id": getattr(child, 'id', None),
                "block_type": str(child.block_type) if hasattr(child, 'block_type') else "Unknown",
                "text": getattr(child, 'text', ''),
            }

            # Add polygon if available
            if hasattr(child, 'polygon') and child.polygon:
                block_dict["polygon"] = child.polygon

            # Add HTML representation if available
            if hasattr(child, 'html') and child.html:
                block_dict["html"] = child.html

            blocks.append(block_dict)

        return blocks

    def _extract_bboxes(self, page_block: Any) -> List[Dict[str, Any]]:
        """
        Extract bounding boxes from page block.

        Args:
            page_block: Page block object

        Returns:
            List of bbox dictionaries
        """
        bboxes = []

        if not hasattr(page_block, 'children'):
            return bboxes

        for child in page_block.children:
            if hasattr(child, 'polygon') and child.polygon:
                bbox = {
                    "block_id": getattr(child, 'id', None),
                    "type": str(child.block_type) if hasattr(child, 'block_type') else "Unknown",
                    "polygon": child.polygon,
                    "text": getattr(child, 'text', ''),
                }
                bboxes.append(bbox)

        return bboxes

    def _extract_full_text(self, rendered: Any) -> str:
        """
        Extract full document text from rendered output.

        Args:
            rendered: Marker rendered output

        Returns:
            Complete document text
        """
        if self.output_format == "markdown":
            try:
                from marker.output import text_from_rendered
                text, _, _ = text_from_rendered(rendered)
                return text
            except Exception as e:
                logger.error(f"Failed to extract markdown text: {e}")
                return ""

        # For JSON format, concatenate all block text
        return self._extract_block_text(rendered)

    def _extract_metadata(self, rendered: Any, filename: str) -> Dict[str, Any]:
        """
        Extract document metadata.

        Args:
            rendered: Marker rendered output
            filename: Original filename

        Returns:
            Metadata dictionary
        """
        import torch

        metadata = {
            "filename": filename,
            "parser": "Marker",
            "parser_version": "1.10+",
            "output_format": self.output_format,
            "used_llm": self.use_llm,
            "device": os.getenv("TORCH_DEVICE", "cpu"),
        }

        # Add GPU info if available
        if torch.cuda.is_available():
            metadata["gpu_name"] = torch.cuda.get_device_name(0)
            metadata["gpu_vram_gb"] = torch.cuda.get_device_properties(0).total_memory / 1e9

        # Extract table of contents if available
        if hasattr(rendered, 'table_of_contents'):
            metadata["table_of_contents"] = rendered.table_of_contents

        return metadata

    def _log_gpu_memory(self, stage: str):
        """Log GPU memory usage."""
        try:
            import torch

            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated() / 1024**3
                reserved = torch.cuda.memory_reserved() / 1024**3
                logger.info(
                    f"GPU Memory ({stage}): {allocated:.2f}GB allocated, "
                    f"{reserved:.2f}GB reserved"
                )
        except Exception as e:
            logger.debug(f"Failed to log GPU memory: {e}")

    def _cleanup_gpu_memory(self):
        """Aggressive GPU memory cleanup."""
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                gc.collect()
                logger.debug("GPU memory cleaned up")
        except Exception as e:
            logger.debug(f"Failed to cleanup GPU memory: {e}")

    def validate(self, file_content: bytes, filename: str) -> bool:
        """
        Validate if this parser can handle the document.

        Args:
            file_content: Raw document bytes
            filename: Original filename

        Returns:
            True if parser can handle this document
        """
        try:
            self._validate_file_content(file_content)
            file_ext = self._get_file_extension(filename)
            return self.supports_format(file_ext)
        except Exception as e:
            logger.debug(f"Validation failed for {filename}: {e}")
            return False

    def supports_format(self, format: str) -> bool:
        """
        Check if parser supports a specific file format.

        Args:
            format: File extension (e.g., '.pdf', '.docx')

        Returns:
            True if format is supported
        """
        # Marker supports multiple formats, but we focus on PDF for now
        supported = ['.pdf']
        return format.lower() in supported

    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported file formats.

        Returns:
            List of file extensions
        """
        return ['.pdf']

    def get_parser_info(self) -> Dict[str, Any]:
        """
        Get information about this parser.

        Returns:
            Dictionary with parser metadata
        """
        import torch

        return {
            "parser_type": "MarkerParser",
            "marker_version": "1.10+",
            "supported_formats": self.get_supported_formats(),
            "use_llm": self.use_llm,
            "llm_service": "Google Gemini" if self.use_llm else None,
            "batch_multiplier": self.batch_multiplier,
            "output_format": self.output_format,
            "device": os.getenv("TORCH_DEVICE", "cpu"),
            "cuda_available": torch.cuda.is_available(),
        }

    def __del__(self):
        """Cleanup resources on deletion."""
        self._cleanup_gpu_memory()
