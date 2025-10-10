"""
Cross-Encoder Reranking Pipeline

Provides reranking functionality using cross-encoder models for improved retrieval accuracy.
Reranking is applied after initial hybrid search to dramatically improve result quality.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """
    Reranker using cross-encoder models for scoring query-document pairs.

    Cross-encoders process query and document together, providing more accurate
    relevance scores than bi-encoders (which embed separately). Typically used
    as a second-stage reranker after initial retrieval.

    FastEmbed cross-encoders are optimized with ONNX for production use.

    Typical workflow:
    1. Hybrid search retrieves top 100 candidates
    2. Cross-encoder reranks to find best 10
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        cache_dir: Optional[str] = None,
        threads: Optional[int] = None,
    ):
        """
        Initialize the cross-encoder reranker.

        Args:
            model_name: HuggingFace cross-encoder model
                       Popular options:
                       - "cross-encoder/ms-marco-MiniLM-L-6-v2" (fast, good quality)
                       - "cross-encoder/ms-marco-MiniLM-L-12-v2" (better quality, slower)
                       - "BAAI/bge-reranker-v2-m3" (best quality, multilingual)
            cache_dir: Directory to cache models
            threads: Number of threads for inference
        """
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.threads = threads

        logger.info(f"Initializing CrossEncoderReranker with model={model_name}")

        # Try to import FastEmbed's TextCrossEncoder (if available)
        try:
            from fastembed import TextCrossEncoder

            kwargs = {"model_name": model_name}
            if cache_dir:
                kwargs["cache_dir"] = cache_dir
            if threads:
                kwargs["threads"] = threads

            self.model = TextCrossEncoder(**kwargs)
            self.backend = "fastembed"
            logger.info(f"Loaded cross-encoder with FastEmbed backend")

        except (ImportError, Exception) as e:
            logger.warning(f"FastEmbed TextCrossEncoder not available: {e}")
            logger.info("Falling back to sentence-transformers CrossEncoder")

            try:
                from sentence_transformers import CrossEncoder
                self.model = CrossEncoder(model_name)
                self.backend = "sentence_transformers"
                logger.info(f"Loaded cross-encoder with sentence-transformers backend")
            except ImportError:
                logger.error("Neither FastEmbed nor sentence-transformers available for cross-encoding")
                raise ImportError(
                    "Cannot load cross-encoder. Install either:\n"
                    "  pip install fastembed>=0.6.1\n"
                    "  pip install sentence-transformers"
                )

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int] = None,
    ) -> List[Tuple[int, float]]:
        """
        Rerank documents by relevance to query.

        Args:
            query: Search query text
            documents: List of document texts to rerank
            top_k: Return only top-k results (default: all)

        Returns:
            List of (document_index, score) tuples, sorted by score descending
        """
        if not documents:
            logger.warning("Empty documents list provided to rerank")
            return []

        try:
            # Create query-document pairs
            pairs = [[query, doc] for doc in documents]

            if self.backend == "fastembed":
                # FastEmbed returns generator of scores
                scores_gen = self.model.predict(pairs)
                scores = list(scores_gen)
            else:
                # sentence-transformers returns numpy array
                scores = self.model.predict(pairs)
                scores = scores.tolist()

            # Create (index, score) tuples
            ranked_results = [(idx, score) for idx, score in enumerate(scores)]

            # Sort by score descending
            ranked_results.sort(key=lambda x: x[1], reverse=True)

            # Apply top_k if specified
            if top_k:
                ranked_results = ranked_results[:top_k]

            logger.info(f"Reranked {len(documents)} documents, returning top {len(ranked_results)}")
            return ranked_results

        except Exception as e:
            logger.error(f"Error during reranking: {e}")
            raise

    def rerank_search_results(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        top_k: Optional[int] = None,
        text_key: str = "text",
    ) -> List[Dict[str, Any]]:
        """
        Rerank search results from hybrid search.

        Args:
            query: Search query text
            search_results: List of search result dicts with text and metadata
            top_k: Return only top-k results (default: all)
            text_key: Key in result dict containing text to rerank (default: "text")

        Returns:
            Reranked search results with updated scores
        """
        if not search_results:
            return []

        # Extract texts for reranking
        documents = [result.get(text_key, "") for result in search_results]

        # Get reranked indices and scores
        reranked = self.rerank(query, documents, top_k=None)

        # Build new result list with reranker scores
        reranked_results = []
        for idx, rerank_score in reranked:
            result = search_results[idx].copy()
            result["rerank_score"] = float(rerank_score)
            result["original_score"] = result.get("score", 0.0)
            result["score"] = float(rerank_score)  # Replace score with rerank score
            reranked_results.append(result)

        # Apply top_k after reranking
        if top_k:
            reranked_results = reranked_results[:top_k]

        return reranked_results

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the reranker configuration.

        Returns:
            Dictionary with model information
        """
        return {
            "model_name": self.model_name,
            "backend": self.backend,
            "cache_dir": self.cache_dir,
            "threads": self.threads,
        }


# Convenience function
def rerank_results(
    query: str,
    search_results: List[Dict[str, Any]],
    top_k: int = 10,
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    text_key: str = "text",
) -> List[Dict[str, Any]]:
    """
    Convenience function to rerank search results.

    Args:
        query: Search query
        search_results: List of search results
        top_k: Number of top results to return
        model_name: Cross-encoder model to use
        text_key: Key containing text in results

    Returns:
        Reranked results
    """
    reranker = CrossEncoderReranker(model_name=model_name)
    return reranker.rerank_search_results(
        query=query,
        search_results=search_results,
        top_k=top_k,
        text_key=text_key,
    )
