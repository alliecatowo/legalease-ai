"""Case management API endpoints."""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.case import CaseStatus
from app.schemas.case import (
    CaseCreate,
    CaseUpdate,
    CaseResponse,
    CaseListItem,
    CaseListResponse,
    CaseStatusUpdate,
    CaseDeleteResponse,
)
from app.services.case_service import (
    CaseService,
    CaseNotFoundError,
    CaseAlreadyExistsError,
    ResourceCreationError,
)

router = APIRouter()


def get_case_service(db: Session = Depends(get_db)) -> CaseService:
    """
    Dependency to get case service instance.

    Args:
        db: Database session

    Returns:
        CaseService instance
    """
    return CaseService(db)


@router.post(
    "",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new case",
    description="Create a new legal case with associated Qdrant collection and MinIO bucket",
)
async def create_case(
    case_data: CaseCreate,
    case_service: CaseService = Depends(get_case_service),
):
    """
    Create a new case.

    The case is created in STAGING status. Upon creation:
    - A Qdrant collection is created for vector search
    - A MinIO bucket is created for document storage

    Args:
        case_data: Case creation data
        case_service: Case service dependency

    Returns:
        Created case details

    Raises:
        HTTPException: If case_number already exists or resource creation fails
    """
    try:
        case = case_service.create_case(
            name=case_data.name,
            case_number=case_data.case_number,
            client=case_data.client,
            matter_type=case_data.matter_type,
        )
        return case
    except CaseAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ResourceCreationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "",
    response_model=CaseListResponse,
    summary="List all cases",
    description="Get a paginated list of cases with optional status filter",
)
async def list_cases(
    status_filter: Optional[CaseStatus] = Query(None, alias="status", description="Filter by case status"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    case_service: CaseService = Depends(get_case_service),
):
    """
    List cases with pagination and optional filtering.

    Args:
        status_filter: Optional status filter
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        case_service: Case service dependency

    Returns:
        Paginated list of cases
    """
    skip = (page - 1) * page_size
    cases, total = case_service.list_cases(
        status=status_filter,
        skip=skip,
        limit=page_size,
    )

    # Convert to list items with document and transcript counts
    case_items = []
    for case in cases:
        # Count documents and transcripts separately (true decoupling)
        document_count = len(case.documents) if case.documents else 0
        transcript_count = len(case.transcriptions) if hasattr(case, 'transcriptions') and case.transcriptions else 0

        case_item = CaseListItem(
            id=case.id,
            name=case.name,
            case_number=case.case_number,
            client=case.client,
            matter_type=case.matter_type,
            status=case.status,
            created_at=case.created_at,
            updated_at=case.updated_at,
            archived_at=case.archived_at,
            document_count=document_count,
            transcript_count=transcript_count,
        )
        case_items.append(case_item)

    return CaseListResponse(
        cases=case_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{case_id}",
    response_model=CaseResponse,
    summary="Get case details",
    description="Get detailed information about a specific case",
)
async def get_case(
    case_id: int,
    case_service: CaseService = Depends(get_case_service),
):
    """
    Get case by ID.

    Args:
        case_id: Case ID
        case_service: Case service dependency

    Returns:
        Case details including documents

    Raises:
        HTTPException: If case not found
    """
    try:
        case = case_service.get_case(case_id)
        return case
    except CaseNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put(
    "/{case_id}",
    response_model=CaseResponse,
    summary="Update case details",
    description="Update case information (name, case_number, client, matter_type)",
)
async def update_case(
    case_id: int,
    case_data: CaseUpdate,
    case_service: CaseService = Depends(get_case_service),
):
    """
    Update case details.

    Args:
        case_id: Case ID
        case_data: Updated case data
        case_service: Case service dependency

    Returns:
        Updated case details

    Raises:
        HTTPException: If case not found or case_number conflict
    """
    try:
        case = case_service.update_case(
            case_id=case_id,
            name=case_data.name,
            case_number=case_data.case_number,
            client=case_data.client,
            matter_type=case_data.matter_type,
        )
        return case
    except CaseNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except CaseAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.put(
    "/{case_id}/activate",
    response_model=CaseStatusUpdate,
    summary="Activate case",
    description="Change case status to ACTIVE, making it available for processing",
)
async def activate_case(
    case_id: int,
    case_service: CaseService = Depends(get_case_service),
):
    """
    Activate a case (RAGFlow load pattern).

    Changes the case status to ACTIVE, making it available for:
    - Document uploads and processing
    - Vector search queries
    - Active case management

    Args:
        case_id: Case ID
        case_service: Case service dependency

    Returns:
        Status update confirmation

    Raises:
        HTTPException: If case not found
    """
    try:
        case = case_service.activate_case(case_id)
        return CaseStatusUpdate(
            id=case.id,
            case_number=case.case_number,
            status=case.status,
            message=f"Case '{case.case_number}' activated successfully",
        )
    except CaseNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put(
    "/{case_id}/unload",
    response_model=CaseStatusUpdate,
    summary="Unload case",
    description="Change case status to UNLOADED, removing it from active processing",
)
async def unload_case(
    case_id: int,
    case_service: CaseService = Depends(get_case_service),
):
    """
    Unload a case (RAGFlow unload pattern).

    Changes the case status to UNLOADED, which:
    - Removes the case from active processing
    - Preserves all data (documents, vectors, files)
    - Keeps Qdrant collection and MinIO bucket intact
    - Can be reactivated later with /activate

    Args:
        case_id: Case ID
        case_service: Case service dependency

    Returns:
        Status update confirmation

    Raises:
        HTTPException: If case not found
    """
    try:
        case = case_service.unload_case(case_id)
        return CaseStatusUpdate(
            id=case.id,
            case_number=case.case_number,
            status=case.status,
            message=f"Case '{case.case_number}' unloaded successfully",
        )
    except CaseNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete(
    "/{case_id}",
    response_model=CaseDeleteResponse,
    summary="Delete case",
    description="Permanently delete a case and all associated resources",
)
async def delete_case(
    case_id: int,
    case_service: CaseService = Depends(get_case_service),
):
    """
    Permanently delete a case.

    This operation:
    - Deletes the case from the database
    - Deletes all associated documents, chunks, entities (via cascade)
    - Deletes the Qdrant collection
    - Deletes the MinIO bucket and all files

    WARNING: This operation is irreversible.

    Args:
        case_id: Case ID
        case_service: Case service dependency

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: If case not found
    """
    try:
        case = case_service.get_case(case_id)
        case_number = case.case_number
        case_service.delete_case(case_id)

        return CaseDeleteResponse(
            id=case_id,
            case_number=case_number,
            message=f"Case '{case_number}' and all associated resources deleted successfully",
            deleted_at=datetime.utcnow(),
        )
    except CaseNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
