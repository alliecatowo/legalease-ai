"""
LangGraph state definitions for research workflows.

This module contains:
- Research state TypedDict definitions with LangGraph reducers
- State update utilities for managing workflow progress
- State validation helpers
- Initial state factory functions
"""

import operator
from datetime import datetime
from typing import Annotated, Dict, List, Optional, TypedDict, Any
from uuid import UUID, uuid4


class ResearchState(TypedDict):
    """
    Comprehensive state definition for the deep research workflow.

    This state is shared across all agents in the research graph and uses
    LangGraph's reducer pattern for append-only collections.

    Reducers:
    - operator.add for lists: Appends new items to existing list
    - operator.add for dicts: Merges dictionaries (new keys added, existing updated)

    Workflow Phases:
    1. DISCOVERY - Inventory all evidence in the case
    2. PLANNING - Create research plan with workstreams and queries
    3. ANALYSIS - Parallel analysis of documents, transcripts, communications
    4. CORRELATION - Build knowledge graph and find patterns
    5. SYNTHESIS - Generate final dossier
    """

    # ==================== Request Context ====================
    research_run_id: str  # UUID of the research run
    case_id: str  # UUID of the case being researched
    query: Optional[str]  # Optional user query to guide research
    defense_theory: Optional[str]  # Optional defense theory to investigate

    # ==================== Evidence Inventory (Discovery Phase) ====================
    # Case map: high-level structure of the case
    case_map: Annotated[Dict[str, Any], operator.add]

    # Inventories: metadata about available evidence
    document_inventory: Annotated[List[Dict[str, Any]], operator.add]
    transcript_inventory: Annotated[List[Dict[str, Any]], operator.add]
    communication_inventory: Annotated[List[Dict[str, Any]], operator.add]

    # ==================== Research Planning ====================
    # Research plan with workstreams, queries, and search heuristics
    research_plan: Optional[Dict[str, Any]]

    # ==================== Analysis Phase Outputs ====================
    # Findings extracted by each analyst agent
    document_findings: Annotated[List[Dict[str, Any]], operator.add]
    transcript_findings: Annotated[List[Dict[str, Any]], operator.add]
    communication_findings: Annotated[List[Dict[str, Any]], operator.add]

    # ==================== Knowledge Graph Construction ====================
    # Entities: People, organizations, locations, etc.
    entities: Annotated[List[Dict[str, Any]], operator.add]

    # Events: Timestamped occurrences
    events: Annotated[List[Dict[str, Any]], operator.add]

    # Relationships: Connections between entities
    relationships: Annotated[List[Dict[str, Any]], operator.add]

    # Timeline: Chronological ordering of events
    timeline: Optional[Dict[str, Any]]

    # ==================== Correlation Phase Outputs ====================
    # Event chains: Sequences of related events forming narratives
    event_chains: Annotated[List[Dict[str, Any]], operator.add]

    # Contradictions: Inconsistencies found in evidence
    contradictions: Annotated[List[Dict[str, Any]], operator.add]

    # Gaps: Missing information or evidence gaps
    gaps: Annotated[List[str], operator.add]

    # ==================== Synthesis Phase Outputs ====================
    # Dossier sections: Structured report sections
    dossier_sections: Annotated[List[Dict[str, Any]], operator.add]

    # Executive summary: High-level overview
    executive_summary: Optional[str]

    # Citations appendix: All source citations
    citations_appendix: Annotated[List[Dict[str, Any]], operator.add]

    # ==================== Workflow Metadata ====================
    # Current phase of the research workflow
    phase: str  # DISCOVERY, PLANNING, ANALYSIS, CORRELATION, SYNTHESIS, COMPLETED

    # Current status
    status: str  # RUNNING, PAUSED, COMPLETED, FAILED, AWAITING_HUMAN

    # Currently active agent
    current_agent: Optional[str]

    # Progress percentage (0.0 to 100.0)
    progress_pct: float

    # Errors encountered during execution
    errors: Annotated[List[str], operator.add]

    # Timestamps
    started_at: Optional[str]  # ISO format datetime
    updated_at: Optional[str]  # ISO format datetime


# ==================== State Factory Functions ====================

def create_initial_state(
    research_run_id: str,
    case_id: str,
    query: Optional[str] = None,
    defense_theory: Optional[str] = None,
) -> ResearchState:
    """
    Create an initial research state for a new research run.

    Args:
        research_run_id: UUID of the research run
        case_id: UUID of the case being researched
        query: Optional user query to guide research
        defense_theory: Optional defense theory to investigate

    Returns:
        Initial ResearchState with empty collections
    """
    now = datetime.utcnow().isoformat()

    return ResearchState(
        # Request context
        research_run_id=research_run_id,
        case_id=case_id,
        query=query,
        defense_theory=defense_theory,

        # Evidence inventory
        case_map={},
        document_inventory=[],
        transcript_inventory=[],
        communication_inventory=[],

        # Planning
        research_plan=None,

        # Analysis outputs
        document_findings=[],
        transcript_findings=[],
        communication_findings=[],

        # Knowledge graph
        entities=[],
        events=[],
        relationships=[],
        timeline=None,

        # Correlation outputs
        event_chains=[],
        contradictions=[],
        gaps=[],

        # Synthesis outputs
        dossier_sections=[],
        executive_summary=None,
        citations_appendix=[],

        # Workflow metadata
        phase="DISCOVERY",
        status="RUNNING",
        current_agent=None,
        progress_pct=0.0,
        errors=[],
        started_at=now,
        updated_at=now,
    )


# ==================== State Update Helpers ====================

def update_phase(state: ResearchState, phase: str) -> Dict[str, Any]:
    """
    Update the current phase of the research workflow.

    Args:
        state: Current research state
        phase: New phase (DISCOVERY, PLANNING, ANALYSIS, CORRELATION, SYNTHESIS, COMPLETED)

    Returns:
        Partial state update dictionary
    """
    return {
        "phase": phase,
        "updated_at": datetime.utcnow().isoformat(),
    }


def update_progress(state: ResearchState, pct: float) -> Dict[str, Any]:
    """
    Update the progress percentage.

    Args:
        state: Current research state
        pct: Progress percentage (0.0 to 100.0)

    Returns:
        Partial state update dictionary
    """
    return {
        "progress_pct": min(100.0, max(0.0, pct)),
        "updated_at": datetime.utcnow().isoformat(),
    }


def update_status(state: ResearchState, status: str) -> Dict[str, Any]:
    """
    Update the workflow status.

    Args:
        state: Current research state
        status: New status (RUNNING, PAUSED, COMPLETED, FAILED, AWAITING_HUMAN)

    Returns:
        Partial state update dictionary
    """
    return {
        "status": status,
        "updated_at": datetime.utcnow().isoformat(),
    }


def update_current_agent(state: ResearchState, agent_name: Optional[str]) -> Dict[str, Any]:
    """
    Update the currently active agent.

    Args:
        state: Current research state
        agent_name: Name of the active agent or None

    Returns:
        Partial state update dictionary
    """
    return {
        "current_agent": agent_name,
        "updated_at": datetime.utcnow().isoformat(),
    }


def add_error(state: ResearchState, error: str) -> Dict[str, Any]:
    """
    Add an error to the state.

    Args:
        state: Current research state
        error: Error message

    Returns:
        Partial state update dictionary
    """
    return {
        "errors": [error],
        "updated_at": datetime.utcnow().isoformat(),
    }


def mark_completed(state: ResearchState) -> Dict[str, Any]:
    """
    Mark the research workflow as completed.

    Args:
        state: Current research state

    Returns:
        Partial state update dictionary
    """
    return {
        "phase": "COMPLETED",
        "status": "COMPLETED",
        "progress_pct": 100.0,
        "current_agent": None,
        "updated_at": datetime.utcnow().isoformat(),
    }


def mark_failed(state: ResearchState, error: str) -> Dict[str, Any]:
    """
    Mark the research workflow as failed.

    Args:
        state: Current research state
        error: Error message describing the failure

    Returns:
        Partial state update dictionary
    """
    return {
        "status": "FAILED",
        "errors": [error],
        "current_agent": None,
        "updated_at": datetime.utcnow().isoformat(),
    }


# ==================== State Validation ====================

def validate_state(state: ResearchState) -> List[str]:
    """
    Validate research state for consistency.

    Args:
        state: Research state to validate

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Validate required fields
    if not state.get("research_run_id"):
        errors.append("research_run_id is required")

    if not state.get("case_id"):
        errors.append("case_id is required")

    # Validate phase
    valid_phases = {"DISCOVERY", "PLANNING", "ANALYSIS", "CORRELATION", "SYNTHESIS", "COMPLETED"}
    if state.get("phase") not in valid_phases:
        errors.append(f"Invalid phase: {state.get('phase')}")

    # Validate status
    valid_statuses = {"RUNNING", "PAUSED", "COMPLETED", "FAILED", "AWAITING_HUMAN"}
    if state.get("status") not in valid_statuses:
        errors.append(f"Invalid status: {state.get('status')}")

    # Validate progress
    progress = state.get("progress_pct", 0.0)
    if not 0.0 <= progress <= 100.0:
        errors.append(f"Invalid progress_pct: {progress}")

    return errors


def get_state_summary(state: ResearchState) -> Dict[str, Any]:
    """
    Get a summary of the current state for logging/debugging.

    Args:
        state: Research state

    Returns:
        Dictionary with summary information
    """
    return {
        "research_run_id": state.get("research_run_id"),
        "case_id": state.get("case_id"),
        "phase": state.get("phase"),
        "status": state.get("status"),
        "current_agent": state.get("current_agent"),
        "progress_pct": state.get("progress_pct"),
        "evidence_counts": {
            "documents": len(state.get("document_inventory", [])),
            "transcripts": len(state.get("transcript_inventory", [])),
            "communications": len(state.get("communication_inventory", [])),
        },
        "findings_counts": {
            "document_findings": len(state.get("document_findings", [])),
            "transcript_findings": len(state.get("transcript_findings", [])),
            "communication_findings": len(state.get("communication_findings", [])),
        },
        "graph_counts": {
            "entities": len(state.get("entities", [])),
            "events": len(state.get("events", [])),
            "relationships": len(state.get("relationships", [])),
        },
        "errors": len(state.get("errors", [])),
        "updated_at": state.get("updated_at"),
    }
