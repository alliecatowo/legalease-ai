"""
API v2 routes for research operations.

RESTful endpoints for:
- Starting new research workflows
- Monitoring research progress
- Managing workflow lifecycle (pause/resume/cancel)
- Retrieving findings and dossiers
"""

import logging
from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from temporalio.client import Client, WorkflowHandle

from app.api.v2.schemas.research import (
    StartResearchRequest,
    StartResearchResponse,
    ResearchStatusResponse,
    ResearchStatus,
    ResearchPhase,
    ActionResponse,
    FindingType,
    FindingsResponse,
    FindingResponse,
    EntityReference,
    CitationReference,
    DossierResponse,
    DossierSectionResponse,
    ResearchRunListResponse,
    ResearchRunListItem,
)
from app.infrastructure.workflows.temporal.client import get_temporal_client
from app.infrastructure.workflows.temporal.workflows.deep_research_workflow import DeepResearchWorkflow
from app.infrastructure.workflows.temporal.models import ResearchWorkflowInput


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["research"])


# ==================== Dependency Injection ====================

async def get_workflow_client() -> Client:
    """Get Temporal client for workflow operations."""
    return await get_temporal_client()


# ==================== Helper Functions ====================

async def get_workflow_handle(workflow_id: str, client: Client) -> WorkflowHandle:
    """
    Get a handle to an existing workflow.

    Args:
        workflow_id: The workflow ID
        client: Temporal client

    Returns:
        WorkflowHandle for the workflow

    Raises:
        HTTPException: If workflow not found
    """
    try:
        handle = client.get_workflow_handle(workflow_id)
        # Verify workflow exists
        await handle.describe()
        return handle
    except Exception as e:
        logger.error(f"Failed to get workflow handle for {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research run not found or workflow unavailable: {str(e)}"
        )


async def query_workflow_status(workflow_id: str, client: Client) -> dict:
    """
    Query the current status of a workflow.

    Args:
        workflow_id: The workflow ID
        client: Temporal client

    Returns:
        Dictionary with workflow status
    """
    handle = await get_workflow_handle(workflow_id, client)
    return await handle.query("get_status")


# ==================== Endpoints ====================

@router.post("", response_model=StartResearchResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_research(
    request: StartResearchRequest,
    client: Client = Depends(get_workflow_client),
):
    """
    Start a new deep research workflow.

    The workflow runs asynchronously and can take 30 minutes to 4 hours depending
    on case complexity. Use the returned research_run_id to poll for status or
    connect via WebSocket for real-time updates.

    The workflow will:
    1. Discover and inventory all evidence (Case Cartography)
    2. Plan search strategies based on available evidence
    3. Execute parallel analysis on documents, transcripts, and communications
    4. Correlate findings and build knowledge graph
    5. Synthesize final dossier with citations
    6. Generate report files (DOCX, PDF)

    Args:
        request: Research start request with case_id, query, and optional config
        client: Temporal client (injected)

    Returns:
        StartResearchResponse with research_run_id, workflow_id, and monitoring URLs

    Raises:
        HTTPException 400: If case not found or invalid parameters
        HTTPException 500: If workflow failed to start
    """
    try:
        # Generate IDs
        research_run_id = f"research_{uuid4().hex[:20]}"
        workflow_id = f"deep-research-{research_run_id}"

        # Prepare workflow input
        workflow_input = ResearchWorkflowInput(
            research_run_id=research_run_id,
            case_id=request.case_id,
            query=request.query,
            defense_theory=request.defense_theory,
            config=request.config,
        )

        logger.info(
            f"Starting research workflow: research_run_id={research_run_id}, "
            f"case_id={request.case_id}, query={request.query}"
        )

        # Start the workflow
        handle = await client.start_workflow(
            DeepResearchWorkflow.run,
            workflow_input,
            id=workflow_id,
            task_queue="deep-research-task-queue",
        )

        logger.info(f"Successfully started workflow: {workflow_id}")

        return StartResearchResponse(
            research_run_id=research_run_id,
            workflow_id=workflow_id,
            message="Research workflow started successfully",
            status_url=f"/api/v2/research/{research_run_id}/status",
            websocket_url=f"/api/v2/research/{research_run_id}/stream",
        )

    except Exception as e:
        logger.error(f"Failed to start research workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start research workflow: {str(e)}"
        )


@router.get("/{research_run_id}/status", response_model=ResearchStatusResponse)
async def get_research_status(
    research_run_id: str,
    client: Client = Depends(get_workflow_client),
):
    """
    Get current status of a research run.

    Provides detailed information about:
    - Current workflow phase and progress percentage
    - Number of findings and citations discovered
    - Start/completion times and estimated completion
    - Any errors encountered

    Args:
        research_run_id: The research run ID (e.g., "research_abc123...")
        client: Temporal client (injected)

    Returns:
        ResearchStatusResponse with detailed status information

    Raises:
        HTTPException 404: If research run not found
    """
    try:
        workflow_id = f"deep-research-{research_run_id}"

        # Get workflow handle and description
        handle = await get_workflow_handle(workflow_id, client)
        description = await handle.describe()

        # Query workflow status
        workflow_status = await handle.query("get_status")

        # Extract workflow execution info
        workflow_execution = description.execution
        started_at = description.start_time
        completed_at = description.close_time if description.close_time else None

        # Map workflow status to API status
        if description.status.name == "RUNNING":
            api_status = ResearchStatus.RUNNING
        elif description.status.name == "COMPLETED":
            api_status = ResearchStatus.COMPLETED
        elif description.status.name in ["FAILED", "TERMINATED"]:
            api_status = ResearchStatus.FAILED
        elif description.status.name == "CANCELLED":
            api_status = ResearchStatus.CANCELLED
        else:
            api_status = ResearchStatus.PENDING

        # Extract errors if any
        errors = []
        if workflow_status.get("error"):
            errors.append(workflow_status["error"])

        return ResearchStatusResponse(
            research_run_id=research_run_id,
            case_id=workflow_status.get("case_id", "unknown"),
            workflow_id=workflow_id,
            status=api_status,
            phase=ResearchPhase(workflow_status.get("phase", "INITIALIZING")),
            progress_pct=workflow_status.get("progress_pct", 0.0),
            query=workflow_status.get("query"),
            defense_theory=workflow_status.get("defense_theory"),
            findings_count=workflow_status.get("findings_count", 0),
            citations_count=workflow_status.get("citations_count", 0),
            current_activity=workflow_status.get("current_activity"),
            is_paused=workflow_status.get("is_paused", False),
            started_at=started_at,
            completed_at=completed_at,
            estimated_completion=None,  # TODO: Calculate based on progress
            errors=errors,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get research status for {research_run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve research status: {str(e)}"
        )


@router.post("/{research_run_id}/pause", response_model=ActionResponse, status_code=status.HTTP_202_ACCEPTED)
async def pause_research(
    research_run_id: str,
    client: Client = Depends(get_workflow_client),
):
    """
    Pause a running research workflow.

    The workflow will pause at the next checkpoint (between activities).
    Progress is preserved and the workflow can be resumed later.

    Args:
        research_run_id: The research run ID
        client: Temporal client (injected)

    Returns:
        ActionResponse confirming the pause action

    Raises:
        HTTPException 404: If research run not found
        HTTPException 400: If workflow cannot be paused (e.g., already completed)
    """
    try:
        workflow_id = f"deep-research-{research_run_id}"
        handle = await get_workflow_handle(workflow_id, client)

        # Send pause signal to workflow
        await handle.signal("pause")

        logger.info(f"Sent pause signal to workflow {workflow_id}")

        return ActionResponse(
            research_run_id=research_run_id,
            action="pause",
            status="PAUSED",
            message="Research workflow will pause at the next checkpoint",
            timestamp=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause research {research_run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause research workflow: {str(e)}"
        )


@router.post("/{research_run_id}/resume", response_model=ActionResponse, status_code=status.HTTP_202_ACCEPTED)
async def resume_research(
    research_run_id: str,
    client: Client = Depends(get_workflow_client),
):
    """
    Resume a paused research workflow.

    The workflow will continue from where it was paused.

    Args:
        research_run_id: The research run ID
        client: Temporal client (injected)

    Returns:
        ActionResponse confirming the resume action

    Raises:
        HTTPException 404: If research run not found
        HTTPException 400: If workflow is not paused
    """
    try:
        workflow_id = f"deep-research-{research_run_id}"
        handle = await get_workflow_handle(workflow_id, client)

        # Send resume signal to workflow
        await handle.signal("resume")

        logger.info(f"Sent resume signal to workflow {workflow_id}")

        return ActionResponse(
            research_run_id=research_run_id,
            action="resume",
            status="RUNNING",
            message="Research workflow resumed successfully",
            timestamp=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume research {research_run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume research workflow: {str(e)}"
        )


@router.post("/{research_run_id}/cancel", response_model=ActionResponse, status_code=status.HTTP_202_ACCEPTED)
async def cancel_research(
    research_run_id: str,
    client: Client = Depends(get_workflow_client),
):
    """
    Cancel a running or paused research workflow.

    The workflow will be cancelled at the next checkpoint.
    Partial results may be available but no dossier will be generated.

    Warning: This action cannot be undone.

    Args:
        research_run_id: The research run ID
        client: Temporal client (injected)

    Returns:
        ActionResponse confirming the cancellation

    Raises:
        HTTPException 404: If research run not found
        HTTPException 400: If workflow is already completed or cancelled
    """
    try:
        workflow_id = f"deep-research-{research_run_id}"
        handle = await get_workflow_handle(workflow_id, client)

        # Send cancel signal to workflow
        await handle.signal("cancel")

        logger.info(f"Sent cancel signal to workflow {workflow_id}")

        return ActionResponse(
            research_run_id=research_run_id,
            action="cancel",
            status="CANCELLED",
            message="Research workflow will be cancelled at the next checkpoint",
            timestamp=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel research {research_run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel research workflow: {str(e)}"
        )


@router.get("/{research_run_id}/findings", response_model=FindingsResponse)
async def get_findings(
    research_run_id: str,
    finding_types: Optional[List[FindingType]] = Query(None, description="Filter by finding types"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence score"),
    min_relevance: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum relevance score"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    limit: int = Query(100, ge=1, le=500, description="Maximum findings to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    client: Client = Depends(get_workflow_client),
):
    """
    Get findings from a research run with optional filters.

    Findings are atomic units of discovery backed by citations to evidence.
    Use filters to narrow down results by type, confidence, relevance, or tags.

    Args:
        research_run_id: The research run ID
        finding_types: Optional list of finding types to include
        min_confidence: Optional minimum confidence threshold
        min_relevance: Optional minimum relevance threshold
        tags: Optional list of tags to filter by
        limit: Maximum findings per page (1-500)
        offset: Offset for pagination
        client: Temporal client (injected)

    Returns:
        FindingsResponse with filtered findings and pagination info

    Raises:
        HTTPException 404: If research run not found
        HTTPException 400: If research is not yet completed
    """
    try:
        workflow_id = f"deep-research-{research_run_id}"
        handle = await get_workflow_handle(workflow_id, client)

        # TODO: Implement actual findings retrieval from database/storage
        # For now, return placeholder response
        logger.warning(
            f"Findings retrieval not yet implemented for {research_run_id}. "
            "Returning placeholder response."
        )

        return FindingsResponse(
            findings=[],
            total=0,
            limit=limit,
            offset=offset,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get findings for {research_run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve findings: {str(e)}"
        )


@router.get("/{research_run_id}/dossier", response_model=DossierResponse)
async def get_dossier(
    research_run_id: str,
    client: Client = Depends(get_workflow_client),
):
    """
    Get the generated research dossier.

    The dossier contains:
    - Executive summary of findings
    - Organized sections with supporting evidence
    - Timeline of events
    - Detected contradictions
    - Complete citations

    Only available after research is completed.

    Args:
        research_run_id: The research run ID
        client: Temporal client (injected)

    Returns:
        DossierResponse with complete dossier content

    Raises:
        HTTPException 404: If research run not found
        HTTPException 400: If research is not yet completed
    """
    try:
        workflow_id = f"deep-research-{research_run_id}"
        handle = await get_workflow_handle(workflow_id, client)

        # Check if workflow is completed
        description = await handle.describe()
        if description.status.name != "COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Research is not yet completed. Dossier is only available after completion."
            )

        # TODO: Implement actual dossier retrieval from storage
        logger.warning(
            f"Dossier retrieval not yet implemented for {research_run_id}. "
            "Returning placeholder response."
        )

        return DossierResponse(
            research_run_id=research_run_id,
            case_id="unknown",
            title="Research Dossier (Not Yet Implemented)",
            executive_summary="Dossier retrieval is not yet implemented.",
            sections=[],
            findings_count=0,
            citations_count=0,
            contradictions_count=0,
            timeline_events_count=0,
            generated_at=datetime.utcnow(),
            file_path=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dossier for {research_run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve dossier: {str(e)}"
        )


@router.get("/{research_run_id}/dossier/download")
async def download_dossier(
    research_run_id: str,
    format: str = Query("pdf", regex="^(pdf|docx)$", description="File format (pdf or docx)"),
    client: Client = Depends(get_workflow_client),
):
    """
    Download the generated dossier file.

    Available formats:
    - PDF: For viewing and sharing
    - DOCX: For editing and further customization

    Only available after research is completed.

    Args:
        research_run_id: The research run ID
        format: File format (pdf or docx)
        client: Temporal client (injected)

    Returns:
        FileResponse with the dossier file

    Raises:
        HTTPException 404: If research run not found or file not available
        HTTPException 400: If research is not yet completed
    """
    try:
        workflow_id = f"deep-research-{research_run_id}"
        handle = await get_workflow_handle(workflow_id, client)

        # Check if workflow is completed
        description = await handle.describe()
        if description.status.name != "COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Research is not yet completed. Dossier file is only available after completion."
            )

        # TODO: Implement actual file retrieval from storage (MinIO)
        # Get workflow result to find dossier_path
        # result = await handle.result()
        # file_path = result.dossier_path

        logger.warning(
            f"Dossier download not yet implemented for {research_run_id}. "
            "Returning 404."
        )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier file not found. File generation may not be implemented yet."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download dossier for {research_run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download dossier: {str(e)}"
        )


# ==================== Case-level endpoints ====================

@router.get("/cases/{case_gid}/research", response_model=ResearchRunListResponse)
async def list_research_runs_for_case(
    case_gid: str,
    status_filter: Optional[ResearchStatus] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum items per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    client: Client = Depends(get_workflow_client),
):
    """
    List all research runs for a specific case.

    Returns a paginated list of research runs with their current status,
    progress, and findings count. Use status filter to show only runs
    in a specific state (e.g., COMPLETED, RUNNING).

    Args:
        case_gid: The case GID
        status_filter: Optional status filter
        limit: Maximum items per page (1-100)
        offset: Offset for pagination
        client: Temporal client (injected)

    Returns:
        ResearchRunListResponse with list of research runs

    Raises:
        HTTPException 404: If case not found
    """
    try:
        # TODO: Implement actual research run listing from database
        # Query database for research runs by case_id
        # Apply status filter if provided
        # Apply pagination

        logger.warning(
            f"Research run listing not yet implemented for case {case_gid}. "
            "Returning empty response."
        )

        return ResearchRunListResponse(
            research_runs=[],
            total=0,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error(f"Failed to list research runs for case {case_gid}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list research runs: {str(e)}"
        )
