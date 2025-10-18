"""Document API endpoints."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.core.database import get_db
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentDeleteResponse,
    PaginatedDocumentListResponse,
)
from app.schemas.search import (
    DocumentContentResponse,
    PageImageResponse,
    PageListResponse,
)
from app.services.document_service import DocumentService
from app.services.page_image_service import PageImageService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/documents",
    response_model=PaginatedDocumentListResponse,
    summary="List all documents with pagination",
    description="Get all documents across all cases with pagination support. "
    "This endpoint efficiently retrieves documents in a single JOIN query to avoid N+1 query problems. "
    "Includes case information (case_name, case_number) for each document.",
)
def list_all_documents(
    page: int = Query(1, ge=1, description="Page number (starting from 1)"),
    page_size: int = Query(50, ge=1, le=100, description="Number of items per page (max 100)"),
    case_gid: Optional[str] = Query(None, description="Optional case GID to filter documents"),
    db: Session = Depends(get_db),
):
    """
    List all documents with pagination.

    Args:
        page: Page number (starting from 1)
        page_size: Number of items per page (max 100)
        case_gid: Optional case GID to filter documents
        db: Database session

    Returns:
        PaginatedDocumentListResponse: Paginated list of documents with case metadata
    """
    logger.info(f"Listing all documents: page={page}, page_size={page_size}, case_gid={case_gid}")

    # Get documents with case information using efficient JOIN
    documents, total = DocumentService.list_all_documents(
        page=page,
        page_size=page_size,
        case_gid=case_gid,
        db=db
    )

    return PaginatedDocumentListResponse(
        documents=documents,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/cases/{case_gid}/documents",
    response_model=List[DocumentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload documents to a case",
    description="Upload one or more documents to a case. Files are stored in MinIO and processing is queued.",
)
async def upload_documents(
    case_gid: str,
    files: List[UploadFile] = File(..., description="List of files to upload"),
    db: Session = Depends(get_db),
):
    """
    Upload documents to a case.

    Args:
        case_gid: GID of the case to upload documents to
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

    logger.info(f"Uploading {len(files)} documents to case {case_gid}")

    documents = await DocumentService.upload_documents(
        case_gid=case_gid,
        files=files,
        db=db,
    )

    return documents


@router.get(
    "/cases/{case_gid}/documents",
    response_model=DocumentListResponse,
    summary="List documents in a case",
    description="Get all documents associated with a case.",
)
def list_case_documents(
    case_gid: str,
    db: Session = Depends(get_db),
):
    """
    List all documents for a case.

    Args:
        case_gid: GID of the case
        db: Database session

    Returns:
        DocumentListResponse: List of documents and total count
    """
    logger.info(f"Listing documents for case {case_gid}")

    documents = DocumentService.list_case_documents(case_gid=case_gid, db=db)

    # Convert Document models to DocumentResponse schemas with case_gid
    document_responses = [
        DocumentResponse(
            gid=doc.gid,
            case_gid=case_gid,
            filename=doc.filename,
            file_path=doc.file_path,
            mime_type=doc.mime_type,
            size=doc.size,
            status=doc.status,
            meta_data=doc.meta_data,
            uploaded_at=doc.uploaded_at,
        )
        for doc in documents
    ]

    return DocumentListResponse(
        documents=document_responses,
        total=len(document_responses),
        case_gid=case_gid,
    )


@router.get(
    "/documents/{document_gid}",
    response_model=DocumentResponse,
    summary="Get document details",
    description="Get detailed information about a specific document.",
)
def get_document(
    document_gid: str,
    db: Session = Depends(get_db),
):
    """
    Get document details by GID.

    Args:
        document_gid: GID of the document
        db: Database session

    Returns:
        DocumentResponse: Document details
    """
    logger.info(f"Getting document {document_gid}")

    document = DocumentService.get_document(document_gid=document_gid, db=db)

    # Get the case to retrieve case_gid
    from app.models.case import Case
    case = db.query(Case).filter(Case.id == document.case_id).first()

    return DocumentResponse(
        gid=document.gid,
        case_gid=case.gid if case else None,
        filename=document.filename,
        file_path=document.file_path,
        mime_type=document.mime_type,
        size=document.size,
        status=document.status,
        meta_data=document.meta_data,
        uploaded_at=document.uploaded_at,
    )


@router.get(
    "/documents/{document_gid}/download",
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
    document_gid: str,
    db: Session = Depends(get_db),
):
    """
    Download a document file.

    Args:
        document_gid: GID of the document
        db: Database session

    Returns:
        StreamingResponse: File content as streaming response
    """
    logger.info(f"Downloading document {document_gid}")

    content, filename, content_type = DocumentService.download_document(
        document_gid=document_gid, db=db
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


@router.get(
    "/documents/{document_gid}/content",
    response_model=DocumentContentResponse,
    summary="Get document content with bboxes",
    description="Get the parsed content of a document including text, pages, and bounding boxes for visual highlighting.",
)
def get_document_content(
    document_gid: str,
    include_images: bool = False,
    db: Session = Depends(get_db),
):
    """
    Get document content with bounding boxes.

    Args:
        document_gid: GID of the document
        include_images: Whether to include presigned URLs for page images
        db: Database session

    Returns:
        DocumentContentResponse: Document content with text, pages, and bboxes
    """
    logger.info(f"Getting content for document {document_gid} (include_images={include_images})")

    content = DocumentService.get_document_content(document_gid=document_gid, db=db)

    # Add page image URLs if requested
    if include_images and content.get("total_pages", 0) > 0:
        document = DocumentService.get_document(document_gid=document_gid, db=db)

        try:
            page_images = PageImageService.get_all_page_image_urls(
                case_gid=document.case_gid,
                document_gid=document_gid,
                page_count=content["total_pages"],
            )

            # Add image URLs to pages
            for page in content.get("pages", []):
                page_num = page.get("page_number", 0)
                if page_num > 0 and page_num <= len(page_images):
                    page["image_url"] = page_images[page_num - 1].get("image_url")

        except Exception as e:
            logger.warning(f"Failed to get page images for document {document_gid}: {e}")

    return content


@router.get(
    "/documents/{document_gid}/pages/{page_num}",
    response_model=PageImageResponse,
    summary="Get page image URL",
    description="Get a presigned URL for a specific page image.",
)
def get_document_page(
    document_gid: str,
    page_num: int,
    expires_in: int = 3600,
    db: Session = Depends(get_db),
):
    """
    Get page image URL.

    Args:
        document_gid: GID of the document
        page_num: Page number (1-indexed)
        expires_in: URL expiration time in seconds (default: 3600)
        db: Database session

    Returns:
        PageImageResponse: Page image URL and metadata
    """
    logger.info(f"Getting page {page_num} image for document {document_gid}")

    # Get document to retrieve case_gid
    document = DocumentService.get_document(document_gid=document_gid, db=db)

    try:
        image_url = PageImageService.get_page_image_url(
            case_gid=document.case_gid,
            document_gid=document_gid,
            page_num=page_num,
            expires_in_seconds=expires_in,
        )

        return PageImageResponse(
            page_number=page_num,
            image_url=image_url,
            document_gid=document_gid,
            expires_in=expires_in,
        )

    except Exception as e:
        logger.error(f"Error getting page image: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Page image not found: {str(e)}",
        )


@router.get(
    "/documents/{document_gid}/pages",
    response_model=PageListResponse,
    summary="List all page images",
    description="Get presigned URLs for all page images in a document.",
)
def list_document_pages(
    document_gid: str,
    expires_in: int = 3600,
    db: Session = Depends(get_db),
):
    """
    List all page images for a document.

    Args:
        document_gid: GID of the document
        expires_in: URL expiration time in seconds (default: 3600)
        db: Database session

    Returns:
        PageListResponse: List of page image URLs
    """
    logger.info(f"Listing page images for document {document_gid}")

    # Get document
    document = DocumentService.get_document(document_gid=document_gid, db=db)

    # Get page count from metadata
    page_count = document.meta_data.get("page_count", 0) if document.meta_data else 0

    if page_count == 0:
        logger.warning(f"No page count metadata for document {document_gid}")
        return PageListResponse(
            document_gid=document_gid,
            total_pages=0,
            pages=[],
        )

    try:
        pages = PageImageService.get_all_page_image_urls(
            case_gid=document.case_gid,
            document_gid=document_gid,
            page_count=page_count,
            expires_in_seconds=expires_in,
        )

        return PageListResponse(
            document_gid=document_gid,
            total_pages=page_count,
            pages=pages,
        )

    except Exception as e:
        logger.error(f"Error listing page images: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list page images: {str(e)}",
        )


@router.delete(
    "/documents/{document_gid}",
    response_model=DocumentDeleteResponse,
    summary="Delete a document",
    description="Delete a document from both storage and database. This action cannot be undone.",
)
def delete_document(
    document_gid: str,
    db: Session = Depends(get_db),
):
    """
    Delete a document.

    Args:
        document_gid: GID of the document
        db: Database session

    Returns:
        DocumentDeleteResponse: Deletion confirmation
    """
    logger.info(f"Deleting document {document_gid}")

    document = DocumentService.delete_document(document_gid=document_gid, db=db)

    return DocumentDeleteResponse(
        gid=document.gid,
        filename=document.filename,
        message=f"Document '{document.filename}' deleted successfully",
    )
