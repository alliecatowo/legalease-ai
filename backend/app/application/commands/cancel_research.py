"""
CancelResearchCommand - Cancels a running research workflow.

This command cancels the Temporal workflow and updates the
ResearchRun status to CANCELLED.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from app.domain.research.repositories.research_repository import ResearchRunRepository
from temporalio.client import Client, WorkflowHandle


logger = logging.getLogger(__name__)


@dataclass
class CancelResearchCommand:
    """
    Command to cancel a research workflow.

    Attributes:
        workflow_id: Temporal workflow ID to cancel
        reason: Optional reason for cancellation
    """

    workflow_id: str
    reason: Optional[str] = None


@dataclass
class CancelResearchResult:
    """
    Result of cancelling research.

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


class CancelResearchCommandHandler:
    """
    Handler for CancelResearchCommand.

    Cancels the Temporal workflow and updates the ResearchRun
    status to CANCELLED.
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

    async def handle(self, command: CancelResearchCommand) -> CancelResearchResult:
        """
        Handle the CancelResearchCommand.

        Args:
            command: The command to execute

        Returns:
            CancelResearchResult with success status

        Process:
            1. Get workflow handle from Temporal
            2. Cancel the workflow
            3. Update ResearchRun status to CANCELLED
            4. Return result
        """
        logger.info(f"Cancelling research workflow {command.workflow_id}")

        try:
            # Get workflow handle
            handle: WorkflowHandle = self.temporal_client.get_workflow_handle(
                command.workflow_id
            )

            # Verify workflow exists
            description = await handle.describe()

            # Check if already in terminal state
            if description.status.name in ("COMPLETED", "FAILED", "CANCELED", "TERMINATED"):
                logger.warning(
                    f"Workflow {command.workflow_id} is already in {description.status.name} state"
                )
                # Update ResearchRun anyway if it's not already cancelled
                if command.workflow_id.startswith("research-"):
                    from uuid import UUID

                    research_run_id = UUID(command.workflow_id.replace("research-", ""))
                    research_run = await self.research_repo.get_by_id(research_run_id)
                    if research_run and research_run.status != "CANCELLED":
                        research_run.cancel()
                        research_run.metadata["cancellation_reason"] = (
                            command.reason or "User requested cancellation"
                        )
                        await self.research_repo.save(research_run)

                return CancelResearchResult(
                    success=True,
                    workflow_id=command.workflow_id,
                    message=f"Workflow already in {description.status.name} state",
                )

            # Cancel the workflow
            await handle.cancel()

            logger.info(f"Cancelled workflow {command.workflow_id}")

            # Extract research_run_id from workflow_id
            if command.workflow_id.startswith("research-"):
                from uuid import UUID

                research_run_id = UUID(command.workflow_id.replace("research-", ""))

                # Update ResearchRun status
                research_run = await self.research_repo.get_by_id(research_run_id)
                if research_run:
                    research_run.cancel()
                    research_run.metadata["cancellation_reason"] = (
                        command.reason or "User requested cancellation"
                    )
                    research_run.metadata["cancelled_at"] = (
                        __import__("datetime").datetime.utcnow().isoformat()
                    )
                    await self.research_repo.save(research_run)
                    logger.info(f"Updated research run {research_run_id} status to CANCELLED")

            return CancelResearchResult(
                success=True,
                workflow_id=command.workflow_id,
                message="Research workflow cancelled successfully",
            )

        except Exception as e:
            logger.error(f"Failed to cancel workflow {command.workflow_id}: {e}", exc_info=True)
            return CancelResearchResult(
                success=False,
                workflow_id=command.workflow_id,
                message="Failed to cancel research workflow",
                error=str(e),
            )
