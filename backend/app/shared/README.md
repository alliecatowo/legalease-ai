# Shared Module

This module provides shared types, exceptions, and contracts used throughout the application for consistency and type safety.

## Structure

```
shared/
├── __init__.py              # Main exports
├── types/                   # Type definitions
│   ├── identifiers.py      # Type-safe identifiers and GID
│   └── enums.py            # Domain enumerations
├── exceptions/              # Exception hierarchy
│   └── domain_exceptions.py
└── contracts/               # Protocol definitions
    ├── repository.py        # Repository protocol
    ├── unit_of_work.py      # Unit of Work protocol
    └── event_dispatcher.py  # Event dispatcher protocol
```

## Components

### 1. Identifiers (`types/identifiers.py`)

Type-safe identifiers using `NewType` for compile-time checking:

```python
from app.shared import CaseId, DocumentId, generate_id, GID

# Type-safe IDs
case_id = CaseId(generate_id())
doc_id = DocumentId(generate_id())

# GID (Global Identifier)
gid = GID.create("case", case_id)
print(gid)  # case:550e8400-e29b-41d4-a716-446655440000

parsed = GID.parse("case:550e8400-e29b-41d4-a716-446655440000")
assert parsed.entity_type == "case"
```

Available identifiers:
- `CaseId` - Case identifiers
- `DocumentId` - Document identifiers
- `ResearchRunId` - Research run identifiers
- `FindingId` - Finding identifiers
- `EntityId` - Knowledge graph entity identifiers
- `TranscriptionId` - Transcription identifiers
- `ChunkId` - Chunk identifiers

### 2. Enumerations (`types/enums.py`)

Domain enums with descriptive values and helper methods:

```python
from app.shared import EvidenceType, ResearchPhase, ConfidenceLevel

# Evidence types
evidence = EvidenceType.DOCUMENT
print(evidence.description)  # "Written documents and files"

# Research phases with progress tracking
phase = ResearchPhase.ANALYSIS
print(phase.progress_percentage)  # 50
print(phase.is_terminal)  # False

# Confidence levels from scores
confidence = ConfidenceLevel.from_score(0.85)
assert confidence == ConfidenceLevel.VERY_HIGH
```

Available enums:
- `EvidenceType` - Types of evidence (DOCUMENT, TRANSCRIPT, etc.)
- `ResearchPhase` - Research pipeline phases (DISCOVERY, ANALYSIS, etc.)
- `ResearchStatus` - Research execution status (PENDING, RUNNING, etc.)
- `FindingType` - Types of research findings (FACT, QUOTE, etc.)
- `EntityType` - Named entity types (PERSON, ORGANIZATION, etc.)
- `RelationshipType` - Entity relationship types (KNOWS, WORKS_FOR, etc.)
- `ChunkType` - Text chunk types (SUMMARY, SECTION, etc.)
- `ConfidenceLevel` - ML confidence levels (VERY_LOW to VERY_HIGH)

### 3. Exceptions (`exceptions/domain_exceptions.py`)

Hierarchical exception system with context:

```python
from app.shared import (
    EntityNotFoundException,
    ValidationException,
    InvalidOperationException,
    ConcurrencyException,
)

# Entity not found
raise EntityNotFoundException("Case", "123")

# Validation errors
raise ValidationException(
    "Invalid email format",
    context={"field": "email", "value": "invalid"}
)

# Business rule violations
raise InvalidOperationException(
    "Cannot archive an active case",
    context={"case_id": "123", "status": "ACTIVE"}
)

# Concurrency conflicts
raise ConcurrencyException(
    "Case", "123",
    expected_version=5,
    actual_version=6
)
```

Exception hierarchy:
- `DomainException` - Base for domain errors
  - `EntityNotFoundException` - Entity not found
  - `InvalidOperationException` - Invalid business operation
  - `ValidationException` - Validation errors
  - `ConcurrencyException` - Optimistic locking conflicts
- `InfrastructureException` - Base for infrastructure errors
  - `RepositoryException` - Database/persistence errors
  - `ExternalServiceException` - External service failures

### 4. Repository Contract (`contracts/repository.py`)

Generic repository protocol for data access:

```python
from typing import Optional, List
from app.shared import Repository, CaseId
from app.models import Case

class CaseRepository(Repository[Case, CaseId]):
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: CaseId) -> Optional[Case]:
        return self.db.query(Case).filter_by(id=id).first()

    def add(self, entity: Case) -> None:
        self.db.add(entity)

    def save(self, entity: Case) -> None:
        self.db.merge(entity)

    def delete(self, entity: Case) -> None:
        self.db.delete(entity)

    def list(self, limit: int = 100, offset: int = 0, **filters) -> List[Case]:
        query = self.db.query(Case)
        if 'status' in filters:
            query = query.filter_by(status=filters['status'])
        return query.limit(limit).offset(offset).all()

    def count(self, **filters) -> int:
        query = self.db.query(Case)
        if 'status' in filters:
            query = query.filter_by(status=filters['status'])
        return query.count()

    def exists(self, id: CaseId) -> bool:
        return self.db.query(Case).filter_by(id=id).count() > 0

    def find_by(self, **criteria) -> Optional[Case]:
        return self.db.query(Case).filter_by(**criteria).first()

    def find_all_by(self, **criteria) -> List[Case]:
        return self.db.query(Case).filter_by(**criteria).all()
```

### 5. Unit of Work Contract (`contracts/unit_of_work.py`)

Transaction management protocol:

```python
from app.shared import UnitOfWork

class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.session = None

    def __enter__(self):
        self.session = self.session_factory()
        self.cases = CaseRepository(self.session)
        self.documents = DocumentRepository(self.session)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        self.session.close()

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()

    def flush(self):
        self.session.flush()

# Usage
with uow:
    case = uow.cases.get(case_id)
    case.status = CaseStatus.CLOSED
    uow.cases.save(case)
    uow.commit()
```

### 6. Event Dispatcher Contract (`contracts/event_dispatcher.py`)

Event publishing protocol:

```python
from dataclasses import dataclass
from datetime import datetime
from app.shared import EventDispatcher, DomainEvent

@dataclass
class CaseCreated:
    event_id: str
    timestamp: datetime
    case_id: str
    case_number: str

    def event_name(self) -> str:
        return "case.created"

    def aggregate_id(self) -> str:
        return self.case_id

# Register handlers
def send_notification(event: CaseCreated):
    print(f"Sending notification for {event.case_number}")

dispatcher.register(CaseCreated, send_notification)

# Dispatch events
event = CaseCreated(
    event_id=str(generate_id()),
    timestamp=datetime.utcnow(),
    case_id="123",
    case_number="2024-001"
)
dispatcher.dispatch(event)
```

## Usage Examples

### Complete Example: Creating a Case

```python
from uuid import UUID
from app.shared import (
    CaseId, generate_id, GID,
    EntityNotFoundException, ValidationException,
    UnitOfWork,
)
from app.models import Case

def create_case(
    name: str,
    case_number: str,
    uow: UnitOfWork
) -> CaseId:
    # Validate input
    if not name or not case_number:
        raise ValidationException(
            "Case name and number are required",
            context={"name": name, "case_number": case_number}
        )

    # Create entity
    case = Case(
        name=name,
        case_number=case_number,
        status=CaseStatus.ACTIVE
    )

    # Persist with unit of work
    with uow:
        # Check for duplicates
        existing = uow.cases.find_by(case_number=case_number)
        if existing:
            raise ValidationException(
                f"Case number {case_number} already exists"
            )

        # Add and commit
        uow.cases.add(case)
        uow.commit()

    return CaseId(case.id)
```

### Type-Safe Querying

```python
def get_case_or_fail(case_id: CaseId, uow: UnitOfWork) -> Case:
    with uow:
        case = uow.cases.get(case_id)
        if not case:
            raise EntityNotFoundException("Case", str(case_id))
        return case

def list_active_cases(uow: UnitOfWork) -> List[Case]:
    with uow:
        return uow.cases.find_all_by(status=CaseStatus.ACTIVE)
```

## Design Principles

1. **Type Safety**: Use `NewType` for identifiers to catch errors at compile time
2. **Descriptive Enums**: All enums have `description` properties for UI display
3. **Rich Exceptions**: Include context dictionaries for debugging
4. **Protocol-Based**: Use `typing.Protocol` for dependency injection
5. **Comprehensive Docs**: All components have docstrings with examples

## Testing

Import validation:
```bash
cd backend
python -c "from app.shared import *; print('All imports successful')"
```

Basic functionality:
```python
from app.shared import *

# Test identifiers
case_id = CaseId(generate_id())
gid = GID.create("case")

# Test enums
confidence = ConfidenceLevel.from_score(0.85)
assert confidence == ConfidenceLevel.VERY_HIGH

# Test exceptions
try:
    raise EntityNotFoundException("Case", "123")
except EntityNotFoundException as e:
    print(e.to_dict())
```
