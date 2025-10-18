"""
Admin API endpoints for document indexing operations.

This module provides REST API endpoints for managing the Qdrant vector index,
including document and case-level indexing, updates, and deletions.
These endpoints are intended for administrative use.
"""

from typing import List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.indexing_service import get_indexing_service, IndexingService
from app.models.document import Document
from app.models.case import Case
from app.core.qdrant import get_qdrant_client
from qdrant_client.models import Filter, FieldCondition, MatchValue
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# Response schemas
class IndexDocumentResponse(BaseModel):
    """Response schema for document indexing operations."""

    document_id: int = Field(..., description="Document ID")
    case_id: Optional[int] = Field(None, description="Case ID")
    indexed_count: int = Field(..., description="Number of chunks indexed")
    failed_count: int = Field(0, description="Number of chunks that failed")
    total_chunks: Optional[int] = Field(None, description="Total number of chunks")
    timestamp: str = Field(..., description="Timestamp of operation")
    message: Optional[str] = Field(None, description="Additional message")
    failed_chunk_ids: Optional[List[int]] = Field(None, description="IDs of failed chunks")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": 42,
                "case_id": 7,
                "indexed_count": 156,
                "failed_count": 0,
                "total_chunks": 156,
                "timestamp": "2025-10-09T12:30:00.000000",
            }
        }


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
                "document_id": 42,
            }
        }


class BatchIndexRequest(BaseModel):
    """Request schema for batch indexing operations."""

    document_gids: List[str] = Field(..., min_length=1, description="List of document GIDs to index")
    batch_size: int = Field(100, ge=1, le=1000, description="Batch size for uploading points")

    class Config:
        json_schema_extra = {
            "example": {
                "document_gids": ["abc123xyz456", "def789uvw012"],
                "batch_size": 100,
            }
        }


class BatchIndexResponse(BaseModel):
    """Response schema for batch indexing operations."""

    total_documents: int = Field(..., description="Total documents processed")
    successful_documents: int = Field(..., description="Successfully indexed documents")
    failed_documents: int = Field(0, description="Failed documents")
    total_chunks_indexed: int = Field(..., description="Total chunks indexed")
    total_chunks_failed: int = Field(0, description="Total chunks failed")
    timestamp: str = Field(..., description="Timestamp of operation")

    class Config:
        json_schema_extra = {
            "example": {
                "total_documents": 5,
                "successful_documents": 5,
                "failed_documents": 0,
                "total_chunks_indexed": 750,
                "total_chunks_failed": 0,
                "timestamp": "2025-10-09T12:30:00.000000",
            }
        }


# Endpoints
@router.post(
    "/document/{document_gid}",
    response_model=IndexDocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Reindex a document",
    description="Index or reindex all chunks of a specific document into Qdrant. "
                "This will generate embeddings and update the vector index.",
)
async def reindex_document(
    document_gid: str = Path(..., description="GID of the document to index"),
    batch_size: int = Query(100, ge=1, le=1000, description="Batch size for uploading points"),
    db: Session = Depends(get_db),
    indexing_service: IndexingService = Depends(get_indexing_service),
):
    """
    Reindex a single document.

    This endpoint will:
    1. Retrieve all chunks for the document from the database
    2. Generate embeddings for each chunk
    3. Create multi-vector points (summary, section, microblock, BM25)
    4. Upsert points to Qdrant collection

    Args:
        document_gid: GID of the document to index
        batch_size: Number of points to upload per batch (default: 100)
        db: Database session (injected)
        indexing_service: Indexing service instance (injected)

    Returns:
        IndexDocumentResponse with indexing statistics

    Raises:
        HTTPException 404: If document not found
        HTTPException 500: If indexing fails
    """
    logger.info(f"Reindex request for document {document_gid}")

    try:
        # Check if document exists
        document = db.query(Document).filter(Document.gid == document_gid).first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_gid} not found",
            )

        # Index the document
        result = indexing_service.index_document(
            document_gid=document_gid,
            db=db,
            batch_size=batch_size,
        )

        logger.info(f"Successfully indexed document {document_gid}: {result}")
        return IndexDocumentResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error indexing document {document_gid}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to index document: {str(e)}",
        )


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


@router.post(
    "/batch",
    response_model=BatchIndexResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch index multiple documents",
    description="Index multiple documents in a single request. "
                "Useful for bulk indexing operations.",
)
async def batch_index_documents(
    request: BatchIndexRequest = Body(..., description="Batch indexing request"),
    db: Session = Depends(get_db),
    indexing_service: IndexingService = Depends(get_indexing_service),
):
    """
    Index multiple documents in batch.

    This endpoint processes multiple documents sequentially and returns
    aggregated statistics. For very large batches, consider using
    async task processing.

    Args:
        request: BatchIndexRequest with document IDs and batch size
        db: Database session (injected)
        indexing_service: Indexing service instance (injected)

    Returns:
        BatchIndexResponse with aggregated indexing statistics

    Raises:
        HTTPException 500: If batch indexing fails
    """
    logger.info(f"Batch index request for {len(request.document_ids)} documents")

    try:
        # Batch index documents
        result = indexing_service.batch_index(
            documents=request.document_gids,
            db=db,
            batch_size=request.batch_size,
        )

        logger.info(f"Batch indexing completed: {result}")
        return BatchIndexResponse(**result)

    except Exception as e:
        logger.error(f"Error in batch indexing: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch index documents: {str(e)}",
        )


@router.delete(
    "/document/{document_gid}",
    response_model=DeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove document from index",
    description="Delete all chunks of a document from the Qdrant index. "
                "This does not delete the document from the database, "
                "only from the vector index.",
)
async def delete_document_from_index(
    document_gid: str = Path(..., description="GID of the document to remove from index"),
    indexing_service: IndexingService = Depends(get_indexing_service),
):
    """
    Remove a document from the vector index.

    This endpoint deletes all vector embeddings for the document's chunks
    from Qdrant. The document and chunks remain in the PostgreSQL database.

    Args:
        document_gid: GID of the document to remove
        indexing_service: Indexing service instance (injected)

    Returns:
        DeleteResponse with deletion status

    Raises:
        HTTPException 500: If deletion fails
    """
    logger.info(f"Delete request for document {document_gid} from index")

    try:
        # Delete from index
        result = indexing_service.delete_from_index(document_gid=document_gid)

        logger.info(f"Successfully deleted document {document_gid} from index")
        return DeleteResponse(**result)

    except Exception as e:
        logger.error(f"Error deleting document {document_gid} from index: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document from index: {str(e)}",
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


@router.put(
    "/document/{document_gid}",
    response_model=IndexDocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update document index",
    description="Update the index for a document by deleting old entries "
                "and reindexing with current chunks. Useful when document "
                "content has been modified or re-processed.",
)
async def update_document_index(
    document_gid: str = Path(..., description="GID of the document to update"),
    batch_size: int = Query(100, ge=1, le=1000, description="Batch size for uploading points"),
    db: Session = Depends(get_db),
    indexing_service: IndexingService = Depends(get_indexing_service),
):
    """
    Update the vector index for a document.

    This endpoint performs a two-step operation:
    1. Delete all existing vector embeddings for the document
    2. Reindex the document with current chunks

    This is useful when:
    - Document has been re-processed with new chunking
    - Text content has been corrected or modified
    - Embedding model has been updated

    Args:
        document_gid: GID of the document to update
        batch_size: Number of points to upload per batch (default: 100)
        db: Database session (injected)
        indexing_service: Indexing service instance (injected)

    Returns:
        IndexDocumentResponse with update statistics

    Raises:
        HTTPException 404: If document not found
        HTTPException 500: If update fails
    """
    logger.info(f"Update index request for document {document_gid}")

    try:
        # Check if document exists
        document = db.query(Document).filter(Document.gid == document_gid).first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_gid} not found",
            )

        # Update the index
        result = indexing_service.update_index(
            document_gid=document_gid,
            db=db,
            batch_size=batch_size,
        )

        logger.info(f"Successfully updated index for document {document_gid}: {result}")
        return IndexDocumentResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating index for document {document_gid}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update document index: {str(e)}",
        )


@router.get(
    "/debug/chunk-types",
    status_code=status.HTTP_200_OK,
    summary="[DEBUG] Check chunk types in Qdrant",
    description="Debug endpoint to check what chunk_types exist in Qdrant and their counts.",
)
async def debug_chunk_types(
    case_gid: Optional[str] = Query(None, description="Filter by case GID"),
):
    """
    Debug endpoint to check chunk types in Qdrant.

    This endpoint scrolls through points in Qdrant and counts how many
    of each chunk_type exist. Useful for debugging search issues.

    Args:
        case_gid: Optional case GID to filter by

    Returns:
        Dictionary with chunk type statistics
    """
    try:
        from app.core.config import settings

        client = get_qdrant_client()
        collection_name = settings.QDRANT_COLLECTION

        # Build filter if case_gid provided
        scroll_filter = None
        if case_gid:
            scroll_filter = Filter(
                must=[
                    FieldCondition(
                        key="case_gid",
                        match=MatchValue(value=case_gid),
                    )
                ]
            )

        # Scroll through all points and count chunk types
        chunk_type_counts = {}
        offset = None
        batch_size = 100
        total_points = 0

        while True:
            response = client.scroll(
                collection_name=collection_name,
                scroll_filter=scroll_filter,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            points, next_offset = response

            if not points:
                break

            for point in points:
                total_points += 1
                chunk_type = point.payload.get("chunk_type", "MISSING")
                chunk_type_counts[chunk_type] = chunk_type_counts.get(chunk_type, 0) + 1

            if next_offset is None:
                break

            offset = next_offset

        logger.info(f"Debug chunk types: {chunk_type_counts} (total: {total_points}, case_gid: {case_gid})")

        return {
            "total_points": total_points,
            "chunk_type_counts": chunk_type_counts,
            "case_gid_filter": case_gid,
            "collection": collection_name,
        }

    except Exception as e:
        logger.error(f"Error in debug chunk types: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check chunk types: {str(e)}",
        )


@router.get(
    "/debug/transcript-segments",
    status_code=status.HTTP_200_OK,
    summary="[DEBUG] Check transcript segments in Qdrant",
    description="Debug endpoint to check transcript_segment points in Qdrant.",
)
async def debug_transcript_segments(
    case_gid: Optional[str] = Query(None, description="Filter by case GID"),
    limit: int = Query(10, ge=1, le=100, description="Number of samples to return"),
):
    """
    Debug endpoint to check transcript segments in Qdrant.

    Returns sample transcript_segment points from Qdrant to verify
    they're indexed correctly.

    Args:
        case_gid: Optional case GID to filter by
        limit: Number of sample points to return

    Returns:
        Dictionary with transcript segment samples and statistics
    """
    try:
        from app.core.config import settings

        client = get_qdrant_client()
        collection_name = settings.QDRANT_COLLECTION

        # Build filter for transcript segments
        conditions = [
            FieldCondition(
                key="chunk_type",
                match=MatchValue(value="transcript_segment"),
            )
        ]

        if case_gid:
            conditions.append(
                FieldCondition(
                    key="case_gid",
                    match=MatchValue(value=case_gid),
                )
            )

        scroll_filter = Filter(must=conditions)

        # Scroll to get samples
        response = client.scroll(
            collection_name=collection_name,
            scroll_filter=scroll_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        points, _ = response

        # Format samples
        samples = []
        for point in points:
            samples.append({
                "id": str(point.id),
                "transcription_id": point.payload.get("transcription_id"),
                "document_id": point.payload.get("document_id"),
                "case_id": point.payload.get("case_id"),
                "speaker": point.payload.get("speaker"),
                "text_preview": point.payload.get("text", "")[:100] + "..." if point.payload.get("text") else None,
                "start_time": point.payload.get("start_time"),
                "end_time": point.payload.get("end_time"),
            })

        logger.info(f"Debug transcript segments: found {len(samples)} samples (case_gid: {case_gid})")

        return {
            "total_samples": len(samples),
            "case_gid_filter": case_gid,
            "collection": collection_name,
            "samples": samples,
        }

    except Exception as e:
        logger.error(f"Error in debug transcript segments: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check transcript segments: {str(e)}",
        )
