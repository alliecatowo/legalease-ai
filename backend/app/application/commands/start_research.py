"""
StartResearchCommand - Initiates a new deep research workflow.

This command creates a ResearchRun entity, persists it to PostgreSQL,
and starts a Temporal workflow for asynchronous research execution.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from app.domain.research.entities import ResearchRun, ResearchPhase, ResearchStatus
from app.domain.research.repositories.research_repository import ResearchRunRepository
from app.infrastructure.workflows.temporal.workflows.deep_research_workflow import (
    DeepResearchWorkflow,
    ResearchWorkflowInput,
)
from temporalio.client import Client


logger = logging.getLogger(__name__)


@dataclass
class StartResearchCommand:
    """
    Command to start a new research run.

    Attributes:
        case_id: UUID of the case to research
        query: Optional research query or objective
        defense_theory: Optional defense theory to investigate
        user_id: Optional ID of user initiating research
        config: Optional configuration parameters
    """

    case_id: UUID
    query: Optional[str] = None
    defense_theory: Optional[str] = None
    user_id: Optional[UUID] = None
    config: Optional[dict] = None


@dataclass
class StartResearchResult:
    """
    Result of starting a research run.

    Attributes:
        success: Whether the command succeeded
        research_run_id: ID of the created research run
        workflow_id: Temporal workflow ID
        message: Human-readable status message
        error: Error message if failed
    """

    success: bool
    research_run_id: Optional[UUID] = None
    workflow_id: Optional[str] = None
    message: str = ""
    error: Optional[str] = None


class StartResearchCommandHandler:
    """
    Handler for StartResearchCommand.

    Orchestrates:
    1. Creating and persisting ResearchRun entity
    2. Starting Temporal workflow
    3. Updating ResearchRun with workflow ID
    """

    def __init__(
        self,
        research_repository: ResearchRunRepository,
        temporal_client: Client,
    ):
        """
        Initialize handler with dependencies.

        Args:
            research_repository: Repository for ResearchRun persistence
            temporal_client: Temporal client for workflow execution
        """
        self.research_repo = research_repository
        self.temporal_client = temporal_client

    async def handle(self, command: StartResearchCommand) -> StartResearchResult:
        """
        Handle the StartResearchCommand.

        Args:
            command: The command to execute

        Returns:
            StartResearchResult with success status and IDs

        Process:
            1. Validate case exists (optional - could be done in API layer)
            2. Create ResearchRun entity with PENDING status
            3. Persist to database
            4. Start Temporal workflow
            5. Update ResearchRun with workflow_id and RUNNING status
            6. Return result
        """
        logger.info(f"Starting research for case {command.case_id}")

        try:
            # Generate research run ID
            research_run_id = uuid4()

            # Determine query text
            query_text = command.query or command.defense_theory or "General case research"

            # Create ResearchRun entity
            research_run = ResearchRun(
                id=research_run_id,
                case_id=command.case_id,
                status=ResearchStatus.PENDING,
                phase=ResearchPhase.INITIALIZING,
                query=query_text,
                findings=[],
                config=command.config or {},
                metadata={
                    "user_id": str(command.user_id) if command.user_id else None,
                    "defense_theory": command.defense_theory,
                    "created_at": datetime.utcnow().isoformat(),
                },
            )

            # Persist research run
            logger.info(f"Persisting research run {research_run_id}")
            saved_run = await self.research_repo.save(research_run)

            # Generate workflow ID (use research_run_id for idempotency)
            workflow_id = f"research-{research_run_id}"

            # Prepare workflow input
            workflow_input = ResearchWorkflowInput(
                research_run_id=research_run_id,
                case_id=command.case_id,
                query=query_text,
                config=command.config or {},
            )

            # Start Temporal workflow
            logger.info(f"Starting Temporal workflow {workflow_id}")
            handle = await self.temporal_client.start_workflow(
                DeepResearchWorkflow.run,
                workflow_input,
                id=workflow_id,
                task_queue="research-task-queue",
                # Workflow timeout of 24 hours
                execution_timeout=86400,
            )

            logger.info(f"Workflow {workflow_id} started successfully")

            # Update research run with workflow ID and RUNNING status
            saved_run.status = ResearchStatus.RUNNING
            saved_run.started_at = datetime.utcnow()
            saved_run.metadata["workflow_id"] = workflow_id

            await self.research_repo.save(saved_run)

            logger.info(
                f"Research run {research_run_id} started with workflow {workflow_id}"
            )

            return StartResearchResult(
                success=True,
                research_run_id=research_run_id,
                workflow_id=workflow_id,
                message=f"Research started successfully for case {command.case_id}",
            )

        except Exception as e:
            logger.error(f"Failed to start research: {e}", exc_info=True)

            # Try to mark research run as failed if it was created
            try:
                if "saved_run" in locals():
                    saved_run.mark_failed(str(e))
                    await self.research_repo.save(saved_run)
            except Exception as cleanup_error:
                logger.error(f"Failed to mark research as failed: {cleanup_error}")

            return StartResearchResult(
                success=False,
                research_run_id=research_run_id if "research_run_id" in locals() else None,
                message="Failed to start research",
                error=str(e),
            )
