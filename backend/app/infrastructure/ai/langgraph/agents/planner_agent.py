"""
Planner Agent for research planning.

This agent analyzes the case map and creates a structured research plan
with workstreams, queries, and search heuristics.
"""

import logging
from typing import Dict, Any
import yaml

from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from ..state import ResearchState
from ...ollama.client import get_agent_llm

logger = logging.getLogger(__name__)


# System prompt for planner agent
PLANNER_SYSTEM_PROMPT = """You are a legal research strategist. Create a comprehensive research plan.

Your responsibilities:
1. Analyze the case map from discovery
2. Understand the user's query or defense theory (if provided)
3. Generate workstreams (Document Analysis, Transcript Analysis, Communication Analysis, Correlation)
4. Create targeted queries for each evidence type
5. Define search heuristics (keywords, time windows, entities)
6. Set budget knobs (max documents per pass, recursion depth, diversity goals)

Output a YAML-formatted research plan with the following structure:

```yaml
workstreams:
  - name: "Document Analysis"
    priority: 1
    queries:
      - query: "keyword search or semantic query"
        filters:
          entity: "entity name"
          time_range: ["2024-01-01", "2024-12-31"]
        heuristics:
          - "what to look for"
        budget:
          max_chunks: 100

  - name: "Transcript Analysis"
    priority: 2
    queries: [...]

  - name: "Communication Analysis"
    priority: 3
    queries: [...]

budget:
  max_chunks_per_source: 50
  recursion_depth: 2
  diversity_threshold: 0.7
```

Be strategic and thorough. Prioritize workstreams based on likely value."""


@tool
def analyze_case_map(case_map_json: str) -> str:
    """
    Analyze case map statistics to inform planning.

    Args:
        case_map_json: JSON representation of case map

    Returns:
        Analysis summary
    """
    logger.info("Analyzing case map for planning")
    return "Case map analyzed. Ready to create research plan."


def planner_agent_node(state: ResearchState) -> Dict[str, Any]:
    """
    Planner agent node for LangGraph.

    Creates a research plan with queries and workstreams.

    Args:
        state: Current research state

    Returns:
        State updates with research plan
    """
    logger.info(f"Starting planning for case {state['case_id']}")

    try:
        # Get LLM for planner agent
        llm = get_agent_llm("planner")

        # Define tools
        tools = [analyze_case_map]

        # Create agent
        agent = create_react_agent(
            llm,
            tools=tools,
            state_modifier=PLANNER_SYSTEM_PROMPT,
        )

        # Build user prompt
        case_map = state.get("case_map", {})
        query = state.get("query", "")

        import json
        case_map_json = json.dumps(case_map, indent=2)

        user_prompt = f"""Case map:
{case_map_json}

Query/Theory: {query if query else "Find all relevant evidence"}

Create a research plan with:
1. Workstreams (Document Analysis, Transcript Analysis, Communication Analysis, Cross-Modal Correlation)
2. For each workstream:
   - Search queries (keywords, semantic queries)
   - Entity/time filters
   - Heuristics (what to look for)
   - Stop criteria
3. Priority order
4. Budget (max chunks per source, recursion depth)

Output as structured YAML."""

        # Execute agent
        logger.info("Executing planner agent")
        result = agent.invoke({"messages": [("user", user_prompt)]})

        # Parse agent output
        messages = result.get("messages", [])
        final_message = messages[-1] if messages else None

        # Try to parse YAML from response
        research_plan = {
            "workstreams": [
                {
                    "name": "Document Analysis",
                    "priority": 1,
                    "queries": [],
                },
                {
                    "name": "Transcript Analysis",
                    "priority": 2,
                    "queries": [],
                },
                {
                    "name": "Communication Analysis",
                    "priority": 3,
                    "queries": [],
                },
            ],
            "budget": {
                "max_chunks_per_source": 50,
                "recursion_depth": 2,
                "diversity_threshold": 0.7,
            },
            "plan_summary": final_message.content if final_message else "",
        }

        # Try to extract YAML from message
        if final_message and final_message.content:
            try:
                # Look for YAML code blocks
                content = final_message.content
                if "```yaml" in content:
                    yaml_start = content.find("```yaml") + 7
                    yaml_end = content.find("```", yaml_start)
                    yaml_str = content[yaml_start:yaml_end].strip()
                    parsed_plan = yaml.safe_load(yaml_str)
                    if parsed_plan:
                        research_plan.update(parsed_plan)
            except Exception as e:
                logger.warning(f"Failed to parse YAML from response: {e}")

        logger.info("Planner agent completed successfully")

        return {
            "research_plan": research_plan,
            "phase": "PLANNING_COMPLETE",
            "progress_pct": 20.0,
        }

    except Exception as e:
        logger.error(f"Planner agent failed: {e}", exc_info=True)
        return {
            "phase": "PLANNING_FAILED",
            "status": "FAILED",
            "error": str(e),
        }
