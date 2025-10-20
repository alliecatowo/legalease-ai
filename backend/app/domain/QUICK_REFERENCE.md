# Domain Layer Quick Reference

## File Locations

### Evidence Domain
```
domain/evidence/
├── entities/
│   ├── document.py          # Document entity
│   ├── transcript.py        # Transcript entity
│   ├── communication.py     # Communication entity
│   └── forensic_report.py   # ForensicReport entity
├── value_objects/
│   ├── citation.py          # Citation value object
│   ├── locator.py           # Locator variants (Page, Timecode, Message, BoundingBox)
│   └── chunk.py             # Chunk value object
└── repositories/
    └── evidence_repository.py  # Repository interfaces
```

### Research Domain
```
domain/research/
├── entities/
│   ├── research_run.py      # ResearchRun entity
│   ├── finding.py           # Finding entity
│   ├── hypothesis.py        # Hypothesis entity
│   └── dossier.py           # Dossier entity
├── value_objects/
│   ├── query.py             # Query value object
│   ├── score.py             # Score value object
│   └── confidence.py        # Confidence value object
└── repositories/
    └── research_repository.py  # Repository interfaces
```

### Knowledge Domain
```
domain/knowledge/
├── entities/
│   ├── entity.py            # Entity entity (Person, Org, Location)
│   ├── event.py             # Event entity
│   └── relationship.py      # Relationship entity
├── value_objects/
│   ├── timeline.py          # Timeline value object
│   └── temporal_bounds.py   # TemporalBounds value object
└── repositories/
    └── graph_repository.py  # Repository interfaces
```

## Import Patterns

### Evidence Domain
```python
# Entities
from app.domain.evidence.entities import (
    Document, DocumentType, DocumentStatus,
    Transcript, TranscriptStatus, Speaker, TranscriptSegment,
    Communication, CommunicationType, CommunicationPlatform, Participant,
    ForensicReport, ReportType, ExtractionStatus, DeviceInfo, Finding,
)

# Value Objects
from app.domain.evidence.value_objects import (
    Citation, SourceType,
    PageLocator, TimecodeLocator, MessageLocator, BoundingBox,
    Chunk, ChunkType, EmbeddingsMetadata,
)

# Repository Interfaces
from app.domain.evidence.repositories import (
    DocumentRepository,
    TranscriptRepository,
    CommunicationRepository,
    ForensicReportRepository,
)
```

### Research Domain
```python
# Entities
from app.domain.research.entities import (
    ResearchRun, ResearchPhase, ResearchStatus,
    Finding, FindingType,
    Hypothesis,
    Dossier, DossierSection,
)

# Value Objects
from app.domain.research.value_objects import (
    Query, QueryType, QueryFilter,
    Score, ScoreComponent,
    Confidence, ConfidenceLevel,
)

# Repository Interfaces
from app.domain.research.repositories import (
    ResearchRunRepository,
    FindingRepository,
    HypothesisRepository,
    DossierRepository,
)
```

### Knowledge Domain
```python
# Entities
from app.domain.knowledge.entities import (
    Entity, EntityType,
    Event, EventType,
    Relationship, RelationshipType,
)

# Value Objects
from app.domain.knowledge.value_objects import (
    Timeline, TimelineGranularity,
    TemporalBounds, TemporalPrecision,
)

# Repository Interfaces
from app.domain.knowledge.repositories import (
    EntityRepository,
    EventRepository,
    RelationshipRepository,
    GraphRepository,
)
```

## Common Patterns

### Creating Entities

```python
from uuid import uuid4
from datetime import datetime

# Document
document = Document(
    id=uuid4(),
    case_id=case_id,
    filename="exhibit_a.pdf",
    file_type=DocumentType.EXHIBIT,
    mime_type="application/pdf",
    size=1024000,
    status=DocumentStatus.PENDING,
    created_at=datetime.utcnow(),
    file_path="/storage/path/file.pdf",
)
document.mark_processing()
document.mark_completed(metadata={"pages": 10})

# Transcript
transcript = Transcript(
    id=uuid4(),
    case_id=case_id,
    filename="interview.mp3",
    duration=3600.0,
    language="en",
    speakers=[Speaker(id="SPEAKER_00", name="Detective")],
    segments=[],
    status=TranscriptStatus.PENDING,
    created_at=datetime.utcnow(),
    file_path="/storage/path/audio.mp3",
    mime_type="audio/mpeg",
    size=5000000,
)

# ResearchRun
research = ResearchRun(
    id=uuid4(),
    case_id=case_id,
    status=ResearchStatus.PENDING,
    phase=ResearchPhase.INITIALIZING,
    query="Find timeline of contract negotiations",
    findings=[],
    config={"max_findings": 50},
)
research.start()
research.advance_to_searching()
```

### Creating Value Objects

```python
# Citation with PageLocator
citation = Citation(
    source_id=document_id,
    source_type=SourceType.DOCUMENT,
    locator=PageLocator(page=5, paragraph=2, bates_number="ACME-00123"),
    excerpt="The parties agreed to the following terms...",
    confidence=0.95,
)

# Citation with TimecodeLocator
citation = Citation(
    source_id=transcript_id,
    source_type=SourceType.TRANSCRIPT,
    locator=TimecodeLocator(start=125.5, end=130.2, segment_id="seg_001"),
    excerpt="I was there on March 15th",
    confidence=0.88,
)

# Query
query = Query(
    text="Find all communications about contract",
    query_type=QueryType.ENTITY_SEARCH,
    filters=[
        QueryFilter("entity_type", "eq", "PERSON"),
        QueryFilter("date", "between", ["2024-03-01", "2024-03-31"]),
    ],
    parameters={"max_results": 100},
)

# Confidence
confidence = Confidence(
    level=ConfidenceLevel.HIGH,
    reasoning="Supported by 3 independent sources with corroborating timestamps",
    supporting_evidence_count=3,
)
```

### Using Repository Interfaces

```python
# Dependency injection - implementation comes from infrastructure layer
class ResearchService:
    def __init__(
        self,
        research_repo: ResearchRunRepository,
        finding_repo: FindingRepository,
        document_repo: DocumentRepository,
    ):
        self.research_repo = research_repo
        self.finding_repo = finding_repo
        self.document_repo = document_repo

    async def start_research(self, case_id: UUID, query: str) -> ResearchRun:
        research = ResearchRun(
            id=uuid4(),
            case_id=case_id,
            status=ResearchStatus.PENDING,
            phase=ResearchPhase.INITIALIZING,
            query=query,
            findings=[],
            config={},
        )
        research.start()
        return await self.research_repo.save(research)
```

## Validation Rules

### Entities
- All entities have UUID `id` field
- Entities are mutable (standard `@dataclass`)
- Entities implement `__eq__` and `__hash__` based on ID
- Business logic methods modify state

### Value Objects
- Value objects are immutable (`@dataclass(frozen=True)`)
- Validation in `__post_init__` method
- No identity field (ID)
- Equality based on all attributes

### Repository Interfaces
- Use `ABC` (Abstract Base Class)
- All methods are `async` for async/await pattern
- Return `Optional[Entity]` for single results
- Return `List[Entity]` for multiple results
- Save operations return the saved entity
- Delete operations return `bool` (success/failure)

## Enum Values Reference

### DocumentType
- PLEADING, EXHIBIT, CORRESPONDENCE, DISCOVERY, COURT_ORDER, BRIEF, MOTION, DEPOSITION, CONTRACT, EVIDENCE, OTHER

### DocumentStatus / TranscriptStatus
- PENDING, PROCESSING, COMPLETED, FAILED

### CommunicationType
- SMS, MMS, EMAIL, CHAT, SOCIAL_MEDIA, VOICE_CALL, VIDEO_CALL, OTHER

### CommunicationPlatform
- WHATSAPP, IMESSAGE, TELEGRAM, SIGNAL, FACEBOOK, INSTAGRAM, TWITTER, SNAPCHAT, SMS_NATIVE, EMAIL_NATIVE, SKYPE, SLACK, TEAMS, UNKNOWN

### EntityType
- PERSON, ORGANIZATION, LOCATION, EVENT, DATE, MONEY, LEGAL_TERM, CASE_NUMBER, STATUTE, OTHER

### EventType
- MEETING, COMMUNICATION, TRANSACTION, AGREEMENT, LEGAL_ACTION, INCIDENT, DEADLINE, OTHER

### RelationshipType
- WORKS_FOR, EMPLOYED_BY, OWNS, PARTNER_OF, FAMILY_OF, KNOWS, LOCATED_AT, PARTY_TO, SIGNED, COMMUNICATED_WITH, ATTENDED, OTHER

### FindingType
- FACT, PATTERN, ANOMALY, RELATIONSHIP, TIMELINE_EVENT, CONTRADICTION, CORROBORATION, GAP

### ResearchPhase
- INITIALIZING, INDEXING, SEARCHING, ANALYZING, HYPOTHESIS_GENERATION, DOSSIER_GENERATION, COMPLETED

### ResearchStatus
- PENDING, RUNNING, COMPLETED, FAILED, CANCELLED

### ConfidenceLevel
- VERY_HIGH (0.9-1.0), HIGH (0.7-0.89), MEDIUM (0.5-0.69), LOW (0.3-0.49), VERY_LOW (0.0-0.29)
