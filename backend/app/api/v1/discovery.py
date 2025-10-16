"""Discovery item API endpoints."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Query, Form
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

logger = logging.getLogger(__name__)

router = APIRouter()


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
