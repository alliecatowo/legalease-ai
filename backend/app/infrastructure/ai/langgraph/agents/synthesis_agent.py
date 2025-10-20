"""
Synthesis Agent for final dossier generation.

This agent creates a comprehensive legal dossier with executive summary,
organized sections, citations appendix, and recommendations.
"""

import logging
from typing import Dict, Any
import json

from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from ..state import ResearchState
from ...ollama.client import get_agent_llm

logger = logging.getLogger(__name__)


# System prompt for synthesis agent
SYNTHESIS_PROMPT = """You are a legal briefing specialist. Generate a comprehensive dossier.

Your responsibilities:
1. Create executive summary (300-500 words)
2. Organize findings into logical sections:
   - Evidence Overview
   - Timeline of Events
   - Key Findings (by type: Documents, Transcripts, Communications)
   - Supporting Evidence for Defense
   - Contradicting Evidence
   - Gaps and Unknowns
   - Recommendations
3. Generate citations appendix (every claim mapped to citation)
4. Assess confidence for each finding
5. Provide strategic recommendations

IMPORTANT RULES:
- Use clear, professional legal language
- Be objective and evidence-based
- Rate confidence for each finding (High/Medium/Low)
- Every claim must have a citation reference
- Organize chronologically within sections where appropriate
- Highlight contradictions and gaps transparently
- Provide actionable recommendations

Structure your dossier with:

# Executive Summary
[300-500 word overview of case, key findings, and significance]

# Evidence Overview
[Summary of evidence inventory and sources]

# Timeline of Events
[Chronological timeline with citations]

# Key Findings

## Document Analysis
[Findings from documents with citations]

## Transcript Analysis
[Findings from transcripts with citations]

## Communications Analysis
[Findings from digital communications with citations]

# Knowledge Graph
[Entity relationships and event chains]

# Supporting Evidence
[Evidence supporting defense theory, if provided]

# Contradicting Evidence
[Evidence contradicting defense theory or internal contradictions]

# Gaps and Unknowns
[Missing information and unanswered questions]

# Recommendations
[Strategic recommendations for investigation or legal strategy]

# Citations Appendix
[Complete list of all citations referenced]
"""


def synthesis_agent_node(state: ResearchState) -> Dict[str, Any]:
    """
    Synthesis agent node for LangGraph.

    Generates final dossier from all research results.

    Args:
        state: Current research state

    Returns:
        State updates with complete dossier
    """
    logger.info(f"Starting synthesis for case {state['case_id']}")

    try:
        # Get LLM for synthesis agent
        llm = get_agent_llm("synthesis")

        # Create agent (no tools needed, uses state only)
        agent = create_react_agent(
            llm,
            tools=[],
            state_modifier=SYNTHESIS_PROMPT,
        )

        # Build comprehensive input from entire state
        case_id = state.get("case_id", "")
        query = state.get("query", "")
        defense_theory = state.get("defense_theory", "")

        case_map = state.get("case_map", {})
        research_plan = state.get("research_plan", {})

        document_findings = state.get("document_findings", [])
        transcript_findings = state.get("transcript_findings", [])
        communication_findings = state.get("communication_findings", [])

        entities = state.get("entities", [])
        events = state.get("events", [])
        relationships = state.get("relationships", [])
        timeline = state.get("timeline", {})
        event_chains = state.get("event_chains", [])
        contradictions = state.get("contradictions", [])
        gaps = state.get("gaps", [])

        # Prepare state summary for synthesis
        state_summary = {
            "case_id": case_id,
            "query": query,
            "defense_theory": defense_theory,
            "case_map": case_map,
            "findings": {
                "documents": {
                    "count": len(document_findings),
                    "samples": document_findings[:10] if document_findings else []
                },
                "transcripts": {
                    "count": len(transcript_findings),
                    "samples": transcript_findings[:10] if transcript_findings else []
                },
                "communications": {
                    "count": len(communication_findings),
                    "samples": communication_findings[:10] if communication_findings else []
                }
            },
            "knowledge_graph": {
                "entities_count": len(entities),
                "events_count": len(events),
                "relationships_count": len(relationships),
                "entities_sample": entities[:10] if entities else [],
                "events_sample": events[:10] if events else []
            },
            "timeline": timeline,
            "event_chains_count": len(event_chains),
            "contradictions_count": len(contradictions),
            "gaps_count": len(gaps),
            "contradictions": contradictions,
            "gaps": gaps,
        }

        state_json = json.dumps(state_summary, indent=2, default=str)

        user_prompt = f"""All research results:

{state_json}

Generate a comprehensive dossier with:
1. Executive Summary (300-500 words)
2. Sections:
   - Evidence Overview
   - Timeline of Events
   - Key Findings (by type)
   - Supporting Evidence for Defense
   - Contradicting Evidence
   - Gaps and Unknowns
   - Recommendations
3. Citations Appendix (every claim → citation)

Use clear, professional legal language. Rate confidence for each finding."""

        # Execute agent
        logger.info("Executing synthesis agent")
        result = agent.invoke({"messages": [("user", user_prompt)]})

        # Parse agent output
        messages = result.get("messages", [])
        final_message = messages[-1] if messages else None

        executive_summary = ""
        dossier_sections = []
        citations_appendix = []

        if final_message and final_message.content:
            content = final_message.content

            # Extract executive summary (first section)
            if "# Executive Summary" in content:
                summary_start = content.find("# Executive Summary") + len("# Executive Summary")
                summary_end = content.find("#", summary_start)
                if summary_end == -1:
                    summary_end = len(content)
                executive_summary = content[summary_start:summary_end].strip()

            # Parse sections (simplified - in production would be more sophisticated)
            section_headers = [
                "Evidence Overview",
                "Timeline of Events",
                "Key Findings",
                "Supporting Evidence",
                "Contradicting Evidence",
                "Gaps and Unknowns",
                "Recommendations",
            ]

            for header in section_headers:
                if f"# {header}" in content:
                    section_start = content.find(f"# {header}") + len(f"# {header}")
                    section_end = content.find("#", section_start)
                    if section_end == -1:
                        section_end = len(content)

                    section_content = content[section_start:section_end].strip()

                    dossier_sections.append({
                        "title": header,
                        "content": section_content,
                        "citations": []  # Would be extracted from content
                    })

        logger.info(f"Synthesis completed: {len(dossier_sections)} sections")

        return {
            "executive_summary": executive_summary,
            "dossier_sections": dossier_sections,
            "citations_appendix": citations_appendix,
            "phase": "SYNTHESIS_COMPLETE",
            "status": "COMPLETED",
            "progress_pct": 100.0,
        }

    except Exception as e:
        logger.error(f"Synthesis agent failed: {e}", exc_info=True)
        return {
            "phase": "SYNTHESIS_FAILED",
            "status": "FAILED",
            "errors": [str(e)],
        }
