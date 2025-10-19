# End-to-End Pipeline Test

Comprehensive test suite for validating the complete document processing pipeline.

## Quick Start

### Test Marker Parser Only
```bash
# Basic test (without LLM)
mise test:marker

# With LLM enhancement (requires GOOGLE_API_KEY)
mise test:marker-llm

# Verbose output
mise test:marker-verbose
```

### Full Pipeline Test
See sections below for complete end-to-end testing.

## What It Tests

### Stage 1: Document Parsing (Marker)
- PDF parsing with VLM (Vision Language Model) support
- Text extraction from complex legal documents
- Page segmentation and structure detection
- Block-level analysis (24 block types)
- Bounding box extraction for precise location tracking
- Metadata extraction

### Stage 2: Hierarchical Chunking
- **Summary chunks**: Document-level overview (max 2000 tokens)
- **Section chunks**: Logical sections (max 500 tokens)
- **Microblock chunks**: Fine-grained paragraphs/sentences (max 128 tokens)
- Semantic splitting on legal markers (WHEREAS, Article, Section, etc.)
- Chunk overlap for context preservation
- Metadata and bounding box preservation

### Stage 3: Embedding Generation
- Dense vector embeddings using FastEmbed
- Model: BAAI/bge-small-en-v1.5 (384 dimensions)
- Memory-efficient batch processing (100 chunks per batch)
- Multi-type embeddings (summary, section, microblock)
- ONNX runtime for 4x faster inference vs PyTorch

### Stage 4: BM25 Encoding
- Sparse vector generation for keyword search
- Token indexing and weighting
- Qdrant-compatible sparse vector format

### Stage 5: Qdrant Indexing
- Multi-vector collection setup
- Point insertion with batch processing
- Named vectors: summary, section, microblock (dense)
- Sparse vector: bm25 (keywords)
- Metadata storage (document_id, case_id, page_number, bboxes)

### Stage 6: Search Retrieval
- **Keyword Search**: BM25 only for exact matches
- **Semantic Search**: Dense vectors for meaning-based retrieval
- **Hybrid Search**: Combined BM25 + dense with RRF/DBSF fusion
- Score normalization and boosting
- Result ranking and filtering

## Prerequisites

1. **Services Running**:
   ```bash
   cd /home/Allie/develop/legalease
   docker-compose up -d
   ```
   
   Requires: Qdrant, PostgreSQL, Redis

2. **Environment Variables**:
   ```bash
   export GOOGLE_API_KEY=your_gemini_api_key  # For Marker VLM
   export QDRANT_HOST=localhost
   export QDRANT_PORT=6333
   ```

3. **Dependencies**:
   ```bash
   cd /home/Allie/develop/legalease/backend
   mise run install  # or: uv sync
   ```

## Usage

### Basic Test (Auto-generated PDF)
```bash
cd /home/Allie/develop/legalease/backend
mise run python scripts/test_full_pipeline.py
```

### Test with Your Own PDF
```bash
mise run python scripts/test_full_pipeline.py --pdf-path /path/to/your/document.pdf
```

### Skip Indexing (Test Parsing Only)
```bash
mise run python scripts/test_full_pipeline.py --skip-indexing
```

### Search Only (Assumes Data Already Indexed)
```bash
mise run python scripts/test_full_pipeline.py --search-only
```

## Expected Output

The script provides detailed output for each stage:

```
================================================================================
END-TO-END DOCUMENT PIPELINE TEST
================================================================================
Start Time: 2025-01-15 10:30:00
PDF Path: Generated sample
Test Document ID: 12345678-1234-5678-1234-567812345678
Test Case ID: 87654321-4321-8765-4321-876543218765

================================================================================
STAGE 1: Document Parsing with Marker
================================================================================
Initializing Marker parser (VLM enabled)...
Parsing document: test_document.pdf (15.2KB)

Parsing Results:
  ✓ Parser Type: ParserType.MARKER
  ✓ Total Pages: 2
  ✓ Content Pages: 2
  ✓ Total Characters: 1,234
  ✓ Total Words: 234
  ✓ Processing Time: 12.34s

✓ Stage 1 completed successfully in 12.34s

================================================================================
STAGE 2: Hierarchical Chunking
================================================================================
Initializing DocumentChunker...
Chunking document (1,234 chars, 234 words)...

Chunking Results:
  ✓ Total Chunks: 15
  ✓ Summary Chunks: 1
  ✓ Section Chunks: 8
  ✓ Microblock Chunks: 6
  ✓ Processing Time: 0.23s

✓ Stage 2 completed successfully in 0.23s

[... continues for all stages ...]

================================================================================
PIPELINE TEST SUMMARY
================================================================================
Total Time: 45.67s
Stages Completed: 6/6

Stage Results:
--------------------------------------------------------------------------------
  ✓ PASS 1_PARSING (12.34s)
  ✓ PASS 2_CHUNKING (0.23s)
  ✓ PASS 3_EMBEDDINGS (15.45s)
  ✓ PASS 4_BM25_ENCODING (0.12s)
  ✓ PASS 5_INDEXING (8.91s)
  ✓ PASS 6_SEARCH (2.34s)
================================================================================

================================================================================
✓ ALL TESTS PASSED!
================================================================================
```

## What Gets Created

1. **Sample PDF** (if no PDF provided):
   - 2-page legal document
   - Contains: definitions, articles, whereas clauses, terms
   - Realistic legal formatting

2. **Test Data in Qdrant**:
   - Collection: `legal_documents` (or your configured collection)
   - Points: 15+ vectors (depends on document size)
   - Vectors: summary, section, microblock (dense) + bm25 (sparse)
   - Metadata: document_id, case_id, chunk_type, page_number, bboxes

3. **Detailed Logs**:
   - Each stage's performance metrics
   - Sample chunks and embeddings
   - Search results with scores
   - Error messages if any stage fails

## Interpreting Results

### Good Results
- **Parsing**: 10-60s depending on document size and VLM usage
- **Chunking**: <1s for small docs, 1-5s for large
- **Embeddings**: 5-20s for 100-500 chunks (FastEmbed is fast!)
- **Indexing**: 1-10s depending on batch size
- **Search**: <100ms per query

### Search Quality Metrics
- **BM25 Scores**: 5-20+ for strong keyword matches
- **Dense Scores**: 0.6-0.95 for semantic similarity
- **Final Scores**: 0.0-1.0 (normalized with boosting)
- **Match Types**: 
  - `bm25`: Keyword match
  - `semantic`: Meaning-based match
  - `hybrid`: Both methods found it

## Troubleshooting

### "GOOGLE_API_KEY not set"
```bash
export GOOGLE_API_KEY=your_key_here
```

### "Qdrant connection failed"
```bash
docker-compose up -d qdrant
```

### "Out of memory during embedding"
- Reduce `EMBEDDING_BATCH_SIZE` in script (currently 100)
- Use smaller embedding model (e.g., "sentence-transformers/all-MiniLM-L6-v2")

### "No results in search"
- Check document_id matches between indexing and search
- Verify Qdrant collection has points: `docker exec -it qdrant-legalease curl http://localhost:6333/collections/legal_documents`
- Lower score_threshold in search (default 0.3)

## Integration with mise

Add to `.mise.toml`:

```toml
[tasks.test-pipeline]
description = "Run end-to-end pipeline test"
run = "python scripts/test_full_pipeline.py"

[tasks."test-pipeline:with-pdf"]
description = "Run pipeline test with custom PDF"
run = "python scripts/test_full_pipeline.py --pdf-path"
```

Usage:
```bash
mise run test-pipeline
mise run test-pipeline:with-pdf /path/to/doc.pdf
```

## Next Steps

After successful tests:

1. **Scale Testing**: Test with larger documents (100+ pages)
2. **Performance Tuning**: Adjust batch sizes, token limits
3. **Quality Analysis**: Review chunk quality and search relevance
4. **Production Deployment**: Use these results to configure production settings

## Related Files

- **Parser**: `/home/Allie/develop/legalease/backend/app/workers/parsers/marker_parser.py`
- **Chunker**: `/home/Allie/develop/legalease/backend/app/workers/pipelines/chunker.py`
- **Embeddings**: `/home/Allie/develop/legalease/backend/app/workers/pipelines/embeddings.py`
- **Indexer**: `/home/Allie/develop/legalease/backend/app/workers/pipelines/indexer.py`
- **Search**: `/home/Allie/develop/legalease/backend/app/services/search/engine.py`
