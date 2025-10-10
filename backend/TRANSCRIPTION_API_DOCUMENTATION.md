# Transcription Management API Documentation

Complete API documentation for the LegalEase Transcription Management System.

## Overview

The Transcription API provides endpoints for uploading audio/video files, managing transcriptions, and exporting transcripts in multiple formats. It supports automatic speaker diarization and timestamped segments.

## Base URL

```
http://localhost:8000/api/v1
```

## Endpoints

### 1. Upload Audio/Video for Transcription

Upload an audio or video file to generate a transcription.

**Endpoint:** `POST /cases/{case_id}/transcriptions`

**Path Parameters:**
- `case_id` (integer, required): ID of the case

**Request Body:**
- Multipart form data with audio/video file

**Supported Formats:**
- **Audio:** MP3, WAV, AAC, M4A, FLAC, OGG, WebM
- **Video:** MP4, MPEG, MOV, AVI, WebM, MKV

**Response:** `201 Created`
```json
{
  "message": "Audio/video file 'deposition.mp3' uploaded successfully. Transcription processing has been queued.",
  "document_id": 123,
  "transcription_id": null,
  "status": "processing"
}
```

**Example (cURL):**
```bash
curl -X POST "http://localhost:8000/api/v1/cases/1/transcriptions" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@deposition.mp3"
```

**Example (Python):**
```python
import requests

with open("deposition.mp3", "rb") as f:
    files = {"file": ("deposition.mp3", f, "audio/mpeg")}
    response = requests.post(
        "http://localhost:8000/api/v1/cases/1/transcriptions",
        files=files
    )
    print(response.json())
```

---

### 2. List Case Transcriptions

Get all transcriptions for a specific case.

**Endpoint:** `GET /cases/{case_id}/transcriptions`

**Path Parameters:**
- `case_id` (integer, required): ID of the case

**Response:** `200 OK`
```json
{
  "transcriptions": [
    {
      "id": 1,
      "document_id": 123,
      "case_id": 1,
      "filename": "deposition.mp3",
      "format": "mp3",
      "duration": 1825.5,
      "segment_count": 145,
      "speaker_count": 3,
      "created_at": "2025-10-09T14:30:00"
    }
  ],
  "total": 1,
  "case_id": 1
}
```

**Example (cURL):**
```bash
curl -X GET "http://localhost:8000/api/v1/cases/1/transcriptions"
```

**Example (Python):**
```python
import requests

response = requests.get("http://localhost:8000/api/v1/cases/1/transcriptions")
transcriptions = response.json()
print(f"Found {transcriptions['total']} transcriptions")
```

---

### 3. Get Transcription Details

Get detailed information about a specific transcription including all segments and speakers.

**Endpoint:** `GET /transcriptions/{transcription_id}`

**Path Parameters:**
- `transcription_id` (integer, required): ID of the transcription

**Response:** `200 OK`
```json
{
  "id": 1,
  "document_id": 123,
  "case_id": 1,
  "filename": "deposition.mp3",
  "format": "mp3",
  "duration": 1825.5,
  "speakers": [
    {
      "speaker_id": "SPEAKER_00",
      "label": "Attorney Johnson",
      "confidence": 0.95
    },
    {
      "speaker_id": "SPEAKER_01",
      "label": "Witness Smith",
      "confidence": 0.92
    }
  ],
  "segments": [
    {
      "start": 0.0,
      "end": 5.2,
      "text": "Please state your name for the record.",
      "speaker": "SPEAKER_00",
      "confidence": 0.98
    },
    {
      "start": 5.5,
      "end": 8.3,
      "text": "My name is John Smith.",
      "speaker": "SPEAKER_01",
      "confidence": 0.96
    }
  ],
  "created_at": "2025-10-09T14:30:00"
}
```

**Example (cURL):**
```bash
curl -X GET "http://localhost:8000/api/v1/transcriptions/1"
```

**Example (Python):**
```python
import requests

response = requests.get("http://localhost:8000/api/v1/transcriptions/1")
transcription = response.json()
print(f"Duration: {transcription['duration']} seconds")
print(f"Speakers: {len(transcription['speakers'])}")
print(f"Segments: {len(transcription['segments'])}")
```

---

### 4. Download Transcription

Download transcription in various formats.

**Endpoint:** `GET /transcriptions/{transcription_id}/download/{format}`

**Path Parameters:**
- `transcription_id` (integer, required): ID of the transcription
- `format` (string, required): Export format

**Supported Formats:**
- `json` - Full JSON with all metadata
- `docx` - Microsoft Word document with formatting
- `srt` - SubRip subtitle format
- `vtt` - WebVTT subtitle format
- `txt` - Plain text with timestamps

**Response:** `200 OK`
- File download with appropriate Content-Type and Content-Disposition headers

#### Format Examples

**JSON Format:**
```json
{
  "transcription_id": 1,
  "document_id": 123,
  "filename": "deposition.mp3",
  "format": "mp3",
  "duration": 125.5,
  "speakers": [...],
  "segments": [...],
  "created_at": "2025-10-09T14:30:00"
}
```

**SRT Format:**
```srt
1
00:00:00,000 --> 00:00:05,200
[SPEAKER_00] Please state your name for the record.

2
00:00:05,500 --> 00:00:08,300
[SPEAKER_01] My name is John Smith.
```

**VTT Format:**
```vtt
WEBVTT

00:00:00.000 --> 00:00:05.200
<v SPEAKER_00>Please state your name for the record.

00:00:05.500 --> 00:00:08.300
<v SPEAKER_01>My name is John Smith.
```

**TXT Format:**
```
[00:00:00] SPEAKER_00: Please state your name for the record.
[00:00:05] SPEAKER_01: My name is John Smith.
```

**DOCX Format:**
- Formatted Microsoft Word document with:
  - Title and metadata
  - Speaker list
  - Timestamped segments with speaker labels

**Example (cURL):**
```bash
# Download as JSON
curl -X GET "http://localhost:8000/api/v1/transcriptions/1/download/json" \
  -o transcription.json

# Download as DOCX
curl -X GET "http://localhost:8000/api/v1/transcriptions/1/download/docx" \
  -o transcription.docx

# Download as SRT subtitles
curl -X GET "http://localhost:8000/api/v1/transcriptions/1/download/srt" \
  -o transcription.srt
```

**Example (Python):**
```python
import requests

# Download as JSON
response = requests.get("http://localhost:8000/api/v1/transcriptions/1/download/json")
with open("transcription.json", "wb") as f:
    f.write(response.content)

# Download as DOCX
response = requests.get("http://localhost:8000/api/v1/transcriptions/1/download/docx")
with open("transcription.docx", "wb") as f:
    f.write(response.content)
```

---

### 5. Delete Transcription

Delete a transcription from the database.

**Endpoint:** `DELETE /transcriptions/{transcription_id}`

**Path Parameters:**
- `transcription_id` (integer, required): ID of the transcription

**Response:** `200 OK`
```json
{
  "id": 1,
  "document_id": 123,
  "filename": "deposition.mp3",
  "message": "Transcription deleted successfully"
}
```

**Note:** The associated audio/video file will remain in storage. Only the transcription is deleted.

**Example (cURL):**
```bash
curl -X DELETE "http://localhost:8000/api/v1/transcriptions/1"
```

**Example (Python):**
```python
import requests

response = requests.delete("http://localhost:8000/api/v1/transcriptions/1")
result = response.json()
print(result['message'])
```

---

## Data Models

### Transcription Segment

```typescript
{
  start: number,          // Start time in seconds
  end: number,            // End time in seconds
  text: string,           // Transcribed text
  speaker: string,        // Speaker identifier (optional)
  confidence: number      // Confidence score 0.0-1.0 (optional)
}
```

### Speaker Info

```typescript
{
  speaker_id: string,     // Unique speaker identifier
  label: string,          // Speaker name/label (optional)
  confidence: number      // Speaker identification confidence (optional)
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Unsupported file format: application/zip. Supported formats: audio (mp3, wav, ...) and video (mp4, ...)"
}
```

### 404 Not Found
```json
{
  "detail": "Transcription 123 not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to process transcription: [error message]"
}
```

---

## Complete Workflow Example

### 1. Create a Case
```python
import requests

# Create case
case_data = {
    "name": "Smith Deposition",
    "case_number": "2025-CV-001",
    "client": "Acme Corp",
    "matter_type": "Deposition"
}
response = requests.post("http://localhost:8000/api/v1/cases", json=case_data)
case_id = response.json()["id"]
```

### 2. Upload Audio for Transcription
```python
# Upload audio file
with open("deposition.mp3", "rb") as f:
    files = {"file": ("deposition.mp3", f, "audio/mpeg")}
    response = requests.post(
        f"http://localhost:8000/api/v1/cases/{case_id}/transcriptions",
        files=files
    )
    result = response.json()
    print(f"Upload status: {result['status']}")
    document_id = result['document_id']
```

### 3. Wait for Processing (Background Task)
The transcription will be processed by a background Celery task. Processing time depends on audio length.

### 4. Check Transcription Status
```python
# List transcriptions for the case
response = requests.get(f"http://localhost:8000/api/v1/cases/{case_id}/transcriptions")
transcriptions = response.json()["transcriptions"]

if transcriptions:
    transcription_id = transcriptions[0]["id"]
    print(f"Transcription ready: ID {transcription_id}")
```

### 5. Get Transcription Details
```python
# Get full transcription details
response = requests.get(f"http://localhost:8000/api/v1/transcriptions/{transcription_id}")
transcription = response.json()

print(f"Duration: {transcription['duration']} seconds")
print(f"Speakers: {len(transcription['speakers'])}")

# Print segments
for segment in transcription['segments'][:5]:
    print(f"[{segment['start']:.1f}s] {segment['speaker']}: {segment['text']}")
```

### 6. Export Transcription
```python
# Download as Word document
response = requests.get(
    f"http://localhost:8000/api/v1/transcriptions/{transcription_id}/download/docx"
)
with open("transcription.docx", "wb") as f:
    f.write(response.content)
print("Transcription exported to transcription.docx")

# Download as subtitles
response = requests.get(
    f"http://localhost:8000/api/v1/transcriptions/{transcription_id}/download/srt"
)
with open("transcription.srt", "wb") as f:
    f.write(response.content)
print("Subtitles exported to transcription.srt")
```

---

## Testing

### Run Test Script
```bash
# Ensure the API is running
uvicorn main:app --reload

# In another terminal, run the test script
python test_transcription_api.py
```

The test script will:
1. Create a test case
2. Upload a mock audio file
3. Create a mock transcription (simulating background processing)
4. List transcriptions
5. Get transcription details
6. Download in all formats (JSON, DOCX, SRT, VTT, TXT)

### API Documentation (Swagger UI)

Visit `http://localhost:8000/docs` to access the interactive API documentation.

---

## Integration Notes

### Background Processing

The actual transcription processing should be implemented as a Celery task:

```python
# app/workers/tasks/transcription_processing.py
from celery import shared_task
from app.services.transcription_service import TranscriptionService

@shared_task
def process_transcription(document_id: int):
    """
    Background task to process audio/video transcription.

    This task should:
    1. Download audio/video from MinIO
    2. Call transcription service (e.g., Whisper, AssemblyAI)
    3. Perform speaker diarization
    4. Save transcription to database
    """
    # Implementation here
    pass
```

### Recommended Transcription Services

1. **Whisper (OpenAI)** - Local, open-source, high accuracy
2. **AssemblyAI** - Cloud-based, excellent speaker diarization
3. **Google Speech-to-Text** - Cloud-based, good for live transcription
4. **AWS Transcribe** - Cloud-based, medical/legal vocabulary support

---

## File Structure

```
app/
├── api/v1/
│   └── transcriptions.py          # API endpoints
├── schemas/
│   └── transcription.py            # Pydantic schemas
├── services/
│   └── transcription_service.py    # Business logic
└── models/
    └── transcription.py            # Database model

test_transcription_api.py           # Test script
TRANSCRIPTION_API_DOCUMENTATION.md  # This file
```

---

## API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/cases/{case_id}/transcriptions` | Upload audio/video for transcription |
| GET | `/cases/{case_id}/transcriptions` | List all transcriptions in a case |
| GET | `/transcriptions/{id}` | Get transcription details |
| GET | `/transcriptions/{id}/download/{format}` | Download in JSON/DOCX/SRT/VTT/TXT |
| DELETE | `/transcriptions/{id}` | Delete transcription |

---

## Support

For questions or issues:
- Check the API documentation at `/docs`
- Review the test script for usage examples
- Consult the code comments in `transcription_service.py`
