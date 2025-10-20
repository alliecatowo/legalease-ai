# Shared Module Usage Examples

This document provides practical examples of using the shared module components.

## Table of Contents
1. [Type-Safe Identifiers](#type-safe-identifiers)
2. [Domain Enumerations](#domain-enumerations)
3. [Exception Handling](#exception-handling)
4. [Repository Pattern](#repository-pattern)
5. [Unit of Work Pattern](#unit-of-work-pattern)
6. [Event Dispatcher Pattern](#event-dispatcher-pattern)

## Type-Safe Identifiers

### Basic Usage

```python
from uuid import uuid4
from app.shared import CaseId, DocumentId, generate_id

# Generate new IDs
case_id = CaseId(generate_id())
doc_id = DocumentId(generate_id())

# Type checker prevents mixing types
def get_case(case_id: CaseId) -> Case:
    return db.query(Case).filter_by(id=case_id).first()

# This works
case = get_case(case_id)

# This would be caught by type checker
# case = get_case(doc_id)  # Error: Expected CaseId, got DocumentId
```

### Global Identifiers (GID)

```python
from app.shared import GID, parse_gid, is_valid_gid

# Create GID with auto-generated UUID
gid = GID.create("case")
print(gid)  # case:550e8400-e29b-41d4-a716-446655440000

# Create GID with specific UUID
from uuid import uuid4
specific_id = uuid4()
gid = GID.create("document", specific_id)

# Parse GID string
gid_str = "case:550e8400-e29b-41d4-a716-446655440000"
parsed = GID.parse(gid_str)
print(parsed.entity_type)  # "case"
print(parsed.id)  # UUID('550e8400-e29b-41d4-a716-446655440000')

# Quick parsing
entity_type, uuid = parse_gid(gid_str)

# Validation
if is_valid_gid(gid_str):
    print("Valid GID format")

# Use in API responses
{
    "id": str(gid),
    "entity_type": gid.entity_type,
    "uuid": str(gid.id)
}
```

## Domain Enumerations

### Evidence Types

```python
from app.shared import EvidenceType

evidence_type = EvidenceType.TRANSCRIPT
print(evidence_type.description)  # "Audio/video transcriptions"

# Use in conditional logic
if evidence_type == EvidenceType.TRANSCRIPT:
    process_transcript(file)
elif evidence_type == EvidenceType.DOCUMENT:
    process_document(file)
```

### Research Phases with Progress

```python
from app.shared import ResearchPhase

phase = ResearchPhase.ANALYSIS

# Get progress information
print(phase.description)  # "Analyzing findings and patterns"
print(phase.progress_percentage)  # 50
print(phase.is_terminal)  # False

# Track research progress
def get_research_status(phase: ResearchPhase) -> dict:
    return {
        "phase": phase.value,
        "description": phase.description,
        "progress": phase.progress_percentage,
        "is_complete": phase.is_terminal
    }

# Phase transitions
current_phase = ResearchPhase.DISCOVERY
if should_advance():
    current_phase = ResearchPhase.PLANNING
```

### Confidence Levels

```python
from app.shared import ConfidenceLevel

# Convert ML scores to confidence levels
ml_score = 0.85
confidence = ConfidenceLevel.from_score(ml_score)
print(confidence)  # ConfidenceLevel.VERY_HIGH

# Use in filtering
min_confidence = ConfidenceLevel.HIGH
if confidence.min_score >= min_confidence.min_score:
    include_result()

# Display to users
print(confidence.description)  # "Very high confidence (80-100%)"
```

### Entity and Relationship Types

```python
from app.shared import EntityType, RelationshipType

# Entity extraction
entity_type = EntityType.PERSON
print(entity_type.description)  # "Person or individual"

# Knowledge graph relationships
relationship = RelationshipType.WORKS_FOR
print(relationship.description)  # "Works for or employed by"

# Build knowledge graph
entities = [
    {"name": "John Doe", "type": EntityType.PERSON},
    {"name": "Acme Corp", "type": EntityType.ORGANIZATION}
]
relationships = [
    {
        "from": "John Doe",
        "to": "Acme Corp",
        "type": RelationshipType.WORKS_FOR
    }
]
```

## Exception Handling

### Entity Not Found

```python
from app.shared import EntityNotFoundException

def get_case_or_fail(case_id: str) -> Case:
    case = db.query(Case).filter_by(id=case_id).first()
    if not case:
        raise EntityNotFoundException(
            "Case",
            case_id,
            context={"user_id": current_user.id}
        )
    return case

# In API handler
try:
    case = get_case_or_fail(case_id)
    return {"case": case.to_dict()}
except EntityNotFoundException as e:
    return JSONResponse(
        status_code=404,
        content=e.to_dict()
    )
```

### Validation Errors

```python
from app.shared import ValidationException

def create_case(data: dict) -> Case:
    # Single field validation
    if not data.get("name"):
        raise ValidationException(
            "Case name is required",
            field="name"
        )

    # Multiple validation errors
    errors = []
    if not data.get("name"):
        errors.append({"field": "name", "error": "required"})
    if not data.get("case_number"):
        errors.append({"field": "case_number", "error": "required"})

    if errors:
        raise ValidationException(
            "Validation failed",
            context={"errors": errors}
        )

    return Case(**data)

# In API handler
try:
    case = create_case(request.json)
    return {"case": case.to_dict()}
except ValidationException as e:
    return JSONResponse(
        status_code=422,
        content=e.to_dict()
    )
```

### Invalid Operations

```python
from app.shared import InvalidOperationException

def archive_case(case: Case) -> None:
    if case.status == CaseStatus.ACTIVE:
        raise InvalidOperationException(
            "Cannot archive an active case",
            context={
                "case_id": str(case.id),
                "status": case.status.value
            }
        )

    case.status = CaseStatus.ARCHIVED
    case.archived_at = datetime.utcnow()
    db.commit()
```

### Concurrency Conflicts

```python
from app.shared import ConcurrencyException

class VersionedCase(Case):
    version = Column(Integer, default=1)

def update_case_with_optimistic_locking(case_id: str, updates: dict) -> None:
    expected_version = updates.pop("version")

    case = db.query(VersionedCase).filter_by(id=case_id).first()

    if case.version != expected_version:
        raise ConcurrencyException(
            "Case",
            case_id,
            expected_version=expected_version,
            actual_version=case.version
        )

    for key, value in updates.items():
        setattr(case, key, value)
    case.version += 1
    db.commit()

# In API handler
try:
    update_case_with_optimistic_locking(case_id, request.json)
    return {"success": True}
except ConcurrencyException as e:
    return JSONResponse(
        status_code=409,
        content={
            "error": "Conflict",
            "message": str(e),
            "retry": True
        }
    )
```

## Repository Pattern

### Implementing a Repository

```python
from typing import Optional, List
from app.shared import Repository, CaseId, EntityNotFoundException
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

        # Apply filters
        if 'status' in filters:
            query = query.filter_by(status=filters['status'])
        if 'client' in filters:
            query = query.filter(Case.client.ilike(f"%{filters['client']}%"))

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

### Using a Repository

```python
# Initialize
db = SessionLocal()
case_repo = CaseRepository(db)

# Get by ID
case_id = CaseId(uuid4())
case = case_repo.get(case_id)
if not case:
    raise EntityNotFoundException("Case", str(case_id))

# Add new entity
new_case = Case(name="New Case", case_number="2024-001")
case_repo.add(new_case)
db.commit()

# Update entity
case.status = CaseStatus.CLOSED
case_repo.save(case)
db.commit()

# Delete entity
case_repo.delete(case)
db.commit()

# List with filters
active_cases = case_repo.list(
    limit=10,
    offset=0,
    status=CaseStatus.ACTIVE
)

# Count
total_active = case_repo.count(status=CaseStatus.ACTIVE)

# Find by criteria
case = case_repo.find_by(case_number="2024-001")
all_client_cases = case_repo.find_all_by(client="Acme Corp")
```

## Unit of Work Pattern

### Implementing Unit of Work

```python
from app.shared import UnitOfWork

class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.session = None

    def __enter__(self):
        self.session = self.session_factory()
        # Initialize repositories
        self.cases = CaseRepository(self.session)
        self.documents = DocumentRepository(self.session)
        self.entities = EntityRepository(self.session)
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
```

### Using Unit of Work

```python
# Create factory
from sqlalchemy.orm import sessionmaker
session_factory = sessionmaker(bind=engine)
uow_factory = lambda: SqlAlchemyUnitOfWork(session_factory)

# Simple transaction
with uow_factory() as uow:
    case = Case(name="Test Case", case_number="2024-001")
    uow.cases.add(case)
    uow.commit()

# Complex transaction with multiple operations
def create_case_with_documents(
    case_data: dict,
    document_files: List[UploadFile]
) -> CaseId:
    with uow_factory() as uow:
        # Create case
        case = Case(**case_data)
        uow.cases.add(case)
        uow.flush()  # Get case.id

        # Create documents
        for file in document_files:
            doc = Document(
                case_id=case.id,
                filename=file.filename,
                size=file.size
            )
            uow.documents.add(doc)

        # All or nothing
        uow.commit()
        return CaseId(case.id)

# Transaction with rollback on error
with uow_factory() as uow:
    case = uow.cases.get(case_id)
    case.status = CaseStatus.CLOSED

    if not validate_can_close(case):
        uow.rollback()
        raise InvalidOperationException("Cannot close case")

    uow.commit()
```

## Event Dispatcher Pattern

### Implementing Event Dispatcher

```python
from typing import Dict, List, Any
from app.shared import EventDispatcher, EventHandler

class InMemoryEventDispatcher(EventDispatcher):
    def __init__(self):
        self._handlers: Dict[type, List[EventHandler]] = {}

    def register(self, event_type: type, handler: EventHandler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unregister(self, event_type: type, handler: EventHandler) -> None:
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)

    def dispatch(self, event: Any) -> None:
        event_type = type(event)
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                handler(event)

    def dispatch_all(self, events: List[Any]) -> None:
        for event in events:
            self.dispatch(event)
```

### Defining Domain Events

```python
from dataclasses import dataclass
from datetime import datetime
from app.shared import DomainEvent

@dataclass
class CaseCreated:
    event_id: str
    timestamp: datetime
    case_id: str
    case_number: str
    client: str

    def event_name(self) -> str:
        return "case.created"

    def aggregate_id(self) -> str:
        return self.case_id

@dataclass
class DocumentAdded:
    event_id: str
    timestamp: datetime
    case_id: str
    document_id: str
    filename: str

    def event_name(self) -> str:
        return "document.added"

    def aggregate_id(self) -> str:
        return self.case_id
```

### Using Event Dispatcher

```python
# Initialize dispatcher
dispatcher = InMemoryEventDispatcher()

# Define handlers
def send_notification(event: CaseCreated) -> None:
    print(f"Sending notification: Case {event.case_number} created")

def update_search_index(event: CaseCreated) -> None:
    print(f"Indexing case {event.case_id} in search engine")

def log_audit_trail(event: CaseCreated) -> None:
    print(f"Logging: {event.event_name()} at {event.timestamp}")

# Register handlers
dispatcher.register(CaseCreated, send_notification)
dispatcher.register(CaseCreated, update_search_index)
dispatcher.register(CaseCreated, log_audit_trail)

# Dispatch events
event = CaseCreated(
    event_id=str(generate_id()),
    timestamp=datetime.utcnow(),
    case_id="123",
    case_number="2024-001",
    client="Acme Corp"
)
dispatcher.dispatch(event)

# Dispatch multiple events
events = [
    CaseCreated(...),
    DocumentAdded(...),
]
dispatcher.dispatch_all(events)
```

### Integrating with Domain Logic

```python
class CaseService:
    def __init__(self, uow: UnitOfWork, dispatcher: EventDispatcher):
        self.uow = uow
        self.dispatcher = dispatcher

    def create_case(self, data: dict) -> CaseId:
        with self.uow:
            # Create case
            case = Case(**data)
            self.uow.cases.add(case)
            self.uow.flush()

            # Dispatch event
            event = CaseCreated(
                event_id=str(generate_id()),
                timestamp=datetime.utcnow(),
                case_id=str(case.id),
                case_number=case.case_number,
                client=case.client
            )

            self.uow.commit()

            # Only dispatch after successful commit
            self.dispatcher.dispatch(event)

            return CaseId(case.id)
```
