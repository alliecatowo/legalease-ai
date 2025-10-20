"""Unit tests for research state utilities."""

from app.infrastructure.ai.langgraph.state import (
    create_initial_state,
    update_phase,
    update_progress,
    update_current_agent,
    add_error,
    mark_completed,
    mark_failed,
    validate_state,
)


def test_create_initial_state_defaults():
    """Initial state should populate mandatory fields with sensible defaults."""
    state = create_initial_state(
        research_run_id="run-123",
        case_id="case-456",
        query="Find key evidence",
        defense_theory="Self defence",
    )

    assert state["research_run_id"] == "run-123"
    assert state["case_id"] == "case-456"
    assert state["query"] == "Find key evidence"
    assert state["defense_theory"] == "Self defence"
    assert state["phase"] == "DISCOVERY"
    assert state["status"] == "RUNNING"
    assert state["progress_pct"] == 0.0
    assert state["document_inventory"] == []
    assert state["timeline"] is None


def test_state_update_helpers():
    """State helper functions should return partial updates with timestamps."""
    state = create_initial_state("run", "case")

    phase_update = update_phase(state, "ANALYSIS")
    assert phase_update["phase"] == "ANALYSIS"
    assert "updated_at" in phase_update

    progress_update = update_progress(state, 42.5)
    assert progress_update["progress_pct"] == 42.5

    agent_update = update_current_agent(state, "DocumentAnalystAgent")
    assert agent_update["current_agent"] == "DocumentAnalystAgent"

    error_update = add_error(state, "Something went wrong")
    assert error_update["errors"] == ["Something went wrong"]


def test_mark_completed_and_failed():
    """Terminal state transitions should produce consistent outputs."""
    state = create_initial_state("run", "case")

    completed = mark_completed(state)
    assert completed["status"] == "COMPLETED"
    assert completed["progress_pct"] == 100.0
    assert completed["current_agent"] is None

    failed = mark_failed(state, "Temporal connection lost")
    assert failed["status"] == "FAILED"
    assert failed["errors"] == ["Temporal connection lost"]
    assert failed["current_agent"] is None


def test_validate_state_detects_errors():
    """validate_state should return descriptive errors for inconsistent state."""
    state = create_initial_state("run", "case")
    state["status"] = "COMPLETED"
    state["phase"] = "DISCOVERY"

    errors = validate_state(state)
    assert errors, "Expected validation errors when status/phase mismatch"
    assert any("phase" in err.lower() for err in errors)
