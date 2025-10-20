# LangGraph Deep Research Workflow

This module implements a multi-agent research workflow using LangGraph for orchestrating AI agents in legal case research.

## Architecture Overview

### State Management (`state.py`)

The workflow uses a comprehensive `ResearchState` TypedDict with LangGraph's reducer pattern for state management:

```python
from app.infrastructure.ai.langgraph import create_initial_state, compile_research_graph

# Create initial state
state = create_initial_state(
    research_run_id="run-123",
    case_id="case-456",
    query="Analyze contract breach evidence"
)
```

**Key State Features:**
- **Reducers**: Uses `Annotated[List, operator.add]` for append-only lists
- **Immutability**: Nodes return partial state updates that are merged
- **Metadata**: Tracks phase, status, progress, errors, and timestamps

### Workflow Phases

1. **DISCOVERY** - Inventory all evidence
   - Documents, transcripts, communications
   - Case map with parties, claims, timeline

2. **PLANNING** - Create research plan
   - Workstreams and priorities
   - Search queries
   - Analysis heuristics

3. **ANALYSIS** - Parallel evidence analysis
   - Document Analyst
   - Transcript Analyst
   - Communications Analyst

4. **CORRELATION** - Build knowledge graph
   - Merge entities across sources
   - Construct timeline
   - Identify event chains
   - Find contradictions and gaps

5. **SYNTHESIS** - Generate dossier
   - Executive summary
   - Structured sections
   - Citations appendix

### Agent Configuration (`agent_config.py`)

Each agent has a comprehensive configuration:

```python
from app.infrastructure.ai.langgraph import AGENT_CONFIGS, get_agent_config

# Get configuration for specific agent
discovery_config = get_agent_config("discovery")

print(discovery_config.model)  # Ollama model
print(discovery_config.temperature)  # 0.1 (low for factual work)
print(discovery_config.tools)  # Available tools
```

**Agent Configurations:**
- `DISCOVERY_AGENT_CONFIG` - Evidence inventory
- `PLANNER_AGENT_CONFIG` - Research planning
- `DOCUMENT_ANALYST_CONFIG` - Document analysis
- `TRANSCRIPT_ANALYST_CONFIG` - Transcript analysis
- `COMMUNICATIONS_ANALYST_CONFIG` - Communications analysis
- `CORRELATOR_AGENT_CONFIG` - Pattern detection
- `SYNTHESIS_AGENT_CONFIG` - Dossier generation

### Tools (`tools/`)

All tools follow hexagonal architecture using repository interfaces:

**Inventory Tools** (`tools/inventory_tools.py`):
- `inventory_documents_tool` - List all documents
- `inventory_transcripts_tool` - List all transcripts
- `inventory_communications_tool` - List all communications
- `get_case_metadata_tool` - Get case information

**Research Tools** (`tools/research_tools.py`):
- `search_evidence_tool` - Hybrid search across all evidence
- `get_document_tool` - Retrieve full document
- `get_transcript_tool` - Retrieve full transcript
- `get_communication_tool` - Retrieve full communication
- `extract_entities_tool` - NER entity extraction
- `find_citations_tool` - Legal citation extraction

**Graph Tools** (`tools/graph_tools.py`):
- `create_entity_tool` - Add entity to knowledge graph
- `create_event_tool` - Add event to knowledge graph
- `create_relationship_tool` - Add relationship between entities
- `get_entity_with_relationships_tool` - Get entity and its relationships
- `find_connected_entities_tool` - Graph traversal
- `find_shortest_path_tool` - Path finding between entities
- `get_timeline_tool` - Chronological event timeline

### Graph Structure (`graphs/research_graph.py`)

The workflow graph uses conditional routing and parallel execution:

```
discovery → planner → [document_analyst]
                   → [transcript_analyst]  → correlator → synthesis
                   → [communications_analyst]
```

**Conditional Routing**: Only runs analyst agents if corresponding evidence exists.

**Parallel Execution**: Multiple analysts can run concurrently during the ANALYSIS phase.

### Checkpointing (`compile_graph.py`)

Support for long-running workflows with state persistence:

```python
from app.infrastructure.ai.langgraph import compile_research_graph

# Compile with production PostgreSQL checkpointing
graph = compile_research_graph(use_production_checkpointer=True)

# Execute with thread ID for checkpointing
config = {"configurable": {"thread_id": "research-run-123"}}
result = await graph.ainvoke(state, config)

# Later, resume from checkpoint
resumed = await graph.ainvoke(None, config)
```

**Checkpointer Options:**
- **Development**: In-memory SQLite (fast, ephemeral)
- **Production**: PostgreSQL (persistent, queryable)

## Usage Examples

### Basic Execution

```python
from app.infrastructure.ai.langgraph import (
    compile_research_graph,
    create_initial_state,
)

# Compile graph
graph = compile_research_graph(use_production_checkpointer=True)

# Create initial state
state = create_initial_state(
    research_run_id="run-123",
    case_id="case-456",
    query="Analyze breach of contract evidence",
)

# Execute workflow
config = {"configurable": {"thread_id": "run-123"}}
final_state = await graph.ainvoke(state, config)

# Access results
print(final_state["phase"])  # "COMPLETED"
print(final_state["executive_summary"])
print(len(final_state["document_findings"]))
```

### High-Level Execution Helper

```python
from app.infrastructure.ai.langgraph import execute_research_workflow

# Execute complete workflow in one call
result = await execute_research_workflow(
    case_id="case-123",
    research_run_id="run-456",
    query="Analyze contract breach evidence",
    use_checkpointing=True,
)

print(result["status"])  # "COMPLETED"
```

### Resume from Checkpoint

```python
from app.infrastructure.ai.langgraph import resume_research_workflow

# Resume a paused or failed workflow
result = await resume_research_workflow(research_run_id="run-456")
```

### Checkpoint Management

```python
from app.infrastructure.ai.langgraph import (
    get_checkpointer,
    get_checkpoint_state,
    list_checkpoints,
    delete_checkpoint,
)

checkpointer = get_checkpointer(use_production=True)

# Get latest checkpoint
state = await get_checkpoint_state(checkpointer, thread_id="run-123")

# List all checkpoints for a thread
checkpoints = await list_checkpoints(checkpointer, thread_id="run-123")

# Delete checkpoints
await delete_checkpoint(checkpointer, thread_id="run-123")
```

### Graph Introspection

```python
from app.infrastructure.ai.langgraph import get_graph_structure, print_graph_structure

# Get structure as dict
structure = get_graph_structure()
print(structure["nodes"])
print(structure["edges"])

# Print human-readable structure
print_graph_structure()
```

## LLM Integration

### LangChain-Compatible Client

```python
from app.infrastructure.ai.langgraph import get_ollama_llm

# Get LangChain ChatOllama instance
llm = get_ollama_llm(
    model="llama3.1:70b",
    temperature=0.1,
    max_tokens=4096,
)

# Use with LangChain agents/chains
from langchain.agents import create_react_agent
agent = create_react_agent(llm, tools, prompt)
```

### Flexible Client

```python
from app.infrastructure.ai.langgraph import get_langgraph_client

# Get client with both LangChain and direct API access
client = get_langgraph_client("llama3.1:70b")

# Use with LangChain
agent = create_react_agent(client.langchain, tools, prompt)

# Or use direct API
response = await client.generate("Summarize this document")
```

### Model Testing

```python
from app.infrastructure.ai.langgraph import (
    test_model_connection,
    ensure_models_ready,
)

# Test if a model works
is_working = await test_model_connection("llama3.1:70b")

# Ensure multiple models are available
results = await ensure_models_ready(["llama3.1:70b", "llama3.1:7b"])
```

## State Structure

### Complete State Schema

```python
ResearchState = {
    # Request context
    "research_run_id": str,
    "case_id": str,
    "query": Optional[str],
    "defense_theory": Optional[str],

    # Evidence inventory
    "case_map": Dict[str, Any],
    "document_inventory": List[Dict],
    "transcript_inventory": List[Dict],
    "communication_inventory": List[Dict],

    # Planning
    "research_plan": Optional[Dict],

    # Analysis findings
    "document_findings": List[Dict],
    "transcript_findings": List[Dict],
    "communication_findings": List[Dict],

    # Knowledge graph
    "entities": List[Dict],
    "events": List[Dict],
    "relationships": List[Dict],
    "timeline": Optional[Dict],

    # Correlation
    "event_chains": List[Dict],
    "contradictions": List[Dict],
    "gaps": List[str],

    # Synthesis
    "dossier_sections": List[Dict],
    "executive_summary": Optional[str],
    "citations_appendix": List[Dict],

    # Metadata
    "phase": str,  # DISCOVERY, PLANNING, ANALYSIS, CORRELATION, SYNTHESIS, COMPLETED
    "status": str,  # RUNNING, PAUSED, COMPLETED, FAILED, AWAITING_HUMAN
    "current_agent": Optional[str],
    "progress_pct": float,
    "errors": List[str],
    "started_at": str,
    "updated_at": str,
}
```

## Design Principles

1. **Hexagonal Architecture**: All tools use repository interfaces - no direct database access
2. **Type Safety**: Comprehensive TypedDict definitions and type hints throughout
3. **Reducers**: LangGraph reducer pattern for append-only state updates
4. **Checkpointing**: Full support for pause/resume via PostgreSQL or SQLite
5. **Conditional Routing**: Dynamic workflow based on available evidence
6. **Parallel Execution**: Multiple analysts can run concurrently
7. **Error Handling**: Comprehensive error tracking in state
8. **Logging**: Detailed logging at each node for debugging

## Development Workflow

### Adding a New Agent

1. Create agent configuration in `agent_config.py`
2. Add node implementation in `graphs/research_graph.py`
3. Update graph structure to include new node
4. Add any new tools needed in `tools/`

### Adding a New Tool

1. Create tool implementation in appropriate file (`tools/inventory_tools.py`, etc.)
2. Define LangChain Tool instance
3. Add to `tools/__init__.py` exports
4. Update `ALL_TOOLS` registry
5. Add tool name to agent configs that should use it

### Testing

```python
# Test individual agents
from app.infrastructure.ai.langgraph.graphs.research_graph import discovery_node

state = create_initial_state(research_run_id="test", case_id="test")
result = await discovery_node(state)

# Test graph structure
from app.infrastructure.ai.langgraph import print_graph_structure
print_graph_structure()

# Test state validation
from app.infrastructure.ai.langgraph import validate_state
errors = validate_state(state)
```

## Production Considerations

1. **Checkpointing**: Always use PostgreSQL checkpointer in production
2. **Timeouts**: Configure appropriate timeouts in agent configs
3. **Monitoring**: Log state summaries at each phase transition
4. **Error Recovery**: Use checkpoint resume for failed workflows
5. **Resource Limits**: Configure max_iterations and timeouts per agent
6. **Model Selection**: Use larger models for complex agents (synthesis)
7. **Concurrency**: Limit parallel analyst execution based on resources

## Future Enhancements

- [ ] Implement actual LLM agent execution (currently placeholder)
- [ ] Add human-in-the-loop interrupt points
- [ ] Implement streaming for long-running operations
- [ ] Add progress callbacks for UI updates
- [ ] Support for multi-turn agent interactions
- [ ] Advanced graph visualization
- [ ] Metrics and performance tracking
- [ ] Configurable retry logic
- [ ] Support for agent sub-graphs
- [ ] Integration with Temporal workflows
