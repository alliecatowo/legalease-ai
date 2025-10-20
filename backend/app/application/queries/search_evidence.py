"""
SearchEvidenceQuery for hybrid search across all evidence types.

This module implements CQRS query pattern for searching evidence using
hybrid retrieval combining keyword and semantic search.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.shared.types.enums import EvidenceType, ChunkType

logger = logging.getLogger(__name__)


@dataclass
class SearchEvidenceQuery:
    """
    Query for hybrid search across all evidence types.

    Combines Qdrant (semantic) and OpenSearch (keyword) results
    for comprehensive evidence retrieval.

    Attributes:
        query: Search query string
        case_ids: Optional filter by case IDs
        evidence_types: Optional filter by evidence types
        chunk_types: Optional filter by chunk types
        speaker_filter: Optional filter by speaker names (for transcripts)
        date_range: Optional (start, end) datetime range filter
        top_k: Maximum results to return
        score_threshold: Minimum similarity/relevance score
        search_mode: HYBRID, KEYWORD_ONLY, or SEMANTIC_ONLY

    Example:
        >>> query = SearchEvidenceQuery(
        ...     query="contract signature date",
        ...     case_ids=[case_uuid],
        ...     evidence_types=[EvidenceType.DOCUMENT],
        ...     top_k=20,
        ...     score_threshold=0.3,
        ...     search_mode="HYBRID",
        ... )
    """

    query: str
    case_ids: Optional[List[UUID]] = None
    evidence_types: Optional[List[EvidenceType]] = None
    chunk_types: Optional[List[ChunkType]] = None
    speaker_filter: Optional[List[str]] = None
    date_range: Optional[tuple[str, str]] = None
    top_k: int = 20
    score_threshold: float = 0.3
    search_mode: str = "HYBRID"

    def __post_init__(self) -> None:
        """Validate query parameters."""
        if not self.query or not self.query.strip():
            raise ValueError("Query string cannot be empty")

        if self.top_k < 1 or self.top_k > 100:
            raise ValueError(f"top_k must be between 1 and 100, got {self.top_k}")

        if not 0.0 <= self.score_threshold <= 1.0:
            raise ValueError(f"score_threshold must be 0.0-1.0, got {self.score_threshold}")

        if self.search_mode not in ("HYBRID", "KEYWORD_ONLY", "SEMANTIC_ONLY"):
            raise ValueError(f"Invalid search_mode: {self.search_mode}")


@dataclass
class SearchResult:
    """
    Individual search result from evidence retrieval.

    Attributes:
        chunk_id: ID of the matched chunk
        source_id: ID of the source evidence (document, transcript, etc.)
        source_type: Type of evidence
        text: Matched text content
        score: Relevance score (0.0-1.0)
        match_type: "keyword", "semantic", or "hybrid"
        metadata: Additional metadata about the chunk
        locator: Position information (page, paragraph, timecode, etc.)
        highlights: Highlighted matching phrases
    """

    chunk_id: UUID
    source_id: UUID
    source_type: EvidenceType
    text: str
    score: float
    match_type: str
    metadata: Dict[str, Any]
    locator: Dict[str, Any]
    highlights: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate search result."""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"Score must be 0.0-1.0, got {self.score}")


@dataclass
class SearchEvidenceResult:
    """
    Complete search results with metadata.

    Attributes:
        results: List of search results
        total_found: Total matching results (may be > len(results) if paginated)
        search_metadata: Metadata about the search execution
    """

    results: List[SearchResult]
    total_found: int
    search_metadata: Dict[str, Any] = field(default_factory=dict)


class SearchEvidenceQueryHandler:
    """
    Handler for executing evidence search queries.

    Orchestrates hybrid search across Qdrant (semantic) and OpenSearch (keyword)
    backends, merges results, and enriches with metadata.
    """

    def __init__(
        self,
        retrieval_pipeline: Any,
        result_enricher: Any,
    ):
        """
        Initialize handler with dependencies.

        Args:
            retrieval_pipeline: Haystack hybrid retrieval pipeline
            result_enricher: Service for enriching results with metadata
        """
        self.pipeline = retrieval_pipeline
        self.enricher = result_enricher
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def handle(self, query: SearchEvidenceQuery) -> SearchEvidenceResult:
        """
        Execute the search query and return results.

        Steps:
        1. Build filters from query parameters
        2. Execute hybrid search pipeline
        3. Merge and rank results
        4. Enrich with metadata
        5. Format and return

        Args:
            query: The search query to execute

        Returns:
            SearchEvidenceResult with ranked results

        Raises:
            ValueError: If query is invalid
            RuntimeError: If search pipeline fails
        """
        self.logger.info(
            "Executing search query",
            extra={
                "query": query.query,
                "search_mode": query.search_mode,
                "top_k": query.top_k,
                "case_ids": query.case_ids,
            }
        )

        try:
            # 1. Build filters
            filters = self._build_filters(query)

            # 2. Execute search based on mode
            if query.search_mode == "SEMANTIC_ONLY":
                raw_results = await self._semantic_search(query, filters)
            elif query.search_mode == "KEYWORD_ONLY":
                raw_results = await self._keyword_search(query, filters)
            else:  # HYBRID
                raw_results = await self._hybrid_search(query, filters)

            # 3. Filter by score threshold
            filtered_results = [
                r for r in raw_results
                if r.score >= query.score_threshold
            ]

            # 4. Enrich results with metadata
            enriched_results = await self._enrich_results(filtered_results)

            # 5. Prepare metadata
            search_metadata = {
                "query": query.query,
                "search_mode": query.search_mode,
                "filters_applied": filters,
                "results_before_filtering": len(raw_results),
                "results_after_filtering": len(filtered_results),
            }

            self.logger.info(
                "Search completed successfully",
                extra={
                    "total_found": len(enriched_results),
                    "search_mode": query.search_mode,
                }
            )

            return SearchEvidenceResult(
                results=enriched_results[:query.top_k],
                total_found=len(enriched_results),
                search_metadata=search_metadata,
            )

        except Exception as e:
            self.logger.error(
                f"Search query failed: {e}",
                extra={"query": query.query},
                exc_info=True
            )
            raise RuntimeError(f"Search execution failed: {e}") from e

    def _build_filters(self, query: SearchEvidenceQuery) -> Dict[str, Any]:
        """Build filter dict from query parameters."""
        filters = {}

        if query.case_ids:
            filters["case_ids"] = [str(cid) for cid in query.case_ids]

        if query.evidence_types:
            filters["evidence_types"] = [et.value for et in query.evidence_types]

        if query.chunk_types:
            filters["chunk_types"] = [ct.value for ct in query.chunk_types]

        if query.speaker_filter:
            filters["speakers"] = query.speaker_filter

        if query.date_range:
            filters["date_range"] = {
                "start": query.date_range[0],
                "end": query.date_range[1],
            }

        return filters

    async def _semantic_search(
        self,
        query: SearchEvidenceQuery,
        filters: Dict[str, Any]
    ) -> List[SearchResult]:
        """Execute semantic search using vector embeddings."""
        self.logger.debug("Executing semantic search")

        # Call retrieval pipeline with semantic mode
        results = await self.pipeline.search_semantic(
            query=query.query,
            top_k=query.top_k * 2,  # Fetch more for filtering
            filters=filters,
        )

        return [
            SearchResult(
                chunk_id=r["chunk_id"],
                source_id=r["source_id"],
                source_type=EvidenceType(r["source_type"]),
                text=r["text"],
                score=r["score"],
                match_type="semantic",
                metadata=r.get("metadata", {}),
                locator=r.get("locator", {}),
                highlights=[],
            )
            for r in results
        ]

    async def _keyword_search(
        self,
        query: SearchEvidenceQuery,
        filters: Dict[str, Any]
    ) -> List[SearchResult]:
        """Execute keyword search using full-text search."""
        self.logger.debug("Executing keyword search")

        # Call retrieval pipeline with keyword mode
        results = await self.pipeline.search_keyword(
            query=query.query,
            top_k=query.top_k * 2,  # Fetch more for filtering
            filters=filters,
        )

        return [
            SearchResult(
                chunk_id=r["chunk_id"],
                source_id=r["source_id"],
                source_type=EvidenceType(r["source_type"]),
                text=r["text"],
                score=r["score"],
                match_type="keyword",
                metadata=r.get("metadata", {}),
                locator=r.get("locator", {}),
                highlights=r.get("highlights", []),
            )
            for r in results
        ]

    async def _hybrid_search(
        self,
        query: SearchEvidenceQuery,
        filters: Dict[str, Any]
    ) -> List[SearchResult]:
        """Execute hybrid search combining semantic and keyword."""
        self.logger.debug("Executing hybrid search")

        # Call retrieval pipeline with hybrid mode
        results = await self.pipeline.search_hybrid(
            query=query.query,
            top_k=query.top_k * 2,  # Fetch more for filtering
            filters=filters,
        )

        return [
            SearchResult(
                chunk_id=r["chunk_id"],
                source_id=r["source_id"],
                source_type=EvidenceType(r["source_type"]),
                text=r["text"],
                score=r["score"],
                match_type="hybrid",
                metadata=r.get("metadata", {}),
                locator=r.get("locator", {}),
                highlights=r.get("highlights", []),
            )
            for r in results
        ]

    async def _enrich_results(
        self,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """Enrich results with additional metadata if needed."""
        # This could add things like:
        # - Source document titles
        # - Entity tags
        # - Related findings
        # For now, pass through as enricher handles this
        if self.enricher:
            return await self.enricher.enrich(results)
        return results
