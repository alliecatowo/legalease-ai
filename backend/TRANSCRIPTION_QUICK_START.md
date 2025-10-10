# Transcription Worker - Quick Start Guide

## Prerequisites

```bash
# 1. Install FFmpeg
sudo apt-get install ffmpeg  # Ubuntu/Debian
brew install ffmpeg          # macOS

# 2. Set OpenAI API key
export OPENAI_API_KEY=sk-...your-key...

# 3. Verify installations
ffmpeg -version
python -c "import openai; print('OK')"
```

## Start Workers

```bash
# Terminal 1: Start Celery worker
celery -A app.workers.celery_app worker \
  --loglevel=info \
  --queue=transcription \
  --concurrency=2

# Terminal 2: (Optional) Start Flower monitoring
celery -A app.workers.celery_app flower
# Access at http://localhost:5555
```

## Usage Examples

### Python API

```python
from app.workers.tasks.transcription import transcribe_audio

# Async (recommended)
task = transcribe_audio.delay(document_id=123, language="en")
print(f"Task ID: {task.id}")

# Check status
print(f"Status: {task.status}")
print(f"Result: {task.result}")

# Wait for completion
result = task.get(timeout=600)  # 10 min timeout
print(f"Transcription ID: {result['transcription_id']}")
print(f"Segments: {result['segments_count']}")
print(f"Speakers: {result['speakers_count']}")
```

### FastAPI Endpoint

```python
from fastapi import APIRouter
from app.workers.tasks.transcription import transcribe_audio

router = APIRouter()

@router.post("/documents/{document_id}/transcribe")
async def transcribe(document_id: int, language: str = "en"):
    task = transcribe_audio.delay(document_id, language)
    return {"task_id": task.id, "status": "processing"}

@router.get("/tasks/{task_id}/status")
async def get_status(task_id: str):
    from celery.result import AsyncResult
    task = AsyncResult(task_id)
    return {
        "status": task.status,
        "result": task.result if task.ready() else task.info
    }
```

## File Structure

```
/home/Allie/develop/legalease/backend/
├── app/
│   ├── workers/
│   │   ├── tasks/
│   │   │   ├── transcription.py           # Main implementation
│   │   │   └── TRANSCRIPTION_README.md    # Full documentation
│   │   └── celery_app.py
│   └── models/
│       ├── document.py
│       └── transcription.py
├── test_transcription_task.py              # Validation tests
└── TRANSCRIPTION_QUICK_START.md            # This file
```

## Features

✓ Download audio/video from MinIO
✓ Preprocess with FFmpeg (16kHz mono WAV)
✓ Transcribe with OpenAI Whisper API
✓ Speaker diarization (heuristic-based)
✓ Export to DOCX, SRT, VTT, JSON
✓ Upload exports to MinIO
✓ Update PostgreSQL database
✓ Progress tracking (0-100%)
✓ Error handling and recovery
✓ Automatic cleanup

## Process Flow

```
Document Upload (API)
    ↓
Queue Task → transcribe_audio.delay()
    ↓
Celery Worker Picks Up Task
    ↓
[10%]  Download from MinIO
    ↓
[20%]  Preprocess with FFmpeg
    ↓
[30%]  Transcribe with Whisper API
    ↓
[60%]  Diarize speakers
    ↓
[70%]  Export to 4 formats
    ↓
[85%]  Upload to MinIO
    ↓
[95%]  Update database
    ↓
[100%] Complete
```

## Export Formats

| Format | File Extension | Use Case |
|--------|---------------|----------|
| DOCX   | .docx        | Editable document with formatting |
| SRT    | .srt         | Standard subtitle format |
| VTT    | .vtt         | Web video subtitles |
| JSON   | .json        | Structured data with metadata |

## Common Commands

```bash
# Test single task
python -c "
from app.workers.tasks.transcription import transcribe_audio
result = transcribe_audio(document_id=1, language='en')
print(result)
"

# Monitor workers
celery -A app.workers.celery_app inspect active

# Purge queue
celery -A app.workers.celery_app purge

# Check registered tasks
celery -A app.workers.celery_app inspect registered

# View logs
tail -f celery_worker.log
```

## Supported Languages

English (en), Spanish (es), French (fr), German (de), Italian (it), Portuguese (pt), Dutch (nl), Russian (ru), Chinese (zh), Japanese (ja), Korean (ko), and many more.

See OpenAI Whisper documentation for full list.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Task stuck in PENDING | Start Celery worker |
| "OpenAI API key not configured" | Set OPENAI_API_KEY env var |
| "FFmpeg not found" | Install FFmpeg |
| Out of memory | Reduce worker concurrency |
| Slow processing | Check OpenAI API status |

## Configuration

Edit `.env` file:

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional (defaults shown)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
DATABASE_URL=postgresql://legalease:legalease@localhost:5432/legalease
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Performance

- **Small files** (< 5 min): ~30-60 seconds
- **Medium files** (5-30 min): 1-5 minutes
- **Large files** (30-120 min): 5-15 minutes

Processing time ≈ 10-20% of audio duration

## Monitoring Progress

```python
from celery.result import AsyncResult

task = AsyncResult('task-id-here')

while not task.ready():
    info = task.info
    print(f"{info.get('status')}: {info.get('progress')}%")
    time.sleep(2)

result = task.result
print(f"Completed: {result['segments_count']} segments")
```

## Next Steps

1. Read full documentation: `app/workers/tasks/TRANSCRIPTION_README.md`
2. Run validation tests: `python test_transcription_task.py`
3. Start development server and workers
4. Upload test audio file
5. Trigger transcription via API
6. Monitor progress in Flower

## Support

- Check logs: `tail -f celery_worker.log`
- Test FFmpeg: `ffmpeg -version`
- Verify API key: `echo $OPENAI_API_KEY`
- Monitor workers: `celery -A app.workers.celery_app inspect active`
