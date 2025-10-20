"""
Transcript Analyst Agent for audio/video transcript analysis.

This agent analyzes transcripts, extracting quotes with speaker + timecode,
analyzing sentiment, detecting contradictions, and identifying hot clips.
"""

import logging
from typing import Dict, Any, List
import json

from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from ..state import ResearchState
from ...ollama.client import get_agent_llm

logger = logging.getLogger(__name__)


# Tool definitions for transcript analyst
@tool
def search_transcripts(
    case_id: str,
    query: str,
    speaker_filter: str = "",
    time_range: str = "{}",
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    Search transcripts using semantic or keyword search.

    Args:
        case_id: Case UUID as string
        query: Search query
        speaker_filter: Optional speaker name filter
        time_range: JSON string with start/end times
        top_k: Maximum number of results

    Returns:
        List of relevant transcript segments with metadata
    """
    logger.info(f"Searching transcripts: query='{query}', speaker='{speaker_filter}', top_k={top_k}")

    # NOTE: In production, this would call the actual search repository
    return []


@tool
def get_transcript_segment(segment_id: str) -> Dict[str, Any]:
    """
    Get a specific transcript segment by ID.

    Args:
        segment_id: Segment UUID as string

    Returns:
        Full segment with speaker, timecode, and text
    """
    logger.info(f"Retrieving transcript segment: {segment_id}")

    return {
        "segment_id": segment_id,
        "speaker": "Speaker A",
        "timecode_start": 0.0,
        "timecode_end": 0.0,
        "text": "",
        "transcript_id": "",
    }


@tool
def extract_entities(text: str) -> List[Dict[str, Any]]:
    """
    Extract entities (people, organizations, locations, dates) from text.

    Args:
        text: Text to extract entities from

    Returns:
        List of extracted entities with types
    """
    logger.info(f"Extracting entities from text (length={len(text)})")

    # NOTE: In production, this would use spaCy or GLiNER
    return []


# System prompt for transcript analyst
TRANSCRIPT_ANALYST_PROMPT = """You are a transcript analyst. Extract quotes and insights with precise timecodes.

Your responsibilities:
1. Execute queries on transcript segments
2. Extract quotes with speaker + timecode (start/end)
3. Analyze speaker intent and sentiment
4. Detect contradictions between speakers or across time
5. Build timeline of events mentioned in transcripts
6. Identify hot clips (threats, admissions, planning, locations)
7. Extract mentioned entities

IMPORTANT RULES:
- Every quote MUST have speaker + timecode citation
- Timecodes must include start and end times in seconds
- Note speaker emotions and intent when relevant
- Flag contradictions (same speaker different times, or different speakers)
- Identify key moments: threats, admissions, planning, location mentions
- Extract all mentioned entities (people, places, dates, events)

Output findings in this JSON structure:
{
  "finding_type": "QUOTE" | "CONTRADICTION" | "KEY_MOMENT",
  "text": "Human-readable description",
  "entities": ["entity1", "entity2"],
  "citations": [{
    "source_id": "transcript-uuid",
    "source_type": "TRANSCRIPT",
    "locator": {
      "speaker": "Speaker A",
      "timecode_start": 914.2,
      "timecode_end": 918.5
    },
    "excerpt": "exact quote"
  }],
  "confidence": 0.92,
  "sentiment": "THREATENING" | "DEFENSIVE" | "NEUTRAL" | etc.,
  "key_moment_type": "THREAT" | "ADMISSION" | "PLANNING" | "LOCATION" | etc.
}"""


def transcript_analyst_node(state: ResearchState) -> Dict[str, Any]:
    """
    Transcript analyst agent node for LangGraph.

    Analyzes transcripts according to research plan queries.

    Args:
        state: Current research state

    Returns:
        State updates with transcript findings
    """
    logger.info(f"Starting transcript analysis for case {state['case_id']}")

    try:
        # Get LLM for transcript analyst
        llm = get_agent_llm("transcript_analyst")

        # Define tools
        tools = [
            search_transcripts,
            get_transcript_segment,
            extract_entities,
        ]

        # Create agent
        agent = create_react_agent(
            llm,
            tools=tools,
            state_modifier=TRANSCRIPT_ANALYST_PROMPT,
        )

        # Build user prompt from research plan
        case_id_str = str(state["case_id"])
        research_plan = state.get("research_plan", {})

        # Extract transcript analysis queries
        workstreams = research_plan.get("workstreams", []) if research_plan else []
        transcript_workstream = next(
            (w for w in workstreams if "transcript" in w.get("name", "").lower()),
            {"queries": []}
        )
        queries = transcript_workstream.get("queries", [])

        if not queries:
            # Default queries if plan doesn't specify
            queries = [
                {"query": "Find all significant quotes and admissions"},
            ]

        queries_json = json.dumps(queries, indent=2)

        user_prompt = f"""Case ID: {case_id_str}

Research queries for transcripts:
{queries_json}

For each transcript query:
1. Search relevant segments
2. Extract:
   - Quotes (with speaker, timecode start/end, text)
   - Speaker intent/sentiment
   - Contradictions (different speakers, different times)
   - Key moments (threats, admissions, planning, locations)
   - Entities mentioned

IMPORTANT: Every quote must have speaker + timecode citation."""

        # Execute agent
        logger.info("Executing transcript analyst agent")
        result = agent.invoke({"messages": [("user", user_prompt)]})

        # Parse agent output
        messages = result.get("messages", [])
        final_message = messages[-1] if messages else None

        # Try to extract findings from response
        findings = []
        events = []

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
            except Exception as e:
                logger.warning(f"Failed to parse findings from response: {e}")

        logger.info(f"Transcript analyst completed: {len(findings)} findings")

        return {
            "transcript_findings": findings,
            "events": events,
            "phase": "TRANSCRIPT_ANALYSIS_COMPLETE",
            "progress_pct": 65.0,
        }

    except Exception as e:
        logger.error(f"Transcript analyst failed: {e}", exc_info=True)
        return {
            "phase": "TRANSCRIPT_ANALYSIS_FAILED",
            "errors": [str(e)],
        }
