"""
Reciprocal Rank Fusion (RRF) ranker for hybrid search.

Combines results from multiple retrievers (BM25 + dense vector)
using reciprocal rank fusion algorithm.
"""

import logging
from typing import List, Dict, Any, Optional
from collections import defaultdict

from haystack import component, Document

logger = logging.getLogger(__name__)


@component
class ReciprocalRankFusionRanker:
    """
    Haystack component for fusing multiple ranked result lists using RRF.

    Reciprocal Rank Fusion (RRF) combines rankings from different sources
    by assigning scores based on reciprocal ranks: score = 1 / (k + rank).

    Features:
    - Fuses results from BM25 (keyword) and dense (semantic) search
    - Configurable k parameter for rank smoothing
    - Score normalization and boosting
    - Deduplication by document ID
    - BM25 score boosting for strong keyword matches

    Reference:
    Cormack, G. V., Clarke, C. L., & Buettcher, S. (2009).
    "Reciprocal rank fusion outperforms condorcet and individual rank learning methods"
    """

    def __init__(
        self,
        rrf_k: int = 60,
        normalize_scores: bool = True,
        boost_keyword_matches: bool = True,
        keyword_boost_weight: float = 0.3,
    ):
        """
        Initialize RRF ranker.

        Args:
            rrf_k: RRF constant k (typically 60). Higher k = less emphasis on top ranks
            normalize_scores: Whether to normalize final scores to 0-1 range
            boost_keyword_matches: Whether to boost results with strong BM25 scores
            keyword_boost_weight: Weight for keyword boost (0.0-1.0)
        """
        self.rrf_k = rrf_k
        self.normalize_scores = normalize_scores
        self.boost_keyword_matches = boost_keyword_matches
        self.keyword_boost_weight = keyword_boost_weight

        logger.info(
            f"Initialized ReciprocalRankFusionRanker "
            f"(k={rrf_k}, normalize={normalize_scores}, boost_keywords={boost_keyword_matches})"
        )

    @component.output_types(documents=List[Document])
    def run(
        self,
        bm25_documents: List[Document],
        dense_documents: List[Document],
        top_k: Optional[int] = None,
    ) -> Dict[str, List[Document]]:
        """
        Fuse BM25 and dense search results using RRF.

        Args:
            bm25_documents: Results from BM25 keyword search
            dense_documents: Results from dense vector search
            top_k: Number of results to return (None = return all)

        Returns:
            Dict with 'documents' key containing fused and re-ranked results
        """
        logger.info(
            f"RRF fusion: {len(bm25_documents)} BM25 results + "
            f"{len(dense_documents)} dense results"
        )

        # Build document maps for deduplication and score tracking
        doc_map: Dict[str, Document] = {}
        rrf_scores: Dict[str, float] = defaultdict(float)
        bm25_scores: Dict[str, float] = {}
        dense_scores: Dict[str, float] = {}

        # Process BM25 results
        for rank, doc in enumerate(bm25_documents, start=1):
            doc_id = doc.id
            rrf_score = 1.0 / (self.rrf_k + rank)
            rrf_scores[doc_id] += rrf_score

            # Track original BM25 score
            bm25_scores[doc_id] = doc.score or 0.0

            # Store document (first occurrence wins for metadata)
            if doc_id not in doc_map:
                doc_map[doc_id] = doc

        # Process dense results
        for rank, doc in enumerate(dense_documents, start=1):
            doc_id = doc.id
            rrf_score = 1.0 / (self.rrf_k + rank)
            rrf_scores[doc_id] += rrf_score

            # Track original dense score
            dense_scores[doc_id] = doc.score or 0.0

            # Store document if not already present
            if doc_id not in doc_map:
                doc_map[doc_id] = doc

        # Build fused result list
        fused_documents = []
        raw_scores = []

        for doc_id, raw_rrf_score in rrf_scores.items():
            doc = doc_map[doc_id]
            raw_scores.append(raw_rrf_score)

            # Update document metadata
            doc.meta = doc.meta or {}
            doc.meta["rrf_score"] = raw_rrf_score
            doc.meta["bm25_score"] = bm25_scores.get(doc_id, 0.0)
            doc.meta["dense_score"] = dense_scores.get(doc_id, 0.0)

            # Determine match type
            has_bm25 = doc_id in bm25_scores
            has_dense = doc_id in dense_scores

            if has_bm25 and has_dense:
                # Found by both - determine which one ranked it higher
                if bm25_scores[doc_id] > dense_scores[doc_id]:
                    doc.meta["match_type"] = "bm25"
                else:
                    doc.meta["match_type"] = "semantic"
            elif has_bm25:
                doc.meta["match_type"] = "bm25"
            elif has_dense:
                doc.meta["match_type"] = "semantic"
            else:
                doc.meta["match_type"] = "hybrid"

            fused_documents.append(doc)

        # Normalize and boost scores
        if self.normalize_scores and raw_scores:
            fused_documents = self._normalize_and_boost_scores(
                fused_documents,
                raw_scores,
                bm25_scores,
            )
        else:
            # Just use raw RRF scores
            for doc in fused_documents:
                doc.score = doc.meta.get("rrf_score", 0.0)

        # Sort by final score descending
        fused_documents.sort(key=lambda d: d.score or 0.0, reverse=True)

        # Limit to top_k if specified
        if top_k is not None:
            fused_documents = fused_documents[:top_k]

        # Log statistics
        bm25_only_count = sum(1 for d in fused_documents if d.meta.get("match_type") == "bm25" and d.meta.get("dense_score", 0) == 0)
        dense_only_count = sum(1 for d in fused_documents if d.meta.get("match_type") == "semantic" and d.meta.get("bm25_score", 0) == 0)
        both_count = sum(1 for d in fused_documents if d.meta.get("bm25_score", 0) > 0 and d.meta.get("dense_score", 0) > 0)

        logger.info(
            f"RRF fusion complete: {len(fused_documents)} results "
            f"({bm25_only_count} BM25-only, {dense_only_count} dense-only, {both_count} in both)"
        )

        return {"documents": fused_documents}

    def _normalize_and_boost_scores(
        self,
        documents: List[Document],
        raw_scores: List[float],
        bm25_scores: Dict[str, float],
    ) -> List[Document]:
        """
        Normalize RRF scores to 0-1 range and boost keyword matches.

        Based on the normalization logic from HybridSearchEngine.

        Args:
            documents: Fused documents
            raw_scores: Raw RRF scores
            bm25_scores: Original BM25 scores by document ID

        Returns:
            Documents with normalized and boosted scores
        """
        if not documents or not raw_scores:
            return documents

        # Calculate score statistics
        min_score = min(raw_scores)
        max_score = max(raw_scores)
        score_range = max_score - min_score

        # Avoid division by zero
        if score_range < 1e-9:
            # All scores are the same, assign uniform scores
            for doc in documents:
                doc.score = 0.7
            return documents

        # Normalize and boost each document
        for i, doc in enumerate(documents):
            raw_rrf_score = raw_scores[i]

            # Step 1: Min-max normalization to 0-1
            normalized_score = (raw_rrf_score - min_score) / score_range

            # Step 2: Boost keyword matches if enabled
            keyword_boost = 0.0
            if self.boost_keyword_matches:
                bm25_score = bm25_scores.get(doc.id, 0.0)

                if bm25_score > 0:
                    # Normalize BM25 score and apply as boost
                    # Strong keyword matches (BM25 > 5) get significant boost
                    bm25_normalized = min(bm25_score / 10.0, 1.0)  # Cap at 1.0
                    keyword_boost = bm25_normalized * self.keyword_boost_weight

            # Step 3: Apply non-linear scaling for better score distribution
            # Use power scaling to spread out top results
            # RRF benefits from square root scaling to spread scores
            boosted_score = (normalized_score ** 0.7) + keyword_boost

            # Step 4: Ensure keyword-only matches get high scores
            # If BM25 score is very high and it's a top result, boost to 0.85+
            if bm25_scores.get(doc.id, 0.0) > 5.0 and i < 5:
                bm25_normalized = min(bm25_scores[doc.id] / 10.0, 1.0)
                boosted_score = max(boosted_score, 0.85 + (bm25_normalized * 0.1))

            # Clamp to 0-1 range
            boosted_score = max(0.0, min(1.0, boosted_score))

            # Update document score
            doc.score = boosted_score

            # Add debug info to metadata
            doc.meta["score_debug"] = {
                "raw_rrf_score": raw_rrf_score,
                "normalized_rrf": normalized_score,
                "keyword_boost": keyword_boost,
                "final_score": boosted_score,
            }

        logger.info(
            f"Score normalization complete: "
            f"raw range [{min_score:.4f}, {max_score:.4f}] -> normalized [0.0, 1.0]"
        )

        return documents


@component
class ScoreThresholdFilter:
    """
    Filters documents by minimum score threshold.

    Simple component to remove low-scoring results after ranking.
    """

    def __init__(self, score_threshold: float = 0.3):
        """
        Initialize score threshold filter.

        Args:
            score_threshold: Minimum score (0.0-1.0)
        """
        self.score_threshold = score_threshold
        logger.info(f"Initialized ScoreThresholdFilter (threshold={score_threshold})")

    @component.output_types(documents=List[Document])
    def run(
        self,
        documents: List[Document],
        score_threshold: Optional[float] = None,
    ) -> Dict[str, List[Document]]:
        """
        Filter documents by score threshold.

        Args:
            documents: Input documents
            score_threshold: Threshold to use (overrides default)

        Returns:
            Dict with 'documents' key containing filtered results
        """
        threshold = score_threshold if score_threshold is not None else self.score_threshold

        original_count = len(documents)
        filtered_documents = [
            doc for doc in documents
            if (doc.score or 0.0) >= threshold
        ]

        filtered_count = original_count - len(filtered_documents)
        if filtered_count > 0:
            logger.info(
                f"Filtered out {filtered_count} documents below threshold {threshold:.2f}"
            )

        return {"documents": filtered_documents}
