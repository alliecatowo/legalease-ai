"""
RAGFlow-style template-based chunking for legal documents.

This module provides chunking strategies specifically designed for legal documents,
with support for different document types (case law, contracts, statutes, briefs)
and multi-size chunking (512/256/128 tokens).
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import tiktoken


class LegalDocumentTemplate(str, Enum):
    """Legal document templates for specialized chunking."""

    CASE_LAW = "case_law"
    CONTRACT = "contract"
    STATUTE = "statute"
    BRIEF = "brief"
    GENERAL = "general"


@dataclass
class ChunkMetadata:
    """Metadata for a document chunk."""

    chunk_type: str
    position: int
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    token_count: int = 0
    citations: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "chunk_type": self.chunk_type,
            "position": self.position,
            "page_number": self.page_number,
            "section_title": self.section_title,
            "token_count": self.token_count,
            "citations": self.citations,
            **self.custom_fields
        }


@dataclass
class DocumentChunk:
    """Represents a chunk of a document."""

    text: str
    metadata: ChunkMetadata

    def __len__(self) -> int:
        """Return token count of the chunk."""
        return self.metadata.token_count


class BaseChunker(ABC):
    """Abstract base class for document chunking strategies."""

    def __init__(self, encoding_name: str = "cl100k_base"):
        """
        Initialize the chunker.

        Args:
            encoding_name: The tokenizer encoding to use (default: cl100k_base for GPT-4)
        """
        self.encoding = tiktoken.get_encoding(encoding_name)

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))

    def split_by_tokens(self, text: str, max_tokens: int, overlap: int = 0) -> List[str]:
        """
        Split text into chunks by token count with optional overlap.

        Args:
            text: Text to split
            max_tokens: Maximum tokens per chunk
            overlap: Number of tokens to overlap between chunks

        Returns:
            List of text chunks
        """
        tokens = self.encoding.encode(text)
        chunks = []

        start = 0
        while start < len(tokens):
            end = min(start + max_tokens, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoding.decode(chunk_tokens)
            chunks.append(chunk_text)

            if end >= len(tokens):
                break

            start = end - overlap

        return chunks

    @abstractmethod
    def chunk(
        self,
        document_text: str,
        preserve_structure: bool = True,
        **kwargs
    ) -> List[DocumentChunk]:
        """
        Chunk a document into smaller pieces.

        Args:
            document_text: The full text of the document
            preserve_structure: Whether to preserve document structure
            **kwargs: Additional chunking parameters

        Returns:
            List of DocumentChunk objects
        """
        pass

    def extract_citations(self, text: str) -> List[str]:
        """
        Extract legal citations from text.

        Common patterns:
        - Case citations: Smith v. Jones, 123 F.3d 456 (9th Cir. 2000)
        - Statute citations: 42 U.S.C. § 1983
        - Short citations: Id. at 123

        Args:
            text: Text to extract citations from

        Returns:
            List of citation strings
        """
        citations = []

        # Case citations (e.g., "123 F.3d 456", "456 U.S. 123")
        case_pattern = r'\d+\s+[A-Z]\.\s*(?:\d+d|2d|3d|Supp\.)?\s*\d+'
        citations.extend(re.findall(case_pattern, text))

        # Statute citations (e.g., "42 U.S.C. § 1983")
        statute_pattern = r'\d+\s+U\.S\.C\.\s*§\s*\d+(?:\([a-z]\))?'
        citations.extend(re.findall(statute_pattern, text))

        # Code of Federal Regulations (e.g., "29 C.F.R. § 1630.2(i)")
        cfr_pattern = r'\d+\s+C\.F\.R\.\s*§\s*[\d.]+(?:\([a-z]\))?'
        citations.extend(re.findall(cfr_pattern, text))

        # Id. citations
        id_pattern = r'Id\.\s+at\s+\d+'
        citations.extend(re.findall(id_pattern, text))

        return citations


class LegalDocumentChunker(BaseChunker):
    """
    Specialized chunker for legal documents with template-based strategies.

    Supports different templates for different legal document types and
    creates multi-size chunks (512/256/128 tokens) for flexible retrieval.
    """

    def __init__(
        self,
        template: str = "general",
        chunk_sizes: List[int] = None,
        overlap: int = 50,
        encoding_name: str = "cl100k_base"
    ):
        """
        Initialize the legal document chunker.

        Args:
            template: Document template type (case_law, contract, statute, brief, general)
            chunk_sizes: List of chunk sizes in tokens (default: [512, 256, 128])
            overlap: Number of tokens to overlap between chunks
            encoding_name: Tokenizer encoding to use
        """
        super().__init__(encoding_name)
        self.template = LegalDocumentTemplate(template)
        self.chunk_sizes = chunk_sizes or [512, 256, 128]
        self.overlap = overlap

    def chunk(
        self,
        document_text: str,
        preserve_structure: bool = True,
        page_breaks: Optional[List[int]] = None,
        **kwargs
    ) -> List[DocumentChunk]:
        """
        Chunk a legal document based on its template type.

        Args:
            document_text: The full text of the document
            preserve_structure: Whether to preserve document structure
            page_breaks: Optional list of character positions where page breaks occur
            **kwargs: Additional parameters (metadata, etc.)

        Returns:
            List of DocumentChunk objects with multiple sizes
        """
        if preserve_structure:
            # First, try to split by structural elements
            if self.template == LegalDocumentTemplate.CASE_LAW:
                structural_chunks = self._chunk_case_law(document_text, page_breaks)
            elif self.template == LegalDocumentTemplate.CONTRACT:
                structural_chunks = self._chunk_contract(document_text, page_breaks)
            elif self.template == LegalDocumentTemplate.STATUTE:
                structural_chunks = self._chunk_statute(document_text, page_breaks)
            elif self.template == LegalDocumentTemplate.BRIEF:
                structural_chunks = self._chunk_brief(document_text, page_breaks)
            else:
                structural_chunks = self._chunk_general(document_text, page_breaks)
        else:
            # Just split by paragraphs if not preserving structure
            structural_chunks = self._chunk_general(document_text, page_breaks)

        # Now create multi-size chunks
        all_chunks = []

        for size in self.chunk_sizes:
            size_chunks = self._create_size_chunks(
                structural_chunks,
                max_tokens=size,
                chunk_type=f"{size}token"
            )
            all_chunks.extend(size_chunks)

        return all_chunks

    def _chunk_case_law(
        self,
        text: str,
        page_breaks: Optional[List[int]] = None
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Chunk case law documents by sections (syllabus, opinion, dissent, etc.).

        Args:
            text: Document text
            page_breaks: Character positions of page breaks

        Returns:
            List of (text, metadata) tuples
        """
        chunks = []

        # Common case law section markers
        section_patterns = [
            (r'(?:^|\n)(?:I+\.?\s+)?SYLLABUS\s*\n', 'syllabus'),
            (r'(?:^|\n)(?:I+\.?\s+)?OPINION(?:\s+OF\s+THE\s+COURT)?\s*\n', 'opinion'),
            (r'(?:^|\n)(?:I+\.?\s+)?CONCURRING\s+OPINION\s*\n', 'concurrence'),
            (r'(?:^|\n)(?:I+\.?\s+)?DISSENTING\s+OPINION\s*\n', 'dissent'),
            (r'(?:^|\n)(?:I+\.?\s+)?FACTS?\s*\n', 'facts'),
            (r'(?:^|\n)(?:I+\.?\s+)?DISCUSSION\s*\n', 'discussion'),
            (r'(?:^|\n)(?:I+\.?\s+)?CONCLUSION\s*\n', 'conclusion'),
        ]

        # Find all section boundaries
        boundaries = []
        for pattern, section_type in section_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                boundaries.append((match.start(), section_type, match.group().strip()))

        # Sort by position
        boundaries.sort(key=lambda x: x[0])

        # Extract sections
        if boundaries:
            for i, (start, section_type, title) in enumerate(boundaries):
                end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
                section_text = text[start:end].strip()

                if section_text:
                    chunks.append((section_text, {
                        'section_type': section_type,
                        'section_title': title
                    }))

        # If no sections found, fall back to paragraph-based chunking
        if not chunks:
            chunks = self._chunk_by_paragraphs(text)

        return chunks

    def _chunk_contract(
        self,
        text: str,
        page_breaks: Optional[List[int]] = None
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Chunk contract documents by articles, sections, and clauses.

        Args:
            text: Document text
            page_breaks: Character positions of page breaks

        Returns:
            List of (text, metadata) tuples
        """
        chunks = []

        # Contract section patterns
        # Matches: "ARTICLE I", "Section 1.1", "1.1 ", "(a) ", etc.
        section_patterns = [
            (r'(?:^|\n)ARTICLE\s+[IVX\d]+[.:]?\s+[^\n]+\n', 'article'),
            (r'(?:^|\n)Section\s+\d+(?:\.\d+)*[.:]?\s+[^\n]+\n', 'section'),
            (r'(?:^|\n)\d+\.\d+(?:\.\d+)*\s+[^\n]+\n', 'subsection'),
        ]

        boundaries = []
        for pattern, section_type in section_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                boundaries.append((match.start(), section_type, match.group().strip()))

        boundaries.sort(key=lambda x: x[0])

        if boundaries:
            for i, (start, section_type, title) in enumerate(boundaries):
                end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
                section_text = text[start:end].strip()

                if section_text:
                    chunks.append((section_text, {
                        'section_type': section_type,
                        'section_title': title
                    }))
        else:
            chunks = self._chunk_by_paragraphs(text)

        return chunks

    def _chunk_statute(
        self,
        text: str,
        page_breaks: Optional[List[int]] = None
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Chunk statutory documents by sections and subsections.

        Args:
            text: Document text
            page_breaks: Character positions of page breaks

        Returns:
            List of (text, metadata) tuples
        """
        chunks = []

        # Statute section patterns (e.g., "§ 1983", "§ 1.1", "Sec. 101")
        section_patterns = [
            (r'(?:^|\n)§\s*\d+(?:\.\d+)*[.:]?\s*[^\n]*\n', 'section'),
            (r'(?:^|\n)Sec(?:tion)?\.?\s+\d+(?:\.\d+)*[.:]?\s*[^\n]*\n', 'section'),
            (r'(?:^|\n)\([a-z]\)\s+', 'subsection'),
            (r'(?:^|\n)\(\d+\)\s+', 'paragraph'),
        ]

        boundaries = []
        for pattern, section_type in section_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                boundaries.append((match.start(), section_type, match.group().strip()))

        boundaries.sort(key=lambda x: x[0])

        if boundaries:
            for i, (start, section_type, title) in enumerate(boundaries):
                end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
                section_text = text[start:end].strip()

                if section_text:
                    chunks.append((section_text, {
                        'section_type': section_type,
                        'section_title': title
                    }))
        else:
            chunks = self._chunk_by_paragraphs(text)

        return chunks

    def _chunk_brief(
        self,
        text: str,
        page_breaks: Optional[List[int]] = None
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Chunk legal briefs by standard sections.

        Args:
            text: Document text
            page_breaks: Character positions of page breaks

        Returns:
            List of (text, metadata) tuples
        """
        chunks = []

        # Brief section patterns
        section_patterns = [
            (r'(?:^|\n)(?:I+\.?\s+)?(?:STATEMENT\s+OF\s+)?JURISDICTION\s*\n', 'jurisdiction'),
            (r'(?:^|\n)(?:I+\.?\s+)?(?:STATEMENT\s+OF\s+(?:THE\s+)?)?ISSUES?\s*(?:PRESENTED)?\s*\n', 'issues'),
            (r'(?:^|\n)(?:I+\.?\s+)?STATEMENT\s+OF\s+(?:THE\s+)?FACTS?\s*\n', 'facts'),
            (r'(?:^|\n)(?:I+\.?\s+)?(?:STATEMENT\s+OF\s+(?:THE\s+)?)?CASE\s*\n', 'case_statement'),
            (r'(?:^|\n)(?:I+\.?\s+)?(?:SUMMARY\s+OF\s+)?ARGUMENT\s*\n', 'summary'),
            (r'(?:^|\n)(?:I+\.?\s+)?ARGUMENT\s*\n', 'argument'),
            (r'(?:^|\n)(?:I+\.?\s+)?CONCLUSION\s*\n', 'conclusion'),
        ]

        boundaries = []
        for pattern, section_type in section_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                boundaries.append((match.start(), section_type, match.group().strip()))

        boundaries.sort(key=lambda x: x[0])

        if boundaries:
            for i, (start, section_type, title) in enumerate(boundaries):
                end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
                section_text = text[start:end].strip()

                if section_text:
                    chunks.append((section_text, {
                        'section_type': section_type,
                        'section_title': title
                    }))
        else:
            chunks = self._chunk_by_paragraphs(text)

        return chunks

    def _chunk_general(
        self,
        text: str,
        page_breaks: Optional[List[int]] = None
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Chunk general documents by paragraphs and headings.

        Args:
            text: Document text
            page_breaks: Character positions of page breaks

        Returns:
            List of (text, metadata) tuples
        """
        return self._chunk_by_paragraphs(text)

    def _chunk_by_paragraphs(self, text: str) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Fallback chunking by paragraphs.

        Args:
            text: Document text

        Returns:
            List of (text, metadata) tuples
        """
        # Split by double newlines (paragraph breaks)
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []

        for para in paragraphs:
            para = para.strip()
            if para:
                chunks.append((para, {'section_type': 'paragraph'}))

        return chunks

    def _create_size_chunks(
        self,
        structural_chunks: List[Tuple[str, Dict[str, Any]]],
        max_tokens: int,
        chunk_type: str
    ) -> List[DocumentChunk]:
        """
        Create chunks of a specific token size from structural chunks.

        Args:
            structural_chunks: List of (text, metadata) tuples from structural chunking
            max_tokens: Maximum tokens per chunk
            chunk_type: Type label for these chunks

        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        position = 0

        for text, section_metadata in structural_chunks:
            token_count = self.count_tokens(text)

            if token_count <= max_tokens:
                # Chunk fits in one piece
                citations = self.extract_citations(text)
                metadata = ChunkMetadata(
                    chunk_type=chunk_type,
                    position=position,
                    section_title=section_metadata.get('section_title'),
                    token_count=token_count,
                    citations=citations,
                    custom_fields={
                        'section_type': section_metadata.get('section_type', 'unknown')
                    }
                )
                chunks.append(DocumentChunk(text=text, metadata=metadata))
                position += 1
            else:
                # Split into multiple chunks
                sub_chunks = self.split_by_tokens(text, max_tokens, self.overlap)
                for sub_text in sub_chunks:
                    sub_token_count = self.count_tokens(sub_text)
                    citations = self.extract_citations(sub_text)
                    metadata = ChunkMetadata(
                        chunk_type=chunk_type,
                        position=position,
                        section_title=section_metadata.get('section_title'),
                        token_count=sub_token_count,
                        citations=citations,
                        custom_fields={
                            'section_type': section_metadata.get('section_type', 'unknown'),
                            'is_split': True
                        }
                    )
                    chunks.append(DocumentChunk(text=sub_text, metadata=metadata))
                    position += 1

        return chunks


def create_chunker(
    template: str = "general",
    chunk_sizes: List[int] = None,
    overlap: int = 50,
    encoding_name: str = "cl100k_base"
) -> LegalDocumentChunker:
    """
    Factory function to create a legal document chunker.

    Args:
        template: Document template type (case_law, contract, statute, brief, general)
        chunk_sizes: List of chunk sizes in tokens (default: [512, 256, 128])
        overlap: Number of tokens to overlap between chunks
        encoding_name: Tokenizer encoding to use

    Returns:
        LegalDocumentChunker instance
    """
    return LegalDocumentChunker(
        template=template,
        chunk_sizes=chunk_sizes,
        overlap=overlap,
        encoding_name=encoding_name
    )
