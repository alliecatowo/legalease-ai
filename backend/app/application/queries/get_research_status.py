"""
GetResearchStatusQuery for checking research run status.

This module implements CQRS query pattern for retrieving current
status of a research run, including workflow execution state.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List, Any
from uuid import UUID

from app.domain.research.entities.research_run import ResearchStatus, ResearchPhase
from app.domain.research.repositories.research_repository import ResearchRunRepository


logger = logging.getLogger(__name__)


@dataclass
class GetResearchStatusQuery:
    """
    Query for getting current status of a research run.

    Attributes:
        research_run_id: ID of the research run to check

    Example:
        >>> query = GetResearchStatusQuery(research_run_id=run_uuid)
    """

    research_run_id: UUID


@dataclass
class ResearchStatusDTO:
    """
    Data Transfer Object for research run status.

    Attributes:
        research_run_id: Research run ID
        case_id: Associated case ID
        status: Overall execution status
        phase: Current research phase
        progress_pct: Estimated progress percentage (0-100)
        query: Research query/objective
        findings_count: Number of findings discovered
        citations_count: Number of citations collected
        started_at: When research started (ISO format)
        completed_at: When research completed (ISO format, optional)
        workflow_id: Temporal workflow ID (optional)
        errors: List of errors encountered
        metadata: Additional metadata
    """

    research_run_id: UUID
    case_id: UUID
    status: ResearchStatus
    phase: ResearchPhase
    progress_pct: float
    query: Optional[str]
    findings_count: int
    citations_count: int
    started_at: str
    completed_at: Optional[str] = None
    workflow_id: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class GetResearchStatusQueryHandler:
    """
    Handler for retrieving research run status.

    Combines data from the database and Temporal workflow system
    to provide real-time status information.
    """

    def __init__(
        self,
        research_repo: ResearchRunRepository,
        temporal_monitor: Optional[Any] = None,
    ):
        """
        Initialize handler with dependencies.

        Args:
            research_repo: Repository for research run persistence
            temporal_monitor: Optional Temporal workflow monitor
        """
        self.repo = research_repo
        self.temporal = temporal_monitor
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def handle(self, query: GetResearchStatusQuery) -> ResearchStatusDTO:
        """
        Execute the query and return status.

        Steps:
        1. Fetch research run from database
        2. Query Temporal for real-time workflow status (if running)
        3. Calculate progress percentage
        4. Collect error information
        5. Convert to DTO and return

        Args:
            query: The query to execute

        Returns:
            ResearchStatusDTO with current status

        Raises:
            ValueError: If research run not found
            RuntimeError: If query fails
        """
        self.logger.info(
            "Fetching research status",
            extra={"research_run_id": query.research_run_id}
        )

        try:
            # 1. Fetch research run
            research_run = await self.repo.get_by_id(query.research_run_id)
            if not research_run:
                raise ValueError(f"Research run not found: {query.research_run_id}")

            # 2. Query Temporal for real-time status if running
            workflow_status = None
            workflow_id = None
            if self.temporal and research_run.is_running():
                workflow_id = research_run.metadata.get("workflow_id")
                if workflow_id:
                    try:
                        workflow_status = await self.temporal.get_workflow_status(workflow_id)
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to fetch Temporal workflow status: {e}",
                            extra={"workflow_id": workflow_id}
                        )

            # 3. Calculate progress
            progress_pct = self._calculate_progress(research_run, workflow_status)

            # 4. Collect errors
            errors = self._collect_errors(research_run, workflow_status)

            # 5. Get counts
            findings_count = len(research_run.findings)
            citations_count = research_run.metadata.get("citations_count", 0)

            # 6. Build DTO
            dto = ResearchStatusDTO(
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
                workflow_id=workflow_id,
                errors=errors,
                metadata=research_run.metadata.copy() if research_run.metadata else {},
            )

            self.logger.info(
                "Research status retrieved successfully",
                extra={
                    "research_run_id": query.research_run_id,
                    "status": research_run.status.value,
                    "phase": research_run.phase.value,
                }
            )

            return dto

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(
                f"Failed to retrieve research status: {e}",
                extra={"research_run_id": query.research_run_id},
                exc_info=True
            )
            raise RuntimeError(f"Failed to retrieve research status: {e}") from e

    def _calculate_progress(
        self,
        research_run: Any,
        workflow_status: Optional[dict]
    ) -> float:
        """
        Calculate progress percentage.

        Args:
            research_run: Research run entity
            workflow_status: Optional Temporal workflow status

        Returns:
            Progress percentage (0.0-100.0)
        """
        # If completed or failed, return 100%
        if research_run.status in (ResearchStatus.COMPLETED, ResearchStatus.FAILED):
            return 100.0

        # If cancelled, return current progress
        if research_run.status == ResearchStatus.CANCELLED:
            return self._phase_to_progress(research_run.phase)

        # If running, use phase-based progress
        if research_run.status == ResearchStatus.RUNNING:
            base_progress = self._phase_to_progress(research_run.phase)

            # If we have workflow status, refine the progress
            if workflow_status and "progress" in workflow_status:
                return workflow_status["progress"]

            return base_progress

        # Pending
        return 0.0

    def _phase_to_progress(self, phase: ResearchPhase) -> float:
        """Map research phase to progress percentage."""
        phase_map = {
            ResearchPhase.INITIALIZING: 5.0,
            ResearchPhase.INDEXING: 15.0,
            ResearchPhase.SEARCHING: 35.0,
            ResearchPhase.ANALYZING: 60.0,
            ResearchPhase.HYPOTHESIS_GENERATION: 80.0,
            ResearchPhase.DOSSIER_GENERATION: 95.0,
            ResearchPhase.COMPLETED: 100.0,
        }
        return phase_map.get(phase, 0.0)

    def _collect_errors(
        self,
        research_run: Any,
        workflow_status: Optional[dict]
    ) -> List[str]:
        """
        Collect all errors from research run and workflow.

        Args:
            research_run: Research run entity
            workflow_status: Optional Temporal workflow status

        Returns:
            List of error messages
        """
        errors = []

        # Check metadata for errors
        if "error" in research_run.metadata:
            errors.append(research_run.metadata["error"])

        if "errors" in research_run.metadata:
            errors.extend(research_run.metadata["errors"])

        # Check workflow status for errors
        if workflow_status and "errors" in workflow_status:
            errors.extend(workflow_status["errors"])

        return errors
