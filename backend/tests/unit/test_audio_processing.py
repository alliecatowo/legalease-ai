import math
import struct
import wave

import pytest

from app.workers.tasks.transcription import AudioProcessor


def _write_sine_wave(path: str, duration_sec: float = 0.5, amplitude: float = 0.5, frequency: float = 440.0):
    sample_rate = 16000
    sample_count = int(sample_rate * duration_sec)

    with wave.open(path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        frames = []
        for i in range(sample_count):
            sample = amplitude * math.sin(2 * math.pi * frequency * (i / sample_rate))
            frames.append(struct.pack("<h", int(sample * 32767)))

        wav_file.writeframes(b"".join(frames))


def test_extract_waveform_data_includes_metrics(tmp_path):
    wav_path = tmp_path / "tone.wav"
    _write_sine_wave(str(wav_path), duration_sec=1.0, amplitude=0.4)

    result = AudioProcessor.extract_waveform_data(str(wav_path))
    assert result is not None
    metrics = result["metrics"]

    assert 0.2 < metrics["rms"] < 0.5
    assert 0.3 < metrics["peak"] <= 1.0
    assert 0 <= metrics["silence_ratio"] < 0.5
    assert "noise_floor" in metrics


def test_audio_enhancement_applies_filters(tmp_path):
    wav_path = tmp_path / "noisy.wav"
    _write_sine_wave(str(wav_path), duration_sec=0.6, amplitude=0.3, frequency=220.0)

    success, message = AudioProcessor.enhance_audio(str(wav_path))

    if not success and "No such filter" in message:
        pytest.skip("FFmpeg build lacks required filters for enhancement")

    assert success, message
    assert wav_path.exists()

    post = AudioProcessor.extract_waveform_data(str(wav_path))
    assert post is not None
    assert "metrics" in post
