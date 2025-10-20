"""
Temporal workflow orchestration for deep research.

This package provides Temporal-based workflow orchestration for AI-powered
deep research analysis of legal cases. It includes:

- Workflows: Long-running orchestration of research phases
- Activities: Individual units of work (search, analysis, synthesis)
- Client: Connection management and health checking
- Worker: Background process that executes workflows and activities
- Starter: Utilities to start workflows from FastAPI
- Monitor: Status queries and progress tracking

Quick Start:
    # Start a deep research workflow
    from app.infrastructure.workflows.temporal.starter import start_deep_research
    workflow_id, research_run_id = await start_deep_research(case_id=uuid)

    # Monitor progress
    from app.infrastructure.workflows.temporal.monitor import get_workflow_status
    status = await get_workflow_status(workflow_id)
    print(f"Progress: {status['progress_pct']}%")

    # Run the worker (separate process)
    python -m app.infrastructure.workflows.temporal.worker
"""

from app.infrastructure.workflows.temporal.client import (
    get_temporal_client,
    temporal_health_check,
    close_temporal_client,
)

# Convenience aliases for main.py lifespan
async def init_temporal_client():
    """Initialize Temporal client (lazy initialization on first use)."""
    await get_temporal_client()

async def cleanup_temporal_client():
    """Cleanup Temporal client on shutdown."""
    await close_temporal_client()
from app.infrastructure.workflows.temporal.starter import (
    start_deep_research,
    cancel_workflow,
    pause_workflow,
    resume_workflow,
)
from app.infrastructure.workflows.temporal.monitor import (
    get_workflow_status,
    get_workflow_progress,
    get_detailed_workflow_info,
)
from app.infrastructure.workflows.temporal.models import (
    ResearchWorkflowInput,
    ResearchWorkflowOutput,
    WorkflowPhase,
)


__all__ = [
    # Client
    "get_temporal_client",
    "temporal_health_check",
    "close_temporal_client",
    # Starter
    "start_deep_research",
    "cancel_workflow",
    "pause_workflow",
    "resume_workflow",
    # Monitor
    "get_workflow_status",
    "get_workflow_progress",
    "get_detailed_workflow_info",
    # Models
    "ResearchWorkflowInput",
    "ResearchWorkflowOutput",
    "WorkflowPhase",
]
