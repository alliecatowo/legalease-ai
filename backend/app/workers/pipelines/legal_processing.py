"""
Legal Document Processing Pipeline

Combines document parsing and chunking with template selection logic
and metadata extraction for legal documents.
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from app.workers.pipelines.chunking import (
    LegalDocumentChunker,
    DocumentChunk,
    LegalDocumentTemplate,
    create_chunker
)


class DocumentType(str, Enum):
    """Document type classification."""

    CASE_LAW = "case_law"
    CONTRACT = "contract"
    STATUTE = "statute"
    BRIEF = "brief"
    GENERAL = "general"
    UNKNOWN = "unknown"


@dataclass
class LegalMetadata:
    """Metadata extracted from legal documents."""

    document_type: DocumentType
    case_number: Optional[str] = None
    parties: List[str] = field(default_factory=list)
    court: Optional[str] = None
    date_filed: Optional[datetime] = None
    jurisdiction: Optional[str] = None
    judge: Optional[str] = None
    docket_number: Optional[str] = None
    contract_parties: List[str] = field(default_factory=list)
    effective_date: Optional[datetime] = None
    statute_citation: Optional[str] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "document_type": self.document_type.value,
            "case_number": self.case_number,
            "parties": self.parties,
            "court": self.court,
            "date_filed": self.date_filed.isoformat() if self.date_filed else None,
            "jurisdiction": self.jurisdiction,
            "judge": self.judge,
            "docket_number": self.docket_number,
            "contract_parties": self.contract_parties,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "statute_citation": self.statute_citation,
            **self.custom_fields
        }


@dataclass
class ProcessedDocument:
    """Result of document processing pipeline."""

    document_id: Optional[int]
    text: str
    chunks: List[DocumentChunk]
    metadata: LegalMetadata
    chunk_count: int = 0
    processing_time: float = 0.0

    def __post_init__(self):
        """Calculate chunk count after initialization."""
        self.chunk_count = len(self.chunks)


class LegalDocumentPipeline:
    """
    Pipeline for processing legal documents.

    Combines parsing, template selection, metadata extraction, and chunking
    to produce a fully processed document ready for indexing and retrieval.
    """

    def __init__(
        self,
        chunk_sizes: List[int] = None,
        overlap: int = 50,
        encoding_name: str = "cl100k_base"
    ):
        """
        Initialize the legal document processing pipeline.

        Args:
            chunk_sizes: List of chunk sizes in tokens (default: [512, 256, 128])
            overlap: Number of tokens to overlap between chunks
            encoding_name: Tokenizer encoding to use
        """
        self.chunk_sizes = chunk_sizes or [512, 256, 128]
        self.overlap = overlap
        self.encoding_name = encoding_name

    def process(
        self,
        document_text: str,
        document_id: Optional[int] = None,
        template: Optional[str] = None,
        preserve_structure: bool = True
    ) -> ProcessedDocument:
        """
        Process a legal document through the full pipeline.

        Args:
            document_text: Raw text of the document
            document_id: Optional database ID of the document
            template: Optional template override (if None, auto-detect)
            preserve_structure: Whether to preserve document structure during chunking

        Returns:
            ProcessedDocument with chunks and metadata
        """
        import time
        start_time = time.time()

        # Step 1: Detect document type if not provided
        if template is None:
            template = self._detect_document_type(document_text)
        else:
            template = template.lower()

        # Step 2: Extract metadata based on document type
        metadata = self._extract_metadata(document_text, template)

        # Step 3: Create appropriate chunker for the document type
        chunker = create_chunker(
            template=template,
            chunk_sizes=self.chunk_sizes,
            overlap=self.overlap,
            encoding_name=self.encoding_name
        )

        # Step 4: Chunk the document
        chunks = chunker.chunk(document_text, preserve_structure=preserve_structure)

        # Step 5: Calculate processing time
        processing_time = time.time() - start_time

        return ProcessedDocument(
            document_id=document_id,
            text=document_text,
            chunks=chunks,
            metadata=metadata,
            processing_time=processing_time
        )

    def _detect_document_type(self, text: str) -> str:
        """
        Automatically detect the type of legal document.

        Args:
            text: Document text

        Returns:
            Detected template type as string
        """
        text_lower = text.lower()
        text_sample = text[:5000]  # Check first 5000 chars for efficiency

        # Case law indicators
        case_indicators = [
            r'\bv\.\s+\w+',  # "Smith v. Jones"
            r'\bpetitioner\b',
            r'\brespondent\b',
            r'\bappellant\b',
            r'\bappellee\b',
            r'opinion\s+of\s+the\s+court',
            r'dissenting\s+opinion',
            r'\bjustice\s+\w+',
            r'\b\d+\s+F\.\s*\d*d\s+\d+',  # Federal reporter citation
            r'\b\d+\s+U\.S\.\s+\d+',  # U.S. Reports citation
        ]

        case_score = sum(1 for pattern in case_indicators if re.search(pattern, text_sample, re.IGNORECASE))

        # Contract indicators
        contract_indicators = [
            r'\bthis\s+agreement\b',
            r'\bwhereas\b',
            r'\bnow,?\s+therefore\b',
            r'\bhereinafter\s+referred\s+to\s+as\b',
            r'\bparty\s+of\s+the\s+first\s+part\b',
            r'\bin\s+consideration\s+of\b',
            r'\bterms\s+and\s+conditions\b',
            r'\bforce\s+and\s+effect\b',
            r'\bexecuted\s+as\s+of\b',
            r'article\s+[ivx\d]+',
        ]

        contract_score = sum(1 for pattern in contract_indicators if re.search(pattern, text_sample, re.IGNORECASE))

        # Statute indicators
        statute_indicators = [
            r'§\s*\d+',  # Section symbol
            r'\bsection\s+\d+\b',
            r'\bsubsection\s+\([a-z]\)',
            r'\bu\.s\.c\.\b',
            r'\bc\.f\.r\.\b',
            r'\benacted\s+by\b',
            r'\bbe\s+it\s+enacted\b',
            r'\bthe\s+legislature\b',
        ]

        statute_score = sum(1 for pattern in statute_indicators if re.search(pattern, text_sample, re.IGNORECASE))

        # Brief indicators
        brief_indicators = [
            r'\bstatement\s+of\s+jurisdiction\b',
            r'\bstatement\s+of\s+issues?\b',
            r'\bstatement\s+of\s+the\s+case\b',
            r'\bsummary\s+of\s+argument\b',
            r'\bargument\b.*\bconclusion\b',
            r'\brespectfully\s+submitted\b',
            r'\bappellant\'s\s+brief\b',
            r'\bappellee\'s\s+brief\b',
            r'\bpetitioner\'s\s+brief\b',
        ]

        brief_score = sum(1 for pattern in brief_indicators if re.search(pattern, text_sample, re.IGNORECASE))

        # Determine document type based on scores
        scores = {
            'case_law': case_score,
            'contract': contract_score,
            'statute': statute_score,
            'brief': brief_score,
        }

        max_score = max(scores.values())

        if max_score >= 3:  # Confidence threshold
            return max(scores, key=scores.get)
        else:
            return 'general'

    def _extract_metadata(self, text: str, template: str) -> LegalMetadata:
        """
        Extract metadata based on document type.

        Args:
            text: Document text
            template: Document template type

        Returns:
            LegalMetadata object
        """
        metadata = LegalMetadata(document_type=DocumentType(template))

        if template == 'case_law':
            self._extract_case_metadata(text, metadata)
        elif template == 'contract':
            self._extract_contract_metadata(text, metadata)
        elif template == 'statute':
            self._extract_statute_metadata(text, metadata)
        elif template == 'brief':
            self._extract_brief_metadata(text, metadata)

        return metadata

    def _extract_case_metadata(self, text: str, metadata: LegalMetadata) -> None:
        """Extract metadata from case law documents."""
        text_sample = text[:10000]  # First 10k chars

        # Extract case number (various formats)
        case_patterns = [
            r'Case\s+No\.?\s*[:.]?\s*([\d-]+)',
            r'No\.?\s+([\d-]+)',
            r'Docket\s+No\.?\s*[:.]?\s*([\d-]+)',
        ]

        for pattern in case_patterns:
            match = re.search(pattern, text_sample, re.IGNORECASE)
            if match:
                metadata.case_number = match.group(1)
                break

        # Extract parties (e.g., "SMITH v. JONES")
        parties_pattern = r'([A-Z][A-Z\s,\.]+)\s+v\.\s+([A-Z][A-Z\s,\.]+)'
        parties_match = re.search(parties_pattern, text_sample)
        if parties_match:
            metadata.parties = [
                parties_match.group(1).strip(),
                parties_match.group(2).strip()
            ]

        # Extract court
        court_patterns = [
            r'(United\s+States\s+Supreme\s+Court)',
            r'(United\s+States\s+Court\s+of\s+Appeals\s+for\s+the\s+\w+\s+Circuit)',
            r'(United\s+States\s+District\s+Court)',
            r'(\w+\s+Circuit\s+Court)',
            r'(\w+\s+Supreme\s+Court)',
        ]

        for pattern in court_patterns:
            match = re.search(pattern, text_sample, re.IGNORECASE)
            if match:
                metadata.court = match.group(1)
                break

        # Extract judge
        judge_pattern = r'(?:Justice|Judge)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        judge_match = re.search(judge_pattern, text_sample)
        if judge_match:
            metadata.judge = judge_match.group(1)

        # Extract date
        date_patterns = [
            r'(?:Decided|Filed):\s*(\w+\s+\d+,\s+\d{4})',
            r'(\w+\s+\d+,\s+\d{4})',
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text_sample)
            if match:
                try:
                    date_str = match.group(1)
                    # Simple date parsing (could be enhanced with dateutil)
                    metadata.date_filed = self._parse_date(date_str)
                    break
                except:
                    pass

    def _extract_contract_metadata(self, text: str, metadata: LegalMetadata) -> None:
        """Extract metadata from contract documents."""
        text_sample = text[:10000]

        # Extract contract parties
        # Pattern: "between PARTY A and PARTY B"
        parties_pattern = r'(?:between|by\s+and\s+between)\s+([A-Z][^,]+?)\s+(?:and|&)\s+([A-Z][^,]+?)(?:\s*,|\s*\()'
        parties_match = re.search(parties_pattern, text_sample, re.IGNORECASE)
        if parties_match:
            metadata.contract_parties = [
                parties_match.group(1).strip(),
                parties_match.group(2).strip()
            ]

        # Extract effective date
        date_patterns = [
            r'(?:effective|dated)\s+as\s+of\s+(\w+\s+\d+,\s+\d{4})',
            r'this\s+\d+(?:st|nd|rd|th)\s+day\s+of\s+(\w+,\s+\d{4})',
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text_sample, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    metadata.effective_date = self._parse_date(date_str)
                    break
                except:
                    pass

    def _extract_statute_metadata(self, text: str, metadata: LegalMetadata) -> None:
        """Extract metadata from statutory documents."""
        text_sample = text[:5000]

        # Extract statute citation
        citation_patterns = [
            r'(\d+\s+U\.S\.C\.\s*§\s*\d+)',
            r'(\d+\s+C\.F\.R\.\s*§\s*[\d.]+)',
            r'(Title\s+\d+,\s+Section\s+\d+)',
        ]

        for pattern in citation_patterns:
            match = re.search(pattern, text_sample)
            if match:
                metadata.statute_citation = match.group(1)
                break

        # Extract jurisdiction
        jurisdiction_pattern = r'(State\s+of\s+\w+|Federal|United\s+States)'
        jurisdiction_match = re.search(jurisdiction_pattern, text_sample)
        if jurisdiction_match:
            metadata.jurisdiction = jurisdiction_match.group(1)

    def _extract_brief_metadata(self, text: str, metadata: LegalMetadata) -> None:
        """Extract metadata from legal brief documents."""
        text_sample = text[:10000]

        # Extract case number
        case_patterns = [
            r'Case\s+No\.?\s*[:.]?\s*([\d-]+)',
            r'No\.?\s+([\d-]+)',
        ]

        for pattern in case_patterns:
            match = re.search(pattern, text_sample, re.IGNORECASE)
            if match:
                metadata.case_number = match.group(1)
                break

        # Extract parties
        parties_pattern = r'([A-Z][A-Z\s,\.]+)\s+v\.\s+([A-Z][A-Z\s,\.]+)'
        parties_match = re.search(parties_pattern, text_sample)
        if parties_match:
            metadata.parties = [
                parties_match.group(1).strip(),
                parties_match.group(2).strip()
            ]

        # Extract court
        court_patterns = [
            r'IN\s+THE\s+([\w\s]+COURT[\w\s]*)',
            r'BEFORE\s+THE\s+([\w\s]+COURT[\w\s]*)',
        ]

        for pattern in court_patterns:
            match = re.search(pattern, text_sample, re.IGNORECASE)
            if match:
                metadata.court = match.group(1).strip()
                break

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string to datetime.

        Args:
            date_str: Date string to parse

        Returns:
            datetime object or None if parsing fails
        """
        # Common date formats in legal documents
        formats = [
            '%B %d, %Y',  # January 1, 2024
            '%b %d, %Y',  # Jan 1, 2024
            '%m/%d/%Y',   # 01/01/2024
            '%Y-%m-%d',   # 2024-01-01
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue

        return None


def create_pipeline(
    chunk_sizes: List[int] = None,
    overlap: int = 50,
    encoding_name: str = "cl100k_base"
) -> LegalDocumentPipeline:
    """
    Factory function to create a legal document processing pipeline.

    Args:
        chunk_sizes: List of chunk sizes in tokens (default: [512, 256, 128])
        overlap: Number of tokens to overlap between chunks
        encoding_name: Tokenizer encoding to use

    Returns:
        LegalDocumentPipeline instance
    """
    return LegalDocumentPipeline(
        chunk_sizes=chunk_sizes,
        overlap=overlap,
        encoding_name=encoding_name
    )
