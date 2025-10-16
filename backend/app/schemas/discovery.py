"""Discovery item schemas for API requests and responses."""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict
from app.models.discovery_item import (
    DiscoveryItemType,
    DiscoveryItemSource,
    DiscoveryItemFormFactor,
)
from app.models.import_batch import ImportStatus
from app.models.category import CategoryType


# ==================== Discovery Item Schemas ====================


class DiscoveryItemCreate(BaseModel):
    """Schema for creating a discovery item."""

    case_id: int = Field(..., description="ID of the case this item belongs to")
    type: DiscoveryItemType = Field(..., description="Type of discovery item")
    source: DiscoveryItemSource = Field(..., description="Source of the discovery item")
    form_factor: DiscoveryItemFormFactor = Field(..., description="Form factor of the content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata as JSON")


class DiscoveryItemUpdate(BaseModel):
    """Schema for updating a discovery item."""

    importance_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Importance score between 0.0 and 1.0"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")


class DiscoveryItemFilters(BaseModel):
    """Schema for filtering discovery items in list queries."""

    case_id: Optional[int] = Field(None, description="Filter by case ID")
    type: Optional[DiscoveryItemType] = Field(None, description="Filter by item type")
    source: Optional[DiscoveryItemSource] = Field(None, description="Filter by source")
    form_factor: Optional[DiscoveryItemFormFactor] = Field(None, description="Filter by form factor")
    min_importance: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum importance score")
    max_importance: Optional[float] = Field(None, ge=0.0, le=1.0, description="Maximum importance score")
    date_from: Optional[datetime] = Field(None, description="Filter items created after this date")
    date_to: Optional[datetime] = Field(None, description="Filter items created before this date")
    search: Optional[str] = Field(None, description="Search query for filename or metadata")
    processed: Optional[bool] = Field(None, description="Filter by processed status")
    skip: int = Field(0, ge=0, description="Number of records to skip (pagination)")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of records to return")

    model_config = ConfigDict(extra="forbid")


class CategoryResponse(BaseModel):
    """Schema for category response."""

    id: int = Field(..., description="Category ID")
    name: str = Field(..., description="Category name")
    type: CategoryType = Field(..., description="Category type")
    parent_category_id: Optional[int] = Field(None, description="Parent category ID")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class DiscoveryItemResponse(BaseModel):
    """Schema for discovery item response."""

    id: int = Field(..., description="Discovery item ID")
    case_id: int = Field(..., description="Case ID")
    type: DiscoveryItemType = Field(..., description="Item type")
    source: DiscoveryItemSource = Field(..., description="Item source")
    form_factor: DiscoveryItemFormFactor = Field(..., description="Form factor")
    original_filename: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="Storage path in MinIO")
    item_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    processed: bool = Field(..., description="Whether item has been processed")
    importance_score: Optional[float] = Field(None, description="Importance score (0.0-1.0)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    categories: Optional[List[CategoryResponse]] = Field(None, description="Associated categories")

    model_config = ConfigDict(from_attributes=True)


class DiscoveryItemPreviewResponse(BaseModel):
    """Schema for discovery item file preview."""

    preview_type: Literal['image', 'video', 'audio', 'text', 'table', 'binary', 'unsupported'] = Field(
        ..., description="Type of preview representation"
    )
    content_type: str = Field(..., description="MIME type of the file")
    size: int = Field(..., description="Size of the file in bytes")
    text: Optional[str] = Field(None, description="Text preview (when applicable)")
    truncated: bool = Field(False, description="Whether the preview was truncated for size limits")
    headers: Optional[List[str]] = Field(None, description="Table headers for structured previews like CSV")
    rows: Optional[List[List[str]]] = Field(None, description="Table rows for structured previews like CSV")
    key_values: Optional[List[Dict[str, str]]] = Field(None, description="Key/value representation for structured data")
    html: Optional[str] = Field(None, description="HTML preview content (sanitized client-side)")
    markdown: Optional[str] = Field(None, description="Markdown preview content")

    model_config = ConfigDict(from_attributes=True)


class DiscoveryBulkDownloadRequest(BaseModel):
    """Schema for bulk discovery item download."""

    item_ids: List[int] = Field(..., min_length=1, max_length=100, description="IDs of discovery items to download")


class DiscoveryItemListResponse(BaseModel):
    """Schema for paginated list of discovery items."""

    items: List[DiscoveryItemResponse] = Field(..., description="List of discovery items")
    total: int = Field(..., description="Total number of items matching filters")
    skip: int = Field(..., description="Number of records skipped")
    limit: int = Field(..., description="Maximum number of records returned")


class DiscoveryItemDeleteResponse(BaseModel):
    """Schema for discovery item deletion response."""

    id: int = Field(..., description="Deleted item ID")
    filename: str = Field(..., description="Deleted filename")
    message: str = Field(..., description="Deletion confirmation message")


# ==================== Visual Content Schemas ====================


class VisualContentResponse(BaseModel):
    """Schema for visual content analysis response."""

    id: int = Field(..., description="Visual content ID")
    discovery_item_id: int = Field(..., description="Associated discovery item ID")
    frame_number: Optional[int] = Field(None, description="Frame number (NULL for photos)")
    timestamp_in_video: Optional[float] = Field(None, description="Timestamp in seconds (NULL for photos)")
    vlm_caption: Optional[str] = Field(None, description="VLM-generated caption/description")
    detected_objects: Optional[List[Dict[str, Any]]] = Field(None, description="Detected objects")
    detected_scenes: Optional[List[Dict[str, Any]]] = Field(None, description="Detected scenes")
    detected_activities: Optional[List[Dict[str, Any]]] = Field(None, description="Detected activities")
    sensitive_flags: Optional[Dict[str, Any]] = Field(None, description="Sensitive content flags")
    is_meme: bool = Field(..., description="Whether content is identified as a meme")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class VisualContentListResponse(BaseModel):
    """Schema for list of visual content analysis results."""

    visual_content: List[VisualContentResponse] = Field(..., description="List of visual content analyses")
    total: int = Field(..., description="Total number of analyses")


# ==================== Video Summary Schemas ====================


class VideoSummaryResponse(BaseModel):
    """Schema for video summary response."""

    id: int = Field(..., description="Video summary ID")
    discovery_item_id: int = Field(..., description="Associated discovery item ID")
    comprehensive_summary: Optional[str] = Field(None, description="Overall video summary")
    key_moments: Optional[List[Dict[str, Any]]] = Field(None, description="Key moments with timestamps")
    visual_summary: Optional[str] = Field(None, description="Summary of visual content")
    audio_summary: Optional[str] = Field(None, description="Summary of audio content")
    importance_score: Optional[float] = Field(None, description="Overall importance score (0.0-1.0)")
    flagged_content: Optional[List[Dict[str, Any]]] = Field(None, description="Flagged content with reasons")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


# ==================== Import Batch Schemas ====================


class ImportBatchCreate(BaseModel):
    """Schema for creating an import batch."""

    case_id: int = Field(..., description="Case ID to import items into")
    source_type: str = Field(..., description="Source type (cellebrite, prosecutor_package, etc.)")
    import_path: str = Field(..., description="Path to source data")
    total_items: int = Field(..., ge=0, description="Total number of items to import")


class ImportBatchResponse(BaseModel):
    """Schema for import batch status response."""

    id: int = Field(..., description="Import batch ID")
    case_id: int = Field(..., description="Case ID")
    source_type: str = Field(..., description="Source type")
    total_items: int = Field(..., description="Total number of items to import")
    processed_items: int = Field(..., description="Number of items processed")
    status: ImportStatus = Field(..., description="Import status")
    import_path: str = Field(..., description="Path to source data")
    error_log: Optional[str] = Field(None, description="Error messages and logs")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    progress_percentage: float = Field(..., description="Import progress percentage (0-100)")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_progress(cls, batch):
        """Create response with calculated progress percentage."""
        progress = 0.0
        if batch.total_items > 0:
            progress = (batch.processed_items / batch.total_items) * 100.0

        data = {
            "id": batch.id,
            "case_id": batch.case_id,
            "source_type": batch.source_type,
            "total_items": batch.total_items,
            "processed_items": batch.processed_items,
            "status": batch.status,
            "import_path": batch.import_path,
            "error_log": batch.error_log,
            "created_at": batch.created_at,
            "completed_at": batch.completed_at,
            "progress_percentage": progress,
        }
        return cls(**data)


class ImportBatchListResponse(BaseModel):
    """Schema for list of import batches."""

    batches: List[ImportBatchResponse] = Field(..., description="List of import batches")
    total: int = Field(..., description="Total number of batches")


# ==================== Category Management Schemas ====================


class CategoryCreate(BaseModel):
    """Schema for creating a category."""

    name: str = Field(..., min_length=1, max_length=255, description="Category name")
    type: CategoryType = Field(..., description="Category type")
    parent_category_id: Optional[int] = Field(None, description="Parent category ID for hierarchical organization")


class CategoryUpdate(BaseModel):
    """Schema for updating a category."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Updated category name")
    parent_category_id: Optional[int] = Field(None, description="Updated parent category ID")


class AddCategoryRequest(BaseModel):
    """Schema for adding a category to a discovery item."""

    category_id: int = Field(..., description="Category ID to add")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score (for auto-generated)")
    auto_generated: bool = Field(False, description="Whether this is an auto-generated classification")


class CategoryAssociationResponse(BaseModel):
    """Schema for category association confirmation."""

    discovery_item_id: int = Field(..., description="Discovery item ID")
    category_id: int = Field(..., description="Category ID")
    confidence_score: Optional[float] = Field(None, description="Confidence score")
    auto_generated: bool = Field(..., description="Whether auto-generated")
    message: str = Field(..., description="Confirmation message")


# ==================== Search Schemas ====================


class DiscoverySearchRequest(BaseModel):
    """Schema for discovery item hybrid search request."""

    case_id: int = Field(..., description="Case ID to search within")
    query: str = Field(..., min_length=1, description="Search query")
    types: Optional[List[DiscoveryItemType]] = Field(None, description="Filter by item types")
    sources: Optional[List[DiscoveryItemSource]] = Field(None, description="Filter by sources")
    min_importance: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum importance score")
    limit: int = Field(20, ge=1, le=100, description="Maximum number of results")


class DiscoverySearchResult(BaseModel):
    """Schema for individual search result."""

    discovery_item: DiscoveryItemResponse = Field(..., description="Discovery item details")
    relevance_score: float = Field(..., description="Search relevance score")
    matched_content: Optional[str] = Field(None, description="Snippet of matched content")


class DiscoverySearchResponse(BaseModel):
    """Schema for discovery search response."""

    results: List[DiscoverySearchResult] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of results")
    query: str = Field(..., description="Original search query")


# ==================== Reprocessing Schema ====================


class ReprocessResponse(BaseModel):
    """Schema for reprocess request response."""

    discovery_item_id: int = Field(..., description="Discovery item ID")
    message: str = Field(..., description="Reprocessing status message")
    status: str = Field(..., description="Current processing status")
