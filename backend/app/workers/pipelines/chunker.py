"""
Legal Document Chunker

Intelligent text chunking strategies optimized for legal documents.
Supports hierarchical chunking (summary, section, microblock) following RAGFlow patterns.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


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
    Legal document chunker with multi-level granularity.

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

        logger.info(
            f"Initialized DocumentChunker (summary={summary_max_tokens}, "
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

        result = {
            "summary": self._create_summary_chunks(text, pages, metadata),
            "section": self._create_section_chunks(text, pages, metadata),
            "microblock": self._create_microblock_chunks(text, pages, metadata),
        }

        total_chunks = sum(len(chunks) for chunks in result.values())
        logger.info(
            f"Created {total_chunks} chunks: "
            f"{len(result['summary'])} summary, "
            f"{len(result['section'])} section, "
            f"{len(result['microblock'])} microblock"
        )

        return result

    def _create_summary_chunks(
        self,
        text: str,
        pages: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[TextChunk]:
        """
        Create summary-level chunks (document or large section overview).

        Args:
            text: Document text
            pages: Optional page data
            metadata: Optional metadata

        Returns:
            List of summary chunks
        """
        chunks = []

        # Extract bboxes from metadata or collect from pages (like section/microblock do)
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

        # For shorter documents, use entire text as summary
        word_count = len(text.split())
        if word_count <= self.summary_max_tokens:
            # Determine page number from bboxes
            page_number = self._determine_page_number(all_bboxes)

            chunks.append(TextChunk(
                text=text,
                chunk_type="summary",
                position=0,
                page_number=page_number,
                metadata=metadata,
                bboxes=all_bboxes,  # Include all bboxes for summary
            ))
        else:
            # For longer documents, create overlapping summary chunks
            words = text.split()
            position = 0

            for i in range(0, len(words), self.summary_max_tokens - self.overlap_tokens):
                chunk_words = words[i:i + self.summary_max_tokens]
                chunk_text = " ".join(chunk_words)

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
                position += 1

        return chunks

    def _create_section_chunks(
        self,
        text: str,
        pages: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[TextChunk]:
        """
        Create section-level chunks (logical document sections).

        Args:
            text: Document text
            pages: Optional page data
            metadata: Optional metadata

        Returns:
            List of section chunks
        """
        chunks = []

        # Extract bboxes from metadata or pages
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

        if self.use_semantic_splitting:
            # Try to split on legal section markers
            sections = self._split_on_legal_sections(text)
        else:
            # Fall back to paragraph splitting
            sections = self._split_on_paragraphs(text)

        position = 0
        for section_text in sections:
            # Further split if section exceeds max tokens
            sub_chunks = self._split_large_section(
                section_text,
                max_tokens=self.section_max_tokens,
                overlap=self.overlap_tokens,
            )

            for sub_chunk in sub_chunks:
                # Extract relevant bboxes for this chunk
                chunk_bboxes = self._extract_bboxes_for_text(sub_chunk, all_bboxes)

                # Determine page number from bboxes
                page_number = self._determine_page_number(chunk_bboxes)

                chunks.append(TextChunk(
                    text=sub_chunk,
                    chunk_type="section",
                    position=position,
                    page_number=page_number,
                    metadata=metadata,
                    bboxes=chunk_bboxes,
                ))
                position += 1

        return chunks

    def _create_microblock_chunks(
        self,
        text: str,
        pages: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[TextChunk]:
        """
        Create microblock-level chunks (fine-grained, sentence-level).

        Args:
            text: Document text
            pages: Optional page data
            metadata: Optional metadata

        Returns:
            List of microblock chunks
        """
        chunks = []

        # Extract bboxes from metadata or pages
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

        # Split into sentences
        sentences = self._split_into_sentences(text)

        # Group sentences into microblocks
        current_block = []
        current_tokens = 0
        position = 0

        for sentence in sentences:
            sentence_tokens = len(sentence.split())

            # Check if adding this sentence would exceed max tokens
            if current_tokens + sentence_tokens > self.microblock_max_tokens and current_block:
                # Create chunk from current block
                block_text = " ".join(current_block)
                # Extract relevant bboxes for this chunk
                chunk_bboxes = self._extract_bboxes_for_text(block_text, all_bboxes)

                # Determine page number from bboxes
                page_number = self._determine_page_number(chunk_bboxes)

                chunks.append(TextChunk(
                    text=block_text,
                    chunk_type="microblock",
                    position=position,
                    page_number=page_number,
                    metadata=metadata,
                    bboxes=chunk_bboxes,
                ))
                position += 1

                # Start new block with overlap
                if self.overlap_tokens > 0 and current_block:
                    # Keep last sentence for overlap
                    current_block = [current_block[-1]]
                    current_tokens = len(current_block[0].split())
                else:
                    current_block = []
                    current_tokens = 0

            current_block.append(sentence)
            current_tokens += sentence_tokens

        # Add final block
        if current_block:
            block_text = " ".join(current_block)
            # Extract relevant bboxes for this chunk
            chunk_bboxes = self._extract_bboxes_for_text(block_text, all_bboxes)

            # Determine page number from bboxes
            page_number = self._determine_page_number(chunk_bboxes)

            chunks.append(TextChunk(
                text=block_text,
                chunk_type="microblock",
                position=position,
                page_number=page_number,
                metadata=metadata,
                bboxes=chunk_bboxes,
            ))

        return chunks

    def _split_on_legal_sections(self, text: str) -> List[str]:
        """
        Split text on legal section markers.

        Looks for patterns like:
        - Article I, Section 1
        - 1. Introduction
        - WHEREAS
        - NOW THEREFORE

        Args:
            text: Document text

        Returns:
            List of section texts
        """
        # Legal section patterns
        patterns = [
            r'\n\s*Article\s+[IVX\d]+',  # Article markers
            r'\n\s*Section\s+[\d]+',  # Section markers
            r'\n\s*ARTICLE\s+[IVX\d]+',  # Uppercase article
            r'\n\s*SECTION\s+[\d]+',  # Uppercase section
            r'\n\s*\d+\.\s+[A-Z]',  # Numbered sections with caps
            r'\n\s*WHEREAS',  # Contract clauses
            r'\n\s*NOW THEREFORE',  # Contract transitions
            r'\n\s*[A-Z][A-Z\s]{10,}\n',  # All-caps headers
        ]

        # Combine patterns
        combined_pattern = '|'.join(patterns)

        # Split on patterns
        sections = re.split(combined_pattern, text)

        # Filter empty sections
        sections = [s.strip() for s in sections if s.strip()]

        # If no sections found, fall back to paragraphs
        if len(sections) <= 1:
            return self._split_on_paragraphs(text)

        return sections

    def _split_on_paragraphs(self, text: str) -> List[str]:
        """
        Split text on paragraph boundaries.

        Args:
            text: Document text

        Returns:
            List of paragraph texts
        """
        # Split on double newlines or paragraph markers
        paragraphs = re.split(r'\n\s*\n+', text)

        # Filter empty paragraphs
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        return paragraphs

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Args:
            text: Document text

        Returns:
            List of sentences
        """
        # Simple sentence splitting (can be enhanced with spaCy/NLTK)
        # Handle common abbreviations
        text = re.sub(r'\bMr\.', 'Mr', text)
        text = re.sub(r'\bMrs\.', 'Mrs', text)
        text = re.sub(r'\bDr\.', 'Dr', text)
        text = re.sub(r'\bU\.S\.', 'US', text)
        text = re.sub(r'\bInc\.', 'Inc', text)
        text = re.sub(r'\bLtd\.', 'Ltd', text)
        text = re.sub(r'\bCorp\.', 'Corp', text)

        # Split on sentence boundaries
        sentences = re.split(r'[.!?]+\s+', text)

        # Filter empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def _split_large_section(
        self,
        text: str,
        max_tokens: int,
        overlap: int,
    ) -> List[str]:
        """
        Split a large section into smaller chunks.

        Args:
            text: Section text
            max_tokens: Maximum tokens per chunk
            overlap: Overlap tokens between chunks

        Returns:
            List of chunk texts
        """
        words = text.split()

        if len(words) <= max_tokens:
            return [text]

        chunks = []
        for i in range(0, len(words), max_tokens - overlap):
            chunk_words = words[i:i + max_tokens]
            chunks.append(" ".join(chunk_words))

        return chunks

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
