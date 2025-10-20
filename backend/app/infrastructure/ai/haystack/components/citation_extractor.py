"""
Custom Haystack component for extracting and normalizing legal citations.

This component detects, parses, and normalizes legal citations from documents,
including case law, statutes, regulations, and internal cross-references.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from haystack import component, Document

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """Parsed legal citation with normalized components."""

    text: str  # Original citation text
    citation_type: str  # CASE, STATUTE, REGULATION, CROSS_REFERENCE
    normalized: str  # Normalized Bluebook format
    components: Dict[str, Any]  # Parsed components
    start_char: int  # Start position in text
    end_char: int  # End position in text
    confidence: float = 1.0  # Extraction confidence (0.0-1.0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for metadata storage."""
        return {
            "text": self.text,
            "type": self.citation_type,
            "normalized": self.normalized,
            "components": self.components,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "confidence": self.confidence,
        }


@component
class CitationExtractor:
    """
    Extract and normalize legal citations from documents.

    This component detects various citation types:
    - **Case citations**: "Smith v. Jones, 123 F.3d 456 (9th Cir. 2020)"
    - **Statute citations**: "18 U.S.C. § 1234", "Cal. Penal Code § 187"
    - **Regulation citations**: "26 C.F.R. § 1.501(c)(3)"
    - **Internal references**: "See Section 4.2 above"

    Citations are parsed, normalized to Bluebook format, and added to
    document metadata for tracking and linking.

    **Metadata Added:**
    - citations: List of citation dictionaries
    - has_citations: Boolean flag
    - citation_count: Number of citations found

    Usage:
        ```python
        extractor = CitationExtractor(
            normalize_citations=True,
            detect_variants=True
        )
        result = extractor.run(documents=documents)
        enriched_docs = result["documents"]
        ```
    """

    def __init__(
        self,
        normalize_citations: bool = True,
        detect_variants: bool = True,
        min_confidence: float = 0.5,
    ):
        """
        Initialize the citation extractor.

        Args:
            normalize_citations: Normalize citations to Bluebook format
            detect_variants: Detect citation variants (same case, different format)
            min_confidence: Minimum confidence threshold for extraction
        """
        self.normalize_citations = normalize_citations
        self.detect_variants = detect_variants
        self.min_confidence = min_confidence

        # Compile regex patterns for performance
        self._compile_patterns()

        logger.info(
            f"Initialized CitationExtractor(normalize={normalize_citations}, "
            f"detect_variants={detect_variants})"
        )

    def _compile_patterns(self):
        """Compile regex patterns for citation detection."""
        # Case citation patterns
        self.case_patterns = [
            # Federal reporters: "123 F.3d 456"
            re.compile(
                r"\b(\d+)\s+(F\.\d?d?|U\.S\.|S\.Ct\.|L\.Ed\.2d)\s+(\d+)",
                re.IGNORECASE,
            ),
            # State reporters: "123 Cal.App.4th 456"
            re.compile(
                r"\b(\d+)\s+([A-Z][a-z]+\.(?:App\.)?(?:\d?[a-z]{2})?)\s+(\d+)",
                re.IGNORECASE,
            ),
            # Case names with v.: "Smith v. Jones"
            re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+v\.\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"),
        ]

        # Statute citation patterns
        self.statute_patterns = [
            # U.S.C.: "18 U.S.C. § 1234"
            re.compile(r"\b(\d+)\s+U\.S\.C\.\s*§\s*(\d+(?:\([a-z0-9]+\))?)", re.IGNORECASE),
            # State codes: "Cal. Penal Code § 187"
            re.compile(
                r"\b([A-Z][a-z]+\.)\s+([A-Za-z]+\.?\s+)?Code\s*§\s*(\d+(?:\.[a-z0-9]+)?)",
                re.IGNORECASE,
            ),
            # CFR: "26 C.F.R. § 1.501(c)(3)"
            re.compile(
                r"\b(\d+)\s+C\.F\.R\.\s*§\s*([\d\.]+(?:\([a-z0-9]+\))*)",
                re.IGNORECASE,
            ),
        ]

        # Cross-reference patterns
        self.cross_ref_patterns = [
            # "Section 4.2", "§ 4.2"
            re.compile(r"\b(?:Section|§)\s+([\d\.]+)", re.IGNORECASE),
            # "supra note 5", "infra Part II"
            re.compile(r"\b(supra|infra)\s+([A-Za-z]+\s+[IVX\d\.]+)", re.IGNORECASE),
            # "Id." or "Id. at 123"
            re.compile(r"\bId\.\s*(?:at\s+(\d+))?", re.IGNORECASE),
        ]

    @component.output_types(documents=List[Document])
    def run(self, documents: List[Document]) -> Dict[str, List[Document]]:
        """
        Extract citations from documents and enrich metadata.

        Args:
            documents: List of Documents to process

        Returns:
            Dictionary with "documents" key containing enriched Documents
        """
        enriched_documents = []

        for doc in documents:
            try:
                enriched_doc = self._extract_citations(doc)
                enriched_documents.append(enriched_doc)
            except Exception as e:
                logger.error(f"Failed to extract citations from document: {e}")
                # On error, include original document
                enriched_documents.append(doc)

        total_citations = sum(
            len(doc.meta.get("citations", [])) for doc in enriched_documents
        )
        logger.info(
            f"Extracted {total_citations} citations from {len(documents)} documents"
        )

        return {"documents": enriched_documents}

    def _extract_citations(self, document: Document) -> Document:
        """
        Extract citations from a single document.

        Args:
            document: Document to process

        Returns:
            Document with enriched citation metadata
        """
        text = document.content or ""
        citations = []

        # Extract case citations
        citations.extend(self._extract_case_citations(text))

        # Extract statute citations
        citations.extend(self._extract_statute_citations(text))

        # Extract cross-references
        citations.extend(self._extract_cross_references(text))

        # Filter by confidence
        citations = [c for c in citations if c.confidence >= self.min_confidence]

        # Detect variants if enabled
        if self.detect_variants:
            citations = self._merge_citation_variants(citations)

        # Sort by position in text
        citations.sort(key=lambda c: c.start_char)

        # Build enriched metadata
        meta = document.meta.copy() if document.meta else {}
        meta["citations"] = [c.to_dict() for c in citations]
        meta["has_citations"] = len(citations) > 0
        meta["citation_count"] = len(citations)

        return Document(content=document.content, meta=meta)

    def _extract_case_citations(self, text: str) -> List[Citation]:
        """
        Extract case law citations.

        Args:
            text: Document text

        Returns:
            List of case Citations
        """
        citations = []

        for pattern in self.case_patterns:
            for match in pattern.finditer(text):
                citation = self._parse_case_citation(match, text)
                if citation:
                    citations.append(citation)

        return citations

    def _parse_case_citation(
        self,
        match: re.Match,
        text: str,
    ) -> Optional[Citation]:
        """
        Parse a case citation match.

        Args:
            match: Regex match object
            text: Full text

        Returns:
            Parsed Citation or None
        """
        citation_text = match.group(0)
        start_char = match.start()
        end_char = match.end()

        # Try to expand citation to include case name and year
        expanded_text, expanded_start, expanded_end = self._expand_case_citation(
            text, start_char, end_char
        )

        # Parse components
        components = self._parse_case_components(expanded_text)

        if not components:
            return None

        # Normalize if enabled
        if self.normalize_citations:
            normalized = self._normalize_case_citation(components)
        else:
            normalized = expanded_text

        return Citation(
            text=expanded_text,
            citation_type="CASE",
            normalized=normalized,
            components=components,
            start_char=expanded_start,
            end_char=expanded_end,
            confidence=0.9,
        )

    def _expand_case_citation(
        self,
        text: str,
        start: int,
        end: int,
    ) -> Tuple[str, int, int]:
        """
        Expand citation to include case name and year.

        Looks backward for case name and forward for year/court.

        Args:
            text: Full text
            start: Citation start position
            end: Citation end position

        Returns:
            Tuple of (expanded_text, new_start, new_end)
        """
        # Look backward for case name (up to 100 chars)
        window_start = max(0, start - 100)
        prefix = text[window_start:start]

        # Find case name pattern (e.g., "Smith v. Jones, ")
        case_name_match = re.search(
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+v\.\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[,\s]*$",
            prefix,
        )

        if case_name_match:
            new_start = window_start + case_name_match.start()
        else:
            new_start = start

        # Look forward for year and court (up to 50 chars)
        window_end = min(len(text), end + 50)
        suffix = text[end:window_end]

        # Find year/court pattern (e.g., " (9th Cir. 2020)")
        year_match = re.search(
            r"\s*\(([A-Za-z0-9\.\s]+)?\s*(\d{4})\)",
            suffix,
        )

        if year_match:
            new_end = end + year_match.end()
        else:
            new_end = end

        return text[new_start:new_end], new_start, new_end

    def _parse_case_components(self, citation_text: str) -> Dict[str, Any]:
        """
        Parse case citation into components.

        Args:
            citation_text: Citation text

        Returns:
            Dictionary of components
        """
        components = {}

        # Extract parties (case name)
        parties_match = re.search(
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+v\.\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            citation_text,
        )
        if parties_match:
            components["plaintiff"] = parties_match.group(1)
            components["defendant"] = parties_match.group(2)
            components["parties"] = f"{parties_match.group(1)} v. {parties_match.group(2)}"

        # Extract volume, reporter, page
        reporter_match = re.search(
            r"\b(\d+)\s+(F\.\d?d?|U\.S\.|S\.Ct\.|L\.Ed\.2d|[A-Z][a-z]+\.(?:App\.)?(?:\d?[a-z]{2})?)\s+(\d+)",
            citation_text,
            re.IGNORECASE,
        )
        if reporter_match:
            components["volume"] = reporter_match.group(1)
            components["reporter"] = reporter_match.group(2)
            components["page"] = reporter_match.group(3)

        # Extract year
        year_match = re.search(r"\(.*?(\d{4})\)", citation_text)
        if year_match:
            components["year"] = year_match.group(1)

        # Extract court
        court_match = re.search(r"\(([A-Za-z0-9\.\s]+?)\s+\d{4}\)", citation_text)
        if court_match:
            components["court"] = court_match.group(1).strip()

        return components if components else None

    def _normalize_case_citation(self, components: Dict[str, Any]) -> str:
        """
        Normalize case citation to Bluebook format.

        Args:
            components: Parsed components

        Returns:
            Normalized citation string
        """
        parts = []

        # Case name
        if "parties" in components:
            parts.append(components["parties"])

        # Reporter cite
        if all(k in components for k in ["volume", "reporter", "page"]):
            parts.append(
                f"{components['volume']} {components['reporter']} {components['page']}"
            )

        # Court and year
        court_year = []
        if "court" in components:
            court_year.append(components["court"])
        if "year" in components:
            court_year.append(components["year"])

        if court_year:
            parts.append(f"({' '.join(court_year)})")

        return ", ".join(parts) if parts else ""

    def _extract_statute_citations(self, text: str) -> List[Citation]:
        """
        Extract statute citations.

        Args:
            text: Document text

        Returns:
            List of statute Citations
        """
        citations = []

        for pattern in self.statute_patterns:
            for match in pattern.finditer(text):
                citation = self._parse_statute_citation(match)
                if citation:
                    citations.append(citation)

        return citations

    def _parse_statute_citation(self, match: re.Match) -> Optional[Citation]:
        """
        Parse a statute citation match.

        Args:
            match: Regex match object

        Returns:
            Parsed Citation or None
        """
        citation_text = match.group(0)

        # Determine statute type
        if "U.S.C." in citation_text:
            statute_type = "federal"
            title = match.group(1)
            section = match.group(2)
            components = {
                "type": statute_type,
                "title": title,
                "section": section,
                "code": "U.S.C.",
            }
            normalized = f"{title} U.S.C. § {section}"

        elif "C.F.R." in citation_text:
            statute_type = "regulation"
            title = match.group(1)
            section = match.group(2)
            components = {
                "type": statute_type,
                "title": title,
                "section": section,
                "code": "C.F.R.",
            }
            normalized = f"{title} C.F.R. § {section}"

        else:
            # State code
            statute_type = "state"
            state = match.group(1)
            code_name = match.group(2) if match.lastindex >= 2 else ""
            section = match.group(match.lastindex)
            components = {
                "type": statute_type,
                "state": state,
                "code": code_name.strip() if code_name else "Code",
                "section": section,
            }
            normalized = f"{state} {code_name}Code § {section}".replace("  ", " ")

        return Citation(
            text=citation_text,
            citation_type="STATUTE",
            normalized=normalized,
            components=components,
            start_char=match.start(),
            end_char=match.end(),
            confidence=0.95,
        )

    def _extract_cross_references(self, text: str) -> List[Citation]:
        """
        Extract internal cross-references.

        Args:
            text: Document text

        Returns:
            List of cross-reference Citations
        """
        citations = []

        for pattern in self.cross_ref_patterns:
            for match in pattern.finditer(text):
                citation = self._parse_cross_reference(match)
                if citation:
                    citations.append(citation)

        return citations

    def _parse_cross_reference(self, match: re.Match) -> Optional[Citation]:
        """
        Parse a cross-reference match.

        Args:
            match: Regex match object

        Returns:
            Parsed Citation or None
        """
        citation_text = match.group(0)

        # Determine reference type
        if "Id." in citation_text or "id." in citation_text:
            ref_type = "id"
            components = {"type": ref_type}
            if match.lastindex and match.group(match.lastindex):
                components["page"] = match.group(match.lastindex)
            normalized = citation_text

        elif match.group(0).lower().startswith(("supra", "infra")):
            ref_type = match.group(1).lower()
            target = match.group(2) if match.lastindex >= 2 else ""
            components = {"type": ref_type, "target": target}
            normalized = f"{ref_type.capitalize()} {target}"

        else:
            # Section reference
            ref_type = "section"
            section = match.group(1)
            components = {"type": ref_type, "section": section}
            normalized = f"§ {section}"

        return Citation(
            text=citation_text,
            citation_type="CROSS_REFERENCE",
            normalized=normalized,
            components=components,
            start_char=match.start(),
            end_char=match.end(),
            confidence=0.8,
        )

    def _merge_citation_variants(self, citations: List[Citation]) -> List[Citation]:
        """
        Merge citation variants (same case cited different ways).

        Args:
            citations: List of citations

        Returns:
            Deduplicated list of citations
        """
        # Group citations by normalized form
        citation_groups = {}

        for citation in citations:
            key = citation.normalized.lower()

            if key in citation_groups:
                # Merge with existing citation
                existing = citation_groups[key]
                # Keep the one with higher confidence
                if citation.confidence > existing.confidence:
                    citation_groups[key] = citation
            else:
                citation_groups[key] = citation

        return list(citation_groups.values())
