# Subtitle Generator Guide

## Overview

The `SubtitleGenerator` pipeline provides comprehensive subtitle generation capabilities for transcribed audio/video content. It supports multiple industry-standard formats (SRT, VTT, JSON) with speaker labels, configurable caption length, and proper timestamp formatting.

## Features

- **Multiple Format Support**:
  - SRT (SubRip) - Universal subtitle format
  - VTT (WebVTT) - Web-based subtitle format with advanced features
  - JSON - Full metadata export for programmatic access

- **Speaker Labels**: Include speaker identification in subtitles
- **Configurable Caption Length**: Control line wrapping for readability
- **Proper Timestamp Formatting**:
  - SRT: `HH:MM:SS,mmm` format
  - VTT: `HH:MM:SS.mmm` format
- **Text Wrapping**: Intelligent word-boundary wrapping for multi-line captions
- **Pure Python**: No external dependencies required

## Installation

The subtitle generator is part of the workers pipeline and requires no additional dependencies beyond the base project requirements.

```python
from app.workers.pipelines import SubtitleGenerator, create_subtitle_generator
```

## Quick Start

### Basic Usage

```python
from app.workers.pipelines.subtitle_generator import SubtitleGenerator

# Create generator
generator = SubtitleGenerator(chars_per_caption=42)

# Prepare transcription segments
segments = [
    {
        "text": "Welcome to the hearing.",
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

# Export to SRT
generator.export_srt(
    segments,
    "/path/to/output.srt",
    include_speaker=True
)
```

### Using the Factory Function

```python
from app.workers.pipelines import create_subtitle_generator

# Create with custom settings
generator = create_subtitle_generator(chars_per_caption=50)

# Export all formats at once
paths = generator.export_all(
    segments,
    "/path/to/base_filename",  # Will create .srt, .vtt, .json
    include_speaker=True
)

print(f"SRT: {paths['srt']}")
print(f"VTT: {paths['vtt']}")
print(f"JSON: {paths['json']}")
```

## API Reference

### SubtitleGenerator Class

#### Constructor

```python
SubtitleGenerator(chars_per_caption: int = 42)
```

**Parameters:**
- `chars_per_caption` (int): Maximum characters per caption line. Default: 42

#### Methods

##### export_srt()

Export subtitles in SRT (SubRip) format.

```python
def export_srt(
    segments: List[Dict[str, Any]],
    output_path: str,
    include_speaker: bool = True
) -> str
```

**Parameters:**
- `segments`: List of segment dictionaries
- `output_path`: Path to output SRT file
- `include_speaker`: Include speaker labels (default: True)

**Returns:** Path to generated file

**Segment Format:**
```python
{
    "text": str,           # Required: Transcribed text
    "start": float,        # Required: Start time in seconds
    "end": float,          # Required: End time in seconds
    "speaker": str,        # Optional: Speaker name/ID
    "confidence": float    # Optional: Confidence score (0-1)
}
```

**Output Format:**
```
1
00:00:00,000 --> 00:00:03,500
[Judge] Welcome to the hearing.

2
00:00:04,000 --> 00:00:06,000
[Attorney] Thank you, Your Honor.
```

##### export_vtt()

Export subtitles in VTT (WebVTT) format.

```python
def export_vtt(
    segments: List[Dict[str, Any]],
    output_path: str,
    include_speaker: bool = True
) -> str
```

**Parameters:** Same as `export_srt()`

**Returns:** Path to generated file

**Output Format:**
```
WEBVTT

00:00:00.000 --> 00:00:03.500
<v Judge>Welcome to the hearing.</v>

00:00:04.000 --> 00:00:06.000
<v Attorney>Thank you, Your Honor.</v>
```

##### export_json()

Export subtitles in JSON format with full metadata.

```python
def export_json(
    segments: List[Dict[str, Any]],
    output_path: str,
    pretty: bool = True
) -> str
```

**Parameters:**
- `segments`: List of segment dictionaries
- `output_path`: Path to output JSON file
- `pretty`: Format with indentation (default: True)

**Returns:** Path to generated file

**Output Format:**
```json
{
  "segments": [
    {
      "index": 0,
      "text": "Welcome to the hearing.",
      "start": 0.0,
      "end": 3.5,
      "duration": 3.5,
      "speaker": "Judge",
      "confidence": 0.98
    }
  ],
  "metadata": {
    "total_segments": 1,
    "total_duration": 3.5,
    "chars_per_caption": 42
  }
}
```

##### export_all()

Export to all formats at once.

```python
def export_all(
    segments: List[Dict[str, Any]],
    base_path: str,
    include_speaker: bool = True,
    formats: Optional[List[str]] = None
) -> Dict[str, str]
```

**Parameters:**
- `segments`: List of segment dictionaries
- `base_path`: Base path without extension (e.g., "/path/to/subtitles")
- `include_speaker`: Include speaker labels
- `formats`: List of formats (default: ["srt", "vtt", "json"])

**Returns:** Dictionary mapping format to file path

**Example:**
```python
paths = generator.export_all(segments, "/path/to/subtitles")
# Creates:
#   /path/to/subtitles.srt
#   /path/to/subtitles.vtt
#   /path/to/subtitles.json
```

### Utility Methods

#### format_timestamp_srt()

Format timestamp for SRT format (HH:MM:SS,mmm).

```python
def format_timestamp_srt(seconds: float) -> str
```

#### format_timestamp_vtt()

Format timestamp for VTT format (HH:MM:SS.mmm).

```python
def format_timestamp_vtt(seconds: float) -> str
```

#### wrap_text()

Wrap text into multiple lines at word boundaries.

```python
def wrap_text(text: str, max_chars: int = None) -> List[str]
```

### TranscriptionSegment Class

Data class for representing a transcription segment.

```python
@dataclass
class TranscriptionSegment:
    text: str
    start: float
    end: float
    speaker: Optional[str] = None
    confidence: Optional[float] = None
```

**Methods:**
- `duration() -> float`: Returns segment duration in seconds
- `to_dict() -> Dict[str, Any]`: Converts to dictionary

## Usage Examples

### Legal Transcription with Speakers

```python
from app.workers.pipelines import SubtitleGenerator

# Legal hearing transcription
segments = [
    {
        "text": "This court is now in session. Case number 2024-CV-1234.",
        "start": 0.0,
        "end": 5.2,
        "speaker": "Judge",
        "confidence": 0.99
    },
    {
        "text": "Your Honor, the plaintiff is ready to proceed with opening statements.",
        "start": 5.8,
        "end": 10.5,
        "speaker": "Plaintiff Attorney",
        "confidence": 0.97
    },
    {
        "text": "The defense is also ready, Your Honor.",
        "start": 11.0,
        "end": 13.5,
        "speaker": "Defense Attorney",
        "confidence": 0.98
    }
]

generator = SubtitleGenerator(chars_per_caption=50)

# Export all formats
results = generator.export_all(
    segments,
    "/case_files/2024-CV-1234/hearing_transcript",
    include_speaker=True
)

print(f"Generated subtitles: {results}")
```

### Deposition Transcript

```python
# Deposition with Q&A format
deposition_segments = [
    {
        "text": "Please state your full name for the record.",
        "start": 0.0,
        "end": 3.0,
        "speaker": "Attorney"
    },
    {
        "text": "My name is John Michael Smith.",
        "start": 3.5,
        "end": 5.5,
        "speaker": "Witness"
    },
    {
        "text": "And where were you on the evening of January 15th, 2024?",
        "start": 6.0,
        "end": 10.0,
        "speaker": "Attorney"
    },
    {
        "text": "I was at my office working late on a project deadline.",
        "start": 10.5,
        "end": 14.0,
        "speaker": "Witness"
    }
]

generator = SubtitleGenerator(chars_per_caption=45)
generator.export_srt(deposition_segments, "/depositions/smith_deposition.srt")
```

### Custom Caption Length

```python
# Short captions for mobile viewing
mobile_generator = SubtitleGenerator(chars_per_caption=30)
mobile_generator.export_vtt(segments, "/mobile/subtitles.vtt")

# Longer captions for desktop
desktop_generator = SubtitleGenerator(chars_per_caption=60)
desktop_generator.export_vtt(segments, "/desktop/subtitles.vtt")
```

### Without Speaker Labels

```python
# Generic subtitles without speaker identification
generator = SubtitleGenerator()
generator.export_srt(
    segments,
    "/output/generic.srt",
    include_speaker=False  # No speaker labels
)
```

### Programmatic Access via JSON

```python
import json

generator = SubtitleGenerator()
json_path = generator.export_json(segments, "/output/data.json")

# Load and process
with open(json_path, 'r') as f:
    data = json.load(f)

total_duration = data['metadata']['total_duration']
segment_count = data['metadata']['total_segments']

for segment in data['segments']:
    print(f"[{segment['speaker']}] {segment['text']}")
    print(f"  Time: {segment['start']:.2f}s - {segment['end']:.2f}s")
    print(f"  Confidence: {segment['confidence']:.2%}\n")
```

## Integration with Transcription Pipeline

### Celery Task Integration

```python
from app.workers.celery_app import celery_app
from app.workers.pipelines import SubtitleGenerator

@celery_app.task(name="generate_subtitles")
def generate_subtitles(
    transcription_id: str,
    segments: List[Dict[str, Any]],
    output_formats: List[str] = None
) -> Dict[str, str]:
    """
    Generate subtitles from transcription segments.

    Args:
        transcription_id: Unique transcription identifier
        segments: List of transcription segments
        output_formats: Formats to generate (default: all)

    Returns:
        Dictionary of generated file paths
    """
    generator = SubtitleGenerator(chars_per_caption=42)

    base_path = f"/subtitles/{transcription_id}"

    results = generator.export_all(
        segments,
        base_path,
        include_speaker=True,
        formats=output_formats
    )

    return results
```

### With Whisper/Speech-to-Text

```python
# After transcription with Whisper or similar
def process_transcription(audio_file: str, case_id: str):
    # 1. Transcribe audio (pseudo-code)
    transcription = whisper_model.transcribe(audio_file)

    # 2. Extract segments with speaker diarization
    segments = []
    for segment in transcription['segments']:
        segments.append({
            'text': segment['text'],
            'start': segment['start'],
            'end': segment['end'],
            'speaker': segment.get('speaker', 'Unknown'),
            'confidence': segment.get('confidence', 0.0)
        })

    # 3. Generate subtitles
    generator = SubtitleGenerator(chars_per_caption=50)
    subtitle_paths = generator.export_all(
        segments,
        f"/cases/{case_id}/transcripts/subtitle"
    )

    return subtitle_paths
```

## Format Specifications

### SRT (SubRip) Format

- **Extension**: `.srt`
- **Timestamp Format**: `HH:MM:SS,mmm` (comma separator for milliseconds)
- **Structure**:
  ```
  [Sequence Number]
  [Start] --> [End]
  [Text Line 1]
  [Text Line 2]

  [Next Sequence]
  ...
  ```
- **Speaker Labels**: `[Speaker Name] Text`

### VTT (WebVTT) Format

- **Extension**: `.vtt`
- **Header**: `WEBVTT`
- **Timestamp Format**: `HH:MM:SS.mmm` (period separator for milliseconds)
- **Structure**:
  ```
  WEBVTT

  [Start] --> [End]
  [Text]

  [Start] --> [End]
  [Text]
  ```
- **Speaker Labels**: `<v Speaker Name>Text</v>` (voice tags)

### JSON Format

- **Extension**: `.json`
- **Structure**: Contains segments array and metadata
- **Fields**:
  - `segments`: Array of segment objects
  - `metadata`: Total duration, segment count, settings

## Best Practices

### Caption Length Guidelines

- **Standard**: 42 characters (traditional subtitle standard)
- **Mobile**: 30-35 characters (smaller screens)
- **Desktop/Cinema**: 50-60 characters (larger displays)
- **Accessibility**: Follow WCAG guidelines for reading speed

### Speaker Identification

- Use consistent speaker names throughout transcription
- For legal proceedings:
  - "Judge" or "Justice [Name]"
  - "Plaintiff Attorney" / "Defense Attorney"
  - "Witness" or specific witness names
  - "Court Reporter" for procedural text

### File Organization

```
/cases/
  /{case_id}/
    /transcripts/
      /hearing_2024-01-15/
        ├── audio.mp3
        ├── transcript.json       # Full JSON with metadata
        ├── transcript.srt        # For video players
        ├── transcript.vtt        # For web playback
        └── segments.json         # Raw segments
```

### Performance Considerations

- Batch processing: Use `export_all()` for multiple formats
- Large files: Process in chunks if needed
- File paths: Use absolute paths or Path objects
- Encoding: UTF-8 for international character support

## Testing

Run the comprehensive test suite:

```bash
python test_subtitle_generator.py
```

This will test:
- Basic subtitle generation (SRT, VTT, JSON)
- Timestamp formatting
- Text wrapping with various lengths
- Factory function
- Speaker label inclusion/exclusion

## Troubleshooting

### Common Issues

**Issue**: Text not wrapping correctly
- **Solution**: Adjust `chars_per_caption` parameter

**Issue**: Timestamp formatting incorrect
- **Solution**: Ensure time values are in seconds (float)

**Issue**: Speaker labels not appearing
- **Solution**: Set `include_speaker=True` and ensure segments have 'speaker' field

**Issue**: File encoding problems
- **Solution**: All files use UTF-8 encoding by default

### Error Handling

```python
from pathlib import Path

try:
    generator = SubtitleGenerator(chars_per_caption=42)
    path = generator.export_srt(segments, output_path)
    print(f"Success: {path}")
except Exception as e:
    print(f"Error generating subtitles: {e}")
    # Handle error appropriately
```

## Future Enhancements

Potential additions for future versions:

- [ ] SCC (Scenarist Closed Caption) format
- [ ] TTML (Timed Text Markup Language)
- [ ] Automatic sentence segmentation
- [ ] Style/formatting support (colors, positioning)
- [ ] Multi-language support
- [ ] Automatic timing optimization
- [ ] Caption reading speed analysis

## References

- [SubRip SRT Format](https://en.wikipedia.org/wiki/SubRip)
- [WebVTT Specification](https://www.w3.org/TR/webvtt1/)
- [WCAG Captioning Guidelines](https://www.w3.org/WAI/media/av/captions/)

## Support

For issues or questions:
- Check the test file: `test_subtitle_generator.py`
- Review code documentation in: `app/workers/pipelines/subtitle_generator.py`
- See integration examples in project documentation
