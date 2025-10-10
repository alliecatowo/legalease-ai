# Transcription Task Documentation

## Overview

The transcription Celery worker provides production-ready audio and video transcription capabilities for the LegalEase platform. It processes audio/video files through a comprehensive pipeline that includes preprocessing, transcription, speaker diarization, and multi-format export.

## Features

### Core Capabilities

1. **Audio Preprocessing**
   - Converts audio/video to optimal format (16kHz mono WAV)
   - Supports multiple input formats (MP3, MP4, WAV, M4A, etc.)
   - Uses FFmpeg for robust format conversion
   - Extracts audio duration metadata

2. **AI Transcription**
   - OpenAI Whisper API integration
   - Word-level and segment-level timestamps
   - Multi-language support
   - High accuracy speech-to-text

3. **Speaker Diarization**
   - Automatic speaker identification
   - Heuristic-based speaker segmentation
   - Pause detection for speaker changes
   - Speaker statistics and metadata

4. **Multi-Format Export**
   - DOCX: Formatted document with timestamps and speakers
   - SRT: Standard subtitle format
   - VTT: WebVTT format for web players
   - JSON: Complete structured data with metadata

5. **Storage Integration**
   - Download from MinIO object storage
   - Upload all export formats to MinIO
   - Automatic file organization by document

6. **Database Management**
   - PostgreSQL transcription records
   - Document status tracking
   - Metadata storage
   - Error state handling

7. **Production Features**
   - Progress tracking with Celery states
   - Comprehensive error handling
   - Automatic cleanup of temporary files
   - Detailed logging
   - Graceful failure recovery

## Architecture

### Main Components

```
transcription.py
├── TranscriptionError          # Custom exception class
├── AudioProcessor              # FFmpeg audio preprocessing
├── WhisperTranscriber         # OpenAI Whisper API integration
├── SpeakerDiarizer            # Speaker identification
├── TranscriptionExporter      # Multi-format export utilities
└── transcribe_audio()         # Main Celery task
```

### Processing Pipeline

```
1. Download → 2. Preprocess → 3. Transcribe → 4. Diarize
                                                   ↓
8. Cleanup ← 7. Update DB ← 6. Upload ← 5. Export
```

## Usage

### Task Invocation

```python
from app.workers.tasks.transcription import transcribe_audio

# Synchronous call
result = transcribe_audio(
    document_id=123,
    language="en"
)

# Async call (recommended)
task = transcribe_audio.delay(
    document_id=123,
    language="en"
)

# Check task status
status = task.status
result = task.result
```

### API Integration

```python
from fastapi import APIRouter, BackgroundTasks
from app.workers.tasks.transcription import transcribe_audio

router = APIRouter()

@router.post("/transcriptions/{document_id}")
async def start_transcription(
    document_id: int,
    language: str = "en"
):
    # Queue transcription task
    task = transcribe_audio.delay(
        document_id=document_id,
        language=language
    )

    return {
        "task_id": task.id,
        "status": "processing",
        "document_id": document_id
    }

@router.get("/transcriptions/status/{task_id}")
async def get_transcription_status(task_id: str):
    from celery.result import AsyncResult

    task = AsyncResult(task_id)

    return {
        "task_id": task_id,
        "status": task.status,
        "result": task.result if task.ready() else task.info
    }
```

### Progress Tracking

The task updates its state at various stages:

```python
# Monitor task progress
task = transcribe_audio.delay(document_id=123)

# Task states:
# - PENDING: Initial state
# - STARTED: Initializing (0%)
# - PROCESSING: Various stages (10%, 20%, 30%, 60%, 70%, 85%, 95%)
# - SUCCESS: Completed (100%)
# - FAILURE: Error occurred

# Get current progress
info = task.info
print(f"Status: {info['status']}, Progress: {info['progress']}%")
```

## Response Format

### Success Response

```json
{
  "status": "completed",
  "document_id": 123,
  "transcription_id": 456,
  "filename": "deposition_audio.mp3",
  "duration": 3661.5,
  "segments_count": 142,
  "speakers_count": 3,
  "speakers": [
    {"id": "SPEAKER_01", "segments_count": 58},
    {"id": "SPEAKER_02", "segments_count": 52},
    {"id": "SPEAKER_03", "segments_count": 32}
  ],
  "export_paths": {
    "docx": "cases/123/documents/deposition_audio.docx",
    "srt": "cases/123/documents/deposition_audio.srt",
    "vtt": "cases/123/documents/deposition_audio.vtt",
    "json": "cases/123/documents/deposition_audio.json"
  },
  "language": "en",
  "task_id": "abc123-def456-ghi789"
}
```

### Error Response

```json
{
  "status": "failed",
  "error": "Transcription failed: Invalid audio format",
  "document_id": 123,
  "task_id": "abc123-def456-ghi789"
}
```

## Export Formats

### DOCX Format

- Professional document layout
- Color-coded speakers
- Timestamped segments
- Easy to edit and annotate
- Compatible with Microsoft Word

### SRT Format

```srt
1
00:00:00,000 --> 00:00:05,320
[SPEAKER_01] Good morning, let's begin the deposition.

2
00:00:05,500 --> 00:00:10,840
[SPEAKER_02] Yes, I'm ready to proceed.
```

### VTT Format

```vtt
WEBVTT

00:00:00.000 --> 00:00:05.320
<v SPEAKER_01>Good morning, let's begin the deposition.</v>

00:00:05.500 --> 00:00:10.840
<v SPEAKER_02>Yes, I'm ready to proceed.</v>
```

### JSON Format

```json
{
  "metadata": {
    "document_id": 123,
    "filename": "deposition.mp3",
    "language": "en",
    "duration": 3661.5,
    "segments_count": 142,
    "speakers_count": 3
  },
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 5.32,
      "text": "Good morning, let's begin the deposition.",
      "speaker": "SPEAKER_01",
      "words": [
        {"word": "Good", "start": 0.0, "end": 0.3},
        {"word": "morning", "start": 0.3, "end": 0.8}
      ]
    }
  ],
  "generated_at": "2025-10-09T20:30:00.000000"
}
```

## Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...your-api-key...

# Optional (from settings)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
DATABASE_URL=postgresql://legalease:legalease@localhost:5432/legalease
```

### System Requirements

- **FFmpeg**: Must be installed and in PATH
- **FFprobe**: Usually comes with FFmpeg
- **Python**: 3.13+
- **Celery**: 5.5.3+
- **OpenAI**: Latest SDK

### Installation

```bash
# Install FFmpeg (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install ffmpeg

# Install FFmpeg (macOS)
brew install ffmpeg

# Install Python dependencies
pip install openai celery python-docx

# Verify installations
ffmpeg -version
python -c "import openai; print('OpenAI SDK installed')"
```

## Error Handling

### Common Errors

1. **Missing OpenAI API Key**
   ```
   Error: "OpenAI API key not configured"
   Solution: Set OPENAI_API_KEY environment variable
   ```

2. **FFmpeg Not Found**
   ```
   Error: "Audio preprocessing failed: ffmpeg not found"
   Solution: Install FFmpeg
   ```

3. **Invalid Audio Format**
   ```
   Error: "Audio preprocessing failed: FFmpeg error..."
   Solution: Check audio file is valid and not corrupted
   ```

4. **MinIO Connection Error**
   ```
   Error: "Failed to download file from MinIO"
   Solution: Verify MinIO is running and credentials are correct
   ```

5. **Database Connection Error**
   ```
   Error: Document database update failed
   Solution: Check PostgreSQL is running and accessible
   ```

### Error Recovery

The task automatically:
- Updates document status to FAILED on errors
- Stores error messages in document metadata
- Cleans up temporary files
- Logs detailed error information
- Returns error details to caller

## Performance

### Processing Times

- **Download**: ~1-5 seconds (depends on file size)
- **Preprocessing**: ~5-30 seconds (depends on duration)
- **Transcription**: ~10% of audio duration (Whisper API)
- **Diarization**: ~1-2 seconds
- **Export**: ~2-5 seconds
- **Upload**: ~1-5 seconds (depends on file size)

**Total**: Typically 1-2 minutes for a 10-minute audio file

### Optimization Tips

1. **Batch Processing**: Queue multiple files for parallel processing
2. **Worker Scaling**: Run multiple Celery workers
3. **Resource Allocation**: Allocate sufficient memory (2GB+ per worker)
4. **Network**: Ensure fast MinIO connection
5. **Storage**: Use SSD for temporary file processing

## Speaker Diarization

### Current Implementation

The current implementation uses a **heuristic-based approach**:
- Detects pauses longer than 2 seconds
- Assumes speaker change on significant pauses
- Simple but effective for many use cases

### Limitations

- May not detect speaker changes without pauses
- Cannot identify specific individuals
- Less accurate for overlapping speech
- No voice profile matching

### Future Improvements

For production deployments requiring advanced diarization:

1. **Pyannote.audio** (Deep Learning)
   ```python
   from pyannote.audio import Pipeline

   pipeline = Pipeline.from_pretrained(
       "pyannote/speaker-diarization",
       use_auth_token="YOUR_HF_TOKEN"
   )

   diarization = pipeline(audio_file)
   ```

2. **AssemblyAI API** (Cloud-based)
   ```python
   import assemblyai as aai

   aai.settings.api_key = "YOUR_API_KEY"
   transcriber = aai.Transcriber()

   transcript = transcriber.transcribe(
       audio_file,
       config=aai.TranscriptionConfig(speaker_labels=True)
   )
   ```

3. **Azure Speech Services** (Enterprise)
   - Advanced speaker recognition
   - Voice profile management
   - Multi-language support

## Testing

### Unit Tests

```python
# Test timestamp formatting
from app.workers.tasks.transcription import TranscriptionExporter

timestamp = TranscriptionExporter._format_srt_timestamp(61.234)
assert timestamp == "00:01:01,234"

# Test speaker diarization
from app.workers.tasks.transcription import SpeakerDiarizer

segments = [
    {'id': 0, 'start': 0.0, 'end': 5.0, 'text': 'Hello'},
    {'id': 1, 'start': 8.0, 'end': 12.0, 'text': 'Hi there'}
]

diarized = SpeakerDiarizer.diarize_segments(segments)
assert diarized[0]['speaker'] == 'SPEAKER_01'
assert diarized[1]['speaker'] == 'SPEAKER_02'  # Pause > 2s
```

### Integration Tests

```python
# Test full transcription pipeline (requires test audio file)
from app.workers.tasks.transcription import transcribe_audio

# Create test document
document = create_test_document(
    filename="test_audio.mp3",
    file_path="test/test_audio.mp3"
)

# Run transcription
result = transcribe_audio(
    document_id=document.id,
    language="en"
)

assert result['status'] == 'completed'
assert result['segments_count'] > 0
assert 'docx' in result['export_paths']
```

## Monitoring

### Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# View logs
tail -f celery_worker.log | grep transcription
```

### Metrics to Track

- **Success Rate**: Completed / Total tasks
- **Average Duration**: Mean processing time
- **Error Rate**: Failed / Total tasks
- **Queue Length**: Pending tasks
- **Worker Utilization**: Active workers / Total workers

### Celery Monitoring

```bash
# Flower - Real-time Celery monitoring
pip install flower
celery -A app.workers.celery_app flower

# Access at http://localhost:5555
```

## Security

### Best Practices

1. **API Keys**: Store in environment variables, never in code
2. **Temporary Files**: Automatically cleaned up after processing
3. **Access Control**: Verify user permissions before transcription
4. **Data Privacy**: Audio files stored securely in MinIO
5. **Audit Logging**: Track all transcription requests

### Compliance

- GDPR: Audio data can be deleted on request
- HIPAA: Encrypt data in transit and at rest
- SOC 2: Comprehensive audit logging

## Troubleshooting

### Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Run task synchronously for debugging
result = transcribe_audio(document_id=123, language="en")
print(result)
```

### Common Issues

**Issue**: Task stuck in PENDING state
- **Cause**: Celery worker not running
- **Solution**: Start Celery worker: `celery -A app.workers.celery_app worker -Q transcription`

**Issue**: Out of memory errors
- **Cause**: Large audio files
- **Solution**: Increase worker memory or split audio

**Issue**: Slow transcription
- **Cause**: API rate limits or network latency
- **Solution**: Check OpenAI API status, verify network connection

## Support

For issues or questions:
- Check logs: `tail -f celery_worker.log`
- Review error messages in database
- Test FFmpeg: `ffmpeg -version`
- Verify OpenAI API: `curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"`

## License

This implementation is part of the LegalEase platform.
