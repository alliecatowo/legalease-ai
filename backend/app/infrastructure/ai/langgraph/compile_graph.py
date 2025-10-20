"""
Graph Compilation Utilities with Checkpointing

This module provides utilities for compiling the research graph with
checkpointing support for long-running workflows and resumability.
"""

import logging
from typing import Optional
from typing import Any

from app.core.config import settings
from .graphs.research_graph import create_research_graph
from .state import ResearchState
try:
    from langgraph.checkpoint.base import BaseCheckpointSaver
except ImportError:  # pragma: no cover - fallback for minimal environments
    class BaseCheckpointSaver:  # type: ignore
        """Fallback base class providing async checkpoint interface."""

        async def aget(self, *args, **kwargs):
            return None

        async def aput(self, *args, **kwargs):
            return None

        async def alist(self, *args, **kwargs):
            return []

        async def adelete(self, *args, **kwargs):
            return None


try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError:  # pragma: no cover - fallback in environments without langgraph extras
    class SqliteSaver(BaseCheckpointSaver):  # type: ignore
        """In-memory checkpoint saver used when SQLite saver is unavailable."""

        def __init__(self):
            self._store: dict[str, dict] = {}

        @classmethod
        def from_conn_string(cls, conn_str: str) -> "SqliteSaver":
            return cls()

        async def aget(self, config):
            thread_id = config.get("configurable", {}).get("thread_id")
            return self._store.get(thread_id)

        async def aput(self, config, checkpoint):
            thread_id = config.get("configurable", {}).get("thread_id")
            if thread_id:
                self._store[thread_id] = checkpoint

        async def alist(self, config, limit=10):
            thread_id = config.get("configurable", {}).get("thread_id")
            if thread_id and thread_id in self._store:
                return [self._store[thread_id]]
            return []

        async def adelete(self, config):
            thread_id = config.get("configurable", {}).get("thread_id")
            if thread_id:
                self._store.pop(thread_id, None)

logger = logging.getLogger(__name__)


# ==================== Checkpointer Configuration ====================

def get_development_checkpointer() -> BaseCheckpointSaver:
    """
    Get in-memory SQLite checkpointer for development.

    This is suitable for testing and development but state will be lost
    when the process restarts.

    Returns:
        SqliteSaver with in-memory database
    """
    logger.info("Creating development checkpointer (in-memory SQLite)")
    return SqliteSaver.from_conn_string(":memory:")


def get_production_checkpointer() -> BaseCheckpointSaver:
    """
    Get PostgreSQL checkpointer for production.

    Uses the application's DATABASE_URL for persistent checkpointing.
    State survives process restarts and can be queried/managed via SQL.

    Returns:
        PostgreSQL-backed checkpointer
    """
    try:
        from langgraph.checkpoint.postgres import PostgresSaver

        logger.info("Creating production checkpointer (PostgreSQL)")
        return PostgresSaver.from_conn_string(settings.DATABASE_URL)
    except ImportError:
        logger.warning(
            "PostgreSQL checkpointer not available, falling back to SQLite. "
            "Install langgraph-checkpoint-postgres for production use."
        )
        # Fallback to persistent SQLite file
        return SqliteSaver.from_conn_string("./langgraph_checkpoints.db")


def get_checkpointer(use_production: bool = False) -> BaseCheckpointSaver:
    """
    Get appropriate checkpointer based on environment.

    Args:
        use_production: If True, use production PostgreSQL checkpointer

    Returns:
        Configured checkpointer
    """
    if use_production or not settings.DEBUG:
        return get_production_checkpointer()
    else:
        return get_development_checkpointer()


# ==================== Graph Compilation ====================

def compile_research_graph(
    checkpointer: Optional[BaseCheckpointSaver] = None,
    use_production_checkpointer: bool = False,
) -> Any:
    """
    Compile the research graph with checkpointing support.

    This creates a compiled graph that can be executed with state persistence,
    enabling pause/resume functionality and recovery from failures.

    Args:
        checkpointer: Optional checkpointer instance. If None, one will be created
        use_production_checkpointer: If True and checkpointer is None, use production checkpointer

    Returns:
        Compiled research graph ready for execution

    Example:
        >>> from app.infrastructure.ai.langgraph import compile_research_graph
        >>> from app.infrastructure.ai.langgraph.state import create_initial_state
        >>>
        >>> # Compile graph
        >>> graph = compile_research_graph(use_production_checkpointer=True)
        >>>
        >>> # Create initial state
        >>> state = create_initial_state(
        ...     research_run_id="run-123",
        ...     case_id="case-456",
        ...     query="Analyze contract breach evidence"
        ... )
        >>>
        >>> # Execute with thread ID for checkpointing
        >>> config = {"configurable": {"thread_id": "research-run-123"}}
        >>> result = await graph.ainvoke(state, config)
        >>>
        >>> # Later, resume from checkpoint
        >>> resumed = await graph.ainvoke(None, config)
    """
    # Create or use provided checkpointer
    if checkpointer is None:
        checkpointer = get_checkpointer(use_production=use_production_checkpointer)

    # Create the graph
    logger.info("Creating research graph...")
    graph = create_research_graph()

    # Compile with checkpointing
    logger.info("Compiling graph with checkpointing...")
    compiled = graph.compile(checkpointer=checkpointer)

    logger.info("Research graph compiled successfully")
    return compiled


def compile_graph_without_checkpointing() -> Any:
    """
    Compile the research graph without checkpointing.

    Use this for stateless execution or when checkpointing is not needed.
    Faster but does not support pause/resume.

    Returns:
        Compiled research graph without checkpointing

    Example:
        >>> graph = compile_graph_without_checkpointing()
        >>> state = create_initial_state(...)
        >>> result = await graph.ainvoke(state)
    """
    logger.info("Creating research graph without checkpointing...")
    graph = create_research_graph()
    compiled = graph.compile()
    logger.info("Research graph compiled (no checkpointing)")
    return compiled


# ==================== Checkpoint Management ====================

async def get_checkpoint_state(
    checkpointer: BaseCheckpointSaver,
    thread_id: str,
) -> Optional[ResearchState]:
    """
    Retrieve the latest checkpoint state for a thread.

    Args:
        checkpointer: Checkpointer instance
        thread_id: Thread ID to retrieve

    Returns:
        Latest state or None if no checkpoint exists
    """
    try:
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint = await checkpointer.aget(config)

        if checkpoint:
            logger.info(f"Retrieved checkpoint for thread {thread_id}")
            return checkpoint.get("state")
        else:
            logger.info(f"No checkpoint found for thread {thread_id}")
            return None
    except Exception as e:
        logger.error(f"Error retrieving checkpoint: {e}")
        return None


async def list_checkpoints(
    checkpointer: BaseCheckpointSaver,
    thread_id: str,
    limit: int = 10,
) -> list:
    """
    List all checkpoints for a thread.

    Args:
        checkpointer: Checkpointer instance
        thread_id: Thread ID
        limit: Maximum number of checkpoints to return

    Returns:
        List of checkpoint metadata
    """
    try:
        config = {"configurable": {"thread_id": thread_id}}
        checkpoints = []

        async for checkpoint in checkpointer.alist(config, limit=limit):
            checkpoints.append({
                "checkpoint_id": checkpoint.id,
                "timestamp": checkpoint.ts,
                "metadata": checkpoint.metadata,
            })

        logger.info(f"Found {len(checkpoints)} checkpoints for thread {thread_id}")
        return checkpoints
    except Exception as e:
        logger.error(f"Error listing checkpoints: {e}")
        return []


async def delete_checkpoint(
    checkpointer: BaseCheckpointSaver,
    thread_id: str,
) -> bool:
    """
    Delete all checkpoints for a thread.

    Args:
        checkpointer: Checkpointer instance
        thread_id: Thread ID

    Returns:
        True if successful, False otherwise
    """
    try:
        config = {"configurable": {"thread_id": thread_id}}
        await checkpointer.adelete(config)
        logger.info(f"Deleted checkpoints for thread {thread_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting checkpoints: {e}")
        return False


# ==================== Execution Helpers ====================

async def execute_research_workflow(
    case_id: str,
    research_run_id: str,
    query: Optional[str] = None,
    defense_theory: Optional[str] = None,
    use_checkpointing: bool = True,
) -> ResearchState:
    """
    Execute a complete research workflow.

    This is a high-level convenience function that:
    1. Creates initial state
    2. Compiles the graph with checkpointing
    3. Executes the workflow
    4. Returns the final state

    Args:
        case_id: Case UUID
        research_run_id: Research run UUID
        query: Optional research query
        defense_theory: Optional defense theory
        use_checkpointing: Whether to use checkpointing

    Returns:
        Final research state after completion

    Example:
        >>> result = await execute_research_workflow(
        ...     case_id="case-123",
        ...     research_run_id="run-456",
        ...     query="Analyze breach of contract evidence"
        ... )
        >>> print(result["phase"])  # "COMPLETED"
        >>> print(len(result["document_findings"]))
    """
    from .state import create_initial_state

    logger.info(f"Starting research workflow: run_id={research_run_id}, case_id={case_id}")

    # Create initial state
    state = create_initial_state(
        research_run_id=research_run_id,
        case_id=case_id,
        query=query,
        defense_theory=defense_theory,
    )

    # Compile graph
    if use_checkpointing:
        graph = compile_research_graph(use_production_checkpointer=True)
        config = {"configurable": {"thread_id": research_run_id}}
    else:
        graph = compile_graph_without_checkpointing()
        config = {}

    # Execute workflow
    logger.info("Executing research workflow...")
    final_state = await graph.ainvoke(state, config)

    logger.info(f"Research workflow completed: phase={final_state.get('phase')}")
    return final_state


async def resume_research_workflow(
    research_run_id: str,
    checkpointer: Optional[BaseCheckpointSaver] = None,
) -> ResearchState:
    """
    Resume a research workflow from its last checkpoint.

    Args:
        research_run_id: Research run UUID (used as thread ID)
        checkpointer: Optional checkpointer instance

    Returns:
        Final research state after resumption

    Example:
        >>> # Start workflow
        >>> result = await execute_research_workflow(case_id="123", research_run_id="456")
        >>>
        >>> # Later, resume if it was paused or failed
        >>> resumed = await resume_research_workflow(research_run_id="456")
    """
    logger.info(f"Resuming research workflow: run_id={research_run_id}")

    # Compile graph with checkpointing
    graph = compile_research_graph(
        checkpointer=checkpointer,
        use_production_checkpointer=True,
    )

    # Resume from checkpoint (None state tells LangGraph to load from checkpoint)
    config = {"configurable": {"thread_id": research_run_id}}
    final_state = await graph.ainvoke(None, config)

    logger.info(f"Research workflow resumed: phase={final_state.get('phase')}")
    return final_state


# ==================== Graph Introspection ====================

def get_graph_structure() -> dict:
    """
    Get the structure of the research graph for visualization/debugging.

    Returns:
        Dictionary describing nodes and edges
    """
    graph = create_research_graph()

    return {
        "nodes": list(graph.nodes.keys()),
        "edges": [
            {"from": edge[0], "to": edge[1]}
            for edge in graph.edges
        ],
        "entry_point": graph.entry_point,
        "finish_points": graph.finish_points,
    }


def print_graph_structure():
    """
    Print a human-readable representation of the graph structure.
    """
    structure = get_graph_structure()

    print("\n=== Research Graph Structure ===")
    print(f"\nEntry Point: {structure['entry_point']}")
    print(f"\nNodes ({len(structure['nodes'])}):")
    for node in structure['nodes']:
        print(f"  - {node}")

    print(f"\nEdges ({len(structure['edges'])}):")
    for edge in structure['edges']:
        print(f"  {edge['from']} -> {edge['to']}")

    print(f"\nFinish Points: {structure['finish_points']}")
    print("=" * 35 + "\n")
