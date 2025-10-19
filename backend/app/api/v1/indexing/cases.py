"""Case-level indexing endpoints for Qdrant vector search."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.services.indexing.core import get_indexing_service, IndexingService
from app.models.case import Case
from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


# Response schemas
class IndexCaseResponse(BaseModel):
    """Response schema for case indexing operations."""

    case_id: int = Field(..., description="Case ID")
    case_number: Optional[str] = Field(None, description="Case number")
    case_name: Optional[str] = Field(None, description="Case name")
    total_documents: int = Field(..., description="Total documents in case")
    successful_documents: int = Field(..., description="Successfully indexed documents")
    failed_documents: int = Field(0, description="Failed documents")
    total_chunks_indexed: int = Field(..., description="Total chunks indexed")
    total_chunks_failed: int = Field(0, description="Total chunks failed")
    timestamp: str = Field(..., description="Timestamp of operation")
    message: Optional[str] = Field(None, description="Additional message")

    class Config:
        json_schema_extra = {
            "example": {
                "case_id": 7,
                "case_number": "CV-2024-001234",
                "case_name": "Smith v. Johnson",
                "total_documents": 15,
                "successful_documents": 15,
                "failed_documents": 0,
                "total_chunks_indexed": 2340,
                "total_chunks_failed": 0,
                "timestamp": "2025-10-09T12:30:00.000000",
            }
        }


class DeleteResponse(BaseModel):
    """Response schema for deletion operations."""

    deleted: bool = Field(..., description="Whether deletion was successful")
    timestamp: str = Field(..., description="Timestamp of operation")
    document_id: Optional[int] = Field(None, description="Document ID (if applicable)")
    case_id: Optional[int] = Field(None, description="Case ID (if applicable)")
    message: Optional[str] = Field(None, description="Additional message")

    class Config:
        json_schema_extra = {
            "example": {
                "deleted": True,
                "timestamp": "2025-10-09T12:30:00.000000",
                "case_id": 7,
            }
        }


# Endpoints
@router.post(
    "/case/{case_gid}",
    response_model=IndexCaseResponse,
    status_code=status.HTTP_200_OK,
    summary="Reindex an entire case",
    description="Index or reindex all documents in a case. "
                "This will process all documents and their chunks, "
                "generating embeddings and updating the vector index.",
)
async def reindex_case(
    case_gid: str = Path(..., description="GID of the case to index"),
    batch_size: int = Query(100, ge=1, le=1000, description="Batch size for uploading points"),
    db: Session = Depends(get_db),
    indexing_service: IndexingService = Depends(get_indexing_service),
):
    """
    Reindex all documents in a case.

    This endpoint will:
    1. Retrieve all documents for the case
    2. Index each document sequentially
    3. Generate embeddings for all chunks
    4. Upsert all points to Qdrant collection

    For large cases, this may take significant time. Consider using
    async task processing for production environments.

    Args:
        case_gid: GID of the case to index
        batch_size: Number of points to upload per batch (default: 100)
        db: Database session (injected)
        indexing_service: Indexing service instance (injected)

    Returns:
        IndexCaseResponse with case indexing statistics

    Raises:
        HTTPException 404: If case not found
        HTTPException 500: If indexing fails
    """
    logger.info(f"Reindex request for case {case_gid}")

    try:
        # Check if case exists
        case = db.query(Case).filter(Case.gid == case_gid).first()
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_gid} not found",
            )

        # Index the case
        result = indexing_service.index_case(
            case_gid=case_gid,
            db=db,
            batch_size=batch_size,
        )

        logger.info(f"Successfully indexed case {case_gid}: {result}")
        return IndexCaseResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error indexing case {case_gid}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to index case: {str(e)}",
        )


@router.delete(
    "/case/{case_gid}",
    response_model=DeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove case from index",
    description="Delete all documents and chunks of a case from the Qdrant index. "
                "This does not delete the case or documents from the database, "
                "only from the vector index.",
)
async def delete_case_from_index(
    case_gid: str = Path(..., description="GID of the case to remove from index"),
    indexing_service: IndexingService = Depends(get_indexing_service),
):
    """
    Remove all documents of a case from the vector index.

    This endpoint deletes all vector embeddings for all chunks of all documents
    in the case from Qdrant. The case, documents, and chunks remain in the
    PostgreSQL database.

    Args:
        case_gid: GID of the case to remove
        indexing_service: Indexing service instance (injected)

    Returns:
        DeleteResponse with deletion status

    Raises:
        HTTPException 500: If deletion fails
    """
    logger.info(f"Delete request for case {case_gid} from index")

    try:
        # Delete from index
        result = indexing_service.delete_case_from_index(case_gid=case_gid)

        logger.info(f"Successfully deleted case {case_gid} from index")
        return DeleteResponse(**result)

    except Exception as e:
        logger.error(f"Error deleting case {case_gid} from index: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete case from index: {str(e)}",
        )
