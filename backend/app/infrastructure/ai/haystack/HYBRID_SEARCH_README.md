# Haystack Hybrid Search Pipeline

Complete implementation of hybrid retrieval combining BM25 (OpenSearch) and dense vectors (Qdrant) using Reciprocal Rank Fusion (RRF).

## Architecture

### Pipeline Flow

```
Query → LegalQueryPreprocessor → [QueryEmbedder → QdrantHybridRetriever (Dense)]
                               → [OpenSearchHybridRetriever (BM25)]
                               → ReciprocalRankFusionRanker
                               → ScoreThresholdFilter
                               → ResultEnricher
                               → HighlightExtractor
                               → Results
```

### Components

#### 1. **Retrievers** (`components/retrievers.py`)

##### QdrantHybridRetriever
- Searches Qdrant collections (documents, transcripts, communications)
- Dense vector similarity search
- Hierarchical embeddings (summary, section, microblock)
- Metadata filtering (case_id, document_id, chunk_types)

##### OpenSearchHybridRetriever
- Searches OpenSearch indexes (documents, transcripts, communications)
- BM25 keyword search
- Legal terminology analysis
- Citation matching support

#### 2. **Ranker** (`components/ranker.py`)

##### ReciprocalRankFusionRanker
Implements RRF algorithm: `score = sum(1 / (k + rank))` for each result list

Features:
- Fuses BM25 and dense results
- Score normalization (min-max to 0-1)
- Keyword boost (strong BM25 matches get +0.3)
- Non-linear scaling (power 0.7) for better distribution
- Deduplication by document ID

##### ScoreThresholdFilter
- Filters results below minimum score
- Default threshold: 0.3
- Configurable per-query

#### 3. **Query Processor** (`components/query_processor.py`)

##### LegalQueryPreprocessor
- **Synonym expansion**: attorney ↔ lawyer, contract ↔ agreement
- **Citation preservation**: Detects and preserves legal citations
- **Legal stopwords**: Preserves important legal terms
- **Normalization**: Lowercasing, whitespace cleanup

##### QueryEmbedder
- Wraps FastEmbedPipeline
- Model: BAAI/bge-small-en-v1.5 (384 dim)
- Fast ONNX inference

##### QuerySparseEncoder
- Wraps BM25Encoder
- Generates sparse vectors for keyword matching
- Configurable k1, b parameters

#### 4. **Enricher** (`components/enricher.py`)

##### ResultEnricher
- Batch fetches full metadata from PostgreSQL
- Enriches with document info (filename, type, page count)
- Enriches with case info (case number, title, court)
- Formats citations (page #, paragraph, timecode)

##### HighlightExtractor
- Extracts context-aware snippets
- Configurable context window (default: 10 words)
- Max highlights per result (default: 3)

#### 5. **Pipeline** (`pipelines/retrieval.py`)

##### HybridRetrievalPipeline
Main pipeline class supporting three modes:

1. **HYBRID**: BM25 + Dense + RRF
2. **KEYWORD_ONLY**: BM25 only
3. **SEMANTIC_ONLY**: Dense only

## Usage

### Basic Usage

```python
from app.infrastructure.ai.haystack.pipelines.retrieval import (
    create_hybrid_search_pipeline,
    SearchMode,
)

# Create pipeline
pipeline = create_hybrid_search_pipeline(
    mode=SearchMode.HYBRID,
    top_k=20,
    score_threshold=0.4,
)

# Run search
results = await pipeline.run(
    query="contract breach liability damages",
    filters={
        "case_ids": ["uuid1", "uuid2"],
        "chunk_types": ["summary", "section"],
        "evidence_types": ["documents", "transcripts"],
    },
)

# Access results
for doc in results["documents"]:
    print(f"Score: {doc.score:.3f}")
    print(f"Text: {doc.content[:100]}")
    print(f"Citation: {doc.meta.get('citation')}")
    print(f"Match type: {doc.meta.get('match_type')}")  # bm25, semantic, or hybrid
```

### Search Modes

#### Hybrid Search (Default)
```python
pipeline = create_hybrid_search_pipeline(
    mode=SearchMode.HYBRID,
    top_k=10,
    score_threshold=0.3,
    rrf_k=60,  # RRF constant
)
```

#### Keyword-Only Search
```python
pipeline = create_keyword_only_pipeline(
    top_k=10,
    score_threshold=0.3,
)
```

#### Semantic-Only Search
```python
pipeline = create_semantic_only_pipeline(
    top_k=10,
    score_threshold=0.3,
)
```

### Filters

```python
filters = {
    # Filter by case(s)
    "case_ids": ["uuid1", "uuid2"],

    # Filter by document(s)
    "document_ids": ["doc-uuid1"],

    # Filter by chunk types
    "chunk_types": ["summary", "section", "microblock"],

    # Filter by evidence types
    "evidence_types": ["documents", "transcripts", "communications"],
}

results = await pipeline.run(
    query="employment discrimination",
    filters=filters,
)
```

### Configuration Options

```python
pipeline = HybridRetrievalPipeline(
    mode=SearchMode.HYBRID,
    top_k=10,                    # Number of results
    score_threshold=0.3,         # Minimum score (0.0-1.0)
    rrf_k=60,                    # RRF constant (higher = less top-rank emphasis)
    expand_synonyms=True,        # Expand legal synonyms
    enrich_results=True,         # Fetch full metadata from PostgreSQL
)
```

## Score Interpretation

Scores are normalized to 0-1 range with keyword boosting:

- **0.85-1.0**: Strong keyword matches (high BM25 score)
- **0.6-0.85**: Semantic matches or moderate keyword matches
- **0.3-0.6**: Weak matches (default threshold filters these)
- **0.0-0.3**: Very weak matches (filtered out)

## Result Metadata

Each result document includes:

```python
{
    "id": "chunk-id",
    "content": "chunk text content",
    "score": 0.87,
    "meta": {
        # Match info
        "match_type": "bm25",  # or "semantic" or "hybrid"
        "bm25_score": 12.5,
        "dense_score": 0.82,
        "rrf_score": 0.0165,

        # Document info
        "document_id": "uuid",
        "document_gid": "gid",
        "document_filename": "contract.pdf",
        "document_file_type": "pdf",
        "document_page_count": 10,

        # Case info
        "case_id": "uuid",
        "case_gid": "gid",
        "case_number": "2023-CV-12345",
        "case_title": "Smith v. Jones",
        "case_court": "Superior Court",

        # Chunk info
        "chunk_type": "section",
        "position": 3,
        "page_number": 5,

        # Citation
        "citation": "contract.pdf, page 5, ¶3",

        # Highlights
        "highlights": [
            "...the defendant breached the contract...",
            "...resulting in damages of $100,000...",
        ],

        # Score debug info
        "score_debug": {
            "raw_rrf_score": 0.0165,
            "normalized_rrf": 0.75,
            "keyword_boost": 0.15,
            "final_score": 0.87,
        },
    },
}
```

## Integration with Existing Code

### Replace HybridSearchEngine

The Haystack pipeline can replace the existing `HybridSearchEngine` from `app/services/search_service.py`:

```python
# Old way
from app.services.search_service import get_search_engine

engine = get_search_engine()
results = engine.search(request)

# New way (Haystack)
from app.infrastructure.ai.haystack.pipelines.retrieval import create_hybrid_search_pipeline

pipeline = create_hybrid_search_pipeline()
results = await pipeline.run(
    query=request.query,
    filters={
        "case_ids": request.case_ids,
        "document_ids": request.document_ids,
        "chunk_types": request.chunk_types,
    },
    top_k=request.top_k,
    score_threshold=request.score_threshold,
)
```

### Convert Results to SearchResponse

```python
from app.schemas.search import HybridSearchResponse, SearchResult

# Convert Haystack Documents to SearchResult objects
search_results = []
for doc in results["documents"]:
    search_results.append(
        SearchResult(
            id=doc.id,
            gid=doc.id,
            score=doc.score,
            text=doc.content,
            match_type=doc.meta.get("match_type"),
            page_number=doc.meta.get("page_number"),
            bboxes=doc.meta.get("bboxes", []),
            metadata=doc.meta,
            highlights=doc.meta.get("highlights"),
            vector_type=doc.meta.get("chunk_type"),
        )
    )

response = HybridSearchResponse(
    results=search_results,
    total_results=len(search_results),
    query=results["query"],
    search_metadata={
        "mode": results["mode"],
        "search_time_ms": 0,  # Add timing
    },
)
```

## RRF Algorithm Details

The RRF algorithm combines rankings from multiple sources:

```python
# For each document found in any result list
for doc_id in all_docs:
    rrf_score = 0

    # BM25 ranking contribution
    if doc_id in bm25_results:
        rank_bm25 = bm25_results.index(doc_id) + 1
        rrf_score += 1 / (k + rank_bm25)

    # Dense ranking contribution
    if doc_id in dense_results:
        rank_dense = dense_results.index(doc_id) + 1
        rrf_score += 1 / (k + rank_dense)

    # Normalize to 0-1 range
    normalized_score = (rrf_score - min_score) / (max_score - min_score)

    # Boost keyword matches
    if bm25_score > 5.0:
        boost = min(bm25_score / 10.0, 1.0) * 0.3
        normalized_score += boost

    # Non-linear scaling
    final_score = normalized_score ** 0.7
```

## Performance Considerations

1. **Batch fetching**: ResultEnricher batches PostgreSQL queries
2. **Top-k multiplier**: Retrievers fetch 2x top_k for better fusion
3. **Async operations**: All I/O operations are async
4. **Caching**: FastEmbed models are cached in memory
5. **Early filtering**: Score threshold applied before enrichment

## Testing

```python
import pytest
from app.infrastructure.ai.haystack.pipelines.retrieval import create_hybrid_search_pipeline

@pytest.mark.asyncio
async def test_hybrid_search():
    pipeline = create_hybrid_search_pipeline(top_k=5)

    results = await pipeline.run(
        query="contract breach",
        filters={"case_ids": ["test-case-id"]},
    )

    assert len(results["documents"]) <= 5
    assert all(doc.score >= 0.3 for doc in results["documents"])
```

## Logging

All components include comprehensive logging:

```python
import logging

# Enable debug logging
logging.getLogger("app.infrastructure.ai.haystack").setLevel(logging.DEBUG)

# Log examples:
# - "RRF fusion: 15 BM25 results + 18 dense results"
# - "Score normalization complete: raw range [0.0083, 0.0333] -> normalized [0.0, 1.0]"
# - "Pipeline returned 10 results"
```

## Future Enhancements

1. **Cross-encoder reranking**: Add optional reranking stage
2. **Query expansion**: Use LLM for query expansion
3. **Context retrieval**: Fetch surrounding chunks
4. **Streaming results**: Support streaming for large result sets
5. **Caching**: Add Redis caching for repeated queries
6. **Analytics**: Track search patterns and performance metrics
