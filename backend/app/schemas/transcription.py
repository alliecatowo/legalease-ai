"""Transcription schemas for API requests and responses."""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class TranscriptionFormat(str, Enum):
    """Supported transcription export formats."""

    JSON = "json"
    DOCX = "docx"
    SRT = "srt"
    VTT = "vtt"
    TXT = "txt"


class TranscriptionOptions(BaseModel):
    """Configuration options for transcription processing."""

    language: Optional[str] = Field(
        None,
        description="Language code (e.g., 'en', 'es', 'fr'). Use None or 'auto' for auto-detection"
    )
    task: Literal["transcribe", "translate"] = Field(
        "transcribe",
        description="Task type: 'transcribe' for same-language transcription, 'translate' for translation to English"
    )
    enable_diarization: bool = Field(
        True,
        description="Enable speaker diarization (identification)"
    )
    num_speakers: Optional[int] = Field(
        None,
        ge=1,
        le=10,
        description="Exact number of speakers (if known). When set, overrides min/max for better accuracy. Use None for auto-detection."
    )
    min_speakers: Optional[int] = Field(
        2,
        ge=1,
        le=10,
        description="Minimum number of speakers to detect (used only when num_speakers is None for auto-detection)"
    )
    max_speakers: Optional[int] = Field(
        5,
        ge=1,
        le=10,
        description="Maximum number of speakers to detect (used only when num_speakers is None for auto-detection). Default: 5 for optimal accuracy."
    )
    temperature: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Sampling temperature (0.0 = deterministic, 1.0 = creative)"
    )
    initial_prompt: Optional[str] = Field(
        None,
        description="Optional initial prompt to provide context for better transcription accuracy"
    )

    model_config = ConfigDict(from_attributes=True)


class SpeakerInfo(BaseModel):
    """Schema for speaker identification information."""

    speaker_id: str = Field(..., description="Unique speaker identifier")
    label: Optional[str] = Field(None, description="Speaker label or name")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Speaker identification confidence")

    model_config = ConfigDict(from_attributes=True)


class TranscriptionSegment(BaseModel):
    """Schema for a single transcription segment with timing and speaker info."""

    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Transcribed text for this segment")
    speaker: Optional[str] = Field(None, description="Speaker identifier")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Transcription confidence score")

    model_config = ConfigDict(from_attributes=True)


class TranscriptionCreate(BaseModel):
    """Schema for creating a transcription (internal use)."""

    document_gid: str = Field(..., description="Global identifier of the associated document")
    format: Optional[str] = Field(None, description="Audio/video format (e.g., 'mp3', 'wav', 'mp4')")
    duration: Optional[float] = Field(None, description="Duration in seconds")
    speakers: Optional[List[SpeakerInfo]] = Field(None, description="List of identified speakers")
    segments: List[TranscriptionSegment] = Field(..., description="List of transcription segments")


class TranscriptionResponse(BaseModel):
    """Schema for transcription response."""

    gid: str = Field(..., description="Transcription global identifier")
    case_gid: str = Field(..., description="Associated case global identifier")
    document_gid: Optional[str] = Field(None, description="Associated document global identifier")
    filename: str = Field(..., description="Original audio/video filename")
    format: Optional[str] = Field(None, description="Audio/video format")
    duration: Optional[float] = Field(None, description="Duration in seconds")
    speakers: Optional[List[Dict[str, Any]]] = Field(None, description="Speaker identification data")
    segments: List[Dict[str, Any]] = Field(..., description="Transcription segments with timestamps")
    status: str = Field(..., description="Processing status (queued, processing, completed, failed)")
    created_at: datetime = Field(..., description="Creation timestamp")
    audio_url: Optional[str] = Field(None, description="URL to stream/download the original audio file")

    model_config = ConfigDict(from_attributes=True)


class TranscriptionListItem(BaseModel):
    """Schema for transcription list items (summary view)."""

    gid: str = Field(..., description="Transcription global identifier")
    case_gid: str = Field(..., description="Associated case global identifier")
    filename: str = Field(..., description="Original audio/video filename")
    format: Optional[str] = Field(None, description="Audio/video format")
    duration: Optional[float] = Field(None, description="Duration in seconds")
    segment_count: int = Field(0, description="Number of transcription segments")
    speaker_count: int = Field(0, description="Number of identified speakers")
    status: str = Field(..., description="Processing status (queued, processing, completed, failed)")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class TranscriptionListResponse(BaseModel):
    """Schema for paginated transcription list responses."""

    transcriptions: List[TranscriptionListItem] = Field(..., description="List of transcriptions")
    total: int = Field(..., description="Total number of transcriptions")
    case_gid: Optional[str] = Field(None, description="Case global identifier if filtered by case")


class TranscriptionDeleteResponse(BaseModel):
    """Schema for transcription deletion responses."""

    gid: str = Field(..., description="Deleted transcription global identifier")
    filename: str = Field(..., description="Deleted audio/video filename")
    message: str = Field(..., description="Deletion confirmation message")


class TranscriptionUploadResponse(BaseModel):
    """Schema for transcription upload response."""

    message: str = Field(..., description="Upload status message")
    transcription_gid: str = Field(..., description="Created transcription global identifier")
    status: str = Field(..., description="Processing status")


class UpdateSpeakerRequest(BaseModel):
    """Schema for updating speaker information."""

    name: str = Field(..., description="Speaker name", min_length=1)
    role: Optional[str] = Field(None, description="Speaker role (e.g., 'Attorney', 'Witness', 'Judge')")

    model_config = ConfigDict(from_attributes=True)


class SpeakerResponse(BaseModel):
    """Schema for speaker response."""

    speaker_id: str = Field(..., description="Speaker identifier")
    name: Optional[str] = Field(None, description="Speaker name")
    role: Optional[str] = Field(None, description="Speaker role")
    color: Optional[str] = Field(None, description="Speaker color for UI")

    model_config = ConfigDict(from_attributes=True)
