# Domain Layer - LegalEase

This directory contains the core business logic organized using **Domain-Driven Design (DDD)** and **Hexagonal Architecture** principles.

## Architecture Overview

The domain layer is completely independent of infrastructure concerns (databases, APIs, external services). It defines:

- **Entities**: Objects with identity and lifecycle
- **Value Objects**: Immutable objects defined by their attributes
- **Repository Interfaces**: Abstract ports for data persistence
- **Domain Services**: Complex business logic that doesn't belong to a single entity

## Domain Organization

### Evidence Domain (`evidence/`)

Manages legal evidence including documents, transcripts, communications, and forensic reports.

#### Entities
- **Document**: Legal documents (pleadings, exhibits, discovery, etc.)
- **Transcript**: Audio/video transcriptions with speaker identification
- **Communication**: Digital messages from forensic exports (Cellebrite)
- **ForensicReport**: Forensic examination reports with findings

#### Value Objects
- **Citation**: References to specific evidence locations
- **Locator**: Location within evidence (page, timecode, message, bounding box)
- **Chunk**: Text segments with embeddings metadata

#### Repository Interfaces
- **DocumentRepository**: Document persistence operations
- **TranscriptRepository**: Transcript persistence operations
- **CommunicationRepository**: Communication persistence operations
- **ForensicReportRepository**: Forensic report persistence operations

### Research Domain (`research/`)

Orchestrates AI-powered deep research sessions to analyze evidence and generate insights.

#### Entities
- **ResearchRun**: Deep research session with phases and configuration
- **Finding**: Discovered facts, patterns, or insights from analysis
- **Hypothesis**: Testable theories generated from findings
- **Dossier**: Final research document with executive summary and sections

#### Value Objects
- **Query**: Structured research query with filters and parameters
- **Score**: Composite scoring with components and methodology
- **Confidence**: Confidence levels with reasoning and evidence counts

#### Repository Interfaces
- **ResearchRunRepository**: Research run persistence operations
- **FindingRepository**: Finding persistence operations
- **HypothesisRepository**: Hypothesis persistence operations
- **DossierRepository**: Dossier persistence operations

### Knowledge Domain (`knowledge/`)

Represents the knowledge graph of entities, events, and relationships.

#### Entities
- **Entity**: People, organizations, locations in the knowledge graph
- **Event**: Temporal occurrences with participants and locations
- **Relationship**: Connections between entities with temporal bounds

#### Value Objects
- **Timeline**: Chronological sequence of events
- **TemporalBounds**: Time ranges with precision indicators

#### Repository Interfaces
- **EntityRepository**: Entity persistence operations
- **EventRepository**: Event persistence operations
- **RelationshipRepository**: Relationship persistence operations
- **GraphRepository**: Complex graph traversal and query operations

## Design Principles

### 1. Entities vs Value Objects

**Entities** have:
- Identity (ID field)
- Lifecycle
- Mutable state
- Business logic methods

**Value Objects** have:
- No identity (defined by attributes)
- Immutable (`frozen=True`)
- Validation in `__post_init__`
- Helper methods for queries

### 2. Repository Pattern (Hexagonal Architecture)

Repositories are **abstract interfaces** (ports) that define data operations without implementation details:

```python
class DocumentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[Document]:
        pass
```

Implementations (adapters) live in the infrastructure layer and can be:
- PostgreSQL with SQLAlchemy
- MongoDB
- In-memory for testing
- Any other storage mechanism

### 3. Type Safety

All domain code uses:
- Type hints on every function/method
- Dataclasses for structure
- Enums for categorical values
- Validation in `__post_init__` methods

### 4. SOLID Principles

- **Single Responsibility**: Each entity/value object has one clear purpose
- **Open/Closed**: Extend through composition, not modification
- **Liskov Substitution**: Repository interfaces are substitutable
- **Interface Segregation**: Specific repository interfaces per entity type
- **Dependency Inversion**: Domain depends on abstractions (repository interfaces)

## Usage Examples

### Creating a Document Entity

```python
from uuid import uuid4
from datetime import datetime
from app.domain.evidence.entities import Document, DocumentType, DocumentStatus

document = Document(
    id=uuid4(),
    case_id=uuid4(),
    filename="complaint.pdf",
    file_type=DocumentType.PLEADING,
    mime_type="application/pdf",
    size=1024000,
    status=DocumentStatus.PENDING,
    created_at=datetime.utcnow(),
    file_path="/storage/case123/complaint.pdf",
)

# Use domain methods
document.mark_processing()
document.mark_completed(metadata={"pages": 25, "extracted_text": True})
```

### Creating a Citation Value Object

```python
from uuid import uuid4
from app.domain.evidence.value_objects import Citation, SourceType, PageLocator

citation = Citation(
    source_id=uuid4(),
    source_type=SourceType.DOCUMENT,
    locator=PageLocator(page=5, paragraph=2),
    excerpt="The defendant signed the agreement on March 15, 2024.",
    confidence=0.95,
)

# Value objects are immutable
assert citation.is_high_confidence()
assert citation.has_excerpt()
```

### Using Repository Interface

```python
from app.domain.evidence.repositories import DocumentRepository

class PostgresDocumentRepository(DocumentRepository):
    """Concrete implementation using PostgreSQL"""

    async def get_by_id(self, id: UUID) -> Optional[Document]:
        # Implementation details hidden from domain
        row = await self.db.execute(select(DocumentModel).where(...))
        return self._to_domain_entity(row)
```

## Testing Strategy

Domain entities and value objects are **pure Python** with no infrastructure dependencies, making them easy to test:

```python
def test_document_lifecycle():
    doc = Document(
        id=uuid4(),
        case_id=uuid4(),
        filename="test.pdf",
        file_type=DocumentType.EXHIBIT,
        mime_type="application/pdf",
        size=1000,
        status=DocumentStatus.PENDING,
        created_at=datetime.utcnow(),
        file_path="/test.pdf",
    )

    doc.mark_processing()
    assert doc.status == DocumentStatus.PROCESSING

    doc.mark_completed()
    assert doc.is_processed()
```

## Migration from Current Models

The existing `/app/models/` directory contains SQLAlchemy ORM models mixed with business logic. The domain layer separates these concerns:

**Before** (mixed concerns):
```python
class Document(Base):
    id = Column(UUID, primary_key=True)
    filename = Column(String)
    # SQLAlchemy specific details mixed with domain
```

**After** (separated):
```python
# Domain entity (pure business logic)
@dataclass
class Document:
    id: UUID
    filename: str
    def mark_completed(self): ...

# Infrastructure adapter (SQLAlchemy details)
class DocumentModel(Base):
    __tablename__ = "documents"
    id = Column(UUID, primary_key=True)
```

## Next Steps

1. **Implement Adapters**: Create concrete repository implementations in `infrastructure/`
2. **Domain Services**: Add complex business logic services
3. **Event Sourcing**: Consider domain events for audit trails
4. **Aggregate Roots**: Define aggregate boundaries for transactional consistency
5. **Specification Pattern**: For complex query logic

## References

- [Domain-Driven Design by Eric Evans](https://www.domainlanguage.com/ddd/)
- [Hexagonal Architecture by Alistair Cockburn](https://alistair.cockburn.us/hexagonal-architecture/)
- [Python Dataclasses](https://docs.python.org/3/library/dataclasses.html)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
