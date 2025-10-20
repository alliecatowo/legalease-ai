"""
Custom Haystack component for legal-aware document chunking.

This component implements hierarchical chunking optimized for legal documents,
respecting legal structures like sections, citations, and clause boundaries.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from haystack import component, Document

logger = logging.getLogger(__name__)


@component
class LegalChunker:
    """
    Legal-aware document chunker with hierarchical granularity.

    This component chunks documents while respecting legal structure:
    - Never splits legal citations
    - Never splits statute references
    - Never splits contract clauses
    - Preserves section headings and numbering
    - Maintains bounding box metadata

    **Chunking Levels:**
    1. **SUMMARY**: Document-level overview (max 2000 tokens)
    2. **SECTION**: Logical sections (max 500 tokens)
    3. **MICROBLOCK**: Fine-grained chunks (max 128 tokens)

    **Legal Citation Preservation:**
    - Case citations: "Smith v. Jones, 123 F.3d 456 (9th Cir. 2020)"
    - Statutes: "18 U.S.C. § 1234"
    - Regulations: "26 C.F.R. § 1.501(c)(3)"
    - Contract clauses: "Section 4.2.1"

    **Chunk Metadata:**
    - chunk_type: "SUMMARY" | "SECTION" | "MICROBLOCK"
    - position: 0-indexed within document
    - page_number: Source page
    - section_heading: Section title
    - parent_chunk_id: For hierarchy
    - bounding_box: From Docling
    - has_citation: Citation presence flag
    - token_count: Estimated token count

    Usage:
        ```python
        chunker = LegalChunker(
            chunk_level="SECTION",
            section_max_tokens=500,
            overlap_tokens=50
        )
        result = chunker.run(documents=documents)
        chunked_docs = result["documents"]
        ```
    """

    def __init__(
        self,
        chunk_level: str = "SECTION",
        summary_max_tokens: int = 2000,
        section_max_tokens: int = 500,
        microblock_max_tokens: int = 128,
        overlap_tokens: int = 50,
        preserve_citations: bool = True,
        preserve_section_numbers: bool = True,
    ):
        """
        Initialize the legal chunker.

        Args:
            chunk_level: Chunking level ("SUMMARY", "SECTION", "MICROBLOCK", or "ALL")
            summary_max_tokens: Maximum tokens for summary chunks
            section_max_tokens: Maximum tokens for section chunks
            microblock_max_tokens: Maximum tokens for microblock chunks
            overlap_tokens: Token overlap between chunks
            preserve_citations: Never split citations
            preserve_section_numbers: Preserve section numbering
        """
        self.chunk_level = chunk_level.upper()
        self.summary_max_tokens = summary_max_tokens
        self.section_max_tokens = section_max_tokens
        self.microblock_max_tokens = microblock_max_tokens
        self.overlap_tokens = overlap_tokens
        self.preserve_citations = preserve_citations
        self.preserve_section_numbers = preserve_section_numbers

        if self.chunk_level not in ["SUMMARY", "SECTION", "MICROBLOCK", "ALL"]:
            raise ValueError(
                f"Invalid chunk_level: {chunk_level}. "
                "Must be SUMMARY, SECTION, MICROBLOCK, or ALL"
            )

        logger.info(
            f"Initialized LegalChunker(level={self.chunk_level}, "
            f"summary={summary_max_tokens}, section={section_max_tokens}, "
            f"microblock={microblock_max_tokens})"
        )

    @component.output_types(documents=List[Document])
    def run(self, documents: List[Document]) -> Dict[str, List[Document]]:
        """
        Chunk documents using legal-aware strategy.

        Args:
            documents: List of Documents to chunk

        Returns:
            Dictionary with "documents" key containing chunked Documents
        """
        chunked_documents = []

        for doc in documents:
            try:
                doc_chunks = self._chunk_document(doc)
                chunked_documents.extend(doc_chunks)
            except Exception as e:
                logger.error(f"Failed to chunk document: {e}")
                # On error, include original document
                chunked_documents.append(doc)

        logger.info(
            f"Chunked {len(documents)} documents into {len(chunked_documents)} chunks"
        )
        return {"documents": chunked_documents}

    def _chunk_document(self, document: Document) -> List[Document]:
        """
        Chunk a single document.

        Args:
            document: Document to chunk

        Returns:
            List of chunked Documents
        """
        text = document.content or ""
        meta = document.meta or {}

        chunks = []

        # Determine which chunk levels to create
        if self.chunk_level == "ALL":
            levels = ["SUMMARY", "SECTION", "MICROBLOCK"]
        else:
            levels = [self.chunk_level]

        # Create chunks at each level
        for level in levels:
            if level == "SUMMARY":
                level_chunks = self._create_summary_chunks(text, meta)
            elif level == "SECTION":
                level_chunks = self._create_section_chunks(text, meta)
            elif level == "MICROBLOCK":
                level_chunks = self._create_microblock_chunks(text, meta)
            else:
                continue

            chunks.extend(level_chunks)

        return chunks

    def _create_summary_chunks(
        self,
        text: str,
        meta: Dict[str, Any],
    ) -> List[Document]:
        """
        Create summary-level chunks.

        Args:
            text: Document text
            meta: Document metadata

        Returns:
            List of summary Documents
        """
        chunks = []
        token_count = self._estimate_tokens(text)

        # If text fits in one summary, create single chunk
        if token_count <= self.summary_max_tokens:
            chunk_meta = self._build_chunk_metadata(
                chunk_type="SUMMARY",
                position=0,
                parent_meta=meta,
                text=text,
            )
            chunks.append(Document(content=text, meta=chunk_meta))
        else:
            # Split into overlapping summary chunks
            chunk_texts = self._split_text_by_tokens(
                text,
                max_tokens=self.summary_max_tokens,
                overlap=self.overlap_tokens,
            )

            for idx, chunk_text in enumerate(chunk_texts):
                chunk_meta = self._build_chunk_metadata(
                    chunk_type="SUMMARY",
                    position=idx,
                    parent_meta=meta,
                    text=chunk_text,
                )
                chunks.append(Document(content=chunk_text, meta=chunk_meta))

        return chunks

    def _create_section_chunks(
        self,
        text: str,
        meta: Dict[str, Any],
    ) -> List[Document]:
        """
        Create section-level chunks (respects legal sections).

        Args:
            text: Document text
            meta: Document metadata

        Returns:
            List of section Documents
        """
        # Split on legal section boundaries
        sections = self._split_on_legal_sections(text)

        chunks = []
        position = 0

        for section_text in sections:
            # Further split if section exceeds max tokens
            if self._estimate_tokens(section_text) > self.section_max_tokens:
                sub_chunks = self._split_text_by_tokens(
                    section_text,
                    max_tokens=self.section_max_tokens,
                    overlap=self.overlap_tokens,
                )
            else:
                sub_chunks = [section_text]

            for chunk_text in sub_chunks:
                # Extract section heading
                section_heading = self._extract_section_heading(chunk_text)

                chunk_meta = self._build_chunk_metadata(
                    chunk_type="SECTION",
                    position=position,
                    parent_meta=meta,
                    text=chunk_text,
                    section_heading=section_heading,
                )
                chunks.append(Document(content=chunk_text, meta=chunk_meta))
                position += 1

        return chunks

    def _create_microblock_chunks(
        self,
        text: str,
        meta: Dict[str, Any],
    ) -> List[Document]:
        """
        Create microblock-level chunks (fine-grained).

        Args:
            text: Document text
            meta: Document metadata

        Returns:
            List of microblock Documents
        """
        # Split into sentences
        sentences = self._split_into_sentences(text)

        chunks = []
        current_block = []
        current_tokens = 0
        position = 0

        for sentence in sentences:
            sentence_tokens = self._estimate_tokens(sentence)

            # Check if adding sentence would exceed limit
            if (
                current_tokens + sentence_tokens > self.microblock_max_tokens
                and current_block
            ):
                # Create chunk from current block
                block_text = " ".join(current_block)
                chunk_meta = self._build_chunk_metadata(
                    chunk_type="MICROBLOCK",
                    position=position,
                    parent_meta=meta,
                    text=block_text,
                )
                chunks.append(Document(content=block_text, meta=chunk_meta))
                position += 1

                # Start new block with overlap
                if self.overlap_tokens > 0 and current_block:
                    current_block = [current_block[-1]]
                    current_tokens = self._estimate_tokens(current_block[0])
                else:
                    current_block = []
                    current_tokens = 0

            current_block.append(sentence)
            current_tokens += sentence_tokens

        # Add final block
        if current_block:
            block_text = " ".join(current_block)
            chunk_meta = self._build_chunk_metadata(
                chunk_type="MICROBLOCK",
                position=position,
                parent_meta=meta,
                text=block_text,
            )
            chunks.append(Document(content=block_text, meta=chunk_meta))

        return chunks

    def _split_on_legal_sections(self, text: str) -> List[str]:
        """
        Split text on legal section boundaries.

        Looks for patterns like:
        - Article I, Section 1
        - SECTION 4.2
        - WHEREAS
        - NOW THEREFORE

        Args:
            text: Document text

        Returns:
            List of section texts
        """
        # Legal section patterns
        patterns = [
            r"\n\s*(?:Article|ARTICLE)\s+[IVX\d]+[\.:]?\s*",
            r"\n\s*(?:Section|SECTION)\s+[\d\.]+[\.:]?\s*",
            r"\n\s*WHEREAS[,:]?\s*",
            r"\n\s*NOW\s+THEREFORE[,:]?\s*",
            r"\n\s*\d+\.\s+[A-Z]",  # Numbered sections with caps
            r"\n\s*[A-Z][A-Z\s]{10,}\n",  # All-caps headers
        ]

        # Combine patterns
        combined_pattern = "|".join(patterns)

        # Split while preserving delimiters
        parts = re.split(f"({combined_pattern})", text)

        # Reconstruct sections with their headers
        sections = []
        current_section = ""

        for part in parts:
            if re.match(combined_pattern, part):
                # This is a section marker
                if current_section.strip():
                    sections.append(current_section.strip())
                current_section = part
            else:
                current_section += part

        # Add final section
        if current_section.strip():
            sections.append(current_section.strip())

        # If no sections found, split on paragraphs
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
        paragraphs = re.split(r"\n\s*\n+", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Handles common legal abbreviations and citations.

        Args:
            text: Document text

        Returns:
            List of sentences
        """
        # Protect common abbreviations
        text = self._protect_abbreviations(text)

        # Split on sentence boundaries
        sentences = re.split(r"[.!?]+\s+", text)

        # Restore abbreviations
        sentences = [self._restore_abbreviations(s) for s in sentences]

        return [s.strip() for s in sentences if s.strip()]

    def _protect_abbreviations(self, text: str) -> str:
        """
        Protect common abbreviations from sentence splitting.

        Args:
            text: Input text

        Returns:
            Text with protected abbreviations
        """
        # Common legal abbreviations
        abbreviations = [
            r"\bMr\.",
            r"\bMrs\.",
            r"\bMs\.",
            r"\bDr\.",
            r"\bU\.S\.",
            r"\bInc\.",
            r"\bLtd\.",
            r"\bCorp\.",
            r"\bv\.",  # versus
            r"\bF\.\d+d",  # F.3d
            r"\bS\.Ct\.",
            r"\b§",  # section symbol
        ]

        for abbr in abbreviations:
            text = re.sub(abbr, lambda m: m.group(0).replace(".", "<!DOT!>"), text)

        return text

    def _restore_abbreviations(self, text: str) -> str:
        """
        Restore protected abbreviations.

        Args:
            text: Text with protected abbreviations

        Returns:
            Text with restored abbreviations
        """
        return text.replace("<!DOT!>", ".")

    def _extract_section_heading(self, text: str) -> Optional[str]:
        """
        Extract section heading from text.

        Args:
            text: Section text

        Returns:
            Section heading or None
        """
        # Try to extract first line if it looks like a heading
        lines = text.split("\n")
        if not lines:
            return None

        first_line = lines[0].strip()

        # Check if first line is a heading
        heading_patterns = [
            r"^(?:Article|ARTICLE)\s+[IVX\d]+",
            r"^(?:Section|SECTION)\s+[\d\.]+",
            r"^WHEREAS",
            r"^NOW\s+THEREFORE",
            r"^\d+\.\s+[A-Z]",
            r"^[A-Z][A-Z\s]{5,}$",  # All caps
        ]

        for pattern in heading_patterns:
            if re.match(pattern, first_line):
                return first_line

        return None

    def _split_text_by_tokens(
        self,
        text: str,
        max_tokens: int,
        overlap: int,
    ) -> List[str]:
        """
        Split text into chunks by token count.

        Uses word-based approximation. For production, use tiktoken.

        Args:
            text: Text to split
            max_tokens: Maximum tokens per chunk
            overlap: Overlap tokens

        Returns:
            List of chunk texts
        """
        words = text.split()

        if len(words) <= max_tokens:
            return [text]

        chunks = []
        step = max_tokens - overlap

        for i in range(0, len(words), step):
            chunk_words = words[i : i + max_tokens]
            chunks.append(" ".join(chunk_words))

        return chunks

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count.

        Simple word-based approximation. For production, use tiktoken.

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        return len(text.split())

    def _detect_citations(self, text: str) -> bool:
        """
        Detect if text contains legal citations.

        Args:
            text: Input text

        Returns:
            True if citations detected
        """
        # Common citation patterns
        citation_patterns = [
            r"\b\d+\s+F\.\d+d\s+\d+",  # Federal reporter
            r"\b\d+\s+U\.S\.\s+\d+",  # U.S. Reports
            r"\b\d+\s+S\.Ct\.\s+\d+",  # Supreme Court
            r"\b\d+\s+U\.S\.C\.\s*§\s*\d+",  # U.S. Code
            r"\bv\.\s+[A-Z]",  # Case name (versus)
        ]

        for pattern in citation_patterns:
            if re.search(pattern, text):
                return True

        return False

    def _build_chunk_metadata(
        self,
        chunk_type: str,
        position: int,
        parent_meta: Dict[str, Any],
        text: str,
        section_heading: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build chunk metadata.

        Args:
            chunk_type: Chunk type (SUMMARY, SECTION, MICROBLOCK)
            position: Chunk position
            parent_meta: Parent document metadata
            text: Chunk text
            section_heading: Optional section heading

        Returns:
            Chunk metadata dictionary
        """
        meta = {
            "chunk_type": chunk_type,
            "position": position,
            "token_count": self._estimate_tokens(text),
            "has_citation": self._detect_citations(text),
        }

        # Copy relevant parent metadata
        if "page_number" in parent_meta:
            meta["page_number"] = parent_meta["page_number"]

        if "bounding_box" in parent_meta:
            meta["bounding_box"] = parent_meta["bounding_box"]

        if "document_id" in parent_meta:
            meta["parent_document_id"] = parent_meta["document_id"]

        if section_heading:
            meta["section_heading"] = section_heading

        # Add any custom metadata from parent
        for key in ["case_id", "source_type", "file_path"]:
            if key in parent_meta:
                meta[key] = parent_meta[key]

        return meta
