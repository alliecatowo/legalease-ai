# LangGraph Research Workflow Structure

## Visual Graph Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         RESEARCH WORKFLOW GRAPH                          │
└─────────────────────────────────────────────────────────────────────────┘

                            START
                              │
                              ▼
                    ┌──────────────────┐
                    │   DISCOVERY      │  Phase: DISCOVERY
                    │   Agent          │  Progress: 10%
                    │                  │  Output: Inventories + Case Map
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   PLANNER        │  Phase: PLANNING
                    │   Agent          │  Progress: 20%
                    │                  │  Output: Research Plan
                    └────────┬─────────┘
                             │
                             │ (conditional routing)
                             │
            ┌────────────────┼────────────────┐
            │                │                │
            ▼                ▼                ▼
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │  DOCUMENT    │  │  TRANSCRIPT  │  │  COMMS       │  Phase: ANALYSIS
  │  ANALYST     │  │  ANALYST     │  │  ANALYST     │  Progress: 40-60%
  │              │  │              │  │              │  Output: Findings
  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    + Entities
         │                 │                 │            + Events
         └────────────────┬┴─────────────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │   CORRELATOR     │  Phase: CORRELATION
                 │   Agent          │  Progress: 75%
                 │                  │  Output: Timeline
                 └────────┬─────────┘    + Event Chains
                          │              + Contradictions
                          │              + Gaps
                          ▼
                 ┌──────────────────┐
                 │   SYNTHESIS      │  Phase: SYNTHESIS
                 │   Agent          │  Progress: 90-100%
                 │                  │  Output: Dossier
                 └────────┬─────────┘    + Summary
                          │              + Citations
                          ▼
                         END
```

## Node Details

### 1. Discovery Node
**Function**: `discovery_node(state: ResearchState)`

**Inputs** (from state):
- `case_id` - Case to inventory
- `research_run_id` - Current run ID

**Tools Used**:
- `inventory_documents_tool`
- `inventory_transcripts_tool`
- `inventory_communications_tool`
- `get_case_metadata_tool`

**Outputs** (state updates):
- `case_map` - High-level case structure
- `document_inventory` - List of document metadata
- `transcript_inventory` - List of transcript metadata
- `communication_inventory` - List of communication metadata
- `phase` = "DISCOVERY"
- `progress_pct` = 10.0

**Agent Config**: `DISCOVERY_AGENT_CONFIG`
- Model: llama3.1:7b (configurable)
- Temperature: 0.1 (low for factual work)
- Timeout: 1800s (30 min)

---

### 2. Planner Node
**Function**: `planner_node(state: ResearchState)`

**Inputs** (from state):
- `case_map` - Case structure
- `document_inventory`, `transcript_inventory`, `communication_inventory`
- `query` - Optional user query
- `defense_theory` - Optional defense theory

**Tools Used**:
- `analyze_case_inventory` (placeholder)
- `generate_search_queries` (placeholder)
- `identify_key_entities` (placeholder)

**Outputs** (state updates):
- `research_plan` - Structured plan with:
  - `workstreams` - Research areas
  - `search_queries` - Targeted queries
  - `search_heuristics` - Analysis guidance
  - `priorities` - Critical vs. important
- `phase` = "PLANNING"
- `progress_pct` = 20.0

**Agent Config**: `PLANNER_AGENT_CONFIG`
- Model: llama3.1:7b
- Temperature: 0.3 (slightly higher for planning)
- Timeout: 1200s (20 min)

---

### 3. Document Analyst Node
**Function**: `document_analyst_node(state: ResearchState)`

**Conditional**: Only runs if `document_inventory` is not empty

**Inputs** (from state):
- `research_plan` - Search queries and heuristics
- `document_inventory` - Documents to analyze
- `case_id` - For filtering

**Tools Used**:
- `search_evidence_tool` - Find relevant documents
- `get_document_tool` - Retrieve full text
- `extract_entities_tool` - NER extraction
- `find_citations_tool` - Legal citations
- `create_entity_tool` - Add to graph
- `create_event_tool` - Add events
- `create_relationship_tool` - Add relationships

**Outputs** (state updates):
- `document_findings[]` - List of findings with:
  - `finding` - Description
  - `source` - Document ID
  - `confidence` - 0.0-1.0
  - `citations` - Page references
  - `quotes` - Supporting quotes
- `entities[]` - Extracted entities
- `events[]` - Extracted events
- `relationships[]` - Entity relationships
- `phase` = "ANALYSIS"
- `progress_pct` = 40.0

**Agent Config**: `DOCUMENT_ANALYST_CONFIG`
- Model: llama3.1:7b
- Temperature: 0.1
- Timeout: 3600s (60 min)
- Max iterations: 50

---

### 4. Transcript Analyst Node
**Function**: `transcript_analyst_node(state: ResearchState)`

**Conditional**: Only runs if `transcript_inventory` is not empty

**Inputs** (from state):
- `research_plan`
- `transcript_inventory`
- `case_id`

**Tools Used**:
- Same as Document Analyst
- Plus `get_transcript_tool`

**Outputs** (state updates):
- `transcript_findings[]` - Testimonial findings with:
  - `finding`
  - `source` - Transcript ID
  - `speaker` - Who said it
  - `citation` - Page:line reference
  - `confidence`
  - `context` - Surrounding testimony
- `entities[]`, `events[]`, `relationships[]`
- `progress_pct` = 50.0

**Agent Config**: `TRANSCRIPT_ANALYST_CONFIG`
- Model: llama3.1:7b
- Temperature: 0.1
- Timeout: 3600s (60 min)
- Max iterations: 50

---

### 5. Communications Analyst Node
**Function**: `communications_analyst_node(state: ResearchState)`

**Conditional**: Only runs if `communication_inventory` is not empty

**Inputs** (from state):
- `research_plan`
- `communication_inventory`
- `case_id`

**Tools Used**:
- Same as Document Analyst
- Plus `get_communication_tool`
- Plus `analyze_communication_thread_tool` (placeholder)

**Outputs** (state updates):
- `communication_findings[]` - Communication findings with:
  - `finding`
  - `source` - Communication ID
  - `participants` - Who was involved
  - `timestamp` - When
  - `confidence`
  - `thread_context` - Related messages
- `entities[]`, `events[]`, `relationships[]`
- `progress_pct` = 60.0

**Agent Config**: `COMMUNICATIONS_ANALYST_CONFIG`
- Model: llama3.1:7b
- Temperature: 0.1
- Timeout: 3600s (60 min)
- Max iterations: 50

---

### 6. Correlator Node
**Function**: `correlator_node(state: ResearchState)`

**Inputs** (from state):
- `document_findings[]`
- `transcript_findings[]`
- `communication_findings[]`
- `entities[]` - All entities from analysts
- `events[]` - All events from analysts
- `relationships[]` - All relationships from analysts

**Tools Used**:
- `get_entity_with_relationships_tool`
- `find_connected_entities_tool`
- `find_shortest_path_tool`
- `get_timeline_tool`
- `merge_entities_tool` (placeholder)
- `create_event_chain_tool` (placeholder)

**Outputs** (state updates):
- `timeline` - Unified chronological timeline
- `event_chains[]` - Causal sequences
- `contradictions[]` - Conflicting evidence
- `gaps[]` - Missing information
- `entities[]` - Deduplicated and merged
- `phase` = "CORRELATION"
- `progress_pct` = 75.0

**Agent Config**: `CORRELATOR_AGENT_CONFIG`
- Model: llama3.1:7b
- Temperature: 0.2 (pattern recognition)
- Timeout: 2400s (40 min)
- Max iterations: 40

---

### 7. Synthesis Node
**Function**: `synthesis_node(state: ResearchState)`

**Inputs** (from state):
- All findings from all sources
- `timeline` - Chronological events
- `event_chains[]` - Narrative sequences
- `contradictions[]`
- `gaps[]`
- `entities[]`, `events[]`, `relationships[]`

**Tools Used**:
- `get_all_findings_tool` (placeholder)
- `get_knowledge_graph_tool` (placeholder)
- `format_citations_tool` (placeholder)
- `create_entity_diagram_tool` (placeholder)
- `create_timeline_visualization_tool` (placeholder)

**Outputs** (state updates):
- `executive_summary` - High-level overview
- `dossier_sections[]` - Structured report sections:
  - Executive Summary
  - Factual Background
  - Key Players
  - Critical Events
  - Documentary Evidence
  - Testimonial Evidence
  - Digital Evidence
  - Contradictions
  - Evidence Gaps
  - Legal Analysis
- `citations_appendix[]` - All citations
- `phase` = "SYNTHESIS" then "COMPLETED"
- `status` = "COMPLETED"
- `progress_pct` = 100.0

**Agent Config**: `SYNTHESIS_AGENT_CONFIG`
- Model: llama3.1:7b
- Temperature: 0.2
- Max tokens: 16384 (larger for synthesis)
- Timeout: 2400s (40 min)
- Max iterations: 30

**Optional**: Human-in-the-loop interrupt point (commented out)

---

## Routing Logic

### Conditional Routing Function
```python
def route_to_analysts(state: ResearchState) -> List[str]:
    agents = []

    if state.get("document_inventory"):
        agents.append("document_analyst")

    if state.get("transcript_inventory"):
        agents.append("transcript_analyst")

    if state.get("communication_inventory"):
        agents.append("communications_analyst")

    return agents
```

**Behavior**:
- If NO evidence: Skip analysis, go directly to correlation
- If ONLY documents: Run only document_analyst
- If ONLY transcripts: Run only transcript_analyst
- If ALL types: Run all three analysts in parallel

### Parallel Execution
The three analyst nodes can run concurrently:
- LangGraph handles parallel execution
- All converge to correlator node
- State updates are merged using reducers

---

## State Flow Example

### Initial State
```python
{
    "research_run_id": "run-123",
    "case_id": "case-456",
    "query": "Analyze contract breach",
    "phase": "DISCOVERY",
    "status": "RUNNING",
    "progress_pct": 0.0,
    # All other fields empty/None
}
```

### After Discovery
```python
{
    # ... previous fields ...
    "phase": "DISCOVERY",
    "progress_pct": 10.0,
    "case_map": {"case_number": "CV-2024-00123", ...},
    "document_inventory": [{"id": "doc-1", ...}],
    "transcript_inventory": [{"id": "trans-1", ...}],
    "communication_inventory": [{"id": "comm-1", ...}],
}
```

### After Analysis (Merged from 3 agents)
```python
{
    # ... previous fields ...
    "phase": "ANALYSIS",
    "progress_pct": 60.0,
    "document_findings": [{...}, {...}],      # From document_analyst
    "transcript_findings": [{...}],           # From transcript_analyst
    "communication_findings": [{...}, {...}], # From comms_analyst
    "entities": [{...}, {...}, {...}],        # Merged from all 3
    "events": [{...}, {...}],                 # Merged from all 3
    "relationships": [{...}],                 # Merged from all 3
}
```

### After Correlation
```python
{
    # ... previous fields ...
    "phase": "CORRELATION",
    "progress_pct": 75.0,
    "timeline": {"start": "2024-01-01", ...},
    "event_chains": [{"name": "Breach Sequence", ...}],
    "contradictions": [{"description": "Conflicting dates", ...}],
    "gaps": ["Missing Feb 2024 communications"],
}
```

### Final State (After Synthesis)
```python
{
    # ... all previous fields ...
    "phase": "COMPLETED",
    "status": "COMPLETED",
    "progress_pct": 100.0,
    "executive_summary": "...",
    "dossier_sections": [{...}, {...}, {...}],
    "citations_appendix": [{...}, {...}],
}
```

---

## Checkpointing

### Thread Configuration
```python
config = {
    "configurable": {
        "thread_id": "research-run-123"  # Same as research_run_id
    }
}
```

### Checkpoint Triggers
Checkpoints are created after each node execution:
1. After discovery → Can resume at planner
2. After planner → Can resume at analysis
3. After each analyst → Can resume remaining analysts
4. After correlator → Can resume at synthesis
5. After synthesis → Workflow complete

### Resume Behavior
```python
# Resume from last checkpoint
result = await graph.ainvoke(None, config)  # None = load from checkpoint
```

---

## Error Handling

### Node-Level Error Handling
Each node has try/except:
```python
try:
    # Agent execution
    updates = {...}
except Exception as e:
    return {
        "errors": [f"Node error: {str(e)}"],
        "current_agent": None,
    }
```

### Error Accumulation
Errors are accumulated in state (reducer pattern):
```python
"errors": [
    "Discovery error: Connection timeout",
    "Document analysis error: Model unavailable",
]
```

### Workflow Continues
Errors don't abort workflow - partial results preserved in state.

---

## Execution Time Estimates

**Fast Track** (minimal evidence):
- Discovery: 2-5 min
- Planning: 3-5 min
- Analysis: 5-15 min (parallel)
- Correlation: 5-10 min
- Synthesis: 10-15 min
- **Total**: ~30-50 min

**Full Analysis** (extensive evidence):
- Discovery: 10-20 min
- Planning: 10-15 min
- Analysis: 45-90 min (parallel)
- Correlation: 20-30 min
- Synthesis: 20-30 min
- **Total**: ~2-3 hours

**Maximum** (with timeouts):
- Discovery: 30 min max
- Planning: 20 min max
- Analysis: 60 min max each (can run parallel)
- Correlation: 40 min max
- Synthesis: 40 min max
- **Total**: ~4 hours max
