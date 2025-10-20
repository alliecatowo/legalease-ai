# Qdrant Repositories - Quick Reference

## Import Statements

```python
# All repositories
from app.infrastructure.persistence.qdrant import (
    QdrantDocumentRepository,
    QdrantTranscriptRepository,
    QdrantCommunicationRepository,
    QdrantFindingRepository,
)

# Collection management
from app.infrastructure.persistence.qdrant import (
    CollectionManager,
    CollectionName,
)

# Client (rarely needed directly)
from app.infrastructure.persistence.qdrant import (
    get_qdrant_client,
    close_qdrant_client,
)
```

## Common Patterns

### Document Indexing & Search

```python
# Initialize repository
repo = QdrantDocumentRepository()

# Index a document
await repo.index_document(
    document_id=document.id,
    case_id=case.id,
    chunks=chunks,  # List[Chunk]
    embeddings={
        "summary": summary_vecs,
        "section": section_vecs,
        "microblock": microblock_vecs,
    },
    sparse_vectors=bm25_vecs,  # Optional
)

# Search across documents
results = await repo.search_documents(
    query_embeddings={
        "summary": query_vec,
        "section": query_vec,
        "microblock": query_vec,
    },
    case_ids=[case.id],  # Filter by case
    chunk_types=["PARAGRAPH"],  # Optional chunk type filter
    top_k=10,
    score_threshold=0.7,  # Optional minimum score
)

# Delete document
await repo.delete_document(document_id=document.id)
```

### Transcript Indexing & Search

```python
# Initialize repository
repo = QdrantTranscriptRepository()

# Index transcript
await repo.index_transcript(
    transcript_id=transcript.id,
    case_id=case.id,
    segments=segments,  # List[TranscriptSegment]
    embeddings=dense_vecs,  # List[List[float]]
    sparse_vectors=bm25_vecs,  # Optional
)

# Search with speaker filter
results = await repo.search_transcripts(
    query_embedding=query_vec,
    case_ids=[case.id],
    speaker_ids=["SPEAKER_00", "John Doe"],  # Optional
    time_range=(0.0, 600.0),  # Optional: first 10 minutes
    top_k=10,
)

# Get all segments for a speaker
segments = await repo.get_speaker_segments(
    case_id=case.id,
    speaker_id="SPEAKER_00",
    top_k=100,  # Optional limit
)
```

### Communication Indexing & Search

```python
# Initialize repository
repo = QdrantCommunicationRepository()

# Index communications
await repo.index_communications(
    case_id=case.id,
    communications=comms,  # List[Communication]
    embeddings=dense_vecs,
    sparse_vectors=bm25_vecs,  # Optional
)

# Search with filters
results = await repo.search_communications(
    query_embedding=query_vec,
    case_ids=[case.id],
    participant_ids=["+1234567890"],  # Optional
    platforms=["WHATSAPP", "IMESSAGE"],  # Optional
    date_range=(start_dt, end_dt),  # Optional
    top_k=10,
)

# Get thread
thread = await repo.get_thread_communications(
    thread_id="thread_12345",
    limit=100,  # Optional
)

# Get participant communications
participant_comms = await repo.get_participant_communications(
    case_id=case.id,
    participant_id="+1234567890",
    limit=100,  # Optional
)
```

### Finding Indexing & Deduplication

```python
# Initialize repository
repo = QdrantFindingRepository()

# Index findings
await repo.index_findings(
    findings=findings,  # List[Finding]
    embeddings=dense_vecs,
    sparse_vectors=bm25_vecs,  # Optional
)

# Check for duplicates before indexing
duplicate = await repo.check_duplicate_finding(
    finding_text="John signed the contract on March 15",
    finding_embedding=embedding,
    research_run_id=run.id,
    similarity_threshold=0.9,
)

if duplicate:
    print(f"Duplicate found: {duplicate['id']}")
else:
    # Index the finding
    await repo.index_findings([finding], [embedding])

# Search similar findings
similar = await repo.search_similar_findings(
    query_embedding=embedding,
    research_run_id=run.id,  # Optional
    min_confidence=0.8,  # Optional
    min_relevance=0.7,  # Optional
    tags=["contract", "signature"],  # Optional
    top_k=5,
)

# Get findings by entity
entity_findings = await repo.search_by_entity(
    entity_id=entity.id,
    top_k=20,
)
```

## Collection Management

### Initialize All Collections

```python
from app.infrastructure.persistence.qdrant import CollectionManager

# Create all collections (skip if they exist)
await CollectionManager.create_all_collections()

# Recreate all collections (WARNING: deletes data)
await CollectionManager.create_all_collections(recreate=True)
```

### Create Individual Collections

```python
# Documents
await CollectionManager.create_document_collection()

# Transcripts
await CollectionManager.create_transcript_collection()

# Communications
await CollectionManager.create_communication_collection()

# Findings
await CollectionManager.create_finding_collection()
```

### Get Collection Stats

```python
stats = await CollectionManager.get_collection_stats()

for collection_name, collection_stats in stats.items():
    print(f"{collection_name}:")
    print(f"  Points: {collection_stats.get('points_count', 0)}")
    print(f"  Vectors: {collection_stats.get('vectors', [])}")
```

## Error Handling

```python
from app.infrastructure.exceptions import (
    IndexingException,
    SearchException,
    DeletionException,
)

try:
    results = await repo.search_documents(...)
except SearchException as e:
    logger.error(f"Search failed: {e.message}")
    logger.error(f"Cause: {e.cause}")
    logger.error(f"Context: {e.context}")
    # Fallback logic
    results = []

try:
    await repo.index_document(...)
except IndexingException as e:
    logger.error(f"Indexing failed: {e}")
    # Handle error
```

## Result Format

All search methods return results in this format:

```python
[
    {
        "id": "chunk_id_or_uuid",
        "payload": {
            "case_id": "uuid-string",
            "text": "chunk text",
            # ... other fields
        },
        "rrf_score": 0.95,  # Fused score from RRF
        "sources": [  # Which vectors contributed
            {
                "vector_type": "dense",
                "rank": 1,
                "score": 0.92,
            },
            {
                "vector_type": "bm25",
                "rank": 3,
                "score": 0.85,
            },
        ],
    },
    # ... more results
]
```

## Filter Building

All repositories inherit `build_filter()` from base:

```python
# Build filter programmatically
from qdrant_client.models import Filter, FieldCondition, MatchValue

filters = repo.build_filter(
    case_ids=[case1.id, case2.id],
    document_ids=[doc1.id],
    additional_conditions=[
        FieldCondition(
            key="chunk_type",
            match=MatchValue(value="PARAGRAPH"),
        )
    ],
)
```

## Cleanup

```python
from app.infrastructure.persistence.qdrant import close_qdrant_client

# When shutting down application
await close_qdrant_client()
```

## CLI Commands

```bash
# Initialize collections
python scripts/init_qdrant_collections.py

# Recreate collections (deletes data)
python scripts/init_qdrant_collections.py --recreate
```

## Common Gotchas

### 1. Always use case_ids filter for multi-tenancy
```python
# ❌ BAD - searches across all cases
results = await repo.search_documents(
    query_embeddings=embeddings,
    top_k=10,
)

# ✅ GOOD - filters by case
results = await repo.search_documents(
    query_embeddings=embeddings,
    case_ids=[case.id],
    top_k=10,
)
```

### 2. Include sparse vectors for best results
```python
# ❌ OK - dense only
results = await repo.search_documents(
    query_embeddings={"summary": vec},
    top_k=10,
)

# ✅ BETTER - hybrid search
results = await repo.search_documents(
    query_embeddings={"summary": vec},
    sparse_vector=bm25_vec,
    top_k=10,
)
```

### 3. Use appropriate batch sizes
```python
# ❌ BAD - no batching
await repo.upsert_points(large_points_list, batch_size=10000)

# ✅ GOOD - reasonable batch size
await repo.upsert_points(large_points_list, batch_size=100)
```

### 4. Handle connection lifecycle
```python
# ❌ BAD - creates new client each time
def get_repo():
    return QdrantDocumentRepository()  # New client every call

# ✅ GOOD - reuse singleton client
repo = QdrantDocumentRepository()  # Once at startup
# Use repo throughout application lifecycle
```

## Performance Tips

1. **Use filters**: Reduce search space with case_ids, document_ids, etc.
2. **Adjust top_k**: Don't retrieve more results than needed
3. **Batch operations**: Use batch_size=100-500 for indexing
4. **Score thresholds**: Set minimum score to filter low-quality results
5. **Cache results**: Cache frequent searches at application layer

## Testing

```python
import pytest
from app.infrastructure.persistence.qdrant import QdrantDocumentRepository

@pytest.fixture
async def setup_collection():
    """Setup test collection."""
    from app.infrastructure.persistence.qdrant import CollectionManager
    await CollectionManager.create_document_collection()
    yield
    # Cleanup if needed

@pytest.mark.asyncio
async def test_document_search(setup_collection):
    repo = QdrantDocumentRepository()

    # Index test data
    await repo.index_document(...)

    # Search
    results = await repo.search_documents(...)

    assert len(results) > 0
    assert results[0]["payload"]["text"] == "expected text"
```

## Monitoring

Track these metrics in production:
- Search latency (p50, p95, p99)
- Indexing throughput (docs/sec)
- Error rates per operation type
- Collection sizes
- Query complexity (filter depth)
- RRF fusion time

## Support

For issues or questions:
1. Check README.md for detailed documentation
2. Review exception context for debugging
3. Enable DEBUG logging for troubleshooting
4. Check Qdrant server logs
