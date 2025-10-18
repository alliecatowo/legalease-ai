"""
Search API endpoints for hybrid vector and keyword search.
"""
from typing import List, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_active_team
from app.core.database import get_db
from app.models.case import Case
from app.models.document import Document

from app.schemas.search import (
    HybridSearchRequest,
    HybridSearchResponse,
    SearchQuery,
)
from app.services.search_service import get_search_engine

router = APIRouter()


def _get_team_case_ids(db: Session, team_id) -> Set[int]:
    """Return set of case IDs accessible to the team."""
    rows = db.query(Case.id).filter(Case.team_id == team_id).all()
    return {row[0] for row in rows}


def _sanitize_case_ids(
    db: Session,
    team_id,
    requested: Optional[List[int]],
) -> List[int]:
    """Ensure requested case IDs belong to the active team."""
    allowed = _get_team_case_ids(db, team_id)
    if not allowed:
        return []

    if requested is None:
        return list(allowed)

    requested_set = set(requested)
    if not requested_set.issubset(allowed):
        raise HTTPException(
            status_code=403,
            detail="One or more requested cases are not accessible in the active team.",
        )

    return list(requested_set)


def _sanitize_document_ids(
    db: Session,
    team_id,
    document_ids: Optional[List[int]],
) -> Optional[List[int]]:
    """Ensure requested document IDs belong to the active team."""
    if not document_ids:
        return None

    rows = (
        db.query(Document.id)
        .join(Case, Document.case_id == Case.id)
        .filter(Document.id.in_(document_ids), Case.team_id == team_id)
        .all()
    )
    valid_ids = {row[0] for row in rows}
    requested_set = set(document_ids)

    if not requested_set.issubset(valid_ids):
        raise HTTPException(
            status_code=403,
            detail="One or more requested documents are not accessible in the active team.",
        )

    return list(requested_set)


@router.get("/")
async def search_documents(
    q: str = Query(..., description="Search query"),
    case_ids: Optional[List[int]] = Query(None, description="Filter by case IDs"),
    document_types: Optional[List[str]] = Query(None, description="Filter by document types: 'document', 'transcript', or both"),
    speakers: Optional[List[str]] = Query(None, description="Filter by speaker names (for transcripts only)"),
    limit: int = Query(10, ge=1, le=100, description="Number of results to return"),
    min_score: Optional[float] = Query(
        0.3,
        ge=0.0,
        le=1.0,
        description="Minimum score threshold. Use 0.0 for 'Show More Results' functionality"
    ),
    db: Session = Depends(get_db),
    active_team=Depends(require_active_team),
):
    """
    Simple search endpoint using hybrid search.

    This endpoint provides a simplified interface for quick searches.
    For more advanced options, use the /hybrid endpoint.

    Score Interpretation:
    - 0.85-1.0: Strong keyword matches (exact or near-exact terms)
    - 0.6-0.85: Good semantic matches
    - 0.3-0.6: Weak matches (may still be relevant)
    - Below 0.3: Very weak matches (filtered by default)

    To implement "Show More Results" functionality:
    - Default request: min_score=0.3 (shows high-quality results)
    - "Show More" request: min_score=0.0 (shows all results)

    Args:
        q: Search query string
        case_ids: Optional list of case IDs to filter results
        limit: Maximum number of results to return
        min_score: Minimum relevance score threshold (default: 0.3)

    Returns:
        Search results with normalized scores and metadata
    """
    try:
        sanitized_case_ids = _sanitize_case_ids(db, active_team.id, case_ids)
        if not sanitized_case_ids:
            return {
                "query": q,
                "results": [],
                "total": 0,
                "limit": limit,
                "min_score": min_score,
                "document_types": document_types,
                "speakers": speakers,
                "results_filtered": 0,
                "search_time_ms": 0,
            }

        # Determine chunk types based on document_types filter
        chunk_types = None
        if document_types:
            chunk_types = []
            if 'transcript' in document_types:
                chunk_types.append('transcript_segment')
            if 'document' in document_types:
                # Add standard document chunk types
                chunk_types.extend(['summary', 'section', 'microblock'])

        # Create search request
        request = HybridSearchRequest(
            query=q,
            case_ids=sanitized_case_ids,
            chunk_types=chunk_types,
            top_k=limit,
            score_threshold=min_score,
            use_bm25=True,
            use_dense=True,
            fusion_method="rrf",
        )

        # Execute hybrid search
        search_engine = get_search_engine()
        response = search_engine.search(request)

        # Filter by speaker if specified (post-search filter for transcripts)
        results = response.results
        if speakers:
            results = [
                r for r in results
                if r.metadata.get('speaker') in speakers or r.metadata.get('chunk_type') != 'transcript_segment'
            ]

        # Return simplified response
        return {
            "query": q,
            "results": [
                {
                    "id": r.id,
                    "score": round(r.score, 3),  # Round to 3 decimal places for cleaner display
                    "text": r.text,
                    "metadata": r.metadata,
                    "highlights": r.highlights,
                }
                for r in results
            ],
            "total": len(results),
            "limit": limit,
            "min_score": min_score,
            "document_types": document_types,
            "speakers": speakers,
            "results_filtered": response.search_metadata.get("results_filtered", 0),
            "search_time_ms": response.search_metadata.get("search_time_ms"),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@router.post("/hybrid", response_model=HybridSearchResponse)
async def hybrid_search(
    request: HybridSearchRequest,
    db: Session = Depends(get_db),
    active_team=Depends(require_active_team),
):
    """
    Advanced hybrid search combining BM25 and dense vector search.

    This endpoint provides full control over the hybrid search process:
    - BM25 keyword matching
    - Dense vector semantic search (summary, section, microblock)
    - Reciprocal Rank Fusion (RRF) for result combination
    - Flexible filtering by case, document, chunk type

    Example request:
    ```json
    {
        "query": "contract breach damages",
        "case_ids": [1, 2],
        "top_k": 20,
        "fusion_method": "rrf",
        "rrf_k": 60,
        "use_bm25": true,
        "use_dense": true
    }
    ```

    Args:
        request: HybridSearchRequest with all search parameters

    Returns:
        HybridSearchResponse with ranked results and metadata
    """
    try:
        request.case_ids = _sanitize_case_ids(db, active_team.id, request.case_ids)

        if not request.case_ids:
            return HybridSearchResponse(
                results=[],
                total_results=0,
                query=request.query,
                search_metadata={"reason": "no accessible cases for active team"},
            )

        if request.document_ids:
            request.document_ids = _sanitize_document_ids(
                db,
                active_team.id,
                request.document_ids,
            )

        search_engine = get_search_engine()
        response = search_engine.search(request)
        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@router.post("/keyword")
async def keyword_search(
    query: str = Query(..., description="Search query"),
    case_ids: Optional[List[int]] = Query(None, description="Filter by case IDs"),
    document_ids: Optional[List[int]] = Query(None, description="Filter by document IDs"),
    chunk_types: Optional[List[str]] = Query(None, description="Filter by chunk types"),
    top_k: int = Query(10, ge=1, le=100, description="Number of results"),
    score_threshold: Optional[float] = Query(0.1, ge=0.0, le=1.0, description="Minimum BM25 score threshold"),
    db: Session = Depends(get_db),
    active_team=Depends(require_active_team),
):
    """
    Pure BM25 keyword search (no dense vectors, no fusion, no reranking).

    This endpoint is useful for exact keyword/phrase matching.
    BM25 scores are raw and not normalized.

    Args:
        query: Search query string
        case_ids: Optional case ID filters
        document_ids: Optional document ID filters
        chunk_types: Optional chunk type filters (summary, section, microblock)
        top_k: Number of results to return
        score_threshold: Minimum BM25 score (default: 0.1 for permissive matching)

    Returns:
        Keyword search results with raw BM25 scores
    """
    try:
        # Create request with only BM25
        sanitized_case_ids = _sanitize_case_ids(db, active_team.id, case_ids)

        if not sanitized_case_ids:
            return {
                "query": query,
                "results": [],
                "total": 0,
                "top_k": top_k,
                "score_threshold": score_threshold,
                "chunk_types": chunk_types,
            }

        sanitized_document_ids = _sanitize_document_ids(db, active_team.id, document_ids)

        request = HybridSearchRequest(
            query=query,
            case_ids=sanitized_case_ids,
            document_ids=sanitized_document_ids,
            chunk_types=chunk_types,
            top_k=top_k,
            score_threshold=score_threshold,
            use_bm25=True,  # Only BM25
            use_dense=False,  # Disable dense vectors
            fusion_method="rrf",
        )

        search_engine = get_search_engine()
        # Use keyword-only search method
        search_results = search_engine.search_keyword_only(request)

        # Log scores for debugging
        if search_results:
            print(f"DEBUG: Keyword search returned {len(search_results)} results with scores: {[r['score'] for r in search_results[:5]]}")
        else:
            print(f"DEBUG: Keyword search returned 0 results from Qdrant")

        # Apply score threshold filtering
        filtered_results = [
            r for r in search_results
            if r["score"] >= score_threshold
        ][:top_k]

        # Format results
        formatted_results = []
        for result in filtered_results:
            payload = result.get("payload", {})
            formatted_results.append({
                "id": result["id"],
                "score": result["score"],
                "text": payload.get("text", ""),
                "metadata": {
                    "document_id": payload.get("document_id"),
                    "case_id": payload.get("case_id"),
                    "chunk_type": payload.get("chunk_type"),
                    "page_number": payload.get("page_number"),
                    "position": payload.get("position"),
                    "bboxes": payload.get("bboxes", []),
                    "bm25_score": result.get("bm25_score", 0.0),
                },
            })

        return {
            "query": query,
            "results": formatted_results,
            "total": len(formatted_results),
            "score_threshold": score_threshold,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@router.post("/semantic")
async def semantic_search(
    query: str = Query(..., description="Search query"),
    case_ids: Optional[List[int]] = Query(None, description="Filter by case IDs"),
    document_ids: Optional[List[int]] = Query(None, description="Filter by document IDs"),
    chunk_types: Optional[List[str]] = Query(None, description="Filter by chunk types"),
    top_k: int = Query(10, ge=1, le=100, description="Number of results"),
):
    """
    Pure semantic search using only dense vectors (no BM25).

    This endpoint is useful when you want semantic similarity only,
    without keyword matching.

    Args:
        query: Search query string
        case_ids: Optional case ID filters
        document_ids: Optional document ID filters
        chunk_types: Optional chunk type filters (summary, section, microblock)
        top_k: Number of results to return

    Returns:
        Semantic search results
    """
    try:
        # Create request with only dense vectors
        request = HybridSearchRequest(
            query=query,
            case_ids=case_ids,
            document_ids=document_ids,
            chunk_types=chunk_types,
            top_k=top_k,
            use_bm25=False,  # Disable BM25
            use_dense=True,  # Only dense vectors
            fusion_method="rrf",
        )

        search_engine = get_search_engine()
        response = search_engine.search(request)

        return {
            "query": query,
            "results": [
                {
                    "id": r.id,
                    "score": r.score,
                    "text": r.text,
                    "metadata": r.metadata,
                    "vector_type": r.vector_type,
                }
                for r in response.results
            ],
            "total": response.total_results,
            "search_time_ms": response.search_metadata.get("search_time_ms"),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")
