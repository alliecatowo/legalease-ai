"""
Audio Processing Module

Handles audio preprocessing with FFmpeg.
Extracted from app.workers.tasks.transcription for better modularity.
"""
import os
import subprocess
import array
import wave
from typing import Dict, Any, Optional, Tuple
from app.core.logging_config import get_logger

logger = get_logger(__name__)


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

                return {
                    'peaks': peaks,
                    'duration': round(duration, 2),
                    'sample_rate': framerate
                }

        except Exception as e:
            logger.error(f"Failed to extract waveform data: {e}")
            return None

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
