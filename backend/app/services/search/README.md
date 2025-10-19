# GraphRAG-Enhanced Search

This module implements GraphRAG (Graph + Retrieval Augmented Generation) for enhanced legal document search.

## Overview

GraphRAG combines vector search with knowledge graph traversal to provide more intelligent and contextual search results. It leverages:

1. **Entity Extraction**: Identifies legal entities (people, organizations, courts, etc.) in queries
2. **Graph Traversal**: Finds related entities and documents through Neo4j knowledge graph
3. **Citation Analysis**: Ranks documents by citation importance using PageRank-style algorithm

## Components

### GraphRAGEngine

Main class that provides two key methods:

#### 1. `entity_enhanced_search()`

Extracts entities from search queries and finds related documents via the knowledge graph.

**How it works:**
1. Extracts entities from the query using GLiNER + LexNLP
2. Finds related entities (1-hop graph traversal)
3. Finds documents mentioning these entities
4. Returns document IDs to boost in vector search

**Example:**
```python
doc_ids = await graph_rag.entity_enhanced_search(
    query="John Doe filed a motion in California Superior Court",
    case_id="case-123",
    db=db_session
)
# Returns: ["doc-1", "doc-5", "doc-12"] - docs mentioning these entities
```

#### 2. `add_citation_context()`

Enhances search results with citation metadata and boosts highly-cited documents.

**How it works:**
1. Gets citation graph from Neo4j for the case
2. Calculates citation centrality using PageRank algorithm
3. Boosts scores of highly-cited documents
4. Adds citation metadata to results

**Example:**
```python
enhanced_results = graph_rag.add_citation_context(
    search_results=vector_search_results,
    case_id="case-123",
    citation_boost_weight=0.15  # 15% max boost from citations
)
# Returns: Results with citation metadata and boosted scores
```

## Integration with Hybrid Search

Here's how to integrate GraphRAG with your existing search pipeline:

```python
from app.services.search.graph_rag import create_graph_rag_engine
from app.services.search.engine import get_search_engine
from app.core.neo4j import neo4j_client
from app.services.entity_service import entity_service

# Initialize
search_engine = get_search_engine()
graph_rag = create_graph_rag_engine(neo4j_client, entity_service)

# Step 1: Entity-enhanced document discovery
entity_doc_ids = await graph_rag.entity_enhanced_search(
    query=query,
    case_id=case_id,
    db=db
)

# Step 2: Hybrid search with entity filtering
search_request = HybridSearchRequest(
    query=query,
    case_ids=[case_id],
    document_ids=entity_doc_ids,  # Focus on entity-related docs
    use_bm25=True,
    use_dense=True,
    top_k=50
)
search_response = search_engine.search(search_request)

# Step 3: Citation enhancement
final_results = graph_rag.add_citation_context(
    search_results=search_response.results,
    case_id=case_id
)
```

## Entity Extraction

The entity service extracts legal entities using three methods:

1. **GLiNER**: Zero-shot NER for general entities (PERSON, ORG, etc.)
2. **LexNLP**: Legal-specific extraction (citations, courts, acts, amounts)
3. **Regex**: Pattern matching for emails, phones, case numbers

Supported entity types:
- **People**: PERSON, ATTORNEY, JUDGE, CLIENT, PARTY
- **Organizations**: ORGANIZATION, LAW_FIRM, COMPANY, GOVERNMENT_AGENCY, COURT
- **Legal**: CITATION, ACT, CASE_NUMBER, STATUTE
- **Financial**: AMOUNT, MONEY, CURRENCY
- **Temporal**: DATE, DURATION
- **Other**: EMAIL, PHONE, LOCATION

## Citation Analysis

The citation centrality algorithm works like PageRank:

1. Build citation graph from Neo4j
2. Initialize all documents with equal scores
3. Iteratively propagate scores based on citations
4. Documents cited by important documents get higher scores

**Parameters:**
- `damping_factor`: 0.85 (standard PageRank value)
- `iterations`: 10 (sufficient for convergence)
- `citation_boost_weight`: 0.15 (max 15% score boost)

## Configuration

```python
# Entity extraction settings
min_confidence = 0.5  # Minimum confidence for entities
max_hops = 1         # Graph traversal depth

# Citation settings
citation_boost_weight = 0.15  # 0-1, how much to boost by citations
damping_factor = 0.85         # PageRank damping
iterations = 10               # PageRank iterations
```

## Performance Considerations

1. **Entity extraction**: Can be slow on first run (model loading)
   - Consider caching entity service instance
   - Use async for non-blocking extraction

2. **Graph queries**: Neo4j queries are fast but can accumulate
   - Results are batched where possible
   - Consider caching citation graphs per case

3. **Citation calculation**: O(n×i) where n=docs, i=iterations
   - Typically <10ms for cases with <1000 documents
   - Calculation is done once per search

## Example Output

### Entity-Enhanced Search

```json
{
  "query": "John Doe vs Acme Corp contract dispute",
  "entities_found": [
    {"text": "John Doe", "type": "PERSON", "confidence": 0.95},
    {"text": "Acme Corp", "type": "ORGANIZATION", "confidence": 0.92},
    {"text": "contract", "type": "LEGAL_TERM", "confidence": 0.88}
  ],
  "related_entities": [
    "Jane Smith",      // Co-mentioned with John Doe
    "Acme Holdings",   // Related to Acme Corp
    "breach of contract"  // Related legal term
  ],
  "document_ids": ["doc-1", "doc-5", "doc-12", "doc-18"]
}
```

### Citation-Enhanced Results

```json
{
  "id": "chunk-1",
  "score": 0.92,  // Boosted from 0.85
  "text": "Document text...",
  "metadata": {
    "citation": {
      "cited_by_count": 5,
      "cites_count": 2,
      "citation_score": 0.78,
      "citation_chain_depth": 3,
      "is_highly_cited": true
    },
    "citation_boost": 0.07
  }
}
```

## Future Enhancements

1. **Multi-hop reasoning**: Expand beyond 1-hop entity traversal
2. **Temporal analysis**: Consider citation recency
3. **Entity disambiguation**: Handle entities with same name
4. **Citation types**: Distinguish positive/negative citations
5. **Document clustering**: Group related documents by entity co-occurrence

## References

- [GraphRAG Paper](https://arxiv.org/abs/2404.16130)
- [Neo4j Graph Data Science](https://neo4j.com/docs/graph-data-science/)
- [PageRank Algorithm](https://en.wikipedia.org/wiki/PageRank)
- [GLiNER: Generalist and Lightweight Named Entity Recognition](https://arxiv.org/abs/2311.08526)
- [LexNLP: Legal NLP Library](https://github.com/LexPredict/lexpredict-lexnlp)
