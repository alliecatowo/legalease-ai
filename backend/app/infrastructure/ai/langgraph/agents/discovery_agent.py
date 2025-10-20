"""
Discovery Agent for evidence inventory.

This agent inventories ALL evidence in a case without assumptions,
creating a comprehensive case map as the foundation for research.
"""

import logging
from typing import Dict, Any, List
from uuid import UUID

from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage

from ..state import ResearchState
from ...ollama.client import get_agent_llm

logger = logging.getLogger(__name__)


# Tool definitions for discovery agent
@tool
def inventory_documents(case_id: str) -> Dict[str, Any]:
    """
    Inventory all documents in a case.

    Args:
        case_id: Case UUID as string

    Returns:
        Document inventory with counts, types, and date ranges
    """
    # NOTE: In production, this would call the actual repository
    # For now, return mock data structure
    logger.info(f"Inventorying documents for case {case_id}")

    return {
        "total_count": 0,
        "document_types": {},
        "date_range": {"earliest": None, "latest": None},
        "documents": [],
    }


@tool
def inventory_transcripts(case_id: str) -> Dict[str, Any]:
    """
    Inventory all transcripts in a case.

    Args:
        case_id: Case UUID as string

    Returns:
        Transcript inventory with counts, speakers, and duration
    """
    logger.info(f"Inventorying transcripts for case {case_id}")

    return {
        "total_count": 0,
        "total_duration_seconds": 0,
        "speakers": [],
        "transcripts": [],
    }


@tool
def inventory_communications(case_id: str) -> Dict[str, Any]:
    """
    Inventory all communications in a case.

    Args:
        case_id: Case UUID as string

    Returns:
        Communication inventory with counts, platforms, and participants
    """
    logger.info(f"Inventorying communications for case {case_id}")

    return {
        "total_count": 0,
        "platforms": [],
        "participants": [],
        "date_range": {"earliest": None, "latest": None},
        "threads": [],
    }


@tool
def extract_entities_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Extract entities (people, organizations, locations, dates) from text.

    Args:
        text: Text to extract entities from

    Returns:
        List of extracted entities with types and names
    """
    # NOTE: In production, this would use spaCy or GLiNER
    logger.info(f"Extracting entities from text (length={len(text)})")

    return []


# System prompt for discovery agent
DISCOVERY_SYSTEM_PROMPT = """You are a legal discovery specialist. Your job is to inventory ALL evidence
in a case without making assumptions. Create a comprehensive case map.

Your responsibilities:
1. Inventory all documents (count, types, date ranges)
2. Inventory all transcripts (count, speakers, duration)
3. Inventory all communications (count, platforms, participants)
4. Extract initial entity list (people, organizations, locations, dates)
5. Determine timeline bounds (earliest to latest evidence)
6. Build a case map with high-level statistics

Be thorough and systematic. Do not skip any evidence type. The case map you create
will be used by other agents to plan their research.

Output your findings in a structured format that includes:
- Evidence counts and types
- Key entities discovered
- Temporal bounds
- Any patterns or anomalies noticed
"""


def discovery_agent_node(state: ResearchState) -> Dict[str, Any]:
    """
    Discovery agent node for LangGraph.

    Inventories all evidence in the case and creates a case map.

    Args:
        state: Current research state

    Returns:
        State updates with discovery results
    """
    logger.info(f"Starting discovery for case {state['case_id']}")

    try:
        # Get LLM for discovery agent
        llm = get_agent_llm("discovery")

        # Define tools
        tools = [
            inventory_documents,
            inventory_transcripts,
            inventory_communications,
            extract_entities_from_text,
        ]

        # Create agent
        agent = create_react_agent(
            llm,
            tools=tools,
            state_modifier=DISCOVERY_SYSTEM_PROMPT,
        )

        # Build user prompt
        case_id_str = str(state["case_id"])
        query = state.get("query", "")

        user_prompt = f"""Case ID: {case_id_str}

Please inventory all evidence and create a case map including:
1. All documents (count, types, date ranges)
2. All transcripts (count, speakers, duration)
3. All communications (count, platforms, participants)
4. Initial entity list (people, organizations, locations, dates)
5. Timeline bounds (earliest to latest evidence)

User query/theory (if provided): {query if query else "None - discover all evidence"}

Be systematic and thorough. Use the inventory tools to gather data."""

        # Execute agent
        logger.info("Executing discovery agent")
        result = agent.invoke({"messages": [("user", user_prompt)]})

        # Parse agent output
        # NOTE: In production, this would parse structured output
        # For now, extract from message content
        messages = result.get("messages", [])
        final_message = messages[-1] if messages else None

        case_map = {
            "total_documents": 0,
            "total_transcripts": 0,
            "total_communications": 0,
            "timeline_bounds": {"earliest": None, "latest": None},
            "entity_count": 0,
            "discovery_summary": final_message.content if final_message else "",
        }

        logger.info("Discovery agent completed successfully")

        return {
            "case_map": case_map,
            "document_inventory": [],
            "transcript_inventory": [],
            "communication_inventory": [],
            "entities": [],
            "phase": "DISCOVERY_COMPLETE",
            "progress_pct": 15.0,
        }

    except Exception as e:
        logger.error(f"Discovery agent failed: {e}", exc_info=True)
        return {
            "phase": "DISCOVERY_FAILED",
            "status": "FAILED",
            "error": str(e),
        }
