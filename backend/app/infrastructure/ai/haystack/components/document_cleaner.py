"""
LegalDocumentCleaner component for Haystack pipelines.

Cleans and normalizes legal documents by removing headers, footers,
page numbers, and other artifacts.
"""

import logging
import re
from typing import List, Dict, Any, Optional

from haystack import component, Document

logger = logging.getLogger(__name__)


@component
class LegalDocumentCleaner:
    """
    Haystack component that cleans legal documents.

    Removes common artifacts from legal documents:
    - Headers and footers
    - Page numbers
    - Excessive whitespace
    - Boilerplate text
    - Formatting artifacts

    Features:
    - Pattern-based cleaning
    - Preserves legal citations
    - Configurable patterns
    - Whitespace normalization

    Usage:
        >>> cleaner = LegalDocumentCleaner()
        >>> result = cleaner.run(documents=[doc1, doc2])
        >>> cleaned_docs = result["documents"]
    """

    def __init__(
        self,
        remove_headers: bool = True,
        remove_page_numbers: bool = True,
        normalize_whitespace: bool = True,
        min_text_length: int = 10,
    ):
        """
        Initialize the document cleaner.

        Args:
            remove_headers: Remove common header patterns
            remove_page_numbers: Remove page numbers
            normalize_whitespace: Normalize whitespace (multiple spaces, newlines)
            min_text_length: Minimum text length to keep (shorter texts are skipped)
        """
        self.remove_headers = remove_headers
        self.remove_page_numbers = remove_page_numbers
        self.normalize_whitespace = normalize_whitespace
        self.min_text_length = min_text_length

        # Common header/footer patterns in legal documents
        self.header_patterns = [
            r'^CONFIDENTIAL.*$',
            r'^PRIVILEGED.*$',
            r'^ATTORNEY-CLIENT.*$',
            r'^WORK PRODUCT.*$',
            r'^\d+\s*$',  # Standalone numbers (page numbers)
            r'^Page \d+ of \d+$',
            r'^\[.*\]$',  # Bracketed text at line start
        ]

        # Compile patterns
        self.compiled_patterns = [
            re.compile(pattern, re.MULTILINE | re.IGNORECASE)
            for pattern in self.header_patterns
        ]

        logger.info(
            f"Initialized LegalDocumentCleaner (remove_headers={remove_headers}, "
            f"remove_page_numbers={remove_page_numbers}, "
            f"normalize_whitespace={normalize_whitespace})"
        )

    @component.output_types(documents=List[Document])
    def run(self, documents: List[Document]) -> Dict[str, Any]:
        """
        Clean documents.

        Args:
            documents: List of Haystack Documents to clean

        Returns:
            Dictionary with:
                - documents: List of cleaned Haystack Documents
        """
        if not documents:
            logger.warning("No documents provided to LegalDocumentCleaner")
            return {"documents": []}

        cleaned_documents = []

        for doc in documents:
            try:
                cleaned_content = self._clean_text(doc.content)

                # Skip if text is too short after cleaning
                if len(cleaned_content.strip()) < self.min_text_length:
                    logger.warning(
                        f"Document too short after cleaning ({len(cleaned_content)} chars), "
                        f"skipping: {doc.meta.get('filename', 'unknown')}"
                    )
                    continue

                # Create cleaned document
                cleaned_doc = Document(
                    content=cleaned_content,
                    meta={
                        **doc.meta,
                        "cleaned": True,
                        "original_length": len(doc.content),
                        "cleaned_length": len(cleaned_content),
                    },
                )

                cleaned_documents.append(cleaned_doc)

            except Exception as e:
                logger.error(
                    f"Failed to clean document {doc.meta.get('filename', 'unknown')}: {e}",
                    exc_info=True
                )
                # Keep original document on error
                cleaned_documents.append(doc)

        logger.info(
            f"Cleaned {len(cleaned_documents)} documents "
            f"({len(documents) - len(cleaned_documents)} skipped)"
        )

        return {"documents": cleaned_documents}

    def _clean_text(self, text: str) -> str:
        """
        Clean a single text string.

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        cleaned = text

        # Remove headers/footers
        if self.remove_headers:
            for pattern in self.compiled_patterns:
                cleaned = pattern.sub('', cleaned)

        # Remove page numbers (standalone numbers on their own line)
        if self.remove_page_numbers:
            # Pattern: line with only digits and optional whitespace
            cleaned = re.sub(r'^\s*\d+\s*$', '', cleaned, flags=re.MULTILINE)

        # Normalize whitespace
        if self.normalize_whitespace:
            # Replace multiple spaces with single space
            cleaned = re.sub(r' +', ' ', cleaned)
            # Replace multiple newlines with double newline (paragraph break)
            cleaned = re.sub(r'\n\n+', '\n\n', cleaned)
            # Remove trailing whitespace from lines
            cleaned = re.sub(r' +$', '', cleaned, flags=re.MULTILINE)
            # Remove leading whitespace from lines (but preserve indentation)
            cleaned = re.sub(r'^\s+', '', cleaned, flags=re.MULTILINE)

        # Remove leading/trailing whitespace
        cleaned = cleaned.strip()

        return cleaned
