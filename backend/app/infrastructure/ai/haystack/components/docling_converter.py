"""
DoclingDocumentConverter component for Haystack pipelines.

Wraps the existing DoclingParser to convert files into Haystack Documents.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

from haystack import component, Document

from app.workers.pipelines.docling_parser import DoclingParser

logger = logging.getLogger(__name__)


@component
class DoclingDocumentConverter:
    """
    Haystack component that converts documents using Docling parser.

    Wraps the existing DoclingParser to provide Haystack-compatible
    document conversion with support for PDF, DOCX, DOC, and TXT files.

    Features:
    - Multi-format support (PDF, DOCX, DOC, TXT)
    - OCR support for scanned documents
    - Bounding box extraction for visual highlighting
    - Metadata extraction (page count, author, title, etc.)
    - Structure preservation

    Usage:
        >>> converter = DoclingDocumentConverter(use_ocr=True)
        >>> result = converter.run(
        ...     sources=["/path/to/document.pdf"],
        ...     meta={"document_id": "doc_123", "case_id": "case_456"}
        ... )
        >>> documents = result["documents"]
    """

    def __init__(
        self,
        use_ocr: bool = True,
        force_full_page_ocr: bool = False,
    ):
        """
        Initialize the Docling converter.

        Args:
            use_ocr: Whether to use OCR for scanned documents
            force_full_page_ocr: Force OCR on all pages (slower but more accurate)
        """
        self.use_ocr = use_ocr
        self.force_full_page_ocr = force_full_page_ocr
        self.parser = DoclingParser(
            use_ocr=use_ocr,
            force_full_page_ocr=force_full_page_ocr,
        )

        logger.info(
            f"Initialized DoclingDocumentConverter (OCR: {use_ocr}, "
            f"Force Full Page OCR: {force_full_page_ocr})"
        )

    @component.output_types(documents=List[Document], raw_output=Dict[str, Any])
    def run(
        self,
        sources: List[Union[str, Path, bytes]],
        meta: Optional[Dict[str, Any]] = None,
        filenames: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Convert documents using Docling parser.

        Args:
            sources: List of file paths, Path objects, or bytes
            meta: Optional metadata to add to all documents
            filenames: Optional list of filenames (required if sources are bytes)

        Returns:
            Dictionary with:
                - documents: List of Haystack Documents
                - raw_output: Raw Docling parser output for advanced use cases
        """
        if not sources:
            logger.warning("No sources provided to DoclingDocumentConverter")
            return {"documents": [], "raw_output": {}}

        documents = []
        raw_outputs = {}

        for i, source in enumerate(sources):
            try:
                # Determine filename
                if isinstance(source, (str, Path)):
                    file_path = Path(source)
                    filename = file_path.name
                    # Read file bytes
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                elif isinstance(source, bytes):
                    file_content = source
                    if filenames and i < len(filenames):
                        filename = filenames[i]
                    else:
                        filename = f"document_{i}.pdf"
                        logger.warning(
                            f"No filename provided for bytes source {i}, "
                            f"using default: {filename}"
                        )
                else:
                    logger.error(f"Unsupported source type: {type(source)}")
                    continue

                logger.info(f"Converting document: {filename}")

                # Parse document
                parsed = self.parser.parse(
                    file_content=file_content,
                    filename=filename,
                )

                # Store raw output
                raw_outputs[filename] = parsed

                # Convert to Haystack Document
                doc_meta = {
                    "filename": filename,
                    "file_ext": Path(filename).suffix.lower(),
                    **parsed.get("metadata", {}),
                }

                # Add user-provided metadata
                if meta:
                    doc_meta.update(meta)

                # Extract pages with bounding boxes
                pages = parsed.get("pages", [])
                doc_meta["page_count"] = len(pages)
                doc_meta["pages"] = pages  # Store full page data in metadata

                # Create Haystack Document
                document = Document(
                    content=parsed.get("text", ""),
                    meta=doc_meta,
                )

                documents.append(document)

                logger.info(
                    f"Successfully converted {filename}: "
                    f"{len(parsed.get('text', ''))} chars, "
                    f"{len(pages)} pages"
                )

            except Exception as e:
                logger.error(f"Failed to convert source {i} ({source}): {e}", exc_info=True)
                continue

        logger.info(f"Converted {len(documents)} documents from {len(sources)} sources")

        return {
            "documents": documents,
            "raw_output": raw_outputs,
        }

    @component.output_types(documents=List[Document], raw_output=Dict[str, Any])
    def run_from_bytes(
        self,
        file_content: bytes,
        filename: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Convert a single document from bytes.

        Convenience method for single document conversion.

        Args:
            file_content: Document bytes
            filename: Document filename (used to determine format)
            meta: Optional metadata to add to document

        Returns:
            Dictionary with:
                - documents: List containing single Haystack Document
                - raw_output: Raw Docling parser output
        """
        return self.run(
            sources=[file_content],
            meta=meta,
            filenames=[filename],
        )

    @component.output_types(documents=List[Document], raw_output=Dict[str, Any])
    def run_from_path(
        self,
        file_path: Union[str, Path],
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Convert a single document from file path.

        Convenience method for single file conversion.

        Args:
            file_path: Path to document file
            meta: Optional metadata to add to document

        Returns:
            Dictionary with:
                - documents: List containing single Haystack Document
                - raw_output: Raw Docling parser output
        """
        return self.run(
            sources=[file_path],
            meta=meta,
        )
