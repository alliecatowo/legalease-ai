"""
Transcript entity for the Evidence domain.

Represents transcribed audio/video recordings with timing information,
speaker identification, and segmentation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID


class TranscriptStatus(str, Enum):
    """Transcript processing status."""

    PENDING = "PENDING"
    TRANSCRIBING = "TRANSCRIBING"
    DIARIZING = "DIARIZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SegmentType(str, Enum):
    """Type of transcript segment."""

    SPEECH = "SPEECH"
    SILENCE = "SILENCE"
    MUSIC = "MUSIC"
    NOISE = "NOISE"


@dataclass(frozen=True)
class Speaker:
    """
    Immutable speaker information.

    Attributes:
        id: Speaker identifier (e.g., 'SPEAKER_00', 'John Doe')
        name: Human-readable speaker name
        confidence: Confidence score for speaker identification (0.0-1.0)
        metadata: Additional speaker metadata
    """

    id: str
    name: Optional[str] = None
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TranscriptSegment:
    """
    Immutable transcript segment with timing and speaker information.

    Attributes:
        id: Unique segment identifier
        start: Start time in seconds
        end: End time in seconds
        text: Transcribed text for this segment
        speaker: Speaker who spoke this segment
        confidence: Transcription confidence score (0.0-1.0)
        segment_type: Type of segment (speech, silence, etc.)
        words: Optional word-level timing information
    """

    id: str
    start: float
    end: float
    text: str
    speaker: Optional[Speaker] = None
    confidence: Optional[float] = None
    segment_type: SegmentType = SegmentType.SPEECH
    words: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def duration(self) -> float:
        """Calculate segment duration in seconds."""
        return self.end - self.start


@dataclass
class Transcript:
    """
    Transcript entity representing audio/video transcription results.

    This entity contains timing information, speaker identification,
    and segmented text from audio/video processing.

    Attributes:
        id: Unique identifier for the transcript
        case_id: ID of the case this transcript belongs to
        filename: Original filename of the audio/video file
        duration: Total duration in seconds
        language: Detected or specified language code (e.g., 'en', 'es')
        speakers: List of identified speakers
        segments: Ordered list of transcript segments
        status: Current processing status
        created_at: When transcription started
        updated_at: When transcript was last modified
        file_path: Storage path or object key for source media
        mime_type: MIME type of source file
        size: File size in bytes
        metadata: Additional metadata (e.g., model version, parameters)

    Example:
        >>> transcript = Transcript(
        ...     id=UUID('...'),
        ...     case_id=UUID('...'),
        ...     filename="interview.mp3",
        ...     duration=3600.0,
        ...     language="en",
        ...     speakers=[
        ...         Speaker(id="SPEAKER_00", name="Detective"),
        ...         Speaker(id="SPEAKER_01", name="Witness"),
        ...     ],
        ...     segments=[
        ...         TranscriptSegment(
        ...             id="seg_001",
        ...             start=0.0,
        ...             end=5.2,
        ...             text="Can you state your name for the record?",
        ...             speaker=Speaker(id="SPEAKER_00"),
        ...         ),
        ...     ],
        ...     status=TranscriptStatus.COMPLETED,
        ... )
        >>> transcript.get_speaker_text("SPEAKER_00")
        "Can you state your name for the record?"
    """

    id: UUID
    case_id: UUID
    filename: str
    duration: float
    language: str
    speakers: List[Speaker]
    segments: List[TranscriptSegment]
    status: TranscriptStatus
    created_at: datetime
    file_path: str
    mime_type: str
    size: int
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def mark_transcribing(self) -> None:
        """Mark transcript as currently being transcribed."""
        self.status = TranscriptStatus.TRANSCRIBING
        self.updated_at = datetime.utcnow()

    def mark_diarizing(self) -> None:
        """Mark transcript as performing speaker diarization."""
        self.status = TranscriptStatus.DIARIZING
        self.updated_at = datetime.utcnow()

    def mark_completed(self) -> None:
        """Mark transcript as successfully completed."""
        self.status = TranscriptStatus.COMPLETED
        self.updated_at = datetime.utcnow()

    def mark_failed(self, error: str) -> None:
        """
        Mark transcription as failed.

        Args:
            error: Error message describing the failure
        """
        self.status = TranscriptStatus.FAILED
        self.updated_at = datetime.utcnow()
        self.metadata["error"] = error
        self.metadata["failed_at"] = datetime.utcnow().isoformat()

    def get_speaker_segments(self, speaker_id: str) -> List[TranscriptSegment]:
        """
        Get all segments spoken by a specific speaker.

        Args:
            speaker_id: Speaker identifier to filter by

        Returns:
            List of segments from the specified speaker
        """
        return [
            seg for seg in self.segments
            if seg.speaker and seg.speaker.id == speaker_id
        ]

    def get_speaker_text(self, speaker_id: str) -> str:
        """
        Get all text spoken by a specific speaker.

        Args:
            speaker_id: Speaker identifier to filter by

        Returns:
            Concatenated text from all segments by this speaker
        """
        segments = self.get_speaker_segments(speaker_id)
        return " ".join(seg.text for seg in segments)

    def get_segment_at_time(self, timestamp: float) -> Optional[TranscriptSegment]:
        """
        Find the segment at a specific timestamp.

        Args:
            timestamp: Time in seconds to search for

        Returns:
            Segment containing the timestamp, or None if not found
        """
        for segment in self.segments:
            if segment.start <= timestamp <= segment.end:
                return segment
        return None

    def get_speaker_count(self) -> int:
        """Get the number of unique speakers."""
        return len(self.speakers)

    def get_text(self) -> str:
        """Get the full transcript text."""
        return " ".join(seg.text for seg in self.segments)

    def __eq__(self, other: object) -> bool:
        """Transcripts are equal if they have the same ID."""
        if not isinstance(other, Transcript):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on transcript ID."""
        return hash(self.id)
