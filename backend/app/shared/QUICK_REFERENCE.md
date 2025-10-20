# Shared Module Quick Reference

## Import Everything
```python
from app.shared import *
```

## Identifiers

```python
# Type-safe IDs
case_id = CaseId(generate_id())
doc_id = DocumentId(generate_id())

# Global IDs
gid = GID.create("case")                    # case:550e8400-...
parsed = GID.parse("case:550e8400-...")     # GID object
entity_type, uuid = parse_gid("case:...")   # ("case", UUID(...))
is_valid_gid("case:550e8400-...")           # True
```

## Enums

```python
# Evidence types
EvidenceType.DOCUMENT.description           # "Written documents and files"

# Research phases (with progress)
ResearchPhase.ANALYSIS.progress_percentage  # 50
ResearchPhase.COMPLETED.is_terminal         # True

# Research status
ResearchStatus.RUNNING.is_active            # True

# Confidence levels
confidence = ConfidenceLevel.from_score(0.85)  # VERY_HIGH
confidence.min_score                           # 0.8
confidence.max_score                           # 1.0

# Entity types
EntityType.PERSON.description               # "Person or individual"

# Chunk types
ChunkType.MICROBLOCK.typical_size           # "50-200 words"
```

## Exceptions

```python
# Entity not found
raise EntityNotFoundException(
    "Case", "123",
    context={"user_id": "user456"}
)

# Validation error
raise ValidationException(
    "Invalid email",
    field="email"
)

# Invalid operation
raise InvalidOperationException(
    "Cannot archive active case",
    context={"status": "ACTIVE"}
)

# Concurrency conflict
raise ConcurrencyException(
    "Case", "123",
    expected_version=5,
    actual_version=6
)

# Repository error
raise RepositoryException(
    "Database error",
    original_exception=db_error
)

# External service error
raise ExternalServiceException(
    "API call failed",
    "ollama",
    context={"status_code": 503}
)

# Serialize for API
exception.to_dict()  # {"type": "...", "message": "...", "context": {...}}
```

## Repository

```python
class CaseRepository(Repository[Case, CaseId]):
    def get(self, id: CaseId) -> Optional[Case]: ...
    def add(self, entity: Case) -> None: ...
    def save(self, entity: Case) -> None: ...
    def delete(self, entity: Case) -> None: ...
    def list(self, limit=100, offset=0, **filters) -> List[Case]: ...
    def count(self, **filters) -> int: ...
    def exists(self, id: CaseId) -> bool: ...
    def find_by(self, **criteria) -> Optional[Case]: ...
    def find_all_by(self, **criteria) -> List[Case]: ...

# Usage
repo = CaseRepository(db)
case = repo.get(case_id)
active = repo.find_all_by(status=CaseStatus.ACTIVE)
total = repo.count(status=CaseStatus.ACTIVE)
```

## Unit of Work

```python
class SqlAlchemyUnitOfWork(UnitOfWork):
    def __enter__(self): ...
    def __exit__(self, exc_type, exc_val, exc_tb): ...
    def commit(self): ...
    def rollback(self): ...
    def flush(self): ...

# Usage
with uow:
    case = uow.cases.get(case_id)
    case.status = CaseStatus.CLOSED
    uow.cases.save(case)
    uow.commit()
```

## Event Dispatcher

```python
@dataclass
class CaseCreated:
    event_id: str
    timestamp: datetime
    case_id: str

    def event_name(self) -> str:
        return "case.created"

    def aggregate_id(self) -> str:
        return self.case_id

# Register handler
dispatcher.register(CaseCreated, send_notification)

# Dispatch event
event = CaseCreated(...)
dispatcher.dispatch(event)

# Multiple events
dispatcher.dispatch_all([event1, event2])
```

## Common Patterns

### Create Entity with Validation
```python
def create_case(data: dict, uow: UnitOfWork) -> CaseId:
    if not data.get("name"):
        raise ValidationException("Name required", field="name")

    with uow:
        if uow.cases.find_by(case_number=data["case_number"]):
            raise ValidationException("Case number exists")

        case = Case(**data)
        uow.cases.add(case)
        uow.commit()

    return CaseId(case.id)
```

### Get Entity or Fail
```python
def get_case_or_fail(case_id: CaseId, uow: UnitOfWork) -> Case:
    with uow:
        case = uow.cases.get(case_id)
        if not case:
            raise EntityNotFoundException("Case", str(case_id))
        return case
```

### Update with Transaction
```python
def update_case(case_id: CaseId, updates: dict, uow: UnitOfWork) -> None:
    with uow:
        case = uow.cases.get(case_id)
        if not case:
            raise EntityNotFoundException("Case", str(case_id))

        if case.status == CaseStatus.ARCHIVED:
            raise InvalidOperationException("Cannot update archived case")

        for key, value in updates.items():
            setattr(case, key, value)

        uow.cases.save(case)
        uow.commit()
```

### Handle Exceptions in API
```python
@app.post("/cases")
async def create_case_endpoint(data: dict):
    try:
        case_id = create_case(data, uow)
        return {"case_id": str(case_id)}
    except ValidationException as e:
        return JSONResponse(
            status_code=422,
            content=e.to_dict()
        )
    except EntityNotFoundException as e:
        return JSONResponse(
            status_code=404,
            content=e.to_dict()
        )
```

## All Available Types

### Identifiers (7)
- CaseId, DocumentId, ResearchRunId, FindingId, EntityId, TranscriptionId, ChunkId

### Enums (8)
- EvidenceType (6 values)
- ResearchPhase (7 values)
- ResearchStatus (6 values)
- FindingType (5 values)
- EntityType (10 values)
- RelationshipType (10 values)
- ChunkType (4 values)
- ConfidenceLevel (5 values)

### Exceptions (8)
- DomainException, EntityNotFoundException, InvalidOperationException
- ValidationException, ConcurrencyException, InfrastructureException
- RepositoryException, ExternalServiceException

### Contracts (11)
- Repository, ReadOnlyRepository
- UnitOfWork, AsyncUnitOfWork, UnitOfWorkFactory, AsyncUnitOfWorkFactory
- EventDispatcher, AsyncEventDispatcher, DomainEvent
- EventStore, AsyncEventStore

## Total: 38 Components

See README.md for detailed documentation and EXAMPLES.md for comprehensive usage examples.
