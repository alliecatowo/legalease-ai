"""
Search API endpoints for hybrid vector and keyword search.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional

from app.schemas.search import (
    HybridSearchRequest,
    HybridSearchResponse,
    SearchQuery,
)
from app.services.search_service import get_search_engine

router = APIRouter()


@router.get("/")
async def search_documents(
    q: str = Query(..., description="Search query"),
    case_ids: Optional[List[int]] = Query(None, description="Filter by case IDs"),
    limit: int = Query(10, ge=1, le=100, description="Number of results to return"),
):
    """
    Simple search endpoint using hybrid search.

    This endpoint provides a simplified interface for quick searches.
    For more advanced options, use the /hybrid endpoint.

    Args:
        q: Search query string
        case_ids: Optional list of case IDs to filter results
        limit: Maximum number of results to return

    Returns:
        Search results with scores and metadata
    """
    try:
        # Create search request
        request = HybridSearchRequest(
            query=q,
            case_ids=case_ids,
            top_k=limit,
            use_bm25=True,
            use_dense=True,
            fusion_method="rrf",
        )

        # Execute search
        search_engine = get_search_engine()
        response = search_engine.search(request)

        # Return simplified response
        return {
            "query": q,
            "results": [
                {
                    "id": r.id,
                    "score": r.score,
                    "text": r.text,
                    "metadata": r.metadata,
                    "highlights": r.highlights,
                }
                for r in response.results
            ],
            "total": response.total_results,
            "limit": limit,
            "search_time_ms": response.search_metadata.get("search_time_ms"),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@router.post("/hybrid", response_model=HybridSearchResponse)
async def hybrid_search(request: HybridSearchRequest):
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
        search_engine = get_search_engine()
        response = search_engine.search(request)
        return response

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
