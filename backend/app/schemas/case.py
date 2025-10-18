"""Case-related Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.models.case import CaseStatus


class CaseBase(BaseModel):
    """Base case schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Case name")
    case_number: str = Field(..., min_length=1, max_length=100, description="Unique case number")
    client: str = Field(..., min_length=1, max_length=255, description="Client name")
    matter_type: Optional[str] = Field(None, max_length=100, description="Type of legal matter")


class CaseCreate(CaseBase):
    """Schema for creating a new case."""

    pass


class CaseUpdate(BaseModel):
    """Schema for updating an existing case."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Case name")
    case_number: Optional[str] = Field(None, min_length=1, max_length=100, description="Unique case number")
    client: Optional[str] = Field(None, min_length=1, max_length=255, description="Client name")
    matter_type: Optional[str] = Field(None, max_length=100, description="Type of legal matter")


class DocumentSummary(BaseModel):
    """Minimal document information for case responses."""

    gid: str = Field(..., description="Document global identifier")
    filename: str
    mime_type: Optional[str]
    size: int
    status: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TranscriptionSummary(BaseModel):
    """Minimal transcription information for case responses."""

    gid: str = Field(..., description="Transcription global identifier")
    filename: str
    mime_type: Optional[str]
    size: int
    duration: Optional[float]
    status: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CaseResponse(CaseBase):
    """Schema for case responses with all fields."""

    gid: str = Field(..., description="Case global identifier")
    status: CaseStatus
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None
    documents: List[DocumentSummary] = []
    transcriptions: List[TranscriptionSummary] = []

    model_config = ConfigDict(from_attributes=True)


class CaseListItem(BaseModel):
    """Schema for case list items (without nested relationships)."""

    gid: str = Field(..., description="Case global identifier")
    name: str
    case_number: str
    client: str
    matter_type: Optional[str]
    status: CaseStatus
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None
    document_count: int = Field(0, description="Number of documents in the case")
    transcript_count: int = Field(0, description="Number of transcriptions in the case")

    model_config = ConfigDict(from_attributes=True)


class CaseListResponse(BaseModel):
    """Schema for paginated case list responses."""

    cases: List[CaseListItem]
    total: int
    page: int = 1
    page_size: int = 50


class CaseStatusUpdate(BaseModel):
    """Schema for status update responses."""

    gid: str = Field(..., description="Case global identifier")
    case_number: str
    status: CaseStatus
    message: str

    model_config = ConfigDict(from_attributes=True)


class CaseDeleteResponse(BaseModel):
    """Schema for case deletion responses."""

    gid: str = Field(..., description="Case global identifier")
    case_number: str
    message: str
    deleted_at: datetime
