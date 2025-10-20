"""
Temporal activities for deep research workflows.

This module exports all activities for registration with the Temporal worker.
"""

from app.infrastructure.workflows.temporal.activities.evidence_processing import (
    initialize_research_run,
    run_discovery_phase,
    run_planning_phase,
)
from app.infrastructure.workflows.temporal.activities.search import (
    run_document_analysis,
    run_transcript_analysis,
    run_communication_analysis,
)
from app.infrastructure.workflows.temporal.activities.correlation import (
    run_correlation_phase,
)
from app.infrastructure.workflows.temporal.activities.report_generation import (
    run_synthesis_phase,
    generate_report_files,
)


__all__ = [
    # Evidence processing activities
    "initialize_research_run",
    "run_discovery_phase",
    "run_planning_phase",
    # Search activities
    "run_document_analysis",
    "run_transcript_analysis",
    "run_communication_analysis",
    # Correlation activity
    "run_correlation_phase",
    # Report generation activities
    "run_synthesis_phase",
    "generate_report_files",
]
