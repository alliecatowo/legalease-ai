"""Discovery item service for managing discovery operations."""

import io
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from minio.error import S3Error

from app.models.discovery_item import (
    DiscoveryItem,
    DiscoveryItemType,
    DiscoveryItemSource,
    DiscoveryItemFormFactor
)
from app.models.visual_content import VisualContent
from app.models.video_summary import VideoSummary
from app.models.category import Category, CategoryType
from app.models.discovery_item_category import DiscoveryItemCategory
from app.models.import_batch import ImportBatch, ImportStatus
from app.models.case import Case
from app.core.minio_client import minio_client
from app.workers.tasks.discovery_processing import process_discovery_photo, process_discovery_video

logger = logging.getLogger(__name__)


class DiscoveryService:
    """Service class for discovery item operations."""

    # Supported file formats for different types
    PHOTO_FORMATS = {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/heic",
        "image/heif",
    }

    VIDEO_FORMATS = {
        "video/mp4",
        "video/mpeg",
        "video/quicktime",
        "video/x-msvideo",
        "video/webm",
        "video/x-matroska",
    }

    @staticmethod
    def _generate_object_name(case_id: int, item_type: DiscoveryItemType, filename: str) -> str:
        """
        Generate a unique object name for MinIO storage.

        Args:
            case_id: ID of the case
            item_type: Type of discovery item
            filename: Original filename

        Returns:
            str: Unique object name in format: cases/{case_id}/discovery/{type}/{uuid}_{filename}
        """
        unique_id = uuid.uuid4().hex[:8]
        # Sanitize filename to prevent path traversal
        safe_filename = filename.replace("/", "_").replace("\\", "_")
        type_folder = item_type.value.lower()
        return f"cases/{case_id}/discovery/{type_folder}/{unique_id}_{safe_filename}"

    @staticmethod
    def _validate_file_type(file: UploadFile, item_type: DiscoveryItemType) -> None:
        """
        Validate file type matches the discovery item type.

        Args:
            file: Uploaded file
            item_type: Expected discovery item type

        Raises:
            HTTPException: If file type doesn't match expected type
        """
        content_type = file.content_type

        if item_type == DiscoveryItemType.PHOTO:
            if content_type not in DiscoveryService.PHOTO_FORMATS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid photo format: {content_type}. Supported formats: jpg, png, gif, webp, heic"
                )
        elif item_type == DiscoveryItemType.VIDEO:
            if content_type not in DiscoveryService.VIDEO_FORMATS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid video format: {content_type}. Supported formats: mp4, mpeg, mov, avi, webm, mkv"
                )

    @staticmethod
    async def upload_discovery_item(
        case_id: int,
        file: UploadFile,
        item_type: DiscoveryItemType,
        source: DiscoveryItemSource,
        form_factor: DiscoveryItemFormFactor,
        metadata: Optional[Dict[str, Any]] = None,
        db: Session = None
    ) -> Tuple[DiscoveryItem, str]:
        """
        Upload a discovery item file and create database record.

        This method:
        1. Validates the case exists
        2. Validates file type matches item type
        3. Uploads file to MinIO
        4. Creates DiscoveryItem database record
        5. Triggers appropriate processing task (photo/video)
        6. Returns item with task_id

        Args:
            case_id: ID of the case
            file: Uploaded file
            item_type: Type of discovery item
            source: Source of the discovery item
            form_factor: Form factor of the item
            metadata: Optional additional metadata
            db: Database session

        Returns:
            Tuple[DiscoveryItem, str]: Created item and Celery task_id

        Raises:
            HTTPException: If validation fails or upload fails
        """
        # Validate case exists
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            logger.error(f"Case {case_id} not found")
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

        # Validate file type
        DiscoveryService._validate_file_type(file, item_type)

        try:
            # Read file content
            content = await file.read()
            file_size = len(content)

            # Generate unique object name
            object_name = DiscoveryService._generate_object_name(
                case_id, item_type, file.filename
            )

            # Upload to MinIO
            logger.info(f"Uploading {file.filename} to MinIO as {object_name}")
            minio_client.upload_file(
                file_data=io.BytesIO(content),
                object_name=object_name,
                content_type=file.content_type,
                length=file_size,
            )

            # Create database record
            discovery_item = DiscoveryItem(
                case_id=case_id,
                type=item_type,
                source=source,
                form_factor=form_factor,
                original_filename=file.filename,
                file_path=object_name,
                item_metadata=metadata or {},
                processed=False,
            )
            db.add(discovery_item)
            db.flush()  # Get the item ID

            logger.info(f"Created discovery item record {discovery_item.id} for {file.filename}")

            # Trigger appropriate processing task
            task_id = None
            if item_type == DiscoveryItemType.PHOTO:
                task = process_discovery_photo.delay(discovery_item.id)
                task_id = task.id
                logger.info(f"Enqueued photo processing task {task_id} for item {discovery_item.id}")
            elif item_type == DiscoveryItemType.VIDEO:
                task = process_discovery_video.delay(discovery_item.id)
                task_id = task.id
                logger.info(f"Enqueued video processing task {task_id} for item {discovery_item.id}")

            # Store task_id in metadata
            if task_id:
                discovery_item.item_metadata["task_id"] = task_id
                discovery_item.item_metadata["file_size"] = file_size
                discovery_item.item_metadata["content_type"] = file.content_type

            # Commit the record
            db.commit()
            db.refresh(discovery_item)

            logger.info(
                f"Successfully uploaded discovery item {discovery_item.id} "
                f"for case {case_id} with task {task_id}"
            )

            return discovery_item, task_id

        except S3Error as e:
            logger.error(f"MinIO error uploading {file.filename}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload {file.filename} to storage: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Error uploading {file.filename}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload {file.filename}: {str(e)}",
            )

    @staticmethod
    def get_discovery_item(item_id: int, db: Session) -> DiscoveryItem:
        """
        Get a discovery item by ID.

        Args:
            item_id: ID of the discovery item
            db: Database session

        Returns:
            DiscoveryItem: Discovery item record

        Raises:
            HTTPException: If item not found
        """
        item = db.query(DiscoveryItem).filter(DiscoveryItem.id == item_id).first()
        if not item:
            logger.error(f"Discovery item {item_id} not found")
            raise HTTPException(
                status_code=404, detail=f"Discovery item {item_id} not found"
            )

        return item

    @staticmethod
    def get_discovery_items(
        case_id: int,
        item_type: Optional[DiscoveryItemType] = None,
        source: Optional[DiscoveryItemSource] = None,
        form_factor: Optional[DiscoveryItemFormFactor] = None,
        processed: Optional[bool] = None,
        min_importance: Optional[float] = None,
        max_importance: Optional[float] = None,
        search_text: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
        db: Session = None
    ) -> Tuple[List[DiscoveryItem], int]:
        """
        List discovery items with filtering and pagination.

        Args:
            case_id: ID of the case
            item_type: Filter by item type
            source: Filter by source
            form_factor: Filter by form factor
            processed: Filter by processed status
            min_importance: Minimum importance score (0.0-1.0)
            max_importance: Maximum importance score (0.0-1.0)
            search_text: Search in captions/summaries
            start_date: Filter items created after this date
            end_date: Filter items created before this date
            skip: Number of items to skip (for pagination)
            limit: Maximum number of items to return
            db: Database session

        Returns:
            Tuple[List[DiscoveryItem], int]: List of items and total count

        Raises:
            HTTPException: If case not found
        """
        # Validate case exists
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            logger.error(f"Case {case_id} not found")
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

        # Build base query
        query = db.query(DiscoveryItem).filter(DiscoveryItem.case_id == case_id)

        # Apply filters
        if item_type:
            query = query.filter(DiscoveryItem.type == item_type)

        if source:
            query = query.filter(DiscoveryItem.source == source)

        if form_factor:
            query = query.filter(DiscoveryItem.form_factor == form_factor)

        if processed is not None:
            query = query.filter(DiscoveryItem.processed == processed)

        if min_importance is not None:
            query = query.filter(DiscoveryItem.importance_score >= min_importance)

        if max_importance is not None:
            query = query.filter(DiscoveryItem.importance_score <= max_importance)

        if start_date:
            query = query.filter(DiscoveryItem.created_at >= start_date)

        if end_date:
            query = query.filter(DiscoveryItem.created_at <= end_date)

        # Text search in visual content captions or video summaries
        if search_text:
            # Join with VisualContent and VideoSummary for text search
            text_filter = or_(
                DiscoveryItem.visual_content.any(
                    VisualContent.vlm_caption.ilike(f"%{search_text}%")
                ),
                DiscoveryItem.video_summary.has(
                    or_(
                        VideoSummary.comprehensive_summary.ilike(f"%{search_text}%"),
                        VideoSummary.visual_summary.ilike(f"%{search_text}%")
                    )
                )
            )
            query = query.filter(text_filter)

        # Get total count before pagination
        total_count = query.count()

        # Apply pagination and ordering (newest first)
        items = query.order_by(desc(DiscoveryItem.created_at)).offset(skip).limit(limit).all()

        logger.info(
            f"Found {total_count} discovery items for case {case_id} "
            f"(returning {len(items)} with skip={skip}, limit={limit})"
        )

        return items, total_count

    @staticmethod
    def get_visual_content(item_id: int, db: Session) -> List[VisualContent]:
        """
        Get VLM analysis results for a discovery item.

        Args:
            item_id: ID of the discovery item
            db: Database session

        Returns:
            List[VisualContent]: List of visual content records (photo has 1, video has multiple frames)

        Raises:
            HTTPException: If item not found
        """
        # Verify item exists
        item = DiscoveryService.get_discovery_item(item_id, db)

        # Get all visual content (ordered by frame number for videos)
        visual_content = (
            db.query(VisualContent)
            .filter(VisualContent.discovery_item_id == item_id)
            .order_by(VisualContent.frame_number.nullsfirst(), VisualContent.timestamp_in_video)
            .all()
        )

        logger.info(
            f"Retrieved {len(visual_content)} visual content records for item {item_id}"
        )

        return visual_content

    @staticmethod
    def get_video_summary(item_id: int, db: Session) -> VideoSummary:
        """
        Get video summary for a discovery item.

        Args:
            item_id: ID of the discovery item
            db: Database session

        Returns:
            VideoSummary: Video summary record

        Raises:
            HTTPException: If item not found or not a video, or summary not available
        """
        # Verify item exists and is a video
        item = DiscoveryService.get_discovery_item(item_id, db)

        if item.type != DiscoveryItemType.VIDEO:
            raise HTTPException(
                status_code=400,
                detail=f"Item {item_id} is not a video (type: {item.type.value})"
            )

        # Get video summary
        summary = (
            db.query(VideoSummary)
            .filter(VideoSummary.discovery_item_id == item_id)
            .first()
        )

        if not summary:
            raise HTTPException(
                status_code=404,
                detail=f"Video summary not found for item {item_id}. "
                       "Video may still be processing."
            )

        logger.info(f"Retrieved video summary {summary.id} for item {item_id}")

        return summary

    @staticmethod
    def download_discovery_item(item_id: int, db: Session) -> Tuple[bytes, str, str]:
        """
        Download a discovery item file from MinIO.

        Args:
            item_id: ID of the discovery item
            db: Database session

        Returns:
            Tuple[bytes, str, str]: (file_content, filename, content_type)

        Raises:
            HTTPException: If item not found or download fails
        """
        # Get item from database
        item = DiscoveryService.get_discovery_item(item_id, db)

        try:
            # Download from MinIO
            logger.info(f"Downloading discovery item {item_id} from MinIO: {item.file_path}")
            content = minio_client.download_file(item.file_path)

            metadata = item.item_metadata or {}
            content_type = metadata.get("content_type", "application/octet-stream")

            return content, item.original_filename, content_type

        except S3Error as e:
            logger.error(f"MinIO error downloading item {item_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download item from storage: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Error downloading item {item_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download item: {str(e)}",
            )

    @staticmethod
    def delete_discovery_item(item_id: int, db: Session) -> DiscoveryItem:
        """
        Delete a discovery item (from both database and MinIO).

        Args:
            item_id: ID of the discovery item
            db: Database session

        Returns:
            DiscoveryItem: Deleted item record

        Raises:
            HTTPException: If item not found or deletion fails
        """
        # Get item from database
        item = DiscoveryService.get_discovery_item(item_id, db)

        try:
            # Delete from MinIO
            logger.info(f"Deleting discovery item {item_id} from MinIO: {item.file_path}")
            minio_client.delete_file(item.file_path)

            # Delete from database (cascade will handle related records)
            db.delete(item)
            db.commit()

            logger.info(f"Successfully deleted discovery item {item_id}")
            return item

        except S3Error as e:
            logger.error(f"MinIO error deleting item {item_id}: {str(e)}")
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete item from storage: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Error deleting item {item_id}: {str(e)}")
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete item: {str(e)}",
            )

    @staticmethod
    def create_import_batch(
        case_id: int,
        source_type: str,
        import_path: str,
        total_items: int = 0,
        db: Session = None
    ) -> ImportBatch:
        """
        Create an import batch record for bulk discovery item imports.

        Args:
            case_id: ID of the case
            source_type: Type of import source (e.g., 'cellebrite', 'prosecutor_package')
            import_path: Path to source data
            total_items: Total number of items to import
            db: Database session

        Returns:
            ImportBatch: Created batch record

        Raises:
            HTTPException: If case not found or creation fails
        """
        # Validate case exists
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            logger.error(f"Case {case_id} not found")
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

        try:
            # Create batch record
            batch = ImportBatch(
                case_id=case_id,
                source_type=source_type,
                import_path=import_path,
                total_items=total_items,
                processed_items=0,
                status=ImportStatus.PENDING,
            )

            db.add(batch)
            db.commit()
            db.refresh(batch)

            logger.info(
                f"Created import batch {batch.id} for case {case_id}: "
                f"{source_type} with {total_items} items"
            )

            return batch

        except Exception as e:
            logger.error(f"Error creating import batch: {str(e)}")
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create import batch: {str(e)}",
            )

    @staticmethod
    def update_import_progress(
        batch_id: int,
        processed_items: int,
        status: Optional[ImportStatus] = None,
        error_log: Optional[str] = None,
        db: Session = None
    ) -> ImportBatch:
        """
        Update import batch progress.

        Args:
            batch_id: ID of the import batch
            processed_items: Number of items processed so far
            status: Optional new status
            error_log: Optional error log to append
            db: Database session

        Returns:
            ImportBatch: Updated batch record

        Raises:
            HTTPException: If batch not found or update fails
        """
        batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
        if not batch:
            logger.error(f"Import batch {batch_id} not found")
            raise HTTPException(
                status_code=404, detail=f"Import batch {batch_id} not found"
            )

        try:
            # Update progress
            batch.processed_items = processed_items

            # Update status if provided
            if status:
                batch.status = status

                # Set completed_at if status is COMPLETED or FAILED
                if status in [ImportStatus.COMPLETED, ImportStatus.FAILED]:
                    batch.completed_at = datetime.utcnow()

            # Append error log if provided
            if error_log:
                existing_log = batch.error_log or ""
                timestamp = datetime.utcnow().isoformat()
                batch.error_log = f"{existing_log}\n[{timestamp}] {error_log}".strip()

            db.commit()
            db.refresh(batch)

            logger.info(
                f"Updated import batch {batch_id}: "
                f"{processed_items}/{batch.total_items} items processed, status={batch.status.value}"
            )

            return batch

        except Exception as e:
            logger.error(f"Error updating import batch {batch_id}: {str(e)}")
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update import batch: {str(e)}",
            )

    @staticmethod
    def get_import_batch_status(batch_id: int, db: Session) -> Dict[str, Any]:
        """
        Get import batch status and progress.

        Args:
            batch_id: ID of the import batch
            db: Database session

        Returns:
            Dict: Batch status information

        Raises:
            HTTPException: If batch not found
        """
        batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
        if not batch:
            logger.error(f"Import batch {batch_id} not found")
            raise HTTPException(
                status_code=404, detail=f"Import batch {batch_id} not found"
            )

        # Calculate progress percentage
        progress_pct = 0.0
        if batch.total_items > 0:
            progress_pct = (batch.processed_items / batch.total_items) * 100

        return {
            "id": batch.id,
            "case_id": batch.case_id,
            "source_type": batch.source_type,
            "status": batch.status.value,
            "total_items": batch.total_items,
            "processed_items": batch.processed_items,
            "progress_percentage": round(progress_pct, 2),
            "created_at": batch.created_at.isoformat(),
            "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
            "error_log": batch.error_log,
        }

    @staticmethod
    def list_import_batches(
        case_id: int,
        status: Optional[ImportStatus] = None,
        db: Session = None
    ) -> List[ImportBatch]:
        """
        List import batches for a case.

        Args:
            case_id: ID of the case
            status: Optional status filter
            db: Database session

        Returns:
            List[ImportBatch]: List of import batches

        Raises:
            HTTPException: If case not found
        """
        # Validate case exists
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            logger.error(f"Case {case_id} not found")
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

        # Build query
        query = db.query(ImportBatch).filter(ImportBatch.case_id == case_id)

        if status:
            query = query.filter(ImportBatch.status == status)

        # Order by created_at descending
        batches = query.order_by(desc(ImportBatch.created_at)).all()

        logger.info(f"Found {len(batches)} import batches for case {case_id}")

        return batches

    @staticmethod
    def add_category_to_item(
        item_id: int,
        category_id: int,
        confidence_score: Optional[float] = None,
        auto_generated: bool = False,
        db: Session = None
    ) -> DiscoveryItemCategory:
        """
        Add a category to a discovery item.

        Args:
            item_id: ID of the discovery item
            category_id: ID of the category
            confidence_score: Optional confidence score (0.0-1.0) for auto-generated
            auto_generated: Whether classification was auto-generated
            db: Database session

        Returns:
            DiscoveryItemCategory: Association record

        Raises:
            HTTPException: If item or category not found, or association fails
        """
        # Verify item exists
        item = DiscoveryService.get_discovery_item(item_id, db)

        # Verify category exists
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            logger.error(f"Category {category_id} not found")
            raise HTTPException(
                status_code=404, detail=f"Category {category_id} not found"
            )

        # Validate confidence score if provided
        if confidence_score is not None and (confidence_score < 0.0 or confidence_score > 1.0):
            raise HTTPException(
                status_code=400,
                detail=f"Confidence score must be between 0.0 and 1.0"
            )

        try:
            # Check if association already exists
            existing = db.query(DiscoveryItemCategory).filter(
                and_(
                    DiscoveryItemCategory.discovery_item_id == item_id,
                    DiscoveryItemCategory.category_id == category_id
                )
            ).first()

            if existing:
                # Update existing association
                existing.confidence_score = confidence_score
                existing.auto_generated = auto_generated
                db.commit()
                db.refresh(existing)

                logger.info(
                    f"Updated category association: item {item_id} -> category {category_id}"
                )

                return existing

            # Create new association
            association = DiscoveryItemCategory(
                discovery_item_id=item_id,
                category_id=category_id,
                confidence_score=confidence_score,
                auto_generated=auto_generated,
            )

            db.add(association)
            db.commit()
            db.refresh(association)

            logger.info(
                f"Added category {category_id} to discovery item {item_id} "
                f"(auto_generated={auto_generated}, confidence={confidence_score})"
            )

            return association

        except Exception as e:
            logger.error(f"Error adding category to item: {str(e)}")
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to add category to item: {str(e)}",
            )

    @staticmethod
    def remove_category_from_item(
        item_id: int,
        category_id: int,
        db: Session = None
    ) -> bool:
        """
        Remove a category from a discovery item.

        Args:
            item_id: ID of the discovery item
            category_id: ID of the category
            db: Database session

        Returns:
            bool: True if removed, False if association didn't exist

        Raises:
            HTTPException: If removal fails
        """
        try:
            # Find association
            association = db.query(DiscoveryItemCategory).filter(
                and_(
                    DiscoveryItemCategory.discovery_item_id == item_id,
                    DiscoveryItemCategory.category_id == category_id
                )
            ).first()

            if not association:
                logger.warning(
                    f"Category association not found: item {item_id} -> category {category_id}"
                )
                return False

            # Delete association
            db.delete(association)
            db.commit()

            logger.info(f"Removed category {category_id} from discovery item {item_id}")

            return True

        except Exception as e:
            logger.error(f"Error removing category from item: {str(e)}")
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to remove category from item: {str(e)}",
            )

    @staticmethod
    def get_item_categories(item_id: int, db: Session) -> List[Dict[str, Any]]:
        """
        Get all categories for a discovery item.

        Args:
            item_id: ID of the discovery item
            db: Database session

        Returns:
            List[Dict]: List of categories with association metadata

        Raises:
            HTTPException: If item not found
        """
        # Verify item exists
        item = DiscoveryService.get_discovery_item(item_id, db)

        # Get all category associations
        associations = (
            db.query(DiscoveryItemCategory, Category)
            .join(Category, DiscoveryItemCategory.category_id == Category.id)
            .filter(DiscoveryItemCategory.discovery_item_id == item_id)
            .all()
        )

        # Build result list
        result = []
        for assoc, category in associations:
            result.append({
                "category_id": category.id,
                "category_name": category.name,
                "category_type": category.type.value,
                "confidence_score": assoc.confidence_score,
                "auto_generated": assoc.auto_generated,
                "added_at": assoc.created_at.isoformat(),
            })

        logger.info(f"Retrieved {len(result)} categories for discovery item {item_id}")

        return result

    @staticmethod
    def create_category(
        name: str,
        category_type: CategoryType,
        parent_category_id: Optional[int] = None,
        db: Session = None
    ) -> Category:
        """
        Create a new category.

        Args:
            name: Category name (must be unique)
            category_type: Type of category
            parent_category_id: Optional parent category ID for hierarchy
            db: Database session

        Returns:
            Category: Created category record

        Raises:
            HTTPException: If category with name already exists or creation fails
        """
        # Check if category with name already exists
        existing = db.query(Category).filter(Category.name == name).first()
        if existing:
            logger.warning(f"Category with name '{name}' already exists")
            raise HTTPException(
                status_code=400,
                detail=f"Category with name '{name}' already exists"
            )

        # Verify parent category exists if provided
        if parent_category_id:
            parent = db.query(Category).filter(Category.id == parent_category_id).first()
            if not parent:
                logger.error(f"Parent category {parent_category_id} not found")
                raise HTTPException(
                    status_code=404,
                    detail=f"Parent category {parent_category_id} not found"
                )

        try:
            # Create category
            category = Category(
                name=name,
                type=category_type,
                parent_category_id=parent_category_id,
            )

            db.add(category)
            db.commit()
            db.refresh(category)

            logger.info(
                f"Created category {category.id}: '{name}' "
                f"(type={category_type.value}, parent={parent_category_id})"
            )

            return category

        except Exception as e:
            logger.error(f"Error creating category: {str(e)}")
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create category: {str(e)}",
            )

    @staticmethod
    def list_categories(
        category_type: Optional[CategoryType] = None,
        parent_category_id: Optional[int] = None,
        db: Session = None
    ) -> List[Category]:
        """
        List categories with optional filtering.

        Args:
            category_type: Filter by category type
            parent_category_id: Filter by parent category (None for root categories)
            db: Database session

        Returns:
            List[Category]: List of categories
        """
        # Build query
        query = db.query(Category)

        if category_type:
            query = query.filter(Category.type == category_type)

        if parent_category_id is not None:
            query = query.filter(Category.parent_category_id == parent_category_id)

        # Order by name
        categories = query.order_by(Category.name).all()

        logger.info(
            f"Found {len(categories)} categories "
            f"(type={category_type}, parent={parent_category_id})"
        )

        return categories

    @staticmethod
    def get_discovery_statistics(case_id: int, db: Session) -> Dict[str, Any]:
        """
        Get statistics for discovery items in a case.

        Args:
            case_id: ID of the case
            db: Database session

        Returns:
            Dict: Statistics including counts by type, source, processing status, etc.

        Raises:
            HTTPException: If case not found
        """
        # Validate case exists
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            logger.error(f"Case {case_id} not found")
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

        # Get total count
        total_items = db.query(DiscoveryItem).filter(
            DiscoveryItem.case_id == case_id
        ).count()

        # Count by type
        type_counts = {}
        for item_type in DiscoveryItemType:
            count = db.query(DiscoveryItem).filter(
                and_(
                    DiscoveryItem.case_id == case_id,
                    DiscoveryItem.type == item_type
                )
            ).count()
            type_counts[item_type.value] = count

        # Count by source
        source_counts = {}
        for source in DiscoveryItemSource:
            count = db.query(DiscoveryItem).filter(
                and_(
                    DiscoveryItem.case_id == case_id,
                    DiscoveryItem.source == source
                )
            ).count()
            source_counts[source.value] = count

        # Count processed vs unprocessed
        processed_count = db.query(DiscoveryItem).filter(
            and_(
                DiscoveryItem.case_id == case_id,
                DiscoveryItem.processed == True
            )
        ).count()

        unprocessed_count = total_items - processed_count

        # Average importance score
        avg_importance = db.query(func.avg(DiscoveryItem.importance_score)).filter(
            and_(
                DiscoveryItem.case_id == case_id,
                DiscoveryItem.importance_score.isnot(None)
            )
        ).scalar()

        return {
            "case_id": case_id,
            "total_items": total_items,
            "processed_items": processed_count,
            "unprocessed_items": unprocessed_count,
            "processing_percentage": round((processed_count / total_items * 100) if total_items > 0 else 0, 2),
            "counts_by_type": type_counts,
            "counts_by_source": source_counts,
            "average_importance_score": round(float(avg_importance), 3) if avg_importance else None,
        }
