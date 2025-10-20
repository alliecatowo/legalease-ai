"""
ResumeResearchCommand - Resumes a paused research workflow.

This command sends a resume signal to the Temporal workflow,
allowing it to continue execution from where it was paused.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from app.domain.research.repositories.research_repository import ResearchRunRepository
from app.domain.research.entities import ResearchStatus
from temporalio.client import Client, WorkflowHandle


logger = logging.getLogger(__name__)


@dataclass
class ResumeResearchCommand:
    """
    Command to resume a paused research workflow.

    Attributes:
        workflow_id: Temporal workflow ID to resume
    """

    workflow_id: str


@dataclass
class ResumeResearchResult:
    """
    Result of resuming research.

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


class ResumeResearchCommandHandler:
    """
    Handler for ResumeResearchCommand.

    Sends a resume signal to the Temporal workflow and updates
    the ResearchRun status back to RUNNING.
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

    async def handle(self, command: ResumeResearchCommand) -> ResumeResearchResult:
        """
        Handle the ResumeResearchCommand.

        Args:
            command: The command to execute

        Returns:
            ResumeResearchResult with success status

        Process:
            1. Get workflow handle from Temporal
            2. Send resume signal
            3. Update ResearchRun status to RUNNING
            4. Return result
        """
        logger.info(f"Resuming research workflow {command.workflow_id}")

        try:
            # Get workflow handle
            handle: WorkflowHandle = self.temporal_client.get_workflow_handle(
                command.workflow_id
            )

            # Verify workflow exists and is not completed
            description = await handle.describe()
            if description.status.name in ("COMPLETED", "FAILED", "CANCELED", "TERMINATED"):
                return ResumeResearchResult(
                    success=False,
                    workflow_id=command.workflow_id,
                    message=f"Cannot resume workflow in {description.status.name} state",
                    error="Workflow in terminal state",
                )

            # Send resume signal
            await handle.signal("resume")

            logger.info(f"Sent resume signal to workflow {command.workflow_id}")

            # Extract research_run_id from workflow_id
            if command.workflow_id.startswith("research-"):
                from uuid import UUID

                research_run_id = UUID(command.workflow_id.replace("research-", ""))

                # Update ResearchRun status
                research_run = await self.research_repo.get_by_id(research_run_id)
                if research_run:
                    research_run.status = ResearchStatus.RUNNING
                    research_run.metadata["resumed_at"] = (
                        __import__("datetime").datetime.utcnow().isoformat()
                    )
                    await self.research_repo.save(research_run)
                    logger.info(f"Updated research run {research_run_id} status to RUNNING")

            return ResumeResearchResult(
                success=True,
                workflow_id=command.workflow_id,
                message="Research workflow resumed successfully",
            )

        except Exception as e:
            logger.error(f"Failed to resume workflow {command.workflow_id}: {e}", exc_info=True)
            return ResumeResearchResult(
                success=False,
                workflow_id=command.workflow_id,
                message="Failed to resume research workflow",
                error=str(e),
            )
