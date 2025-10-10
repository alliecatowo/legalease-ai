# WhisperX Transcription Pipeline Setup Guide

This guide covers the installation and usage of the WhisperX transcription pipeline for the LegalEase backend.

## Overview

The WhisperX pipeline provides state-of-the-art audio transcription with:
- **High-accuracy transcription** using OpenAI's Whisper models
- **Word-level timestamps** via Wav2Vec2 alignment
- **Speaker diarization** using Pyannote.audio
- **Audio preprocessing** with FFmpeg for optimal format conversion

## Architecture

```
┌─────────────────┐
│  Audio File     │
│  (any format)   │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ AudioPreprocessor│
│  - FFmpeg       │
│  - 16kHz mono   │
│  - WAV format   │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ WhisperXPipeline│
│  1. Transcribe  │
│  2. Align       │
│  3. Diarize     │
└────────┬────────┘
         │
         v
┌─────────────────┐
│TranscriptionResult│
│  - Segments     │
│  - Speakers     │
│  - Timestamps   │
└─────────────────┘
```

## Requirements

### System Dependencies

1. **FFmpeg** (required for audio preprocessing)
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install ffmpeg

   # macOS
   brew install ffmpeg

   # Verify installation
   ffmpeg -version
   ```

2. **CUDA** (recommended for GPU acceleration)
   ```bash
   # Check CUDA availability
   nvidia-smi

   # Install PyTorch with CUDA support (if needed)
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

### Python Dependencies

The main dependencies are already in `pyproject.toml`, but WhisperX requires a special installation:

```bash
# Install WhisperX from GitHub (not available on PyPI)
uv pip install git+https://github.com/m-bain/whisperX.git

# Or using regular pip in your virtual environment
pip install git+https://github.com/m-bain/whisperX.git
```

**Note**: WhisperX must be installed from GitHub because it's not published to PyPI.

### HuggingFace Token (for Speaker Diarization)

Speaker diarization requires Pyannote models from HuggingFace, which need authentication:

1. Create a HuggingFace account: https://huggingface.co/join
2. Accept the terms for Pyannote models:
   - https://huggingface.co/pyannote/speaker-diarization
   - https://huggingface.co/pyannote/segmentation
3. Generate an access token: https://huggingface.co/settings/tokens
4. Set the token as an environment variable:
   ```bash
   export HF_TOKEN="your_token_here"

   # Or add to your .env file
   echo "HF_TOKEN=your_token_here" >> .env
   ```

## Installation

### Complete Installation Steps

```bash
# 1. Navigate to backend directory
cd /home/Allie/develop/legalease/backend

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Install system dependencies
sudo apt-get install ffmpeg  # Ubuntu/Debian

# 4. Install WhisperX
uv pip install git+https://github.com/m-bain/whisperX.git

# 5. Set HuggingFace token (for diarization)
export HF_TOKEN="your_token_here"

# 6. Verify installation
python -c "import whisperx; print('WhisperX installed successfully')"
```

### Model Downloads

Models are downloaded automatically on first use:

- **Whisper models** (~150MB to ~3GB depending on size):
  - `tiny` (39M params, ~150MB)
  - `base` (74M params, ~290MB)
  - `small` (244M params, ~970MB)
  - `medium` (769M params, ~3.1GB)
  - `large-v2` (1550M params, ~6.2GB)
  - `large-v3` (1550M params, ~6.2GB) - **Recommended for legal transcription**

- **Alignment models** (~300MB per language)
- **Diarization models** (~1.2GB total)

Models are cached in `~/.cache/whisperx/` and `~/.cache/huggingface/`

## Usage

### Basic Transcription

```python
from app.workers.pipelines import WhisperXPipeline

# Initialize pipeline
pipeline = WhisperXPipeline(
    model_name="large-v3",  # Best accuracy
    device="cuda",          # Use GPU
    compute_type="float16"  # Fast inference
)

# Transcribe audio
result = pipeline.transcribe(
    audio_path="/path/to/audio.mp3",
    enable_alignment=True,      # Word-level timestamps
    enable_diarization=False    # Speaker labels (requires HF_TOKEN)
)

# Access results
print(f"Language: {result.language}")
print(f"Duration: {result.duration:.2f}s")
print(f"Full text: {result.get_full_text()}")

for segment in result.segments:
    print(f"[{segment.start:.2f}s - {segment.end:.2f}s] {segment.text}")
```

### Audio Preprocessing

```python
from app.workers.pipelines import AudioPreprocessor

# Initialize preprocessor
preprocessor = AudioPreprocessor(
    target_sample_rate=16000,  # WhisperX optimal
    target_channels=1,         # Mono
    trim_silence=False         # Optional
)

# Convert audio to optimal format
result = preprocessor.preprocess(
    input_file="/path/to/audio.mp3",
    output_file="/tmp/audio_preprocessed.wav"
)

print(f"Preprocessed audio: {result['output_path']}")
print(f"Duration: {result['converted_metadata']['duration']:.2f}s")
```

### Complete Workflow with Preprocessing

```python
from app.workers.pipelines import AudioPreprocessor, WhisperXPipeline

# Step 1: Preprocess audio
preprocessor = AudioPreprocessor()
preprocess_result = preprocessor.preprocess(
    input_file="/path/to/interview.mp3"
)

audio_path = preprocess_result["output_path"]

# Step 2: Transcribe with WhisperX
pipeline = WhisperXPipeline(
    model_name="large-v3",
    device="cuda",
    hf_token="your_hf_token_here"  # For diarization
)

transcription = pipeline.transcribe(
    audio_path=audio_path,
    enable_alignment=True,
    enable_diarization=True,
    min_speakers=2,
    max_speakers=5
)

# Step 3: Process results
print(f"Detected {transcription.num_speakers} speakers")

for speaker, text in transcription.get_text_by_speaker().items():
    print(f"\n{speaker}:")
    print(text)

# Step 4: Cleanup temporary files
preprocessor.cleanup(audio_path)
pipeline.cleanup()
```

### Speaker Diarization

```python
# Enable speaker diarization
result = pipeline.transcribe(
    audio_path="deposition.wav",
    enable_diarization=True,
    min_speakers=2,    # Minimum expected speakers
    max_speakers=4     # Maximum expected speakers
)

# Access speaker information
print(f"Detected speakers: {result.num_speakers}")
print(f"Speaker labels: {result.speakers['unique_speakers']}")

# Get text by speaker
speaker_texts = result.get_text_by_speaker()
for speaker, text in speaker_texts.items():
    print(f"\n{speaker}:")
    print(text[:200] + "...")  # First 200 chars
```

### Convenience Functions

```python
from app.workers.pipelines import transcribe_audio, preprocess_audio

# Quick preprocessing
wav_path = preprocess_audio(
    input_file="interview.mp3",
    sample_rate=16000,
    mono=True
)

# Quick transcription
result = transcribe_audio(
    audio_path=wav_path,
    model="large-v3",
    device="cuda",
    enable_diarization=True
)
```

## Integration with Celery Tasks

Update the transcription task to use WhisperX:

```python
# app/workers/tasks/transcription.py

from app.workers.celery_app import celery_app
from app.workers.pipelines import AudioPreprocessor, WhisperXPipeline
from app.core.database import get_db
from app.models.transcription import Transcription
import os

@celery_app.task(name="transcribe_audio", bind=True)
def transcribe_audio_task(
    self,
    transcription_id: int,
    audio_file_path: str,
    enable_diarization: bool = True,
):
    """Transcribe audio using WhisperX pipeline."""

    # Download audio from MinIO to temp file
    # (implementation depends on your storage service)
    local_audio_path = download_from_minio(audio_file_path)

    try:
        # Preprocess audio
        preprocessor = AudioPreprocessor()
        preprocess_result = preprocessor.preprocess(local_audio_path)
        wav_path = preprocess_result["output_path"]

        # Transcribe with WhisperX
        pipeline = WhisperXPipeline(
            model_name="large-v3",
            device="cuda",
            hf_token=os.getenv("HF_TOKEN")
        )

        result = pipeline.transcribe(
            audio_path=wav_path,
            enable_alignment=True,
            enable_diarization=enable_diarization,
            min_speakers=2,
            max_speakers=10
        )

        # Save to database
        db = next(get_db())
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id
        ).first()

        transcription.segments = result.to_dict()["segments"]
        transcription.speakers = result.speakers
        transcription.duration = result.duration
        db.commit()

        # Cleanup
        preprocessor.cleanup(wav_path)
        pipeline.cleanup()

        return {
            "status": "completed",
            "transcription_id": transcription_id,
            "language": result.language,
            "duration": result.duration,
            "num_speakers": result.num_speakers
        }

    finally:
        # Cleanup temp files
        if os.path.exists(local_audio_path):
            os.remove(local_audio_path)
```

## Model Selection Guide

Choose the appropriate Whisper model based on your needs:

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| `tiny` | 39M | Fastest | Low | Quick testing, draft transcripts |
| `base` | 74M | Very Fast | Medium | Development, previews |
| `small` | 244M | Fast | Good | General use, non-critical |
| `medium` | 769M | Moderate | Very Good | Production, good balance |
| `large-v2` | 1550M | Slow | Excellent | Legal documents, high accuracy |
| `large-v3` | 1550M | Slow | Best | **Recommended for legal work** |

**Recommendation**: Use `large-v3` for legal depositions, court proceedings, and client interviews.

## Performance Optimization

### GPU Acceleration

```python
# Check CUDA availability
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA device: {torch.cuda.get_device_name(0)}")

# Use appropriate compute type
pipeline = WhisperXPipeline(
    model_name="large-v3",
    device="cuda",
    compute_type="float16"  # Faster than float32, minimal accuracy loss
)
```

### Batch Processing

```python
# Process multiple files efficiently
audio_files = [
    "deposition_1.mp3",
    "deposition_2.mp3",
    "deposition_3.mp3"
]

pipeline = WhisperXPipeline(model_name="large-v3", device="cuda")

results = pipeline.transcribe_batch(
    audio_paths=audio_files,
    enable_alignment=True,
    enable_diarization=True
)

for audio_file, result in zip(audio_files, results):
    print(f"{audio_file}: {result.duration:.2f}s, {result.num_speakers} speakers")
```

### Memory Management

```python
# Process large files with memory cleanup
pipeline = WhisperXPipeline(model_name="large-v3", device="cuda")

for audio_file in large_audio_files:
    result = pipeline.transcribe(audio_file)

    # Process result
    save_to_database(result)

    # Clear memory between files
    import gc
    gc.collect()
    torch.cuda.empty_cache()

# Final cleanup
pipeline.cleanup()
```

## Troubleshooting

### Common Issues

1. **CUDA Out of Memory**
   ```python
   # Use smaller batch size
   result = pipeline.transcribe(audio_path, batch_size=8)

   # Or use CPU
   pipeline = WhisperXPipeline(device="cpu")
   ```

2. **FFmpeg Not Found**
   ```bash
   # Install FFmpeg
   sudo apt-get install ffmpeg

   # Verify
   which ffmpeg
   ```

3. **HuggingFace Token Error**
   ```bash
   # Set token environment variable
   export HF_TOKEN="your_token_here"

   # Or pass directly
   pipeline = WhisperXPipeline(hf_token="your_token_here")
   ```

4. **Alignment Model Not Found**
   ```python
   # Models download automatically, ensure internet connection
   # Check cache directory
   ls ~/.cache/whisperx/
   ```

## Advanced Features

### Custom Language

```python
# Force specific language (skip auto-detection)
pipeline = WhisperXPipeline(
    model_name="large-v3",
    language="en"  # English
)

# Supported languages: en, es, fr, de, it, pt, nl, etc.
```

### Word-Level Details

```python
result = pipeline.transcribe(audio_path, enable_alignment=True)

for segment in result.segments:
    print(f"Segment: {segment.text}")

    # Access word-level timestamps
    if segment.words:
        for word_info in segment.words:
            print(f"  {word_info['word']}: {word_info['start']:.2f}s - {word_info['end']:.2f}s")
```

### Export Results

```python
# Export as JSON
import json

with open("transcript.json", "w") as f:
    json.dump(result.to_dict(), f, indent=2)

# Export as SRT subtitles (use SubtitleGenerator)
from app.workers.pipelines import SubtitleGenerator

subtitle_gen = SubtitleGenerator()
srt_content = subtitle_gen.generate_srt(result.segments)

with open("transcript.srt", "w") as f:
    f.write(srt_content)
```

## Best Practices for Legal Transcription

1. **Use Large Models**: Always use `large-v3` for legal work
2. **Enable Diarization**: Speaker identification is critical for depositions
3. **Preprocess Audio**: Convert to optimal format first
4. **Review Output**: Always review transcriptions manually
5. **Save Metadata**: Store model version, timestamps, and confidence scores
6. **Backup Raw Audio**: Keep original files alongside transcripts
7. **Test First**: Run on small samples before batch processing

## Support & Resources

- **WhisperX GitHub**: https://github.com/m-bain/whisperX
- **Whisper Models**: https://github.com/openai/whisper
- **Pyannote.audio**: https://github.com/pyannote/pyannote-audio
- **FFmpeg Documentation**: https://ffmpeg.org/documentation.html

## License Considerations

- **Whisper**: MIT License (OpenAI)
- **WhisperX**: BSD-4-Clause License
- **Pyannote.audio**: MIT License (requires HuggingFace agreement)

Make sure to review and comply with all licenses for production use.
