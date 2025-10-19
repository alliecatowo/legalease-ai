"""
Score Normalization and Fusion Logic

Handles score normalization, boosting, and fusion for hybrid search results.
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def normalize_and_boost_scores(
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
            "raw_fusion_score": raw_scores[i],
            "normalized_fusion": normalized_score,
            "actual_bm25_score": bm25_score,
            "actual_dense_score": result.get("dense_score", 0.0),
            "keyword_boost": keyword_boost,
            "final_score": boosted_score,
        }

    logger.info(
        f"Score normalization complete: "
        f"raw range [{min_score:.4f}, {max_score:.4f}] -> "
        f"normalized range [0.0, 1.0]"
    )

    return results
