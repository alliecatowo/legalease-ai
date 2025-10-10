"""Document API endpoints."""

import logging
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.core.database import get_db
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentDeleteResponse,
)
from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/cases/{case_id}/documents",
    response_model=List[DocumentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload documents to a case",
    description="Upload one or more documents to a case. Files are stored in MinIO and processing is queued.",
)
async def upload_documents(
    case_id: int,
    files: List[UploadFile] = File(..., description="List of files to upload"),
    db: Session = Depends(get_db),
):
    """
    Upload documents to a case.

    Args:
        case_id: ID of the case to upload documents to
        files: List of files to upload
        db: Database session

    Returns:
        List[DocumentResponse]: List of created document records
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided",
        )

    logger.info(f"Uploading {len(files)} documents to case {case_id}")

    documents = await DocumentService.upload_documents(
        case_id=case_id,
        files=files,
        db=db,
    )

    return documents


@router.get(
    "/cases/{case_id}/documents",
    response_model=DocumentListResponse,
    summary="List documents in a case",
    description="Get all documents associated with a case.",
)
def list_case_documents(
    case_id: int,
    db: Session = Depends(get_db),
):
    """
    List all documents for a case.

    Args:
        case_id: ID of the case
        db: Database session

    Returns:
        DocumentListResponse: List of documents and total count
    """
    logger.info(f"Listing documents for case {case_id}")

    documents = DocumentService.list_case_documents(case_id=case_id, db=db)

    return DocumentListResponse(
        documents=documents,
        total=len(documents),
        case_id=case_id,
    )


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
    description="Get detailed information about a specific document.",
)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    """
    Get document details by ID.

    Args:
        document_id: ID of the document
        db: Database session

    Returns:
        DocumentResponse: Document details
    """
    logger.info(f"Getting document {document_id}")

    document = DocumentService.get_document(document_id=document_id, db=db)

    return document


@router.get(
    "/documents/{document_id}/download",
    summary="Download a document",
    description="Download the actual file content from storage.",
    responses={
        200: {
            "description": "Document file",
            "content": {
                "application/octet-stream": {},
                "application/pdf": {},
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {},
                "text/plain": {},
            },
        }
    },
)
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    """
    Download a document file.

    Args:
        document_id: ID of the document
        db: Database session

    Returns:
        StreamingResponse: File content as streaming response
    """
    logger.info(f"Downloading document {document_id}")

    content, filename, content_type = DocumentService.download_document(
        document_id=document_id, db=db
    )

    # Return as streaming response with proper headers
    return StreamingResponse(
        io.BytesIO(content),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
    )


@router.delete(
    "/documents/{document_id}",
    response_model=DocumentDeleteResponse,
    summary="Delete a document",
    description="Delete a document from both storage and database. This action cannot be undone.",
)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a document.

    Args:
        document_id: ID of the document
        db: Database session

    Returns:
        DocumentDeleteResponse: Deletion confirmation
    """
    logger.info(f"Deleting document {document_id}")

    document = DocumentService.delete_document(document_id=document_id, db=db)

    return DocumentDeleteResponse(
        id=document.id,
        filename=document.filename,
        message=f"Document '{document.filename}' deleted successfully",
    )
