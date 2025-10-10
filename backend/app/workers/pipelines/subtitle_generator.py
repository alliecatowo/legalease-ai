"""
Subtitle Generator Pipeline

Generates subtitles in multiple formats (SRT, VTT, JSON) from transcription segments.
Supports speaker labels, configurable caption length, and proper timestamp formatting.
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path


@dataclass
class TranscriptionSegment:
    """
    Represents a segment of transcribed audio.

    Attributes:
        text: The transcribed text
        start: Start time in seconds
        end: End time in seconds
        speaker: Optional speaker identifier
        confidence: Optional confidence score
    """
    text: str
    start: float
    end: float
    speaker: Optional[str] = None
    confidence: Optional[float] = None

    def duration(self) -> float:
        """Return the duration of the segment in seconds."""
        return self.end - self.start

    def to_dict(self) -> Dict[str, Any]:
        """Convert segment to dictionary."""
        return {
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "speaker": self.speaker,
            "confidence": self.confidence,
        }


class SubtitleGenerator:
    """
    Generator for multiple subtitle formats with speaker labels and configurable settings.

    Supports:
    - SRT (SubRip) format with timestamp format HH:MM:SS,mmm
    - VTT (WebVTT) format with timestamp format HH:MM:SS.mmm
    - JSON format with full metadata
    """

    def __init__(self, chars_per_caption: int = 42):
        """
        Initialize the subtitle generator.

        Args:
            chars_per_caption: Maximum characters per caption line (default: 42)
                              Used for splitting long text into multiple lines
        """
        self.chars_per_caption = chars_per_caption

    def format_timestamp_srt(self, seconds: float) -> str:
        """
        Format timestamp for SRT format: HH:MM:SS,mmm

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    def format_timestamp_vtt(self, seconds: float) -> str:
        """
        Format timestamp for VTT format: HH:MM:SS.mmm

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"

    def wrap_text(self, text: str, max_chars: int = None) -> List[str]:
        """
        Wrap text into multiple lines based on character limit.
        Attempts to break at word boundaries.

        Args:
            text: Text to wrap
            max_chars: Maximum characters per line (uses self.chars_per_caption if None)

        Returns:
            List of text lines
        """
        if max_chars is None:
            max_chars = self.chars_per_caption

        if len(text) <= max_chars:
            return [text]

        lines = []
        words = text.split()
        current_line = ""

        for word in words:
            # If adding this word would exceed the limit
            if current_line and len(current_line) + len(word) + 1 > max_chars:
                lines.append(current_line)
                current_line = word
            else:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word

        if current_line:
            lines.append(current_line)

        return lines

    def prepare_segments(
        self,
        segments: List[Dict[str, Any]]
    ) -> List[TranscriptionSegment]:
        """
        Convert raw segment dictionaries to TranscriptionSegment objects.

        Args:
            segments: List of segment dictionaries with keys:
                     - text: str
                     - start: float (seconds)
                     - end: float (seconds)
                     - speaker: str (optional)
                     - confidence: float (optional)

        Returns:
            List of TranscriptionSegment objects
        """
        result = []
        for seg in segments:
            result.append(TranscriptionSegment(
                text=seg.get("text", ""),
                start=float(seg.get("start", 0)),
                end=float(seg.get("end", 0)),
                speaker=seg.get("speaker"),
                confidence=seg.get("confidence"),
            ))
        return result

    def export_srt(
        self,
        segments: List[Dict[str, Any]],
        output_path: str,
        include_speaker: bool = True
    ) -> str:
        """
        Export segments to SRT (SubRip) format.

        SRT Format:
        1
        00:00:00,000 --> 00:00:05,000
        [Speaker 1] First subtitle text

        2
        00:00:05,000 --> 00:00:10,000
        Second subtitle text

        Args:
            segments: List of transcription segments
            output_path: Path to output SRT file
            include_speaker: Whether to include speaker labels (default: True)

        Returns:
            Path to the generated file
        """
        prepared_segments = self.prepare_segments(segments)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            for idx, segment in enumerate(prepared_segments, start=1):
                # Write sequence number
                f.write(f"{idx}\n")

                # Write timestamp
                start_time = self.format_timestamp_srt(segment.start)
                end_time = self.format_timestamp_srt(segment.end)
                f.write(f"{start_time} --> {end_time}\n")

                # Prepare text with optional speaker label
                text = segment.text.strip()
                if include_speaker and segment.speaker:
                    text = f"[{segment.speaker}] {text}"

                # Write text (with wrapping if needed)
                lines = self.wrap_text(text)
                for line in lines:
                    f.write(f"{line}\n")

                # Blank line separator
                f.write("\n")

        return str(output_path)

    def export_vtt(
        self,
        segments: List[Dict[str, Any]],
        output_path: str,
        include_speaker: bool = True
    ) -> str:
        """
        Export segments to VTT (WebVTT) format.

        VTT Format:
        WEBVTT

        00:00:00.000 --> 00:00:05.000
        <v Speaker 1>First subtitle text</v>

        00:00:05.000 --> 00:00:10.000
        Second subtitle text

        Args:
            segments: List of transcription segments
            output_path: Path to output VTT file
            include_speaker: Whether to include speaker labels (default: True)

        Returns:
            Path to the generated file
        """
        prepared_segments = self.prepare_segments(segments)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            # VTT header
            f.write("WEBVTT\n\n")

            for segment in prepared_segments:
                # Write timestamp
                start_time = self.format_timestamp_vtt(segment.start)
                end_time = self.format_timestamp_vtt(segment.end)
                f.write(f"{start_time} --> {end_time}\n")

                # Prepare text with optional speaker tag
                text = segment.text.strip()
                if include_speaker and segment.speaker:
                    # VTT uses voice tags for speakers
                    text = f"<v {segment.speaker}>{text}</v>"

                # Write text (with wrapping if needed)
                lines = self.wrap_text(text)
                for line in lines:
                    f.write(f"{line}\n")

                # Blank line separator
                f.write("\n")

        return str(output_path)

    def export_json(
        self,
        segments: List[Dict[str, Any]],
        output_path: str,
        pretty: bool = True
    ) -> str:
        """
        Export segments to JSON format with full metadata.

        JSON Format:
        {
          "segments": [
            {
              "index": 0,
              "text": "First subtitle text",
              "start": 0.0,
              "end": 5.0,
              "duration": 5.0,
              "speaker": "Speaker 1",
              "confidence": 0.95
            },
            ...
          ],
          "metadata": {
            "total_segments": 10,
            "total_duration": 120.5,
            "chars_per_caption": 42
          }
        }

        Args:
            segments: List of transcription segments
            output_path: Path to output JSON file
            pretty: Whether to format JSON with indentation (default: True)

        Returns:
            Path to the generated file
        """
        prepared_segments = self.prepare_segments(segments)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build JSON structure
        json_segments = []
        total_duration = 0.0

        for idx, segment in enumerate(prepared_segments):
            json_segments.append({
                "index": idx,
                "text": segment.text.strip(),
                "start": segment.start,
                "end": segment.end,
                "duration": segment.duration(),
                "speaker": segment.speaker,
                "confidence": segment.confidence,
            })
            total_duration = max(total_duration, segment.end)

        output_data = {
            "segments": json_segments,
            "metadata": {
                "total_segments": len(json_segments),
                "total_duration": total_duration,
                "chars_per_caption": self.chars_per_caption,
            }
        }

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            if pretty:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            else:
                json.dump(output_data, f, ensure_ascii=False)

        return str(output_path)

    def export_all(
        self,
        segments: List[Dict[str, Any]],
        base_path: str,
        include_speaker: bool = True,
        formats: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Export segments to multiple formats at once.

        Args:
            segments: List of transcription segments
            base_path: Base path for output files (without extension)
            include_speaker: Whether to include speaker labels
            formats: List of formats to export (default: ["srt", "vtt", "json"])

        Returns:
            Dictionary mapping format to output file path
        """
        if formats is None:
            formats = ["srt", "vtt", "json"]

        results = {}
        base_path = Path(base_path)

        if "srt" in formats:
            srt_path = base_path.with_suffix(".srt")
            results["srt"] = self.export_srt(segments, str(srt_path), include_speaker)

        if "vtt" in formats:
            vtt_path = base_path.with_suffix(".vtt")
            results["vtt"] = self.export_vtt(segments, str(vtt_path), include_speaker)

        if "json" in formats:
            json_path = base_path.with_suffix(".json")
            results["json"] = self.export_json(segments, str(json_path))

        return results


def create_subtitle_generator(chars_per_caption: int = 42) -> SubtitleGenerator:
    """
    Factory function to create a subtitle generator.

    Args:
        chars_per_caption: Maximum characters per caption line

    Returns:
        SubtitleGenerator instance
    """
    return SubtitleGenerator(chars_per_caption=chars_per_caption)
