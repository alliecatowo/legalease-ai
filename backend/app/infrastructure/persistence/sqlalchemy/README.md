# SQLAlchemy Persistence Layer

This directory contains the SQLAlchemy-based persistence implementation for the Research and Knowledge Graph domains, following hexagonal architecture principles.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Domain Layer                            │
│  (Entities, Value Objects, Repository Interfaces)            │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ implements
                            │
┌─────────────────────────────────────────────────────────────┐
│              Infrastructure Persistence Layer                │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Models    │  │  Repositories │  │ Unit of Work │       │
│  │ (ORM)       │  │  (SQLAlchemy) │  │ (Transaction)│       │
│  └─────────────┘  └──────────────┘  └──────────────┘       │
│         ▲                  ▲                  ▲              │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                    Mappers (Bidirectional)                   │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. ORM Models (`models/`)

SQLAlchemy 2.0 declarative models that map domain entities to database tables.

**Research Models:**
- `ResearchRunModel` - Research session tracking
- `FindingModel` - Discovered insights
- `HypothesisModel` - Generated theories
- `DossierModel` - Final research documents

**Knowledge Graph Models:**
- `EntityModel` - People, organizations, locations
- `EventModel` - Temporal events
- `RelationshipModel` - Entity connections

### 2. Mappers (`mappers.py`)

Bidirectional conversion functions between ORM models and domain entities.

```python
# ORM → Domain
domain_entity = to_domain_research_run(model)

# Domain → ORM
orm_model = to_model_research_run(entity)
```

### 3. Repositories (`repositories/`)

Async repository implementations following domain interfaces.

**Research Repositories:**
- `SQLAlchemyResearchRunRepository`
- `SQLAlchemyFindingRepository`
- `SQLAlchemyHypothesisRepository`
- `SQLAlchemyDossierRepository`

**Knowledge Graph Repositories:**
- `SQLAlchemyEntityRepository`
- `SQLAlchemyEventRepository`
- `SQLAlchemyRelationshipRepository`
- `SQLAlchemyGraphRepository` (high-level graph operations)

### 4. Unit of Work (`unit_of_work.py`)

Transaction management coordinating multiple repository operations.

```python
async with uow:
    # All operations in same transaction
    research_run = await uow.research_runs.get_by_id(run_id)
    research_run.mark_completed("path/to/dossier")
    await uow.research_runs.save(research_run)

    # Create dossier
    dossier = create_dossier(research_run)
    await uow.dossiers.save(dossier)

    # Commit or rollback together
    await uow.commit()
```

### 5. Repository Factory (`repository_factory.py`)

Centralized factory for dependency injection.

```python
from app.infrastructure.persistence.sqlalchemy import (
    init_repository_factory,
    get_repository_factory,
)
from app.core.database import AsyncSessionLocal

# Initialize at startup
factory = init_repository_factory(AsyncSessionLocal)

# Use in application
async with factory.create_unit_of_work() as uow:
    # Use repositories...
    await uow.commit()
```

## Usage Examples

### Basic CRUD Operations

```python
from uuid import uuid4
from app.core.database import AsyncSessionLocal
from app.infrastructure.persistence.sqlalchemy import get_repository_factory

factory = get_repository_factory()

# Create a research run
async with factory.create_unit_of_work() as uow:
    research_run = ResearchRun(
        id=uuid4(),
        case_id=case_id,
        status=ResearchStatus.PENDING,
        phase=ResearchPhase.INITIALIZING,
        query="Analyze contract timeline",
        findings=[],
        config={"max_findings": 50},
    )
    await uow.research_runs.save(research_run)
    await uow.commit()

# Query research runs
async with factory.create_unit_of_work() as uow:
    runs = await uow.research_runs.find_by_case_id(case_id)
    for run in runs:
        print(f"Run {run.id}: {run.status}")
```

### Complex Graph Operations

```python
# Find connected entities
async with factory.create_unit_of_work() as uow:
    # Get entity with all relationships
    entity, relationships = await uow.graph.get_entity_with_relationships(entity_id)

    # Find entities connected within 2 hops
    connected = await uow.graph.get_connected_entities(entity_id, max_depth=2)

    # Find shortest path between entities
    path = await uow.graph.find_shortest_path(from_id, to_id)

    # Get timeline for entity
    events = await uow.graph.get_timeline_for_entity(entity_id)
```

### Transaction Management

```python
async with factory.create_unit_of_work() as uow:
    try:
        # Multiple operations
        research_run = await uow.research_runs.get_by_id(run_id)
        research_run.advance_to_analyzing()
        await uow.research_runs.save(research_run)

        # Create findings
        for finding_data in discovered_findings:
            finding = Finding(**finding_data)
            await uow.findings.save(finding)
            research_run.add_finding(finding.id)

        # Update research run with findings
        await uow.research_runs.save(research_run)

        # All succeed or all fail
        await uow.commit()
    except Exception as e:
        # Automatic rollback on exception
        logger.error(f"Failed to update research run: {e}")
        # No need to call rollback - __aexit__ handles it
```

### FastAPI Integration

```python
from fastapi import APIRouter, Depends
from app.infrastructure.persistence.sqlalchemy import get_unit_of_work

router = APIRouter()

@router.post("/research/runs")
async def create_research_run(
    case_id: UUID,
    query: str,
    uow = Depends(get_unit_of_work)
):
    async with uow:
        research_run = ResearchRun(
            id=uuid4(),
            case_id=case_id,
            status=ResearchStatus.PENDING,
            phase=ResearchPhase.INITIALIZING,
            query=query,
            findings=[],
            config={},
        )
        await uow.research_runs.save(research_run)
        await uow.commit()

        return {"id": str(research_run.id)}

@router.get("/research/runs/{run_id}")
async def get_research_run(
    run_id: UUID,
    uow = Depends(get_unit_of_work)
):
    async with uow:
        research_run = await uow.research_runs.get_by_id(run_id)
        if not research_run:
            raise HTTPException(404, "Research run not found")
        return research_run
```

## Database Migration

The migration script is located at:
```
alembic/versions/001_add_research_and_knowledge_tables.py
```

Apply migrations:
```bash
# Using mise
mise run db:migrate

# Or directly
alembic upgrade head
```

Rollback migrations:
```bash
alembic downgrade -1
```

## Error Handling

All repositories raise `RepositoryException` on database errors:

```python
from app.infrastructure.persistence.sqlalchemy.repositories import RepositoryException

async with uow:
    try:
        await uow.research_runs.save(research_run)
        await uow.commit()
    except RepositoryException as e:
        logger.error(f"Database error: {e}")
        # Automatic rollback
        raise
```

## Design Principles

1. **Hexagonal Architecture**: Domain entities never leak to infrastructure code
2. **Async Throughout**: All database operations use async/await
3. **Type Safety**: Comprehensive type hints using SQLAlchemy 2.0 Mapped types
4. **Transaction Integrity**: Unit of Work ensures atomic operations
5. **Error Handling**: Proper exception wrapping and cleanup
6. **Dependency Injection**: Factory pattern for clean DI

## Testing

```python
import pytest
from app.infrastructure.persistence.sqlalchemy import init_repository_factory

@pytest.fixture
async def uow(async_session_factory):
    factory = init_repository_factory(async_session_factory)
    return factory.create_unit_of_work()

@pytest.mark.asyncio
async def test_create_research_run(uow):
    async with uow:
        research_run = ResearchRun(...)
        await uow.research_runs.save(research_run)
        await uow.commit()

    async with uow:
        loaded = await uow.research_runs.get_by_id(research_run.id)
        assert loaded.id == research_run.id
```

## Performance Considerations

1. **Connection Pooling**: Configured in `app/core/database.py`
2. **Indexes**: All queries are indexed for performance
3. **JSONB Queries**: Use PostgreSQL JSONB operators for efficient queries
4. **Eager Loading**: Use SQLAlchemy relationships for N+1 prevention
5. **Session Management**: Sessions are short-lived (per-request)

## Future Enhancements

- [ ] Read/write splitting for scaling
- [ ] Query result caching
- [ ] Optimistic locking for concurrency
- [ ] Soft deletes
- [ ] Audit logging
- [ ] Database sharding for large datasets
