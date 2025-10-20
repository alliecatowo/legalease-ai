"""
Communications Analyst Agent for digital forensics.

This agent analyzes digital communications (Cellebrite), detecting patterns,
finding gaps, building participant maps, and cross-device correlation.
"""

import logging
from typing import Dict, Any, List
import json

from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from ..state import ResearchState
from ...ollama.client import get_agent_llm

logger = logging.getLogger(__name__)


# Tool definitions for communications analyst
@tool
def search_communications(
    case_id: str,
    query: str,
    thread_filter: str = "",
    participant_filter: str = "",
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    Search communications using semantic or keyword search.

    Args:
        case_id: Case UUID as string
        query: Search query
        thread_filter: Optional thread ID filter
        participant_filter: Optional participant name filter
        top_k: Maximum number of results

    Returns:
        List of relevant messages with metadata
    """
    logger.info(f"Searching communications: query='{query}', participant='{participant_filter}', top_k={top_k}")

    # NOTE: In production, this would call the actual search repository
    return []


@tool
def get_thread(thread_id: str) -> Dict[str, Any]:
    """
    Get all messages in a conversation thread.

    Args:
        thread_id: Thread UUID or identifier as string

    Returns:
        Thread with all messages in chronological order
    """
    logger.info(f"Retrieving thread: {thread_id}")

    return {
        "thread_id": thread_id,
        "participants": [],
        "messages": [],
        "platform": "SMS",
    }


@tool
def detect_gaps(thread_id: str) -> List[Dict[str, Any]]:
    """
    Detect gaps in communication (deleted messages, time gaps).

    Args:
        thread_id: Thread UUID or identifier as string

    Returns:
        List of detected gaps with descriptions
    """
    logger.info(f"Detecting gaps in thread: {thread_id}")

    return []


# System prompt for communications analyst
COMMUNICATIONS_ANALYST_PROMPT = """You are a digital forensics analyst specializing in communications.

Your responsibilities:
1. Analyze message threads for patterns and evidence
2. Extract important messages (threats, planning, admissions, location data)
3. Map participant relationships (who talks to whom, frequency)
4. Analyze communication patterns over time
5. Detect gaps (deleted messages, suspicious time windows)
6. Find cross-references to physical events
7. Build timeline of digital communications

IMPORTANT RULES:
- Citations must include thread_id, message_id, timestamp, sender
- Note communication patterns (frequency, timing, platforms)
- Flag suspicious gaps or deletions
- Identify participant roles and relationships
- Extract location data from messages when present
- Note platform-specific metadata (read receipts, etc.)

Output findings in this JSON structure:
{
  "finding_type": "MESSAGE" | "PATTERN" | "GAP" | "RELATIONSHIP",
  "text": "Human-readable description",
  "entities": ["participant1", "participant2"],
  "citations": [{
    "source_id": "thread-uuid",
    "source_type": "COMMUNICATION",
    "locator": {
      "thread_id": "thread-123",
      "message_id": "msg-456",
      "timestamp": "2024-03-15T14:30:00Z",
      "sender": "John Doe"
    },
    "excerpt": "message text"
  }],
  "confidence": 0.88,
  "pattern_type": "THREAT" | "PLANNING" | "LOCATION_SHARING" | etc.
}"""


def communications_analyst_node(state: ResearchState) -> Dict[str, Any]:
    """
    Communications analyst agent node for LangGraph.

    Analyzes digital communications according to research plan queries.

    Args:
        state: Current research state

    Returns:
        State updates with communication findings
    """
    logger.info(f"Starting communications analysis for case {state['case_id']}")

    try:
        # Get LLM for communications analyst
        llm = get_agent_llm("communications_analyst")

        # Define tools
        tools = [
            search_communications,
            get_thread,
            detect_gaps,
        ]

        # Create agent
        agent = create_react_agent(
            llm,
            tools=tools,
            state_modifier=COMMUNICATIONS_ANALYST_PROMPT,
        )

        # Build user prompt from research plan
        case_id_str = str(state["case_id"])
        research_plan = state.get("research_plan", {})

        # Extract communications analysis queries
        workstreams = research_plan.get("workstreams", []) if research_plan else []
        comm_workstream = next(
            (w for w in workstreams if "communication" in w.get("name", "").lower()),
            {"queries": []}
        )
        queries = comm_workstream.get("queries", [])

        if not queries:
            # Default queries if plan doesn't specify
            queries = [
                {"query": "Find all significant communications and patterns"},
            ]

        queries_json = json.dumps(queries, indent=2)

        user_prompt = f"""Case ID: {case_id_str}

Research queries for communications:
{queries_json}

Analyze digital communications:
1. Search relevant threads
2. Extract:
   - Important messages (threats, planning, admissions, location data)
   - Participant relationships (who talks to whom, frequency)
   - Communication patterns over time
   - Gaps (deleted messages, suspicious time windows)
   - Cross-references to physical events

IMPORTANT: Citations must include thread_id, message_id, timestamp, sender."""

        # Execute agent
        logger.info("Executing communications analyst agent")
        result = agent.invoke({"messages": [("user", user_prompt)]})

        # Parse agent output
        messages = result.get("messages", [])
        final_message = messages[-1] if messages else None

        # Try to extract findings from response
        findings = []
        relationships = []
        gaps = []

        if final_message and final_message.content:
            try:
                content = final_message.content
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    json_str = content[json_start:json_end].strip()
                    parsed = json.loads(json_str)
                    if isinstance(parsed, list):
                        findings = parsed
                    elif isinstance(parsed, dict):
                        findings = [parsed]

                # Extract relationships and gaps from findings
                for finding in findings:
                    if finding.get("finding_type") == "RELATIONSHIP":
                        relationships.append(finding)
                    elif finding.get("finding_type") == "GAP":
                        gap_desc = finding.get("text", "Unknown gap")
                        gaps.append(gap_desc)

            except Exception as e:
                logger.warning(f"Failed to parse findings from response: {e}")

        logger.info(f"Communications analyst completed: {len(findings)} findings")

        return {
            "communication_findings": findings,
            "relationships": relationships,
            "gaps": gaps,
            "phase": "COMMUNICATION_ANALYSIS_COMPLETE",
            "progress_pct": 80.0,
        }

    except Exception as e:
        logger.error(f"Communications analyst failed: {e}", exc_info=True)
        return {
            "phase": "COMMUNICATION_ANALYSIS_FAILED",
            "errors": [str(e)],
        }
