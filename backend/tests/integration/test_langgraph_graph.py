"""Integration test for the LangGraph research workflow."""

import pytest

from app.infrastructure.ai.langgraph import (
    compile_graph_without_checkpointing,
    create_initial_state,
)


@pytest.mark.asyncio
async def test_research_graph_executes_end_to_end():
    """
    Compile the research graph and execute it with placeholder nodes.

    The placeholder implementations should still take the workflow from
    discovery through synthesis and mark the run as completed.
    """
    graph = compile_graph_without_checkpointing()
    initial_state = create_initial_state(
        research_run_id="run-test",
        case_id="case-test",
        query="Map core evidence",
    )

    result = await graph.ainvoke(initial_state)

    assert result["phase"] == "COMPLETED"
    assert result["status"] == "COMPLETED"
    assert result["progress_pct"] == 100.0
    # Placeholder agents should have produced sample findings
    assert result["document_findings"]
    assert result["executive_summary"]
