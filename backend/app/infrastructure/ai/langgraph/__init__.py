"""
LangGraph Deep Research Workflow

This module provides a multi-agent research workflow using LangGraph for
orchestrating AI agents in legal case research.

Architecture:
- State: ResearchState TypedDict with reducer patterns
- Agents: Discovery, Planner, Analysts (Documents, Transcripts, Communications), Correlator, Synthesis
- Graph: StateGraph with conditional routing and checkpointing
- Tools: LangChain tools using repository interfaces

Usage:
    >>> from app.infrastructure.ai.langgraph import compile_research_graph, create_initial_state
    >>>
    >>> # Create and execute research workflow
    >>> graph = compile_research_graph(use_production_checkpointer=True)
    >>> state = create_initial_state(
    ...     research_run_id="run-123",
    ...     case_id="case-456",
    ...     query="Analyze contract breach evidence"
    ... )
    >>> config = {"configurable": {"thread_id": "run-123"}}
    >>> result = await graph.ainvoke(state, config)

Workflow Phases:
1. DISCOVERY - Inventory all evidence in the case
2. PLANNING - Create research plan with workstreams and queries
3. ANALYSIS - Parallel analysis of documents, transcripts, communications
4. CORRELATION - Build knowledge graph and find patterns
5. SYNTHESIS - Generate final dossier
"""

# State management
from .state import (
    ResearchState,
    create_initial_state,
    update_phase,
    update_progress,
    update_status,
    update_current_agent,
    add_error,
    mark_completed,
    mark_failed,
    validate_state,
    get_state_summary,
)

# Agent configuration
from .agent_config import (
    AgentConfig,
    AGENT_CONFIGS,
    get_agent_config,
    list_agents,
    DISCOVERY_AGENT_CONFIG,
    PLANNER_AGENT_CONFIG,
    DOCUMENT_ANALYST_CONFIG,
    TRANSCRIPT_ANALYST_CONFIG,
    COMMUNICATIONS_ANALYST_CONFIG,
    CORRELATOR_AGENT_CONFIG,
    SYNTHESIS_AGENT_CONFIG,
)

# LLM clients
from .llm_client import (
    LangGraphOllamaClient,
    get_ollama_llm,
    get_langgraph_client,
    get_default_model,
    get_model_for_agent,
    ensure_models_ready,
    test_model_connection,
)

# Tools
from .tools import (
    ALL_TOOLS,
    get_tools_for_agent,
    # Inventory tools
    inventory_documents_tool,
    inventory_transcripts_tool,
    inventory_communications_tool,
    get_case_metadata_tool,
    # Research tools
    search_evidence_tool,
    get_document_tool,
    get_transcript_tool,
    get_communication_tool,
    extract_entities_tool,
    find_citations_tool,
    # Graph tools
    create_entity_tool,
    create_event_tool,
    create_relationship_tool,
    get_entity_with_relationships_tool,
    find_connected_entities_tool,
    find_shortest_path_tool,
    get_timeline_tool,
)

# Graph construction and compilation
from .compile_graph import (
    compile_research_graph,
    compile_graph_without_checkpointing,
    get_checkpointer,
    get_development_checkpointer,
    get_production_checkpointer,
    execute_research_workflow,
    resume_research_workflow,
    get_checkpoint_state,
    list_checkpoints,
    delete_checkpoint,
    get_graph_structure,
    print_graph_structure,
)

# Graph structure
from .graphs.research_graph import (
    create_research_graph,
    discovery_node,
    planner_node,
    document_analyst_node,
    transcript_analyst_node,
    communications_analyst_node,
    correlator_node,
    synthesis_node,
    route_to_analysts,
)


__all__ = [
    # State
    "ResearchState",
    "create_initial_state",
    "update_phase",
    "update_progress",
    "update_status",
    "update_current_agent",
    "add_error",
    "mark_completed",
    "mark_failed",
    "validate_state",
    "get_state_summary",

    # Agent config
    "AgentConfig",
    "AGENT_CONFIGS",
    "get_agent_config",
    "list_agents",
    "DISCOVERY_AGENT_CONFIG",
    "PLANNER_AGENT_CONFIG",
    "DOCUMENT_ANALYST_CONFIG",
    "TRANSCRIPT_ANALYST_CONFIG",
    "COMMUNICATIONS_ANALYST_CONFIG",
    "CORRELATOR_AGENT_CONFIG",
    "SYNTHESIS_AGENT_CONFIG",

    # LLM
    "LangGraphOllamaClient",
    "get_ollama_llm",
    "get_langgraph_client",
    "get_default_model",
    "get_model_for_agent",
    "ensure_models_ready",
    "test_model_connection",

    # Tools
    "ALL_TOOLS",
    "get_tools_for_agent",
    "inventory_documents_tool",
    "inventory_transcripts_tool",
    "inventory_communications_tool",
    "get_case_metadata_tool",
    "search_evidence_tool",
    "get_document_tool",
    "get_transcript_tool",
    "get_communication_tool",
    "extract_entities_tool",
    "find_citations_tool",
    "create_entity_tool",
    "create_event_tool",
    "create_relationship_tool",
    "get_entity_with_relationships_tool",
    "find_connected_entities_tool",
    "find_shortest_path_tool",
    "get_timeline_tool",

    # Graph compilation
    "compile_research_graph",
    "compile_graph_without_checkpointing",
    "get_checkpointer",
    "get_development_checkpointer",
    "get_production_checkpointer",
    "execute_research_workflow",
    "resume_research_workflow",
    "get_checkpoint_state",
    "list_checkpoints",
    "delete_checkpoint",
    "get_graph_structure",
    "print_graph_structure",

    # Graph nodes
    "create_research_graph",
    "discovery_node",
    "planner_node",
    "document_analyst_node",
    "transcript_analyst_node",
    "communications_analyst_node",
    "correlator_node",
    "synthesis_node",
    "route_to_analysts",
]
