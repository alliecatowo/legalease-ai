"""
GetFindingsQuery for retrieving findings from a research run.

This module implements CQRS query pattern for fetching research findings
with optional filtering by type, confidence, and relevance.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.domain.research.entities.finding import FindingType
from app.domain.research.repositories.research_repository import FindingRepository


logger = logging.getLogger(__name__)


@dataclass
class GetFindingsQuery:
    """
    Query for retrieving findings from a research run.

    Supports filtering by finding type, confidence threshold,
    relevance threshold, and tags with pagination.

    Attributes:
        research_run_id: ID of the research run
        finding_types: Optional filter by finding types
        min_confidence: Optional minimum confidence threshold (0.0-1.0)
        min_relevance: Optional minimum relevance threshold (0.0-1.0)
        tags: Optional filter by tags
        limit: Maximum number of results
        offset: Pagination offset

    Example:
        >>> query = GetFindingsQuery(
        ...     research_run_id=run_uuid,
        ...     finding_types=[FindingType.FACT, FindingType.QUOTE],
        ...     min_confidence=0.7,
        ...     limit=50,
        ... )
    """

    research_run_id: UUID
    finding_types: Optional[List[FindingType]] = None
    min_confidence: Optional[float] = None
    min_relevance: Optional[float] = None
    tags: Optional[List[str]] = None
    limit: int = 100
    offset: int = 0

    def __post_init__(self) -> None:
        """Validate query parameters."""
        if self.limit < 1 or self.limit > 1000:
            raise ValueError(f"limit must be between 1 and 1000, got {self.limit}")

        if self.offset < 0:
            raise ValueError(f"offset must be >= 0, got {self.offset}")

        if self.min_confidence is not None:
            if not 0.0 <= self.min_confidence <= 1.0:
                raise ValueError(f"min_confidence must be 0.0-1.0, got {self.min_confidence}")

        if self.min_relevance is not None:
            if not 0.0 <= self.min_relevance <= 1.0:
                raise ValueError(f"min_relevance must be 0.0-1.0, got {self.min_relevance}")


@dataclass
class FindingDTO:
    """
    Data Transfer Object for Finding entity.

    Never expose domain entities directly - use DTOs to decouple
    domain layer from application/API layers.

    Attributes:
        id: Finding ID
        research_run_id: Research run ID
        finding_type: Type of finding
        text: Finding description
        entities: Referenced entity IDs
        citations: Supporting citation IDs
        confidence: Confidence score (0.0-1.0)
        relevance: Relevance score (0.0-1.0)
        tags: Categorical tags
        created_at: When finding was created
        metadata: Additional metadata
    """

    id: UUID
    research_run_id: UUID
    finding_type: FindingType
    text: str
    entities: List[UUID]
    citations: List[UUID]
    confidence: float
    relevance: float
    tags: List[str]
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GetFindingsResult:
    """
    Result of GetFindingsQuery.

    Attributes:
        findings: List of finding DTOs
        total: Total count (for pagination)
    """

    findings: List[FindingDTO]
    total: int


class GetFindingsQueryHandler:
    """
    Handler for retrieving findings from a research run.

    Queries the finding repository with filters and converts
    domain entities to DTOs for application layer consumption.
    """

    def __init__(self, finding_repo: FindingRepository):
        """
        Initialize handler with dependencies.

        Args:
            finding_repo: Repository for finding persistence
        """
        self.repo = finding_repo
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def handle(self, query: GetFindingsQuery) -> GetFindingsResult:
        """
        Execute the query and return findings.

        Steps:
        1. Fetch findings from repository
        2. Apply filters (type, confidence, relevance, tags)
        3. Apply pagination
        4. Convert to DTOs
        5. Return results

        Args:
            query: The query to execute

        Returns:
            GetFindingsResult with findings and total count

        Raises:
            ValueError: If query is invalid
            RuntimeError: If repository query fails
        """
        self.logger.info(
            "Fetching findings",
            extra={
                "research_run_id": query.research_run_id,
                "limit": query.limit,
                "offset": query.offset,
            }
        )

        try:
            # 1. Fetch all findings for research run
            all_findings = await self.repo.find_by_research_run(query.research_run_id)

            # 2. Apply filters
            filtered_findings = self._apply_filters(all_findings, query)

            # 3. Sort by relevance (descending), then confidence
            sorted_findings = sorted(
                filtered_findings,
                key=lambda f: (f.relevance, f.confidence),
                reverse=True
            )

            # 4. Apply pagination
            total_count = len(sorted_findings)
            paginated_findings = sorted_findings[query.offset:query.offset + query.limit]

            # 5. Convert to DTOs
            finding_dtos = [self._to_dto(f) for f in paginated_findings]

            self.logger.info(
                "Findings retrieved successfully",
                extra={
                    "total_found": total_count,
                    "returned": len(finding_dtos),
                }
            )

            return GetFindingsResult(
                findings=finding_dtos,
                total=total_count,
            )

        except Exception as e:
            self.logger.error(
                f"Failed to retrieve findings: {e}",
                extra={"research_run_id": query.research_run_id},
                exc_info=True
            )
            raise RuntimeError(f"Failed to retrieve findings: {e}") from e

    def _apply_filters(self, findings: List[Any], query: GetFindingsQuery) -> List[Any]:
        """Apply filters to findings list."""
        filtered = findings

        # Filter by finding type
        if query.finding_types:
            filtered = [
                f for f in filtered
                if f.finding_type in query.finding_types
            ]

        # Filter by confidence
        if query.min_confidence is not None:
            filtered = [
                f for f in filtered
                if f.confidence >= query.min_confidence
            ]

        # Filter by relevance
        if query.min_relevance is not None:
            filtered = [
                f for f in filtered
                if f.relevance >= query.min_relevance
            ]

        # Filter by tags
        if query.tags:
            filtered = [
                f for f in filtered
                if any(tag in f.tags for tag in query.tags)
            ]

        return filtered

    def _to_dto(self, finding: Any) -> FindingDTO:
        """
        Convert domain Finding entity to DTO.

        Args:
            finding: Domain finding entity

        Returns:
            FindingDTO
        """
        # Assuming finding has metadata with created_at timestamp
        created_at = finding.metadata.get("created_at")
        if isinstance(created_at, datetime):
            created_at_str = created_at.isoformat()
        elif created_at is None:
            created_at_str = datetime.utcnow().isoformat()
        else:
            created_at_str = str(created_at)

        return FindingDTO(
            id=finding.id,
            research_run_id=finding.research_run_id,
            finding_type=finding.finding_type,
            text=finding.text,
            entities=finding.entities.copy(),
            citations=finding.citations.copy(),
            confidence=finding.confidence,
            relevance=finding.relevance,
            tags=finding.tags.copy(),
            created_at=created_at_str,
            metadata=finding.metadata.copy() if finding.metadata else {},
        )
