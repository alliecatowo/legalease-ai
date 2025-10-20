"""
Temporal workflows for deep research.

This module exports all workflows for registration with the Temporal worker.
"""

from app.infrastructure.workflows.temporal.workflows.deep_research_workflow import (
    DeepResearchWorkflow,
)


__all__ = [
    "DeepResearchWorkflow",
]
