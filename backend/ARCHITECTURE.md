# PostgreSQL Persistence Architecture

## Hexagonal Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                            Application Layer                               │
│                      (FastAPI Routes, Service Classes)                     │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ uses
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                             Domain Layer                                   │
│  ┌──────────────────────┐              ┌──────────────────────┐           │
│  │  Research Domain     │              │  Knowledge Domain     │           │
│  │                      │              │                       │           │
│  │  - ResearchRun       │              │  - Entity             │           │
│  │  - Finding           │              │  - Event              │           │
│  │  - Hypothesis        │              │  - Relationship       │           │
│  │  - Dossier           │              │                       │           │
│  │                      │              │                       │           │
│  │  Interfaces:         │              │  Interfaces:          │           │
│  │  - ResearchRunRepo   │              │  - EntityRepo         │           │
│  │  - FindingRepo       │              │  - EventRepo          │           │
│  │  - HypothesisRepo    │              │  - RelationshipRepo   │           │
│  │  - DossierRepo       │              │  - GraphRepo          │           │
│  └──────────────────────┘              └──────────────────────┘           │
└────────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ implements
                                    │
┌────────────────────────────────────────────────────────────────────────────┐
│                    Infrastructure Persistence Layer                        │
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │                         Unit of Work                                │   │
│  │  ┌──────────────────────────────────────────────────────────────┐  │   │
│  │  │  SQLAlchemyUnitOfWork                                        │  │   │
│  │  │  - Manages AsyncSession                                      │  │   │
│  │  │  - Provides all repositories                                 │  │   │
│  │  │  - Coordinates transactions                                  │  │   │
│  │  │                                                               │  │   │
│  │  │  Properties:                                                  │  │   │
│  │  │  .research_runs  .findings  .hypotheses  .dossiers          │  │   │
│  │  │  .entities  .events  .relationships  .graph                  │  │   │
│  │  │                                                               │  │   │
│  │  │  Methods:                                                     │  │   │
│  │  │  commit()  rollback()  flush()                              │  │   │
│  │  └──────────────────────────────────────────────────────────────┘  │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                    │                                       │
│                                    │ creates and manages                   │
│                                    ▼                                       │
│  ┌─────────────────────┐    ┌──────────────────────┐                     │
│  │    Repositories     │    │      Mappers         │                     │
│  │                     │    │                      │                     │
│  │  Research:          │◄───┤  ORM ◄─► Domain     │                     │
│  │  - ResearchRunRepo  │    │                      │                     │
│  │  - FindingRepo      │    │  - to_domain_*()     │                     │
│  │  - HypothesisRepo   │    │  - to_model_*()      │                     │
│  │  - DossierRepo      │    │                      │                     │
│  │                     │    │  Handle:             │                     │
│  │  Knowledge:         │    │  - Enums             │                     │
│  │  - EntityRepo       │    │  - UUIDs             │                     │
│  │  - EventRepo        │    │  - Value Objects     │                     │
│  │  - RelationshipRepo │    │  - JSONB arrays      │                     │
│  │  - GraphRepo        │    │                      │                     │
│  └─────────────────────┘    └──────────────────────┘                     │
│           │                            │                                   │
│           │ uses                       │ uses                              │
│           ▼                            ▼                                   │
│  ┌──────────────────────────────────────────────────────────────────┐     │
│  │                       ORM Models                                  │     │
│  │  Research:                         Knowledge:                     │     │
│  │  - ResearchRunModel                - EntityModel                 │     │
│  │  - FindingModel                    - EventModel                  │     │
│  │  - HypothesisModel                 - RelationshipModel           │     │
│  │  - DossierModel                                                  │     │
│  │                                                                   │     │
│  │  Features:                                                        │     │
│  │  - SQLAlchemy 2.0 Mapped types                                  │     │
│  │  - UUID primary keys                                             │     │
│  │  - JSONB columns                                                 │     │
│  │  - Foreign key relationships                                     │     │
│  │  - Cascade deletes                                               │     │
│  └──────────────────────────────────────────────────────────────────┘     │
│                                    │                                       │
│                                    │ maps to                               │
│                                    ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────┐     │
│  │                      PostgreSQL Database                          │     │
│  │                                                                   │     │
│  │  Tables:                                                          │     │
│  │  - research_runs                                                  │     │
│  │  - findings                                                       │     │
│  │  - hypotheses                                                     │     │
│  │  - dossiers                                                       │     │
│  │  - kg_entities                                                    │     │
│  │  - kg_events                                                      │     │
│  │  - kg_relationships                                               │     │
│  │                                                                   │     │
│  │  Features:                                                        │     │
│  │  - JSONB columns for flexible data                              │     │
│  │  - Comprehensive indexes                                         │     │
│  │  - Foreign keys with CASCADE                                     │     │
│  │  - UUID primary keys                                             │     │
│  └──────────────────────────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Write Operation (Create/Update)

```
1. Application creates Domain Entity
   ResearchRun(id=..., status=PENDING, ...)

2. Unit of Work receives entity
   await uow.research_runs.save(research_run)

3. Repository uses Mapper to convert
   to_model_research_run(entity) → ResearchRunModel

4. SQLAlchemy persists ORM Model
   session.add(model)

5. Unit of Work commits transaction
   await uow.commit()
   → session.commit()

6. PostgreSQL stores data
   INSERT INTO research_runs (...)
```

### Read Operation (Query)

```
1. Application requests data via Repository
   await uow.research_runs.get_by_id(run_id)

2. Repository queries via SQLAlchemy
   select(ResearchRunModel).where(...)

3. PostgreSQL returns row data
   Row from research_runs table

4. SQLAlchemy creates ORM Model
   ResearchRunModel instance

5. Mapper converts to Domain Entity
   to_domain_research_run(model) → ResearchRun

6. Application receives Domain Entity
   ResearchRun(id=..., status=PENDING, ...)
```

## Transaction Flow

```
┌─────────────────────────────────────────────────────────────┐
│  async with uow:  # __aenter__                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  1. Create AsyncSession                               │  │
│  │  2. Initialize all repositories                       │  │
│  │  3. Begin implicit transaction                        │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  # Application code                                         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  await uow.research_runs.save(run)                    │  │
│  │  await uow.findings.save(finding)                     │  │
│  │  await uow.entities.save(entity)                      │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  # Commit or Rollback                                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  if success:                                          │  │
│  │    await uow.commit()    # All changes persisted     │  │
│  │  else:                                                │  │
│  │    await uow.rollback()  # All changes discarded     │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  # __aexit__                                                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  1. Auto-rollback if exception                        │  │
│  │  2. Close session                                     │  │
│  │  3. Cleanup resources                                 │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Repository Pattern

### Research Run Repository

```
┌───────────────────────────────────────────────────────────────┐
│  SQLAlchemyResearchRunRepository                              │
│  implements ResearchRunRepository (domain interface)          │
├───────────────────────────────────────────────────────────────┤
│  Methods:                                                     │
│                                                               │
│  Query Operations:                                            │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  get_by_id(id: UUID) → Optional[ResearchRun]          │ │
│  │    ↓ SQL: SELECT * FROM research_runs WHERE id = ?     │ │
│  │                                                         │ │
│  │  find_by_case_id(case_id: UUID) → List[ResearchRun]   │ │
│  │    ↓ SQL: SELECT * FROM research_runs                  │ │
│  │           WHERE case_id = ? ORDER BY started_at DESC   │ │
│  │                                                         │ │
│  │  find_by_status(status: str) → List[ResearchRun]      │ │
│  │    ↓ SQL: SELECT * FROM research_runs                  │ │
│  │           WHERE status = ? ORDER BY started_at DESC    │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  Write Operations:                                            │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  save(research_run: ResearchRun) → ResearchRun        │ │
│  │    ↓ Check if exists                                   │ │
│  │    ↓ UPDATE if exists, INSERT if new                   │ │
│  │                                                         │ │
│  │  delete(id: UUID) → bool                               │ │
│  │    ↓ SQL: DELETE FROM research_runs WHERE id = ?       │ │
│  └─────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

### Graph Repository

```
┌───────────────────────────────────────────────────────────────┐
│  SQLAlchemyGraphRepository                                    │
│  implements GraphRepository (domain interface)                │
├───────────────────────────────────────────────────────────────┤
│  Dependencies:                                                │
│  - EntityRepository                                           │
│  - EventRepository                                            │
│  - RelationshipRepository                                     │
│                                                               │
│  Complex Queries:                                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  get_connected_entities(id, max_depth=2)               │ │
│  │    Algorithm: Breadth-First Search                      │ │
│  │    1. Start with entity_id                              │ │
│  │    2. Find all relationships                            │ │
│  │    3. Get connected entities                            │ │
│  │    4. Repeat for max_depth hops                         │ │
│  │    5. Return unique set of entities                     │ │
│  │                                                         │ │
│  │  find_shortest_path(from_id, to_id)                    │ │
│  │    Algorithm: Breadth-First Search                      │ │
│  │    1. Queue: [(from_id, [])]                           │ │
│  │    2. For each node, find relationships                 │ │
│  │    3. Track path to node                                │ │
│  │    4. Return when to_id found                          │ │
│  │                                                         │ │
│  │  get_timeline_for_entity(entity_id)                    │ │
│  │    ↓ SQL: SELECT * FROM kg_events                       │ │
│  │           WHERE participants @> [entity_id]             │ │
│  │           ORDER BY timestamp                            │ │
│  └─────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

## Database Schema

### Research Tables

```sql
research_runs
├── id (UUID, PK)
├── case_id (UUID, FK → cases.id)
├── status (VARCHAR) ─────────┐ Indexed
├── phase (VARCHAR)           │
├── query (TEXT)              │
├── started_at (TIMESTAMP) ───┤ Indexed
├── completed_at (TIMESTAMP)  │
├── dossier_path (VARCHAR)    │
├── findings (JSONB) ─────────┘ Array of UUIDs
├── config (JSONB)
└── metadata (JSONB)

findings
├── id (UUID, PK)
├── research_run_id (UUID, FK → research_runs.id) ─┐ Indexed
├── finding_type (VARCHAR) ─────────────────────────┤ Indexed
├── text (TEXT)                                     │
├── confidence (FLOAT) ─────────────────────────────┤ Indexed
├── relevance (FLOAT)                               │
├── entities (JSONB) ───────────────────────────────┘ Array of UUIDs
├── citations (JSONB)
├── tags (JSONB)
└── metadata (JSONB)

hypotheses
├── id (UUID, PK)
├── research_run_id (UUID, FK → research_runs.id)
├── hypothesis_text (TEXT)
├── confidence (FLOAT) ──────────┐ Indexed
├── supporting_findings (JSONB) ─┘ Array of UUIDs
├── contradicting_findings (JSONB)
└── metadata (JSONB)

dossiers
├── id (UUID, PK)
├── research_run_id (UUID, FK, UNIQUE)
├── executive_summary (TEXT)
├── citations_appendix (TEXT)
├── generated_at (TIMESTAMP)
├── sections (JSONB) ──────────┐ Array of {title, content, order}
└── metadata (JSONB) ──────────┘
```

### Knowledge Graph Tables

```sql
kg_entities
├── id (UUID, PK)
├── entity_type (VARCHAR) ──────┐ Indexed
├── name (VARCHAR) ─────────────┤ Indexed
├── first_seen (TIMESTAMP) ─────┤ Indexed
├── last_seen (TIMESTAMP) ──────┤ Indexed
├── aliases (JSONB) ────────────┘ Array of strings
├── attributes (JSONB)
├── source_citations (JSONB)
└── metadata (JSONB)

kg_events
├── id (UUID, PK)
├── event_type (VARCHAR) ────────┐ Indexed
├── description (TEXT)           │
├── timestamp (TIMESTAMP) ───────┤ Indexed
├── duration (FLOAT)             │
├── location (VARCHAR)           │
├── participants (JSONB) ────────┘ Array of entity UUIDs
├── source_citations (JSONB)
└── metadata (JSONB)

kg_relationships
├── id (UUID, PK)
├── from_entity_id (UUID, FK → kg_entities.id) ─┐ Indexed
├── to_entity_id (UUID, FK → kg_entities.id) ───┤ Indexed
├── relationship_type (VARCHAR) ─────────────────┤ Indexed
├── strength (FLOAT) ────────────────────────────┤ Indexed
├── temporal_start (TIMESTAMP)                   │
├── temporal_end (TIMESTAMP)                     │
├── source_citations (JSONB) ────────────────────┘
└── metadata (JSONB)
```

## Key Design Principles

1. **Hexagonal Architecture**: Domain never depends on infrastructure
2. **Async Throughout**: All operations use async/await for scalability
3. **Type Safety**: Comprehensive type hints with SQLAlchemy 2.0
4. **Transaction Integrity**: Unit of Work ensures ACID properties
5. **Flexible Storage**: JSONB for evolving data structures
6. **Performance**: Strategic indexing on all query patterns
7. **Clean Separation**: Mappers handle bidirectional conversion
8. **Error Handling**: Proper exception wrapping and cleanup
