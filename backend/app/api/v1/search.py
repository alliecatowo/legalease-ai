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
    case_gids: Optional[List[str]] = Query(None, description="Filter by case GIDs"),
    document_types: Optional[List[str]] = Query(None, description="Filter by document types: 'document', 'transcript', or both"),
    speakers: Optional[List[str]] = Query(None, description="Filter by speaker names (for transcripts only)"),
    limit: int = Query(10, ge=1, le=100, description="Number of results to return"),
    min_score: Optional[float] = Query(
        0.3,
        ge=0.0,
        le=1.0,
        description="Minimum score threshold. Use 0.0 for 'Show More Results' functionality"
    ),
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
        case_gids: Optional list of case GIDs to filter results
        limit: Maximum number of results to return
        min_score: Minimum relevance score threshold (default: 0.3)

    Returns:
        Search results with normalized scores and metadata
    """
    try:
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
            case_gids=case_gids,
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
                    "gid": r.gid,  # Use gid not id
                    "score": round(r.score, 3),  # Round to 3 decimal places for cleaner display
                    "text": r.text,
                    "metadata": r.metadata,
                    "highlights": r.highlights,
                    "page_number": r.page_number,
                    "bboxes": r.bboxes,
                    "match_type": r.match_type,
                    "vector_type": r.vector_type,
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


@router.post("/keyword")
async def keyword_search(
    query: str = Query(..., description="Search query"),
    case_gids: Optional[List[str]] = Query(None, description="Filter by case GIDs"),
    document_gids: Optional[List[str]] = Query(None, description="Filter by document GIDs"),
    chunk_types: Optional[List[str]] = Query(None, description="Filter by chunk types"),
    top_k: int = Query(10, ge=1, le=100, description="Number of results"),
    score_threshold: Optional[float] = Query(0.1, ge=0.0, le=1.0, description="Minimum BM25 score threshold"),
):
    """
    Pure BM25 keyword search (no dense vectors, no fusion, no reranking).

    This endpoint is useful for exact keyword/phrase matching.
    BM25 scores are raw and not normalized.

    Args:
        query: Search query string
        case_gids: Optional case GID filters
        document_gids: Optional document GID filters
        chunk_types: Optional chunk type filters (summary, section, microblock)
        top_k: Number of results to return
        score_threshold: Minimum BM25 score (default: 0.1 for permissive matching)

    Returns:
        Keyword search results with raw BM25 scores
    """
    try:
        # Create request with only BM25
        request = HybridSearchRequest(
            query=query,
            case_gids=case_gids,
            document_gids=document_gids,
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
                "gid": result["id"],  # Chunk point ID
                "score": result["score"],
                "text": payload.get("text", ""),
                "metadata": {
                    "document_gid": payload.get("document_gid"),
                    "case_gid": payload.get("case_gid"),
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
    case_gids: Optional[List[str]] = Query(None, description="Filter by case GIDs"),
    document_gids: Optional[List[str]] = Query(None, description="Filter by document GIDs"),
    chunk_types: Optional[List[str]] = Query(None, description="Filter by chunk types"),
    top_k: int = Query(10, ge=1, le=100, description="Number of results"),
):
    """
    Pure semantic search using only dense vectors (no BM25).

    This endpoint is useful when you want semantic similarity only,
    without keyword matching.

    Args:
        query: Search query string
        case_gids: Optional case GID filters
        document_gids: Optional document GID filters
        chunk_types: Optional chunk type filters (summary, section, microblock)
        top_k: Number of results to return

    Returns:
        Semantic search results
    """
    try:
        # Create request with only dense vectors
        request = HybridSearchRequest(
            query=query,
            case_gids=case_gids,
            document_gids=document_gids,
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
                    "gid": r.gid,  # Use gid not id
                    "score": r.score,
                    "text": r.text,
                    "metadata": r.metadata,
                    "vector_type": r.vector_type,
                    "page_number": r.page_number,
                    "bboxes": r.bboxes,
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
