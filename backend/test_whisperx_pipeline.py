"""
Test script for WhisperX transcription pipeline.

This script demonstrates the complete WhisperX transcription workflow
including audio preprocessing, transcription, alignment, and diarization.

Usage:
    python test_whisperx_pipeline.py [audio_file.mp3]

Requirements:
    - WhisperX installed: pip install git+https://github.com/m-bain/whisperX.git
    - FFmpeg installed: sudo apt-get install ffmpeg
    - HF_TOKEN environment variable (for diarization)
"""

import os
import sys
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_audio_preprocessor():
    """Test audio preprocessing functionality."""
    from app.workers.pipelines import AudioPreprocessor

    logger.info("=" * 60)
    logger.info("Testing AudioPreprocessor")
    logger.info("=" * 60)

    # Create a test preprocessor
    preprocessor = AudioPreprocessor(
        target_sample_rate=16000,
        target_channels=1,
        trim_silence=False,
    )

    # Check if FFmpeg is available
    try:
        preprocessor._check_ffmpeg()
        logger.info("✓ FFmpeg is available")
    except RuntimeError as e:
        logger.error(f"✗ FFmpeg check failed: {e}")
        return False

    logger.info("✓ AudioPreprocessor initialized successfully")
    return True


def test_whisperx_dependencies():
    """Test WhisperX dependencies."""
    logger.info("=" * 60)
    logger.info("Testing WhisperX Dependencies")
    logger.info("=" * 60)

    # Check WhisperX
    try:
        import whisperx
        logger.info("✓ WhisperX is installed")
    except ImportError:
        logger.error("✗ WhisperX not found. Install with:")
        logger.error("  pip install git+https://github.com/m-bain/whisperX.git")
        return False

    # Check PyTorch
    try:
        import torch
        logger.info(f"✓ PyTorch is installed (version {torch.__version__})")

        if torch.cuda.is_available():
            logger.info(f"✓ CUDA is available: {torch.cuda.get_device_name(0)}")
        else:
            logger.warning("⚠ CUDA not available, will use CPU (slower)")
    except ImportError:
        logger.error("✗ PyTorch not found")
        return False

    # Check HuggingFace token (for diarization)
    hf_token = os.getenv("HF_TOKEN")
    if hf_token:
        logger.info("✓ HF_TOKEN environment variable is set")
    else:
        logger.warning("⚠ HF_TOKEN not set (diarization will be disabled)")

    return True


def test_basic_transcription(audio_path: str):
    """
    Test basic transcription without diarization.

    Args:
        audio_path: Path to audio file
    """
    from app.workers.pipelines import WhisperXPipeline

    logger.info("=" * 60)
    logger.info("Testing Basic Transcription")
    logger.info("=" * 60)

    # Initialize pipeline
    logger.info(f"Loading Whisper model: base")

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"

    pipeline = WhisperXPipeline(
        model_name="base",  # Small model for testing
        device=device,
        compute_type="float16" if device == "cuda" else "float32",
    )

    # Transcribe
    logger.info(f"Transcribing: {audio_path}")
    result = pipeline.transcribe(
        audio_path=audio_path,
        enable_alignment=True,
        enable_diarization=False,  # Disable for basic test
    )

    # Display results
    logger.info(f"✓ Transcription completed!")
    logger.info(f"  Language: {result.language}")
    logger.info(f"  Duration: {result.duration:.2f}s")
    logger.info(f"  Segments: {len(result.segments)}")

    logger.info("\nFirst 3 segments:")
    for i, segment in enumerate(result.segments[:3]):
        logger.info(f"  [{segment.start:.2f}s - {segment.end:.2f}s] {segment.text}")

    # Full text
    full_text = result.get_full_text()
    logger.info(f"\nFull text ({len(full_text)} characters):")
    logger.info(f"  {full_text[:200]}...")

    # Cleanup
    pipeline.cleanup()

    return result


def test_complete_pipeline(audio_path: str):
    """
    Test complete pipeline with preprocessing and diarization.

    Args:
        audio_path: Path to audio file
    """
    from app.workers.pipelines import AudioPreprocessor, WhisperXPipeline
    import tempfile
    import torch

    logger.info("=" * 60)
    logger.info("Testing Complete Pipeline")
    logger.info("=" * 60)

    # Step 1: Preprocess audio
    logger.info("Step 1: Preprocessing audio...")
    preprocessor = AudioPreprocessor(
        target_sample_rate=16000,
        target_channels=1,
        trim_silence=False,
    )

    temp_dir = tempfile.mkdtemp(prefix="whisperx_test_")
    wav_path = os.path.join(temp_dir, "preprocessed.wav")

    try:
        result = preprocessor.preprocess(
            input_file=audio_path,
            output_file=wav_path,
        )

        logger.info(f"✓ Audio preprocessed")
        logger.info(f"  Output: {result['output_path']}")
        if result['converted_metadata']:
            metadata = result['converted_metadata']
            logger.info(f"  Duration: {metadata['duration']:.2f}s")
            logger.info(f"  Sample rate: {metadata['sample_rate']}Hz")
            logger.info(f"  Channels: {metadata['channels']}")

        # Step 2: Transcribe with WhisperX
        logger.info("\nStep 2: Transcribing with WhisperX...")

        device = "cuda" if torch.cuda.is_available() else "cpu"
        hf_token = os.getenv("HF_TOKEN")
        enable_diarization = bool(hf_token)

        if not enable_diarization:
            logger.warning("⚠ HF_TOKEN not set, skipping diarization")

        pipeline = WhisperXPipeline(
            model_name="base",  # Use small model for testing
            device=device,
            compute_type="float16" if device == "cuda" else "float32",
            hf_token=hf_token,
        )

        transcription = pipeline.transcribe(
            audio_path=wav_path,
            enable_alignment=True,
            enable_diarization=enable_diarization,
            min_speakers=2,
            max_speakers=5,
        )

        logger.info(f"✓ Transcription completed!")
        logger.info(f"  Language: {transcription.language}")
        logger.info(f"  Duration: {transcription.duration:.2f}s")
        logger.info(f"  Segments: {len(transcription.segments)}")

        if transcription.num_speakers:
            logger.info(f"  Speakers: {transcription.num_speakers}")

        # Display segments with speakers
        logger.info("\nFirst 5 segments:")
        for segment in transcription.segments[:5]:
            speaker = f"[{segment.speaker}] " if segment.speaker else ""
            logger.info(f"  {speaker}[{segment.start:.2f}s] {segment.text}")

        # Export results
        logger.info("\nStep 3: Exporting results...")
        export_dir = os.path.join(temp_dir, "exports")
        os.makedirs(export_dir, exist_ok=True)

        # Export as JSON
        json_path = os.path.join(export_dir, "transcription.json")
        with open(json_path, "w") as f:
            json.dump(transcription.to_dict(), f, indent=2)
        logger.info(f"✓ Exported JSON: {json_path}")

        # Export as text
        text_path = os.path.join(export_dir, "transcription.txt")
        with open(text_path, "w") as f:
            f.write(transcription.get_full_text())
        logger.info(f"✓ Exported text: {text_path}")

        # Export by speaker (if available)
        if transcription.num_speakers:
            speaker_texts = transcription.get_text_by_speaker()
            for speaker, text in speaker_texts.items():
                speaker_file = os.path.join(export_dir, f"{speaker}.txt")
                with open(speaker_file, "w") as f:
                    f.write(text)
                logger.info(f"✓ Exported {speaker}: {speaker_file}")

        logger.info(f"\n✓ All exports saved to: {export_dir}")

        # Cleanup
        pipeline.cleanup()

        return transcription

    finally:
        # Cleanup temp files
        preprocessor.cleanup(wav_path)


def test_convenience_functions(audio_path: str):
    """Test convenience functions."""
    from app.workers.pipelines import preprocess_audio, transcribe_audio
    import tempfile
    import torch

    logger.info("=" * 60)
    logger.info("Testing Convenience Functions")
    logger.info("=" * 60)

    temp_dir = tempfile.mkdtemp(prefix="whisperx_conv_test_")

    try:
        # Quick preprocessing
        logger.info("Testing preprocess_audio()...")
        wav_path = preprocess_audio(
            input_file=audio_path,
            output_file=os.path.join(temp_dir, "quick.wav"),
            sample_rate=16000,
            mono=True,
        )
        logger.info(f"✓ Preprocessed: {wav_path}")

        # Quick transcription
        logger.info("\nTesting transcribe_audio()...")
        device = "cuda" if torch.cuda.is_available() else "cpu"

        result = transcribe_audio(
            audio_path=wav_path,
            model="base",
            device=device,
            enable_diarization=False,  # Disable for quick test
        )

        logger.info(f"✓ Transcribed: {len(result.segments)} segments")
        logger.info(f"  First segment: {result.segments[0].text if result.segments else 'N/A'}")

        return result

    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)


def main():
    """Run all tests."""
    logger.info("\n" + "=" * 60)
    logger.info("WhisperX Pipeline Test Suite")
    logger.info("=" * 60 + "\n")

    # Test 1: Dependencies
    if not test_whisperx_dependencies():
        logger.error("\n✗ Dependency check failed. Please install required packages.")
        return 1

    # Test 2: Audio preprocessor
    if not test_audio_preprocessor():
        logger.error("\n✗ Audio preprocessor test failed.")
        return 1

    # Get audio file path
    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
    else:
        logger.warning("\nNo audio file provided. Skipping transcription tests.")
        logger.info("Usage: python test_whisperx_pipeline.py <audio_file>")
        logger.info("\n✓ Basic dependency tests passed!")
        return 0

    # Validate audio file
    if not os.path.exists(audio_path):
        logger.error(f"\n✗ Audio file not found: {audio_path}")
        return 1

    logger.info(f"\nUsing audio file: {audio_path}")
    logger.info(f"File size: {os.path.getsize(audio_path) / (1024*1024):.2f} MB")

    # Test 3: Basic transcription
    try:
        test_basic_transcription(audio_path)
    except Exception as e:
        logger.error(f"\n✗ Basic transcription test failed: {e}", exc_info=True)
        return 1

    # Test 4: Complete pipeline
    try:
        test_complete_pipeline(audio_path)
    except Exception as e:
        logger.error(f"\n✗ Complete pipeline test failed: {e}", exc_info=True)
        return 1

    # Test 5: Convenience functions
    try:
        test_convenience_functions(audio_path)
    except Exception as e:
        logger.error(f"\n✗ Convenience functions test failed: {e}", exc_info=True)
        return 1

    logger.info("\n" + "=" * 60)
    logger.info("✓ All tests passed successfully!")
    logger.info("=" * 60 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
