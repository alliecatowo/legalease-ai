"""
Graph-Enhanced Search Integration

Integrates EnhancedGraphRAGEngine with HybridSearchEngine to provide
entity-enhanced search with knowledge graph context.

Pipeline:
1. Hybrid vector search (BM25 + Dense + Fusion)
2. Entity extraction from query
3. Graph traversal for entity expansion
4. Score boosting based on entity matches
5. Citation network analysis
6. Result re-ranking with graph signals
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.search import HybridSearchRequest, HybridSearchResponse, SearchResult
from app.services.search.engine import HybridSearchEngine
from app.services.search.graph_rag_enhanced import EnhancedGraphRAGEngine
from app.core.neo4j import neo4j_client
from app.services.entity_service import entity_service
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class GraphEnhancedSearchEngine:
    """
    Search engine combining hybrid vector search with graph knowledge.

    This engine enhances search results by:
    1. Using entity extraction to find semantically related documents
    2. Leveraging citation networks to boost important documents
    3. Expanding queries via knowledge graph traversal
    4. Re-ranking based on entity relevance and graph centrality
    """

    def __init__(
        self,
        hybrid_search_engine: Optional[HybridSearchEngine] = None,
        graph_rag_engine: Optional[EnhancedGraphRAGEngine] = None,
        enable_entity_boost: bool = True,
        enable_citation_boost: bool = True,
        entity_boost_weight: float = 0.20,
        citation_boost_weight: float = 0.15
    ):
        """
        Initialize graph-enhanced search engine.

        Args:
            hybrid_search_engine: Hybrid search engine instance
            graph_rag_engine: Enhanced GraphRAG engine instance
            enable_entity_boost: Enable entity-based score boosting
            enable_citation_boost: Enable citation-based score boosting
            entity_boost_weight: Weight for entity boost (0-1, default: 0.20)
            citation_boost_weight: Weight for citation boost (0-1, default: 0.15)
        """
        self.hybrid_engine = hybrid_search_engine or HybridSearchEngine()
        self.graph_engine = graph_rag_engine or EnhancedGraphRAGEngine(
            neo4j_client=neo4j_client,
            entity_service=entity_service
        )

        self.enable_entity_boost = enable_entity_boost
        self.enable_citation_boost = enable_citation_boost
        self.entity_boost_weight = entity_boost_weight
        self.citation_boost_weight = citation_boost_weight

        logger.info(
            f"GraphEnhancedSearchEngine initialized "
            f"(entity_boost={enable_entity_boost}, citation_boost={enable_citation_boost})"
        )

    async def search(
        self,
        request: HybridSearchRequest,
        db: AsyncSession,
        case_id: Optional[str] = None,
        entity_expansion_strategy: str = "co_occurrence",
        max_entity_hops: int = 2
    ) -> HybridSearchResponse:
        """
        Perform graph-enhanced hybrid search.

        Pipeline:
        1. Initial hybrid vector search (BM25 + Dense + Fusion)
        2. Extract entities from query and expand via graph
        3. Boost scores for documents matching entities
        4. Add citation network context and boost
        5. Re-rank and return results

        Args:
            request: Search request
            db: Database session
            case_id: Optional case ID for scoping (extracted from request if None)
            entity_expansion_strategy: Strategy for entity expansion ("co_occurrence" or "citation_chain")
            max_entity_hops: Maximum hops for entity graph traversal (1-3)

        Returns:
            Enhanced search response with graph-boosted scores
        """
        # Extract case_id from request if not provided
        if case_id is None:
            case_id = self._extract_case_id_from_request(request)

        # Stage 1: Hybrid vector search
        logger.info(f"Stage 1: Hybrid vector search for query: '{request.query}'")
        vector_response = self.hybrid_engine.search(request)

        # Convert SearchResult objects to dictionaries for processing
        search_results = [
            self._search_result_to_dict(result)
            for result in vector_response.results
        ]

        logger.info(f"Hybrid search returned {len(search_results)} results")

        # If no case_id available, skip graph enhancement
        if not case_id:
            logger.warning("No case_id available - skipping graph enhancement")
            return vector_response

        # Stage 2: Entity-based boosting (if enabled)
        if self.enable_entity_boost and search_results:
            logger.info("Stage 2: Entity extraction and graph traversal")
            entity_data = await self.graph_engine.entity_enhanced_search(
                query=request.query,
                case_id=case_id,
                db=db,
                max_hops=max_entity_hops,
                expansion_strategy=entity_expansion_strategy
            )

            entity_scores = entity_data.get("entity_scores", {})

            if entity_scores:
                logger.info(f"Boosting scores for {len(entity_scores)} entity-matched documents")
                search_results = self._apply_entity_boost(
                    search_results=search_results,
                    entity_scores=entity_scores,
                    boost_weight=self.entity_boost_weight
                )

                # Add entity metadata
                for result in search_results:
                    doc_id = self._extract_doc_id_from_result(result)
                    if doc_id and doc_id in entity_scores:
                        if "metadata" not in result:
                            result["metadata"] = {}
                        result["metadata"]["entity_score"] = entity_scores[doc_id]
                        result["metadata"]["entity_matched"] = True
                        result["metadata"]["query_entities"] = entity_data.get("query_entities", [])
            else:
                logger.info("No entity matches found - skipping entity boost")

        # Stage 3: Citation network boosting (if enabled)
        if self.enable_citation_boost and search_results:
            logger.info("Stage 3: Citation network analysis")
            search_results = self.graph_engine.add_citation_context(
                search_results=search_results,
                case_id=case_id,
                citation_boost_weight=self.citation_boost_weight,
                use_pagerank=True
            )

        # Stage 4: Re-sort by boosted scores
        search_results.sort(key=lambda x: x.get("score", 0.0), reverse=True)

        # Stage 5: Convert back to SearchResult objects
        enhanced_results = []
        for result in search_results[:request.top_k]:
            enhanced_results.append(self._dict_to_search_result(result))

        # Update response with enhanced results
        vector_response.results = enhanced_results
        vector_response.total_results = len(enhanced_results)

        # Add graph enhancement metadata
        if "search_metadata" not in vector_response.search_metadata:
            vector_response.search_metadata = {}

        vector_response.search_metadata["graph_enhancement"] = {
            "entity_boost_enabled": self.enable_entity_boost,
            "citation_boost_enabled": self.enable_citation_boost,
            "entity_boost_weight": self.entity_boost_weight,
            "citation_boost_weight": self.citation_boost_weight,
            "entity_expansion_strategy": entity_expansion_strategy,
            "max_entity_hops": max_entity_hops
        }

        logger.info(
            f"Graph-enhanced search completed: {len(enhanced_results)} results"
        )

        return vector_response

    def _apply_entity_boost(
        self,
        search_results: List[Dict],
        entity_scores: Dict[str, float],
        boost_weight: float
    ) -> List[Dict]:
        """
        Apply entity-based score boosting.

        Args:
            search_results: List of search results
            entity_scores: Dict mapping doc_id -> entity relevance score (0-1)
            boost_weight: Weight for entity boost

        Returns:
            Search results with boosted scores
        """
        for result in search_results:
            doc_id = self._extract_doc_id_from_result(result)
            if not doc_id:
                continue

            entity_score = entity_scores.get(doc_id, 0.0)
            if entity_score > 0:
                original_score = result.get("score", 0.0)
                entity_boost = entity_score * boost_weight
                boosted_score = original_score + entity_boost

                # Ensure score stays in valid range (0-1)
                result["score"] = min(1.0, boosted_score)

                # Track boost amount
                if "metadata" not in result:
                    result["metadata"] = {}
                result["metadata"]["entity_boost"] = entity_boost

                logger.debug(
                    f"Document {doc_id}: entity_score={entity_score:.3f}, "
                    f"boost={entity_boost:.3f}, "
                    f"score={original_score:.3f}->{result['score']:.3f}"
                )

        return search_results

    def _extract_case_id_from_request(
        self,
        request: HybridSearchRequest
    ) -> Optional[str]:
        """Extract case ID from search request."""
        # Try case_ids list
        if request.case_ids and len(request.case_ids) > 0:
            return str(request.case_ids[0])

        # Try case_gids and resolve
        if request.case_gids and len(request.case_gids) > 0:
            case_gid = request.case_gids[0]
            # This would need GID resolver to convert to UUID
            # For now, return the GID as-is
            return case_gid

        return None

    def _extract_doc_id_from_result(self, result: Dict) -> Optional[str]:
        """Extract document ID from search result."""
        # Try direct document_id
        doc_id = result.get("document_id")
        if doc_id:
            return str(doc_id)

        # Try metadata
        metadata = result.get("metadata", {})
        doc_id = metadata.get("document_id") or metadata.get("doc_id")
        if doc_id:
            return str(doc_id)

        # Try payload
        payload = result.get("payload", {})
        doc_id = payload.get("document_id") or payload.get("doc_id")
        if doc_id:
            return str(doc_id)

        return None

    def _search_result_to_dict(self, result: SearchResult) -> Dict[str, Any]:
        """Convert SearchResult to dictionary for processing."""
        return {
            "id": result.id,
            "score": result.score,
            "text": result.text,
            "match_type": result.match_type,
            "page_number": result.page_number,
            "bboxes": result.bboxes,
            "metadata": result.metadata,
            "highlights": result.highlights,
            "vector_type": result.vector_type,
            "document_id": result.metadata.get("document_id") if result.metadata else None,
            "payload": {
                "document_id": result.metadata.get("document_id") if result.metadata else None,
                "case_id": result.metadata.get("case_id") if result.metadata else None,
                "text": result.text
            }
        }

    def _dict_to_search_result(self, result_dict: Dict[str, Any]) -> SearchResult:
        """Convert dictionary back to SearchResult."""
        return SearchResult(
            id=result_dict.get("id", ""),
            gid=result_dict.get("gid", result_dict.get("id", "")),
            score=result_dict.get("score", 0.0),
            text=result_dict.get("text", ""),
            match_type=result_dict.get("match_type", "hybrid"),
            page_number=result_dict.get("page_number"),
            bboxes=result_dict.get("bboxes", []),
            metadata=result_dict.get("metadata", {}),
            highlights=result_dict.get("highlights"),
            vector_type=result_dict.get("vector_type")
        )


# Factory function
def create_graph_enhanced_search_engine(
    enable_entity_boost: bool = True,
    enable_citation_boost: bool = True,
    entity_boost_weight: float = 0.20,
    citation_boost_weight: float = 0.15
) -> GraphEnhancedSearchEngine:
    """
    Create a graph-enhanced search engine instance.

    Args:
        enable_entity_boost: Enable entity-based score boosting
        enable_citation_boost: Enable citation-based score boosting
        entity_boost_weight: Weight for entity boost (0-1, default: 0.20)
        citation_boost_weight: Weight for citation boost (0-1, default: 0.15)

    Returns:
        Configured graph-enhanced search engine
    """
    return GraphEnhancedSearchEngine(
        enable_entity_boost=enable_entity_boost,
        enable_citation_boost=enable_citation_boost,
        entity_boost_weight=entity_boost_weight,
        citation_boost_weight=citation_boost_weight
    )


# Singleton instance (optional - can create per-request)
_graph_search_engine: Optional[GraphEnhancedSearchEngine] = None


def get_graph_enhanced_search_engine() -> GraphEnhancedSearchEngine:
    """
    Get or create singleton GraphEnhancedSearchEngine.

    Returns:
        GraphEnhancedSearchEngine instance
    """
    global _graph_search_engine

    if _graph_search_engine is None:
        _graph_search_engine = create_graph_enhanced_search_engine()
        logger.info("Created singleton GraphEnhancedSearchEngine")

    return _graph_search_engine
