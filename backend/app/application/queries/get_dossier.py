"""
GetDossierQuery for retrieving generated research dossier.

This module implements CQRS query pattern for fetching the final
research output document.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any
from uuid import UUID

from app.domain.research.repositories.research_repository import DossierRepository


logger = logging.getLogger(__name__)


@dataclass
class GetDossierQuery:
    """
    Query for retrieving generated dossier.

    Attributes:
        research_run_id: ID of the research run

    Example:
        >>> query = GetDossierQuery(research_run_id=run_uuid)
    """

    research_run_id: UUID


@dataclass
class DossierSectionDTO:
    """
    Data Transfer Object for dossier section.

    Attributes:
        title: Section title
        content: Section content (markdown)
        order: Display order
        metadata: Section metadata
    """

    title: str
    content: str
    order: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DossierDTO:
    """
    Data Transfer Object for Dossier entity.

    Attributes:
        id: Dossier ID
        research_run_id: Research run ID
        executive_summary: Executive summary text
        sections: List of content sections
        citations_appendix: Citations in appendix format
        file_paths: Paths to generated files (PDF, DOCX, etc.)
        generated_at: Generation timestamp
        word_count: Total word count
        metadata: Additional metadata
    """

    id: UUID
    research_run_id: UUID
    executive_summary: str
    sections: List[DossierSectionDTO]
    citations_appendix: str
    file_paths: List[str]
    generated_at: str
    word_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class GetDossierQueryHandler:
    """
    Handler for retrieving research dossier.

    Fetches the dossier from repository and converts to DTO.
    """

    def __init__(self, dossier_repo: DossierRepository):
        """
        Initialize handler with dependencies.

        Args:
            dossier_repo: Repository for dossier persistence
        """
        self.repo = dossier_repo
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def handle(self, query: GetDossierQuery) -> DossierDTO:
        """
        Execute the query and return dossier.

        Args:
            query: The query to execute

        Returns:
            DossierDTO with complete dossier

        Raises:
            ValueError: If dossier not found
            RuntimeError: If query fails
        """
        self.logger.info(
            "Fetching dossier",
            extra={"research_run_id": query.research_run_id}
        )

        try:
            # Fetch dossier
            dossier = await self.repo.get_by_research_run(query.research_run_id)

            if not dossier:
                raise ValueError(f"Dossier not found for research run: {query.research_run_id}")

            # Convert to DTO
            dto = self._to_dto(dossier)

            self.logger.info(
                "Dossier retrieved successfully",
                extra={
                    "research_run_id": query.research_run_id,
                    "word_count": dto.word_count,
                    "sections_count": len(dto.sections),
                }
            )

            return dto

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(
                f"Failed to retrieve dossier: {e}",
                extra={"research_run_id": query.research_run_id},
                exc_info=True
            )
            raise RuntimeError(f"Failed to retrieve dossier: {e}") from e

    def _to_dto(self, dossier: Any) -> DossierDTO:
        """
        Convert domain Dossier entity to DTO.

        Args:
            dossier: Domain dossier entity

        Returns:
            DossierDTO
        """
        # Convert sections
        section_dtos = [
            DossierSectionDTO(
                title=s.title,
                content=s.content,
                order=s.order,
                metadata=s.metadata.copy() if hasattr(s, "metadata") else {},
            )
            for s in dossier.get_sections_ordered()
        ]

        # Get file paths from metadata
        file_paths = dossier.metadata.get("file_paths", [])
        if not isinstance(file_paths, list):
            file_paths = [file_paths] if file_paths else []

        return DossierDTO(
            id=dossier.id,
            research_run_id=dossier.research_run_id,
            executive_summary=dossier.executive_summary,
            sections=section_dtos,
            citations_appendix=dossier.citations_appendix,
            file_paths=file_paths,
            generated_at=dossier.generated_at.isoformat() if dossier.generated_at else "",
            word_count=dossier.get_word_count(),
            metadata=dossier.metadata.copy() if dossier.metadata else {},
        )
