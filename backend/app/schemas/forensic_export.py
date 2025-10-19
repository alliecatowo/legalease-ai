"""Forensic Export-related Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class SummaryField(BaseModel):
    """Schema for summary field items (name/value pairs)."""

    name: str
    value: str


class ExportOption(BaseModel):
    """Schema for export option items (name/value pairs)."""

    name: str
    value: str


class ForensicExportBase(BaseModel):
    """Base forensic export schema with common fields."""

    folder_path: str = Field(..., min_length=1, max_length=1024, description="Absolute path to export folder")
    folder_name: Optional[str] = Field(None, max_length=512, description="Folder name for display")
    export_uuid: Optional[str] = Field(None, max_length=36, description="UUID from ExportSummary.json")
    axiom_version: Optional[str] = Field(None, max_length=50, description="AXIOM version used for export")
    total_records: Optional[int] = Field(None, ge=0, description="Total number of records")
    exported_records: Optional[int] = Field(None, ge=0, description="Number of records in export")
    num_attachments: Optional[int] = Field(None, ge=0, description="Number of attachments")
    export_start_date: Optional[datetime] = Field(None, description="Export start date/time")
    export_end_date: Optional[datetime] = Field(None, description="Export end date/time")
    export_duration: Optional[str] = Field(None, max_length=50, description="Export duration")
    size_bytes: Optional[int] = Field(None, ge=0, description="Export size in bytes")
    export_status: Optional[str] = Field(None, max_length=50, description="Export status (e.g., Completed)")
    case_directory: Optional[str] = Field(None, max_length=512, description="Case directory from export")
    case_storage_location: Optional[str] = Field(None, max_length=256, description="Case storage location")


class ForensicExportCreate(ForensicExportBase):
    """Schema for creating a new forensic export."""

    case_gid: str = Field(..., description="Global identifier of the case this export belongs to")


class ForensicExportResponse(ForensicExportBase):
    """Schema for forensic export responses with all fields."""

    gid: str = Field(..., description="Forensic export global identifier")
    case_gid: str = Field(..., description="Case global identifier")
    case_name: Optional[str] = Field(None, description="Case name for display")
    summary_json: Optional[List[SummaryField]] = Field(None, description="Full summary array from JSON")
    export_options_json: Optional[List[ExportOption]] = Field(None, description="Export options from JSON")
    problems_json: Optional[List[Any]] = Field(None, description="Problems array from JSON")
    discovered_at: datetime
    last_verified_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ForensicExportListItem(BaseModel):
    """Schema for forensic export list items (without full JSON)."""

    gid: str = Field(..., description="Forensic export global identifier")
    case_gid: str = Field(..., description="Case global identifier")
    case_name: Optional[str] = Field(None, description="Case name for display")
    folder_name: Optional[str]
    export_uuid: Optional[str]
    total_records: Optional[int]
    exported_records: Optional[int]
    num_attachments: Optional[int]
    size_bytes: Optional[int]
    export_status: Optional[str]
    discovered_at: datetime
    last_verified_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ForensicExportListResponse(BaseModel):
    """Schema for paginated forensic export list responses."""

    exports: List[ForensicExportListItem]
    total: int


class ScanLocationRequest(BaseModel):
    """Schema for scan location request."""

    path: str = Field(..., min_length=1, description="Root path to scan for exports")


class ScanResultItem(BaseModel):
    """Schema for a single scan result."""

    gid: str = Field(..., description="Forensic export global identifier")
    path: str
    name: str


class ScanErrorItem(BaseModel):
    """Schema for a scan error."""

    path: str
    error: str


class ScanLocationResponse(BaseModel):
    """Schema for scan location response."""

    scanned_path: str
    case_gid: str = Field(..., description="Case global identifier")
    found: List[ScanResultItem] = Field(default_factory=list, description="Newly discovered exports")
    existing: List[str] = Field(default_factory=list, description="Already registered export paths")
    errors: List[ScanErrorItem] = Field(default_factory=list, description="Errors during scanning")


class VerifyExportResponse(BaseModel):
    """Schema for verify export response."""

    exists: bool
    path: str
    verified_at: datetime


class DeleteForensicExportResponse(BaseModel):
    """Schema for forensic export deletion responses."""

    gid: str = Field(..., description="Deleted forensic export global identifier")
    folder_path: str
    message: str
