# Embedding Pipeline - Quick Start Guide

## Overview

The LegalEase embedding pipeline generates both **dense** and **sparse** vectors for hybrid search with Qdrant. This enables powerful semantic search combined with keyword matching for legal documents.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Document Processing                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          │                       │
┌─────────▼──────────┐  ┌────────▼─────────┐
│ EmbeddingPipeline  │  │  BM25Encoder     │
│  (Dense Vectors)   │  │ (Sparse Vectors) │
└─────────┬──────────┘  └────────┬─────────┘
          │                      │
          │     768-dim dense    │  Variable sparse
          │     embeddings       │  token weights
          │                      │
          └──────────┬───────────┘
                     │
          ┌──────────▼──────────┐
          │  Qdrant Collection  │
          │   Hybrid Search     │
          └─────────────────────┘
```

## Key Files

### Core Components

| File | Purpose | LOC |
|------|---------|-----|
| `app/workers/pipelines/embeddings.py` | Dense vector generation | 286 |
| `app/workers/pipelines/bm25_encoder.py` | Sparse vector generation | 308 |
| `app/workers/pipelines/__init__.py` | Exports | 44 |

### Documentation & Examples

| File | Purpose |
|------|---------|
| `app/workers/pipelines/README.md` | Full API documentation |
| `app/workers/pipelines/INTEGRATION_EXAMPLE.py` | Real-world integration examples |
| `test_pipelines_simple.py` | Working test suite |

## Quick Start

### 1. Installation

Already installed! Dependencies are in `pyproject.toml`:
- `sentence-transformers>=5.1.1` ✓
- `torch>=2.8.0` ✓

### 2. Basic Usage

```python
from app.workers.pipelines import EmbeddingPipeline, BM25Encoder

# Initialize pipelines
embedding = EmbeddingPipeline()
bm25 = BM25Encoder()

# Fit BM25 on corpus
corpus = ["doc1 text", "doc2 text", "doc3 text"]
bm25.fit(corpus)

# Generate vectors for a document
document = "This is a legal contract between parties."

# Dense embedding (768-dim)
dense = embedding.generate_single_embedding(document)

# Sparse BM25 vector
sparse_idx, sparse_vals = bm25.encode_to_qdrant_format(document)

# Create Qdrant point
point = {
    "id": doc_id,
    "vector": {
        "dense": dense.tolist(),
        "sparse": {
            "indices": sparse_idx,
            "values": sparse_vals,
        },
    },
    "payload": {"text": document, "type": "contract"},
}
```

### 3. Run Tests

```bash
# Simple test (recommended)
uv run python test_pipelines_simple.py

# Expected output:
# ✓ Dense embeddings test PASSED
# ✓ BM25 sparse vectors test PASSED
# ✓ Combined pipeline test PASSED
# ALL TESTS PASSED!
```

## Features

### EmbeddingPipeline (Dense Vectors)

✓ Automatic GPU/CPU detection (CUDA available)
✓ Model caching for performance
✓ Batch processing (32 docs/batch default)
✓ Multi-size support (summary/section/microblock)
✓ Normalized embeddings (cosine similarity ready)
✓ Default model: BAAI/bge-base-en-v1.5 (768-dim)

### BM25Encoder (Sparse Vectors)

✓ BM25 algorithm for keyword relevance
✓ Legal-specific stopword filtering
✓ Configurable parameters (k1=1.5, b=0.75)
✓ Qdrant-compatible sparse format
✓ Token preprocessing & normalization
✓ Vocabulary management & persistence

## Performance

### GPU Acceleration

```python
pipeline = EmbeddingPipeline()
print(pipeline.device)  # "cuda" ✓

# Model info:
# - device: cuda
# - cuda_available: True
# - embedding_dim: 768
```

### Batch Processing

```python
# Process 1000 documents efficiently
texts = [...]  # 1000 documents
embeddings = pipeline.generate_embeddings(
    texts,
    show_progress=True  # Shows progress bar
)
# Shape: (1000, 768)
```

### Model Caching

Models are cached at class level:
```python
# First instance: loads model (~3 seconds)
pipeline1 = EmbeddingPipeline()

# Second instance: reuses cached model (~instant)
pipeline2 = EmbeddingPipeline()
```

## Integration Examples

### Example 1: Index Document Chunks

```python
def index_document(doc_id, chunks, metadata):
    embedding = EmbeddingPipeline()
    bm25 = BM25Encoder()
    bm25.fit(chunks)

    # Generate all embeddings
    dense_vecs = embedding.generate_embeddings(chunks)
    sparse_vecs = bm25.batch_encode_to_qdrant_format(chunks)

    # Create points
    points = []
    for i, (chunk, dense, (sp_idx, sp_vals)) in enumerate(
        zip(chunks, dense_vecs, sparse_vecs)
    ):
        points.append({
            "id": f"{doc_id}_{i}",
            "vector": {
                "dense": dense.tolist(),
                "sparse": {"indices": sp_idx, "values": sp_vals},
            },
            "payload": {"doc_id": doc_id, "text": chunk, **metadata},
        })

    # Upload to Qdrant
    # client.upsert(collection_name="legal_docs", points=points)
    return points
```

### Example 2: Multi-Granularity Indexing

```python
def index_multi_level(doc_id, summary, sections, microblocks):
    embedding = EmbeddingPipeline()

    # Generate embeddings by size
    embeddings = embedding.generate_embeddings_by_size({
        "summary": [summary],
        "section": sections,
        "microblock": microblocks,
    })

    # embeddings["summary"].shape = (1, 768)
    # embeddings["section"].shape = (N, 768)
    # embeddings["microblock"].shape = (M, 768)
```

### Example 3: Semantic Search

```python
def search(query, top_k=10):
    embedding = EmbeddingPipeline()
    bm25 = BM25Encoder()  # Pre-fitted on corpus

    # Generate query vectors
    query_dense = embedding.generate_single_embedding(query)
    query_sparse = bm25.encode_to_qdrant_format(query)

    # Search Qdrant with hybrid vectors
    # results = client.search(
    #     collection_name="legal_docs",
    #     query_vector={
    #         "dense": query_dense.tolist(),
    #         "sparse": query_sparse,
    #     },
    #     limit=top_k
    # )
```

## Qdrant Collection Setup

```python
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, SparseVectorParams, SparseIndexParams
)

client = QdrantClient(host="localhost", port=6333)

client.create_collection(
    collection_name="legal_documents",
    vectors_config={
        "dense": VectorParams(
            size=768,  # BGE-base dimension
            distance=Distance.COSINE,
        ),
    },
    sparse_vectors_config={
        "sparse": SparseVectorParams(
            index=SparseIndexParams(),
        ),
    },
)
```

## Model Options

### Recommended Models

| Model | Dimension | Quality | Speed | Use Case |
|-------|-----------|---------|-------|----------|
| **BAAI/bge-base-en-v1.5** (default) | 768 | ★★★★☆ | ★★★★☆ | Production (balanced) |
| BAAI/bge-large-en-v1.5 | 1024 | ★★★★★ | ★★★☆☆ | High quality needed |
| all-MiniLM-L6-v2 | 384 | ★★★☆☆ | ★★★★★ | Fast inference |

### Change Model

```python
# At initialization
pipeline = EmbeddingPipeline(model_name="BAAI/bge-large-en-v1.5")

# Or dynamically
embeddings = pipeline.generate_embeddings(
    texts,
    model="sentence-transformers/all-MiniLM-L6-v2"
)
```

## Test Results

```
================================================================================
Testing Dense Embeddings
================================================================================
Model info: {
  'model_name': 'BAAI/bge-base-en-v1.5',
  'device': 'cuda',
  'embedding_dim': 768,
  'batch_size': 32,
  'normalize_embeddings': True,
  'cuda_available': True
}
Generated embeddings shape: (3, 768)
Similarity between doc 0 and 1: 0.6237
Dense embeddings test PASSED

================================================================================
Testing BM25 Sparse Vectors
================================================================================
Encoder stats: {
  'num_docs': 5,
  'vocab_size': 22,
  'avg_doc_length': 5.0,
  'k1': 1.5,
  'b': 0.75,
  'use_legal_stopwords': True
}
Sparse vector has 4 non-zero dimensions
Top 5 tokens:
  'breach': 1.5234
  'plaintiff': 0.9621
  'contract': 0.9621
  'alleges': 0.2747
BM25 sparse vectors test PASSED

================================================================================
Testing Combined Pipeline for Qdrant
================================================================================
Dense vector dimension: 768
Sparse vector non-zero dims: 6
Qdrant point structure:
  - ID: 1
  - Dense vector length: 768
  - Sparse indices length: 6
  - Sparse values length: 6
  - Payload keys: ['text', 'doc_type']
Combined pipeline test PASSED

********************************************************************************
ALL TESTS PASSED!
********************************************************************************
```

## API Reference

### EmbeddingPipeline

```python
# Initialize
pipeline = EmbeddingPipeline(
    model_name="BAAI/bge-base-en-v1.5",
    device=None,  # Auto-detect
    batch_size=32,
    normalize_embeddings=True,
)

# Generate embeddings
embeddings = pipeline.generate_embeddings(texts)  # (N, 768)
embedding = pipeline.generate_single_embedding(text)  # (768,)

# Multi-size
embs = pipeline.generate_embeddings_by_size({
    "summary": [...],
    "section": [...],
})

# Similarity
score = pipeline.compute_similarity(emb1, emb2)  # -1 to 1

# Info
info = pipeline.get_model_info()
```

### BM25Encoder

```python
# Initialize
encoder = BM25Encoder(
    k1=1.5,
    b=0.75,
    epsilon=0.25,
    use_legal_stopwords=True,
)

# Fit on corpus
encoder.fit(documents)

# Encode
indices, values = encoder.encode_to_qdrant_format(text)
sparse_vecs = encoder.batch_encode_to_qdrant_format(texts)

# Analyze
top_tokens = encoder.get_top_tokens(text, top_k=5)
stats = encoder.get_stats()
```

## Next Steps

1. **Integrate with Celery tasks** - See `INTEGRATION_EXAMPLE.py`
2. **Set up Qdrant collection** - Use the collection setup code above
3. **Index your documents** - Use the indexing examples
4. **Implement search** - Use the search examples

## Support

- Full documentation: `app/workers/pipelines/README.md`
- Integration examples: `app/workers/pipelines/INTEGRATION_EXAMPLE.py`
- Test file: `test_pipelines_simple.py`

## Summary

✓ Production-ready embedding pipeline
✓ Hybrid search (dense + sparse vectors)
✓ GPU acceleration (CUDA detected)
✓ Multi-granularity support
✓ Qdrant-compatible format
✓ Tested and working

**Ready for integration with LegalEase document processing workflow!**
