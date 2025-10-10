# Embedding Generation Pipeline

Production-ready embedding generation pipeline for LegalEase document processing. Generates both dense and sparse vectors for hybrid search with Qdrant.

## Components

### 1. EmbeddingPipeline (`embeddings.py`)

Generates dense vector embeddings using sentence-transformers.

**Features:**
- Automatic GPU/CPU detection
- Model caching for performance
- Batch processing support
- Multi-size embeddings (summary/section/microblock)
- Normalized embeddings for cosine similarity

**Usage:**

```python
from app.workers.pipelines import EmbeddingPipeline

# Initialize pipeline
pipeline = EmbeddingPipeline(
    model_name="BAAI/bge-base-en-v1.5",  # Default model
    batch_size=32,
    normalize_embeddings=True,
)

# Generate embeddings for texts
texts = [
    "This is a contract for the sale of goods.",
    "The plaintiff seeks damages for breach.",
]
embeddings = pipeline.generate_embeddings(texts)
# Returns: numpy array of shape (2, 768)

# Single embedding
embedding = pipeline.generate_single_embedding("Legal document text")
# Returns: numpy array of shape (768,)

# Multi-size embeddings
texts_by_size = {
    "summary": ["Document summary"],
    "section": ["Section 1 text", "Section 2 text"],
    "microblock": ["Sentence 1", "Sentence 2", "Sentence 3"],
}
embeddings_by_size = pipeline.generate_embeddings_by_size(texts_by_size)
# Returns: {"summary": array(1, 768), "section": array(2, 768), ...}

# Compute similarity
similarity = pipeline.compute_similarity(embedding1, embedding2)
# Returns: float between -1 and 1
```

### 2. BM25Encoder (`bm25_encoder.py`)

Generates BM25-based sparse vectors for keyword matching.

**Features:**
- BM25 algorithm for relevance scoring
- Legal-specific stopword filtering
- Token preprocessing
- Qdrant-compatible sparse vector format
- Configurable parameters (k1, b)

**Usage:**

```python
from app.workers.pipelines import BM25Encoder

# Initialize encoder
encoder = BM25Encoder(
    k1=1.5,              # Term frequency saturation
    b=0.75,              # Length normalization
    use_legal_stopwords=True,
)

# Fit on corpus
corpus = [
    "This is a contract between parties.",
    "The plaintiff seeks damages.",
    "The court finds in favor of plaintiff.",
]
encoder.fit(corpus)

# Encode single text
text = "The plaintiff alleges breach of contract."
indices, values = encoder.encode_to_qdrant_format(text)
# Returns: (indices=[...], values=[...]) for Qdrant sparse vector

# Batch encoding
texts = ["Text 1", "Text 2", "Text 3"]
sparse_vectors = encoder.batch_encode_to_qdrant_format(texts)
# Returns: [(indices, values), (indices, values), ...]

# Get top tokens
top_tokens = encoder.get_top_tokens(text, top_k=5)
# Returns: [("breach", 1.52), ("contract", 0.96), ...]

# Get statistics
stats = encoder.get_stats()
# Returns: {"num_docs": 3, "vocab_size": 15, "avg_doc_length": 5.3, ...}
```

## Combined Usage for Qdrant

Generate both dense and sparse vectors for hybrid search:

```python
from app.workers.pipelines import EmbeddingPipeline, BM25Encoder

# Initialize pipelines
embedding_pipeline = EmbeddingPipeline()
bm25_encoder = BM25Encoder()

# Fit BM25 on your corpus
corpus = [...] # Your document corpus
bm25_encoder.fit(corpus)

# For each document to index:
document = "Legal document text to be indexed"

# Generate dense embedding
dense_vector = embedding_pipeline.generate_single_embedding(document)

# Generate sparse vector
sparse_indices, sparse_values = bm25_encoder.encode_to_qdrant_format(document)

# Create Qdrant point
point = {
    "id": doc_id,
    "vector": {
        "dense": dense_vector.tolist(),
        "sparse": {
            "indices": sparse_indices,
            "values": sparse_values,
        },
    },
    "payload": {
        "text": document,
        "doc_type": "contract",
        "metadata": {...},
    },
}

# Upsert to Qdrant
# qdrant_client.upsert(collection_name="legal_docs", points=[point])
```

## Qdrant Collection Setup

Create a Qdrant collection with both dense and sparse vectors:

```python
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    SparseVectorParams,
    SparseIndexParams,
)

client = QdrantClient(host="localhost", port=6333)

# Create collection with hybrid vectors
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

## Performance Considerations

### GPU Acceleration

The pipeline automatically detects and uses CUDA if available:

```python
pipeline = EmbeddingPipeline()  # Auto-detects GPU
print(pipeline.device)  # "cuda" or "cpu"

# Force CPU usage
pipeline = EmbeddingPipeline(device="cpu")
```

### Batch Processing

For large datasets, use batch processing:

```python
# Process 1000 documents in batches of 32
texts = [...]  # 1000 texts
embeddings = pipeline.generate_embeddings(texts, show_progress=True)
```

### Model Caching

Models are cached at the class level to avoid reloading:

```python
# First instance loads model
pipeline1 = EmbeddingPipeline()

# Second instance reuses cached model
pipeline2 = EmbeddingPipeline()

# Clear cache if needed
EmbeddingPipeline.clear_cache()
```

## Model Options

### Recommended Models

1. **BAAI/bge-base-en-v1.5** (default)
   - Size: 768 dimensions
   - Best balance of quality/speed
   - Optimized for retrieval

2. **BAAI/bge-large-en-v1.5**
   - Size: 1024 dimensions
   - Higher quality
   - Slower inference

3. **sentence-transformers/all-MiniLM-L6-v2**
   - Size: 384 dimensions
   - Faster inference
   - Lower quality

### Changing Models

```python
pipeline = EmbeddingPipeline(model_name="BAAI/bge-large-en-v1.5")

# Or switch dynamically
embeddings = pipeline.generate_embeddings(
    texts,
    model="sentence-transformers/all-MiniLM-L6-v2"
)
```

## Testing

Run the test suite:

```bash
# Simple test
uv run python test_pipelines_simple.py

# Full test suite
uv run python test_embedding_pipeline.py
```

## API Reference

### EmbeddingPipeline

#### Methods

- `__init__(model_name, device, batch_size, normalize_embeddings)`
- `generate_embeddings(texts, model, show_progress, convert_to_numpy) -> np.ndarray`
- `generate_single_embedding(text, model) -> np.ndarray`
- `generate_embeddings_by_size(texts_dict, model) -> Dict[str, np.ndarray]`
- `batch_generate(texts, batch_size, model) -> List[np.ndarray]`
- `compute_similarity(embedding1, embedding2) -> float`
- `get_model_info() -> Dict`
- `clear_cache()` (class method)

### BM25Encoder

#### Methods

- `__init__(k1, b, epsilon, use_legal_stopwords)`
- `fit(documents) -> None`
- `encode(text) -> Dict[str, float]`
- `encode_to_qdrant_format(text, token_to_id) -> Tuple[List[int], List[float]]`
- `batch_encode_to_qdrant_format(texts) -> List[Tuple[List[int], List[float]]]`
- `get_top_tokens(text, top_k) -> List[Tuple[str, float]]`
- `get_stats() -> Dict`
- `tokenize(text) -> List[str]`

## Environment Variables

None required. All configuration is done through constructor parameters.

## Dependencies

- `sentence-transformers>=5.1.1`
- `torch>=2.8.0`
- `numpy`

All dependencies are already installed in the project.
