"""
Hybrid search service for legal documents.

This module implements a HybridSearchEngine that combines BM25 keyword search
with dense vector semantic search using Reciprocal Rank Fusion (RRF) following
the RAGFlow pattern for multi-recall fusion.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
import logging
from collections import defaultdict
import re

from sentence_transformers import SentenceTransformer
from qdrant_client.models import SparseVector, Filter

from app.core.qdrant import (
    get_qdrant_client,
    search_hybrid,
    build_filter,
)
from app.core.config import settings
from app.schemas.search import (
    SearchQuery,
    SearchResult,
    HybridSearchRequest,
    HybridSearchResponse,
)

logger = logging.getLogger(__name__)


class HybridSearchEngine:
    """
    Hybrid search engine combining BM25 and dense vector search.

    This class implements multi-recall search using:
    1. BM25 sparse vectors for keyword matching
    2. Dense vectors (summary, section, microblock) for semantic search
    3. Reciprocal Rank Fusion (RRF) to combine results

    Attributes:
        embedding_model: SentenceTransformer model for generating embeddings
        collection_name: Qdrant collection name
    """

    def __init__(
        self,
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        collection_name: Optional[str] = None,
    ):
        """
        Initialize the hybrid search engine.

        Args:
            embedding_model_name: Name of the SentenceTransformer model
            collection_name: Qdrant collection name (default: from settings)
        """
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.client = get_qdrant_client()
        logger.info(f"HybridSearchEngine initialized with model: {embedding_model_name}")

    def _tokenize_for_bm25(self, text: str) -> List[str]:
        """
        Tokenize text for BM25 indexing.

        Args:
            text: Input text to tokenize

        Returns:
            List of tokens
        """
        # Simple tokenization: lowercase, remove punctuation, split on whitespace
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = text.split()
        return tokens

    def _create_sparse_vector(self, text: str) -> SparseVector:
        """
        Create a BM25 sparse vector from text.

        This is a simplified BM25 implementation. For production,
        consider using a proper BM25 library or pre-computed term frequencies.

        Args:
            text: Input text

        Returns:
            SparseVector for Qdrant
        """
        tokens = self._tokenize_for_bm25(text)

        # Count token frequencies
        token_counts = defaultdict(int)
        for token in tokens:
            token_counts[token] += 1

        # Create sparse vector (indices are hash of tokens, values are counts)
        # In production, you'd use a proper vocabulary mapping
        indices = []
        values = []

        for token, count in token_counts.items():
            # Use hash for simple token->index mapping
            # In production, maintain a proper token vocabulary
            token_idx = hash(token) % (2**31)  # Keep positive
            indices.append(token_idx)
            values.append(float(count))

        return SparseVector(indices=indices, values=values)

    def _create_dense_vectors(self, text: str) -> Dict[str, List[float]]:
        """
        Create dense embeddings for text.

        Generates embeddings for summary, section, and microblock vectors.
        In this implementation, we use the same embedding for all vector types,
        but in production you might use different models or processing for each.

        Args:
            text: Input text

        Returns:
            Dictionary mapping vector names to embedding lists
        """
        embedding = self.embedding_model.encode(text, convert_to_tensor=False)
        embedding_list = embedding.tolist()

        # For now, use same embedding for all vector types
        # In production, you might want different embeddings or preprocessing
        return {
            "summary": embedding_list,
            "section": embedding_list,
            "microblock": embedding_list,
        }

    def bm25_search(
        self,
        query: str,
        filters: Optional[Filter] = None,
        top_k: int = 10,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform BM25 keyword search.

        Args:
            query: Search query text
            filters: Optional Qdrant filters
            top_k: Maximum number of results
            score_threshold: Minimum score threshold

        Returns:
            List of search results with scores and payloads
        """
        try:
            # Create sparse vector from query
            sparse_vector = self._create_sparse_vector(query)

            # Search using BM25 sparse vector
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=("bm25", sparse_vector),
                query_filter=filters,
                limit=top_k,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=False,
            )

            # Convert to standard format
            formatted_results = []
            for hit in results:
                formatted_results.append({
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload,
                    "vector_type": "bm25",
                })

            logger.info(f"BM25 search returned {len(formatted_results)} results")
            return formatted_results

        except Exception as e:
            logger.error(f"BM25 search error: {e}")
            raise

    def vector_search(
        self,
        query: str,
        filters: Optional[Filter] = None,
        top_k: int = 10,
        score_threshold: Optional[float] = None,
        vector_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform dense vector semantic search.

        Searches across multiple named vectors (summary, section, microblock).

        Args:
            query: Search query text
            filters: Optional Qdrant filters
            top_k: Maximum number of results per vector type
            score_threshold: Minimum score threshold
            vector_types: List of vector types to search (default: all)

        Returns:
            List of search results from all vector types
        """
        try:
            # Generate embeddings
            query_vectors = self._create_dense_vectors(query)

            # Filter to requested vector types
            if vector_types:
                query_vectors = {
                    k: v for k, v in query_vectors.items()
                    if k in vector_types
                }

            # Search with each vector type
            all_results = []
            for vector_name, vector_values in query_vectors.items():
                results = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=(vector_name, vector_values),
                    query_filter=filters,
                    limit=top_k,
                    score_threshold=score_threshold,
                    with_payload=True,
                    with_vectors=False,
                )

                for hit in results:
                    all_results.append({
                        "id": hit.id,
                        "score": hit.score,
                        "payload": hit.payload,
                        "vector_type": vector_name,
                    })

            logger.info(f"Vector search returned {len(all_results)} results from {len(query_vectors)} vector types")
            return all_results

        except Exception as e:
            logger.error(f"Vector search error: {e}")
            raise

    def reciprocal_rank_fusion(
        self,
        result_lists: List[List[Dict[str, Any]]],
        k: int = 60,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Combine multiple result lists using Reciprocal Rank Fusion (RRF).

        RRF formula: RRF_score(d) = sum over all ranklists r: 1 / (k + rank_r(d))
        where k is typically 60 (default parameter).

        Args:
            result_lists: List of result lists from different search methods
            k: RRF k parameter (default: 60)
            top_k: Number of final results to return

        Returns:
            Fused and ranked list of results
        """
        # Track RRF scores for each document
        rrf_scores: Dict[int, float] = defaultdict(float)
        doc_data: Dict[int, Dict[str, Any]] = {}

        # Process each result list
        for result_list in result_lists:
            for rank, result in enumerate(result_list, start=1):
                doc_id = result["id"]

                # Calculate RRF score: 1 / (k + rank)
                rrf_scores[doc_id] += 1.0 / (k + rank)

                # Store document data (from first occurrence)
                if doc_id not in doc_data:
                    doc_data[doc_id] = result

        # Sort by RRF score
        sorted_docs = sorted(
            rrf_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]

        # Build final result list
        fused_results = []
        for doc_id, rrf_score in sorted_docs:
            result = doc_data[doc_id].copy()
            result["score"] = rrf_score  # Replace with RRF score
            result["fusion_score"] = rrf_score
            fused_results.append(result)

        logger.info(f"RRF fusion combined {len(result_lists)} lists into {len(fused_results)} results")
        return fused_results

    def search(
        self,
        request: HybridSearchRequest,
    ) -> HybridSearchResponse:
        """
        Perform hybrid search combining BM25 and vector search.

        This is the main search method that:
        1. Performs BM25 search if enabled
        2. Performs dense vector search if enabled
        3. Combines results using RRF or other fusion method
        4. Applies filters and returns formatted response

        Args:
            request: HybridSearchRequest with search parameters

        Returns:
            HybridSearchResponse with fused and ranked results
        """
        import time
        start_time = time.time()

        try:
            # Build filters
            filters = build_filter(
                case_ids=request.case_ids,
                document_ids=request.document_ids,
                chunk_types=request.chunk_types,
            )

            # Collect results from different search methods
            result_lists = []
            vectors_used = []

            # BM25 search
            if request.use_bm25:
                bm25_results = self.bm25_search(
                    query=request.query,
                    filters=filters,
                    top_k=request.top_k * 2,  # Get more for fusion
                    score_threshold=request.score_threshold,
                )
                if bm25_results:
                    result_lists.append(bm25_results)
                    vectors_used.append("bm25")

            # Dense vector search
            if request.use_dense:
                vector_results = self.vector_search(
                    query=request.query,
                    filters=filters,
                    top_k=request.top_k,
                    score_threshold=request.score_threshold,
                )
                if vector_results:
                    # Group by vector type for separate ranking
                    vector_groups = defaultdict(list)
                    for result in vector_results:
                        vector_groups[result["vector_type"]].append(result)

                    # Add each vector type as a separate list for fusion
                    for vector_type, results in vector_groups.items():
                        result_lists.append(results)
                        vectors_used.append(vector_type)

            # Fuse results
            if len(result_lists) == 0:
                # No results
                fused_results = []
            elif len(result_lists) == 1:
                # Only one search method, no fusion needed
                fused_results = result_lists[0][:request.top_k]
            else:
                # Apply fusion
                if request.fusion_method == "rrf":
                    fused_results = self.reciprocal_rank_fusion(
                        result_lists=result_lists,
                        k=request.rrf_k,
                        top_k=request.top_k,
                    )
                else:
                    # Fallback: use first list (BM25 or vector)
                    logger.warning(f"Fusion method '{request.fusion_method}' not implemented, using first list")
                    fused_results = result_lists[0][:request.top_k]

            # Convert to SearchResult objects
            search_results = []
            for result in fused_results:
                payload = result.get("payload", {})

                # Extract highlights (simple implementation)
                highlights = self._extract_highlights(
                    text=payload.get("text", ""),
                    query=request.query,
                )

                search_results.append(
                    SearchResult(
                        id=result["id"],
                        score=result["score"],
                        text=payload.get("text", ""),
                        metadata={
                            "document_id": payload.get("document_id"),
                            "case_id": payload.get("case_id"),
                            "chunk_type": payload.get("chunk_type"),
                            "page_number": payload.get("page_number"),
                            "position": payload.get("position"),
                        },
                        highlights=highlights,
                        vector_type=result.get("vector_type"),
                    )
                )

            # Calculate execution time
            search_time_ms = int((time.time() - start_time) * 1000)

            # Build response
            response = HybridSearchResponse(
                results=search_results,
                total_results=len(search_results),
                query=request.query,
                search_metadata={
                    "search_time_ms": search_time_ms,
                    "vectors_used": vectors_used,
                    "fusion_method": request.fusion_method,
                    "filters_applied": {
                        "case_ids": request.case_ids,
                        "document_ids": request.document_ids,
                        "chunk_types": request.chunk_types,
                    },
                },
            )

            logger.info(
                f"Hybrid search completed in {search_time_ms}ms: "
                f"{len(search_results)} results, vectors={vectors_used}"
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
        Extract highlighted snippets from text matching query terms.

        Args:
            text: Source text to extract from
            query: Search query
            max_highlights: Maximum number of highlights to return
            context_words: Number of context words around match

        Returns:
            List of highlighted text snippets or None
        """
        if not text or not query:
            return None

        # Tokenize query
        query_tokens = set(self._tokenize_for_bm25(query))

        # Tokenize text and find matches
        words = text.split()
        highlights = []

        for i, word in enumerate(words):
            # Check if word matches any query token
            clean_word = re.sub(r'[^\w\s]', '', word.lower())
            if clean_word in query_tokens:
                # Extract context around match
                start = max(0, i - context_words)
                end = min(len(words), i + context_words + 1)
                snippet = " ".join(words[start:end])

                # Add ellipsis if truncated
                if start > 0:
                    snippet = "..." + snippet
                if end < len(words):
                    snippet = snippet + "..."

                highlights.append(snippet)

                if len(highlights) >= max_highlights:
                    break

        return highlights if highlights else None


# Singleton instance for reuse
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
