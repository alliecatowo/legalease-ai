"""
ListResearchRunsQuery for listing research runs for a case.

This module implements CQRS query pattern for fetching all
research runs with optional status filtering.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID

from app.domain.research.entities.research_run import ResearchStatus
from app.domain.research.repositories.research_repository import ResearchRunRepository
from app.application.queries.get_research_status import ResearchStatusDTO


logger = logging.getLogger(__name__)


@dataclass
class ListResearchRunsQuery:
    """
    Query for listing research runs for a case.

    Attributes:
        case_id: Case ID to filter by
        status: Optional status filter
        limit: Maximum results to return
        offset: Pagination offset

    Example:
        >>> query = ListResearchRunsQuery(
        ...     case_id=case_uuid,
        ...     status=ResearchStatus.COMPLETED,
        ...     limit=10,
        ... )
    """

    case_id: UUID
    status: Optional[ResearchStatus] = None
    limit: int = 20
    offset: int = 0

    def __post_init__(self) -> None:
        """Validate query parameters."""
        if self.limit < 1 or self.limit > 100:
            raise ValueError(f"limit must be between 1 and 100, got {self.limit}")

        if self.offset < 0:
            raise ValueError(f"offset must be >= 0, got {self.offset}")


@dataclass
class ListResearchRunsResult:
    """
    Result of ListResearchRunsQuery.

    Attributes:
        runs: List of research run status DTOs
        total: Total count (for pagination)
    """

    runs: List[ResearchStatusDTO]
    total: int


class ListResearchRunsQueryHandler:
    """
    Handler for listing research runs.

    Queries the research run repository and converts to DTOs.
    """

    def __init__(self, research_repo: ResearchRunRepository):
        """
        Initialize handler with dependencies.

        Args:
            research_repo: Repository for research run persistence
        """
        self.repo = research_repo
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def handle(self, query: ListResearchRunsQuery) -> ListResearchRunsResult:
        """
        Execute the query and return list of research runs.

        Steps:
        1. Fetch research runs from repository
        2. Apply status filter if provided
        3. Sort by start date (descending)
        4. Apply pagination
        5. Convert to DTOs
        6. Return result

        Args:
            query: The query to execute

        Returns:
            ListResearchRunsResult with research runs

        Raises:
            ValueError: If query is invalid
            RuntimeError: If query fails
        """
        self.logger.info(
            "Listing research runs",
            extra={
                "case_id": query.case_id,
                "status": query.status.value if query.status else None,
                "limit": query.limit,
                "offset": query.offset,
            }
        )

        try:
            # 1. Fetch research runs for case
            all_runs = await self.repo.find_by_case_id(query.case_id)

            # 2. Apply status filter
            if query.status:
                filtered_runs = [r for r in all_runs if r.status == query.status]
            else:
                filtered_runs = all_runs

            # 3. Sort by started_at descending (most recent first)
            sorted_runs = sorted(
                filtered_runs,
                key=lambda r: r.started_at if r.started_at else "",
                reverse=True
            )

            # 4. Apply pagination
            total_count = len(sorted_runs)
            paginated_runs = sorted_runs[query.offset:query.offset + query.limit]

            # 5. Convert to DTOs
            run_dtos = [self._to_dto(r) for r in paginated_runs]

            self.logger.info(
                "Research runs listed successfully",
                extra={
                    "total_found": total_count,
                    "returned": len(run_dtos),
                }
            )

            return ListResearchRunsResult(
                runs=run_dtos,
                total=total_count,
            )

        except Exception as e:
            self.logger.error(
                f"Failed to list research runs: {e}",
                extra={"case_id": query.case_id},
                exc_info=True
            )
            raise RuntimeError(f"Failed to list research runs: {e}") from e

    def _to_dto(self, research_run: Any) -> ResearchStatusDTO:
        """
        Convert domain ResearchRun entity to DTO.

        Args:
            research_run: Domain research run entity

        Returns:
            ResearchStatusDTO
        """
        # Calculate progress
        progress_pct = self._calculate_progress(research_run)

        # Get counts
        findings_count = len(research_run.findings)
        citations_count = research_run.metadata.get("citations_count", 0)

        # Collect errors
        errors = []
        if "error" in research_run.metadata:
            errors.append(research_run.metadata["error"])
        if "errors" in research_run.metadata:
            errors.extend(research_run.metadata["errors"])

        return ResearchStatusDTO(
            research_run_id=research_run.id,
            case_id=research_run.case_id,
            status=research_run.status,
            phase=research_run.phase,
            progress_pct=progress_pct,
            query=research_run.query,
            findings_count=findings_count,
            citations_count=citations_count,
            started_at=research_run.started_at.isoformat() if research_run.started_at else "",
            completed_at=research_run.completed_at.isoformat() if research_run.completed_at else None,
            workflow_id=research_run.metadata.get("workflow_id"),
            errors=errors,
            metadata=research_run.metadata.copy() if research_run.metadata else {},
        )

    def _calculate_progress(self, research_run: Any) -> float:
        """Calculate progress percentage based on status and phase."""
        if research_run.status in (ResearchStatus.COMPLETED, ResearchStatus.FAILED):
            return 100.0

        if research_run.status == ResearchStatus.PENDING:
            return 0.0

        # Use phase-based progress for running/paused
        from app.domain.research.entities.research_run import ResearchPhase

        phase_map = {
            ResearchPhase.INITIALIZING: 5.0,
            ResearchPhase.INDEXING: 15.0,
            ResearchPhase.SEARCHING: 35.0,
            ResearchPhase.ANALYZING: 60.0,
            ResearchPhase.HYPOTHESIS_GENERATION: 80.0,
            ResearchPhase.DOSSIER_GENERATION: 95.0,
            ResearchPhase.COMPLETED: 100.0,
        }

        return phase_map.get(research_run.phase, 0.0)
