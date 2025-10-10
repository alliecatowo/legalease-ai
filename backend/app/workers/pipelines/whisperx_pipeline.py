"""
WhisperX Transcription Pipeline

Advanced transcription pipeline using WhisperX for:
- High-accuracy transcription with Whisper
- Word-level timestamp alignment with Wav2Vec2
- Speaker diarization with Pyannote.audio

WhisperX: https://github.com/m-bain/whisperX
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionSegment:
    """A segment of transcription with timing and speaker information."""

    start: float
    end: float
    text: str
    speaker: Optional[str] = None
    words: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert segment to dictionary."""
        return asdict(self)


@dataclass
class TranscriptionResult:
    """Complete transcription result with metadata."""

    segments: List[TranscriptionSegment]
    language: str
    duration: float
    num_speakers: Optional[int] = None
    speakers: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "segments": [seg.to_dict() for seg in self.segments],
            "language": self.language,
            "duration": self.duration,
            "num_speakers": self.num_speakers,
            "speakers": self.speakers,
            "metadata": self.metadata,
        }

    def get_full_text(self) -> str:
        """Get complete transcription as single text."""
        return " ".join(seg.text.strip() for seg in self.segments if seg.text.strip())

    def get_text_by_speaker(self) -> Dict[str, str]:
        """Get text grouped by speaker."""
        speaker_texts = {}
        for seg in self.segments:
            speaker = seg.speaker or "Unknown"
            if speaker not in speaker_texts:
                speaker_texts[speaker] = []
            speaker_texts[speaker].append(seg.text.strip())

        return {
            speaker: " ".join(texts)
            for speaker, texts in speaker_texts.items()
        }


class WhisperXPipeline:
    """
    WhisperX transcription pipeline with alignment and diarization.

    This pipeline provides state-of-the-art audio transcription with:
    1. Whisper model for initial transcription
    2. Wav2Vec2 for word-level timestamp alignment
    3. Pyannote.audio for speaker diarization

    Requirements:
    - whisperx (install: pip install git+https://github.com/m-bain/whisperX.git)
    - torch with CUDA support (recommended)
    - HuggingFace token for Pyannote models (optional, for diarization)

    Usage:
        pipeline = WhisperXPipeline(
            model_name="large-v3",
            device="cuda",
            compute_type="float16"
        )

        result = pipeline.transcribe(
            "audio.wav",
            enable_diarization=True,
            min_speakers=2,
            max_speakers=5
        )
    """

    def __init__(
        self,
        model_name: str = "large-v3",
        device: str = "cuda",
        compute_type: str = "float16",
        language: Optional[str] = None,
        hf_token: Optional[str] = None,
    ):
        """
        Initialize WhisperX pipeline.

        Args:
            model_name: Whisper model size (tiny, base, small, medium, large-v2, large-v3)
            device: Device to run on ("cuda" or "cpu")
            compute_type: Computation precision ("float16", "int8", "float32")
            language: Force specific language (None for auto-detection)
            hf_token: HuggingFace token for Pyannote models (required for diarization)
        """
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.hf_token = hf_token or os.getenv("HF_TOKEN")

        # Lazy-loaded models
        self._whisper_model = None
        self._alignment_model = None
        self._diarization_pipeline = None

        # Check dependencies
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Check if required dependencies are installed."""
        try:
            import whisperx
            logger.info("WhisperX is available")
        except ImportError:
            raise ImportError(
                "WhisperX is not installed. Install it with:\n"
                "pip install git+https://github.com/m-bain/whisperX.git"
            )

        try:
            import torch
            if self.device == "cuda" and not torch.cuda.is_available():
                logger.warning("CUDA requested but not available, falling back to CPU")
                self.device = "cpu"
            logger.info(f"PyTorch available, using device: {self.device}")
        except ImportError:
            raise ImportError("PyTorch is required for WhisperX")

    def load_model(self) -> None:
        """Load Whisper model."""
        if self._whisper_model is not None:
            return

        logger.info(f"Loading Whisper model: {self.model_name}")
        import whisperx

        try:
            self._whisper_model = whisperx.load_model(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
                language=self.language,
            )
            logger.info(f"Successfully loaded Whisper model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise

    def load_alignment_model(self, language_code: str) -> None:
        """
        Load alignment model for word-level timestamps.

        Args:
            language_code: Language code (e.g., "en", "es", "fr")
        """
        if self._alignment_model is not None:
            return

        logger.info(f"Loading alignment model for language: {language_code}")
        import whisperx

        try:
            self._alignment_model, self._alignment_metadata = whisperx.load_align_model(
                language_code=language_code,
                device=self.device,
            )
            logger.info(f"Successfully loaded alignment model for {language_code}")
        except Exception as e:
            logger.error(f"Failed to load alignment model: {e}")
            raise

    def load_diarization_pipeline(self) -> None:
        """Load speaker diarization pipeline."""
        if self._diarization_pipeline is not None:
            return

        if not self.hf_token:
            raise ValueError(
                "HuggingFace token required for diarization. "
                "Set HF_TOKEN environment variable or pass hf_token parameter."
            )

        logger.info("Loading diarization pipeline")
        import whisperx

        try:
            self._diarization_pipeline = whisperx.DiarizationPipeline(
                use_auth_token=self.hf_token,
                device=self.device,
            )
            logger.info("Successfully loaded diarization pipeline")
        except Exception as e:
            logger.error(f"Failed to load diarization pipeline: {e}")
            raise

    def transcribe(
        self,
        audio_path: str,
        enable_alignment: bool = True,
        enable_diarization: bool = False,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None,
        batch_size: int = 16,
    ) -> TranscriptionResult:
        """
        Transcribe audio file with optional alignment and diarization.

        Args:
            audio_path: Path to audio file (preferably 16kHz mono WAV)
            enable_alignment: Enable word-level timestamp alignment (default: True)
            enable_diarization: Enable speaker diarization (default: False)
            min_speakers: Minimum number of speakers (optional)
            max_speakers: Maximum number of speakers (optional)
            batch_size: Batch size for processing (default: 16)

        Returns:
            TranscriptionResult with segments, speakers, and metadata
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Transcribing {audio_path}")

        # Load Whisper model
        self.load_model()

        # Step 1: Transcribe with Whisper
        logger.info("Step 1/3: Running Whisper transcription...")
        import whisperx

        audio = whisperx.load_audio(audio_path)
        result = self._whisper_model.transcribe(
            audio,
            batch_size=batch_size,
        )

        detected_language = result.get("language", "en")
        logger.info(f"Detected language: {detected_language}")

        segments = result["segments"]
        logger.info(f"Initial transcription: {len(segments)} segments")

        # Step 2: Align for word-level timestamps (optional)
        if enable_alignment:
            logger.info("Step 2/3: Aligning word-level timestamps...")
            self.load_alignment_model(detected_language)

            result = whisperx.align(
                segments,
                self._alignment_model,
                self._alignment_metadata,
                audio,
                device=self.device,
                return_char_alignments=False,
            )
            segments = result["segments"]
            logger.info("Alignment completed")
        else:
            logger.info("Step 2/3: Skipping alignment")

        # Step 3: Speaker diarization (optional)
        speakers_info = None
        num_speakers = None

        if enable_diarization:
            logger.info("Step 3/3: Running speaker diarization...")
            self.load_diarization_pipeline()

            diarize_segments = self._diarization_pipeline(
                audio_path,
                min_speakers=min_speakers,
                max_speakers=max_speakers,
            )

            result = whisperx.assign_word_speakers(
                diarize_segments,
                segments,
            )
            segments = result["segments"]

            # Extract speaker information
            unique_speakers = set()
            for seg in segments:
                if "speaker" in seg:
                    unique_speakers.add(seg["speaker"])

            num_speakers = len(unique_speakers)
            speakers_info = {
                "unique_speakers": sorted(list(unique_speakers)),
                "count": num_speakers,
            }
            logger.info(f"Diarization completed: {num_speakers} speakers detected")
        else:
            logger.info("Step 3/3: Skipping diarization")

        # Convert to our data structures
        transcription_segments = []
        for seg in segments:
            transcription_segments.append(
                TranscriptionSegment(
                    start=seg["start"],
                    end=seg["end"],
                    text=seg["text"],
                    speaker=seg.get("speaker"),
                    words=seg.get("words"),
                )
            )

        # Calculate total duration
        duration = max(seg.end for seg in transcription_segments) if transcription_segments else 0.0

        return TranscriptionResult(
            segments=transcription_segments,
            language=detected_language,
            duration=duration,
            num_speakers=num_speakers,
            speakers=speakers_info,
            metadata={
                "model": self.model_name,
                "device": self.device,
                "alignment_enabled": enable_alignment,
                "diarization_enabled": enable_diarization,
            },
        )

    def transcribe_batch(
        self,
        audio_paths: List[str],
        **kwargs,
    ) -> List[TranscriptionResult]:
        """
        Transcribe multiple audio files.

        Args:
            audio_paths: List of audio file paths
            **kwargs: Arguments passed to transcribe()

        Returns:
            List of TranscriptionResult objects
        """
        results = []
        for audio_path in audio_paths:
            try:
                result = self.transcribe(audio_path, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to transcribe {audio_path}: {e}")
                # Continue with next file
                continue

        return results

    def cleanup(self) -> None:
        """Release models from memory."""
        logger.info("Cleaning up WhisperX models")
        self._whisper_model = None
        self._alignment_model = None
        self._diarization_pipeline = None

        # Force garbage collection
        import gc
        gc.collect()

        # Clear CUDA cache if available
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info("Cleared CUDA cache")
        except ImportError:
            pass


# Convenience function for quick transcription
def transcribe_audio(
    audio_path: str,
    model: str = "large-v3",
    device: str = "cuda",
    language: Optional[str] = None,
    enable_diarization: bool = False,
    hf_token: Optional[str] = None,
) -> TranscriptionResult:
    """
    Quick transcription function.

    Args:
        audio_path: Path to audio file
        model: Whisper model name (default: "large-v3")
        device: Device to use (default: "cuda")
        language: Language code or None for auto-detection
        enable_diarization: Enable speaker diarization (default: False)
        hf_token: HuggingFace token for diarization

    Returns:
        TranscriptionResult object
    """
    pipeline = WhisperXPipeline(
        model_name=model,
        device=device,
        language=language,
        hf_token=hf_token,
    )

    result = pipeline.transcribe(
        audio_path,
        enable_alignment=True,
        enable_diarization=enable_diarization,
    )

    return result
