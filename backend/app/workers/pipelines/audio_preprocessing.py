"""
Audio Preprocessing Pipeline

Handles audio file conversion and preprocessing for transcription.
Uses FFmpeg for format conversion and audio normalization.
"""

import os
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AudioMetadata:
    """Metadata about preprocessed audio file."""

    duration: float
    sample_rate: int
    channels: int
    format: str
    file_size: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "duration": self.duration,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "format": self.format,
            "file_size": self.file_size,
        }


class AudioPreprocessor:
    """
    Audio preprocessing pipeline for transcription.

    Converts audio files to the optimal format for WhisperX:
    - 16kHz sample rate
    - Mono channel
    - WAV format (PCM 16-bit)

    Features:
    - Format conversion using FFmpeg
    - Sample rate normalization
    - Channel reduction (stereo -> mono)
    - Optional silence trimming
    - Audio metadata extraction
    """

    def __init__(
        self,
        target_sample_rate: int = 16000,
        target_channels: int = 1,
        trim_silence: bool = False,
        silence_threshold: float = -50.0,  # dB
        output_dir: Optional[str] = None,
    ):
        """
        Initialize audio preprocessor.

        Args:
            target_sample_rate: Target sample rate in Hz (default: 16000)
            target_channels: Number of channels (1=mono, 2=stereo) (default: 1)
            trim_silence: Whether to trim silence from start/end (default: False)
            silence_threshold: Silence detection threshold in dB (default: -50.0)
            output_dir: Directory for output files (default: temp directory)
        """
        self.target_sample_rate = target_sample_rate
        self.target_channels = target_channels
        self.trim_silence = trim_silence
        self.silence_threshold = silence_threshold
        self.output_dir = output_dir or tempfile.gettempdir()

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Check FFmpeg availability
        self._check_ffmpeg()

    def _check_ffmpeg(self) -> None:
        """Check if FFmpeg is installed and accessible."""
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            logger.info("FFmpeg is available")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError(
                "FFmpeg is not installed or not accessible. "
                "Please install FFmpeg: https://ffmpeg.org/download.html"
            ) from e

    def get_audio_metadata(self, file_path: str) -> AudioMetadata:
        """
        Extract metadata from audio file using FFprobe.

        Args:
            file_path: Path to audio file

        Returns:
            AudioMetadata object with file information
        """
        try:
            # Get audio stream information
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_path,
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True,
            )

            import json
            data = json.loads(result.stdout)

            # Find audio stream
            audio_stream = None
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "audio":
                    audio_stream = stream
                    break

            if not audio_stream:
                raise ValueError(f"No audio stream found in {file_path}")

            # Extract metadata
            format_info = data.get("format", {})
            duration = float(format_info.get("duration", 0))
            sample_rate = int(audio_stream.get("sample_rate", 0))
            channels = int(audio_stream.get("channels", 0))
            format_name = format_info.get("format_name", "unknown")
            file_size = int(format_info.get("size", 0))

            return AudioMetadata(
                duration=duration,
                sample_rate=sample_rate,
                channels=channels,
                format=format_name,
                file_size=file_size,
            )

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to extract metadata from {file_path}: {e}")
            raise
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse metadata from {file_path}: {e}")
            raise

    def convert_to_wav(
        self,
        input_file: str,
        output_file: Optional[str] = None,
    ) -> str:
        """
        Convert audio file to WAV format optimized for transcription.

        Args:
            input_file: Path to input audio file (any format supported by FFmpeg)
            output_file: Optional output path (default: auto-generated in output_dir)

        Returns:
            Path to converted WAV file
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")

        # Generate output path if not provided
        if output_file is None:
            input_path = Path(input_file)
            output_file = os.path.join(
                self.output_dir,
                f"{input_path.stem}_preprocessed.wav"
            )

        logger.info(f"Converting {input_file} to {output_file}")

        # Build FFmpeg command
        cmd = [
            "ffmpeg",
            "-i", input_file,
            "-ar", str(self.target_sample_rate),  # Sample rate
            "-ac", str(self.target_channels),     # Channels
            "-c:a", "pcm_s16le",                  # PCM 16-bit codec
        ]

        # Add silence trimming if enabled
        if self.trim_silence:
            # Remove silence from start and end
            filter_complex = (
                f"silenceremove=start_periods=1:start_threshold={self.silence_threshold}dB:"
                f"stop_periods=1:stop_threshold={self.silence_threshold}dB"
            )
            cmd.extend(["-af", filter_complex])

        # Add output file and overwrite flag
        cmd.extend(["-y", output_file])

        try:
            # Run FFmpeg conversion
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True,
            )

            logger.info(f"Successfully converted to {output_file}")
            return output_file

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg conversion failed: {e.stderr}")
            raise RuntimeError(f"Failed to convert {input_file}: {e.stderr}") from e

    def preprocess(
        self,
        input_file: str,
        output_file: Optional[str] = None,
        extract_metadata: bool = True,
    ) -> Dict[str, Any]:
        """
        Preprocess audio file for transcription.

        This is the main entry point that combines conversion and metadata extraction.

        Args:
            input_file: Path to input audio file
            output_file: Optional output path
            extract_metadata: Whether to extract metadata (default: True)

        Returns:
            Dictionary with preprocessed file path and metadata
        """
        # Get original metadata if requested
        original_metadata = None
        if extract_metadata:
            try:
                original_metadata = self.get_audio_metadata(input_file)
                logger.info(f"Original audio: {original_metadata.duration:.2f}s, "
                           f"{original_metadata.sample_rate}Hz, "
                           f"{original_metadata.channels}ch")
            except Exception as e:
                logger.warning(f"Could not extract original metadata: {e}")

        # Convert to WAV
        output_path = self.convert_to_wav(input_file, output_file)

        # Get converted metadata if requested
        converted_metadata = None
        if extract_metadata:
            try:
                converted_metadata = self.get_audio_metadata(output_path)
                logger.info(f"Converted audio: {converted_metadata.duration:.2f}s, "
                           f"{converted_metadata.sample_rate}Hz, "
                           f"{converted_metadata.channels}ch")
            except Exception as e:
                logger.warning(f"Could not extract converted metadata: {e}")

        return {
            "output_path": output_path,
            "original_metadata": original_metadata.to_dict() if original_metadata else None,
            "converted_metadata": converted_metadata.to_dict() if converted_metadata else None,
        }

    def cleanup(self, file_path: str) -> None:
        """
        Remove preprocessed audio file.

        Args:
            file_path: Path to file to remove
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {file_path}: {e}")


# Convenience function for quick preprocessing
def preprocess_audio(
    input_file: str,
    output_file: Optional[str] = None,
    sample_rate: int = 16000,
    mono: bool = True,
    trim_silence: bool = False,
) -> str:
    """
    Quick audio preprocessing function.

    Args:
        input_file: Path to input audio file
        output_file: Optional output path
        sample_rate: Target sample rate (default: 16000)
        mono: Convert to mono (default: True)
        trim_silence: Trim silence from start/end (default: False)

    Returns:
        Path to preprocessed WAV file
    """
    preprocessor = AudioPreprocessor(
        target_sample_rate=sample_rate,
        target_channels=1 if mono else 2,
        trim_silence=trim_silence,
    )

    result = preprocessor.preprocess(input_file, output_file)
    return result["output_path"]
