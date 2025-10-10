# Document Processing Pipeline Guide

Complete implementation of the LegalEase document processing pipeline.

## Overview

The document processing pipeline transforms uploaded legal documents into searchable vector embeddings stored in Qdrant. The pipeline consists of 4 main stages executed by the `process_uploaded_document` Celery task.

## Architecture

```
Document Upload (MinIO)
    ↓
Parse (DoclingParser)
    ↓
Chunk (DocumentChunker)
    ↓
Embed (EmbeddingPipeline + BM25Encoder)
    ↓
Index (QdrantIndexer)
    ↓
Update Database Status
```

## Pipeline Components

### 1. DoclingParser (`app/workers/pipelines/docling_parser.py`)

**Purpose**: Extract text and structure from various document formats

**Features**:
- Multi-format support: PDF, DOCX, DOC, TXT
- PDF parsing with PyMuPDF (with pypdf fallback)
- DOCX parsing with python-docx
- OCR support for scanned documents (Tesseract)
- Metadata extraction

**Example**:
```python
parser = DoclingParser(use_ocr=True)
result = parser.parse(
    file_content=pdf_bytes,
    filename="contract.pdf"
)
# result = {
#     "text": "full document text...",
#     "pages": [...],
#     "metadata": {...},
#     "structure": {...}
# }
```

### 2. DocumentChunker (`app/workers/pipelines/chunker.py`)

**Purpose**: Split documents into hierarchical chunks for multi-level search

**Chunking Strategy** (following RAGFlow pattern):
- **Summary**: Document-level overview (up to 2000 tokens)
- **Section**: Logical sections (up to 500 tokens)
- **Microblock**: Fine-grained chunks (up to 128 tokens)

**Legal-Aware Splitting**:
- Detects legal section markers (Article I, Section 1, WHEREAS, etc.)
- Respects paragraph boundaries
- Configurable overlap for context preservation

**Example**:
```python
chunker = DocumentChunker(
    summary_max_tokens=2000,
    section_max_tokens=500,
    microblock_max_tokens=128,
    overlap_tokens=50
)
chunks = chunker.chunk_document(text)
# chunks = {
#     "summary": [TextChunk(...), ...],
#     "section": [TextChunk(...), ...],
#     "microblock": [TextChunk(...), ...]
# }
```

### 3. EmbeddingPipeline (`app/workers/pipelines/embeddings.py`)

**Purpose**: Generate dense vector embeddings for semantic search

**Features**:
- Model: BAAI/bge-base-en-v1.5 (768 dimensions)
- Automatic GPU/CPU detection
- Batch processing for efficiency
- Model caching for performance
- L2 normalization for cosine similarity

**Example**:
```python
embedder = EmbeddingPipeline(model_name="BAAI/bge-base-en-v1.5")
embeddings = embedder.generate_embeddings([
    "chunk text 1",
    "chunk text 2"
])
# embeddings.shape = (2, 768)
```

### 4. BM25Encoder (`app/workers/pipelines/bm25_encoder.py`)

**Purpose**: Generate sparse vectors for keyword-based search

**Features**:
- BM25 algorithm for TF-IDF weighting
- Legal stopword filtering
- Qdrant-compatible sparse vector format
- Configurable parameters (k1, b)

**Example**:
```python
bm25 = BM25Encoder(k1=1.5, b=0.75)
bm25.fit(all_chunk_texts)
indices, values = bm25.encode_to_qdrant_format("query text")
```

### 5. QdrantIndexer (`app/workers/pipelines/indexer.py`)

**Purpose**: Index embeddings into Qdrant vector database

**Features**:
- Multi-vector support (summary, section, microblock)
- Hybrid indexing (dense + sparse vectors)
- Batch upserts for efficiency
- Metadata-rich payloads
- Automatic point ID generation

**Example**:
```python
indexer = QdrantIndexer()
indexer.index_chunks(
    chunks=chunks_list,
    embeddings=embeddings_dict,
    sparse_vectors=sparse_vectors,
    document_id=123,
    case_id=456
)
```

### 6. DocumentProcessor (`app/workers/pipelines/document_pipeline.py`)

**Purpose**: Orchestrate the entire pipeline

**Process Flow**:
1. Parse document → extract text
2. Chunk text → hierarchical chunks
3. Generate embeddings → dense + sparse
4. Index to Qdrant → multi-vector storage

**Example**:
```python
processor = DocumentProcessor(use_ocr=True, use_bm25=True)
result = processor.process(
    file_content=file_bytes,
    filename="contract.pdf",
    document_id=123,
    case_id=456
)

if result.success:
    print(f"Processed {result.data['chunks_count']} chunks")
else:
    print(f"Failed at {result.stage}: {result.error}")
```

## Celery Task Implementation

### `process_uploaded_document`

**Location**: `app/workers/tasks/document_processing.py`

**Workflow**:
1. Fetch document record from PostgreSQL
2. Update status to PROCESSING
3. Download file from MinIO
4. Process through DocumentProcessor
5. Update document metadata
6. Set status to COMPLETED (or FAILED on error)

**Usage**:
```python
from app.workers.tasks.document_processing import process_uploaded_document

# Automatically called by document upload endpoint
task = process_uploaded_document.delay(document_id=123)

# Monitor progress
status = task.status  # PENDING, STARTED, SUCCESS, FAILURE
result = task.get(timeout=300)
```

## Database Integration

### Document Status Tracking

The Document model tracks processing status:

```python
class DocumentStatus(str, Enum):
    PENDING = "PENDING"         # Uploaded, waiting for processing
    PROCESSING = "PROCESSING"   # Currently being processed
    COMPLETED = "COMPLETED"     # Successfully processed
    FAILED = "FAILED"           # Processing failed
```

### Metadata Storage

Processing results are stored in `Document.meta_data`:

```json
{
    "chunks_count": 45,
    "text_length": 15000,
    "pages_count": 10,
    "processing_stage": "completed",
    "processed_at": "2025-10-09T20:00:00"
}
```

On failure:
```json
{
    "error": "MinIO download failed: Connection timeout",
    "error_stage": "processing"
}
```

## Qdrant Storage Schema

### Point Structure

Each chunk is stored as a Qdrant point:

```python
{
    "id": "uuid-123-456",
    "vector": {
        "summary": [0.1, 0.2, ..., 0.8],      # 768-dim dense
        "section": [0.1, 0.2, ..., 0.8],      # 768-dim dense
        "microblock": [0.1, 0.2, ..., 0.8],   # 768-dim dense
        "bm25": SparseVector(indices=[...], values=[...])
    },
    "payload": {
        "text": "chunk text content",
        "chunk_type": "section",
        "position": 5,
        "page_number": 2,
        "document_id": 123,
        "case_id": 456,
        "char_count": 850,
        "word_count": 150
    }
}
```

## Error Handling

### Comprehensive Logging

All stages log detailed progress:
```
INFO: Processing document 123: contract.pdf
INFO: Downloading document from MinIO: cases/456/abc_contract.pdf
INFO: Downloaded 1048576 bytes from MinIO
INFO: Starting document processing pipeline
INFO: Stage 1/4: Parsing document
INFO: Parsed document: 15000 chars, 10 pages
INFO: Stage 2/4: Chunking document
INFO: Created 45 chunks
INFO: Stage 3/4: Generating embeddings
INFO: Generating section embeddings for 30 chunks
INFO: Generating BM25 sparse vectors
INFO: Stage 4/4: Indexing to Qdrant
INFO: Successfully indexed 45 points
INFO: Document 123 processed successfully
```

### Error Recovery

Errors at any stage:
1. Log detailed error with traceback
2. Update document status to FAILED
3. Store error message in metadata
4. Return failure result

## Performance Optimization

### GPU Acceleration
- Embeddings automatically use CUDA if available
- Fallback to CPU for compatibility
- Set `CUDA_VISIBLE_DEVICES` to control GPU selection

### Batch Processing
- Embeddings: 32 texts per batch (configurable)
- Qdrant indexing: 100 points per batch
- BM25 encoding: Single pass over corpus

### Memory Management
- Streaming downloads from MinIO
- Model caching for repeated tasks
- Efficient sparse vector encoding

## Configuration

### Environment Variables

```bash
# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=legalease_documents

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=legalease

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Pipeline Parameters

```python
DocumentProcessor(
    use_ocr=True,              # Enable OCR for scanned docs
    use_bm25=True,             # Generate sparse vectors
    embedding_model="BAAI/bge-base-en-v1.5",
    summary_max_tokens=2000,
    section_max_tokens=500,
    microblock_max_tokens=128
)
```

## Testing

### Test Pipeline Components

```bash
# Test parser
python -c "from app.workers.pipelines import DoclingParser; print('OK')"

# Test chunker
python -c "from app.workers.pipelines import DocumentChunker; print('OK')"

# Test embedder
python -c "from app.workers.pipelines import EmbeddingPipeline; print('OK')"

# Test full pipeline
python -c "from app.workers.pipelines import DocumentProcessor; print('OK')"
```

### Test Celery Task

```python
from app.workers.tasks.document_processing import process_uploaded_document

# Test with actual document
task = process_uploaded_document.delay(document_id=1)
result = task.get(timeout=300)
print(result)
```

## Monitoring

### Worker Status
```bash
celery -A app.workers.celery_app inspect active
celery -A app.workers.celery_app inspect stats
```

### Task Results
```bash
# Check document processing status
SELECT id, status, meta_data FROM documents WHERE id = 123;
```

### Qdrant Health
```python
from app.core.qdrant import get_collection_info
info = get_collection_info()
print(f"Points: {info['vectors_count']}")
```

## Dependencies

All required packages are in `pyproject.toml`:
- `pymupdf>=1.25.3` - PDF parsing
- `pypdf>=5.1.0` - PDF fallback
- `python-docx>=1.1.2` - DOCX parsing
- `pytesseract>=0.3.13` - OCR
- `sentence-transformers>=5.1.1` - Embeddings
- `torch>=2.0.0` - ML backend
- `qdrant-client>=1.15.1` - Vector storage
- `numpy>=1.26.0` - Numerical ops

## Best Practices

1. **Document Upload**
   - Validate file types before upload
   - Check file size limits
   - Use unique object names in MinIO

2. **Processing**
   - Monitor task queue length
   - Set appropriate worker concurrency
   - Use autoscaling for production

3. **Error Handling**
   - Check document status before download
   - Implement retry logic for transient errors
   - Log detailed error context

4. **Performance**
   - Use GPU for embeddings when available
   - Monitor memory usage
   - Scale workers horizontally

5. **Monitoring**
   - Track processing success rate
   - Monitor average processing time
   - Alert on high failure rates
   - Check Qdrant collection size

## Future Enhancements

- [ ] Entity extraction with spaCy
- [ ] Table extraction and indexing
- [ ] Image OCR improvements
- [ ] Multi-language support
- [ ] Advanced chunking strategies
- [ ] Incremental indexing
- [ ] Document deduplication
- [ ] Custom embedding models
