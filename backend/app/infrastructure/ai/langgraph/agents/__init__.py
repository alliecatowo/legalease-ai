"""
LangGraph agent implementations for deep research workflow.

This package contains all specialized agents for the multi-agent research system:
- DiscoveryAgent: Inventory all evidence in the case
- PlannerAgent: Create research plan with workstreams and queries
- DocumentAnalystAgent: Analyze legal documents with precise citations
- TranscriptAnalystAgent: Analyze audio/video transcripts
- CommunicationsAnalystAgent: Analyze digital communications
- CorrelatorAgent: Build knowledge graph and find patterns
- SynthesisAgent: Generate final dossier

Each agent is implemented as a node function that:
1. Receives ResearchState as input
2. Uses LLM with appropriate tools
3. Returns partial state updates (Dict[str, Any])
"""

from .discovery_agent import discovery_agent_node
from .planner_agent import planner_agent_node
from .document_analyst import document_analyst_node
from .transcript_analyst import transcript_analyst_node
from .communications_analyst import communications_analyst_node
from .correlator_agent import correlator_agent_node
from .synthesis_agent import synthesis_agent_node

__all__ = [
    "discovery_agent_node",
    "planner_agent_node",
    "document_analyst_node",
    "transcript_analyst_node",
    "communications_analyst_node",
    "correlator_agent_node",
    "synthesis_agent_node",
]
