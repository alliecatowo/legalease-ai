"""
PauseResearchCommand - Pauses a running research workflow.

This command sends a pause signal to the Temporal workflow,
allowing it to gracefully suspend execution.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from app.domain.research.repositories.research_repository import ResearchRunRepository
from app.domain.research.entities import ResearchStatus
from temporalio.client import Client, WorkflowHandle


logger = logging.getLogger(__name__)


@dataclass
class PauseResearchCommand:
    """
    Command to pause a running research workflow.

    Attributes:
        workflow_id: Temporal workflow ID to pause
    """

    workflow_id: str


@dataclass
class PauseResearchResult:
    """
    Result of pausing research.

    Attributes:
        success: Whether the command succeeded
        workflow_id: The workflow ID
        message: Human-readable status message
        error: Error message if failed
    """

    success: bool
    workflow_id: str
    message: str = ""
    error: Optional[str] = None


class PauseResearchCommandHandler:
    """
    Handler for PauseResearchCommand.

    Sends a pause signal to the Temporal workflow and updates
    the ResearchRun status to PAUSED.
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
            temporal_client: Temporal client for workflow control
        """
        self.research_repo = research_repository
        self.temporal_client = temporal_client

    async def handle(self, command: PauseResearchCommand) -> PauseResearchResult:
        """
        Handle the PauseResearchCommand.

        Args:
            command: The command to execute

        Returns:
            PauseResearchResult with success status

        Process:
            1. Get workflow handle from Temporal
            2. Send pause signal
            3. Update ResearchRun status to PAUSED
            4. Return result
        """
        logger.info(f"Pausing research workflow {command.workflow_id}")

        try:
            # Get workflow handle
            handle: WorkflowHandle = self.temporal_client.get_workflow_handle(
                command.workflow_id
            )

            # Verify workflow is running
            description = await handle.describe()
            if description.status.name not in ("RUNNING",):
                return PauseResearchResult(
                    success=False,
                    workflow_id=command.workflow_id,
                    message=f"Workflow is not running (status: {description.status.name})",
                    error="Workflow not in running state",
                )

            # Send pause signal
            # Note: Temporal doesn't have built-in pause/resume, so we send a signal
            # that the workflow should handle to pause gracefully
            await handle.signal("pause")

            logger.info(f"Sent pause signal to workflow {command.workflow_id}")

            # Extract research_run_id from workflow_id
            # Format is "research-{research_run_id}"
            if command.workflow_id.startswith("research-"):
                from uuid import UUID

                research_run_id = UUID(command.workflow_id.replace("research-", ""))

                # Update ResearchRun status
                research_run = await self.research_repo.get_by_id(research_run_id)
                if research_run:
                    research_run.status = ResearchStatus.PAUSED
                    research_run.metadata["paused_at"] = (
                        __import__("datetime").datetime.utcnow().isoformat()
                    )
                    await self.research_repo.save(research_run)
                    logger.info(f"Updated research run {research_run_id} status to PAUSED")

            return PauseResearchResult(
                success=True,
                workflow_id=command.workflow_id,
                message="Research workflow paused successfully",
            )

        except Exception as e:
            logger.error(f"Failed to pause workflow {command.workflow_id}: {e}", exc_info=True)
            return PauseResearchResult(
                success=False,
                workflow_id=command.workflow_id,
                message="Failed to pause research workflow",
                error=str(e),
            )
