# Subtitle Generator - Quick Start

## Installation

No additional dependencies required - pure Python implementation.

```python
from app.workers.pipelines import SubtitleGenerator, create_subtitle_generator
```

## Basic Usage

### Generate All Formats

```python
from app.workers.pipelines import SubtitleGenerator

# Sample transcription data
segments = [
    {
        "text": "Welcome to the courtroom.",
        "start": 0.0,
        "end": 3.5,
        "speaker": "Judge",
        "confidence": 0.98
    },
    {
        "text": "Thank you, Your Honor.",
        "start": 4.0,
        "end": 6.0,
        "speaker": "Attorney",
        "confidence": 0.95
    }
]

# Create generator
generator = SubtitleGenerator(chars_per_caption=42)

# Export all formats at once
paths = generator.export_all(
    segments,
    "/path/to/output/subtitle"  # Creates .srt, .vtt, .json
)

print(f"SRT: {paths['srt']}")
print(f"VTT: {paths['vtt']}")
print(f"JSON: {paths['json']}")
```

## Segment Format

Each segment should be a dictionary with:

```python
{
    "text": str,           # Required: Transcribed text
    "start": float,        # Required: Start time in seconds
    "end": float,          # Required: End time in seconds
    "speaker": str,        # Optional: Speaker name/ID
    "confidence": float    # Optional: Confidence score (0-1)
}
```

## Export Formats

### SRT (SubRip)

```python
generator.export_srt(
    segments,
    "/path/to/output.srt",
    include_speaker=True
)
```

Output:
```
1
00:00:00,000 --> 00:00:03,500
[Judge] Welcome to the courtroom.

2
00:00:04,000 --> 00:00:06,000
[Attorney] Thank you, Your Honor.
```

### VTT (WebVTT)

```python
generator.export_vtt(
    segments,
    "/path/to/output.vtt",
    include_speaker=True
)
```

Output:
```
WEBVTT

00:00:00.000 --> 00:00:03.500
<v Judge>Welcome to the courtroom.</v>

00:00:04.000 --> 00:00:06.000
<v Attorney>Thank you, Your Honor.</v>
```

### JSON

```python
generator.export_json(
    segments,
    "/path/to/output.json",
    pretty=True
)
```

Output:
```json
{
  "segments": [
    {
      "index": 0,
      "text": "Welcome to the courtroom.",
      "start": 0.0,
      "end": 3.5,
      "duration": 3.5,
      "speaker": "Judge",
      "confidence": 0.98
    }
  ],
  "metadata": {
    "total_segments": 2,
    "total_duration": 6.0,
    "chars_per_caption": 42
  }
}
```

## Configuration

### Caption Length

```python
# Mobile (30-35 chars)
mobile_gen = SubtitleGenerator(chars_per_caption=30)

# Standard (42 chars - default)
standard_gen = SubtitleGenerator(chars_per_caption=42)

# Desktop/Cinema (50-60 chars)
desktop_gen = SubtitleGenerator(chars_per_caption=60)
```

### Factory Function

```python
from app.workers.pipelines import create_subtitle_generator

generator = create_subtitle_generator(chars_per_caption=50)
```

### Without Speaker Labels

```python
generator.export_srt(
    segments,
    "/path/to/output.srt",
    include_speaker=False  # No speaker labels
)
```

## Timestamp Formatting

- **SRT**: `HH:MM:SS,mmm` (comma separator)
- **VTT**: `HH:MM:SS.mmm` (period separator)

```python
# Manual timestamp formatting
srt_time = generator.format_timestamp_srt(125.5)  # "00:02:05,500"
vtt_time = generator.format_timestamp_vtt(125.5)  # "00:02:05.500"
```

## Integration Example

### With Celery Task

```python
from app.workers.celery_app import celery_app
from app.workers.pipelines import SubtitleGenerator

@celery_app.task(name="generate_subtitles")
def generate_subtitles(transcription_id: str, segments: List[Dict]):
    generator = SubtitleGenerator(chars_per_caption=42)

    paths = generator.export_all(
        segments,
        f"/transcriptions/{transcription_id}/subtitle"
    )

    return {
        "transcription_id": transcription_id,
        "subtitle_files": paths
    }
```

### With MinIO Storage

```python
from app.core.minio_client import minio_client
from app.workers.pipelines import SubtitleGenerator
import tempfile
from pathlib import Path

def generate_and_upload_subtitles(segments, case_id):
    generator = SubtitleGenerator()

    with tempfile.TemporaryDirectory() as temp_dir:
        # Generate locally
        base_path = Path(temp_dir) / "subtitle"
        paths = generator.export_all(segments, str(base_path))

        # Upload to MinIO
        uploaded = {}
        for fmt, local_path in paths.items():
            with open(local_path, 'rb') as f:
                minio_path = f"cases/{case_id}/subtitles/transcript.{fmt}"
                minio_client.upload_file(
                    file_data=f,
                    object_name=minio_path,
                    content_type="text/plain" if fmt in ["srt", "vtt"] else "application/json"
                )
                uploaded[fmt] = minio_path

        return uploaded
```

## Testing

Run the test suite:

```bash
python test_subtitle_generator.py
```

This tests:
- SRT/VTT/JSON generation
- Timestamp formatting
- Text wrapping
- Factory function
- Speaker label handling

## Key Features

- Pure Python (no external dependencies)
- Multiple format support (SRT, VTT, JSON)
- Speaker labels included
- Configurable caption length
- Intelligent text wrapping at word boundaries
- Proper timestamp formatting for each format
- Batch export to all formats

## File Structure

```
app/workers/pipelines/
├── subtitle_generator.py       # Main implementation
└── __init__.py                 # Exports

test_subtitle_generator.py      # Test suite
SUBTITLE_GENERATOR_GUIDE.md     # Full documentation
SUBTITLE_QUICK_START.md         # This file
```

## Common Use Cases

### Legal Deposition
```python
segments = [
    {"text": "Please state your name.", "start": 0.0, "end": 2.0, "speaker": "Attorney"},
    {"text": "John Smith.", "start": 2.5, "end": 3.5, "speaker": "Witness"}
]
generator.export_all(segments, "/depositions/smith")
```

### Court Hearing
```python
segments = [
    {"text": "This court is in session.", "start": 0.0, "end": 3.0, "speaker": "Judge"},
    {"text": "We're ready to proceed.", "start": 3.5, "end": 5.0, "speaker": "Prosecutor"}
]
generator.export_all(segments, "/hearings/case_123")
```

### Generic Transcription
```python
# Without speaker labels
segments = [
    {"text": "First line", "start": 0.0, "end": 2.0},
    {"text": "Second line", "start": 2.5, "end": 4.5}
]
generator.export_srt(segments, "/output.srt", include_speaker=False)
```

## Next Steps

- See **SUBTITLE_GENERATOR_GUIDE.md** for complete API documentation
- Check **test_subtitle_generator.py** for more examples
- Review `app/workers/pipelines/subtitle_generator.py` for implementation details
