# Quick Start: PostgreSQL Persistence Layer

This guide will help you get started with the new SQLAlchemy persistence layer for Research and Knowledge Graph domains.

## 1. Install Dependencies

The `asyncpg` driver is required for async PostgreSQL operations:

```bash
# Add to pyproject.toml
uv add asyncpg

# Or install directly
uv pip install asyncpg
```

## 2. Run Database Migration

Apply the migration to create the new tables:

```bash
# Using mise
mise run db:migrate

# Or directly with alembic
cd backend
alembic upgrade head
```

This creates the following tables:
- `research_runs`, `findings`, `hypotheses`, `dossiers`
- `kg_entities`, `kg_events`, `kg_relationships`

## 3. Initialize Repository Factory

Add this to your application startup (e.g., `main.py` or `app.py`):

```python
from app.core.database import AsyncSessionLocal
from app.infrastructure.persistence.sqlalchemy import init_repository_factory

# At application startup
@app.on_event("startup")
async def startup():
    # Initialize repository factory
    init_repository_factory(AsyncSessionLocal)
```

## 4. Basic Usage

### Create a Research Run

```python
from uuid import uuid4
from app.infrastructure.persistence.sqlalchemy import get_repository_factory
from app.domain.research.entities import (
    ResearchRun,
    ResearchStatus,
    ResearchPhase,
)

factory = get_repository_factory()

async def create_research_run(case_id: UUID, query: str):
    async with factory.create_unit_of_work() as uow:
        research_run = ResearchRun(
            id=uuid4(),
            case_id=case_id,
            status=ResearchStatus.PENDING,
            phase=ResearchPhase.INITIALIZING,
            query=query,
            findings=[],
            config={"max_findings": 50, "min_confidence": 0.7},
        )

        # Save research run
        saved = await uow.research_runs.save(research_run)

        # Commit transaction
        await uow.commit()

        return saved
```

### Query Research Runs

```python
async def get_case_research_runs(case_id: UUID):
    async with factory.create_unit_of_work() as uow:
        runs = await uow.research_runs.find_by_case_id(case_id)
        return runs
```

### Create Findings

```python
from app.domain.research.entities import Finding, FindingType

async def add_finding(research_run_id: UUID, text: str, confidence: float):
    async with factory.create_unit_of_work() as uow:
        finding = Finding(
            id=uuid4(),
            research_run_id=research_run_id,
            finding_type=FindingType.FACT,
            text=text,
            entities=[],
            citations=[],
            confidence=confidence,
            relevance=0.85,
            tags=["auto-generated"],
        )

        await uow.findings.save(finding)

        # Update research run with finding
        research_run = await uow.research_runs.get_by_id(research_run_id)
        research_run.add_finding(finding.id)
        await uow.research_runs.save(research_run)

        await uow.commit()
```

### Work with Knowledge Graph

```python
from datetime import datetime
from app.domain.knowledge.entities import (
    Entity,
    Event,
    Relationship,
    EntityType,
    EventType,
    RelationshipType,
)

async def create_knowledge_graph():
    async with factory.create_unit_of_work() as uow:
        # Create entities
        person = Entity(
            id=uuid4(),
            entity_type=EntityType.PERSON,
            name="John Doe",
            aliases=["J. Doe"],
            attributes={"role": "CEO"},
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            source_citations=[],
        )
        await uow.entities.save(person)

        org = Entity(
            id=uuid4(),
            entity_type=EntityType.ORGANIZATION,
            name="Acme Corp",
            aliases=[],
            attributes={"industry": "Technology"},
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            source_citations=[],
        )
        await uow.entities.save(org)

        # Create relationship
        relationship = Relationship(
            id=uuid4(),
            from_entity_id=person.id,
            to_entity_id=org.id,
            relationship_type=RelationshipType.WORKS_FOR,
            strength=0.95,
            source_citations=[],
        )
        await uow.relationships.save(relationship)

        # Create event
        event = Event(
            id=uuid4(),
            event_type=EventType.MEETING,
            description="Contract signing meeting",
            participants=[person.id],
            timestamp=datetime.utcnow(),
            source_citations=[],
        )
        await uow.events.save(event)

        await uow.commit()
```

### Graph Queries

```python
async def analyze_entity_network(entity_id: UUID):
    async with factory.create_unit_of_work() as uow:
        # Get entity with relationships
        entity, relationships = await uow.graph.get_entity_with_relationships(entity_id)

        # Find connected entities within 2 hops
        connected = await uow.graph.get_connected_entities(entity_id, max_depth=2)

        # Get timeline
        events = await uow.graph.get_timeline_for_entity(entity_id)

        return {
            "entity": entity,
            "relationships": relationships,
            "connected_count": len(connected),
            "events": events,
        }
```

## 5. FastAPI Integration

### Setup Dependency

```python
from fastapi import FastAPI, Depends
from app.infrastructure.persistence.sqlalchemy import get_unit_of_work

app = FastAPI()

@app.on_event("startup")
async def startup():
    from app.core.database import AsyncSessionLocal
    from app.infrastructure.persistence.sqlalchemy import init_repository_factory
    init_repository_factory(AsyncSessionLocal)
```

### Use in Endpoints

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/research")

class CreateResearchRunRequest(BaseModel):
    case_id: UUID
    query: str
    config: dict = {}

@router.post("/runs")
async def create_run(
    request: CreateResearchRunRequest,
    uow = Depends(get_unit_of_work)
):
    async with uow:
        research_run = ResearchRun(
            id=uuid4(),
            case_id=request.case_id,
            status=ResearchStatus.PENDING,
            phase=ResearchPhase.INITIALIZING,
            query=request.query,
            findings=[],
            config=request.config,
        )

        await uow.research_runs.save(research_run)
        await uow.commit()

        return {"id": str(research_run.id)}

@router.get("/runs/{run_id}")
async def get_run(
    run_id: UUID,
    uow = Depends(get_unit_of_work)
):
    async with uow:
        run = await uow.research_runs.get_by_id(run_id)
        if not run:
            raise HTTPException(404, "Research run not found")
        return run

@router.get("/runs/{run_id}/findings")
async def get_findings(
    run_id: UUID,
    min_confidence: float = 0.0,
    uow = Depends(get_unit_of_work)
):
    async with uow:
        findings = await uow.findings.find_by_confidence(
            run_id,
            min_confidence
        )
        return findings
```

## 6. Error Handling

```python
from app.infrastructure.persistence.sqlalchemy.repositories import RepositoryException
from app.infrastructure.persistence.sqlalchemy import UnitOfWorkException

async def safe_operation():
    try:
        async with factory.create_unit_of_work() as uow:
            # Your operations
            await uow.commit()
    except RepositoryException as e:
        logger.error(f"Database error: {e}")
        # Handle gracefully
    except UnitOfWorkException as e:
        logger.error(f"Transaction error: {e}")
        # Already rolled back automatically
```

## 7. Testing

```python
import pytest
from app.infrastructure.persistence.sqlalchemy import init_repository_factory

@pytest.fixture
async def uow(async_session_factory):
    """Provide a Unit of Work for tests."""
    factory = init_repository_factory(async_session_factory)
    return factory.create_unit_of_work()

@pytest.mark.asyncio
async def test_create_research_run(uow):
    async with uow:
        research_run = ResearchRun(
            id=uuid4(),
            case_id=uuid4(),
            status=ResearchStatus.PENDING,
            phase=ResearchPhase.INITIALIZING,
            query="Test query",
            findings=[],
            config={},
        )

        await uow.research_runs.save(research_run)
        await uow.commit()

    # Verify in new transaction
    async with uow:
        loaded = await uow.research_runs.get_by_id(research_run.id)
        assert loaded is not None
        assert loaded.query == "Test query"
```

## Common Patterns

### Pattern 1: Multi-Step Transaction

```python
async with uow:
    # Step 1: Update research run
    run = await uow.research_runs.get_by_id(run_id)
    run.advance_to_analyzing()
    await uow.research_runs.save(run)

    # Step 2: Create findings
    for data in findings_data:
        finding = Finding(**data)
        await uow.findings.save(finding)
        run.add_finding(finding.id)

    # Step 3: Update run with findings
    await uow.research_runs.save(run)

    # All or nothing
    await uow.commit()
```

### Pattern 2: Read-Only Query

```python
async with uow:
    # Just read, no commit needed
    runs = await uow.research_runs.find_by_status(ResearchStatus.RUNNING)
    # Context manager closes session automatically
```

### Pattern 3: Conditional Commit

```python
async with uow:
    run = await uow.research_runs.get_by_id(run_id)

    if run.is_completed():
        # Already done, rollback
        await uow.rollback()
        return

    run.mark_completed("path/to/dossier")
    await uow.research_runs.save(run)
    await uow.commit()
```

## Troubleshooting

### Issue: "Repository factory not initialized"
**Solution**: Call `init_repository_factory(AsyncSessionLocal)` at startup

### Issue: "asyncpg not installed"
**Solution**: Run `uv add asyncpg`

### Issue: "Table does not exist"
**Solution**: Run database migration: `alembic upgrade head`

### Issue: "Session already closed"
**Solution**: Always use `async with uow:` context manager

## Next Steps

1. Read the full documentation: `app/infrastructure/persistence/sqlalchemy/README.md`
2. Review implementation details: `IMPLEMENTATION_SUMMARY.md`
3. Check out domain entities: `app/domain/research/` and `app/domain/knowledge/`
4. Write tests for your repositories
5. Monitor query performance with logging

## Resources

- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
