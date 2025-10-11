"""
Hybrid Search Service - Using Qdrant Query API

Production hybrid search implementation using:
- Qdrant Query API (v1.10+) for proper hybrid search
- FastEmbed for embeddings
- Cross-encoder reranking
- RRF and DBSF fusion methods
- Proper named sparse vector handling
"""

from typing import List, Dict, Any, Optional
import logging
from collections import defaultdict
import re

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Prefetch,
    SparseVector,
    Filter,
    Fusion,
    FusionQuery,
)

from app.core.qdrant import get_qdrant_client, build_filter
from app.core.config import settings
from app.schemas.search import (
    HybridSearchRequest,
    HybridSearchResponse,
    SearchResult,
)
from app.workers.pipelines.embeddings import FastEmbedPipeline
from app.workers.pipelines.reranker import CrossEncoderReranker
from app.workers.pipelines.bm25_encoder import BM25Encoder

logger = logging.getLogger(__name__)


class HybridSearchEngine:
    """
    Modern hybrid search engine using Qdrant Query API.

    Features:
    - Multi-stage retrieval (BM25 → Dense → Rerank)
    - Proper named vector support
    - RRF and DBSF fusion
    - Cross-encoder reranking
    - FastEmbed for fast inference
    """

    def __init__(
        self,
        embedding_model_name: str = "BAAI/bge-small-en-v1.5",
        reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        collection_name: Optional[str] = None,
        enable_reranking: bool = False,  # Disabled until sentence-transformers is added
    ):
        """
        Initialize the hybrid search engine.

        Args:
            embedding_model_name: FastEmbed model for dense vectors
            reranker_model_name: Cross-encoder model for reranking
            collection_name: Qdrant collection name
            enable_reranking: Enable cross-encoder reranking
        """
        self.embedding_model_name = embedding_model_name
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.client = get_qdrant_client()
        self.enable_reranking = enable_reranking

        logger.info(f"HybridSearchEngine initialized")
        logger.info(f"  Embedding model: {embedding_model_name}")
        logger.info(f"  Reranking: {enable_reranking}")

        # Initialize components
        self.embed_pipeline = FastEmbedPipeline(model_name=embedding_model_name)
        self.bm25_encoder = BM25Encoder()

        if enable_reranking:
            self.reranker = CrossEncoderReranker(model_name=reranker_model_name)
        else:
            self.reranker = None

    def _create_sparse_vector(self, text: str) -> SparseVector:
        """
        Create BM25 sparse vector from text.

        Args:
            text: Input text

        Returns:
            Qdrant SparseVector
        """
        indices, values = self.bm25_encoder.encode_to_qdrant_format(text)
        return SparseVector(indices=indices, values=values)

    def _create_dense_vector(self, text: str) -> List[float]:
        """
        Create dense embedding from text.

        Args:
            text: Input text

        Returns:
            Embedding vector as list
        """
        embedding = self.embed_pipeline.generate_single_embedding(text)
        return embedding.tolist()

    def _normalize_and_boost_scores(
        self,
        results: List[Dict[str, Any]],
        raw_scores: List[float],
        fusion_method: str,
        bm25_scores: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """
        Normalize RRF/DBSF scores to 0-1 range and boost keyword matches.

        RRF scores are rank-based (1/(rank+k)) and typically range 0-0.02 for k=60.
        We need to:
        1. Normalize to 0-1 range using min-max scaling
        2. Boost results with strong BM25 scores (keyword matches)
        3. Apply non-linear scaling to spread out the top results

        Args:
            results: Search results with raw scores
            raw_scores: List of raw fusion scores
            fusion_method: Fusion method used (rrf or dbsf)
            bm25_scores: Dictionary of BM25 scores by point ID

        Returns:
            Results with normalized and boosted scores
        """
        if not results or not raw_scores:
            return results

        # Calculate score statistics
        min_score = min(raw_scores)
        max_score = max(raw_scores)
        score_range = max_score - min_score

        # Avoid division by zero
        if score_range < 1e-9:
            # All scores are the same, assign uniform scores
            for result in results:
                result["score"] = 0.7
            return results

        # Step 1: Min-max normalization to 0-1
        for i, result in enumerate(results):
            normalized_score = (raw_scores[i] - min_score) / score_range

            # Step 2: Boost keyword matches
            point_id = result["id"]
            bm25_score = bm25_scores.get(point_id, 0.0)

            # Keyword boost: High BM25 scores indicate strong keyword matches
            # BM25 scores typically range 0-20+ for good matches
            keyword_boost = 0.0
            if bm25_score > 0:
                # Normalize BM25 score and apply as boost
                # Strong keyword matches (BM25 > 5) get significant boost
                bm25_normalized = min(bm25_score / 10.0, 1.0)  # Cap at 1.0
                keyword_boost = bm25_normalized * 0.3  # Up to +0.3 boost

            # Step 3: Apply non-linear scaling for better score distribution
            # Use power scaling to spread out top results
            if fusion_method == "rrf":
                # RRF benefits from square root scaling to spread scores
                boosted_score = (normalized_score ** 0.7) + keyword_boost
            else:
                # DBSF is already normalized, apply lighter scaling
                boosted_score = (normalized_score ** 0.85) + keyword_boost

            # Step 4: Ensure keyword-only matches get high scores
            # If BM25 score is very high and it's a top result, boost to 0.85+
            if bm25_score > 5.0 and i < 5:
                boosted_score = max(boosted_score, 0.85 + (bm25_normalized * 0.1))

            # Clamp to 0-1 range
            boosted_score = max(0.0, min(1.0, boosted_score))

            result["score"] = boosted_score

            # Add debug info
            result["_score_debug"] = {
                "raw_score": raw_scores[i],
                "normalized": normalized_score,
                "bm25_score": bm25_score,
                "keyword_boost": keyword_boost,
                "final_score": boosted_score,
            }

        logger.info(
            f"Score normalization complete: "
            f"raw range [{min_score:.4f}, {max_score:.4f}] -> "
            f"normalized range [0.0, 1.0]"
        )

        return results

    def search_with_query_api(
        self,
        request: HybridSearchRequest,
    ) -> List[Dict[str, Any]]:
        """
        Search using Qdrant Query API with hybrid approach.

        Uses prefetch for initial retrieval and Query API for fusion.

        Args:
            request: Search request

        Returns:
            List of search results with normalized scores
        """
        try:
            # Build filters
            filters = build_filter(
                case_ids=request.case_ids,
                document_ids=request.document_ids,
                chunk_types=request.chunk_types,
            )

            # Build prefetch queries
            prefetch_queries = []

            # Add BM25 sparse prefetch if enabled
            bm25_results = {}  # Track BM25-only results for boosting
            if request.use_bm25:
                sparse_vector = self._create_sparse_vector(request.query)
                prefetch_queries.append(
                    Prefetch(
                        query=sparse_vector,  # SparseVector directly
                        using="bm25",  # Named vector name
                        filter=filters,
                        limit=request.top_k * 2,  # Get more for fusion
                    )
                )

                # Get BM25-only results for keyword match detection
                try:
                    bm25_only = self.client.query_points(
                        collection_name=self.collection_name,
                        query=sparse_vector,
                        using="bm25",
                        filter=filters,
                        limit=request.top_k * 2,
                        with_payload=False,
                    )
                    # Store BM25 scores by point ID for boosting
                    for point in bm25_only.points:
                        bm25_results[str(point.id)] = point.score if point.score else 0.0
                except Exception as e:
                    logger.warning(f"Failed to get BM25-only results: {e}")

            # Add dense vector prefetch if enabled
            if request.use_dense:
                dense_vector = self._create_dense_vector(request.query)

                # Search multiple vector types
                for vector_name in ["summary", "section", "microblock"]:
                    prefetch_queries.append(
                        Prefetch(
                            query=dense_vector,  # List of floats directly
                            using=vector_name,  # Named vector name
                            filter=filters,
                            limit=request.top_k,
                        )
                    )

            # Determine fusion method
            if request.fusion_method == "rrf":
                fusion = Fusion.RRF
            elif request.fusion_method == "dbsf":
                fusion = Fusion.DBSF
            else:
                fusion = Fusion.RRF  # Default

            # Execute query with prefetch and fusion
            # Use FusionQuery to combine prefetch results
            results = self.client.query_points(
                collection_name=self.collection_name,
                prefetch=prefetch_queries,
                query=FusionQuery(fusion=fusion),  # Fusion combines prefetch results
                limit=request.top_k * 3,  # Get more for score normalization and filtering
                with_payload=True,
            )

            # Convert to standard format with score normalization
            formatted_results = []
            raw_scores = []

            for point in results.points:
                score = point.score if point.score is not None else 0.0
                raw_scores.append(score)

                formatted_results.append({
                    "id": str(point.id),  # Convert to string to handle UUIDs
                    "score": score,
                    "payload": point.payload if point.payload else {},
                    "bm25_score": bm25_results.get(str(point.id), 0.0),  # Track BM25 score
                })

            # Normalize and boost scores
            formatted_results = self._normalize_and_boost_scores(
                formatted_results,
                raw_scores,
                request.fusion_method,
                bm25_results,
            )

            logger.info(
                f"Query API returned {len(formatted_results)} results "
                f"(before threshold filtering)"
            )
            return formatted_results

        except Exception as e:
            logger.error(f"Error in Query API search: {e}", exc_info=True)
            raise

    def search(
        self,
        request: HybridSearchRequest,
    ) -> HybridSearchResponse:
        """
        Main search method with reranking and score filtering.

        Pipeline:
        1. Hybrid search with Query API (BM25 + Dense + Fusion)
        2. Score normalization and boosting
        3. Score threshold filtering
        4. Cross-encoder reranking (optional)
        5. Format results

        Args:
            request: Search request

        Returns:
            Search response with normalized scores
        """
        import time
        start_time = time.time()

        try:
            # Stage 1: Hybrid search with score normalization
            search_results = self.search_with_query_api(request)

            # Stage 2: Apply score threshold filtering
            score_threshold = request.score_threshold if request.score_threshold is not None else 0.3
            results_before_filtering = len(search_results)

            search_results = [
                result for result in search_results
                if result["score"] >= score_threshold
            ]

            filtered_count = results_before_filtering - len(search_results)
            if filtered_count > 0:
                logger.info(
                    f"Filtered out {filtered_count} results below "
                    f"threshold {score_threshold:.2f}"
                )

            # Stage 3: Limit to top_k after filtering
            search_results = search_results[:request.top_k]

            # Stage 4: Reranking (optional)
            if self.enable_reranking and self.reranker and len(search_results) > 0:
                logger.info(f"Reranking {len(search_results)} results")
                search_results = self.reranker.rerank_search_results(
                    query=request.query,
                    search_results=search_results,
                    top_k=request.top_k,
                    text_key="payload.text",  # Nested key
                )

            # Stage 5: Format results
            formatted_results = []
            for result in search_results:
                payload = result.get("payload", {})

                # Extract text from payload
                text = payload.get("text", "")

                # Extract highlights (simple implementation)
                highlights = self._extract_highlights(text, request.query)

                formatted_results.append(
                    SearchResult(
                        id=result["id"],
                        score=result["score"],
                        text=text,
                        metadata={
                            "document_id": payload.get("document_id"),
                            "case_id": payload.get("case_id"),
                            "chunk_type": payload.get("chunk_type"),
                            "page_number": payload.get("page_number"),
                            "position": payload.get("position"),
                            "bboxes": payload.get("bboxes", []),
                            "bm25_score": result.get("bm25_score", 0.0),
                            "score_debug": result.get("_score_debug"),
                        },
                        highlights=highlights,
                        vector_type=payload.get("chunk_type"),
                    )
                )

            # Calculate execution time
            search_time_ms = int((time.time() - start_time) * 1000)

            # Build response
            response = HybridSearchResponse(
                results=formatted_results,
                total_results=len(formatted_results),
                query=request.query,
                search_metadata={
                    "search_time_ms": search_time_ms,
                    "fusion_method": request.fusion_method,
                    "reranking_enabled": self.enable_reranking,
                    "score_threshold": score_threshold,
                    "results_filtered": filtered_count,
                    "filters_applied": {
                        "case_ids": request.case_ids,
                        "document_ids": request.document_ids,
                        "chunk_types": request.chunk_types,
                    },
                },
            )

            logger.info(
                f"Hybrid search completed in {search_time_ms}ms: "
                f"{len(formatted_results)} results (filtered {filtered_count})"
            )

            return response

        except Exception as e:
            logger.error(f"Hybrid search error: {e}", exc_info=True)
            raise

    def _extract_highlights(
        self,
        text: str,
        query: str,
        max_highlights: int = 3,
        context_words: int = 10,
    ) -> Optional[List[str]]:
        """
        Extract highlighted snippets from text.

        Args:
            text: Source text
            query: Search query
            max_highlights: Max number of highlights
            context_words: Context words around match

        Returns:
            List of highlight snippets
        """
        if not text or not query:
            return None

        # Simple tokenization
        query_tokens = set(query.lower().split())
        words = text.split()
        highlights = []

        for i, word in enumerate(words):
            clean_word = re.sub(r'[^\w\s]', '', word.lower())
            if clean_word in query_tokens:
                start = max(0, i - context_words)
                end = min(len(words), i + context_words + 1)
                snippet = " ".join(words[start:end])

                if start > 0:
                    snippet = "..." + snippet
                if end < len(words):
                    snippet = snippet + "..."

                highlights.append(snippet)

                if len(highlights) >= max_highlights:
                    break

        return highlights if highlights else None


# Singleton instance
_search_engine_instance: Optional[HybridSearchEngine] = None


def get_search_engine() -> HybridSearchEngine:
    """
    Get or create singleton HybridSearchEngine instance.

    Returns:
        HybridSearchEngine instance
    """
    global _search_engine_instance

    if _search_engine_instance is None:
        _search_engine_instance = HybridSearchEngine()
        logger.info("Created new HybridSearchEngine singleton instance")

    return _search_engine_instance
