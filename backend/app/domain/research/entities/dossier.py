"""
Dossier entity for the Research domain.

Represents the final research output document with executive summary,
findings, hypotheses, and citations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any
from uuid import UUID


@dataclass(frozen=True)
class DossierSection:
    """
    Immutable section of a dossier.

    Attributes:
        title: Section title
        content: Section content (markdown formatted)
        order: Display order
        metadata: Section-specific metadata
    """

    title: str
    content: str
    order: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Dossier:
    """
    Dossier entity representing the final research document.

    A dossier is the comprehensive output of a research run, containing
    an executive summary, detailed sections, and citations appendix.

    Attributes:
        id: Unique identifier
        research_run_id: ID of the research run
        executive_summary: High-level summary (200-300 words)
        sections: Ordered list of content sections
        citations_appendix: Formatted citations for all sources
        metadata: Additional metadata (word count, generation time, etc.)
        generated_at: When the dossier was generated

    Example:
        >>> dossier = Dossier(
        ...     id=uuid4(),
        ...     research_run_id=uuid4(),
        ...     executive_summary="Analysis reveals...",
        ...     sections=[
        ...         DossierSection("Timeline", "## Timeline\n...", 1),
        ...         DossierSection("Key Findings", "## Findings\n...", 2),
        ...     ],
        ...     citations_appendix="## Citations\n[1] Document...",
        ...     generated_at=datetime.utcnow(),
        ... )
    """

    id: UUID
    research_run_id: UUID
    executive_summary: str
    sections: List[DossierSection]
    citations_appendix: str
    generated_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_word_count(self) -> int:
        """Calculate total word count of the dossier."""
        text = self.executive_summary + " " + self.citations_appendix
        text += " ".join(section.content for section in self.sections)
        return len(text.split())

    def get_section(self, title: str) -> DossierSection | None:
        """Get a section by title."""
        for section in self.sections:
            if section.title == title:
                return section
        return None

    def get_sections_ordered(self) -> List[DossierSection]:
        """Get sections in display order."""
        return sorted(self.sections, key=lambda s: s.order)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Dossier):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
