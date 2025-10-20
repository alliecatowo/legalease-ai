"""
Transcription Tasks

Celery tasks for audio transcription and processing.
Production-ready implementation with WhisperX integration.
"""
import os
import json
import logging
import tempfile
import subprocess
import uuid
import re
import httpx
import warnings
import time
import math
from collections import OrderedDict, defaultdict
from typing import Dict, Any, Optional, List, Tuple, Set
from datetime import datetime, timedelta
from io import BytesIO
from uuid import UUID

# Suppress torchaudio deprecation warnings from pyannote
warnings.filterwarnings("ignore", message=".*torchaudio.*deprecated.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*AudioMetaData.*deprecated.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*pkg_resources.*deprecated.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*torchaudio.load_with_torchcodec.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*TorchCodec.*", category=UserWarning)

from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.minio_client import minio_client
from app.models.transcription import Transcription
from app.models.document import Document, DocumentStatus
from app.workers.pipelines.speaker_identification import SpeakerIdentificationPipeline

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Custom exception for transcription errors."""
    pass


class AudioProcessor:
    """Handles audio preprocessing with FFmpeg."""

    @staticmethod
    def extract_waveform_data(wav_path: str, num_samples: int = 800) -> Optional[Dict[str, Any]]:
        """
        Extract waveform peak data from WAV file for visualization.

        Args:
            wav_path: Path to WAV file
            num_samples: Number of data points to extract (default: 800 for smooth visualization)

        Returns:
            Dict containing peaks array, duration, and sample_rate, or None if failed
        """
        try:
            import wave
            import struct
            import array

            with wave.open(wav_path, 'rb') as wav_file:
                # Get WAV file properties
                num_channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                framerate = wav_file.getframerate()
                num_frames = wav_file.getnframes()
                duration = num_frames / float(framerate)

                # Read all frames
                raw_data = wav_file.readframes(num_frames)

                # Convert bytes to samples based on sample width
                if sample_width == 1:
                    # 8-bit unsigned
                    samples = array.array('B', raw_data)
                    samples = [(s - 128) / 128.0 for s in samples]  # Normalize to -1 to 1
                elif sample_width == 2:
                    # 16-bit signed
                    samples = array.array('h', raw_data)
                    samples = [s / 32768.0 for s in samples]  # Normalize to -1 to 1
                elif sample_width == 4:
                    # 32-bit signed
                    samples = array.array('i', raw_data)
                    samples = [s / 2147483648.0 for s in samples]  # Normalize to -1 to 1
                else:
                    logger.warning(f"Unsupported sample width: {sample_width}")
                    return None

                # If stereo, convert to mono by averaging channels
                if num_channels == 2:
                    samples = [(samples[i] + samples[i+1]) / 2 for i in range(0, len(samples), 2)]

                # Downsample to num_samples peaks for efficient rendering
                samples_per_peak = max(1, len(samples) // num_samples)
                peaks = []

                for i in range(0, len(samples), samples_per_peak):
                    chunk = samples[i:i + samples_per_peak]
                    if chunk:
                        # Get peak (max absolute value) for this chunk
                        peak = max(abs(min(chunk)), abs(max(chunk)))
                        peaks.append(round(peak, 4))  # Round to 4 decimals to reduce size

                # Ensure we have exactly num_samples points
                if len(peaks) > num_samples:
                    peaks = peaks[:num_samples]
                elif len(peaks) < num_samples:
                    # Pad with zeros if needed
                    peaks.extend([0.0] * (num_samples - len(peaks)))

                logger.info(f"Extracted {len(peaks)} waveform peaks from {duration:.1f}s audio")

                metrics = AudioProcessor._compute_audio_metrics(samples)

                return {
                    'peaks': peaks,
                    'duration': round(duration, 2),
                    'sample_rate': framerate,
                    'metrics': metrics
                }

        except Exception as e:
            logger.error(f"Failed to extract waveform data: {e}")
            return None

    @staticmethod
    def _compute_audio_metrics(samples: List[float]) -> Dict[str, float]:
        """Compute signal metrics used for adaptive transcription."""
        if not samples:
            return {
                'rms': 0.0,
                'peak': 0.0,
                'crest_factor': 0.0,
                'silence_ratio': 1.0,
                'noise_floor': -120.0
            }

        abs_samples = [abs(s) for s in samples]
        peak = max(abs_samples)
        rms = math.sqrt(sum(s * s for s in samples) / len(samples))
        crest_factor = peak / rms if rms > 0 else 0.0

        # Estimate silence ratio using adaptive threshold (1% of peak or 0.01 min)
        silence_threshold = max(0.01, peak * 0.05)
        silence_frames = sum(1 for s in abs_samples if s < silence_threshold)
        silence_ratio = silence_frames / len(abs_samples)

        # Estimate noise floor as 10th percentile amplitude
        percentile_index = max(1, int(0.1 * len(abs_samples)))
        sorted_samples = sorted(abs_samples)
        noise_floor_linear = sorted_samples[percentile_index - 1]
        noise_floor_db = 20 * math.log10(noise_floor_linear + 1e-9)

        return {
            'rms': rms,
            'peak': peak,
            'crest_factor': crest_factor,
            'silence_ratio': silence_ratio,
            'noise_floor': noise_floor_db
        }

    @staticmethod
    def enhance_audio(input_path: str) -> Tuple[bool, str]:
        """
        Apply adaptive audio enhancement (normalization + gentle denoise).

        Returns:
            Tuple of (success: bool, message: str)
        """
        temp_fd, enhanced_path = tempfile.mkstemp(suffix=".wav")
        os.close(temp_fd)

        # Loudness normalization and broadband denoise
        # afftdn keeps speech clarity while reducing stationary noise
        filter_chain = (
            "loudnorm=I=-18:TP=-1.5:LRA=11,"
            "highpass=f=60,"
            "lowpass=f=9000,"
            "afftdn=nf=-28"
        )

        cmd = [
            'ffmpeg',
            '-hide_banner',
            '-loglevel', 'error',
            '-i', input_path,
            '-af', filter_chain,
            '-ar', '16000',
            '-ac', '1',
            '-c:a', 'pcm_s16le',
            '-y',
            enhanced_path
        ]

        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
            if result.returncode != 0:
                os.unlink(enhanced_path)
                error_msg = result.stderr.decode('utf-8', errors='ignore')
                return False, f"Audio enhancement failed: {error_msg}"

            # Replace original file atomically
            os.replace(enhanced_path, input_path)
            return True, "Audio enhancement applied"
        except Exception as exc:
            if os.path.exists(enhanced_path):
                os.unlink(enhanced_path)
            return False, f"Audio enhancement error: {exc}"


def _annotation_to_dataframe(annotation) -> Optional["pd.DataFrame"]:
    """Convert a pyannote Annotation object to a pandas DataFrame compatible with whisperx."""
    try:
        import pandas as pd  # type: ignore
    except ImportError:
        logger.warning("pandas is required for advanced diarization alignment but is not available.")
        return None

    rows = []
    for segment, _, speaker in annotation.itertracks(yield_label=True):
        rows.append({
            "start": segment.start,
            "end": segment.end,
            "speaker": speaker,
        })

    return pd.DataFrame(rows, columns=["start", "end", "speaker"])


def _assign_speakers_from_annotation(
    segments: List[Dict[str, Any]],
    annotation,
    coverage_threshold: float = 0.25
) -> List[Dict[str, Any]]:
    """Fallback speaker assignment using overlap between transcript segments and diarization annotation."""
    try:
        from pyannote.core import Segment  # type: ignore
    except ImportError:
        logger.warning("pyannote.core is required for overlap-based speaker assignment.")
        return segments

    assigned = []
    previous_speaker = None

    for segment in segments:
        speech_span = Segment(segment['start'], segment['end'])
        cropped = annotation.crop(speech_span)

        assigned_speaker = None
        coverage_ratio = 0.0

        if cropped and cropped.labels():
            label_durations = {
                label: cropped.label_duration(label)
                for label in cropped.labels()
            }
            assigned_speaker = max(label_durations, key=label_durations.get)
            coverage_ratio = label_durations[assigned_speaker] / max(1e-6, speech_span.duration)
            if not str(assigned_speaker).startswith("SPEAKER_"):
                assigned_speaker = f"SPEAKER_{assigned_speaker}"

        if not assigned_speaker:
            assigned_speaker = previous_speaker or "SPEAKER_00"
        elif coverage_ratio < coverage_threshold and previous_speaker:
            assigned_speaker = previous_speaker

        segment['speaker'] = assigned_speaker
        assigned.append(segment)
        previous_speaker = assigned_speaker

    return assigned


def _merge_minor_speakers(
    segments: List[Dict[str, Any]],
    max_speakers: int = 4,
    min_share: float = 0.02,
    coverage: float = 0.92,
    min_keep: int = 2
) -> List[Dict[str, Any]]:
    """Merge short-lived speakers into dominant speakers to reduce fragmentation."""
    if not segments:
        return segments

    durations: Dict[str, float] = defaultdict(float)
    for seg in segments:
        speaker = seg.get('speaker') or "SPEAKER_00"
        seg['speaker'] = speaker
        durations[speaker] += max(0.0, seg.get('end', 0.0) - seg.get('start', 0.0))

    total_duration = sum(durations.values())
    if total_duration <= 0:
        return segments

    sorted_speakers = sorted(durations.items(), key=lambda item: item[1], reverse=True)

    keep: List[str] = []
    cumulative = 0.0
    target_coverage = max(min(coverage, 0.99), 0.5)
    max_speakers = max(min_keep, max_speakers)

    for speaker, dur in sorted_speakers:
        keep.append(speaker)
        cumulative += dur
        if len(keep) >= max_speakers:
            break
        if cumulative / total_duration >= target_coverage and len(keep) >= min_keep:
            break

    if len(keep) < min_keep and sorted_speakers:
        keep = [speaker for speaker, _ in sorted_speakers[:min_keep]]

    keep_set = set(keep)
    if len(keep_set) == len(durations):
        return segments

    def reassign_segment(idx: int, old: str) -> None:
        prev_speaker = segments[idx - 1].get('speaker') if idx > 0 else None
        next_speaker = segments[idx + 1].get('speaker') if idx + 1 < len(segments) else None
        candidate = None
        if prev_speaker in keep_set and next_speaker in keep_set:
            candidate = prev_speaker if durations[prev_speaker] >= durations[next_speaker] else next_speaker
        elif prev_speaker in keep_set:
            candidate = prev_speaker
        elif next_speaker in keep_set:
            candidate = next_speaker
        else:
            candidate = keep[0]
        segments[idx]['speaker'] = candidate

    for idx, segment in enumerate(segments):
        if segment.get('speaker') not in keep_set:
            reassign_segment(idx, segment.get('speaker'))

    return segments


def _segment_from_words(
    original_segment: "TranscriptionSegment",
    words: List[Dict[str, Any]],
    speaker: Optional[str]
) -> "TranscriptionSegment":
    text = ''.join(word.get('word', '') for word in words).strip()
    start = words[0].get('start', original_segment.start)
    end = words[-1].get('end', original_segment.end)
    confidence_values = [word.get('confidence') for word in words if word.get('confidence') is not None]
    confidence = (
        sum(confidence_values) / len(confidence_values)
        if confidence_values
        else original_segment.confidence
    )

    new_words = []
    for word in words:
        new_word = dict(word)
        new_word.setdefault('speaker', speaker)
        new_words.append(new_word)

    return TranscriptionSegment(
        start=start,
        end=end,
        text=text or original_segment.text,
        speaker=speaker or original_segment.speaker,
        words=new_words,
        avg_logprob=original_segment.avg_logprob,
        no_speech_prob=original_segment.no_speech_prob,
        compression_ratio=original_segment.compression_ratio,
        temperature=original_segment.temperature,
        confidence=confidence,
        refined=original_segment.refined,
    )


def _split_segments_by_speaker(
    segments: List["TranscriptionSegment"]
) -> List["TranscriptionSegment"]:
    """Split segments when word-level speaker labels indicate turn changes."""
    split_segments: List[TranscriptionSegment] = []
    for segment in segments:
        words = segment.words or []
        speakers_in_words = [word.get('speaker') for word in words if word.get('speaker')]
        if not words or len(set(speakers_in_words)) <= 1:
            split_segments.append(segment)
            continue

        current_speaker = None
        buffer: List[Dict[str, Any]] = []

        for word in words:
            speaker = word.get('speaker', current_speaker)
            if current_speaker is None:
                current_speaker = speaker

            if speaker != current_speaker and buffer:
                split_segments.append(_segment_from_words(segment, buffer, current_speaker))
                buffer = []
                current_speaker = speaker

            buffer.append(word)

        if buffer:
            split_segments.append(_segment_from_words(segment, buffer, current_speaker))

    return split_segments


def _segments_to_dicts(segments: List["TranscriptionSegment"]) -> List[Dict[str, Any]]:
    """Convert WhisperX transcription segments into serializable dictionaries with IDs."""
    segment_dicts: List[Dict[str, Any]] = []
    for seg in segments:
        seg_dict = seg.to_dict()
        seg_dict['id'] = seg_dict.get('id') or str(uuid.uuid4())
        segment_dicts.append(seg_dict)
    return segment_dicts


def _refine_low_confidence_segments(
    pipeline: "WhisperXPipeline",
    transcription_result,
    audio_path: str,
    language: Optional[str],
    batch_size: int,
    temperature: float,
    max_segments: int = 6
) -> None:
    """Re-transcribe low-confidence segments with more aggressive decoding settings."""
    if getattr(pipeline, "_whisper_model", None) is None:
        return

    try:
        import whisperx  # type: ignore
    except ImportError:
        logger.warning("WhisperX unavailable for quality refinement.")
        return

    try:
        audio = whisperx.load_audio(audio_path)
    except Exception as exc:
        logger.warning(f"Failed to load audio for refinement: {exc}")
        return

    sample_rate = 16000
    duration = transcription_result.duration or (len(audio) / sample_rate)

    low_confidence_segments = [
        seg for seg in transcription_result.segments
        if (seg.confidence or 1.0) < 0.6 and (seg.end - seg.start) > 0.3
    ]

    if not low_confidence_segments:
        return

    low_confidence_segments.sort(key=lambda s: s.confidence or 0.0)
    segments_to_refine = low_confidence_segments[:max_segments]

    logger.info(f"Refining {len(segments_to_refine)} low-confidence segment(s) with targeted decoding.")

    for segment in segments_to_refine:
        chunk_padding = 0.4
        chunk_start = max(0.0, segment.start - chunk_padding)
        chunk_end = min(duration, segment.end + chunk_padding)

        start_index = int(chunk_start * sample_rate)
        end_index = int(chunk_end * sample_rate)
        chunk_audio = audio[start_index:end_index]

        if len(chunk_audio) < int(0.2 * sample_rate):
            continue

        try:
            refined = pipeline._whisper_model.transcribe(  # type: ignore[union-attr]
                chunk_audio,
                batch_size=max(1, batch_size // 2) if batch_size else 1,
                language=language if language and language != "auto" else None,
                temperature=max(0.0, min(1.0, temperature)),
                beam_size=8,
                best_of=8,
                condition_on_previous_text=False,
                no_speech_threshold=0.3,
                compression_ratio_threshold=2.4,
                log_prob_threshold=-2.0,
                print_progress=False,
            )
        except Exception as decode_error:
            logger.debug(f"Refinement decoding failed for segment at {segment.start:.1f}s: {decode_error}")
            continue

        refined_segments = refined.get("segments", []) if isinstance(refined, dict) else []
        if not refined_segments:
            continue

        # Align refined segments for word-level timings if alignment model is available
        try:
            if getattr(pipeline, "_alignment_model", None) is not None:
                aligned = whisperx.align(
                    refined_segments,
                    pipeline._alignment_model,
                    pipeline._alignment_metadata,
                    chunk_audio,
                    device=pipeline.device,
                    return_char_alignments=False,
                )
                refined_segments = aligned.get("segments", refined_segments)
        except Exception as align_error:
            logger.debug(f"Alignment of refined segment failed: {align_error}")

        combined_text = " ".join(seg.get("text", "").strip() for seg in refined_segments).strip()
        if not combined_text:
            continue

        refined_confidences = [pipeline._estimate_confidence(seg) for seg in refined_segments]
        new_confidence = max(refined_confidences) if refined_confidences else segment.confidence or 0.0

        if new_confidence < (segment.confidence or 0.0) + 0.05 and len(combined_text) <= len(segment.text):
            continue

        segment.text = combined_text
        segment.avg_logprob = sum(seg.get("avg_logprob", -1.0) for seg in refined_segments) / len(refined_segments)
        segment.no_speech_prob = sum(seg.get("no_speech_prob", 0.0) for seg in refined_segments) / len(refined_segments)
        segment.compression_ratio = max(seg.get("compression_ratio", 0.0) for seg in refined_segments)
        segment.confidence = max(min(new_confidence, 1.0), 0.0)
        segment.start = chunk_start + min(seg.get("start", 0.0) for seg in refined_segments)
        segment.end = chunk_start + max(seg.get("end", 0.0) for seg in refined_segments)
        segment.words = []
        for refined_seg in refined_segments:
            for word in refined_seg.get("words", []):
                segment.words.append({
                    **word,
                    "start": word.get("start", 0.0) + chunk_start,
                    "end": word.get("end", 0.0) + chunk_start,
                })
        segment.refined = True

    @staticmethod
    def preprocess_audio(input_path: str, output_path: str) -> Tuple[bool, str]:
        """
        Preprocess audio file to 16kHz mono WAV format for optimal transcription.

        Args:
            input_path: Path to input audio/video file
            output_path: Path to output WAV file

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Calculate dynamic timeout based on file size
            # Allow 5 minutes per GB, minimum 5 minutes, maximum 60 minutes
            file_size_gb = os.path.getsize(input_path) / (1024**3)
            timeout_seconds = max(300, min(3600, int(file_size_gb * 300)))
            logger.info(f"FFmpeg timeout set to {timeout_seconds}s for {file_size_gb:.2f}GB file")

            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-ar', '16000',  # 16kHz sample rate
                '-ac', '1',       # Mono channel
                '-c:a', 'pcm_s16le',  # 16-bit PCM
                '-y',             # Overwrite output file
                output_path
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_seconds  # Dynamic timeout based on file size
            )

            if result.returncode == 0:
                return True, "Audio preprocessing successful"
            else:
                error_msg = result.stderr.decode('utf-8', errors='ignore')
                return False, f"FFmpeg error: {error_msg}"

        except subprocess.TimeoutExpired:
            return False, f"Audio preprocessing timed out after {timeout_seconds}s"
        except Exception as e:
            return False, f"Audio preprocessing failed: {str(e)}"

    @staticmethod
    def get_audio_duration(file_path: str) -> Optional[float]:
        """
        Get audio duration in seconds using FFprobe.

        Args:
            file_path: Path to audio file

        Returns:
            Duration in seconds, or None if failed
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                file_path
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30
            )

            if result.returncode == 0:
                duration_str = result.stdout.decode('utf-8').strip()
                return float(duration_str)
            return None

        except Exception as e:
            logger.warning(f"Failed to get audio duration: {e}")
            return None


class WhisperTranscriber:
    """Handles transcription using OpenAI Whisper API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize transcriber with OpenAI API key."""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise TranscriptionError("OpenAI API key not configured")

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        task: str = "transcribe",
        temperature: float = 0.0,
        initial_prompt: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio file using OpenAI Whisper API.

        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'en', 'es') or None for auto-detect
            task: 'transcribe' for same-language or 'translate' for English translation
            temperature: Sampling temperature (0.0-1.0)
            initial_prompt: Optional context prompt
            task_id: Optional Celery task ID for progress updates

        Returns:
            Dict containing transcription results with segments
        """
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            logger.info(f"Starting Whisper API transcription for {audio_path} (task={task}, language={language})")

            with open(audio_path, 'rb') as audio_file:
                # Build API parameters
                api_params = {
                    "model": "whisper-1",
                    "file": audio_file,
                    "response_format": "verbose_json",
                    "timestamp_granularities": ["segment", "word"],
                    "temperature": temperature,
                }

                # Add optional parameters
                if language and language != "auto":
                    api_params["language"] = language
                if initial_prompt:
                    api_params["prompt"] = initial_prompt

                # Use transcriptions or translations API based on task
                if task == "translate":
                    response = client.audio.translations.create(**api_params)
                else:
                    response = client.audio.transcriptions.create(**api_params)

            # Parse response into segments format
            segments = []
            if hasattr(response, 'segments') and response.segments:
                for idx, segment in enumerate(response.segments):
                    seg_data = {
                        'id': str(uuid.uuid4()),  # Generate UUID for segment
                        'start': segment.get('start', 0.0),
                        'end': segment.get('end', 0.0),
                        'text': segment.get('text', '').strip(),
                        'words': []
                    }

                    # Add word-level timestamps if available
                    if hasattr(segment, 'words') and segment.words:
                        for word in segment.words:
                            seg_data['words'].append({
                                'word': word.get('word', ''),
                                'start': word.get('start', 0.0),
                                'end': word.get('end', 0.0)
                            })

                    segments.append(seg_data)
            else:
                # Fallback: create single segment from text
                segments = [{
                    'id': str(uuid.uuid4()),  # Generate UUID for segment
                    'start': 0.0,
                    'end': 0.0,
                    'text': response.text,
                    'words': []
                }]

            result = {
                'text': response.text,
                'language': response.language if hasattr(response, 'language') else language,
                'duration': response.duration if hasattr(response, 'duration') else None,
                'segments': segments
            }

            logger.info(f"Transcription completed: {len(segments)} segments")
            return result

        except Exception as e:
            logger.error(f"Whisper API transcription failed: {str(e)}")
            raise TranscriptionError(f"Transcription failed: {str(e)}")


class LocalWhisperTranscriber:
    """
    Handles transcription using the open-source Faster-Whisper implementation.

    Provides an on-premise fallback when WhisperX or the OpenAI API are unavailable.
    """

    _model_cache: Dict[Tuple[str, str, str], Any] = {}

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cuda",
        compute_type: str = "float16",
    ):
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError as exc:
            raise TranscriptionError(
                "Faster-Whisper is not installed. Install it with `pip install faster-whisper`."
            ) from exc

        # Ensure compute type is compatible with CPU usage
        if device == "cpu" and compute_type.lower() in {"float16", "bfloat16"}:
            logger.info("Adjusting compute_type to 'int8' for CPU inference")
            compute_type = "int8"

        cache_key = (model_size, device, compute_type)
        if cache_key not in self._model_cache:
            logger.info(
                f"Loading Faster-Whisper model: size={model_size}, device={device}, compute_type={compute_type}"
            )
            self._model_cache[cache_key] = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
            )

        self.model = self._model_cache[cache_key]
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        beam_size: int = 5,
        temperature: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Transcribe audio using Faster-Whisper.

        Args:
            audio_path: Path to WAV audio file
            language: Optional ISO language code, or None/'auto' to let the model decide
            beam_size: Beam search size for decoding
            temperature: Sampling temperature (not heavily used in deterministic decoding)

        Returns:
            Dict containing transcription text, segments, and metadata
        """
        try:
            from faster_whisper import WhisperModel  # type: ignore
            start_time = time.time()

            language_option = None if language in (None, "auto") else language

            segments_iter, info = self.model.transcribe(
                audio_path,
                language=language_option,
                beam_size=beam_size,
                temperature=temperature,
                vad_filter=True,
            )

            segments_list = []
            text_parts: List[str] = []

            for segment in segments_iter:
                segment_text = segment.text.strip()
                text_parts.append(segment_text)
                word_items = []
                if getattr(segment, "words", None):
                    for word in segment.words:
                        word_items.append({
                            "word": word.word,
                            "start": word.start if word.start is not None else segment.start,
                            "end": word.end if word.end is not None else segment.end,
                        })

                segments_list.append({
                    "id": str(uuid.uuid4()),
                    "start": segment.start if segment.start is not None else 0.0,
                    "end": segment.end if segment.end is not None else 0.0,
                    "text": segment_text,
                    "words": word_items,
                })

            elapsed = time.time() - start_time
            full_text = " ".join(text_parts).strip()

            logger.info(
                f"Faster-Whisper transcription completed in {elapsed:.1f}s "
                f"(model={self.model_size}, device={self.device}) with {len(segments_list)} segments"
            )

            return {
                "text": full_text,
                "language": info.language if hasattr(info, "language") else language_option,
                "duration": info.duration if hasattr(info, "duration") else None,
                "segments": segments_list,
            }
        except Exception as exc:
            logger.error(f"Faster-Whisper transcription failed: {exc}")
            raise TranscriptionError(f"Faster-Whisper transcription failed: {exc}") from exc


class SpeakerDiarizer:
    """Handles speaker diarization using simple heuristics."""

    @staticmethod
    def diarize_segments(
        segments: List[Dict[str, Any]],
        pause_threshold: float = 2.0
    ) -> List[Dict[str, Any]]:
        """
        Add speaker labels to segments using simple pause-based heuristics.

        This is a simplified implementation. For production, consider using:
        - Pyannote.audio for deep learning-based diarization
        - AssemblyAI API for cloud-based diarization

        Args:
            segments: List of transcription segments

        Returns:
            List of segments with speaker labels added
        """
        if not segments:
            return segments

        # Simple heuristic: detect speaker changes based on pauses
        current_speaker = 1
        diarized_segments = []

        for idx, segment in enumerate(segments):
            # Check if there's a significant pause before this segment
            if idx > 0:
                prev_end = segments[idx - 1]['end']
                current_start = segment['start']
                pause_duration = current_start - prev_end

                # If pause is significant, assume speaker change
                if pause_duration > pause_threshold:
                    current_speaker += 1

            # Add speaker label
            segment_copy = segment.copy()
            segment_copy['speaker'] = f"SPEAKER_{current_speaker:02d}"
            diarized_segments.append(segment_copy)

        return diarized_segments

    @staticmethod
    def smooth_speaker_changes(
        segments: List[Dict[str, Any]],
        min_segment_duration: float = 0.5,
        min_speaker_gap: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Smooth rapid speaker changes using post-processing.

        Production-quality diarization requires smoothing to reduce false speaker changes
        caused by short pauses, overlapping speech, or diarization errors.

        Strategy:
        1. Merge very short segments (< min_segment_duration) with neighbors
        2. Apply majority voting for rapid speaker changes
        3. Require minimum gap (min_speaker_gap) between speaker changes

        Args:
            segments: List of diarized segments
            min_segment_duration: Minimum segment duration in seconds (default: 0.5s)
            min_speaker_gap: Minimum time between speaker changes in seconds (default: 0.3s)

        Returns:
            List of smoothed segments
        """
        if not segments or len(segments) < 2:
            return segments

        logger.info(f"Smoothing speaker changes (min_duration={min_segment_duration}s, min_gap={min_speaker_gap}s)")

        smoothed = []
        i = 0

        while i < len(segments):
            current = segments[i].copy()
            duration = current['end'] - current['start']

            # If segment is very short, try to merge with neighbor
            if duration < min_segment_duration and i < len(segments) - 1:
                next_seg = segments[i + 1]

                # Merge with next segment if speakers match
                if current.get('speaker') == next_seg.get('speaker'):
                    logger.debug(f"Merging short segment ({duration:.2f}s) at {current['start']:.1f}s with next")
                    # Skip this segment, will be handled by next iteration
                    i += 1
                    continue
                # If speakers don't match, assign to majority speaker based on surrounding context
                elif i > 0:
                    prev_seg = smoothed[-1]
                    # If surrounded by same speaker, reassign
                    if prev_seg.get('speaker') == next_seg.get('speaker'):
                        logger.debug(f"Reassigning isolated short segment ({duration:.2f}s) to majority speaker")
                        current['speaker'] = next_seg.get('speaker')

            # Check for rapid speaker changes (speaker switches back and forth quickly)
            if smoothed and i < len(segments) - 1:
                prev_seg = smoothed[-1]
                next_seg = segments[i + 1]
                time_since_last_change = current['start'] - prev_seg['end']

                # If speaker changed very recently and changes back, smooth it
                if (time_since_last_change < min_speaker_gap and
                    prev_seg.get('speaker') == next_seg.get('speaker') and
                    current.get('speaker') != prev_seg.get('speaker')):

                    logger.debug(
                        f"Smoothing rapid speaker change at {current['start']:.1f}s "
                        f"(gap={time_since_last_change:.2f}s)"
                    )
                    current['speaker'] = prev_seg.get('speaker')

            smoothed.append(current)
            i += 1

        # Log improvement metrics
        original_speaker_changes = sum(
            1 for i in range(1, len(segments))
            if segments[i].get('speaker') != segments[i-1].get('speaker')
        )
        smoothed_speaker_changes = sum(
            1 for i in range(1, len(smoothed))
            if smoothed[i].get('speaker') != smoothed[i-1].get('speaker')
        )

        logger.info(
            f"Speaker smoothing: reduced changes from {original_speaker_changes} to {smoothed_speaker_changes} "
            f"({original_speaker_changes - smoothed_speaker_changes} false changes removed)"
        )

        return smoothed


class SpeakerNameInferencer:
    """
    Handles speaker name inference using spaCy NER and linguistic context analysis.

    Uses SpeakerIdentificationPipeline for evidence-based name extraction from:
    - spaCy NER (PERSON entities with context classification)
    - Pattern matching (conservative fallback)
    - Filename analysis

    Replaces the old LLM-based approach with faster, more reliable linguistic analysis.
    """

    @staticmethod
    async def infer_speaker_names(
        segments: List[Dict[str, Any]],
        speakers: Dict[str, Dict[str, Any]],
        filename: Optional[str] = None,
        ollama_url: str = "http://localhost:11434",
        duration: float = 0.0
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
        """
        Infer speaker names using modular pipeline with spaCy NER and context analysis.

        Uses the new SpeakerIdentificationPipeline which:
        - Analyzes the FULL conversation (not just first N segments)
        - Uses spaCy NER for linguistic understanding (PERSON entities, POS tags)
        - Distinguishes context types (self-ID vs vocative vs mention)
        - Provides evidence-based confidence scores
        - Optionally validates with LLM for extra confidence

        Args:
            segments: List of transcription segments
            speakers: Dictionary of speaker information
            filename: Optional filename to extract names from
            ollama_url: Ollama API URL (for optional LLM validation)
            duration: Total audio duration

        Returns:
            Tuple of (updated_speakers, metadata with inference info)
        """
        logger.info(
            "Starting speaker name inference with new pipeline (segments=%d, speakers=%d)",
            len(segments),
            len(speakers),
        )

        # Use the new modular pipeline
        pipeline = SpeakerIdentificationPipeline(use_spacy=True)
        speaker_ids = list(speakers.keys())

        # Run pipeline to get evidence-based name inferences
        inferred_names = await pipeline.identify_speakers(
            segments=segments,
            speakers=speaker_ids,
            filename=filename,
            duration=duration
        )

        # Apply inferred names if confidence > 0.6 (balanced threshold for spaCy + patterns)
        updated_speakers = speakers.copy()
        metadata = {
            'inference_performed': True,
            'pipeline': 'SpeakerIdentificationPipeline',
            'extractors_used': [extractor.__class__.__name__ for extractor in pipeline.extractors],
            'inferred_names': inferred_names,
            'applied_names': {}
        }

        for speaker_id, inference in inferred_names.items():
            confidence = inference.get('confidence', 0.0)
            inferred_name = inference.get('name', '')
            reasoning = inference.get('reasoning', '')
            evidence_count = inference.get('evidence_count', 0)

            if speaker_id in updated_speakers:
                if confidence > 0.6 and inferred_name:
                    # Apply inferred name
                    old_name = updated_speakers[speaker_id].get('name', speaker_id)
                    updated_speakers[speaker_id]['name'] = inferred_name
                    metadata['applied_names'][speaker_id] = {
                        'old_name': old_name,
                        'new_name': inferred_name,
                        'confidence': confidence,
                        'evidence_count': evidence_count,
                        'reasoning': reasoning
                    }
                    logger.info(
                        f"Applied inferred name for {speaker_id}: '{inferred_name}' "
                        f"(confidence: {confidence:.2f}, evidence: {evidence_count}, reason: {reasoning})"
                    )
                else:
                    logger.info(
                        f"Skipped {speaker_id}: confidence {confidence:.2f} below threshold 0.6 "
                        f"(evidence: {evidence_count})"
                    )

        if metadata['applied_names']:
            logger.info(f"Successfully inferred {len(metadata['applied_names'])} speaker names")
        else:
            logger.info("No speaker names met confidence threshold (0.6), using default names")

        return updated_speakers, metadata


class TranscriptionExporter:
    """Handles exporting transcriptions to various formats."""

    @staticmethod
    def export_to_docx(segments: List[Dict[str, Any]], output_path: str) -> bool:
        """
        Export transcription to DOCX format.

        Args:
            segments: List of transcription segments
            output_path: Path to output DOCX file

        Returns:
            True if successful, False otherwise
        """
        try:
            from docx import Document
            from docx.shared import Pt, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH

            doc = Document()

            # Add title
            title = doc.add_heading('Transcription', 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER

            # Add metadata
            doc.add_paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            doc.add_paragraph("")

            # Group segments by speaker
            current_speaker = None
            current_paragraph = None

            for segment in segments:
                speaker = segment.get('speaker', 'SPEAKER_01')
                start_time = segment.get('start', 0.0)
                text = segment.get('text', '').strip()

                if not text:
                    continue

                # Add speaker header if speaker changed
                if speaker != current_speaker:
                    current_speaker = speaker

                    # Add speaker heading
                    speaker_para = doc.add_paragraph()
                    speaker_run = speaker_para.add_run(f"\n{speaker}")
                    speaker_run.bold = True
                    speaker_run.font.size = Pt(12)
                    speaker_run.font.color.rgb = RGBColor(0, 0, 139)

                # Add timestamped text
                para = doc.add_paragraph()

                # Add timestamp
                timestamp_str = TranscriptionExporter._format_timestamp(start_time)
                time_run = para.add_run(f"[{timestamp_str}] ")
                time_run.font.color.rgb = RGBColor(128, 128, 128)
                time_run.font.size = Pt(9)

                # Add text
                text_run = para.add_run(text)
                text_run.font.size = Pt(11)

            doc.save(output_path)
            logger.info(f"Exported DOCX to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export DOCX: {e}")
            return False

    @staticmethod
    def export_to_srt(segments: List[Dict[str, Any]], output_path: str) -> bool:
        """
        Export transcription to SRT subtitle format.

        Args:
            segments: List of transcription segments
            output_path: Path to output SRT file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for idx, segment in enumerate(segments, start=1):
                    start = segment.get('start', 0.0)
                    end = segment.get('end', 0.0)
                    text = segment.get('text', '').strip()
                    speaker = segment.get('speaker', '')

                    if not text:
                        continue

                    # Format: sequence number
                    f.write(f"{idx}\n")

                    # Format: start --> end
                    start_str = TranscriptionExporter._format_srt_timestamp(start)
                    end_str = TranscriptionExporter._format_srt_timestamp(end)
                    f.write(f"{start_str} --> {end_str}\n")

                    # Format: text (with optional speaker)
                    if speaker:
                        f.write(f"[{speaker}] {text}\n")
                    else:
                        f.write(f"{text}\n")

                    # Blank line between subtitles
                    f.write("\n")

            logger.info(f"Exported SRT to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export SRT: {e}")
            return False

    @staticmethod
    def export_to_vtt(segments: List[Dict[str, Any]], output_path: str) -> bool:
        """
        Export transcription to WebVTT subtitle format.

        Args:
            segments: List of transcription segments
            output_path: Path to output VTT file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                # WebVTT header
                f.write("WEBVTT\n\n")

                for idx, segment in enumerate(segments, start=1):
                    start = segment.get('start', 0.0)
                    end = segment.get('end', 0.0)
                    text = segment.get('text', '').strip()
                    speaker = segment.get('speaker', '')

                    if not text:
                        continue

                    # Format: start --> end
                    start_str = TranscriptionExporter._format_vtt_timestamp(start)
                    end_str = TranscriptionExporter._format_vtt_timestamp(end)
                    f.write(f"{start_str} --> {end_str}\n")

                    # Format: text with speaker as voice tag
                    if speaker:
                        f.write(f"<v {speaker}>{text}</v>\n")
                    else:
                        f.write(f"{text}\n")

                    # Blank line between cues
                    f.write("\n")

            logger.info(f"Exported VTT to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export VTT: {e}")
            return False

    @staticmethod
    def export_to_json(
        segments: List[Dict[str, Any]],
        output_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Export transcription to JSON format.

        Args:
            segments: List of transcription segments
            output_path: Path to output JSON file
            metadata: Optional metadata to include

        Returns:
            True if successful, False otherwise
        """
        try:
            data = {
                'metadata': metadata or {},
                'segments': segments,
                'generated_at': datetime.utcnow().isoformat()
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Exported JSON to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export JSON: {e}")
            return False

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Format seconds to HH:MM:SS."""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        secs = int(td.total_seconds() % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @staticmethod
    def _format_srt_timestamp(seconds: float) -> str:
        """Format seconds to SRT timestamp format (HH:MM:SS,mmm)."""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        secs = int(td.total_seconds() % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def _format_vtt_timestamp(seconds: float) -> str:
        """Format seconds to WebVTT timestamp format (HH:MM:SS.mmm)."""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        secs = int(td.total_seconds() % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


@celery_app.task(name="transcribe_audio", bind=True)
def transcribe_audio(
    self,
    transcription_gid: str,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Transcribe an audio/video file to text with timestamps and speaker diarization.

    Full pipeline:
    1. Download audio/video from MinIO
    2. Preprocess with FFmpeg (convert to 16kHz mono WAV)
    3. Transcribe with OpenAI Whisper API
    4. Diarize speakers (optional, based on options)
    5. Export to DOCX, SRT, VTT, JSON formats
    6. Upload exports to MinIO
    7. Update transcription record in PostgreSQL
    8. Handle errors gracefully with status updates

    Args:
        transcription_gid: GID of the transcription to process
        options: Optional dict containing transcription configuration:
            - language: Language code or None for auto-detect
            - task: 'transcribe' or 'translate'
            - enable_diarization: Enable speaker identification
            - temperature: Sampling temperature
            - initial_prompt: Optional context prompt

    Returns:
        Dict containing transcription status and results
    """
    db = SessionLocal()
    temp_dir = None
    overall_start = time.time()

    # Parse options with defaults
    options = options or {}
    if not isinstance(options, dict):
        # Celery can deserialize into AttributeDict; convert to plain dict
        options = dict(options)

    logger.info(
        "Transcription options resolved for %s: %s",
        transcription_gid,
        json.dumps(options, sort_keys=True),
    )
    language = options.get("language")
    task = options.get("task", "transcribe")
    enable_diarization = options.get("enable_diarization", True)
    temperature = float(options.get("temperature", 0.5))
    initial_prompt = options.get("initial_prompt")
    adaptive_enhancement = options.get("adaptive_enhancement", True)
    quality_boost = options.get("quality_boost", True)

    try:
        # Update task state to STARTED
        self.update_state(
            state='STARTED',
            meta={'status': 'Initializing transcription', 'progress': 0}
        )

        # Step 1: Get transcription from database using GID
        logger.info(f"Starting transcription for transcription GID {transcription_gid}")
        transcription = db.query(Transcription).filter(Transcription.gid == transcription_gid).first()

        if not transcription:
            raise TranscriptionError(f"Transcription with GID {transcription_gid} not found")

        # Update transcription status
        transcription.status = DocumentStatus.PROCESSING
        db.commit()

        # Step 2: Download audio/video from MinIO (STREAMING - memory efficient)
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Downloading audio from storage', 'progress': 10}
        )

        # Create temporary directory for processing
        temp_dir = tempfile.mkdtemp(prefix='transcription_')
        logger.info(f"Created temporary directory: {temp_dir}")

        # Get file extension
        _, ext = os.path.splitext(transcription.filename)
        original_file = os.path.join(temp_dir, f"original{ext}")
        processed_wav = os.path.join(temp_dir, "audio.wav")

        # Stream file directly to disk (no memory loading)
        logger.info(f"Streaming file from MinIO: {transcription.file_path} -> {original_file}")
        try:
            minio_client.download_file_to_path(transcription.file_path, original_file)
        except Exception as e:
            logger.error(f"Failed to stream file from MinIO: {e}")
            raise TranscriptionError(f"Failed to download file from MinIO: {e}")

        logger.info(f"File streamed successfully to {original_file}")

        # Step 3: Preprocess audio with FFmpeg
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Preprocessing audio', 'progress': 20}
        )

        logger.info("Preprocessing audio with FFmpeg")
        processor = AudioProcessor()
        success, message = processor.preprocess_audio(original_file, processed_wav)

        if not success:
            raise TranscriptionError(f"Audio preprocessing failed: {message}")

        # Get audio duration
        duration = processor.get_audio_duration(processed_wav)
        logger.info(f"Audio duration: {duration} seconds")

        # Step 3.5: Extract waveform data for visualization
        logger.info("Extracting waveform data for instant visualization")
        waveform_data = processor.extract_waveform_data(processed_wav)
        audio_metrics = None

        if waveform_data:
            logger.info(f"Successfully extracted waveform with {len(waveform_data['peaks'])} peaks")
            audio_metrics = waveform_data.get('metrics')
            if audio_metrics:
                logger.info(
                    "Audio metrics: rms=%.4f peak=%.4f crest=%.2f silence=%.1f%% noise_floor=%.1f dBFS",
                    audio_metrics['rms'],
                    audio_metrics['peak'],
                    audio_metrics['crest_factor'],
                    audio_metrics['silence_ratio'] * 100,
                    audio_metrics['noise_floor'],
                )
        else:
            logger.warning("Failed to extract waveform data, will fallback to client-side generation")

        # Step 3.6: Enhance audio (normalization + denoise) before transcription
        if adaptive_enhancement:
            logger.info("Enhancing audio prior to transcription")
            enhancement_success, enhancement_message = processor.enhance_audio(processed_wav)
            if enhancement_success:
                logger.info(enhancement_message)
                # Recompute waveform + metrics after enhancement for accurate adaptation
                waveform_data = processor.extract_waveform_data(processed_wav) or waveform_data
                if waveform_data:
                    audio_metrics = waveform_data.get('metrics')
                    if audio_metrics:
                        logger.info(
                            "Post-enhancement metrics: rms=%.4f peak=%.4f crest=%.2f silence=%.1f%% noise_floor=%.1f dBFS",
                            audio_metrics['rms'],
                            audio_metrics['peak'],
                            audio_metrics['crest_factor'],
                            audio_metrics['silence_ratio'] * 100,
                            audio_metrics['noise_floor'],
                        )
            else:
                logger.warning(enhancement_message)
        else:
            logger.info("Adaptive audio enhancement disabled; proceeding with preprocessed audio")

        # Step 4: Transcribe with Whisper
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Transcribing audio', 'progress': 30}
        )

        # Use self-hosted transcription with Pyannote diarization (NO HuggingFace token needed)
        logger.info(f"Starting self-hosted transcription (language={language or 'auto'}, diarization={enable_diarization})")

        whisper_result = None
        segment_dicts: List[Dict[str, Any]] = []

        try:
            import torch
            from app.services.model_manager import get_pyannote_model_paths
            from app.services.device_manager import get_device_manager, get_device, get_compute_type
            from app.services.model_selector import ModelSelector
            from app.core.config import settings

            # Get device and compute type (supports both CUDA and ROCm)
            device_manager = get_device_manager()
            device = get_device()
            compute_type = get_compute_type(prefer_fp16=True)

            # Get VRAM and calculate optimal settings
            vram_gb = device_manager._vram_gb or 0
            if vram_gb == 0:
                # Fallback for CPU or unknown device
                logger.warning("Unable to detect VRAM, using conservative defaults")
                vram_gb = 4.0  # Assume 4GB for conservative defaults

            # Calculate optimal settings based on VRAM
            optimal_settings = ModelSelector.calculate_optimal_settings(
                vram_gb=vram_gb,
                user_model=settings.WHISPER_MODEL,
                enable_diarization=options.get("enable_diarization", settings.ENABLE_DIARIZATION),
            )

            # Extract settings
            whisper_model = optimal_settings["model"]
            batch_size = optimal_settings["batch_size"]
            enable_diarization = optimal_settings["enable_diarization"]

            logger.info(f"Using device: {device} with compute type: {compute_type}")
            logger.info(
                f"Adaptive settings: model={whisper_model}, batch_size={batch_size}, "
                f"diarization={enable_diarization}, VRAM={vram_gb:.1f}GB"
            )
            logger.info(f"Reason: {optimal_settings['reason']}")

            # Check if HF token is available for Pyannote diarization
            # (enable_diarization may have been adjusted by ModelSelector)
            hf_token = os.getenv("HF_TOKEN")
            pyannote_available = hf_token is not None and enable_diarization

            if not enable_diarization:
                logger.info("Speaker diarization disabled by adaptive model selector")
            elif pyannote_available:
                logger.info("HuggingFace token available - will use Pyannote for speaker diarization")
            else:
                logger.warning("No HF_TOKEN found - will use simple heuristic diarization")

            # Try WhisperX for transcription + alignment (faster, more accurate)
            try:
                from app.workers.pipelines.whisperx_pipeline import WhisperXPipeline

                min_speakers = options.get("min_speakers", settings.DIARIZATION_MIN_SPEAKERS)
                max_speakers = options.get("max_speakers", settings.DIARIZATION_MAX_SPEAKERS)

                # Initialize WhisperX with adaptively selected model
                # Adaptive ASR/VAD configuration based on measured audio metrics
                asr_options = {
                    "condition_on_previous_text": True,
                    "beam_size": 5,
                    "best_of": 5,
                    "compression_ratio_threshold": 2.3,
                    "log_prob_threshold": -1.2,
                    "hallucination_silence_threshold": 0.5,
                }
                vad_options: Dict[str, Any] = {}
                pause_threshold = 2.0
                min_segment_duration = 0.5
                min_speaker_gap = 0.3

                user_temperature = max(0.0, min(1.0, float(temperature)))
                temp_set = {0.0, 0.2, 0.4, 0.6, round(user_temperature, 2)}

                if audio_metrics:
                    rms = audio_metrics.get('rms', 0.0)
                    silence_ratio = audio_metrics.get('silence_ratio', 0.0)
                    crest_factor = audio_metrics.get('crest_factor', 0.0)
                    noise_floor = audio_metrics.get('noise_floor', -120.0)

                    if rms < 0.02:
                        vad_options.update({"vad_onset": 0.35, "vad_offset": 0.25})
                        asr_options["no_speech_threshold"] = 0.45
                        temp_set.update({0.0, 0.2, 0.4})
                        asr_options["beam_size"] = max(asr_options["beam_size"], 6)
                        asr_options["best_of"] = max(asr_options["best_of"], 6)
                        pause_threshold = 1.5
                        min_segment_duration = 0.45
                        min_speaker_gap = 0.25
                    elif rms > 0.12:
                        vad_options.update({"vad_onset": 0.6, "vad_offset": 0.5})
                        asr_options["no_speech_threshold"] = 0.7
                        temp_set.update({0.0, 0.2, 0.4, 0.6, 0.8})
                        pause_threshold = 2.4
                        min_segment_duration = 0.6
                        min_speaker_gap = 0.4
                    else:
                        vad_options.update({"vad_onset": 0.5, "vad_offset": 0.36})
                        asr_options["no_speech_threshold"] = 0.6

                    if silence_ratio > 0.65:
                        vad_options["vad_offset"] = min(vad_options.get("vad_offset", 0.36), 0.3)
                        pause_threshold = max(pause_threshold, 2.5)
                        min_segment_duration = max(0.45, min_segment_duration)
                    elif silence_ratio < 0.2:
                        vad_options["vad_onset"] = max(vad_options.get("vad_onset", 0.5), 0.55)
                        pause_threshold = min(pause_threshold, 1.4)
                        min_speaker_gap = max(0.2, min_speaker_gap * 0.8)

                    if crest_factor > 12:
                        asr_options["beam_size"] = max(asr_options["beam_size"], 6)
                        asr_options["best_of"] = max(asr_options["best_of"], 6)

                    if noise_floor > -25:
                        asr_options["log_prob_threshold"] = -1.5
                        asr_options["compression_ratio_threshold"] = 2.1
                        temp_set.update({0.0, 0.2, 0.4})

                asr_options.setdefault("no_speech_threshold", 0.6)
                asr_options["temperatures"] = sorted({round(t, 2) for t in temp_set})

                logger.info("Adaptive ASR options: %s", asr_options)
                if vad_options:
                    logger.info("Adaptive VAD options: %s", vad_options)
                else:
                    logger.info("Using default VAD options")

                pipeline = WhisperXPipeline(
                    model_name=whisper_model,  # Adaptive model selection
                    device=device,
                    compute_type=compute_type,
                    language=language if language and language != "auto" else None,
                    hf_token=None,  # No HF token needed for transcription
                    asr_options=asr_options,
                    vad_options=vad_options or None
                )

                # Transcribe with alignment only (no diarization yet)
                whisperx_start = time.time()
                whisper_result = pipeline.transcribe(
                    audio_path=processed_wav,
                    enable_alignment=True,
                    enable_diarization=False,  # We'll do this separately with Pyannote
                    batch_size=batch_size  # Adaptive batch size
                )
                whisperx_time = time.time() - whisperx_start

                detected_language = whisper_result.language
                full_text = whisper_result.get_full_text()

                if quality_boost:
                    _refine_low_confidence_segments(
                        pipeline,
                        whisper_result,
                        processed_wav,
                        detected_language,
                        batch_size,
                        user_temperature,
                    )

                whisper_result.segments = _split_segments_by_speaker(whisper_result.segments)
                segment_dicts = _segments_to_dicts(whisper_result.segments)

                logger.info(f"WhisperX transcription completed in {whisperx_time:.1f}s: {len(segment_dicts)} segments, language={detected_language}")
                logger.info(f"Performance: {duration/whisperx_time:.2f}x realtime (processed {duration:.0f}s audio in {whisperx_time:.1f}s)")

                # Cleanup WhisperX models from memory
                pipeline.cleanup()
            except ImportError:
                logger.info("WhisperX not available, attempting Faster-Whisper fallback")

                try:
                    local_transcriber = LocalWhisperTranscriber(
                        model_size=whisper_model,
                        device=device,
                        compute_type=compute_type,
                    )
                    local_start = time.time()
                    transcription_result = local_transcriber.transcribe(
                        processed_wav,
                        language=language,
                        beam_size=options.get("beam_size", 5),
                        temperature=temperature,
                    )
                    local_time = time.time() - local_start

                    segment_dicts = transcription_result['segments']
                    full_text = transcription_result['text']
                    detected_language = transcription_result.get('language', language)

                    logger.info(
                        f"Faster-Whisper transcription completed in {local_time:.1f}s "
                        f"({len(segment_dicts)} segments, language={detected_language})"
                    )
                except TranscriptionError as local_error:
                    logger.warning(f"Faster-Whisper unavailable: {local_error}")

                    if os.getenv("OPENAI_API_KEY"):
                        logger.info("Falling back to OpenAI Whisper API")
                        transcriber = WhisperTranscriber()
                        transcription_result = transcriber.transcribe(
                            processed_wav,
                            language=language,
                            task=task,
                            temperature=temperature,
                            initial_prompt=initial_prompt,
                            task_id=self.request.id
                        )

                        segment_dicts = transcription_result['segments']
                        full_text = transcription_result['text']
                        detected_language = transcription_result.get('language', language)

                        logger.info(f"OpenAI Whisper transcription completed: {len(segment_dicts)} segments")
                    else:
                        raise TranscriptionError(
                            "No transcription backend available. Install WhisperX or Faster-Whisper, "
                            "or configure OPENAI_API_KEY for the OpenAI Whisper API."
                        ) from local_error

            # Step 5: Speaker diarization (if enabled)
            if enable_diarization:
                self.update_state(
                    state='PROCESSING',
                    meta={'status': 'Identifying speakers', 'progress': 60}
                )

                # Try Pyannote if HF token available, otherwise use simple diarization
                if pyannote_available:
                    try:
                        # Use Pyannote.audio directly with HuggingFace models
                        from pyannote.audio import Pipeline

                        logger.info("Running Pyannote speaker diarization...")
                        diarization_start = time.time()

                        # Check if exact speaker count is provided
                        num_speakers = options.get("num_speakers")
                        min_speakers = options.get("min_speakers", settings.DIARIZATION_MIN_SPEAKERS)
                        max_speakers = options.get("max_speakers", settings.DIARIZATION_MAX_SPEAKERS)

                        # Load diarization pipeline from HuggingFace
                        logger.info("Loading speaker-diarization-3.1 from HuggingFace...")
                        diarization_pipeline = Pipeline.from_pretrained(
                            "pyannote/speaker-diarization-3.1",
                            use_auth_token=hf_token
                        )
                        logger.info("Pyannote pipeline loaded successfully")

                        # Move to GPU if available
                        if device == "cuda":
                            diarization_pipeline.to(torch.device("cuda"))

                        # Run diarization with exact speaker count or range
                        if num_speakers is not None:
                            logger.info(f"Using exact speaker count: {num_speakers}")
                            diarization = diarization_pipeline(
                                processed_wav,
                                num_speakers=num_speakers
                            )
                        else:
                            logger.info(f"Using auto-detection with speaker range: {min_speakers}-{max_speakers}")
                            diarization = diarization_pipeline(
                                processed_wav,
                                min_speakers=min_speakers,
                                max_speakers=max_speakers
                            )

                        diarization_time = time.time() - diarization_start

                        try:
                            import whisperx  # type: ignore
                            diarize_df = _annotation_to_dataframe(diarization)
                            if diarize_df is not None and whisper_result is not None:
                                try:
                                    aligned_result = whisperx.assign_word_speakers(diarize_df, whisper_result)
                                    if aligned_result:
                                        whisper_result = aligned_result
                                        segment_dicts = _segments_to_dicts(whisper_result.segments)
                                except Exception as assign_error:
                                    logger.warning(
                                        "Word-level speaker assignment failed (%s). Falling back to overlap heuristic.",
                                        assign_error
                                    )
                                    segment_dicts = _assign_speakers_from_annotation(segment_dicts, diarization)
                            else:
                                segment_dicts = _assign_speakers_from_annotation(segment_dicts, diarization)
                        except Exception as assign_error:
                            logger.warning(
                                "Advanced diarization alignment unavailable (%s); using overlap heuristic.",
                                assign_error
                            )
                            segment_dicts = _assign_speakers_from_annotation(segment_dicts, diarization)

                        diarizer = SpeakerDiarizer()
                        diarized_segments = diarizer.smooth_speaker_changes(
                            segment_dicts,
                            min_segment_duration=min_segment_duration,
                            min_speaker_gap=min_speaker_gap
                        )
                        segment_dicts = _merge_minor_speakers(
                            diarized_segments,
                            max_speakers=min(max_speakers or 4, 6)
                        )
                        num_detected_speakers = len({s.get('speaker') for s in diarized_segments})
                        logger.info(f"Diarization completed in {diarization_time:.1f}s: {num_detected_speakers} speakers detected")
                        logger.info(f"Diarization performance: {duration/diarization_time:.2f}x realtime")

                        # Cleanup Pyannote pipeline to free GPU memory for speaker name inference
                        del diarization_pipeline
                        import gc
                        gc.collect()
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                            logger.info("Cleared CUDA cache after Pyannote diarization")

                    except Exception as e:
                        logger.error(f"Pyannote diarization failed: {e}", exc_info=True)
                        logger.warning("Falling back to simple heuristic diarization")

                        diarizer = SpeakerDiarizer()
                        diarized_segments = diarizer.diarize_segments(
                            segment_dicts,
                            pause_threshold=pause_threshold
                        )
                        diarized_segments = diarizer.smooth_speaker_changes(
                            diarized_segments,
                            min_segment_duration=min_segment_duration,
                            min_speaker_gap=min_speaker_gap
                        )
                        segment_dicts = _merge_minor_speakers(
                            diarized_segments,
                            max_speakers=min(max_speakers or 4, 6)
                        )
                else:
                    # Pyannote not available, use simple heuristic diarization
                    logger.info("Using simple heuristic diarization (no HF token or diarization disabled)")
                    diarizer = SpeakerDiarizer()
                    diarized_segments = diarizer.diarize_segments(
                        segment_dicts,
                        pause_threshold=pause_threshold
                    )
                    diarized_segments = diarizer.smooth_speaker_changes(
                        diarized_segments,
                        min_segment_duration=min_segment_duration,
                        min_speaker_gap=min_speaker_gap
                    )
                    segment_dicts = _merge_minor_speakers(
                        diarized_segments,
                        max_speakers=min(max_speakers or 4, 6)
                    )
            else:
                logger.info("Speaker diarization disabled")
                segment_dicts = segment_dicts

            diarized_segments = segment_dicts

            if duration is None:
                if whisper_result is not None and whisper_result.duration:
                    duration = whisper_result.duration
                elif diarized_segments:
                    duration = max(segment.get('end', 0.0) for segment in diarized_segments)
                else:
                    duration = 0.0

            # Renumber speakers by descending total duration for consistency
            speaker_duration: Dict[str, float] = defaultdict(float)
            for seg in diarized_segments:
                speaker = seg.get('speaker') or "SPEAKER_00"
                span = max(0.0, seg.get('end', 0.0) - seg.get('start', 0.0))
                speaker_duration[speaker] += span

            ordered_speakers = [speaker for speaker, _ in sorted(speaker_duration.items(), key=lambda item: item[1], reverse=True)]
            speaker_map = {speaker: f"SPEAKER_{idx:02d}" for idx, speaker in enumerate(ordered_speakers)}

            for seg in diarized_segments:
                original = seg.get('speaker') or "SPEAKER_00"
                seg['speaker'] = speaker_map.get(original, original)

        except Exception as e:
            logger.error(f"Self-hosted transcription failed: {e}", exc_info=True)
            raise TranscriptionError(f"Transcription failed: {str(e)}")

        # Extract speaker information and generate speaker colors
        def generate_speaker_color(index: int) -> str:
            """Generate a distinct color for each speaker."""
            colors = [
                "#3B82F6",  # Blue
                "#EF4444",  # Red
                "#10B981",  # Green
                "#F59E0B",  # Amber
                "#8B5CF6",  # Purple
                "#EC4899",  # Pink
                "#14B8A6",  # Teal
                "#F97316",  # Orange
                "#6366F1",  # Indigo
                "#84CC16",  # Lime
            ]
            return colors[index % len(colors)]

        speaker_counts: "OrderedDict[str, int]" = OrderedDict()
        for segment in diarized_segments:
            speaker_id = segment.get('speaker') or 'SPEAKER_01'
            segment['speaker'] = speaker_id
            speaker_counts[speaker_id] = speaker_counts.get(speaker_id, 0) + 1

        speakers: Dict[str, Dict[str, Any]] = {}
        for speaker_index, (speaker_id, segment_count) in enumerate(speaker_counts.items()):
            speaker_name = f"Speaker {speaker_index + 1}"
            speakers[speaker_id] = {
                'id': speaker_id,
                'name': speaker_name,
                'color': generate_speaker_color(speaker_index),
                'segments_count': segment_count
            }

        # Step 5.5: AI-powered speaker name inference (if enabled)
        inference_metadata = None
        enable_name_inference = options.get("enable_name_inference", settings.ENABLE_SPEAKER_NAME_INFERENCE)

        logger.info(
            "Speaker inference gate for %s -> enabled=%s, detected_speakers=%d",
            transcription_gid,
            enable_name_inference,
            len(speakers),
        )

        if enable_name_inference and len(speakers) > 0:
            try:
                self.update_state(
                    state='PROCESSING',
                    meta={'status': 'Inferring speaker names with AI', 'progress': 65}
                )

                # Get Ollama URL from environment
                ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

                # Run async inference in sync context using asyncio
                import asyncio

                # Create event loop if needed
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                # Perform inference
                logger.info("Starting AI-powered speaker name inference with new pipeline...")
                inference_start = time.time()
                inferencer = SpeakerNameInferencer()
                speakers, inference_metadata = loop.run_until_complete(
                    inferencer.infer_speaker_names(
                        segments=diarized_segments,
                        speakers=speakers,
                        filename=transcription.filename,
                        ollama_url=ollama_url,
                        duration=duration
                    )
                )
                inference_time = time.time() - inference_start

                logger.info(f"Speaker name inference completed in {inference_time:.1f}s")
                logger.info(f"Inference metadata: {inference_metadata}")

            except Exception as e:
                logger.warning(f"Speaker name inference failed, using default names: {e}")
                inference_metadata = {
                    'inference_performed': True,
                    'error': str(e),
                    'applied_names': {}
                }
        else:
            logger.info(
                "Skipping speaker name inference for %s (enabled=%s, speakers=%d)",
                transcription_gid,
                enable_name_inference,
                len(speakers),
            )

        # Step 6: Export to multiple formats
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Exporting transcription', 'progress': 70}
        )

        logger.info("Exporting transcription to multiple formats")
        exporter = TranscriptionExporter()

        # Prepare metadata (include inference metadata if available)
        metadata = {
            'transcription_gid': transcription.gid,
            'filename': transcription.filename,
            'language': language,
            'duration': duration,
            'segments_count': len(diarized_segments),
            'speakers_count': len(speakers)
        }

        # Add inference metadata if name inference was performed
        if inference_metadata:
            metadata['speaker_name_inference'] = inference_metadata

        # Export paths
        docx_path = os.path.join(temp_dir, "transcription.docx")
        srt_path = os.path.join(temp_dir, "transcription.srt")
        vtt_path = os.path.join(temp_dir, "transcription.vtt")
        json_path = os.path.join(temp_dir, "transcription.json")

        # Export to all formats
        exporter.export_to_docx(diarized_segments, docx_path)
        exporter.export_to_srt(diarized_segments, srt_path)
        exporter.export_to_vtt(diarized_segments, vtt_path)
        exporter.export_to_json(diarized_segments, json_path, metadata)

        # Step 7: Upload exports to MinIO
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Uploading results', 'progress': 85}
        )

        logger.info("Uploading exports to MinIO")

        # Generate MinIO paths
        base_path = os.path.splitext(transcription.file_path)[0]
        export_paths = {}

        for format_name, local_path in [
            ('docx', docx_path),
            ('srt', srt_path),
            ('vtt', vtt_path),
            ('json', json_path)
        ]:
            if os.path.exists(local_path):
                minio_path = f"{base_path}.{format_name}"

                with open(local_path, 'rb') as f:
                    file_data = f.read()
                    content_type = {
                        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        'srt': 'text/plain',
                        'vtt': 'text/vtt',
                        'json': 'application/json'
                    }.get(format_name, 'application/octet-stream')

                    minio_client.upload_file(
                        file_data=BytesIO(file_data),
                        object_name=minio_path,
                        content_type=content_type,
                        length=len(file_data)
                    )

                export_paths[format_name] = minio_path
                logger.info(f"Uploaded {format_name.upper()} to {minio_path}")

        # Step 8: Update transcription record in database
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Saving transcription', 'progress': 95}
        )

        logger.info("Updating database with transcription results")

        # Update transcription record with results (transcription already fetched at start)

        # Update transcription fields
        transcription.format = ext.lstrip('.') if ext else None
        transcription.duration = duration
        transcription.speakers = list(speakers.values())
        transcription.segments = diarized_segments
        transcription.waveform_data = waveform_data  # Save pre-computed waveform
        transcription.status = DocumentStatus.COMPLETED

        db.commit()

        # Calculate total processing time
        total_time = time.time() - overall_start

        logger.info(f"Transcription completed successfully for transcription GID {transcription_gid} (UUID: {transcription.id})")
        logger.info("=" * 80)
        logger.info("PERFORMANCE SUMMARY:")
        logger.info(f"  Total pipeline time: {total_time:.1f}s")
        logger.info(f"  Audio duration: {duration:.1f}s ({duration/60:.1f} minutes)")
        if 'whisperx_time' in locals():
            logger.info(f"  WhisperX time: {whisperx_time:.1f}s ({duration/whisperx_time:.2f}x realtime)")
        if 'diarization_time' in locals():
            logger.info(f"  Diarization time: {diarization_time:.1f}s ({duration/diarization_time:.2f}x realtime)")
        if 'inference_time' in locals():
            logger.info(f"  Speaker inference time: {inference_time:.1f}s")
        logger.info("=" * 80)

        # Step 9: Queue transcript indexing for search
        try:
            from app.workers.tasks.transcript_indexing import index_transcript
            logger.info(f"Queueing transcript indexing for transcription {transcription.gid}")
            index_transcript.delay(transcription.gid)
        except Exception as e:
            logger.warning(f"Failed to queue transcript indexing: {e}")
            # Don't fail the whole transcription if indexing fails to queue

        # Step 10: Return success result
        return {
            'status': 'completed',
            'transcription_gid': transcription.gid,
            'filename': transcription.filename,
            'duration': duration,
            'segments_count': len(diarized_segments),
            'speakers_count': len(speakers),
            'speakers': list(speakers.values()),
            'export_paths': export_paths,
            'language': language,
            'task_id': self.request.id
        }

    except Exception as e:
        logger.error(f"Transcription failed for transcription GID {transcription_gid}: {str(e)}", exc_info=True)

        # Update transcription status to FAILED
        try:
            transcription = db.query(Transcription).filter(Transcription.gid == transcription_gid).first()
            if transcription:
                transcription.status = DocumentStatus.FAILED
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update transcription status: {str(db_error)}")

        # Update task state
        self.update_state(
            state='FAILURE',
            meta={'status': f'Transcription failed: {str(e)}', 'error': str(e)}
        )

        return {
            'status': 'failed',
            'error': str(e),
            'transcription_gid': transcription_gid,
            'task_id': self.request.id
        }

    finally:
        # Cleanup temporary files
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp directory: {cleanup_error}")

        db.close()


@celery_app.task(name="process_transcription", bind=True)
def process_transcription(
    self,
    transcription_id: UUID,
    case_id: UUID,
    extract_entities: bool = True
) -> Dict[str, Any]:
    """
    Process a completed transcription for analysis and entity extraction.

    This is a placeholder task that will be fully implemented in Phase 3.
    It will handle post-transcription processing and NLP tasks.

    Args:
        transcription_id: UUID of the transcription
        case_id: UUID of the case
        extract_entities: Whether to extract named entities (default: True)

    Returns:
        Dict containing processing status and analysis results
    """
    # Placeholder - will implement in Phase 3
    # Future implementation will:
    # 1. Fetch transcription from database
    # 2. Run NLP entity extraction
    # 3. Extract legal terms and entities
    # 4. Create searchable chunks
    # 5. Index in Qdrant for semantic search
    # 6. Update database with entities

    return {
        "status": "pending",
        "transcription_id": str(transcription_id),
        "case_id": str(case_id),
        "extract_entities": extract_entities,
        "task_id": self.request.id,
    }
