"""Document schemas for API requests and responses."""

from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from app.models.document import DocumentStatus


class DocumentUpload(BaseModel):
    """Schema for document upload metadata."""

    case_gid: str = Field(..., description="Global ID of the case this document belongs to")


class DocumentMetadata(BaseModel):
    """Schema for document metadata."""

    author: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="allow")


class DocumentResponse(BaseModel):
    """Schema for document response."""

    gid: str = Field(..., description="Document global identifier")
    case_gid: str = Field(..., description="Case global identifier")
    filename: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="Storage path in MinIO")
    mime_type: Optional[str] = Field(None, description="MIME type of the file")
    size: int = Field(..., description="File size in bytes")
    status: DocumentStatus = Field(..., description="Processing status")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    uploaded_at: datetime = Field(..., description="Upload timestamp")

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    """Schema for list of documents response."""

    documents: List[DocumentResponse] = Field(..., description="List of documents")
    total: int = Field(..., description="Total number of documents")
    case_gid: Optional[str] = Field(None, description="Case global identifier if filtered by case")


class DocumentWithCaseInfo(DocumentResponse):
    """Schema for document response with case information."""

    case_name: str = Field(..., description="Name of the case")
    case_number: str = Field(..., description="Case number")


class PaginatedDocumentListResponse(BaseModel):
    """Schema for paginated list of documents response."""

    documents: List[DocumentWithCaseInfo] = Field(..., description="List of documents with case info")
    total: int = Field(..., description="Total number of documents")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")


class DocumentDeleteResponse(BaseModel):
    """Schema for document deletion response."""

    gid: str = Field(..., description="Deleted document global identifier")
    filename: str = Field(..., description="Deleted filename")
    message: str = Field(..., description="Deletion confirmation message")


class DocumentStatusUpdate(BaseModel):
    """Schema for updating document status."""

    status: DocumentStatus = Field(..., description="New document status")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")
