# WhisperX Quick Start Guide

## Installation

```bash
# 1. Install system dependencies
sudo apt-get update
sudo apt-get install ffmpeg

# 2. Install WhisperX (from GitHub, not PyPI)
cd /home/Allie/develop/legalease/backend
source .venv/bin/activate
uv pip install git+https://github.com/m-bain/whisperX.git

# 3. Set HuggingFace token (optional, for speaker diarization)
export HF_TOKEN="your_huggingface_token_here"
# Or add to .env file:
echo "HF_TOKEN=your_token_here" >> .env
```

## Quick Test

```bash
# Test basic functionality (no audio file needed)
python test_whisperx_pipeline.py

# Test with audio file
python test_whisperx_pipeline.py /path/to/audio.mp3
```

## Basic Usage

### Simple Transcription

```python
from app.workers.pipelines import transcribe_audio

# Quick transcription
result = transcribe_audio(
    audio_path="interview.mp3",
    model="large-v3",
    device="cuda",  # or "cpu"
    enable_diarization=False
)

print(f"Language: {result.language}")
print(f"Full text: {result.get_full_text()}")
```

### With Preprocessing

```python
from app.workers.pipelines import preprocess_audio, transcribe_audio

# Step 1: Convert to optimal format
wav_path = preprocess_audio(
    input_file="interview.mp3",
    sample_rate=16000,
    mono=True
)

# Step 2: Transcribe
result = transcribe_audio(
    audio_path=wav_path,
    model="large-v3",
    device="cuda"
)
```

### With Speaker Diarization

```python
from app.workers.pipelines import WhisperXPipeline

# Initialize pipeline with HuggingFace token
pipeline = WhisperXPipeline(
    model_name="large-v3",
    device="cuda",
    hf_token="your_hf_token"  # or set HF_TOKEN env var
)

# Transcribe with speaker labels
result = pipeline.transcribe(
    audio_path="deposition.wav",
    enable_diarization=True,
    min_speakers=2,
    max_speakers=5
)

# Get text by speaker
for speaker, text in result.get_text_by_speaker().items():
    print(f"{speaker}:")
    print(text[:200] + "...\n")
```

### Complete Workflow

```python
from app.workers.pipelines import AudioPreprocessor, WhisperXPipeline

# Step 1: Preprocess
preprocessor = AudioPreprocessor()
preprocess_result = preprocessor.preprocess("interview.mp3")
audio_path = preprocess_result["output_path"]

# Step 2: Transcribe
pipeline = WhisperXPipeline(model_name="large-v3", device="cuda")
result = pipeline.transcribe(
    audio_path=audio_path,
    enable_alignment=True,
    enable_diarization=True
)

# Step 3: Process results
print(f"Detected {result.num_speakers} speakers")
print(f"Duration: {result.duration:.2f}s")

for segment in result.segments:
    speaker = f"[{segment.speaker}] " if segment.speaker else ""
    print(f"{speaker}[{segment.start:.2f}s] {segment.text}")

# Step 4: Cleanup
preprocessor.cleanup(audio_path)
pipeline.cleanup()
```

## Model Selection

| Model | Size | Speed | Accuracy | Best For |
|-------|------|-------|----------|----------|
| `tiny` | 39M | Fastest | Low | Testing only |
| `base` | 74M | Fast | Medium | Development |
| `small` | 244M | Moderate | Good | General use |
| `medium` | 769M | Slow | Very Good | Production |
| `large-v3` | 1550M | Slowest | Best | Legal documents |

**Recommendation**: Use `large-v3` for legal depositions and court proceedings.

## HuggingFace Token Setup

Required only for speaker diarization:

1. Create account: https://huggingface.co/join
2. Accept Pyannote terms:
   - https://huggingface.co/pyannote/speaker-diarization
   - https://huggingface.co/pyannote/segmentation
3. Generate token: https://huggingface.co/settings/tokens
4. Set environment variable:
   ```bash
   export HF_TOKEN="your_token_here"
   ```

## Common Issues

### CUDA Out of Memory
```python
# Use smaller batch size or CPU
result = pipeline.transcribe(audio_path, batch_size=8)
# or
pipeline = WhisperXPipeline(device="cpu")
```

### FFmpeg Not Found
```bash
sudo apt-get install ffmpeg
```

### WhisperX Import Error
```bash
# Must install from GitHub
pip install git+https://github.com/m-bain/whisperX.git
```

## API Reference

See full documentation in `WHISPERX_SETUP.md`

## Support

- WhisperX: https://github.com/m-bain/whisperX
- Issues: Check backend logs for detailed error messages
