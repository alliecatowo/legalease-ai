# Haystack Document Indexing Pipelines

This module provides production-ready Haystack 2.x indexing pipelines for legal evidence processing with dual-store architecture (Qdrant + OpenSearch).

## Architecture

### Dual-Store Design
- **Qdrant**: Dense vector search using FastEmbed (ONNX-optimized)
- **OpenSearch**: BM25 sparse search with legal terminology analysis
- **Atomic writes**: Rollback on failure to ensure data consistency

### Evidence Types
1. **Documents**: PDF, DOCX, DOC, TXT files
2. **Transcripts**: Audio/video transcriptions with speaker diarization
3. **Communications**: Cellebrite exports (messages, emails, chats)

## Components

### Document Processing (`components/`)

#### Converters
- **DoclingDocumentConverter**: Wraps existing Docling parser for multi-format document conversion
- **TranscriptSegmentConverter**: Converts transcript segments to Haystack Documents
- **CommunicationConverter**: Converts communication entities to Documents

#### Cleaners & Chunkers
- **LegalDocumentCleaner**: Removes headers, footers, page numbers, normalizes whitespace
- **SpeakerAwareChunker**: Chunks transcripts by speaker turns with configurable size
- **ThreadGrouper**: Groups communications by thread for better context

#### Embedders
- **FastEmbedDocumentEmbedder**: Dense embeddings using FastEmbed (ONNX)
- **FastEmbedQueryEmbedder**: Query-optimized embeddings
- **SparseEmbedder**: Placeholder for BM25 (handled by OpenSearch)

### Store Writers (`stores/`)

#### DualStoreWriter
Custom Haystack component that writes to both stores atomically:
- Writes to Qdrant first (dense vectors)
- Then writes to OpenSearch (BM25)
- Automatic rollback on failure
- Support for all three evidence types

## Pipelines

### 1. Document Indexing Pipeline

**Flow:**
```
File Path → DoclingConverter → Cleaner → [Chunker]
→ Dense Embedder (3 levels) → Sparse Embedder → DualStoreWriter
```

**Features:**
- Multi-format support (PDF, DOCX, DOC, TXT)
- OCR for scanned documents
- Hierarchical embeddings (summary, section, microblock)
- Metadata extraction (page numbers, bounding boxes)

**Usage:**
```python
from app.infrastructure.ai.haystack.pipelines import create_document_pipeline

# Create pipeline
async with PipelineFactory() as factory:
    pipeline = await factory.create_document_indexing_pipeline(
        use_ocr=True,
        model_name="BAAI/bge-small-en-v1.5",
        batch_size=100
    )

    # Index document
    result = await pipeline.run(
        file_path="/path/to/document.pdf",
        case_id=case_uuid,
        document_id=doc_uuid,
        chunks=chunks  # Pre-chunked Chunk value objects
    )

    print(f"Indexed {result['chunks_indexed']} chunks")
```

### 2. Transcript Indexing Pipeline

**Flow:**
```
TranscriptSegments → Converter → SpeakerChunker
→ Dense Embedder → Sparse Embedder → DualStoreWriter
```

**Features:**
- Speaker-aware chunking
- Temporal metadata preservation
- Confidence score tracking
- Word-level timing support

**Usage:**
```python
from app.infrastructure.ai.haystack.pipelines import create_transcript_pipeline

# Create pipeline
async with PipelineFactory() as factory:
    pipeline = await factory.create_transcript_indexing_pipeline(
        max_chunk_size=500
    )

    # Index transcript
    result = await pipeline.run(
        segments=transcript_segments,  # List[TranscriptSegment]
        transcript_id=transcript_uuid,
        case_id=case_uuid
    )

    print(f"Indexed {result['segments_indexed']} segments")
```

### 3. Communication Indexing Pipeline

**Flow:**
```
Communications → Converter → ThreadGrouper
→ Dense Embedder → Sparse Embedder → DualStoreWriter
```

**Features:**
- Thread-based grouping
- Participant metadata preservation
- Platform and device tracking
- Attachment metadata

**Usage:**
```python
from app.infrastructure.ai.haystack.pipelines import create_communication_pipeline

# Create pipeline
async with PipelineFactory() as factory:
    pipeline = await factory.create_communication_indexing_pipeline(
        max_messages_per_group=10
    )

    # Index communications
    result = await pipeline.run(
        communications=comms,  # List[Communication]
        case_id=case_uuid
    )

    print(f"Indexed {result['communications_indexed']} communications")
```

## Pipeline Factory

The `PipelineFactory` provides dependency injection and configuration management:

```python
from app.infrastructure.ai.haystack.pipelines import PipelineFactory

# Use as context manager (recommended)
async with PipelineFactory() as factory:
    doc_pipeline = await factory.create_document_indexing_pipeline()
    transcript_pipeline = await factory.create_transcript_indexing_pipeline()
    comm_pipeline = await factory.create_communication_indexing_pipeline()

    # Use pipelines...
    # Resources automatically cleaned up on exit

# Or manual cleanup
factory = PipelineFactory()
pipeline = await factory.create_document_indexing_pipeline()
# ... use pipeline ...
await factory.close()
```

## Configuration

Pipelines use settings from `app.core.config`:

```python
# Embedding configuration
model_name: str = "BAAI/bge-small-en-v1.5"  # FastEmbed model
batch_size: int = 100  # Embedding batch size

# Document pipeline
use_ocr: bool = True  # Enable OCR for scanned docs

# Transcript pipeline
max_chunk_size: int = 500  # Max chars per speaker turn

# Communication pipeline
max_messages_per_group: int = 10  # Max messages per thread group
```

## Error Handling

All pipelines return a standardized result structure:

```python
{
    "success": bool,
    "chunks_indexed": int,  # or segments_indexed, communications_indexed
    "errors": List[str]
}
```

The `DualStoreWriter` ensures atomicity:
1. Write to Qdrant
2. If successful, write to OpenSearch
3. If OpenSearch fails, rollback Qdrant write
4. Return detailed error information

## Repository Integration

Pipelines use repository pattern for data access:

**Qdrant Repositories:**
- `QdrantDocumentRepository`
- `QdrantTranscriptRepository`
- `QdrantCommunicationRepository`

**OpenSearch Repositories:**
- `OpenSearchDocumentRepository`
- `OpenSearchTranscriptRepository`
- `OpenSearchCommunicationRepository`

All injected via `PipelineFactory` with proper connection management.

## Testing

```python
import pytest
from uuid import uuid4
from app.infrastructure.ai.haystack.pipelines import PipelineFactory
from app.domain.evidence.value_objects.chunk import Chunk, ChunkType

@pytest.mark.asyncio
async def test_document_indexing():
    async with PipelineFactory() as factory:
        pipeline = await factory.create_document_indexing_pipeline()

        result = await pipeline.run(
            file_path="tests/fixtures/sample.pdf",
            case_id=uuid4(),
            document_id=uuid4(),
            chunks=[
                Chunk(
                    text="Sample chunk text",
                    chunk_type=ChunkType.PARAGRAPH,
                    position=0
                )
            ]
        )

        assert result["success"] is True
        assert result["chunks_indexed"] > 0
```

## Future Enhancements

- [ ] Implement full `LegalChunker` component (currently using placeholder)
- [ ] Add citation-aware chunking
- [ ] Optimize hierarchical embedding generation
- [ ] Add progress callbacks for long-running operations
- [ ] Implement incremental indexing (update vs full reindex)
- [ ] Add embedding model fine-tuning support
- [ ] Optimize batch sizes based on GPU memory
- [ ] Add distributed processing support

## See Also

- Retrieval pipelines: `app/infrastructure/ai/haystack/pipelines/retrieval.py`
- Repository implementations: `app/infrastructure/persistence/`
- Domain entities: `app/domain/evidence/entities/`
- Value objects: `app/domain/evidence/value_objects/`
