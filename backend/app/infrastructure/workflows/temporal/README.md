# Temporal Deep Research Workflows

This package implements a comprehensive Temporal-based orchestration system for AI-powered deep research analysis of legal cases. Research workflows can take 30 minutes to 4 hours depending on case complexity.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Starter    │  │   Monitor    │  │   Client     │      │
│  │  - Start     │  │  - Status    │  │  - Connect   │      │
│  │  - Cancel    │  │  - Progress  │  │  - Health    │      │
│  │  - Pause     │  │  - Queries   │  │              │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    Temporal Server                           │
│                  (Orchestration Engine)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              DeepResearchWorkflow                     │  │
│  │  Phase 1: Discovery (Case Cartography)               │  │
│  │  Phase 2: Planning                                    │  │
│  │  Phase 3: Parallel Analysis (Docs, Trans, Comms)     │  │
│  │  Phase 4: Correlation (Knowledge Graph)              │  │
│  │  Phase 5: Synthesis (Dossier Generation)             │  │
│  │  Phase 6: Report Generation (DOCX, PDF)              │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Temporal Worker                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Evidence    │  │    Search    │  │   Report     │      │
│  │  Processing  │  │  Activities  │  │  Generation  │      │
│  │  Activities  │  │              │  │  Activities  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         ▼                  ▼                  ▼              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         LangGraph Agents & Haystack Pipelines        │  │
│  │  - Discovery Agent  - Document Analyst               │  │
│  │  - Planner Agent    - Transcript Analyst             │  │
│  │  - Correlator       - Communication Analyst          │  │
│  │  - Synthesizer      - Hybrid Search Pipelines        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│              Infrastructure & Data Stores                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │PostgreSQL│  │  Neo4j   │  │OpenSearch│  │  MinIO   │   │
│  │(Research │  │(Knowledge│  │ (Hybrid  │  │(Reports) │   │
│  │  Runs)   │  │  Graph)  │  │  Search) │  │          │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
temporal/
├── __init__.py                     # Public API exports
├── README.md                       # This file
├── models.py                       # Pydantic data models for all phases
├── client.py                       # Temporal client (singleton)
├── worker.py                       # Temporal worker (run as separate process)
├── starter.py                      # Workflow starter utilities for FastAPI
├── monitor.py                      # Status monitoring and queries
├── activities/
│   ├── __init__.py
│   ├── evidence_processing.py     # Discovery, planning activities
│   ├── search.py                  # Document, transcript, comm analysis
│   ├── correlation.py             # Cross-evidence correlation
│   └── report_generation.py       # Synthesis, file generation
└── workflows/
    ├── __init__.py
    └── deep_research_workflow.py  # Main orchestration workflow
```

## Workflow Phases

### Phase 0: Initialization
- **Activity**: `initialize_research_run`
- **Duration**: < 1 minute
- **Purpose**: Create research run record in PostgreSQL

### Phase 1: Discovery (Case Cartography)
- **Activity**: `run_discovery_phase`
- **Duration**: 5-30 minutes
- **Purpose**: Inventory all evidence, generate case map
- **Invokes**: LangGraph Discovery Agent

### Phase 2: Planning
- **Activity**: `run_planning_phase`
- **Duration**: 5-20 minutes
- **Purpose**: Generate search strategies for each evidence type
- **Invokes**: LangGraph Planner Agent

### Phase 3: Parallel Analysis
- **Activities**: `run_document_analysis`, `run_transcript_analysis`, `run_communication_analysis`
- **Duration**: 30-120 minutes (runs in parallel)
- **Purpose**: Extract findings from each evidence type using Haystack hybrid search
- **Invokes**: LangGraph Analyst Agents (Document, Transcript, Communication)

### Phase 4: Correlation
- **Activity**: `run_correlation_phase`
- **Duration**: 10-40 minutes
- **Purpose**: Build knowledge graph, detect contradictions, create timeline
- **Invokes**: LangGraph Correlator Agent
- **Stores**: Knowledge graph in Neo4j

### Phase 5: Synthesis
- **Activity**: `run_synthesis_phase`
- **Duration**: 10-20 minutes
- **Purpose**: Generate final dossier with executive summary, sections, recommendations
- **Invokes**: LangGraph Synthesis Agent

### Phase 6: Report Generation
- **Activity**: `generate_report_files`
- **Duration**: 5-10 minutes
- **Purpose**: Render dossier to DOCX and PDF, upload to MinIO

## Usage

### Starting a Workflow from FastAPI

```python
from uuid import UUID
from app.infrastructure.workflows.temporal.starter import start_deep_research

# Start a research workflow
workflow_id, research_run_id = await start_deep_research(
    case_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
    query="Identify timeline of communications regarding contract negotiation",
    defense_theory="Defendant was not involved in decision-making process",
)

print(f"Started workflow: {workflow_id}")
print(f"Research run ID: {research_run_id}")
```

### Monitoring Progress

```python
from app.infrastructure.workflows.temporal.monitor import (
    get_workflow_status,
    get_detailed_workflow_info,
)

# Get current status
status = await get_workflow_status(workflow_id)
print(f"Phase: {status['phase']}")
print(f"Progress: {status['progress_pct']}%")
print(f"Findings: {status['findings_count']}")

# Get detailed info
info = await get_detailed_workflow_info(workflow_id)
print(f"Execution state: {info['execution_state']}")
print(f"Start time: {info['start_time']}")
```

### Pause/Resume/Cancel

```python
from app.infrastructure.workflows.temporal.starter import (
    pause_workflow,
    resume_workflow,
    cancel_workflow,
)

# Pause workflow (will pause at next checkpoint)
await pause_workflow(workflow_id)

# Resume workflow
await resume_workflow(workflow_id)

# Cancel workflow
await cancel_workflow(workflow_id, reason="User requested cancellation")
```

### Running the Worker

The worker must run as a separate process to execute workflows and activities:

```bash
# Direct Python
python -m app.infrastructure.workflows.temporal.worker

# Or with mise (recommended)
mise run worker:temporal
```

The worker will:
- Connect to Temporal server
- Register workflows and activities
- Process tasks from the `legalease-research` queue
- Handle retries and failures automatically
- Log progress and errors

## Configuration

Settings are defined in `/home/Allie/develop/legalease/backend/app/core/config.py`:

```python
# Temporal settings
TEMPORAL_HOST: str = "localhost:7233"
TEMPORAL_NAMESPACE: str = "legalease"
TEMPORAL_TASK_QUEUE: str = "legalease-research"
TEMPORAL_WORKFLOW_EXECUTION_TIMEOUT: int = 14400  # 4 hours

# Research settings
RESEARCH_MAX_CONCURRENT_AGENTS: int = 4
RESEARCH_DEFAULT_TIMEOUT: int = 14400
```

## Error Handling

### Activity Retries
All activities have automatic retry policies:
- **Initial interval**: 1 second
- **Maximum interval**: 5 minutes
- **Maximum attempts**: 3
- **Backoff coefficient**: 2.0

### Workflow Failures
If an activity fails after all retries, the workflow will fail and return a `ResearchWorkflowOutput` with:
- `status: "FAILED"`
- `error: "Workflow failed: <error message>"`

### Recovery
Failed workflows can be inspected in the Temporal UI at `http://localhost:8233`

## Observability

### Temporal UI
- **URL**: http://localhost:8233
- **Features**:
  - View workflow execution history
  - See activity timeline
  - Inspect workflow state
  - Query workflow status
  - Retry failed workflows

### Logging
All components log extensively:
- Worker logs: Activity execution, errors, retries
- Workflow logs: Phase transitions, progress
- Activity logs: Detailed operation logs

### Heartbeats
Long-running activities send heartbeats every few seconds to indicate progress:
```python
activity.heartbeat("Processing documents: 50/100")
```

## Best Practices

### 1. Idempotent Activities
All activities are designed to be idempotent (safe to retry):
- Check if work already done before executing
- Use unique IDs for database records
- Handle partial state gracefully

### 2. Heartbeats for Long Operations
Activities that run > 30 seconds should send heartbeats:
```python
for i, item in enumerate(items):
    process_item(item)
    if i % 10 == 0:
        activity.heartbeat(f"Processed {i}/{len(items)} items")
```

### 3. Workflow State Management
- Store state in workflow instance variables
- Never modify external state directly from workflow code
- Use activities for all side effects (database, API calls, etc.)

### 4. Query Pattern
Use queries for real-time status, not for business logic:
```python
# Good: Query current status
@workflow.query
def get_status(self) -> Dict:
    return {"phase": self.current_phase, "progress": self.progress_pct}

# Bad: Don't use queries to trigger actions
@workflow.query
def cancel_now(self):  # NO! Use signals instead
    self.is_cancelled = True
```

## Testing

### Unit Testing Activities
```python
import pytest
from app.infrastructure.workflows.temporal.activities.search import run_document_analysis

@pytest.mark.asyncio
async def test_document_analysis():
    planning = PlanningResult(...)
    result = await run_document_analysis(planning)
    assert len(result.findings) > 0
```

### Integration Testing Workflows
Use Temporal's test framework:
```python
from temporalio.testing import WorkflowEnvironment
from app.infrastructure.workflows.temporal.workflows import DeepResearchWorkflow

async def test_workflow():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        # Test workflow execution
        result = await env.client.execute_workflow(
            DeepResearchWorkflow.run,
            input,
            id="test-workflow",
            task_queue="test-queue",
        )
        assert result.status == "COMPLETED"
```

## Troubleshooting

### Worker Not Processing Tasks
1. Check worker is running: `ps aux | grep temporal.worker`
2. Check Temporal server is accessible: `curl http://localhost:7233`
3. Check worker logs for errors
4. Verify task queue name matches configuration

### Workflow Stuck
1. Check Temporal UI for activity failures
2. Look for heartbeat timeouts (activity might be hung)
3. Check database connections in activities
4. Verify LangGraph agents are responding

### Activities Timing Out
1. Increase `start_to_close_timeout` for activity
2. Add or increase `heartbeat_timeout`
3. Optimize activity code
4. Break activity into smaller sub-activities

## Future Enhancements

- [ ] Add LangGraph agent implementations
- [ ] Implement Haystack hybrid search pipelines
- [ ] Add Neo4j knowledge graph operations
- [ ] Implement DOCX/PDF report generation
- [ ] Add progress checkpointing for resumability
- [ ] Implement activity-level caching
- [ ] Add metrics collection (Prometheus)
- [ ] Create workflow replay testing suite
