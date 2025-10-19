"""
Legal Document Chunker - LlamaIndex Implementation

Intelligent text chunking using LlamaIndex node parsers.
Supports hierarchical chunking (summary, section, microblock) following RAGFlow patterns.
Replaces custom implementation with industry-standard LlamaIndex tooling.
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from llama_index.core.node_parser import SentenceSplitter
from app.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""
    text: str
    chunk_type: str  # 'summary', 'section', 'microblock'
    position: int  # Position in document
    page_number: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    bboxes: Optional[List[Dict[str, Any]]] = None  # Bounding boxes for this chunk


class DocumentChunker:
    """
    Legal document chunker with multi-level granularity using LlamaIndex.

    Implements hierarchical chunking strategy:
    - Summary: Document-level overview (entire document or large sections)
    - Section: Logical sections (paragraphs, subsections)
    - Microblock: Fine-grained chunks (sentences, small paragraphs)
    """

    def __init__(
        self,
        summary_max_tokens: int = 2000,
        section_max_tokens: int = 500,
        microblock_max_tokens: int = 128,
        overlap_tokens: int = 50,
        use_semantic_splitting: bool = True,
    ):
        """
        Initialize the document chunker.

        Args:
            summary_max_tokens: Maximum tokens for summary chunks
            section_max_tokens: Maximum tokens for section chunks
            microblock_max_tokens: Maximum tokens for microblock chunks
            overlap_tokens: Number of tokens to overlap between chunks
            use_semantic_splitting: Whether to split on semantic boundaries
        """
        self.summary_max_tokens = summary_max_tokens
        self.section_max_tokens = section_max_tokens
        self.microblock_max_tokens = microblock_max_tokens
        self.overlap_tokens = overlap_tokens
        self.use_semantic_splitting = use_semantic_splitting

        # Initialize LlamaIndex sentence splitters for each level
        # chunk_size is in characters, we approximate: 1 token ≈ 4 chars
        self.summary_splitter = SentenceSplitter(
            chunk_size=summary_max_tokens * 4,
            chunk_overlap=overlap_tokens * 4,
            paragraph_separator="\n\n",
            secondary_chunking_regex="[^,.;。？！]+[,.;。？！]?",
        )

        self.section_splitter = SentenceSplitter(
            chunk_size=section_max_tokens * 4,
            chunk_overlap=overlap_tokens * 4,
            paragraph_separator="\n\n",
            secondary_chunking_regex="[^,.;。？！]+[,.;。？！]?",
        )

        self.microblock_splitter = SentenceSplitter(
            chunk_size=microblock_max_tokens * 4,
            chunk_overlap=overlap_tokens * 4,
            paragraph_separator="\n\n",
            secondary_chunking_regex="[^,.;。？！]+[,.;。？！]?",
        )

        logger.info(
            f"Initialized DocumentChunker with LlamaIndex (summary={summary_max_tokens}, "
            f"section={section_max_tokens}, microblock={microblock_max_tokens})"
        )

    def chunk_document(
        self,
        text: str,
        pages: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[TextChunk]]:
        """
        Chunk a document into hierarchical levels.

        Args:
            text: Full document text
            pages: Optional list of page data
            metadata: Optional document metadata

        Returns:
            Dictionary mapping chunk types to lists of chunks
        """
        logger.info(f"Chunking document ({len(text)} chars, {len(text.split())} words)")

        # Preprocess text for legal sections if enabled
        if self.use_semantic_splitting:
            preprocessed_text = self._preprocess_legal_sections(text)
        else:
            preprocessed_text = text

        result = {
            "summary": self._create_summary_chunks(preprocessed_text, pages, metadata),
            "section": self._create_section_chunks(preprocessed_text, pages, metadata),
            "microblock": self._create_microblock_chunks(preprocessed_text, pages, metadata),
        }

        total_chunks = sum(len(chunks) for chunks in result.values())
        logger.info(
            f"Created {total_chunks} chunks: "
            f"{len(result['summary'])} summary, "
            f"{len(result['section'])} section, "
            f"{len(result['microblock'])} microblock"
        )

        return result

    def _preprocess_legal_sections(self, text: str) -> str:
        """
        Preprocess text to enhance legal section boundaries.

        Inserts extra newlines before legal section markers to help
        the sentence splitter recognize them as natural break points.

        Args:
            text: Document text

        Returns:
            Preprocessed text with enhanced boundaries
        """
        # Legal section patterns (same as original)
        patterns = [
            (r'\n\s*Article\s+[IVX\d]+', r'\n\n\nArticle '),
            (r'\n\s*Section\s+[\d]+', r'\n\n\nSection '),
            (r'\n\s*ARTICLE\s+[IVX\d]+', r'\n\n\nARTICLE '),
            (r'\n\s*SECTION\s+[\d]+', r'\n\n\nSECTION '),
            (r'\n\s*WHEREAS', r'\n\n\nWHEREAS'),
            (r'\n\s*NOW THEREFORE', r'\n\n\nNOW THEREFORE'),
        ]

        preprocessed = text
        for pattern, replacement in patterns:
            preprocessed = re.sub(pattern, replacement, preprocessed)

        return preprocessed

    def _create_summary_chunks(
        self,
        text: str,
        pages: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[TextChunk]:
        """
        Create summary-level chunks using LlamaIndex SentenceSplitter.

        Args:
            text: Document text
            pages: Optional page data
            metadata: Optional metadata

        Returns:
            List of summary chunks
        """
        chunks = []

        # Extract all bboxes from pages
        all_bboxes = self._extract_all_bboxes(pages, metadata)

        # Use LlamaIndex to split text
        text_splits = self.summary_splitter.split_text(text)

        for position, chunk_text in enumerate(text_splits):
            # Extract relevant bboxes for this chunk
            chunk_bboxes = self._extract_bboxes_for_text(chunk_text, all_bboxes)

            # Determine page number from bboxes
            page_number = self._determine_page_number(chunk_bboxes)

            chunks.append(TextChunk(
                text=chunk_text,
                chunk_type="summary",
                position=position,
                page_number=page_number,
                metadata=metadata,
                bboxes=chunk_bboxes,
            ))

        return chunks

    def _create_section_chunks(
        self,
        text: str,
        pages: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[TextChunk]:
        """
        Create section-level chunks using LlamaIndex SentenceSplitter.

        Args:
            text: Document text
            pages: Optional page data
            metadata: Optional metadata

        Returns:
            List of section chunks
        """
        chunks = []

        # Extract all bboxes from pages
        all_bboxes = self._extract_all_bboxes(pages, metadata)

        # Use LlamaIndex to split text
        text_splits = self.section_splitter.split_text(text)

        for position, chunk_text in enumerate(text_splits):
            # Extract relevant bboxes for this chunk
            chunk_bboxes = self._extract_bboxes_for_text(chunk_text, all_bboxes)

            # Determine page number from bboxes
            page_number = self._determine_page_number(chunk_bboxes)

            chunks.append(TextChunk(
                text=chunk_text,
                chunk_type="section",
                position=position,
                page_number=page_number,
                metadata=metadata,
                bboxes=chunk_bboxes,
            ))

        return chunks

    def _create_microblock_chunks(
        self,
        text: str,
        pages: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[TextChunk]:
        """
        Create microblock-level chunks using LlamaIndex SentenceSplitter.

        Args:
            text: Document text
            pages: Optional page data
            metadata: Optional metadata

        Returns:
            List of microblock chunks
        """
        chunks = []

        # Extract all bboxes from pages
        all_bboxes = self._extract_all_bboxes(pages, metadata)

        # Use LlamaIndex to split text
        text_splits = self.microblock_splitter.split_text(text)

        for position, chunk_text in enumerate(text_splits):
            # Extract relevant bboxes for this chunk
            chunk_bboxes = self._extract_bboxes_for_text(chunk_text, all_bboxes)

            # Determine page number from bboxes
            page_number = self._determine_page_number(chunk_bboxes)

            chunks.append(TextChunk(
                text=chunk_text,
                chunk_type="microblock",
                position=position,
                page_number=page_number,
                metadata=metadata,
                bboxes=chunk_bboxes,
            ))

        return chunks

    def _extract_all_bboxes(
        self,
        pages: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extract all bounding boxes from pages or metadata.

        Args:
            pages: Optional page data
            metadata: Optional metadata

        Returns:
            List of all bboxes with page numbers
        """
        all_bboxes = metadata.get("bboxes", []) if metadata else []

        if not all_bboxes and pages:
            # Collect bboxes from all pages (Docling stores them in items array)
            for page in pages:
                page_num = page.get("page_number", 1)
                # First check if page has direct bboxes array (PyMuPDF fallback)
                if "bboxes" in page:
                    for bbox in page.get("bboxes", []):
                        # Add page number to bbox
                        bbox_with_page = bbox.copy() if isinstance(bbox, dict) else {}
                        bbox_with_page["page"] = page_num
                        all_bboxes.append(bbox_with_page)
                # Then check for items with bbox fields (Docling format)
                elif "items" in page:
                    for item in page["items"]:
                        if "bbox" in item and item["bbox"]:
                            # Add bbox with text and page number for matching
                            all_bboxes.append({
                                "bbox": item["bbox"],
                                "text": item.get("text", ""),
                                "type": item.get("type", "unknown"),
                                "page": page_num,
                            })

        return all_bboxes

    def _extract_bboxes_for_text(
        self,
        chunk_text: str,
        all_bboxes: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Extract relevant bounding boxes for a text chunk.

        Matches bboxes to chunk text by finding bboxes whose text appears in the chunk.

        Args:
            chunk_text: The chunk text to match
            all_bboxes: List of all available bboxes

        Returns:
            List of relevant bboxes for this chunk
        """
        if not all_bboxes:
            return []

        chunk_bboxes = []
        chunk_lower = chunk_text.lower()

        for bbox in all_bboxes:
            bbox_text = bbox.get("text", "")
            if bbox_text and bbox_text.lower() in chunk_lower:
                chunk_bboxes.append(bbox)

        return chunk_bboxes

    def _determine_page_number(self, chunk_bboxes: List[Dict[str, Any]]) -> Optional[int]:
        """
        Determine the primary page number for a chunk based on its bboxes.

        Uses the most common page number among the bboxes. For chunks spanning
        multiple pages, returns the page with the most bboxes.

        Args:
            chunk_bboxes: List of bboxes for this chunk

        Returns:
            Page number or None if no bboxes have page info
        """
        if not chunk_bboxes:
            return None

        # Count page occurrences
        page_counts = {}
        for bbox in chunk_bboxes:
            page = bbox.get("page")
            if page is not None:
                page_counts[page] = page_counts.get(page, 0) + 1

        if not page_counts:
            return None

        # Return the page with the most bboxes
        return max(page_counts, key=page_counts.get)

    def chunk_with_metadata(
        self,
        text: str,
        pages: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Chunk document and return as list of dictionaries with full metadata.

        Args:
            text: Document text
            pages: Optional page data
            metadata: Optional metadata

        Returns:
            List of chunk dictionaries
        """
        chunks_by_type = self.chunk_document(text, pages, metadata)

        all_chunks = []
        for chunk_type, chunks in chunks_by_type.items():
            for chunk in chunks:
                all_chunks.append({
                    "text": chunk.text,
                    "chunk_type": chunk.chunk_type,
                    "position": chunk.position,
                    "page_number": chunk.page_number,
                    "metadata": chunk.metadata or {},
                    "char_count": len(chunk.text),
                    "word_count": len(chunk.text.split()),
                })

        return all_chunks

    def estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for text.

        Simple approximation: word count (can be replaced with tiktoken).

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        return len(text.split())


# Convenience function for quick chunking
def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> List[str]:
    """
    Simple convenience function to chunk text.

    Args:
        text: Text to chunk
        chunk_size: Maximum tokens per chunk
        overlap: Overlap tokens between chunks

    Returns:
        List of text chunks
    """
    chunker = DocumentChunker(
        section_max_tokens=chunk_size,
        overlap_tokens=overlap,
    )

    result = chunker.chunk_document(text)
    return [chunk.text for chunk in result["section"]]
