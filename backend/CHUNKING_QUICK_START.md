# Legal Document Chunking - Quick Start Guide

## Installation

```bash
cd /home/Allie/develop/legalease/backend
uv add tiktoken  # Already done
```

## Quick Usage

### 1. Basic Processing

```python
from app.workers.pipelines import create_pipeline

# Create pipeline
pipeline = create_pipeline()

# Process document
result = pipeline.process(
    document_text=your_text,
    template=None,  # Auto-detect
    preserve_structure=True
)

# Results
print(f"Type: {result.metadata.document_type}")
print(f"Chunks: {result.chunk_count}")
print(f"Time: {result.processing_time:.3f}s")
```

### 2. Process with Specific Template

```python
# Case law
result = pipeline.process(opinion_text, template="case_law")

# Contract
result = pipeline.process(contract_text, template="contract")

# Statute
result = pipeline.process(statute_text, template="statute")

# Brief
result = pipeline.process(brief_text, template="brief")

# General
result = pipeline.process(other_text, template="general")
```

### 3. Access Metadata

```python
metadata = result.metadata

# Case law
if metadata.case_number:
    print(f"Case: {metadata.case_number}")
    print(f"Parties: {metadata.parties}")
    print(f"Court: {metadata.court}")

# Contract
if metadata.contract_parties:
    print(f"Parties: {metadata.contract_parties}")
    print(f"Date: {metadata.effective_date}")

# Statute
if metadata.statute_citation:
    print(f"Citation: {metadata.statute_citation}")
```

### 4. Process Chunks

```python
for chunk in result.chunks:
    print(f"Chunk {chunk.metadata.position}")
    print(f"  Type: {chunk.metadata.chunk_type}")  # "512token", "256token", "128token"
    print(f"  Tokens: {chunk.metadata.token_count}")
    print(f"  Section: {chunk.metadata.section_title}")
    print(f"  Citations: {chunk.metadata.citations}")
    print(f"  Text: {chunk.text[:100]}...")
```

### 5. Database Integration

```python
from app.workers.pipelines.integration_example import process_document_with_chunking
from app.core.database import SessionLocal
from app.models.document import Document

db = SessionLocal()
try:
    document = db.query(Document).filter(Document.id == doc_id).first()
    text = extract_text_from_file(document.file_path)

    # Process and save
    chunk_count = process_document_with_chunking(
        document=document,
        document_text=text,
        db=db
    )

    print(f"Created {chunk_count} chunks")
finally:
    db.close()
```

## Configuration Options

### Chunk Sizes

```python
# Default: [512, 256, 128]
pipeline = create_pipeline(chunk_sizes=[512, 256, 128])

# Larger chunks
pipeline = create_pipeline(chunk_sizes=[1024, 512, 256])

# Single size
pipeline = create_pipeline(chunk_sizes=[512])
```

### Overlap

```python
# Default: 50 tokens
pipeline = create_pipeline(overlap=50)

# More overlap
pipeline = create_pipeline(overlap=100)
```

### Structure Preservation

```python
# Preserve structure (recommended for legal docs)
result = pipeline.process(text, preserve_structure=True)

# Simple paragraph chunking
result = pipeline.process(text, preserve_structure=False)
```

## Templates

| Template | Use For | Preserves |
|----------|---------|-----------|
| `case_law` | Court opinions, decisions | Syllabus, opinion, dissent, concurrence |
| `contract` | Contracts, agreements | Articles, sections, clauses |
| `statute` | Statutes, regulations | Sections, subsections, paragraphs |
| `brief` | Legal briefs, motions | Jurisdiction, issues, facts, argument |
| `general` | Other documents | Paragraphs |

## Testing

```bash
source .venv/bin/activate
python test_chunking_pipeline.py
```

## Common Patterns

### Auto-Detect and Process

```python
pipeline = create_pipeline()
result = pipeline.process(unknown_text, template=None)
print(f"Detected: {result.metadata.document_type}")
```

### Get Citations

```python
all_citations = []
for chunk in result.chunks:
    all_citations.extend(chunk.metadata.citations)

unique_citations = list(set(all_citations))
print(f"Citations: {unique_citations}")
```

### Filter Chunks by Size

```python
large_chunks = [c for c in result.chunks if c.metadata.chunk_type == "512token"]
medium_chunks = [c for c in result.chunks if c.metadata.chunk_type == "256token"]
small_chunks = [c for c in result.chunks if c.metadata.chunk_type == "128token"]
```

### Export Metadata

```python
metadata_dict = result.metadata.to_dict()
# Save to database or JSON
```

## Files

- `app/workers/pipelines/chunking.py` - Core chunking
- `app/workers/pipelines/legal_processing.py` - Pipeline & metadata
- `app/workers/pipelines/integration_example.py` - DB integration
- `test_chunking_pipeline.py` - Test suite
- `LEGAL_CHUNKING.md` - Full documentation

## Support

For detailed documentation, see `LEGAL_CHUNKING.md`.
