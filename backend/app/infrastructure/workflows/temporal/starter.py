"""
Workflow starter utilities for FastAPI integration.

Helper functions to start deep research workflows from API endpoints.
"""

import logging
from datetime import timedelta
from typing import Optional
from uuid import UUID, uuid4

from temporalio.client import WorkflowHandle

from app.core.config import settings
from app.infrastructure.workflows.temporal.client import get_temporal_client
from app.infrastructure.workflows.temporal.models import (
    ResearchWorkflowInput,
    ResearchWorkflowOutput,
)
from app.infrastructure.workflows.temporal.workflows import DeepResearchWorkflow


logger = logging.getLogger(__name__)


async def start_deep_research(
    case_id: UUID,
    query: Optional[str] = None,
    defense_theory: Optional[str] = None,
    config: Optional[dict] = None,
) -> tuple[str, str]:
    """
    Start a deep research workflow for a case.

    This function is called from FastAPI endpoints to initiate a new
    research run. It creates a unique workflow ID and starts the workflow
    on the Temporal server.

    Args:
        case_id: UUID of the case to research
        query: Optional research query or objective
        defense_theory: Optional defense theory to investigate
        config: Optional configuration parameters

    Returns:
        Tuple of (workflow_id, research_run_id)

    Raises:
        ConnectionError: If unable to connect to Temporal server
        ValueError: If case_id is invalid

    Example:
        >>> from app.infrastructure.workflows.temporal.starter import start_deep_research
        >>> workflow_id, research_run_id = await start_deep_research(
        ...     case_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        ...     query="Identify timeline of communications",
        ... )
        >>> print(f"Started workflow: {workflow_id}")
    """
    logger.info(f"Starting deep research workflow for case_id={case_id}")

    # Generate research run ID
    research_run_id = str(uuid4())

    # Get Temporal client
    client = await get_temporal_client()

    # Create workflow input
    workflow_input = ResearchWorkflowInput(
        research_run_id=research_run_id,
        case_id=str(case_id),
        query=query,
        defense_theory=defense_theory,
        config=config or {},
    )

    # Generate workflow ID
    workflow_id = f"research-{research_run_id}"

    # Start workflow
    try:
        handle: WorkflowHandle = await client.start_workflow(
            DeepResearchWorkflow.run,
            workflow_input,
            id=workflow_id,
            task_queue=settings.TEMPORAL_TASK_QUEUE,
            execution_timeout=timedelta(seconds=settings.TEMPORAL_WORKFLOW_EXECUTION_TIMEOUT),
            retry_policy=None,  # Don't retry the entire workflow, let activities retry
        )

        logger.info(
            f"Deep research workflow started: workflow_id={workflow_id}, "
            f"research_run_id={research_run_id}, case_id={case_id}"
        )

        return workflow_id, research_run_id

    except Exception as e:
        logger.error(f"Failed to start deep research workflow: {e}", exc_info=True)
        raise


async def get_workflow_result(workflow_id: str) -> ResearchWorkflowOutput:
    """
    Get the result of a completed workflow.

    Waits for the workflow to complete and returns the final output.
    This is a blocking call that will wait until the workflow finishes.

    Args:
        workflow_id: The workflow ID

    Returns:
        ResearchWorkflowOutput with results

    Raises:
        ValueError: If workflow not found
        Exception: If workflow failed

    Example:
        >>> result = await get_workflow_result("research-123e4567-e89b-12d3-a456-426614174000")
        >>> print(f"Status: {result.status}, Findings: {result.findings_count}")
    """
    logger.info(f"Waiting for workflow result: {workflow_id}")

    client = await get_temporal_client()

    try:
        handle = client.get_workflow_handle(workflow_id)
        result: ResearchWorkflowOutput = await handle.result()

        logger.info(f"Workflow {workflow_id} completed with status: {result.status}")
        return result

    except Exception as e:
        logger.error(f"Error getting workflow result for {workflow_id}: {e}", exc_info=True)
        raise


async def cancel_workflow(workflow_id: str, reason: str = "Cancelled by user") -> None:
    """
    Cancel a running workflow.

    Sends a cancel signal to the workflow, which will stop at the next
    checkpoint (between activities).

    Args:
        workflow_id: The workflow ID
        reason: Reason for cancellation

    Raises:
        ValueError: If workflow not found

    Example:
        >>> await cancel_workflow("research-123e4567-e89b-12d3-a456-426614174000")
    """
    logger.info(f"Cancelling workflow: {workflow_id}, reason: {reason}")

    client = await get_temporal_client()

    try:
        handle = client.get_workflow_handle(workflow_id)

        # Send cancel signal
        await handle.signal(DeepResearchWorkflow.cancel)

        logger.info(f"Cancel signal sent to workflow {workflow_id}")

    except Exception as e:
        logger.error(f"Error cancelling workflow {workflow_id}: {e}", exc_info=True)
        raise


async def pause_workflow(workflow_id: str) -> None:
    """
    Pause a running workflow.

    The workflow will pause at the next checkpoint (between activities).

    Args:
        workflow_id: The workflow ID

    Raises:
        ValueError: If workflow not found

    Example:
        >>> await pause_workflow("research-123e4567-e89b-12d3-a456-426614174000")
    """
    logger.info(f"Pausing workflow: {workflow_id}")

    client = await get_temporal_client()

    try:
        handle = client.get_workflow_handle(workflow_id)

        # Send pause signal
        await handle.signal(DeepResearchWorkflow.pause)

        logger.info(f"Pause signal sent to workflow {workflow_id}")

    except Exception as e:
        logger.error(f"Error pausing workflow {workflow_id}: {e}", exc_info=True)
        raise


async def resume_workflow(workflow_id: str) -> None:
    """
    Resume a paused workflow.

    Args:
        workflow_id: The workflow ID

    Raises:
        ValueError: If workflow not found

    Example:
        >>> await resume_workflow("research-123e4567-e89b-12d3-a456-426614174000")
    """
    logger.info(f"Resuming workflow: {workflow_id}")

    client = await get_temporal_client()

    try:
        handle = client.get_workflow_handle(workflow_id)

        # Send resume signal
        await handle.signal(DeepResearchWorkflow.resume)

        logger.info(f"Resume signal sent to workflow {workflow_id}")

    except Exception as e:
        logger.error(f"Error resuming workflow {workflow_id}: {e}", exc_info=True)
        raise
