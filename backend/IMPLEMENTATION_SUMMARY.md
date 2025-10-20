# PostgreSQL Repositories Implementation Summary

## Overview

Implemented a comprehensive SQLAlchemy-based persistence layer for the Research and Knowledge Graph domains, following hexagonal architecture and using async SQLAlchemy 2.0.

## What Was Implemented

### 1. Database Configuration (`app/core/database.py`)

**Updated to SQLAlchemy 2.0 Async:**
- Replaced synchronous engine with `create_async_engine`
- Updated session factory to `async_sessionmaker`
- Added `DeclarativeBase` for SQLAlchemy 2.0
- Created async dependency injection helper `get_async_db()`
- Auto-converts database URL to async format (postgresql+asyncpg)

### 2. ORM Models (`app/infrastructure/persistence/sqlalchemy/models/`)

**Research Models (`research.py`):**
- `ResearchRunModel` - Tracks AI research sessions
  - Status, phase, query, findings, configuration
  - Relationships to findings, hypotheses, and dossier
- `FindingModel` - Discovered insights with confidence scores
  - Type, text, entities, citations, relevance
  - Tag-based categorization
- `HypothesisModel` - Generated theories from findings
  - Supporting and contradicting findings
  - Confidence scores
- `DossierModel` - Final research documents
  - Executive summary, sections, citations
  - JSONB storage for flexible structure

**Knowledge Graph Models (`knowledge.py`):**
- `EntityModel` - People, organizations, locations
  - Type, name, aliases, attributes
  - Temporal tracking (first_seen, last_seen)
- `EventModel` - Timeline events
  - Type, description, participants, timestamp
  - Optional duration and location
- `RelationshipModel` - Entity connections
  - From/to entities, type, strength
  - Temporal bounds (start/end dates)

**Key Features:**
- UUID primary keys throughout
- JSONB columns for flexible data
- Comprehensive indexing for performance
- Proper foreign key relationships with CASCADE deletes
- SQLAlchemy 2.0 `Mapped` type annotations

### 3. Mappers (`app/infrastructure/persistence/sqlalchemy/mappers.py`)

Bidirectional conversion functions between ORM models and domain entities:

**Research Mappers:**
- `to_domain_research_run()` / `to_model_research_run()`
- `to_domain_finding()` / `to_model_finding()`
- `to_domain_hypothesis()` / `to_model_hypothesis()`
- `to_domain_dossier()` / `to_model_dossier()`

**Knowledge Graph Mappers:**
- `to_domain_entity()` / `to_model_entity()`
- `to_domain_event()` / `to_model_event()`
- `to_domain_relationship()` / `to_model_relationship()`

**Features:**
- Handles enum conversions (ResearchStatus, FindingType, etc.)
- UUID string serialization for JSONB storage
- Proper value object conversion (DossierSection)
- Null-safe handling

### 4. Repositories (`app/infrastructure/persistence/sqlalchemy/repositories/`)

**Research Repositories (`research.py`):**
- `SQLAlchemyResearchRunRepository`
  - `get_by_id()`, `find_by_case_id()`, `find_by_status()`
  - `save()`, `delete()`
- `SQLAlchemyFindingRepository`
  - `find_by_research_run()`, `find_by_type()`, `find_by_confidence()`
  - `find_by_tag()` - JSONB array search
- `SQLAlchemyHypothesisRepository`
  - `find_by_research_run()`, `find_by_confidence()`
- `SQLAlchemyDossierRepository`
  - `get_by_research_run()` - Unique dossier per research run

**Knowledge Graph Repositories (`knowledge.py`):**
- `SQLAlchemyEntityRepository`
  - `find_by_name()` - Searches name and aliases
  - `find_by_type()`, `find_by_case_id()`
- `SQLAlchemyEventRepository`
  - `find_by_time_range()` - Temporal queries
  - `find_by_participant()` - JSONB array search
  - `find_by_type()`
- `SQLAlchemyRelationshipRepository`
  - `find_by_entity()` - Bidirectional search
  - `find_by_type()`, `find_between()`
- `SQLAlchemyGraphRepository` - High-level graph operations
  - `get_entity_with_relationships()`
  - `get_connected_entities(max_depth)` - BFS traversal
  - `find_shortest_path()` - BFS pathfinding
  - `get_timeline_for_entity()` - Chronological events
  - `get_subgraph()` - Extract connected subgraphs

**Features:**
- All operations are async
- Proper exception handling with `RepositoryException`
- Efficient SQL queries with proper indexes
- JSONB operators for array searches
- Update-or-insert logic in `save()` methods

### 5. Unit of Work (`app/infrastructure/persistence/sqlalchemy/unit_of_work.py`)

`SQLAlchemyUnitOfWork` - Transaction management:
- Implements `AsyncUnitOfWork` protocol
- Async context manager (`__aenter__`, `__aexit__`)
- Properties for all repositories:
  - `research_runs`, `findings`, `hypotheses`, `dossiers`
  - `entities`, `events`, `relationships`, `graph`
- Transaction methods:
  - `commit()` - Persist all changes
  - `rollback()` - Discard all changes
  - `flush()` - Sync to DB without committing
- Auto-rollback on exceptions
- Proper resource cleanup

`SQLAlchemyUnitOfWorkFactory`:
- Factory for creating UoW instances
- Encapsulates session factory

### 6. Repository Factory (`app/infrastructure/persistence/sqlalchemy/repository_factory.py`)

`RepositoryFactory` - Dependency injection helper:
- `create_unit_of_work()` - Main entry point
- Individual repository factories for all types
- Handles repository dependencies (e.g., GraphRepository)

**Global Factory Functions:**
- `init_repository_factory()` - Initialize at startup
- `get_repository_factory()` - Get singleton instance
- `get_unit_of_work()` - FastAPI dependency helper

### 7. Database Migration (`alembic/versions/001_add_research_and_knowledge_tables.py`)

Complete migration script creating all tables:

**Research Tables:**
- `research_runs` with indexes on case_id, status, started_at
- `findings` with indexes on research_run_id, type, confidence
- `hypotheses` with indexes on research_run_id, confidence
- `dossiers` with unique constraint on research_run_id

**Knowledge Graph Tables:**
- `kg_entities` with indexes on type, name, first_seen, last_seen
- `kg_events` with indexes on type, timestamp
- `kg_relationships` with indexes on entities, type, strength

**Features:**
- UUID primary keys with `gen_random_uuid()`
- JSONB columns with default values
- Foreign keys with CASCADE delete
- Comprehensive indexes for performance
- Proper upgrade/downgrade support

### 8. Documentation

**README.md** - Comprehensive guide covering:
- Architecture overview with diagrams
- Component descriptions
- Usage examples (CRUD, graph operations, transactions)
- FastAPI integration
- Error handling
- Design principles
- Testing guidelines
- Performance considerations

## File Structure

```
backend/app/
├── core/
│   └── database.py (UPDATED - async SQLAlchemy 2.0)
├── infrastructure/persistence/sqlalchemy/
│   ├── __init__.py
│   ├── README.md (NEW)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── research.py (NEW)
│   │   └── knowledge.py (NEW)
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── research.py (NEW)
│   │   └── knowledge.py (NEW)
│   ├── mappers.py (NEW)
│   ├── unit_of_work.py (NEW)
│   └── repository_factory.py (NEW)
└── alembic/versions/
    └── 001_add_research_and_knowledge_tables.py (NEW)
```

## Key Design Decisions

1. **Async Throughout**: All database operations use async/await for scalability
2. **SQLAlchemy 2.0**: Modern type-safe ORM with Mapped types
3. **JSONB for Flexibility**: Lists of UUIDs stored as JSONB for easy queries
4. **Hexagonal Architecture**: Clean separation between domain and infrastructure
5. **Unit of Work Pattern**: Atomic transactions across multiple repositories
6. **Factory Pattern**: Centralized dependency injection
7. **Comprehensive Indexing**: All query patterns are indexed
8. **Type Safety**: Full type annotations throughout
9. **Error Handling**: Proper exception wrapping and cleanup
10. **Documentation**: Extensive inline docs and usage examples

## Usage Example

```python
from app.infrastructure.persistence.sqlalchemy import (
    init_repository_factory,
    get_repository_factory,
)
from app.core.database import AsyncSessionLocal

# At startup
init_repository_factory(AsyncSessionLocal)

# In application code
factory = get_repository_factory()

async with factory.create_unit_of_work() as uow:
    # Create research run
    research_run = ResearchRun(
        id=uuid4(),
        case_id=case_id,
        status=ResearchStatus.RUNNING,
        phase=ResearchPhase.ANALYZING,
        query="Analyze contract modifications",
        findings=[],
        config={"max_findings": 50},
    )
    await uow.research_runs.save(research_run)

    # Create findings
    finding = Finding(
        id=uuid4(),
        research_run_id=research_run.id,
        finding_type=FindingType.FACT,
        text="Contract signed on 2024-03-15",
        entities=[entity1_id, entity2_id],
        citations=[citation_id],
        confidence=0.95,
        relevance=0.88,
        tags=["contract", "signature"],
    )
    await uow.findings.save(finding)

    # Add to research run
    research_run.add_finding(finding.id)
    await uow.research_runs.save(research_run)

    # Commit all changes
    await uow.commit()
```

## Next Steps

1. **Apply Migration**: Run `mise run db:migrate` or `alembic upgrade head`
2. **Initialize Factory**: Add startup code to initialize repository factory
3. **Update Services**: Migrate existing services to use new repositories
4. **Add Tests**: Create integration tests for repositories
5. **Add Monitoring**: Instrument queries for performance tracking

## Dependencies Required

Add to `pyproject.toml`:
```toml
asyncpg = "^0.29.0"  # Async PostgreSQL driver
```

Already present:
- sqlalchemy >= 2.0
- alembic
- pydantic-settings
