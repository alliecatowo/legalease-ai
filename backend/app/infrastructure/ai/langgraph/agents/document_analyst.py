"""
Document Analyst Agent for deep analysis of legal documents.

This agent executes queries from the research plan on documents,
extracting facts, claims, quotes with precise citations.
"""

import logging
from typing import Dict, Any, List
import json

from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from ..state import ResearchState
from ...ollama.client import get_agent_llm

logger = logging.getLogger(__name__)


# Tool definitions for document analyst
@tool
def search_documents(
    case_id: str,
    query: str,
    filters: str = "{}",
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    Search documents in a case using semantic or keyword search.

    Args:
        case_id: Case UUID as string
        query: Search query (semantic or keyword)
        filters: JSON string with filters (entity, date_range, etc.)
        top_k: Maximum number of results

    Returns:
        List of relevant document chunks with metadata
    """
    logger.info(f"Searching documents: query='{query}', top_k={top_k}")

    # NOTE: In production, this would call the actual search repository
    return []


@tool
def get_document_chunk(chunk_id: str) -> Dict[str, Any]:
    """
    Get a specific document chunk by ID.

    Args:
        chunk_id: Chunk UUID as string

    Returns:
        Full chunk content with metadata
    """
    logger.info(f"Retrieving document chunk: {chunk_id}")

    return {
        "chunk_id": chunk_id,
        "text": "",
        "page": 1,
        "paragraph": 1,
        "document_id": "",
    }


@tool
def extract_entities(text: str) -> List[Dict[str, Any]]:
    """
    Extract entities (people, organizations, locations, dates) from text.

    Args:
        text: Text to extract entities from

    Returns:
        List of extracted entities with types and positions
    """
    logger.info(f"Extracting entities from text (length={len(text)})")

    # NOTE: In production, this would use spaCy or GLiNER
    return []


@tool
def extract_citations_from_chunk(
    text: str,
    page: int,
    paragraph: int,
    excerpt: str
) -> Dict[str, Any]:
    """
    Create a citation from a chunk with precise locator.

    Args:
        text: Full chunk text
        page: Page number
        paragraph: Paragraph number
        excerpt: Excerpt to cite

    Returns:
        Citation object with locator
    """
    logger.info(f"Creating citation: page={page}, paragraph={paragraph}")

    return {
        "page": page,
        "paragraph": paragraph,
        "excerpt": excerpt,
    }


# System prompt for document analyst
DOCUMENT_ANALYST_PROMPT = """You are a legal document analyst. Extract facts and evidence with precise citations.

Your responsibilities:
1. Execute queries from the research plan on documents
2. Extract facts, claims, quotes with precise citations (page, paragraph)
3. Identify key evidence types: motive, intent, opportunity, alibi, physical evidence
4. Extract entities and relationships
5. Find contradictions between documents
6. Assign confidence scores to each finding

IMPORTANT RULES:
- Every finding MUST have a precise citation with page, paragraph, and excerpt
- Confidence scores must be 0.0-1.0 based on evidence strength
- Focus on factual claims, not speculation
- Note when evidence is ambiguous or contradictory
- Extract all mentioned entities (people, organizations, locations, dates)

Output findings in this JSON structure:
{
  "finding_type": "FACT" | "QUOTE" | "EVIDENCE" | "CONTRADICTION",
  "text": "Human-readable description",
  "entities": ["entity1", "entity2"],
  "citations": [{
    "source_id": "doc-uuid",
    "source_type": "DOCUMENT",
    "locator": {"page": 12, "paragraph": 3},
    "excerpt": "exact text excerpt"
  }],
  "confidence": 0.85,
  "relevance": 0.90,
  "evidence_type": "MOTIVE" | "INTENT" | "OPPORTUNITY" | "ALIBI" | etc.
}"""


def document_analyst_node(state: ResearchState) -> Dict[str, Any]:
    """
    Document analyst agent node for LangGraph.

    Analyzes documents according to research plan queries.

    Args:
        state: Current research state

    Returns:
        State updates with document findings
    """
    logger.info(f"Starting document analysis for case {state['case_id']}")

    try:
        # Get LLM for document analyst
        llm = get_agent_llm("document_analyst")

        # Define tools
        tools = [
            search_documents,
            get_document_chunk,
            extract_entities,
            extract_citations_from_chunk,
        ]

        # Create agent
        agent = create_react_agent(
            llm,
            tools=tools,
            state_modifier=DOCUMENT_ANALYST_PROMPT,
        )

        # Build user prompt from research plan
        case_id_str = str(state["case_id"])
        research_plan = state.get("research_plan", {})

        # Extract document analysis queries
        workstreams = research_plan.get("workstreams", []) if research_plan else []
        doc_workstream = next(
            (w for w in workstreams if "document" in w.get("name", "").lower()),
            {"queries": []}
        )
        queries = doc_workstream.get("queries", [])

        if not queries:
            # Default queries if plan doesn't specify
            queries = [
                {"query": "Find all relevant evidence"},
            ]

        queries_json = json.dumps(queries, indent=2)

        user_prompt = f"""Case ID: {case_id_str}

Research plan queries for documents:
{queries_json}

For each query:
1. Search documents
2. Read relevant chunks
3. Extract:
   - Facts/claims (with citations: page, paragraph, excerpt)
   - Entities (people, organizations, locations, dates)
   - Relationships between entities
   - Evidence type (motive, intent, opportunity, alibi, physical evidence)
   - Confidence score (0.0-1.0)

IMPORTANT: Every finding must have a precise citation."""

        # Execute agent
        logger.info("Executing document analyst agent")
        result = agent.invoke({"messages": [("user", user_prompt)]})

        # Parse agent output
        messages = result.get("messages", [])
        final_message = messages[-1] if messages else None

        # Try to extract findings from response
        findings = []
        if final_message and final_message.content:
            try:
                # Look for JSON structures in the response
                content = final_message.content
                # Simple extraction - in production, this would be more sophisticated
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

        logger.info(f"Document analyst completed: {len(findings)} findings")

        return {
            "document_findings": findings,
            "phase": "DOCUMENT_ANALYSIS_COMPLETE",
            "progress_pct": 50.0,
        }

    except Exception as e:
        logger.error(f"Document analyst failed: {e}", exc_info=True)
        return {
            "phase": "DOCUMENT_ANALYSIS_FAILED",
            "errors": [str(e)],
        }
