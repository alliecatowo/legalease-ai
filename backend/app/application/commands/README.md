# Application Commands

This directory contains all **CQRS write operations (commands)** for the LegalEase application. Commands modify state and trigger workflows, following the Command pattern with dependency injection.

## Architecture

Each command follows a consistent structure:

1. **Command Class** - Immutable dataclass representing the intent
2. **Result Class** - Structured response with success/error information
3. **Handler Class** - Contains business logic and orchestration
4. **Dependencies** - Injected repositories and services

## Available Commands

### 1. StartResearchCommand
**Purpose**: Initiates a new deep research workflow

**Handler**: `StartResearchCommandHandler`

**Dependencies**:
- `ResearchRunRepository` - Persists research run entities
- `TemporalClient` - Starts Temporal workflows

**Process**:
1. Creates ResearchRun entity with PENDING status
2. Persists to PostgreSQL
3. Starts Temporal workflow
4. Updates ResearchRun with workflow_id and RUNNING status

**Usage**:
```python
from app.application.commands import StartResearchCommand, get_start_research_handler

command = StartResearchCommand(
    case_id=uuid4(),
    query="Analyze communication timeline",
    config={"max_findings": 50}
)

handler = await get_start_research_handler(db, temporal_client)
result = await handler.handle(command)

if result.success:
    print(f"Research started: {result.workflow_id}")
```

---

### 2. ProcessEvidenceCommand
**Purpose**: Processes and indexes new evidence (documents, transcripts, communications)

**Handler**: `ProcessEvidenceCommandHandler`

**Dependencies**:
- `IndexingPipelineFactory` - Creates Haystack indexing pipelines
- `QdrantDocumentRepository` - Vector storage
- `OpenSearchDocumentRepository` - Text search

**Process**:
1. Validates evidence file/data exists
2. Selects appropriate pipeline based on evidence type
3. Runs indexing pipeline (writes to Qdrant + OpenSearch)
4. Returns chunk count

**Usage**:
```python
from app.application.commands import ProcessEvidenceCommand
from app.shared.types.enums import EvidenceType

command = ProcessEvidenceCommand(
    evidence_id=uuid4(),
    evidence_type=EvidenceType.DOCUMENT,
    case_id=uuid4(),
    file_path="/path/to/document.pdf"
)

result = await handler.handle(command)
print(f"Indexed {result.chunks_indexed} chunks")
```

---

### 3. GenerateReportCommand
**Purpose**: Generates dossier files (DOCX, PDF) from completed research

**Handler**: `GenerateReportCommandHandler`

**Dependencies**:
- `DossierRepository` - Retrieves dossier data
- `ResearchRunRepository` - Validates research completion
- `MinIOClient` - Uploads generated files

**Process**:
1. Retrieves research run and dossier
2. Validates research is completed
3. Renders DOCX using template
4. Converts to PDF if requested
5. Uploads to MinIO
6. Updates dossier with file paths

**Usage**:
```python
from app.application.commands import GenerateReportCommand

command = GenerateReportCommand(
    research_run_id=uuid4(),
    format="BOTH",  # "DOCX", "PDF", or "BOTH"
    include_citations=True
)

result = await handler.handle(command)
print(f"Generated files: {result.file_paths}")
```

---

### 4. PauseResearchCommand
**Purpose**: Pauses a running research workflow

**Handler**: `PauseResearchCommandHandler`

**Process**:
1. Gets workflow handle from Temporal
2. Sends pause signal
3. Updates ResearchRun status to PAUSED

**Usage**:
```python
command = PauseResearchCommand(workflow_id="research-{uuid}")
result = await handler.handle(command)
```

---

### 5. ResumeResearchCommand
**Purpose**: Resumes a paused research workflow

**Handler**: `ResumeResearchCommandHandler`

**Process**:
1. Gets workflow handle from Temporal
2. Sends resume signal
3. Updates ResearchRun status to RUNNING

**Usage**:
```python
command = ResumeResearchCommand(workflow_id="research-{uuid}")
result = await handler.handle(command)
```

---

### 6. CancelResearchCommand
**Purpose**: Cancels a running research workflow

**Handler**: `CancelResearchCommandHandler`

**Process**:
1. Gets workflow handle from Temporal
2. Cancels the workflow
3. Updates ResearchRun status to CANCELLED

**Usage**:
```python
command = CancelResearchCommand(
    workflow_id="research-{uuid}",
    reason="User requested cancellation"
)
result = await handler.handle(command)
```

---

## Command Bus

The `CommandBus` provides centralized command dispatching with:
- Handler registration
- Dependency injection
- Logging and monitoring
- Error handling

### Basic Usage

```python
from app.application.commands import get_command_bus, StartResearchCommand

# Get singleton command bus
bus = get_command_bus()

# Register handlers (typically done at startup)
bus.register(StartResearchCommand, start_research_handler)

# Execute command
command = StartResearchCommand(case_id=uuid4())
result = await bus.execute(command)
```

### FastAPI Integration

In FastAPI endpoints, use dependency injection:

```python
from fastapi import APIRouter, Depends
from app.application.commands import (
    StartResearchCommand,
    get_start_research_handler,
)

router = APIRouter()

@router.post("/research/start")
async def start_research(
    case_id: UUID,
    handler=Depends(get_start_research_handler)
):
    command = StartResearchCommand(case_id=case_id)
    result = await handler.handle(command)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return result
```

---

## Dependency Injection

All command handlers use FastAPI's dependency injection system:

```python
from app.application.commands import get_start_research_handler

# In a FastAPI endpoint
@app.post("/research")
async def endpoint(handler=Depends(get_start_research_handler)):
    # Handler is automatically instantiated with all dependencies
    result = await handler.handle(command)
```

Available dependency functions:
- `get_start_research_handler()`
- `get_process_evidence_handler()`
- `get_generate_report_handler()`
- `get_pause_research_handler()`
- `get_resume_research_handler()`
- `get_cancel_research_handler()`

---

## Error Handling

All command results follow a consistent pattern:

```python
@dataclass
class CommandResult:
    success: bool
    message: str
    error: Optional[str] = None
```

Always check `result.success` before proceeding:

```python
result = await handler.handle(command)

if result.success:
    logger.info(result.message)
    # Proceed with success logic
else:
    logger.error(f"Command failed: {result.error}")
    # Handle failure
```

---

## Testing

### Unit Testing Command Handlers

```python
import pytest
from unittest.mock import AsyncMock
from app.application.commands import StartResearchCommandHandler, StartResearchCommand

@pytest.mark.asyncio
async def test_start_research_handler():
    # Mock dependencies
    mock_repo = AsyncMock()
    mock_temporal = AsyncMock()

    # Create handler
    handler = StartResearchCommandHandler(mock_repo, mock_temporal)

    # Execute command
    command = StartResearchCommand(case_id=uuid4())
    result = await handler.handle(command)

    # Assert
    assert result.success
    assert result.workflow_id is not None
    mock_repo.save.assert_called_once()
```

### Integration Testing with CommandBus

```python
@pytest.mark.asyncio
async def test_command_bus_execution():
    from app.application.commands import get_command_bus, reset_command_bus

    # Reset for clean state
    reset_command_bus()

    bus = get_command_bus()
    bus.register(StartResearchCommand, handler)

    command = StartResearchCommand(case_id=uuid4())
    result = await bus.execute(command)

    assert result.success
```

---

## Design Principles

1. **Immutable Commands**: Commands are immutable dataclasses
2. **Single Responsibility**: Each handler has one clear purpose
3. **Dependency Injection**: All dependencies are injected, not created
4. **Structured Results**: Results are structured dataclasses, not exceptions for business logic failures
5. **Comprehensive Logging**: All commands log execution details
6. **Type Safety**: Full type hints throughout

---

## File Structure

```
commands/
├── __init__.py                 # Module exports
├── command_bus.py              # Command bus implementation
├── dependencies.py             # FastAPI dependency injection
├── start_research.py           # Start research command
├── process_evidence.py         # Process evidence command
├── generate_report.py          # Generate report command
├── pause_research.py           # Pause research command
├── resume_research.py          # Resume research command
├── cancel_research.py          # Cancel research command
└── README.md                   # This file
```

---

## Related Documentation

- [Domain Layer](../../domain/README.md) - Domain entities and repositories
- [Infrastructure Layer](../../infrastructure/README.md) - Infrastructure implementations
- [Temporal Workflows](../../infrastructure/workflows/temporal/README.md) - Workflow orchestration
- [Haystack Pipelines](../../infrastructure/ai/haystack/README.md) - Indexing pipelines
