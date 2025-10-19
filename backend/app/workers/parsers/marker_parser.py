"""
Marker PDF Parser

Lightweight wrapper around marker-pdf with minimal customisation so we inherit the
library defaults.  The parser converts PDFs into structured data and exposes the
result through our DocumentParser interface.
"""

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
from app.workers.parsers.bbox_utils import normalize_bbox
from app.core.retry import retry_gemini
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class MarkerParser(DocumentParser):
    """
    Thin wrapper around marker-pdf.
    """

    def __init__(
        self,
        use_llm: bool = True,
        gemini_api_key: Optional[str] = None,
        gemini_model_name: str = "gemini-2.0-flash",
        batch_multiplier: int = 1,
        output_format: str = "json",
        debug: bool = False,
    ):
        self.use_llm = use_llm
        self.gemini_api_key = gemini_api_key or os.getenv("GOOGLE_API_KEY")
        self.gemini_model_name = gemini_model_name
        self.batch_multiplier = max(1, batch_multiplier)
        self.output_format = output_format
        self.debug = debug

        if self.use_llm and not self.gemini_api_key:
            raise ValueError(
                "Gemini API key required for LLM mode. "
                "Set GOOGLE_API_KEY environment variable or pass gemini_api_key parameter."
            )

        self._converter = None
        self._model_dict = None

        logger.info(
            "Initialized MarkerParser (LLM=%s, batch_multiplier=%s, format=%s)",
            use_llm,
            self.batch_multiplier,
            output_format,
        )

    def _get_converter(self):
        """Load the marker converter on demand."""
        if self._converter is not None:
            return self._converter

        try:
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict
            from marker.config.parser import ConfigParser
        except ImportError as exc:
            raise ImportError(
                f"Failed to import marker-pdf: {exc}. Install with: uv add marker-pdf"
            ) from exc

        config: Dict[str, Any] = {
            "output_format": self.output_format,
            "batch_multiplier": self.batch_multiplier,
        }

        if self.use_llm:
            config.update(
                {
                    "use_llm": True,
                    "llm_service": "marker.services.gemini.GoogleGeminiService",
                    "gemini_api_key": self.gemini_api_key,
                    "gemini_model_name": self.gemini_model_name,
                }
            )

        if self.debug:
            config["debug"] = True

        if self._model_dict is None:
            logger.info("Loading Marker models (this may take a minute)...")
            self._model_dict = create_model_dict()
            logger.info("Marker models loaded successfully")

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
        **kwargs,
    ) -> ParsedDocument:
        """
        Parse a PDF using marker-pdf.
        """
        start_time = time.time()
        tmp_path = None

        try:
            self._validate_file_content(file_content)
            file_ext = self._get_file_extension(filename)
            if not self.supports_format(file_ext):
                raise ValueError(f"Unsupported file format: {file_ext}")

            self._log_gpu_memory("Before parsing")

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name

            logger.info(
                "Parsing %s (%.1fKB)",
                filename,
                len(file_content) / 1024,
            )

            converter = self._get_converter()
            rendered = converter(tmp_path)

            pages = self._extract_pages(rendered)
            full_text = self._extract_full_text(rendered)
            metadata = self._extract_metadata(rendered, filename)

            processing_time = time.time() - start_time

            self._log_gpu_memory("After parsing")

            result = ParsedDocument(
                text=full_text,
                pages=pages,
                metadata=metadata,
                parser_type=ParserType.MARKER,
                processing_time=processing_time,
            )

            logger.info(
                "Successfully parsed %s: %s pages (%0.2fs)",
                filename,
                result.page_count,
                processing_time,
            )

            return result

        except Exception as exc:
            processing_time = time.time() - start_time
            logger.error(
                "Failed to parse %s after %0.2fs: %s", filename, processing_time, exc, exc_info=True
            )
            if isinstance(exc, ParsingError):
                raise
            raise ParsingError(f"Marker parsing failed: {exc}") from exc

        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception as cleanup_exc:
                    logger.warning("Failed to delete temp file %s: %s", tmp_path, cleanup_exc)

            self._cleanup_gpu_memory()

    def _extract_pages(self, rendered: Any) -> List[ParsedPage]:
        """
        Extract pages from Marker's rendered output.
        """
        pages: List[ParsedPage] = []

        if self.output_format == "json":
            pages = self._extract_pages_from_json(rendered)
        elif self.output_format == "markdown":
            pages = self._extract_pages_from_markdown(rendered)
        else:
            pages = self._extract_pages_from_json(rendered)

        return pages

    def _extract_pages_from_json(self, rendered: Any) -> List[ParsedPage]:
        """
        Extract pages from JSON output format.
        """
        pages: List[ParsedPage] = []
        page_num = 1

        if not hasattr(rendered, "children"):
            logger.warning("Rendered document has no children - returning empty pages")
            return pages

        for page_block in rendered.children:
            if not hasattr(page_block, "block_type"):
                continue

            page_text = self._extract_block_text(page_block)
            blocks = self._extract_blocks(page_block)
            bboxes = self._extract_bboxes(page_block, page_num)

            parsed_page = ParsedPage(
                page_number=page_num,
                text=page_text,
                blocks=blocks,
                bboxes=bboxes,
                metadata={
                    "block_type": str(page_block.block_type)
                    if hasattr(page_block, "block_type")
                    else "Page",
                    "block_count": len(blocks),
                    "bbox_count": len(bboxes),
                },
            )

            pages.append(parsed_page)
            page_num += 1

        return pages

    def _extract_pages_from_markdown(self, rendered: Any) -> List[ParsedPage]:
        try:
            from marker.output import text_from_rendered

            text, metadata, images = text_from_rendered(rendered)
            page_stats = metadata.get("page_stats", [])

            if not page_stats:
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

            pages: List[ParsedPage] = []
            for idx, stats in enumerate(page_stats):
                page_num = idx + 1
                pages.append(
                    ParsedPage(
                        page_number=page_num,
                        text="",
                        blocks=[],
                        bboxes=[],
                        metadata=stats,
                    )
                )

            return pages

        except Exception as exc:
            logger.error("Failed to extract pages from markdown: %s", exc)
            return []

    def _extract_block_text(self, block: Any) -> str:
        text_parts: List[str] = []

        if hasattr(block, "text") and block.text:
            text_parts.append(block.text)

        if hasattr(block, "children") and block.children:
            for child in block.children:
                child_text = self._extract_block_text(child)
                if child_text:
                    text_parts.append(child_text)

        return "\n".join(text_parts)

    def _extract_blocks(self, page_block: Any) -> List[Dict[str, Any]]:
        blocks: List[Dict[str, Any]] = []

        if not hasattr(page_block, "children"):
            return blocks

        for child in page_block.children:
            block_dict: Dict[str, Any] = {
                "id": getattr(child, "id", None),
                "block_type": str(child.block_type) if hasattr(child, "block_type") else "Unknown",
                "text": getattr(child, "text", ""),
            }

            if hasattr(child, "polygon") and child.polygon:
                block_dict["polygon"] = child.polygon

            if hasattr(child, "html") and child.html:
                block_dict["html"] = child.html

            blocks.append(block_dict)

        return blocks

    def _extract_bboxes(self, page_block: Any, page_num: int) -> List[Dict[str, Any]]:
        bboxes: List[Dict[str, Any]] = []

        if not hasattr(page_block, "children"):
            return bboxes

        for child in page_block.children:
            if hasattr(child, "polygon") and child.polygon:
                raw_bbox = {
                    "polygon": child.polygon,
                    "text": getattr(child, "text", ""),
                    "type": str(child.block_type) if hasattr(child, "block_type") else "Unknown",
                    "page": page_num,
                }
                normalized = normalize_bbox(raw_bbox, page_num=page_num, source="marker")
                bboxes.append(normalized)

        return bboxes

    def _extract_full_text(self, rendered: Any) -> str:
        if self.output_format == "markdown":
            try:
                from marker.output import text_from_rendered

                text, _, _ = text_from_rendered(rendered)
                return text
            except Exception as exc:
                logger.error("Failed to extract markdown text: %s", exc)
                return ""

        return self._extract_block_text(rendered)

    def _extract_metadata(self, rendered: Any, filename: str) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {
            "filename": filename,
            "parser": "Marker",
            "parser_version": "1.10+",
            "output_format": self.output_format,
            "used_llm": self.use_llm,
            "device": self._current_device(),
        }

        try:
            import torch

            if torch.cuda.is_available():
                metadata["gpu_name"] = torch.cuda.get_device_name(0)
                metadata["gpu_vram_gb"] = torch.cuda.get_device_properties(0).total_memory / 1e9
        except Exception:
            pass

        if hasattr(rendered, "table_of_contents"):
            metadata["table_of_contents"] = rendered.table_of_contents

        return metadata

    def validate(self, file_content: bytes, filename: str) -> bool:
        try:
            self._validate_file_content(file_content)
            file_ext = self._get_file_extension(filename)
            return self.supports_format(file_ext)
        except Exception as exc:
            logger.debug("Validation failed for %s: %s", filename, exc)
            return False

    def supports_format(self, file_format: str) -> bool:
        supported = [".pdf"]
        return file_format.lower() in supported

    def get_supported_formats(self) -> List[str]:
        return [".pdf"]

    def get_parser_info(self) -> Dict[str, Any]:
        info = {
            "parser_type": "MarkerParser",
            "marker_version": "1.10+",
            "supported_formats": self.get_supported_formats(),
            "use_llm": self.use_llm,
            "llm_service": "Google Gemini" if self.use_llm else None,
            "batch_multiplier": self.batch_multiplier,
            "output_format": self.output_format,
            "device": self._current_device(),
        }

        try:
            import torch

            info["cuda_available"] = torch.cuda.is_available()
        except Exception:
            info["cuda_available"] = False

        return info

    def _current_device(self) -> str:
        device = os.getenv("TORCH_DEVICE")
        if device:
            return device

        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass

        return "cpu"

    def _log_gpu_memory(self, stage: str):
        try:
            import torch

            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated() / 1024**3
                reserved = torch.cuda.memory_reserved() / 1024**3
                logger.info(
                    "GPU Memory (%s): %.2fGB allocated, %.2fGB reserved",
                    stage,
                    allocated,
                    reserved,
                )
        except Exception as exc:
            logger.debug("Failed to log GPU memory: %s", exc)

    def _cleanup_gpu_memory(self):
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                gc.collect()
        except Exception:
            pass

    def __del__(self):
        self._cleanup_gpu_memory()
