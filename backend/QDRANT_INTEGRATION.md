# Qdrant Vector Database Integration

This document describes the Qdrant vector database integration for LegalEase, implementing hybrid search with multi-vector configuration following the RAGFlow pattern.

## Overview

The integration provides:
- **Multi-vector storage**: Separate embeddings for summaries, sections, and microblocks
- **Sparse vector support**: BM25 keyword matching
- **Hybrid search**: Combines dense and sparse vectors using Reciprocal Rank Fusion (RRF)
- **Flexible filtering**: By case, document, chunk type, etc.

## Architecture

### Components

1. **app/core/qdrant.py** - Core Qdrant client and utilities
2. **app/schemas/search.py** - Pydantic schemas for requests/responses
3. **app/services/search_service.py** - Hybrid search engine implementation

## File Descriptions

### 1. app/core/qdrant.py

Provides low-level Qdrant operations:

**Functions:**
- `get_qdrant_client()` - Singleton client instance
- `create_collection()` - Initialize collection with multi-vector config
- `upsert_points()` - Batch upload document chunks
- `search_hybrid()` - Execute hybrid search
- `delete_points()` - Remove chunks by ID
- `delete_by_filter()` - Remove chunks by filter
- `get_collection_info()` - Get collection statistics
- `build_filter()` - Build Qdrant filters from parameters

**Collection Schema:**

Dense vectors:
- `summary` (768-dim, COSINE) - Document/section summaries
- `section` (768-dim, COSINE) - Section-level chunks
- `microblock` (768-dim, COSINE) - Fine-grained chunks

Sparse vectors:
- `bm25` (SparseVector) - Keyword matching

### 2. app/schemas/search.py

Pydantic models for type safety and validation:

**Request Models:**
- `SearchQuery` - Basic search parameters
- `HybridSearchRequest` - Full hybrid search with fusion config
- `IndexRequest` - Batch indexing request

**Response Models:**
- `SearchResult` - Individual result with score, text, metadata
- `HybridSearchResponse` - Complete search response with metadata
- `IndexResponse` - Indexing confirmation

**Data Models:**
- `DocumentChunk` - Chunk to be indexed

### 3. app/services/search_service.py

High-level search engine implementation:

**HybridSearchEngine Class:**

Methods:
- `bm25_search()` - BM25 keyword search
- `vector_search()` - Dense vector semantic search
- `reciprocal_rank_fusion()` - RRF result fusion
- `search()` - Main hybrid search orchestrator

Private methods:
- `_tokenize_for_bm25()` - Text tokenization
- `_create_sparse_vector()` - Generate BM25 vectors
- `_create_dense_vectors()` - Generate embeddings
- `_extract_highlights()` - Extract query highlights

## Configuration

Add to `.env` or configure in `app/core/config.py`:

```env
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=legalease_documents
```

## Usage Examples

### 1. Initialize Collection

```python
from app.core.qdrant import create_collection

# Create collection with default 768-dim vectors (all-MiniLM-L6-v2)
create_collection(
    summary_vector_size=768,
    section_vector_size=768,
    microblock_vector_size=768,
    recreate=False,
)
```

### 2. Index Documents

```python
from app.core.qdrant import upsert_points
from qdrant_client.models import PointStruct, SparseVector
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Prepare chunk data
text = "The defendant breached the contract..."
embedding = model.encode(text).tolist()

# Create BM25 sparse vector (simplified)
tokens = text.lower().split()
sparse_indices = [hash(t) % (2**31) for t in set(tokens)]
sparse_values = [float(tokens.count(t)) for t in set(tokens)]

# Create point
point = PointStruct(
    id=1,
    vector={
        "summary": embedding,
        "section": embedding,
        "microblock": embedding,
        "bm25": SparseVector(indices=sparse_indices, values=sparse_values),
    },
    payload={
        "text": text,
        "document_id": 123,
        "case_id": 1,
        "chunk_type": "section",
        "page_number": 5,
        "position": 2,
    }
)

# Upload
upsert_points([point])
```

### 3. Perform Hybrid Search

```python
from app.services.search_service import get_search_engine
from app.schemas.search import HybridSearchRequest

# Get search engine instance
engine = get_search_engine()

# Create search request
request = HybridSearchRequest(
    query="contract breach damages",
    case_ids=[1, 2, 3],  # Filter by cases
    top_k=10,
    fusion_method="rrf",
    rrf_k=60,
    use_bm25=True,
    use_dense=True,
)

# Execute search
response = engine.search(request)

# Process results
for result in response.results:
    print(f"Score: {result.score:.4f}")
    print(f"Text: {result.text}")
    print(f"Metadata: {result.metadata}")
    print(f"Highlights: {result.highlights}")
```

### 4. Filter by Document or Chunk Type

```python
request = HybridSearchRequest(
    query="employment discrimination",
    document_ids=[10, 20],  # Specific documents
    chunk_types=["summary"],  # Only summaries
    top_k=5,
)

response = engine.search(request)
```

## Integration with FastAPI

Example API endpoint:

```python
from fastapi import APIRouter, HTTPException
from app.schemas.search import HybridSearchRequest, HybridSearchResponse
from app.services.search_service import get_search_engine

router = APIRouter(prefix="/api/search", tags=["search"])

@router.post("/hybrid", response_model=HybridSearchResponse)
async def hybrid_search(request: HybridSearchRequest):
    """Perform hybrid search on legal documents."""
    try:
        engine = get_search_engine()
        response = engine.search(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Reciprocal Rank Fusion (RRF)

The implementation uses RRF to combine results from multiple search methods:

**Formula:**
```
RRF_score(d) = Σ (1 / (k + rank_r(d)))
```

Where:
- `d` = document
- `r` = ranklist (e.g., BM25, summary vector, section vector)
- `k` = constant (typically 60)
- `rank_r(d)` = rank of document d in ranklist r

**Benefits:**
- No need to normalize scores across different search methods
- Robust to outliers
- Simple and effective for combining heterogeneous rankings

## Multi-Vector Strategy

Following RAGFlow's approach:

1. **Summary vectors** - High-level document understanding
2. **Section vectors** - Mid-level semantic chunks
3. **Microblock vectors** - Fine-grained retrieval

Each chunk is indexed with all three vector types, allowing:
- Broad semantic search (summaries)
- Balanced precision/recall (sections)
- Exact match retrieval (microblocks)

Combined with BM25 for keyword matching, providing comprehensive multi-recall search.

## Performance Considerations

### Indexing
- Batch upload in chunks of 100 points (configurable)
- Async support recommended for large datasets
- Consider background jobs (Celery) for document processing

### Search
- BM25 + 3 dense vectors = 4 queries per search
- RRF fusion is O(n log n) where n = total results
- Typical latency: 50-200ms for 10k documents

### Optimization
- Use score thresholds to reduce result sets
- Filter by case/document to limit search scope
- Cache frequently used embeddings
- Consider GPU for embedding generation at scale

## Testing

Run the example:

```bash
# Start Qdrant
docker run -p 6333:6333 qdrant/qdrant

# Run example
python example_usage.py
```

## Dependencies

Required packages (already in `pyproject.toml`):
- `qdrant-client>=1.15.1` - Qdrant Python client
- `sentence-transformers>=5.1.1` - Embedding models
- `pydantic>=2.12.0` - Schema validation

## Future Enhancements

1. **Advanced BM25**: Integrate proper BM25 library (e.g., rank-bm25)
2. **Query expansion**: Add synonyms, legal term expansion
3. **Reranking**: Cross-encoder reranking for top-k results
4. **Caching**: Redis cache for frequent queries
5. **Analytics**: Track search performance and relevance metrics
6. **Vector models**: Experiment with legal-domain-specific embeddings
7. **Hybrid fusion**: Implement weighted and max fusion methods

## Troubleshooting

### Connection errors
- Ensure Qdrant is running: `docker ps | grep qdrant`
- Check `QDRANT_HOST` and `QDRANT_PORT` settings

### Import errors
- Verify all dependencies installed: `pip install -r requirements.txt`
- Check Python version (>=3.13)

### Empty results
- Verify collection exists: Call `get_collection_info()`
- Check if points indexed: Collection should have `points_count > 0`
- Try broader search: Remove filters, increase `top_k`

### Slow search
- Add filters to reduce search space
- Use score thresholds
- Check network latency to Qdrant
- Consider local Qdrant instance

## References

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [RAGFlow Architecture](https://github.com/infiniflow/ragflow)
- [Reciprocal Rank Fusion Paper](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [Sentence Transformers](https://www.sbert.net/)
