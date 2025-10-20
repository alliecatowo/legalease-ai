"""
Correlator Agent for cross-modal correlation and knowledge graph construction.

This agent combines findings from all analysts, builds a knowledge graph,
constructs timelines, finds event chains, detects contradictions, and identifies gaps.
"""

import logging
from typing import Dict, Any, List
import json

from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from ..state import ResearchState
from ...ollama.client import get_agent_llm

logger = logging.getLogger(__name__)


# Tool definitions for correlator agent
@tool
def create_entity(entity_data: str) -> Dict[str, Any]:
    """
    Create an entity in the knowledge graph.

    Args:
        entity_data: JSON string with entity data (name, type, attributes)

    Returns:
        Created entity with assigned ID
    """
    logger.info("Creating entity in knowledge graph")

    # NOTE: In production, this would call the graph repository
    try:
        data = json.loads(entity_data)
        return {
            "entity_id": "new-entity-id",
            "name": data.get("name", ""),
            "entity_type": data.get("type", "PERSON"),
        }
    except Exception as e:
        logger.error(f"Failed to create entity: {e}")
        return {}


@tool
def create_event(event_data: str) -> Dict[str, Any]:
    """
    Create an event in the knowledge graph.

    Args:
        event_data: JSON string with event data (description, timestamp, participants)

    Returns:
        Created event with assigned ID
    """
    logger.info("Creating event in knowledge graph")

    try:
        data = json.loads(event_data)
        return {
            "event_id": "new-event-id",
            "description": data.get("description", ""),
            "timestamp": data.get("timestamp", ""),
        }
    except Exception as e:
        logger.error(f"Failed to create event: {e}")
        return {}


@tool
def create_relationship(relationship_data: str) -> Dict[str, Any]:
    """
    Create a relationship between entities.

    Args:
        relationship_data: JSON string with relationship data (from, to, type)

    Returns:
        Created relationship with assigned ID
    """
    logger.info("Creating relationship in knowledge graph")

    try:
        data = json.loads(relationship_data)
        return {
            "relationship_id": "new-relationship-id",
            "from_entity": data.get("from", ""),
            "to_entity": data.get("to", ""),
            "relationship_type": data.get("type", "RELATED_TO"),
        }
    except Exception as e:
        logger.error(f"Failed to create relationship: {e}")
        return {}


@tool
def find_shortest_path(entity1_id: str, entity2_id: str) -> List[Dict[str, Any]]:
    """
    Find shortest path between two entities in the graph.

    Args:
        entity1_id: First entity ID
        entity2_id: Second entity ID

    Returns:
        List of relationships forming the path
    """
    logger.info(f"Finding path between {entity1_id} and {entity2_id}")

    # NOTE: In production, this would query the graph database
    return []


@tool
def build_timeline(case_id: str) -> Dict[str, Any]:
    """
    Build chronological timeline of all events.

    Args:
        case_id: Case UUID as string

    Returns:
        Timeline with events ordered chronologically
    """
    logger.info(f"Building timeline for case {case_id}")

    return {
        "events": [],
        "earliest": None,
        "latest": None,
    }


# System prompt for correlator agent
CORRELATOR_PROMPT = """You are a legal correlation specialist. Build a knowledge graph and find patterns.

Your responsibilities:
1. Merge entities from all findings (resolve duplicates, aliases)
2. Create events from findings (with timestamps, participants, locations)
3. Create relationships between entities
4. Build chronological timeline
5. Find event chains (causal sequences of related events)
6. Detect contradictions (conflicting claims across sources)
7. Identify gaps (unknown information, missing connections)

IMPORTANT RULES:
- Merge duplicate entities (same person mentioned in different sources)
- Resolve aliases (John Doe, J. Doe, Jonathan Doe)
- Every event must have a timestamp
- Relationships must be meaningful (not just "mentioned together")
- Event chains show causality or temporal sequences
- Contradictions require evidence from multiple sources
- Gaps indicate missing information needed for complete picture

Output structured analysis with:
- Consolidated entity list
- Timeline of events
- Entity relationship graph
- Event chains (narratives)
- Contradictions found
- Gaps identified
"""


def correlator_agent_node(state: ResearchState) -> Dict[str, Any]:
    """
    Correlator agent node for LangGraph.

    Builds knowledge graph from all analyst findings.

    Args:
        state: Current research state

    Returns:
        State updates with knowledge graph and correlations
    """
    logger.info(f"Starting correlation for case {state['case_id']}")

    try:
        # Get LLM for correlator agent
        llm = get_agent_llm("correlator")

        # Define tools
        tools = [
            create_entity,
            create_event,
            create_relationship,
            find_shortest_path,
            build_timeline,
        ]

        # Create agent
        agent = create_react_agent(
            llm,
            tools=tools,
            state_modifier=CORRELATOR_PROMPT,
        )

        # Build user prompt with all findings
        document_findings = state.get("document_findings", [])
        transcript_findings = state.get("transcript_findings", [])
        communication_findings = state.get("communication_findings", [])

        # Prepare findings summary
        findings_summary = {
            "document_findings_count": len(document_findings),
            "transcript_findings_count": len(transcript_findings),
            "communication_findings_count": len(communication_findings),
            "sample_findings": {
                "documents": document_findings[:5] if document_findings else [],
                "transcripts": transcript_findings[:5] if transcript_findings else [],
                "communications": communication_findings[:5] if communication_findings else [],
            }
        }

        findings_json = json.dumps(findings_summary, indent=2)

        user_prompt = f"""All findings from analysts:

{findings_json}

Tasks:
1. Merge entities (resolve duplicates and aliases)
2. Create events from findings (with timestamps, participants, locations)
3. Create relationships between entities
4. Build timeline
5. Find event chains (causal sequences)
6. Detect contradictions (conflicting claims)
7. Identify gaps (unknown information)

Use the knowledge graph tools to create entities, events, and relationships."""

        # Execute agent
        logger.info("Executing correlator agent")
        result = agent.invoke({"messages": [("user", user_prompt)]})

        # Parse agent output
        messages = result.get("messages", [])
        final_message = messages[-1] if messages else None

        # Extract structured outputs
        entities = []
        events = []
        relationships = []
        event_chains = []
        contradictions = []
        gaps = []
        timeline = {"events": [], "earliest": None, "latest": None}

        if final_message and final_message.content:
            # In production, this would parse structured output from the agent
            # For now, we create placeholder structures
            logger.info("Parsing correlator output")

        logger.info(f"Correlation completed: {len(entities)} entities, {len(events)} events")

        return {
            "entities": entities,
            "events": events,
            "relationships": relationships,
            "timeline": timeline,
            "event_chains": event_chains,
            "contradictions": contradictions,
            "gaps": gaps,
            "phase": "CORRELATION_COMPLETE",
            "progress_pct": 90.0,
        }

    except Exception as e:
        logger.error(f"Correlator agent failed: {e}", exc_info=True)
        return {
            "phase": "CORRELATION_FAILED",
            "errors": [str(e)],
        }
