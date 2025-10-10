# Professional Legal Transcript Export

## Overview

The **TranscriptExporter** provides professional DOCX transcript generation for legal proceedings, depositions, and court transcripts. It uses `docxtpl` (python-docx-template) to create beautifully formatted Word documents suitable for legal use and court submissions.

## Features

- **Professional Legal Formatting**: Clean, readable layout optimized for legal documents
- **Speaker Identification**: Clear speaker labels with optional roles and affiliations
- **Precise Timestamps**: Segment-level timestamps in HH:MM:SS format
- **Case Metadata Header**: Comprehensive case information at document start
- **Participants Table**: Automatic speaker/participant listing
- **Duration Formatting**: Human-readable duration displays
- **Customizable Templates**: Use custom DOCX templates for branding
- **Court-Ready Output**: Suitable for submission to courts and legal proceedings

## File Structure

```
app/workers/pipelines/
├── transcript_exporter.py          # Main exporter class
└── test_transcript_export.py       # Comprehensive test suite

app/workers/templates/
├── transcript_template.docx        # Default professional template
└── create_template.py             # Template generator script
```

## Installation

The required package `docxtpl` is already installed. If you need to install it manually:

```bash
pip install docxtpl
```

## Quick Start

### Basic Usage

```python
from app.workers.pipelines.transcript_exporter import export_transcript

# Define transcript segments
segments = [
    {
        "speaker_id": "1",
        "speaker_label": "Attorney Johnson",
        "text": "Please state your name for the record.",
        "start_time": 0.0,
        "end_time": 3.5,
        "confidence": 0.95,
    },
    {
        "speaker_id": "2",
        "speaker_label": "Dr. Emily Chen",
        "text": "My name is Emily Chen, C-H-E-N.",
        "start_time": 4.0,
        "end_time": 7.2,
        "confidence": 0.98,
    },
]

# Define case metadata
metadata = {
    "case_number": "2025-CV-12345",
    "case_name": "Smith v. Johnson Medical Center",
    "client": "Smith Family Trust",
    "matter_type": "Medical Malpractice",
    "document_name": "Deposition_Chen_Emily_20250109.mp3",
    "date": "January 9, 2025",
    "location": "Law Offices of Johnson & Associates",
    "witness": "Dr. Emily Chen",
    "duration": 3600,  # seconds
}

# Export transcript
success = export_transcript(
    segments=segments,
    metadata=metadata,
    output_path="/path/to/output/transcript.docx"
)
```

### Using the TranscriptExporter Class

```python
from app.workers.pipelines.transcript_exporter import TranscriptExporter

# Initialize exporter with default template
exporter = TranscriptExporter()

# Or use a custom template
exporter = TranscriptExporter(template_path="/path/to/custom_template.docx")

# Export transcript
success = exporter.export_to_docx(
    segments=segments,
    metadata=metadata,
    output_path="/path/to/output.docx"
)
```

## Data Formats

### Segment Format

Each segment dictionary should contain:

```python
{
    "speaker_id": str,              # Unique speaker identifier
    "speaker_label": str,           # Display name for speaker
    "text": str,                    # Transcribed text
    "start_time": float,            # Start time in seconds
    "end_time": float,              # End time in seconds
    "confidence": float,            # Optional: transcription confidence (0-1)
    "speaker_role": str,            # Optional: speaker's role (e.g., "Attorney", "Witness")
    "speaker_affiliation": str,     # Optional: organization/affiliation
}
```

### Metadata Format

```python
{
    # Required fields
    "case_number": str,             # Case identification number
    "case_name": str,               # Full case name
    "client": str,                  # Client name
    "matter_type": str,             # Type of legal matter
    "document_name": str,           # Audio/video filename

    # Optional fields
    "date": str | datetime,         # Recording/proceeding date
    "location": str,                # Location of proceeding
    "witness": str,                 # Primary witness/deponent
    "duration": float,              # Total duration in seconds
}
```

## Integration with WhisperX/Transcription Pipeline

### Converting WhisperX Output

```python
from app.workers.pipelines.whisperx_pipeline import transcribe_audio
from app.workers.pipelines.transcript_exporter import export_transcript

# Transcribe audio
result = transcribe_audio("/path/to/audio.mp3")

# Convert to export format
segments = []
for i, seg in enumerate(result.segments):
    segments.append({
        "speaker_id": seg.get("speaker", "UNKNOWN"),
        "speaker_label": f"Speaker {seg.get('speaker', 'UNKNOWN')}",
        "text": seg["text"],
        "start_time": seg["start"],
        "end_time": seg["end"],
        "segment_number": i + 1,
    })

# Prepare metadata from database
metadata = {
    "case_number": case.case_number,
    "case_name": case.name,
    "client": case.client,
    "matter_type": case.matter_type,
    "document_name": document.filename,
    "date": document.created_at,
    "duration": transcription.duration,
}

# Export
export_transcript(segments, metadata, output_path)
```

### Database Integration Example

```python
from sqlalchemy.orm import Session
from app.models import Transcription, Document, Case
from app.workers.pipelines.transcript_exporter import export_transcript

def export_transcription_to_docx(
    db: Session,
    transcription_id: int,
    output_path: str
) -> bool:
    """Export a database transcription to DOCX."""

    # Fetch transcription with relationships
    transcription = (
        db.query(Transcription)
        .filter(Transcription.id == transcription_id)
        .first()
    )

    if not transcription:
        return False

    document = transcription.document
    case = document.case

    # Prepare segments
    segments = []
    for i, seg in enumerate(transcription.segments):
        segments.append({
            "speaker_id": seg.get("speaker_id", "UNKNOWN"),
            "speaker_label": seg.get("speaker_label", f"Speaker {seg.get('speaker_id', 'UNKNOWN')}"),
            "text": seg["text"],
            "start_time": seg["start"],
            "end_time": seg["end"],
            "segment_number": i + 1,
            "confidence": seg.get("confidence"),
        })

    # Prepare metadata
    metadata = {
        "case_number": case.case_number,
        "case_name": case.name,
        "client": case.client,
        "matter_type": case.matter_type,
        "document_name": document.filename,
        "date": document.created_at,
        "duration": transcription.duration,
    }

    # Export
    return export_transcript(segments, metadata, output_path)
```

## Template Customization

### Using the Default Template

The default template includes:
- Professional header with case information
- Document information table
- Participants/speakers list
- Formatted transcript segments with timestamps
- Certification footer

### Creating a Custom Template

1. Use the template generator:

```bash
python app/workers/templates/create_template.py
```

2. Or modify the existing template in Word:
   - Open `app/workers/templates/transcript_template.docx`
   - Edit formatting, styles, headers, footers
   - Use Jinja2 placeholders for dynamic content:
     - `{{ case_number }}`
     - `{{ speaker_label }}`
     - `{{ segment.text }}`
     - etc.

3. Use your custom template:

```python
exporter = TranscriptExporter(template_path="/path/to/custom_template.docx")
```

### Available Template Variables

**Case Information:**
- `{{ case_number }}`
- `{{ case_name }}`
- `{{ client }}`
- `{{ matter_type }}`

**Document Information:**
- `{{ document_name }}`
- `{{ proceeding_date }}`
- `{{ location }}`
- `{{ witness }}`
- `{{ total_duration }}`
- `{{ segment_count }}`

**Export Information:**
- `{{ export_date }}`
- `{{ export_time }}`

**Speakers (list):**
```
{% for speaker in speakers %}
  {{ speaker.label }}
  {{ speaker.role }}
  {{ speaker.affiliation }}
  {{ speaker.appearance_count }}
{% endfor %}
```

**Segments (list):**
```
{% for segment in segments %}
  {{ segment.number }}
  {{ segment.speaker_label }}
  {{ segment.text }}
  {{ segment.timestamp }}
  {{ segment.time_range }}
  {{ segment.duration }}
{% endfor %}
```

## API Reference

### TranscriptExporter Class

```python
class TranscriptExporter:
    def __init__(self, template_path: Optional[str] = None):
        """
        Initialize the transcript exporter.

        Args:
            template_path: Path to custom DOCX template.
                          If None, uses default template.
        """

    def export_to_docx(
        self,
        segments: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        output_path: str,
    ) -> bool:
        """
        Export transcript to DOCX file.

        Args:
            segments: List of transcript segments
            metadata: Case and document metadata
            output_path: Output file path

        Returns:
            True if successful, False otherwise
        """
```

### Helper Classes

```python
@dataclass
class Speaker:
    id: str
    label: str
    role: Optional[str] = None
    affiliation: Optional[str] = None

@dataclass
class TranscriptSegment:
    speaker_id: str
    speaker_label: str
    text: str
    start_time: float
    end_time: float
    segment_number: int
    confidence: Optional[float] = None
```

### Convenience Function

```python
def export_transcript(
    segments: List[Dict[str, Any]],
    metadata: Dict[str, Any],
    output_path: str,
    template_path: Optional[str] = None,
) -> bool:
    """
    Convenience function to export a transcript.

    Args:
        segments: List of transcript segments
        metadata: Case and document metadata
        output_path: Output file path
        template_path: Optional custom template path

    Returns:
        True if successful, False otherwise
    """
```

## Testing

Run the comprehensive test suite:

```bash
python app/workers/pipelines/test_transcript_export.py
```

Or test with example data:

```bash
python app/workers/pipelines/transcript_exporter.py
```

## Output Examples

The exporter creates professional DOCX files with:

1. **Header Section**: Case number, name, client, matter type, date, location
2. **Document Info**: Filename, witness, duration, segment count
3. **Participants List**: All speakers with roles and affiliations
4. **Transcript Body**:
   - Speaker labels in bold
   - Timestamps in brackets [HH:MM:SS]
   - Clean paragraph formatting
   - Proper line spacing for readability
5. **Certification Footer**: Export date/time and certification text

## Best Practices

1. **Segment Quality**: Ensure segments have accurate timestamps and speaker identification
2. **Metadata Completeness**: Provide all required metadata fields for professional output
3. **Speaker Labels**: Use descriptive speaker labels (e.g., "Attorney Johnson" vs "Speaker 1")
4. **File Paths**: Use absolute paths for output files to avoid path issues
5. **Error Handling**: Always check the return value for successful export
6. **Template Testing**: Test custom templates with sample data before production use

## Troubleshooting

### Template Not Found Error
```python
FileNotFoundError: Template file not found
```
**Solution**: Ensure the template exists at the specified path, or create it:
```bash
python app/workers/templates/create_template.py
```

### Empty Segments
**Solution**: Verify segments list is not empty and has required fields

### Missing Metadata
**Solution**: Provide all required metadata fields (case_number, case_name, etc.)

### Formatting Issues
**Solution**: Check template formatting in Word; ensure Jinja2 syntax is correct

## Future Enhancements

Potential future features:
- PDF export option
- Multi-language support
- Custom styling via configuration
- Redaction support for sensitive information
- Audio waveform integration
- Automated speaker identification enhancement
- Export to SRT/VTT subtitle formats (already available via SubtitleGenerator)

## Related Components

- `whisperx_pipeline.py`: Audio transcription
- `subtitle_generator.py`: SRT/VTT subtitle export
- `audio_preprocessing.py`: Audio preparation
- Database models: `Transcription`, `Document`, `Case`

## License

Part of the LegalEase backend system.
