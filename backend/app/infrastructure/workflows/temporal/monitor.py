"""
Workflow monitoring utilities.

Helper functions to query workflow status and track progress.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from temporalio.client import WorkflowExecutionStatus

from app.infrastructure.workflows.temporal.client import get_temporal_client
from app.infrastructure.workflows.temporal.workflows import DeepResearchWorkflow


logger = logging.getLogger(__name__)


class WorkflowExecutionState(str, Enum):
    """Workflow execution state."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TERMINATED = "TERMINATED"
    TIMED_OUT = "TIMED_OUT"
    UNKNOWN = "UNKNOWN"


async def get_workflow_status(workflow_id: str) -> Dict[str, Any]:
    """
    Get the current status of a workflow.

    Queries the workflow for its current phase, progress, and findings count.
    This is a non-blocking call that returns immediately with the current state.

    Args:
        workflow_id: The workflow ID

    Returns:
        Dictionary with workflow status including:
        - phase: Current workflow phase
        - progress_pct: Progress percentage (0-100)
        - current_activity: Name of currently executing activity
        - findings_count: Number of findings discovered so far
        - citations_count: Number of citations generated
        - is_paused: Whether workflow is paused
        - is_cancelled: Whether workflow is cancelled
        - error: Error message if failed

    Raises:
        ValueError: If workflow not found

    Example:
        >>> status = await get_workflow_status("research-123e4567-e89b-12d3-a456-426614174000")
        >>> print(f"Phase: {status['phase']}, Progress: {status['progress_pct']}%")
    """
    logger.debug(f"Getting workflow status for {workflow_id}")

    client = await get_temporal_client()

    try:
        handle = client.get_workflow_handle(workflow_id)

        # Query workflow for status
        status = await handle.query(DeepResearchWorkflow.get_status)

        logger.debug(f"Workflow {workflow_id} status: {status}")
        return status

    except Exception as e:
        logger.error(f"Error getting workflow status for {workflow_id}: {e}", exc_info=True)
        raise ValueError(f"Workflow {workflow_id} not found or inaccessible") from e


async def get_workflow_progress(workflow_id: str) -> float:
    """
    Get workflow progress percentage.

    Args:
        workflow_id: The workflow ID

    Returns:
        Progress as a float between 0.0 and 100.0

    Raises:
        ValueError: If workflow not found

    Example:
        >>> progress = await get_workflow_progress("research-123e4567-e89b-12d3-a456-426614174000")
        >>> print(f"Progress: {progress:.1f}%")
    """
    logger.debug(f"Getting workflow progress for {workflow_id}")

    client = await get_temporal_client()

    try:
        handle = client.get_workflow_handle(workflow_id)

        # Query workflow for progress
        progress = await handle.query(DeepResearchWorkflow.get_progress)

        return progress

    except Exception as e:
        logger.error(f"Error getting workflow progress for {workflow_id}: {e}", exc_info=True)
        raise ValueError(f"Workflow {workflow_id} not found or inaccessible") from e


async def get_workflow_execution_state(workflow_id: str) -> WorkflowExecutionState:
    """
    Get the execution state of a workflow.

    This returns the Temporal-level execution state (running, completed, failed, etc.),
    which is different from the workflow's internal phase.

    Args:
        workflow_id: The workflow ID

    Returns:
        WorkflowExecutionState enum value

    Raises:
        ValueError: If workflow not found

    Example:
        >>> state = await get_workflow_execution_state("research-123e4567-e89b-12d3-a456-426614174000")
        >>> if state == WorkflowExecutionState.COMPLETED:
        ...     print("Workflow finished!")
    """
    logger.debug(f"Getting workflow execution state for {workflow_id}")

    client = await get_temporal_client()

    try:
        handle = client.get_workflow_handle(workflow_id)

        # Get workflow description
        description = await handle.describe()

        # Map Temporal status to our enum
        status_map = {
            WorkflowExecutionStatus.RUNNING: WorkflowExecutionState.RUNNING,
            WorkflowExecutionStatus.COMPLETED: WorkflowExecutionState.COMPLETED,
            WorkflowExecutionStatus.FAILED: WorkflowExecutionState.FAILED,
            WorkflowExecutionStatus.CANCELLED: WorkflowExecutionState.CANCELLED,
            WorkflowExecutionStatus.TERMINATED: WorkflowExecutionState.TERMINATED,
            WorkflowExecutionStatus.TIMED_OUT: WorkflowExecutionState.TIMED_OUT,
        }

        state = status_map.get(description.status, WorkflowExecutionState.UNKNOWN)

        logger.debug(f"Workflow {workflow_id} execution state: {state}")
        return state

    except Exception as e:
        logger.error(
            f"Error getting workflow execution state for {workflow_id}: {e}", exc_info=True
        )
        raise ValueError(f"Workflow {workflow_id} not found or inaccessible") from e


async def get_detailed_workflow_info(workflow_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a workflow.

    Combines execution state with workflow status for a comprehensive view.

    Args:
        workflow_id: The workflow ID

    Returns:
        Dictionary with detailed workflow information including:
        - workflow_id: The workflow ID
        - execution_state: Temporal execution state
        - phase: Current workflow phase
        - progress_pct: Progress percentage
        - current_activity: Currently executing activity
        - findings_count: Number of findings
        - citations_count: Number of citations
        - is_paused: Whether paused
        - is_cancelled: Whether cancelled
        - error: Error message if failed
        - start_time: When workflow started
        - close_time: When workflow completed (if finished)

    Raises:
        ValueError: If workflow not found

    Example:
        >>> info = await get_detailed_workflow_info("research-123e4567-e89b-12d3-a456-426614174000")
        >>> print(f"State: {info['execution_state']}, Phase: {info['phase']}")
    """
    logger.debug(f"Getting detailed workflow info for {workflow_id}")

    client = await get_temporal_client()

    try:
        handle = client.get_workflow_handle(workflow_id)

        # Get workflow description
        description = await handle.describe()

        # Get workflow status (if running)
        status = {}
        if description.status == WorkflowExecutionStatus.RUNNING:
            try:
                status = await handle.query(DeepResearchWorkflow.get_status)
            except Exception as e:
                logger.warning(f"Could not query workflow status: {e}")

        # Build detailed info
        info = {
            "workflow_id": workflow_id,
            "execution_state": await get_workflow_execution_state(workflow_id),
            "start_time": description.start_time.isoformat() if description.start_time else None,
            "close_time": description.close_time.isoformat() if description.close_time else None,
            "run_id": description.run_id,
            **status,  # Include workflow status fields
        }

        logger.debug(f"Workflow {workflow_id} detailed info: {info}")
        return info

    except Exception as e:
        logger.error(
            f"Error getting detailed workflow info for {workflow_id}: {e}", exc_info=True
        )
        raise ValueError(f"Workflow {workflow_id} not found or inaccessible") from e


async def list_workflows(
    case_id: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    List workflows, optionally filtered by case ID.

    Args:
        case_id: Optional case ID to filter by
        limit: Maximum number of workflows to return

    Returns:
        List of workflow information dictionaries

    Example:
        >>> workflows = await list_workflows(case_id="123e4567-e89b-12d3-a456-426614174000")
        >>> for wf in workflows:
        ...     print(f"Workflow: {wf['workflow_id']}, State: {wf['execution_state']}")
    """
    logger.debug(f"Listing workflows (case_id={case_id}, limit={limit})")

    client = await get_temporal_client()

    workflows = []

    try:
        # Build query
        query = "WorkflowType='DeepResearchWorkflow'"
        if case_id:
            query += f" AND case_id='{case_id}'"

        # List workflows
        async for workflow in client.list_workflows(query):
            workflows.append({
                "workflow_id": workflow.id,
                "run_id": workflow.run_id,
                "workflow_type": workflow.workflow_type,
                "start_time": workflow.start_time.isoformat() if workflow.start_time else None,
                "close_time": workflow.close_time.isoformat() if workflow.close_time else None,
                "execution_state": workflow.status.name if workflow.status else "UNKNOWN",
            })

            if len(workflows) >= limit:
                break

        logger.info(f"Found {len(workflows)} workflows")
        return workflows

    except Exception as e:
        logger.error(f"Error listing workflows: {e}", exc_info=True)
        raise
