"""
LangGraph Tools for Research Agents

This module provides LangChain-compatible tools for the deep research workflow.
All tools use repository interfaces following hexagonal architecture principles.
"""

from .inventory_tools import (
    inventory_documents_tool,
    inventory_transcripts_tool,
    inventory_communications_tool,
    get_case_metadata_tool,
)

from .research_tools import (
    search_evidence_tool,
    get_document_tool,
    get_transcript_tool,
    get_communication_tool,
    extract_entities_tool,
    find_citations_tool,
)

from .graph_tools import (
    create_entity_tool,
    create_event_tool,
    create_relationship_tool,
    get_entity_with_relationships_tool,
    find_connected_entities_tool,
    find_shortest_path_tool,
    get_timeline_tool,
)


# Tool registry for easy access by agent configs
ALL_TOOLS = {
    # Inventory tools
    "inventory_documents": inventory_documents_tool,
    "inventory_transcripts": inventory_transcripts_tool,
    "inventory_communications": inventory_communications_tool,
    "get_case_metadata": get_case_metadata_tool,

    # Research tools
    "search_evidence": search_evidence_tool,
    "get_document": get_document_tool,
    "get_transcript": get_transcript_tool,
    "get_communication": get_communication_tool,
    "extract_entities": extract_entities_tool,
    "find_citations": find_citations_tool,

    # Graph tools
    "create_entity": create_entity_tool,
    "create_event": create_event_tool,
    "create_relationship": create_relationship_tool,
    "get_entity_with_relationships": get_entity_with_relationships_tool,
    "find_connected_entities": find_connected_entities_tool,
    "find_shortest_path": find_shortest_path_tool,
    "get_timeline": get_timeline_tool,
}


def get_tools_for_agent(tool_names: list[str]) -> list:
    """
    Get tool instances for a specific agent.

    Args:
        tool_names: List of tool names from agent config

    Returns:
        List of tool instances

    Raises:
        ValueError: If any tool name is not found
    """
    tools = []
    for name in tool_names:
        if name not in ALL_TOOLS:
            raise ValueError(
                f"Unknown tool: {name}. "
                f"Available tools: {', '.join(ALL_TOOLS.keys())}"
            )
        tools.append(ALL_TOOLS[name])
    return tools


__all__ = [
    # Inventory
    "inventory_documents_tool",
    "inventory_transcripts_tool",
    "inventory_communications_tool",
    "get_case_metadata_tool",

    # Research
    "search_evidence_tool",
    "get_document_tool",
    "get_transcript_tool",
    "get_communication_tool",
    "extract_entities_tool",
    "find_citations_tool",

    # Graph
    "create_entity_tool",
    "create_event_tool",
    "create_relationship_tool",
    "get_entity_with_relationships_tool",
    "find_connected_entities_tool",
    "find_shortest_path_tool",
    "get_timeline_tool",

    # Utilities
    "ALL_TOOLS",
    "get_tools_for_agent",
]
