# Application Layer

The **Application Layer** orchestrates business workflows and use cases by coordinating between the domain layer and infrastructure layer. It implements the CQRS (Command Query Responsibility Segregation) pattern.

## Architecture

```
Application Layer
├── Commands (Write Operations)
│   ├── StartResearchCommand
│   ├── ProcessEvidenceCommand
│   ├── GenerateReportCommand
│   └── Workflow Control (Pause/Resume/Cancel)
│
├── Queries (Read Operations)
│   ├── GetResearchRunQuery
│   ├── ListResearchRunsQuery
│   ├── GetFindingsQuery
│   └── SearchEvidenceQuery
│
└── Orchestrators
    ├── ResearchOrchestrator
    ├── EvidenceOrchestrator
    └── ReportOrchestrator
```

## CQRS Pattern

The application layer separates:
- **Commands** - Modify state (write operations)
- **Queries** - Retrieve data (read operations)

### Why CQRS?

1. **Separation of Concerns** - Different models for reading and writing
2. **Scalability** - Read and write paths can be optimized independently
3. **Flexibility** - Different data sources for queries (e.g., read replicas, search indexes)
4. **Clarity** - Clear distinction between operations that change state vs. retrieve data

## Commands

Commands represent user intent to modify system state. They:
- Are immutable dataclasses
- Return structured results (not exceptions for business failures)
- Use dependency injection
- Are orchestrated by handlers

**See [commands/README.md](./commands/README.md) for detailed documentation.**

### Available Commands

| Command | Purpose |
|---------|---------|
| `StartResearchCommand` | Initiate a new deep research workflow |
| `ProcessEvidenceCommand` | Process and index evidence |
| `GenerateReportCommand` | Generate dossier reports (DOCX/PDF) |
| `PauseResearchCommand` | Pause a running research workflow |
| `ResumeResearchCommand` | Resume a paused workflow |
| `CancelResearchCommand` | Cancel a running workflow |

## Queries

Queries retrieve data without modifying state. They:
- Return DTOs (Data Transfer Objects)
- Can use optimized read paths (materialized views, search indexes)
- Are cacheable
- Don't have side effects

**See [queries/README.md](./queries/README.md) for detailed documentation.**

### Available Queries

| Query | Purpose |
|-------|---------|
| `GetResearchRunQuery` | Get a single research run by ID |
| `ListResearchRunsQuery` | List research runs with filtering/pagination |
| `GetFindingsQuery` | Get findings for a research run |
| `SearchEvidenceQuery` | Search across evidence using vector/text search |

## Orchestrators

Orchestrators coordinate complex multi-step workflows that don't fit into a single command or query. They:
- Coordinate multiple domain operations
- Handle transaction boundaries
- Manage workflow state
- Integrate with Temporal for long-running processes

**See [orchestrators/README.md](./orchestrators/README.md) for detailed documentation.**

## Dependency Injection

The application layer uses FastAPI's dependency injection system:

```python
from fastapi import Depends
from app.application.commands import get_start_research_handler

@app.post("/research/start")
async def start_research(
    handler=Depends(get_start_research_handler)
):
    command = StartResearchCommand(...)
    result = await handler.handle(command)
    return result
```

### Benefits

1. **Testability** - Easy to mock dependencies
2. **Flexibility** - Swap implementations without changing code
3. **Clarity** - Dependencies are explicit in function signatures
4. **Lifecycle Management** - FastAPI manages object lifecycle

## Error Handling

All commands and queries return structured results:

```python
@dataclass
class CommandResult:
    success: bool
    message: str
    error: Optional[str] = None
```

**Never raise exceptions for business logic failures** - return error results instead.

### Exception vs. Result

| Use Exception | Use Result |
|---------------|------------|
| Infrastructure failures (DB down, network error) | Business rule violations |
| Programming errors (type errors, null reference) | Validation failures |
| Unrecoverable errors | Expected failure conditions |

## Testing

### Unit Testing Commands

```python
@pytest.mark.asyncio
async def test_start_research_command():
    # Arrange
    mock_repo = AsyncMock()
    mock_temporal = AsyncMock()
    handler = StartResearchCommandHandler(mock_repo, mock_temporal)

    # Act
    result = await handler.handle(
        StartResearchCommand(case_id=uuid4())
    )

    # Assert
    assert result.success
    mock_repo.save.assert_called_once()
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_research_workflow_integration(db, temporal_client):
    # Use real dependencies
    handler = StartResearchCommandHandler(
        research_repo=SQLAlchemyResearchRunRepository(db),
        temporal_client=temporal_client,
    )

    result = await handler.handle(
        StartResearchCommand(case_id=case_id)
    )

    assert result.success
    # Verify database state
    research_run = await db.get(ResearchRunModel, result.research_run_id)
    assert research_run.status == "RUNNING"
```

## Design Principles

### 1. Separation of Concerns
- Application layer coordinates, doesn't implement business logic
- Business logic lives in domain layer
- Infrastructure details in infrastructure layer

### 2. Dependency Inversion
- Application layer depends on domain abstractions (repositories, interfaces)
- Never depends on infrastructure implementations directly

### 3. Single Responsibility
- Each command/query handler has one clear purpose
- Orchestrators handle multi-step workflows

### 4. Immutability
- Commands are immutable once created
- Results are immutable

### 5. Explicit Dependencies
- All dependencies injected through constructor
- No hidden dependencies or service locators

## Directory Structure

```
application/
├── commands/                   # Write operations (CQRS commands)
│   ├── __init__.py
│   ├── command_bus.py          # Central command dispatcher
│   ├── dependencies.py         # Dependency injection setup
│   ├── start_research.py       # Start research command
│   ├── process_evidence.py     # Process evidence command
│   ├── generate_report.py      # Generate report command
│   ├── pause_research.py       # Pause research command
│   ├── resume_research.py      # Resume research command
│   ├── cancel_research.py      # Cancel research command
│   └── README.md               # Commands documentation
│
├── queries/                    # Read operations (CQRS queries)
│   ├── __init__.py
│   ├── query_bus.py            # Central query dispatcher
│   ├── get_research_run.py     # Get research run query
│   ├── list_research_runs.py   # List research runs query
│   ├── get_findings.py         # Get findings query
│   ├── search_evidence.py      # Search evidence query
│   └── README.md               # Queries documentation
│
├── orchestrators/              # Complex multi-step workflows
│   ├── __init__.py
│   ├── research_orchestrator.py    # Research workflow coordination
│   ├── evidence_orchestrator.py    # Evidence processing coordination
│   └── README.md                   # Orchestrators documentation
│
├── __init__.py                 # Application layer exports
└── README.md                   # This file
```

## Usage Examples

### Starting Research via API

```python
from fastapi import APIRouter, Depends, HTTPException
from app.application.commands import (
    StartResearchCommand,
    get_start_research_handler,
)

router = APIRouter()

@router.post("/research/start")
async def start_research(
    case_id: UUID,
    query: Optional[str] = None,
    handler=Depends(get_start_research_handler),
):
    command = StartResearchCommand(
        case_id=case_id,
        query=query,
    )

    result = await handler.handle(command)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return {
        "research_run_id": result.research_run_id,
        "workflow_id": result.workflow_id,
        "message": result.message,
    }
```

### Querying Research Results

```python
from app.application.queries import (
    GetResearchRunQuery,
    get_research_run_handler,
)

@router.get("/research/{research_run_id}")
async def get_research_run(
    research_run_id: UUID,
    handler=Depends(get_research_run_handler),
):
    query = GetResearchRunQuery(research_run_id=research_run_id)
    result = await handler.handle(query)

    if not result.found:
        raise HTTPException(status_code=404, detail="Research run not found")

    return result.research_run
```

## Related Documentation

- [Domain Layer](../domain/README.md) - Business entities and rules
- [Infrastructure Layer](../infrastructure/README.md) - Technical implementations
- [API Layer](../api/README.md) - REST API endpoints
- [Commands Documentation](./commands/README.md) - Detailed command reference
- [Queries Documentation](./queries/README.md) - Detailed query reference
