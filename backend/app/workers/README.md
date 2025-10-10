# Celery Workers

Distributed task queue for LegalEase backend using Celery with Redis.

## Architecture

### Task Queues

- **documents** - Document processing and generation tasks
- **transcription** - Audio transcription tasks
- **ai** - AI/ML tasks (entity extraction, analysis)

### Task Routing

Tasks are automatically routed to appropriate queues:

- `process_document` → documents queue
- `generate_document` → documents queue
- `process_uploaded_document` → documents queue
- `transcribe_audio` → transcription queue
- `process_transcription` → transcription queue
- `extract_entities` → ai queue
- `analyze_document` → ai queue

## Configuration

Celery is configured to use:
- **Broker**: Redis (redis://localhost:6379/1)
- **Result Backend**: Redis (redis://localhost:6379/2)
- **Serialization**: JSON
- **Timezone**: UTC

Settings are loaded from `app.core.config.Settings`.

## Running Workers

### Start all queues (default worker)
```bash
uv run celery -A app.workers.celery_app worker -l info
```

### Start specific queue
```bash
# Documents queue only
uv run celery -A app.workers.celery_app worker -Q documents -l info

# Transcription queue only
uv run celery -A app.workers.celery_app worker -Q transcription -l info

# AI queue only
uv run celery -A app.workers.celery_app worker -Q ai -l info
```

### Production deployment (with autoscaling)
```bash
uv run celery -A app.workers.celery_app worker \
  --autoscale=10,3 \
  --max-tasks-per-child=1000 \
  -l info
```

## Monitoring

### List registered tasks
```bash
uv run celery -A app.workers.celery_app inspect registered
```

### Check active tasks
```bash
uv run celery -A app.workers.celery_app inspect active
```

### Check worker status
```bash
uv run celery -A app.workers.celery_app inspect stats
```

### Flower (Web-based monitoring) - Optional
```bash
pip install flower
uv run celery -A app.workers.celery_app flower
```
Then visit http://localhost:5555

## Tasks

### Document Processing Tasks

#### process_document
Process a document for a case using a template.
```python
from app.workers.tasks.document_processing import process_document

result = process_document.delay(
    document_id="doc-123",
    case_id="case-456",
    template="motion"
)
```

#### generate_document
Generate a document from a template.
```python
from app.workers.tasks.document_processing import generate_document

result = generate_document.delay(
    case_id="case-456",
    template_name="motion_to_dismiss",
    context_data={"defendant": "John Doe", "case_number": "2024-CV-001"}
)
```

#### process_uploaded_document
Process an uploaded document (extract text, entities, embeddings).
```python
from app.workers.tasks.document_processing import process_uploaded_document

result = process_uploaded_document.delay(document_id=123)
```

### Transcription Tasks

#### transcribe_audio
Transcribe an audio file.
```python
from app.workers.tasks.transcription import transcribe_audio

result = transcribe_audio.delay(
    transcription_id="trans-123",
    audio_file_path="cases/case-456/audio.wav",
    case_id="case-456",
    language="en"
)
```

#### process_transcription
Process a completed transcription.
```python
from app.workers.tasks.transcription import process_transcription

result = process_transcription.delay(
    transcription_id="trans-123",
    case_id="case-456",
    extract_entities=True
)
```

## Task Results

Check task status and results:
```python
from app.workers.celery_app import celery_app

# Get task result
result = celery_app.AsyncResult(task_id)
print(result.status)  # PENDING, STARTED, SUCCESS, FAILURE
print(result.result)  # Task return value
```

## Development Notes

- All tasks are currently **stub implementations**
- Full functionality will be implemented in **Phase 3**
- Tasks use `bind=True` to access task context (`self.request.id`)
- Database operations use `SessionLocal()` context manager
- Tasks should be idempotent and handle failures gracefully

## Prerequisites

Ensure Redis is running:
```bash
# Check if Redis is running
redis-cli ping

# Start Redis (if not running)
redis-server
```
