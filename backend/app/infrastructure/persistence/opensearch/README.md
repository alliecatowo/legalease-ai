# OpenSearch BM25 Repository Implementation

This package provides OpenSearch-based BM25 lexical search for the LegalEase platform, complementing Qdrant's dense vector search in hybrid retrieval.

## Overview

OpenSearch provides:
- **BM25 ranking** for keyword/lexical search
- **Legal text analysis** with custom analyzers for legal terminology
- **Citation matching** for case law and statute references
- **Full-text search** across documents, transcripts, and communications

## Architecture

```
opensearch/
├── client.py              # Async OpenSearch client with connection pooling
├── analyzers.py           # Custom legal text analyzers
├── schemas.py             # Index mappings and settings
├── index_manager.py       # Index lifecycle management
└── repositories/
    ├── base.py            # Base BM25 repository
    ├── document.py        # Document chunk search
    ├── transcript.py      # Transcript segment search
    ├── communication.py   # Digital communication search
    └── finding.py         # Research finding search
```

## Features

### 1. Custom Legal Analyzers

#### Legal Analyzer
- Tokenization with standard tokenizer
- Legal stopword removal (plaintiff, defendant, etc.)
- Stemming (snowball)
- Legal synonym expansion (contract→agreement, attorney→lawyer, etc.)

#### Shingle Analyzer
- 2-3 word phrase combinations
- Improved phrase matching and relevance

#### Citation Analyzer
- Preserves legal citation formats
- Case numbers (e.g., "123 F.3d 456")
- Statute references (e.g., "18 U.S.C. § 1001")
- Court identifiers (e.g., "9th Cir.")

### 2. Index Schemas

#### Documents Index (`legalease-documents`)
Stores document chunks with:
- Full-text search on chunk text
- Case and document filtering
- Chunk type filtering (paragraph, page, section, etc.)
- Page number and position tracking
- Citation analysis support

#### Transcripts Index (`legalease-transcripts`)
Stores transcript segments with:
- Full-text search on speech content
- Speaker identification and filtering
- Timecode-based range queries
- Exact quote matching
- Confidence scoring

#### Communications Index (`legalease-communications`)
Stores digital communications with:
- Full-text search on message body
- Thread grouping and filtering
- Participant filtering
- Temporal range queries
- Platform identification

#### Findings Index (`legalease-findings`)
Stores research findings with:
- Full-text search on finding text
- Type filtering (fact, pattern, anomaly, etc.)
- Confidence and relevance scoring
- Tag-based organization
- Entity and citation linking

## Usage

### Initialization

```python
from app.infrastructure.persistence.opensearch import (
    get_opensearch_client,
    OpenSearchIndexManager,
    OpenSearchDocumentRepository,
)

# Initialize client
client = await get_opensearch_client()

# Create indexes
manager = OpenSearchIndexManager(client)
await manager.create_all_indexes()
```

### Document Search

```python
# Create repository
doc_repo = OpenSearchDocumentRepository(client)

# Index document chunks
from app.domain.evidence.value_objects.chunk import Chunk, ChunkType

chunks = [
    Chunk(
        text="The contract was signed on March 15, 2024.",
        chunk_type=ChunkType.PARAGRAPH,
        position=0,
        metadata={"page": 1}
    ),
    # ... more chunks
]

await doc_repo.index_document_chunks(
    document_id=document_id,
    case_id=case_id,
    chunks=chunks
)

# Search documents
results = await doc_repo.search_documents(
    query="contract terms",
    case_ids=[case_id],
    chunk_types=["PARAGRAPH"],
    top_k=10
)

for result in results.results:
    print(f"Score: {result.score}")
    print(f"Text: {result.source['text']}")
    print(f"Page: {result.source['page_number']}")

# Search by citation
results = await doc_repo.search_by_citation(
    citation="123 F.3d 456",
    case_ids=[case_id]
)
```

### Transcript Search

```python
from app.infrastructure.persistence.opensearch import OpenSearchTranscriptRepository

# Create repository
transcript_repo = OpenSearchTranscriptRepository(client)

# Search transcripts
results = await transcript_repo.search_transcripts(
    query="contract discussion",
    case_ids=[case_id],
    speaker="John Doe",
    time_range=(0.0, 300.0),  # First 5 minutes
    top_k=10
)

# Search exact quotes
results = await transcript_repo.search_quotes(
    phrase="I never signed the contract",
    exact=True,
    case_ids=[case_id]
)

# Get segments by speaker
results = await transcript_repo.get_segments_by_speaker(
    transcript_id=transcript_id,
    speaker_id="SPEAKER_00"
)
```

### Communication Search

```python
from app.infrastructure.persistence.opensearch import OpenSearchCommunicationRepository

# Create repository
comm_repo = OpenSearchCommunicationRepository(client)

# Index communications
from app.domain.evidence.entities.communication import Communication

await comm_repo.index_communications(
    case_id=case_id,
    communications=[comm1, comm2, comm3]
)

# Search communications
results = await comm_repo.search_communications(
    query="contract negotiation",
    case_ids=[case_id],
    participants=["john.doe@example.com"],
    platforms=["EMAIL"]
)

# Search by thread
results = await comm_repo.search_threads(
    query="settlement discussion",
    case_ids=[case_id]
)

# Search by time range
from datetime import datetime

results = await comm_repo.search_by_timerange(
    start=datetime(2024, 1, 1),
    end=datetime(2024, 3, 31),
    case_ids=[case_id],
    query="payment terms"
)
```

### Finding Search

```python
from app.infrastructure.persistence.opensearch import OpenSearchFindingRepository

# Create repository
finding_repo = OpenSearchFindingRepository(client)

# Search findings
results = await finding_repo.search_findings(
    query="breach of contract",
    research_run_ids=[run_id],
    finding_types=["FACT", "CONTRADICTION"],
    tags=["contract", "breach"],
    min_confidence=0.8,
    top_k=20
)

# Search by tags
results = await finding_repo.search_by_tags(
    tags=["contract", "damages"],
    match_all=True  # Require all tags
)

# Get high-confidence findings
results = await finding_repo.get_high_confidence_findings(
    research_run_id=run_id,
    min_confidence=0.9
)
```

### Index Management

```python
from app.infrastructure.persistence.opensearch import get_index_manager

manager = await get_index_manager()

# Create all indexes
await manager.create_all_indexes()

# Check index health
health = await manager.check_index_health()
for index_name, info in health.items():
    print(f"{index_name}: {info['doc_count']} documents, {info['size_mb']} MB")

# Refresh indexes
await manager.refresh_all_indexes()

# Recreate all indexes (CAUTION: deletes data)
await manager.recreate_all_indexes()

# Reindex operation
await manager.reindex(
    source_index="legalease-documents",
    dest_index="legalease-documents-v2"
)
```

## Configuration

OpenSearch settings in `app/core/config.py`:

```python
OPENSEARCH_URL: str = "http://localhost:9200"
OPENSEARCH_INDEX_PREFIX: str = "legalease"
OPENSEARCH_TIMEOUT: int = 30
OPENSEARCH_MAX_RETRIES: int = 3
```

## BM25 Ranking

BM25 (Best Matching 25) is a probabilistic ranking function that scores documents based on:

1. **Term Frequency (TF)**: How often query terms appear in documents
2. **Inverse Document Frequency (IDF)**: Rarity of terms across the corpus
3. **Document Length Normalization**: Prevents bias toward long documents

### Query Strategies

1. **Multi-Match Query**: Searches across multiple fields with field boosting
   ```python
   fields=["text^3", "text.shingles^2", "text.citation"]
   ```

2. **Bool Query**: Combines must/should/filter clauses
   ```python
   bool: {
       must: [match_query],
       filter: [term_filters],
       should: [boost_queries]
   }
   ```

3. **Phrase Match**: For exact or near-exact phrase matching
   ```python
   match_phrase: {
       text: {
           query: "breach of contract",
           slop: 2  # Allow 2 word gaps
       }
   }
   ```

## Performance Considerations

### Indexing
- Use bulk operations (batch_size=500) for efficiency
- Refresh index only when needed (impacts write performance)
- Index in background for large datasets

### Searching
- Use filters (cached) instead of queries where possible
- Limit result size (top_k) appropriately
- Use pagination (from, size) for large result sets
- Enable highlighting only when needed

### Index Configuration
- **Shards**: 2 (small/medium datasets) to 5+ (large datasets)
- **Replicas**: 1 (development) to 2+ (production)
- **Refresh interval**: "1s" (default) or longer for write-heavy workloads

## Testing

Run the demo script:

```bash
cd backend
python scripts/opensearch_demo.py
```

This will:
1. Initialize client and create indexes
2. Index sample legal document chunks
3. Perform various BM25 searches
4. Display results with scores
5. Clean up test data

## Error Handling

All operations raise `RepositoryException` on failure:

```python
from app.shared.exceptions.domain_exceptions import RepositoryException

try:
    results = await doc_repo.search_documents("query")
except RepositoryException as e:
    print(f"Search failed: {e.message}")
    print(f"Context: {e.context}")
    print(f"Original error: {e.original_exception}")
```

## Integration with Hybrid Search

OpenSearch BM25 complements Qdrant vector search:

1. **BM25 (OpenSearch)**: Keyword/lexical matching, citations, exact phrases
2. **Dense vectors (Qdrant)**: Semantic similarity, concept matching
3. **Hybrid**: Combine both with reciprocal rank fusion (RRF)

```python
# Get BM25 results
bm25_results = await doc_repo.search_documents(query)

# Get vector results
vector_results = await qdrant_repo.search_documents(query)

# Combine with RRF
hybrid_results = reciprocal_rank_fusion(
    [bm25_results, vector_results],
    weights=[0.5, 0.5]
)
```

## Future Enhancements

- [ ] Learning to Rank (LTR) for result re-ranking
- [ ] Query expansion with legal thesaurus
- [ ] Custom scoring functions for legal relevance
- [ ] Percolator queries for real-time alerting
- [ ] Aggregations for faceted search
- [ ] More specific legal citation patterns
- [ ] Multi-language support

## Resources

- [OpenSearch Documentation](https://opensearch.org/docs/latest/)
- [opensearch-py Client](https://github.com/opensearch-project/opensearch-py)
- [BM25 Algorithm](https://en.wikipedia.org/wiki/Okapi_BM25)
- [Text Analysis](https://opensearch.org/docs/latest/analyzers/)
