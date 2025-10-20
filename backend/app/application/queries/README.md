# Application Layer Queries (CQRS)

This module implements the **Query** side of the CQRS (Command Query Responsibility Segregation) pattern for the LegalEase application.

## Overview

Queries are **read-only operations** that fetch data without modifying state. They are completely separated from commands (write operations) to enable:

- **Optimized read models** - Queries can be optimized independently from writes
- **Scalability** - Read and write workloads can be scaled separately
- **Clarity** - Clear separation between operations that change state vs. those that don't
- **Flexibility** - Different data representations for reads vs. writes

## Architecture

```
┌─────────────┐
│   API/UI    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  QueryBus   │ ◄── Central dispatcher
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│   Query Handlers                │
│  ┌────────────────────────┐    │
│  │ SearchEvidenceHandler  │    │
│  │ GetFindingsHandler     │    │
│  │ GetStatusHandler       │    │
│  │ QueryGraphHandler      │    │
│  │ GetDossierHandler      │    │
│  │ GetTimelineHandler     │    │
│  │ ListRunsHandler        │    │
│  └────────────────────────┘    │
└───────────┬─────────────────────┘
            │
            ▼
┌───────────────────────┐
│   Repositories        │
│   (Read Models)       │
└───────────────────────┘
```

## Available Queries

### 1. SearchEvidenceQuery

Hybrid search across all evidence types (documents, transcripts, communications) combining semantic and keyword search.

```python
from app.application.queries import SearchEvidenceQuery

query = SearchEvidenceQuery(
    query="contract signature date",
    case_ids=[case_uuid],
    evidence_types=[EvidenceType.DOCUMENT],
    chunk_types=[ChunkType.SECTION, ChunkType.MICROBLOCK],
    top_k=20,
    score_threshold=0.3,
    search_mode="HYBRID",  # or "KEYWORD_ONLY", "SEMANTIC_ONLY"
)

result = await query_bus.execute(query)
# Returns: SearchEvidenceResult with SearchResult items
```

**Use Cases:**
- Evidence discovery during case preparation
- Finding supporting quotes for arguments
- Locating specific communications or documents

### 2. GetFindingsQuery

Retrieve findings from a research run with optional filtering.

```python
from app.application.queries import GetFindingsQuery
from app.domain.research.entities.finding import FindingType

query = GetFindingsQuery(
    research_run_id=run_uuid,
    finding_types=[FindingType.FACT, FindingType.QUOTE],
    min_confidence=0.7,
    min_relevance=0.8,
    tags=["contract", "signature"],
    limit=50,
    offset=0,
)

result = await query_bus.execute(query)
# Returns: GetFindingsResult with FindingDTO items
```

**Use Cases:**
- Reviewing AI-discovered facts
- Filtering high-confidence findings
- Paginated display of research results

### 3. GetResearchStatusQuery

Get current status and progress of a research run.

```python
from app.application.queries import GetResearchStatusQuery

query = GetResearchStatusQuery(
    research_run_id=run_uuid,
)

status = await query_bus.execute(query)
# Returns: ResearchStatusDTO with status, phase, progress, etc.
```

**Use Cases:**
- Progress tracking in UI
- Monitoring long-running research
- Debugging research failures

### 4. QueryGraphQuery

Query the knowledge graph with various query types.

```python
from app.application.queries import QueryGraphQuery

# Entity lookup with relationships
query = QueryGraphQuery(
    case_id=case_uuid,
    query_type="entity",
    entity_id=entity_uuid,
    depth=2,
)

# Shortest path between entities
query = QueryGraphQuery(
    case_id=case_uuid,
    query_type="path",
    entity1_id=person1_uuid,
    entity2_id=person2_uuid,
)

# Timeline for entity
query = QueryGraphQuery(
    case_id=case_uuid,
    query_type="timeline",
    entity_id=entity_uuid,
)

result = await query_bus.execute(query)
# Returns: QueryGraphResult with entities, relationships, events
```

**Use Cases:**
- Visualizing entity relationships
- Finding connections between people/organizations
- Timeline visualization

### 5. GetDossierQuery

Retrieve the generated research dossier document.

```python
from app.application.queries import GetDossierQuery

query = GetDossierQuery(
    research_run_id=run_uuid,
)

dossier = await query_bus.execute(query)
# Returns: DossierDTO with executive summary, sections, citations
```

**Use Cases:**
- Downloading final research report
- Displaying dossier in UI
- Exporting to PDF/DOCX

### 6. GetTimelineQuery

Get chronological timeline of events.

```python
from app.application.queries import GetTimelineQuery

query = GetTimelineQuery(
    case_id=case_uuid,
    start_date="2024-01-01",
    end_date="2024-12-31",
    entity_id=person_uuid,  # Optional: filter by entity
    limit=100,
)

timeline = await query_bus.execute(query)
# Returns: GetTimelineResult with TimelineEventDTO items
```

**Use Cases:**
- Timeline visualization
- Chronological case analysis
- Event sequencing

### 7. ListResearchRunsQuery

List all research runs for a case.

```python
from app.application.queries import ListResearchRunsQuery
from app.domain.research.entities.research_run import ResearchStatus

query = ListResearchRunsQuery(
    case_id=case_uuid,
    status=ResearchStatus.COMPLETED,  # Optional filter
    limit=20,
    offset=0,
)

result = await query_bus.execute(query)
# Returns: ListResearchRunsResult with ResearchStatusDTO items
```

**Use Cases:**
- Case dashboard showing all research runs
- Filtering completed/failed runs
- Pagination of research history

## QueryBus

The `QueryBus` is the central dispatcher that routes queries to their handlers.

### Setup

```python
from app.application.queries import setup_query_bus

# Configure with dependencies
query_bus = setup_query_bus(
    retrieval_pipeline=haystack_pipeline,
    result_enricher=enricher_service,
    finding_repo=finding_repository,
    research_repo=research_repository,
    dossier_repo=dossier_repository,
    graph_repo=graph_repository,
    temporal_monitor=temporal_monitor,
)

# Register with FastAPI app
app.state.query_bus = query_bus
```

### Usage

```python
# Execute any query
query = SearchEvidenceQuery(query="contract terms")
result = await query_bus.execute(query)

# Check registration
if query_bus.is_registered(SearchEvidenceQuery):
    print("Handler registered")

# Get all registered queries
query_types = query_bus.get_registered_queries()
```

### Middleware

The QueryBus supports middleware for cross-cutting concerns:

```python
from app.application.queries import LoggingMiddleware, ValidationMiddleware

bus = QueryBus()
bus.add_middleware(LoggingMiddleware())
bus.add_middleware(ValidationMiddleware())

# Custom middleware
class CachingMiddleware:
    async def before_query(self, query):
        # Check cache
        pass

    async def after_query(self, query, result):
        # Store in cache
        pass

    async def on_error(self, query, error):
        # Handle error
        pass

bus.add_middleware(CachingMiddleware())
```

## Data Transfer Objects (DTOs)

All queries return **DTOs** rather than domain entities to:

- Decouple application layer from domain layer
- Control what data is exposed to API/UI
- Enable optimized serialization
- Support API versioning

### Example DTO Structure

```python
@dataclass
class FindingDTO:
    id: UUID
    research_run_id: UUID
    finding_type: FindingType
    text: str
    entities: List[UUID]
    citations: List[UUID]
    confidence: float
    relevance: float
    tags: List[str]
    created_at: str
    metadata: Dict[str, Any]
```

## Design Principles

### 1. Immutability
All queries are immutable dataclasses with validation in `__post_init__`:

```python
@dataclass
class SearchEvidenceQuery:
    query: str
    top_k: int = 20

    def __post_init__(self):
        if not self.query:
            raise ValueError("Query cannot be empty")
        if self.top_k < 1:
            raise ValueError("top_k must be >= 1")
```

### 2. Single Responsibility
Each handler has one responsibility - execute one query type:

```python
class GetFindingsQueryHandler:
    async def handle(self, query: GetFindingsQuery) -> GetFindingsResult:
        # Only handles GetFindingsQuery
        pass
```

### 3. Dependency Injection
Handlers receive dependencies via constructor injection:

```python
class SearchEvidenceQueryHandler:
    def __init__(self, retrieval_pipeline, result_enricher):
        self.pipeline = retrieval_pipeline
        self.enricher = result_enricher
```

### 4. Type Safety
Full type hints for compile-time checking:

```python
async def handle(self, query: GetFindingsQuery) -> GetFindingsResult:
    findings: List[FindingDTO] = []
    # Type-safe operations
    return GetFindingsResult(findings=findings, total=len(findings))
```

### 5. Comprehensive Logging
Structured logging at all levels:

```python
self.logger.info(
    "Query executed successfully",
    extra={
        "query_type": "SearchEvidence",
        "results_count": len(results),
        "execution_time_ms": elapsed_ms,
    }
)
```

## Testing

### Unit Testing Handlers

```python
import pytest
from app.application.queries import GetFindingsQuery, GetFindingsQueryHandler

@pytest.mark.asyncio
async def test_get_findings_handler():
    # Mock repository
    mock_repo = Mock()
    mock_repo.find_by_research_run.return_value = [
        Finding(id=uuid4(), ...),
        Finding(id=uuid4(), ...),
    ]

    # Create handler
    handler = GetFindingsQueryHandler(finding_repo=mock_repo)

    # Execute query
    query = GetFindingsQuery(
        research_run_id=uuid4(),
        min_confidence=0.7,
    )
    result = await handler.handle(query)

    # Assert
    assert len(result.findings) == 2
    assert all(f.confidence >= 0.7 for f in result.findings)
```

### Integration Testing QueryBus

```python
@pytest.mark.asyncio
async def test_query_bus_integration():
    # Setup real dependencies
    bus = setup_query_bus(
        finding_repo=test_finding_repo,
        research_repo=test_research_repo,
    )

    # Execute query
    query = GetFindingsQuery(research_run_id=test_run_id)
    result = await bus.execute(query)

    # Assert
    assert isinstance(result, GetFindingsResult)
```

## Error Handling

All handlers follow consistent error handling:

```python
try:
    # Execute query logic
    result = await self.repo.find_by_id(query.id)

    if not result:
        raise ValueError(f"Entity not found: {query.id}")

    return self._to_dto(result)

except ValueError:
    # Re-raise validation errors
    raise

except Exception as e:
    # Wrap infrastructure errors
    self.logger.error(f"Query failed: {e}", exc_info=True)
    raise RuntimeError(f"Query execution failed: {e}") from e
```

## Performance Considerations

### Pagination
Always use pagination for large result sets:

```python
query = GetFindingsQuery(
    research_run_id=run_id,
    limit=50,
    offset=0,  # Page 1
)
```

### Filtering at Repository Level
Filter at the database level when possible:

```python
# Good - filters in DB
findings = await repo.find_by_confidence(run_id, min_confidence=0.7)

# Bad - fetches all, filters in memory
all_findings = await repo.find_by_research_run(run_id)
findings = [f for f in all_findings if f.confidence >= 0.7]
```

### Caching
Consider caching for frequently accessed, slow queries:

```python
class CachingMiddleware:
    async def before_query(self, query):
        cache_key = self._get_cache_key(query)
        if cached := await cache.get(cache_key):
            return cached  # Return cached result
```

## Integration with FastAPI

```python
from fastapi import FastAPI, Depends
from app.application.queries import QueryBus, SearchEvidenceQuery

app = FastAPI()

# Setup in startup
@app.on_event("startup")
async def startup():
    app.state.query_bus = setup_query_bus(...)

# Dependency
def get_query_bus() -> QueryBus:
    return app.state.query_bus

# Route
@app.get("/api/search")
async def search(
    q: str,
    bus: QueryBus = Depends(get_query_bus),
):
    query = SearchEvidenceQuery(query=q, top_k=20)
    result = await bus.execute(query)
    return result
```

## Future Enhancements

Potential improvements:

1. **Query Result Caching** - Cache frequently accessed queries
2. **Query Metrics** - Track execution times, hit rates
3. **Query Composition** - Compose complex queries from simple ones
4. **Streaming Results** - Stream large result sets
5. **Query Optimization** - Query plan analysis and optimization
6. **GraphQL Support** - Map GraphQL queries to CQRS queries
