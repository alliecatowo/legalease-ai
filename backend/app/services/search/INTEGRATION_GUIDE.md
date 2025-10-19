# GraphRAG Integration Guide

This guide shows how to integrate GraphRAG-enhanced search into your legal document search API.

## Quick Start

### 1. Import the Engine

```python
from app.services.search.graph_rag import create_graph_rag_engine
from app.core.neo4j import neo4j_client
from app.services.entity_service import entity_service

# Create engine instance
graph_rag = create_graph_rag_engine(
    neo4j_client=neo4j_client,
    entity_service=entity_service
)
```

### 2. Basic Usage

#### Entity-Enhanced Search

```python
# Extract entities and find related documents
doc_ids = await graph_rag.entity_enhanced_search(
    query="contract dispute between parties",
    case_id=case_id,
    db=db_session
)

# Use these doc_ids to filter/boost your vector search
```

#### Citation Enhancement

```python
# After vector search, add citation context
enhanced_results = graph_rag.add_citation_context(
    search_results=vector_search_results,
    case_id=case_id
)
```

## Full Integration Example

Here's a complete example integrating GraphRAG with hybrid search:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.search.engine import get_search_engine
from app.services.search.graph_rag import create_graph_rag_engine
from app.core.neo4j import neo4j_client
from app.services.entity_service import entity_service
from app.schemas.search import HybridSearchRequest, HybridSearchResponse

router = APIRouter()

# Initialize GraphRAG engine (singleton)
graph_rag = create_graph_rag_engine(neo4j_client, entity_service)


@router.post("/search/enhanced", response_model=HybridSearchResponse)
async def enhanced_search(
    request: HybridSearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    GraphRAG-enhanced search endpoint.

    Combines:
    - Entity extraction and graph traversal
    - Hybrid BM25 + dense vector search
    - Citation-based ranking
    """
    search_engine = get_search_engine()

    # Step 1: Entity-enhanced document discovery
    entity_doc_ids = await graph_rag.entity_enhanced_search(
        query=request.query,
        case_id=request.case_ids[0] if request.case_ids else None,
        db=db,
        min_confidence=0.5
    )

    # Step 2: Hybrid vector search
    # Option A: Filter to only entity-related docs
    if entity_doc_ids:
        request.document_ids = entity_doc_ids

    # Option B: Boost entity-related docs (recommended)
    # This allows non-entity docs to appear if semantically relevant
    search_response = search_engine.search(request)

    # Step 3: Citation enhancement
    if search_response.results:
        # Convert to dict for processing
        results_dict = [r.dict() for r in search_response.results]

        # Add citation context and boost scores
        enhanced_results = graph_rag.add_citation_context(
            search_results=results_dict,
            case_id=request.case_ids[0] if request.case_ids else None,
            citation_boost_weight=0.15
        )

        # Convert back to response format
        from app.schemas.search import SearchResult
        search_response.results = [
            SearchResult(**r) for r in enhanced_results
        ]

    # Add metadata about enhancements
    search_response.search_metadata.update({
        "graph_rag_enabled": True,
        "entity_enhanced_docs": len(entity_doc_ids) if entity_doc_ids else 0,
        "citation_boost_applied": True
    })

    return search_response
```

## Integration Strategies

### Strategy 1: Entity Filtering (Precision-Focused)

Use when you want to strictly limit results to documents mentioning query entities.

```python
# Get entity-enhanced docs
entity_doc_ids = await graph_rag.entity_enhanced_search(
    query=query,
    case_id=case_id,
    db=db
)

# Filter search to only these documents
search_request.document_ids = entity_doc_ids
results = search_engine.search(search_request)
```

**Pros:**
- High precision
- Guaranteed entity relevance
- Faster search (smaller search space)

**Cons:**
- May miss semantically relevant docs without exact entity matches
- Lower recall

### Strategy 2: Entity Boosting (Recall-Focused)

Use when you want to boost entity-related docs but still allow other results.

```python
# Get entity-enhanced docs
entity_doc_ids = await graph_rag.entity_enhanced_search(
    query=query,
    case_id=case_id,
    db=db
)

# Convert to set for fast lookup
entity_doc_set = set(entity_doc_ids)

# Perform regular search
results = search_engine.search(search_request)

# Boost scores of entity-related docs
for result in results:
    doc_id = result.metadata.get("document_id")
    if doc_id in entity_doc_set:
        result.score = min(1.0, result.score * 1.2)  # 20% boost
```

**Pros:**
- Better recall
- Balances entity and semantic relevance
- More flexible

**Cons:**
- May include less relevant docs
- Requires score tuning

### Strategy 3: Hybrid Approach (Recommended)

Combine both filtering and boosting for best results.

```python
# Get entity-enhanced docs
entity_doc_ids = await graph_rag.entity_enhanced_search(
    query=query,
    case_id=case_id,
    db=db
)

# Search 1: Entity-focused (top 30)
entity_search = HybridSearchRequest(
    query=query,
    document_ids=entity_doc_ids,
    top_k=30
)
entity_results = search_engine.search(entity_search)

# Search 2: Semantic-focused (top 20)
semantic_search = HybridSearchRequest(
    query=query,
    case_ids=[case_id],
    top_k=20
)
semantic_results = search_engine.search(semantic_search)

# Merge and deduplicate
merged_results = merge_search_results(
    entity_results.results,
    semantic_results.results,
    max_results=50
)

# Add citation context
enhanced_results = graph_rag.add_citation_context(
    search_results=merged_results,
    case_id=case_id
)
```

## Configuration

### Entity Extraction Settings

```python
# Minimum confidence for entity extraction
MIN_ENTITY_CONFIDENCE = 0.5  # 0-1

# Maximum graph hops for entity relationships
MAX_ENTITY_HOPS = 1  # 1-3 recommended

# Entity-enhanced search call
doc_ids = await graph_rag.entity_enhanced_search(
    query=query,
    case_id=case_id,
    db=db,
    min_confidence=MIN_ENTITY_CONFIDENCE,
    max_hops=MAX_ENTITY_HOPS
)
```

### Citation Ranking Settings

```python
# Citation boost weight (0-1)
# 0.0 = no boost, 1.0 = up to 100% boost
CITATION_BOOST_WEIGHT = 0.15  # 15% max boost recommended

# PageRank parameters
CITATION_DAMPING = 0.85  # Standard PageRank value
CITATION_ITERATIONS = 10  # Sufficient for convergence

# Citation enhancement call
enhanced_results = graph_rag.add_citation_context(
    search_results=results,
    case_id=case_id,
    citation_boost_weight=CITATION_BOOST_WEIGHT
)
```

## Performance Optimization

### 1. Cache Entity Service

Entity extraction can be slow on first run. Cache the service instance:

```python
from functools import lru_cache

@lru_cache(maxsize=1)
def get_graph_rag_engine():
    return create_graph_rag_engine(neo4j_client, entity_service)

# Use in endpoints
graph_rag = get_graph_rag_engine()
```

### 2. Async Processing

Entity extraction is I/O bound. Use async properly:

```python
import asyncio

# Run entity extraction and vector search in parallel
entity_task = graph_rag.entity_enhanced_search(query, case_id, db)
search_task = search_engine.search_async(request)

entity_docs, search_results = await asyncio.gather(
    entity_task,
    search_task
)
```

### 3. Cache Citation Graphs

Citation graphs are stable. Cache per case:

```python
from cachetools import TTLCache
import time

# Cache citation graphs for 5 minutes
citation_cache = TTLCache(maxsize=100, ttl=300)

def get_cached_case_graph(case_id):
    if case_id not in citation_cache:
        citation_cache[case_id] = neo4j_client.get_case_graph(case_id)
    return citation_cache[case_id]
```

### 4. Batch Entity Queries

For multiple searches, batch entity queries:

```python
# Get all unique entities first
all_entities = set()
for query in queries:
    entities = await extract_entities(query)
    all_entities.update(entities)

# Single graph query for all entities
related_docs = neo4j_client.find_related_documents(
    entity_texts=list(all_entities),
    case_id=case_id
)
```

## Monitoring and Debugging

### Add Logging

```python
import logging

logger = logging.getLogger(__name__)

# Log entity extraction results
logger.info(
    f"Entity search found {len(entity_doc_ids)} docs "
    f"for query: {query[:100]}..."
)

# Log citation enhancements
logger.info(
    f"Citation boost: avg={avg_boost:.3f}, "
    f"max={max_boost:.3f}, "
    f"highly_cited_count={highly_cited_count}"
)
```

### Track Metrics

```python
from prometheus_client import Counter, Histogram

# Metrics
entity_searches = Counter(
    "graph_rag_entity_searches_total",
    "Total entity-enhanced searches"
)
entity_docs_found = Histogram(
    "graph_rag_entity_docs_found",
    "Number of entity-related documents found"
)
citation_boosts = Histogram(
    "graph_rag_citation_boost",
    "Citation boost amounts"
)

# Track
entity_searches.inc()
entity_docs_found.observe(len(entity_doc_ids))
citation_boosts.observe(avg_boost)
```

### Debug Output

Enable debug output in results:

```python
# Add debug metadata
for result in enhanced_results:
    result["_debug"] = {
        "entity_matched": result["document_id"] in entity_doc_set,
        "citation_score": result["metadata"]["citation"]["citation_score"],
        "citation_boost": result["metadata"]["citation_boost"],
        "original_score": result["_original_score"]
    }
```

## Testing

See `test_graph_rag.py` for comprehensive unit tests.

Run tests:
```bash
pytest app/services/search/test_graph_rag.py -v
```

## Troubleshooting

### Issue: No entity-enhanced docs found

**Cause:** Low confidence entities or no entities in query

**Solution:**
- Lower `min_confidence` threshold
- Check entity extraction logs
- Verify entities exist in Neo4j

### Issue: Citation boost has no effect

**Cause:** No citations in case or low citation connectivity

**Solution:**
- Verify citations are indexed in Neo4j
- Increase `citation_boost_weight`
- Check citation graph with `get_case_graph()`

### Issue: Slow performance

**Cause:** Entity extraction or graph queries

**Solution:**
- Cache entity service instance
- Use async properly
- Cache citation graphs
- Add indexes to Neo4j

## Next Steps

1. **Monitor performance**: Track entity extraction and citation query times
2. **Tune parameters**: Adjust confidence thresholds and boost weights
3. **Add features**: Multi-hop reasoning, temporal analysis, entity disambiguation
4. **Scale**: Consider caching and query optimization for large cases

## Support

For issues or questions:
- Check logs: `app/services/search/graph_rag.py`
- Review tests: `app/services/search/test_graph_rag.py`
- See examples: `app/services/search/example_usage.py`
