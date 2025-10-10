"""Transcription schemas for API requests and responses."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class TranscriptionFormat(str, Enum):
    """Supported transcription export formats."""

    JSON = "json"
    DOCX = "docx"
    SRT = "srt"
    VTT = "vtt"
    TXT = "txt"


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

    document_id: int = Field(..., description="ID of the associated document")
    format: Optional[str] = Field(None, description="Audio/video format (e.g., 'mp3', 'wav', 'mp4')")
    duration: Optional[float] = Field(None, description="Duration in seconds")
    speakers: Optional[List[SpeakerInfo]] = Field(None, description="List of identified speakers")
    segments: List[TranscriptionSegment] = Field(..., description="List of transcription segments")


class TranscriptionResponse(BaseModel):
    """Schema for transcription response."""

    id: int = Field(..., description="Transcription ID")
    document_id: int = Field(..., description="Associated document ID")
    case_id: int = Field(..., description="Associated case ID")
    filename: str = Field(..., description="Original audio/video filename")
    format: Optional[str] = Field(None, description="Audio/video format")
    duration: Optional[float] = Field(None, description="Duration in seconds")
    speakers: Optional[List[Dict[str, Any]]] = Field(None, description="Speaker identification data")
    segments: List[Dict[str, Any]] = Field(..., description="Transcription segments with timestamps")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class TranscriptionListItem(BaseModel):
    """Schema for transcription list items (summary view)."""

    id: int = Field(..., description="Transcription ID")
    document_id: int = Field(..., description="Associated document ID")
    case_id: int = Field(..., description="Associated case ID")
    filename: str = Field(..., description="Original audio/video filename")
    format: Optional[str] = Field(None, description="Audio/video format")
    duration: Optional[float] = Field(None, description="Duration in seconds")
    segment_count: int = Field(0, description="Number of transcription segments")
    speaker_count: int = Field(0, description="Number of identified speakers")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class TranscriptionListResponse(BaseModel):
    """Schema for paginated transcription list responses."""

    transcriptions: List[TranscriptionListItem] = Field(..., description="List of transcriptions")
    total: int = Field(..., description="Total number of transcriptions")
    case_id: Optional[int] = Field(None, description="Case ID if filtered by case")


class TranscriptionDeleteResponse(BaseModel):
    """Schema for transcription deletion responses."""

    id: int = Field(..., description="Deleted transcription ID")
    document_id: int = Field(..., description="Associated document ID")
    filename: str = Field(..., description="Deleted audio/video filename")
    message: str = Field(..., description="Deletion confirmation message")


class TranscriptionUploadResponse(BaseModel):
    """Schema for transcription upload response."""

    message: str = Field(..., description="Upload status message")
    document_id: int = Field(..., description="Created document ID")
    transcription_id: Optional[int] = Field(None, description="Transcription ID (if processing completed)")
    status: str = Field(..., description="Processing status")
