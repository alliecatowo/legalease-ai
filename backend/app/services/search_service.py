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
            List of search results
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
                limit=request.top_k * 2 if self.enable_reranking else request.top_k,
                with_payload=True,
            )

            # Convert to standard format
            formatted_results = []
            for point in results.points:
                formatted_results.append({
                    "id": str(point.id),  # Convert to string to handle UUIDs
                    "score": point.score if point.score is not None else 0.0,
                    "payload": point.payload if point.payload else {},
                })

            logger.info(f"Query API returned {len(formatted_results)} results")
            return formatted_results

        except Exception as e:
            logger.error(f"Error in Query API search: {e}", exc_info=True)
            raise

    def search(
        self,
        request: HybridSearchRequest,
    ) -> HybridSearchResponse:
        """
        Main search method with reranking.

        Pipeline:
        1. Hybrid search with Query API (BM25 + Dense + Fusion)
        2. Cross-encoder reranking (optional)
        3. Format results

        Args:
            request: Search request

        Returns:
            Search response
        """
        import time
        start_time = time.time()

        try:
            # Stage 1: Hybrid search
            search_results = self.search_with_query_api(request)

            # Stage 2: Reranking (optional)
            if self.enable_reranking and self.reranker and len(search_results) > 0:
                logger.info(f"Reranking {len(search_results)} results")
                search_results = self.reranker.rerank_search_results(
                    query=request.query,
                    search_results=search_results,
                    top_k=request.top_k,
                    text_key="payload.text",  # Nested key
                )

            # Stage 3: Format results
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
                    "filters_applied": {
                        "case_ids": request.case_ids,
                        "document_ids": request.document_ids,
                        "chunk_types": request.chunk_types,
                    },
                },
            )

            logger.info(
                f"Hybrid search completed in {search_time_ms}ms: "
                f"{len(formatted_results)} results"
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
