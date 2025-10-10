# Celery Quick Start Guide

## Overview

Celery distributed task queue is configured and ready to use. The setup includes:

- **Broker & Backend**: Redis (localhost:6379/0)
- **3 Task Queues**: documents, transcription, ai
- **6 Registered Tasks**: All stub implementations ready for Phase 3

## Starting the Celery Worker

### Basic Command
```bash
uv run celery -A app.workers.celery_app worker -l info
```

### With Specific Queue
```bash
# Documents queue only
uv run celery -A app.workers.celery_app worker -Q documents -l info

# Transcription queue only
uv run celery -A app.workers.celery_app worker -Q transcription -l info

# AI queue only
uv run celery -A app.workers.celery_app worker -Q ai -l info
```

### Production Mode (with autoscaling)
```bash
uv run celery -A app.workers.celery_app worker \
  --autoscale=10,3 \
  --max-tasks-per-child=1000 \
  -l info
```

## Verify Setup

Run the test script:
```bash
uv run python test_celery_setup.py
```

Expected output: All 6 tests should pass ✓

## Available Tasks

### Document Processing Queue
- `process_document(document_id, case_id, template)` - Process a document with template
- `generate_document(case_id, template_name, context_data)` - Generate document from template
- `process_uploaded_document(document_id)` - Process uploaded document (extract, analyze, embed)

### Transcription Queue
- `transcribe_audio(transcription_id, audio_file_path, case_id, language)` - Transcribe audio file
- `process_transcription(transcription_id, case_id, extract_entities)` - Process transcription results

### AI Queue (Future)
- `extract_entities` - Extract legal entities from text
- `analyze_document` - Analyze document content

## Task Usage Example

```python
from app.workers.tasks.document_processing import process_uploaded_document

# Queue a task
result = process_uploaded_document.delay(document_id=123)

# Check task status
print(result.status)  # PENDING, STARTED, SUCCESS, FAILURE
print(result.result)  # Task return value when completed
```

## Monitoring Commands

```bash
# List registered tasks
uv run celery -A app.workers.celery_app inspect registered

# Check active tasks
uv run celery -A app.workers.celery_app inspect active

# Worker statistics
uv run celery -A app.workers.celery_app inspect stats

# Purge all tasks (careful!)
uv run celery -A app.workers.celery_app purge
```

## Prerequisites

Ensure Redis is running:
```bash
# Check Redis
redis-cli ping
# Should return: PONG

# Start Redis (if not running)
redis-server
```

## Configuration Files

- `app/workers/celery_app.py` - Main Celery configuration
- `app/workers/tasks/document_processing.py` - Document tasks
- `app/workers/tasks/transcription.py` - Transcription tasks
- `app/core/config.py` - Application settings
- `.env` - Environment configuration

## Task Queue Routing

Tasks are automatically routed to queues based on their name:

| Task Name | Queue |
|-----------|-------|
| process_document | documents |
| generate_document | documents |
| process_uploaded_document | documents |
| transcribe_audio | transcription |
| process_transcription | transcription |
| extract_entities | ai |
| analyze_document | ai |

## Notes

- All tasks are **stub implementations** - full functionality coming in Phase 3
- Tasks use `bind=True` to access task context (self.request.id)
- Results expire after 1 hour (configurable in celery_app.py)
- Workers restart after 1000 tasks to prevent memory leaks
- Task acknowledgment is late (acks_late=True) for reliability

## Troubleshooting

### Worker won't start
- Check Redis is running: `redis-cli ping`
- Verify Python environment: `uv run python -c "from app.workers.celery_app import celery_app; print('OK')"`

### Tasks not being processed
- Check worker logs for errors
- Verify task is registered: `uv run celery -A app.workers.celery_app inspect registered`
- Check Redis connection: `redis-cli ping`

### Import errors
- Clear Python cache: `find . -name "*.pyc" -delete`
- Restart worker after code changes

## Next Steps (Phase 3)

Tasks to be fully implemented:
1. Document text extraction (PDF, DOCX)
2. NLP entity extraction
3. Vector embedding generation
4. Qdrant indexing
5. Audio transcription with Whisper
6. Speaker diarization
7. Template rendering with docxtpl
