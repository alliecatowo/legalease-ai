"""
API v2 routes for evidence management and search.

This module provides FastAPI routes for:
- Hybrid search across evidence (documents, transcripts, communications)
- Processing and indexing evidence
- Retrieving evidence metadata and details
"""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status

from app.api.v2.schemas.evidence import (
    SearchEvidenceRequest,
    SearchEvidenceResponse,
    SearchResultSchema,
    ProcessEvidenceRequest,
    ProcessEvidenceResponse,
    DocumentDetailResponse,
    TranscriptDetailResponse,
    CommunicationDetailResponse,
)
from app.shared.types.enums import EvidenceType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evidence", tags=["evidence"])


# Dependency injection functions (to be implemented)
async def get_search_evidence_handler():
    """
    Get SearchEvidenceQueryHandler instance.

    This will be implemented to return the actual handler from the application layer.
    For now, raises NotImplementedError.
    """
    raise NotImplementedError("SearchEvidenceQueryHandler not yet implemented")


async def get_process_evidence_handler():
    """
    Get ProcessEvidenceCommandHandler instance.

    This will be implemented to return the actual handler from the application layer.
    For now, raises NotImplementedError.
    """
    raise NotImplementedError("ProcessEvidenceCommandHandler not yet implemented")


async def get_evidence_service():
    """
    Get EvidenceService instance for retrieving evidence details.

    This will be implemented to return the actual service from the domain layer.
    For now, raises NotImplementedError.
    """
    raise NotImplementedError("EvidenceService not yet implemented")


@router.post("/search", response_model=SearchEvidenceResponse)
async def search_evidence(
    request: SearchEvidenceRequest,
    query_handler=Depends(get_search_evidence_handler),
):
    """
    Hybrid search across all evidence types (documents, transcripts, communications).

    Combines BM25 keyword search with semantic vector search using Reciprocal Rank Fusion.

    Args:
        request: Search request with query and filters
        query_handler: SearchEvidenceQueryHandler from dependency injection

    Returns:
        SearchEvidenceResponse with ranked results

    Example:
        POST /api/v2/evidence/search
        {
            "query": "contract breach damages",
            "case_ids": ["123e4567-e89b-12d3-a456-426614174000"],
            "evidence_types": ["DOCUMENT", "TRANSCRIPT"],
            "top_k": 20,
            "score_threshold": 0.3,
            "search_mode": "HYBRID"
        }
    """
    try:
        logger.info(f"Evidence search: query='{request.query}', mode={request.search_mode}")

        # Create application layer query
        from app.application.queries.search_evidence import SearchEvidenceQuery

        query = SearchEvidenceQuery(
            query=request.query,
            case_ids=request.case_ids,
            evidence_types=request.evidence_types,
            chunk_types=request.chunk_types,
            speaker_filter=request.speaker_filter,
            date_range=request.date_range,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            search_mode=request.search_mode,
        )

        # Execute query through handler
        result = await query_handler.handle(query)

        # Convert DTOs to response schemas
        return SearchEvidenceResponse(
            results=[SearchResultSchema.from_dto(r) for r in result.results],
            total_found=result.total_found,
            search_metadata=result.search_metadata,
        )

    except ValueError as e:
        logger.error(f"Validation error in evidence search: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error in evidence search: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search error: {str(e)}",
        )


@router.get("/search", response_model=SearchEvidenceResponse)
async def search_evidence_simple(
    q: str = Query(..., min_length=2, description="Search query"),
    case_ids: Optional[List[UUID]] = Query(None, description="Filter by case IDs"),
    evidence_types: Optional[List[str]] = Query(None, description="Filter by evidence types"),
    chunk_types: Optional[List[str]] = Query(None, description="Filter by chunk types"),
    speaker_filter: Optional[List[str]] = Query(None, description="Filter by speaker names"),
    top_k: int = Query(20, ge=1, le=100, description="Maximum results"),
    score_threshold: float = Query(0.3, ge=0.0, le=1.0, description="Minimum score"),
    search_mode: str = Query("HYBRID", description="HYBRID, KEYWORD_ONLY, or SEMANTIC_ONLY"),
    query_handler=Depends(get_search_evidence_handler),
):
    """
    Simple GET-based search endpoint with query parameters.

    This is a convenience endpoint for simple searches that can be bookmarked or linked.
    For advanced searches with complex filters, use the POST endpoint.

    Args:
        q: Search query text
        case_ids: Optional case ID filters
        evidence_types: Optional evidence type filters
        chunk_types: Optional chunk type filters
        speaker_filter: Optional speaker name filters
        top_k: Maximum number of results
        score_threshold: Minimum relevance score
        search_mode: Search mode (HYBRID, KEYWORD_ONLY, SEMANTIC_ONLY)
        query_handler: SearchEvidenceQueryHandler from dependency injection

    Returns:
        SearchEvidenceResponse with ranked results

    Example:
        GET /api/v2/evidence/search?q=contract%20breach&top_k=10
    """
    try:
        logger.info(f"Simple evidence search: query='{q}'")

        # Convert string types to enums
        evidence_type_enums = None
        if evidence_types:
            evidence_type_enums = [EvidenceType(et) for et in evidence_types]

        from app.application.queries.search_evidence import SearchEvidenceQuery
        from app.shared.types.enums import ChunkType

        chunk_type_enums = None
        if chunk_types:
            chunk_type_enums = [ChunkType(ct) for ct in chunk_types]

        query = SearchEvidenceQuery(
            query=q,
            case_ids=case_ids,
            evidence_types=evidence_type_enums,
            chunk_types=chunk_type_enums,
            speaker_filter=speaker_filter,
            date_range=None,
            top_k=top_k,
            score_threshold=score_threshold,
            search_mode=search_mode,
        )

        result = await query_handler.handle(query)

        return SearchEvidenceResponse(
            results=[SearchResultSchema.from_dto(r) for r in result.results],
            total_found=result.total_found,
            search_metadata=result.search_metadata,
        )

    except ValueError as e:
        logger.error(f"Validation error in simple search: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error in simple search: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search error: {str(e)}",
        )


@router.post("/process", status_code=status.HTTP_202_ACCEPTED, response_model=ProcessEvidenceResponse)
async def process_evidence(
    request: ProcessEvidenceRequest,
    command_handler=Depends(get_process_evidence_handler),
):
    """
    Process and index new evidence.

    Triggers async indexing pipeline (Haystack) that writes to Qdrant + OpenSearch.
    Returns immediately with 202 Accepted status.

    Args:
        request: Processing request with evidence ID and type
        command_handler: ProcessEvidenceCommandHandler from dependency injection

    Returns:
        ProcessEvidenceResponse with processing status

    Example:
        POST /api/v2/evidence/process
        {
            "evidence_id": "123e4567-e89b-12d3-a456-426614174000",
            "evidence_type": "DOCUMENT",
            "force_reindex": false
        }
    """
    try:
        logger.info(f"Processing evidence: id={request.evidence_id}, type={request.evidence_type}")

        from app.application.commands.process_evidence import ProcessEvidenceCommand

        command = ProcessEvidenceCommand(
            evidence_id=request.evidence_id,
            evidence_type=request.evidence_type,
            force_reindex=request.force_reindex,
        )

        result = await command_handler.handle(command)

        return ProcessEvidenceResponse(
            message="Evidence processing started",
            evidence_id=request.evidence_id,
            chunks_indexed=result.chunks_indexed,
        )

    except ValueError as e:
        logger.error(f"Validation error in evidence processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error processing evidence: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing error: {str(e)}",
        )


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document_details(
    document_id: UUID,
    evidence_service=Depends(get_evidence_service),
):
    """
    Get detailed document information.

    Args:
        document_id: Document UUID
        evidence_service: EvidenceService from dependency injection

    Returns:
        DocumentDetailResponse with full document metadata

    Example:
        GET /api/v2/evidence/documents/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        logger.info(f"Getting document details: id={document_id}")

        document = await evidence_service.get_document(document_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found",
            )

        return DocumentDetailResponse(
            id=document.id,
            filename=document.filename,
            file_path=document.file_path,
            mime_type=document.mime_type,
            size=document.size,
            page_count=document.metadata.get("page_count"),
            uploaded_at=document.uploaded_at,
            processed_at=document.metadata.get("processed_at"),
            status=document.status,
            metadata=document.metadata,
            case_id=document.case_id,
            chunk_count=document.metadata.get("chunk_count"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document details: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving document: {str(e)}",
        )


@router.get("/transcripts/{transcript_id}", response_model=TranscriptDetailResponse)
async def get_transcript_details(
    transcript_id: UUID,
    evidence_service=Depends(get_evidence_service),
):
    """
    Get detailed transcript information.

    Args:
        transcript_id: Transcript UUID
        evidence_service: EvidenceService from dependency injection

    Returns:
        TranscriptDetailResponse with full transcript metadata

    Example:
        GET /api/v2/evidence/transcripts/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        logger.info(f"Getting transcript details: id={transcript_id}")

        transcript = await evidence_service.get_transcript(transcript_id)

        if not transcript:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transcript {transcript_id} not found",
            )

        return TranscriptDetailResponse(
            id=transcript.id,
            filename=transcript.filename,
            audio_file_path=transcript.audio_file_path,
            transcript_file_path=transcript.transcript_file_path,
            duration_seconds=transcript.metadata.get("duration_seconds"),
            uploaded_at=transcript.uploaded_at,
            transcribed_at=transcript.metadata.get("transcribed_at"),
            status=transcript.status,
            metadata=transcript.metadata,
            case_id=transcript.case_id,
            segment_count=transcript.metadata.get("segment_count"),
            speaker_count=transcript.metadata.get("speaker_count"),
            speakers=transcript.metadata.get("speakers", []),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transcript details: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving transcript: {str(e)}",
        )


@router.get("/communications/{communication_id}", response_model=CommunicationDetailResponse)
async def get_communication_details(
    communication_id: UUID,
    evidence_service=Depends(get_evidence_service),
):
    """
    Get detailed communication (email/message) information.

    Args:
        communication_id: Communication UUID
        evidence_service: EvidenceService from dependency injection

    Returns:
        CommunicationDetailResponse with full communication metadata

    Example:
        GET /api/v2/evidence/communications/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        logger.info(f"Getting communication details: id={communication_id}")

        communication = await evidence_service.get_communication(communication_id)

        if not communication:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Communication {communication_id} not found",
            )

        return CommunicationDetailResponse(
            id=communication.id,
            subject=communication.subject,
            sender=communication.sender,
            recipients=communication.recipients,
            cc=communication.cc,
            bcc=communication.bcc,
            sent_at=communication.sent_at,
            received_at=communication.received_at,
            body=communication.body,
            attachments=communication.attachments,
            metadata=communication.metadata,
            case_id=communication.case_id,
            thread_id=communication.thread_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting communication details: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving communication: {str(e)}",
        )
