"""Discovery item API endpoints."""

import csv
import io
import json
import logging
import mimetypes
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Query, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.discovery import (
    DiscoveryItemResponse,
    DiscoveryItemUpdate,
    DiscoveryItemFilters,
    DiscoveryItemListResponse,
    DiscoveryItemDeleteResponse,
    VisualContentResponse,
    VisualContentListResponse,
    VideoSummaryResponse,
    ImportBatchCreate,
    ImportBatchResponse,
    ImportBatchListResponse,
    CategoryResponse,
    CategoryCreate,
    CategoryUpdate,
    AddCategoryRequest,
    CategoryAssociationResponse,
    DiscoverySearchRequest,
    DiscoverySearchResponse,
    ReprocessResponse,
    DiscoveryItemPreviewResponse,
    DiscoveryBulkDownloadRequest,
)
from app.models.discovery_item import (
    DiscoveryItem,
    DiscoveryItemType,
    DiscoveryItemSource,
    DiscoveryItemFormFactor,
)
from app.models.visual_content import VisualContent
from app.models.video_summary import VideoSummary
from app.models.import_batch import ImportBatch, ImportStatus
from app.models.category import Category, CategoryType
from app.models.discovery_item_category import DiscoveryItemCategory
from app.services.discovery_service import DiscoveryService

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_PREVIEW_BYTES = 512 * 1024  # 512 KB
MAX_PREVIEW_ROWS = 50
MAX_KEY_VALUES = 100
MAX_TEXT_PREVIEW_CHARS = 6000


def _flatten_key_values(data, prefix="", results=None):
    """Flatten nested structures into label/value pairs."""

    if results is None:
        results = []

    if len(results) >= MAX_KEY_VALUES:
        return results

    if isinstance(data, dict):
        for key, value in data.items():
            label = f"{prefix}.{key}" if prefix else str(key)
            _flatten_key_values(value, label, results)
            if len(results) >= MAX_KEY_VALUES:
                break
    elif isinstance(data, list):
        for index, value in enumerate(data):
            label = f"{prefix}[{index}]" if prefix else f"[{index}]"
            _flatten_key_values(value, label, results)
            if len(results) >= MAX_KEY_VALUES:
                break
    else:
        label = prefix or "value"
        results.append({
            "label": label,
            "value": str(data)
        })

    return results


# ==================== Discovery Item Upload & Management ====================


@router.post(
    "/discovery/items",
    response_model=DiscoveryItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a discovery item",
    description="Upload a single discovery item (photo, video, audio, etc.) to a case. Files are stored in MinIO and processing is queued.",
)
async def create_discovery_item(
    case_id: int = Form(..., description="Case ID"),
    type: DiscoveryItemType = Form(..., description="Discovery item type"),
    source: DiscoveryItemSource = Form(..., description="Source of the item"),
    form_factor: DiscoveryItemFormFactor = Form(..., description="Form factor"),
    file: UploadFile = File(..., description="File to upload"),
    db: Session = Depends(get_db),
):
    """
    Upload a discovery item to a case.

    Args:
        case_id: ID of the case
        type: Type of discovery item
        source: Source of the item
        form_factor: Form factor of the content
        file: File to upload
        db: Database session

    Returns:
        DiscoveryItemResponse: Created discovery item
    """
    logger.info(f"Uploading discovery item '{file.filename}' to case {case_id}")

    # TODO: Implement upload logic using discovery service
    # This will:
    # 1. Validate case exists
    # 2. Upload file to MinIO
    # 3. Create DiscoveryItem record
    # 4. Queue processing job based on type

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Discovery item upload not yet implemented",
    )


@router.get(
    "/discovery/items",
    response_model=DiscoveryItemListResponse,
    summary="List discovery items",
    description="Get a paginated list of discovery items with optional filters.",
)
async def list_discovery_items(
    case_id: Optional[int] = Query(None, description="Filter by case ID"),
    type: Optional[DiscoveryItemType] = Query(None, description="Filter by item type"),
    source: Optional[DiscoveryItemSource] = Query(None, description="Filter by source"),
    form_factor: Optional[DiscoveryItemFormFactor] = Query(None, description="Filter by form factor"),
    min_importance: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum importance score"),
    max_importance: Optional[float] = Query(None, ge=0.0, le=1.0, description="Maximum importance score"),
    processed: Optional[bool] = Query(None, description="Filter by processed status"),
    search: Optional[str] = Query(None, description="Search query for filename or metadata"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
):
    """
    List discovery items with filters and pagination.

    Args:
        case_id: Filter by case ID
        type: Filter by item type
        source: Filter by source
        form_factor: Filter by form factor
        min_importance: Minimum importance score
        max_importance: Maximum importance score
        processed: Filter by processed status
        search: Search query
        skip: Number of records to skip
        limit: Maximum records to return
        db: Database session

    Returns:
        DiscoveryItemListResponse: Paginated list of items
    """
    logger.info(f"Listing discovery items (skip={skip}, limit={limit})")

    query = db.query(DiscoveryItem)

    # Apply filters
    if case_id:
        query = query.filter(DiscoveryItem.case_id == case_id)
    if type:
        query = query.filter(DiscoveryItem.type == type)
    if source:
        query = query.filter(DiscoveryItem.source == source)
    if form_factor:
        query = query.filter(DiscoveryItem.form_factor == form_factor)
    if min_importance is not None:
        query = query.filter(DiscoveryItem.importance_score >= min_importance)
    if max_importance is not None:
        query = query.filter(DiscoveryItem.importance_score <= max_importance)
    if processed is not None:
        query = query.filter(DiscoveryItem.processed == processed)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(DiscoveryItem.original_filename.ilike(search_pattern))

    # Get total count
    total = query.count()

    # Apply pagination
    items = query.order_by(DiscoveryItem.created_at.desc()).offset(skip).limit(limit).all()

    return DiscoveryItemListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/discovery/stats",
    summary="Get discovery statistics",
    description="Get aggregate statistics for discovery items.",
)
async def get_discovery_stats(
    case_id: Optional[int] = Query(None, description="Filter by case ID"),
    db: Session = Depends(get_db),
):
    """
    Get discovery statistics.

    Args:
        case_id: Optional case ID filter
        db: Database session

    Returns:
        dict: Statistics including total, high importance, processing, storage used
    """
    logger.info(f"Getting discovery stats{f' for case {case_id}' if case_id else ''}")

    query = db.query(DiscoveryItem)
    if case_id:
        query = query.filter(DiscoveryItem.case_id == case_id)

    # Total items
    total = query.count()

    # High importance items (>= 0.7)
    high_importance = query.filter(DiscoveryItem.importance_score >= 0.7).count()

    # Processing items
    processing = query.filter(DiscoveryItem.processed == False).count()

    # Storage used (sum of file sizes from metadata)
    items = query.all()
    storage_used = sum(
        item.item_metadata.get("file_size", 0) if item.item_metadata else 0
        for item in items
    )

    return {
        "total": total,
        "highImportance": high_importance,
        "processing": processing,
        "storageUsed": storage_used,
    }


@router.get(
    "/discovery/items/{item_id}",
    response_model=DiscoveryItemResponse,
    summary="Get discovery item details",
    description="Get detailed information about a specific discovery item.",
)
async def get_discovery_item(
    item_id: int,
    db: Session = Depends(get_db),
):
    """
    Get discovery item by ID.

    Args:
        item_id: Discovery item ID
        db: Database session

    Returns:
        DiscoveryItemResponse: Item details
    """
    logger.info(f"Getting discovery item {item_id}")

    item = db.query(DiscoveryItem).filter(DiscoveryItem.id == item_id).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery item {item_id} not found",
        )

    return item


@router.get(
    "/discovery/items/{item_id}/download",
    summary="Download discovery item file",
    description="Download the original file associated with a discovery item.",
)
async def download_discovery_item(
    item_id: int,
    db: Session = Depends(get_db),
):
    """
    Download a discovery item file.

    Args:
        item_id: Discovery item ID
        db: Database session

    Returns:
        StreamingResponse: File stream response
    """
    logger.info(f"Downloading discovery item {item_id}")

    content, filename, content_type = DiscoveryService.download_discovery_item(item_id, db)

    if not content_type:
        guess, _ = mimetypes.guess_type(filename)
        content_type = guess or "application/octet-stream"

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"'
    }

    return StreamingResponse(
        io.BytesIO(content),
        media_type=content_type,
        headers=headers,
    )


@router.post(
    "/discovery/items/bulk-download",
    summary="Download multiple discovery items as a bundle",
    description="Download a zipped archive containing the selected discovery item files.",
)
async def bulk_download_discovery_items(
    request: DiscoveryBulkDownloadRequest,
    db: Session = Depends(get_db),
):
    """Bundle multiple discovery item files into a single ZIP download."""

    if len(request.item_ids) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="At least one item ID is required")

    logger.info("Bulk downloading %d discovery items", len(request.item_ids))

    zip_buffer = io.BytesIO()
    seen_names = set()

    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item_id in request.item_ids:
            item = db.query(DiscoveryItem).filter(DiscoveryItem.id == item_id).first()
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Discovery item {item_id} not found",
                )

            content, filename, _ = DiscoveryService.download_discovery_item(item_id, db)

            safe_name = filename or f"discovery-item-{item_id}"
            if safe_name in seen_names:
                stem = Path(safe_name).stem or f"item-{item_id}"
                suffix = Path(safe_name).suffix
                safe_name = f"{stem}_{item_id}{suffix}"
            seen_names.add(safe_name)

            archive.writestr(safe_name, content)

    zip_buffer.seek(0)
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    headers = {
        "Content-Disposition": f'attachment; filename="discovery-items-{timestamp}.zip"'
    }

    return StreamingResponse(zip_buffer, media_type="application/zip", headers=headers)


@router.get(
    "/discovery/items/{item_id}/preview",
    response_model=DiscoveryItemPreviewResponse,
    summary="Get discovery item preview",
    description="Return a lightweight preview of a discovery item's content for inline viewing.",
)
async def preview_discovery_item(
    item_id: int,
    db: Session = Depends(get_db),
):
    """
    Generate a preview for a discovery item.

    Args:
        item_id: Discovery item ID
        db: Database session

    Returns:
        DiscoveryItemPreviewResponse: Preview details for the item
    """
    logger.info(f"Generating preview for discovery item {item_id}")

    item = db.query(DiscoveryItem).filter(DiscoveryItem.id == item_id).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery item {item_id} not found",
        )

    try:
        content, filename, content_type = DiscoveryService.download_discovery_item(item_id, db)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
            logger.warning("Preview unavailable for item %s due to storage error: %s", item_id, exc.detail)
            metadata = item.item_metadata or {}
            fallback_type = metadata.get("content_type") or mimetypes.guess_type(item.original_filename)[0] or "application/octet-stream"
            return DiscoveryItemPreviewResponse(
                preview_type="unsupported",
                content_type=fallback_type,
                size=0,
                text=None,
                truncated=False,
                headers=None,
                rows=None,
            )
        raise

    if not content_type:
        guess, _ = mimetypes.guess_type(filename)
        content_type = guess or "application/octet-stream"

    preview_type = "binary"
    text_preview: Optional[str] = None
    headers: Optional[List[str]] = None
    rows: Optional[List[List[str]]] = None
    key_values: Optional[List[Dict[str, str]]] = None
    html_content: Optional[str] = None
    markdown_content: Optional[str] = None
    truncated = False

    extension = Path(filename).suffix.lower()

    if item.type == DiscoveryItemType.PHOTO or content_type.startswith("image/"):
        preview_type = "image"
    elif item.type == DiscoveryItemType.VIDEO or content_type.startswith("video/"):
        preview_type = "video"
    elif item.type == DiscoveryItemType.AUDIO or content_type.startswith("audio/"):
        preview_type = "audio"
    else:
        preview_bytes = content[:MAX_PREVIEW_BYTES]
        truncated = len(content) > MAX_PREVIEW_BYTES
        decoded_text = preview_bytes.decode("utf-8", errors="replace") if preview_bytes else ""

        is_markdown = content_type in {"text/markdown"} or extension in {".md", ".markdown"}
        is_html = content_type in {"text/html"} or extension in {".html", ".htm", ".xhtml"}
        is_csv = (
            content_type in {"text/csv", "application/csv", "text/tab-separated-values"}
            or extension in {".csv", ".tsv"}
            or item.type == DiscoveryItemType.CALL_LOG
        )
        is_json = content_type in {"application/json", "text/json"} or extension == ".json"
        is_excel = extension in {".xlsx", ".xlsm", ".xltx", ".xltm"}
        is_docx = extension == ".docx"
        is_plain_text = content_type.startswith("text/") or extension in {".txt", ".log", ".rtf"}

        if is_markdown and decoded_text:
            preview_type = "markdown"
            markdown_content = decoded_text[:MAX_TEXT_PREVIEW_CHARS]
            if len(decoded_text) > MAX_TEXT_PREVIEW_CHARS:
                truncated = True
        elif is_html and decoded_text:
            preview_type = "html"
            html_content = decoded_text[:MAX_TEXT_PREVIEW_CHARS]
            if len(decoded_text) > MAX_TEXT_PREVIEW_CHARS:
                truncated = True
        elif is_json and decoded_text:
            try:
                parsed = json.loads(decoded_text)
                pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
                if len(pretty) > MAX_TEXT_PREVIEW_CHARS:
                    pretty = pretty[:MAX_TEXT_PREVIEW_CHARS]
                    truncated = True
                text_preview = pretty
                key_values = _flatten_key_values(parsed)
                if len(key_values) > MAX_KEY_VALUES:
                    key_values = key_values[:MAX_KEY_VALUES]
                    truncated = True
                preview_type = "key_value"
            except json.JSONDecodeError:
                preview_type = "text"
                text_preview = decoded_text[:MAX_TEXT_PREVIEW_CHARS]
                if len(decoded_text) > MAX_TEXT_PREVIEW_CHARS:
                    truncated = True
        elif is_csv and decoded_text:
            preview_type = "table"
            try:
                delimiter = '\t' if extension == ".tsv" else ','
                reader = csv.reader(io.StringIO(decoded_text), delimiter=delimiter)
                rows_list = list(reader)
                if rows_list:
                    headers = [cell.strip() for cell in rows_list[0]]
                    rows = [
                        [cell.strip() for cell in row]
                        for row in rows_list[1:MAX_PREVIEW_ROWS + 1]
                    ]
                    if len(rows_list) - 1 > MAX_PREVIEW_ROWS:
                        truncated = True
                else:
                    headers = []
                    rows = []
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Failed to parse CSV/TSV preview for item %s: %s", item_id, exc)
                preview_type = "text"
                text_preview = decoded_text[:MAX_TEXT_PREVIEW_CHARS]
                if len(decoded_text) > MAX_TEXT_PREVIEW_CHARS:
                    truncated = True
        elif is_excel:
            preview_type = "table"
            try:
                from openpyxl import load_workbook

                workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
                sheet = workbook.active
                headers = []
                rows = []

                for row_index, row in enumerate(sheet.iter_rows(values_only=True)):
                    values = ["" if cell is None else str(cell) for cell in row]
                    if row_index == 0:
                        headers = values
                    else:
                        rows.append(values)
                        if len(rows) >= MAX_PREVIEW_ROWS:
                            truncated = True
                            break

                if not headers and rows:
                    max_columns = max(len(r) for r in rows)
                    headers = [f"Column {i + 1}" for i in range(max_columns)]

                workbook.close()
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Failed to parse spreadsheet preview for item %s: %s", item_id, exc)
                preview_type = "binary"
                headers = None
                rows = None
        elif is_docx:
            try:
                from docx import Document

                document = Document(io.BytesIO(content))
                paragraphs = [para.text for para in document.paragraphs if para.text.strip()]
                combined = '\n\n'.join(paragraphs)
                text_preview = combined[:MAX_TEXT_PREVIEW_CHARS]
                if len(combined) > MAX_TEXT_PREVIEW_CHARS:
                    truncated = True
                preview_type = "text"
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Failed to parse DOCX preview for item %s: %s", item_id, exc)
                preview_type = "binary"
        elif is_plain_text and decoded_text:
            preview_type = "text"
            text_preview = decoded_text[:MAX_TEXT_PREVIEW_CHARS]
            if len(decoded_text) > MAX_TEXT_PREVIEW_CHARS:
                truncated = True
        else:
            preview_type = "binary"

    return DiscoveryItemPreviewResponse(
        preview_type=preview_type,
        content_type=content_type,
        size=len(content),
        text=text_preview,
        truncated=truncated,
        headers=headers,
        rows=rows,
        key_values=key_values,
        html=html_content,
        markdown=markdown_content,
    )


@router.patch(
    "/discovery/items/{item_id}",
    response_model=DiscoveryItemResponse,
    summary="Update discovery item",
    description="Update a discovery item's importance score or metadata.",
)
async def update_discovery_item(
    item_id: int,
    update: DiscoveryItemUpdate,
    db: Session = Depends(get_db),
):
    """
    Update discovery item.

    Args:
        item_id: Discovery item ID
        update: Update data
        db: Database session

    Returns:
        DiscoveryItemResponse: Updated item
    """
    logger.info(f"Updating discovery item {item_id}")

    item = db.query(DiscoveryItem).filter(DiscoveryItem.id == item_id).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery item {item_id} not found",
        )

    # Update fields
    if update.importance_score is not None:
        item.importance_score = update.importance_score
    if update.metadata is not None:
        item.item_metadata = update.metadata

    db.commit()
    db.refresh(item)

    return item


@router.delete(
    "/discovery/items/{item_id}",
    response_model=DiscoveryItemDeleteResponse,
    summary="Delete a discovery item",
    description="Delete a discovery item from both storage and database. This action cannot be undone.",
)
async def delete_discovery_item(
    item_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a discovery item.

    Args:
        item_id: Discovery item ID
        db: Database session

    Returns:
        DiscoveryItemDeleteResponse: Deletion confirmation
    """
    logger.info(f"Deleting discovery item {item_id}")

    item = db.query(DiscoveryItem).filter(DiscoveryItem.id == item_id).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery item {item_id} not found",
        )

    filename = item.original_filename

    # TODO: Delete file from MinIO storage
    # TODO: Delete from vector database if indexed

    db.delete(item)
    db.commit()

    return DiscoveryItemDeleteResponse(
        id=item_id,
        filename=filename,
        message=f"Discovery item '{filename}' deleted successfully",
    )


# ==================== Analysis Results ====================


@router.get(
    "/discovery/items/{item_id}/visual",
    response_model=VisualContentListResponse,
    summary="Get visual content analysis",
    description="Get VLM analysis results for an item's visual content (images or video frames).",
)
async def get_visual_content(
    item_id: int,
    db: Session = Depends(get_db),
):
    """
    Get visual content analysis for an item.

    Args:
        item_id: Discovery item ID
        db: Database session

    Returns:
        VisualContentListResponse: Visual analysis results
    """
    logger.info(f"Getting visual content for discovery item {item_id}")

    # Verify item exists
    item = db.query(DiscoveryItem).filter(DiscoveryItem.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery item {item_id} not found",
        )

    # Get visual content
    visual_content = db.query(VisualContent).filter(
        VisualContent.discovery_item_id == item_id
    ).all()

    return VisualContentListResponse(
        visual_content=visual_content,
        total=len(visual_content),
    )


@router.get(
    "/discovery/items/{item_id}/video-summary",
    response_model=VideoSummaryResponse,
    summary="Get video summary",
    description="Get comprehensive video analysis including summaries, key moments, and flagged content.",
)
async def get_video_summary(
    item_id: int,
    db: Session = Depends(get_db),
):
    """
    Get video summary for an item.

    Args:
        item_id: Discovery item ID
        db: Database session

    Returns:
        VideoSummaryResponse: Video summary
    """
    logger.info(f"Getting video summary for discovery item {item_id}")

    # Verify item exists and is a video
    item = db.query(DiscoveryItem).filter(DiscoveryItem.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery item {item_id} not found",
        )

    if item.type != DiscoveryItemType.VIDEO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Item {item_id} is not a video",
        )

    # Get video summary
    summary = db.query(VideoSummary).filter(
        VideoSummary.discovery_item_id == item_id
    ).first()

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video summary not found for item {item_id}",
        )

    return summary


@router.post(
    "/discovery/items/{item_id}/reprocess",
    response_model=ReprocessResponse,
    summary="Reprocess discovery item",
    description="Queue a discovery item for reprocessing with VLM/analysis pipeline.",
)
async def reprocess_discovery_item(
    item_id: int,
    db: Session = Depends(get_db),
):
    """
    Reprocess a discovery item.

    Args:
        item_id: Discovery item ID
        db: Database session

    Returns:
        ReprocessResponse: Reprocessing status
    """
    logger.info(f"Reprocessing discovery item {item_id}")

    item = db.query(DiscoveryItem).filter(DiscoveryItem.id == item_id).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery item {item_id} not found",
        )

    # Reset processed flag
    item.processed = False
    db.commit()

    # TODO: Queue reprocessing job based on item type

    return ReprocessResponse(
        discovery_item_id=item_id,
        message="Item queued for reprocessing",
        status="queued",
    )


# ==================== Batch Import ====================


@router.post(
    "/discovery/batches",
    response_model=ImportBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create import batch",
    description="Create a batch import job for bulk discovery items (e.g., Cellebrite export).",
)
async def create_import_batch(
    batch: ImportBatchCreate,
    db: Session = Depends(get_db),
):
    """
    Create an import batch.

    Args:
        batch: Batch creation data
        db: Database session

    Returns:
        ImportBatchResponse: Created batch
    """
    logger.info(f"Creating import batch for case {batch.case_id}, source: {batch.source_type}")

    # Create batch record
    import_batch = ImportBatch(
        case_id=batch.case_id,
        source_type=batch.source_type,
        import_path=batch.import_path,
        total_items=batch.total_items,
        processed_items=0,
        status=ImportStatus.PENDING,
    )

    db.add(import_batch)
    db.commit()
    db.refresh(import_batch)

    # TODO: Queue batch processing job

    return ImportBatchResponse.from_orm_with_progress(import_batch)


@router.get(
    "/discovery/batches/{batch_id}",
    response_model=ImportBatchResponse,
    summary="Get import batch status",
    description="Get the status and progress of a batch import.",
)
async def get_import_batch(
    batch_id: int,
    db: Session = Depends(get_db),
):
    """
    Get import batch by ID.

    Args:
        batch_id: Batch ID
        db: Database session

    Returns:
        ImportBatchResponse: Batch status
    """
    logger.info(f"Getting import batch {batch_id}")

    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()

    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Import batch {batch_id} not found",
        )

    return ImportBatchResponse.from_orm_with_progress(batch)


@router.get(
    "/discovery/batches",
    response_model=ImportBatchListResponse,
    summary="List import batches",
    description="List all import batches for a case.",
)
async def list_import_batches(
    case_id: int = Query(..., description="Case ID"),
    db: Session = Depends(get_db),
):
    """
    List import batches for a case.

    Args:
        case_id: Case ID
        db: Database session

    Returns:
        ImportBatchListResponse: List of batches
    """
    logger.info(f"Listing import batches for case {case_id}")

    batches = db.query(ImportBatch).filter(
        ImportBatch.case_id == case_id
    ).order_by(ImportBatch.created_at.desc()).all()

    batch_responses = [ImportBatchResponse.from_orm_with_progress(b) for b in batches]

    return ImportBatchListResponse(
        batches=batch_responses,
        total=len(batches),
    )


# ==================== Categories ====================


@router.get(
    "/discovery/categories",
    response_model=List[CategoryResponse],
    summary="List categories",
    description="Get all available discovery item categories.",
)
async def list_categories(
    type: Optional[CategoryType] = Query(None, description="Filter by category type"),
    db: Session = Depends(get_db),
):
    """
    List all categories.

    Args:
        type: Filter by category type
        db: Database session

    Returns:
        List[CategoryResponse]: List of categories
    """
    logger.info("Listing categories")

    query = db.query(Category)

    if type:
        query = query.filter(Category.type == type)

    categories = query.order_by(Category.name).all()

    return categories


@router.post(
    "/discovery/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create category",
    description="Create a new category for classifying discovery items.",
)
async def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new category.

    Args:
        category: Category data
        db: Database session

    Returns:
        CategoryResponse: Created category
    """
    logger.info(f"Creating category '{category.name}'")

    # Check if category already exists
    existing = db.query(Category).filter(Category.name == category.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category '{category.name}' already exists",
        )

    # Validate parent category if specified
    if category.parent_category_id:
        parent = db.query(Category).filter(Category.id == category.parent_category_id).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parent category {category.parent_category_id} not found",
            )

    new_category = Category(
        name=category.name,
        type=category.type,
        parent_category_id=category.parent_category_id,
    )

    db.add(new_category)
    db.commit()
    db.refresh(new_category)

    return new_category


@router.post(
    "/discovery/items/{item_id}/categories",
    response_model=CategoryAssociationResponse,
    summary="Add category to item",
    description="Associate a category with a discovery item.",
)
async def add_category_to_item(
    item_id: int,
    request: AddCategoryRequest,
    db: Session = Depends(get_db),
):
    """
    Add a category to a discovery item.

    Args:
        item_id: Discovery item ID
        request: Category association data
        db: Database session

    Returns:
        CategoryAssociationResponse: Confirmation
    """
    logger.info(f"Adding category {request.category_id} to item {item_id}")

    # Verify item exists
    item = db.query(DiscoveryItem).filter(DiscoveryItem.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery item {item_id} not found",
        )

    # Verify category exists
    category = db.query(Category).filter(Category.id == request.category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category {request.category_id} not found",
        )

    # Check if association already exists
    existing = db.query(DiscoveryItemCategory).filter(
        DiscoveryItemCategory.discovery_item_id == item_id,
        DiscoveryItemCategory.category_id == request.category_id,
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category {request.category_id} already associated with item {item_id}",
        )

    # Create association
    association = DiscoveryItemCategory(
        discovery_item_id=item_id,
        category_id=request.category_id,
        confidence_score=request.confidence_score,
        auto_generated=request.auto_generated,
    )

    db.add(association)
    db.commit()

    return CategoryAssociationResponse(
        discovery_item_id=item_id,
        category_id=request.category_id,
        confidence_score=request.confidence_score,
        auto_generated=request.auto_generated,
        message=f"Category '{category.name}' added to item",
    )


@router.delete(
    "/discovery/items/{item_id}/categories/{category_id}",
    summary="Remove category from item",
    description="Remove a category association from a discovery item.",
)
async def remove_category_from_item(
    item_id: int,
    category_id: int,
    db: Session = Depends(get_db),
):
    """
    Remove a category from a discovery item.

    Args:
        item_id: Discovery item ID
        category_id: Category ID
        db: Database session

    Returns:
        dict: Confirmation message
    """
    logger.info(f"Removing category {category_id} from item {item_id}")

    # Find association
    association = db.query(DiscoveryItemCategory).filter(
        DiscoveryItemCategory.discovery_item_id == item_id,
        DiscoveryItemCategory.category_id == category_id,
    ).first()

    if not association:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category {category_id} not associated with item {item_id}",
        )

    db.delete(association)
    db.commit()

    return {"message": f"Category {category_id} removed from item {item_id}"}


# ==================== Search ====================


@router.post(
    "/discovery/search",
    response_model=DiscoverySearchResponse,
    summary="Search discovery items",
    description="Hybrid search across discovery items using VLM captions, video summaries, and metadata.",
)
async def search_discovery_items(
    search_request: DiscoverySearchRequest,
    db: Session = Depends(get_db),
):
    """
    Search discovery items using hybrid search.

    Args:
        search_request: Search parameters
        db: Database session

    Returns:
        DiscoverySearchResponse: Search results
    """
    logger.info(f"Searching discovery items for case {search_request.case_id}: '{search_request.query}'")

    # TODO: Implement hybrid search using:
    # 1. Vector search in Qdrant (VLM captions, video summaries)
    # 2. Full-text search in PostgreSQL (metadata, filenames)
    # 3. Combine and rank results

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Discovery item search not yet implemented",
    )
