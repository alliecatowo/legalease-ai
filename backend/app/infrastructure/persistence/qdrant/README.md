# Qdrant Vector Database Integration

This package provides a comprehensive Qdrant vector database integration for LegalEase, following hexagonal architecture principles.

## Architecture

The implementation follows the repository pattern with clean separation of concerns:

```
qdrant/
├── client.py                    # Enhanced async Qdrant client
├── collection_manager.py        # Collection schema management
└── repositories/
    ├── base.py                  # Abstract base repository
    ├── document.py              # Document vector operations
    ├── transcript.py            # Transcript vector operations
    ├── communication.py         # Communication vector operations
    └── finding.py               # Finding vector operations
```

## Collections

### 1. legalease_documents
Stores hierarchical document embeddings with three levels of granularity:

**Vectors:**
- `summary`: High-level document understanding (768 dims)
- `section`: Section-level semantic search (768 dims)
- `microblock`: Fine-grained passage retrieval (768 dims)
- `bm25`: Sparse BM25 vectors for keyword matching

**Payload:**
- `case_id`: Case UUID
- `document_id`: Document UUID
- `chunk_type`: Type of chunk (PARAGRAPH, PAGE, SECTION, etc.)
- `position`: Sequential position in document
- `text`: Chunk text content
- `word_count`, `char_count`: Size metrics
- Additional metadata from chunk

**Use Cases:**
- Semantic document search across cases
- Citation retrieval with precise locations
- Multi-level granularity search (document → section → paragraph)

### 2. legalease_transcripts
Stores transcript segment embeddings with temporal and speaker information:

**Vectors:**
- `dense`: Semantic embeddings of segments (768 dims)
- `bm25`: Sparse BM25 vectors

**Payload:**
- `case_id`: Case UUID
- `transcript_id`: Transcript UUID
- `segment_id`: Segment identifier
- `start_time`, `end_time`, `duration`: Temporal bounds
- `text`: Segment text
- `speaker_id`, `speaker_name`, `speaker_confidence`: Speaker info
- `transcription_confidence`: ASR confidence score
- `segment_type`: SPEECH, SILENCE, MUSIC, NOISE

**Use Cases:**
- Search by speaker ("What did John Doe say about the contract?")
- Temporal search ("Find mentions of payment in the first 10 minutes")
- Speaker-specific analysis

### 3. legalease_communications
Stores communication embeddings from forensic exports (Cellebrite):

**Vectors:**
- `dense`: Semantic embeddings (768 dims)
- `bm25`: Sparse BM25 vectors

**Payload:**
- `case_id`: Case UUID
- `communication_id`: Communication UUID
- `thread_id`: Thread/conversation identifier
- `sender_id`, `sender_name`: Sender information
- `participant_ids`, `participant_names`: All participants
- `timestamp`, `timestamp_unix`: When sent
- `body`: Message content
- `platform`: WHATSAPP, IMESSAGE, TELEGRAM, etc.
- `communication_type`: SMS, EMAIL, CHAT, etc.
- `device_id`: Source device
- `has_attachments`, `attachment_count`: Attachment info

**Use Cases:**
- Search communications by content
- Thread-based retrieval
- Participant-based filtering
- Platform-specific analysis
- Timeline reconstruction

### 4. legalease_findings
Stores research finding embeddings for deduplication and retrieval:

**Vectors:**
- `dense`: Semantic embeddings (768 dims)
- `bm25`: Sparse BM25 vectors

**Payload:**
- `finding_id`: Finding UUID
- `research_run_id`: Research run UUID
- `finding_type`: FACT, PATTERN, ANOMALY, RELATIONSHIP, etc.
- `text`: Finding description
- `entity_ids`: Referenced entity UUIDs
- `citation_ids`: Supporting citation UUIDs
- `confidence`: Confidence score (0.0-1.0)
- `relevance`: Relevance score (0.0-1.0)
- `tags`: Categorical tags

**Use Cases:**
- Finding deduplication (similarity threshold 0.9)
- Entity-based finding retrieval
- Research run analysis
- High-confidence finding filtering

## Components

### Enhanced Qdrant Client

`EnhancedQdrantClient` provides:
- Async operations throughout
- Lazy connection initialization
- Connection pooling via AsyncQdrantClient
- Health checks
- Multiple collection management
- Proper error handling with custom exceptions

```python
from app.infrastructure.persistence.qdrant import get_qdrant_client

client = get_qdrant_client()

# Health check
is_healthy = await client.health_check()

# Get collection info
info = await client.get_collection_info("legalease_documents")

# Context manager for direct operations
async with client.get_client() as qdrant:
    results = await qdrant.search(...)
```

### Collection Manager

`CollectionManager` centralizes collection schema definitions:

```python
from app.infrastructure.persistence.qdrant import CollectionManager

# Create all collections
await CollectionManager.create_all_collections(recreate=False)

# Create specific collection
await CollectionManager.create_document_collection()

# Get stats for all collections
stats = await CollectionManager.get_collection_stats()
```

### Base Repository

`BaseQdrantRepository` provides common operations:

**Methods:**
- `upsert_points(points, batch_size=100)`: Batch upsert with error handling
- `search_hybrid(query_vectors, sparse_vector, filters, top_k)`: Hybrid search with RRF
- `delete_by_ids(point_ids)`: Delete by IDs
- `delete_by_filter(filter_conditions)`: Delete by filter
- `build_filter(case_ids, document_ids, conditions)`: Build Qdrant filters

**Reciprocal Rank Fusion (RRF):**
Combines results from multiple vector searches using the formula:
```
RRF_score = Σ (1 / (k + rank))
```
where k=60 by default. This provides better results than simple score averaging.

### Repository Implementations

#### QdrantDocumentRepository

```python
from app.infrastructure.persistence.qdrant import QdrantDocumentRepository

repo = QdrantDocumentRepository()

# Index a document
await repo.index_document(
    document_id=doc_uuid,
    case_id=case_uuid,
    chunks=chunks,
    embeddings={
        "summary": summary_vectors,
        "section": section_vectors,
        "microblock": microblock_vectors,
    },
    sparse_vectors=bm25_vectors,
)

# Search documents
results = await repo.search_documents(
    query_embeddings={"summary": q_vec, "section": q_vec, "microblock": q_vec},
    case_ids=[case_uuid],
    chunk_types=["PARAGRAPH"],
    top_k=10,
)

# Delete document
await repo.delete_document(document_id=doc_uuid)

# Get all chunks
chunks = await repo.get_document_chunks(document_id=doc_uuid)
```

#### QdrantTranscriptRepository

```python
from app.infrastructure.persistence.qdrant import QdrantTranscriptRepository

repo = QdrantTranscriptRepository()

# Index transcript
await repo.index_transcript(
    transcript_id=trans_uuid,
    case_id=case_uuid,
    segments=segments,
    embeddings=dense_vectors,
    sparse_vectors=bm25_vectors,
)

# Search with speaker filter
results = await repo.search_transcripts(
    query_embedding=query_vec,
    case_ids=[case_uuid],
    speaker_ids=["SPEAKER_00"],
    time_range=(0.0, 300.0),  # First 5 minutes
    top_k=10,
)

# Get all segments for a speaker
segments = await repo.get_speaker_segments(
    case_id=case_uuid,
    speaker_id="SPEAKER_00",
)
```

#### QdrantCommunicationRepository

```python
from app.infrastructure.persistence.qdrant import QdrantCommunicationRepository

repo = QdrantCommunicationRepository()

# Index communications
await repo.index_communications(
    case_id=case_uuid,
    communications=comms,
    embeddings=dense_vectors,
    sparse_vectors=bm25_vectors,
)

# Search with filters
results = await repo.search_communications(
    query_embedding=query_vec,
    case_ids=[case_uuid],
    participant_ids=["+1234567890"],
    platforms=["WHATSAPP", "IMESSAGE"],
    date_range=(start_date, end_date),
    top_k=10,
)

# Get thread
thread = await repo.get_thread_communications(thread_id="thread_123")

# Get participant communications
comms = await repo.get_participant_communications(
    case_id=case_uuid,
    participant_id="+1234567890",
)
```

#### QdrantFindingRepository

```python
from app.infrastructure.persistence.qdrant import QdrantFindingRepository

repo = QdrantFindingRepository()

# Index findings
await repo.index_findings(
    findings=findings,
    embeddings=dense_vectors,
    sparse_vectors=bm25_vectors,
)

# Check for duplicates
duplicate = await repo.check_duplicate_finding(
    finding_text="John signed the contract",
    finding_embedding=embedding,
    research_run_id=run_uuid,
    similarity_threshold=0.9,
)

# Search similar findings
similar = await repo.search_similar_findings(
    query_embedding=embedding,
    min_confidence=0.8,
    top_k=5,
)

# Get findings by entity
entity_findings = await repo.search_by_entity(entity_id=entity_uuid)
```

## Error Handling

All operations use custom exceptions from `app.infrastructure.exceptions`:

- `InfrastructureException`: Base exception
- `VectorStoreException`: General vector store errors
- `ConnectionException`: Connection failures
- `CollectionException`: Collection management errors
- `IndexingException`: Indexing failures
- `SearchException`: Search failures
- `DeletionException`: Deletion failures

Each exception includes:
- Human-readable message
- Original exception cause
- Context dictionary with relevant details

```python
try:
    await repo.index_document(...)
except IndexingException as e:
    logger.error(f"Indexing failed: {e}")
    logger.error(f"Context: {e.context}")
    logger.error(f"Cause: {e.cause}")
```

## Setup & Initialization

### 1. Install Dependencies

Ensure you have the required packages:
```bash
pip install qdrant-client
```

### 2. Configure Settings

Update `.env` or `app/core/config.py`:
```bash
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

### 3. Initialize Collections

Run the initialization script:
```bash
# Create collections (skip if they exist)
python scripts/init_qdrant_collections.py

# Recreate collections (WARNING: deletes existing data)
python scripts/init_qdrant_collections.py --recreate
```

Or programmatically:
```python
from app.infrastructure.persistence.qdrant import CollectionManager

await CollectionManager.create_all_collections()
```

## Best Practices

### 1. Use Hybrid Search
Always combine dense and sparse vectors for best results:
```python
results = await repo.search_documents(
    query_embeddings={"summary": vec, "section": vec, "microblock": vec},
    sparse_vector=bm25_vec,  # Don't skip this!
    top_k=10,
)
```

### 2. Batch Operations
Use batch sizes appropriate for your data:
```python
# Default batch_size=100 is good for most cases
await repo.upsert_points(points, batch_size=100)

# Larger batches for smaller vectors
await repo.upsert_points(points, batch_size=500)
```

### 3. Filter Aggressively
Use filters to reduce search space:
```python
results = await repo.search_documents(
    query_embeddings=embeddings,
    case_ids=[case_uuid],  # Critical for multi-tenancy
    chunk_types=["PARAGRAPH"],  # Focus on relevant chunks
    top_k=10,
)
```

### 4. Handle Errors Gracefully
```python
try:
    results = await repo.search_documents(...)
except SearchException as e:
    logger.error(f"Search failed: {e}")
    # Fallback to keyword search or return empty results
    results = []
```

### 5. Close Connections
When shutting down:
```python
from app.infrastructure.persistence.qdrant import close_qdrant_client

await close_qdrant_client()
```

## Testing

Example test:
```python
import pytest
from app.infrastructure.persistence.qdrant import (
    QdrantDocumentRepository,
    CollectionManager,
)

@pytest.mark.asyncio
async def test_document_indexing():
    # Setup
    await CollectionManager.create_document_collection()
    repo = QdrantDocumentRepository()

    # Index
    await repo.index_document(
        document_id=uuid4(),
        case_id=uuid4(),
        chunks=test_chunks,
        embeddings=test_embeddings,
    )

    # Search
    results = await repo.search_documents(
        query_embeddings=query_embeddings,
        top_k=5,
    )

    assert len(results) > 0
```

## Performance Considerations

### Vector Dimensions
All collections use 768-dimensional dense vectors (all-MiniLM-L6-v2 compatible). If using different embedding models, update `DENSE_VECTOR_DIM` in `collection_manager.py`.

### Sparse Vectors
BM25 sparse vectors are stored in memory (`on_disk=False`) for faster search. For very large collections, set `on_disk=True`:

```python
sparse_vectors = {
    "bm25": SparseVectorParams(
        index=SparseIndexParams(on_disk=True)  # Disk-based for scale
    )
}
```

### RRF Parameter
The `rrf_k` parameter (default 60) controls fusion behavior:
- Lower k (30-40): Emphasizes top-ranked results
- Higher k (60-100): Gives more weight to lower ranks
- Tune based on your use case

### Batch Sizes
- Documents: 100 points per batch (default)
- Transcripts: 100-200 points per batch
- Communications: 200-500 points per batch
- Findings: 50-100 points per batch

## Migration Guide

When updating collection schemas:

1. Create migration script:
```python
# Create new collection with updated schema
await CollectionManager.create_document_collection_v2()

# Copy data from old to new
# ... migration logic ...

# Swap collections
await client.delete_collection("legalease_documents")
await client.update_collection_aliases(...)
```

2. Or use `recreate=True` (destructive):
```python
await CollectionManager.create_all_collections(recreate=True)
```

## Troubleshooting

### Connection Refused
- Check Qdrant is running: `docker ps | grep qdrant`
- Verify host/port in settings
- Check firewall rules

### Dimension Mismatch
- Ensure all embeddings match `DENSE_VECTOR_DIM` (768)
- Check embedding model output dimensions
- Verify vector names match collection schema

### Slow Search
- Reduce `top_k` value
- Add more specific filters
- Consider enabling `on_disk=True` for sparse vectors
- Check Qdrant server resources

### Memory Issues
- Reduce batch sizes
- Enable `on_disk=True` for sparse vectors
- Increase Qdrant server memory
- Consider collection sharding

## License

Copyright (c) 2024 LegalEase. All rights reserved.
