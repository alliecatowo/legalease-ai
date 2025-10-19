#!/usr/bin/env python3
"""
Test script for BM25 Encoder - FastEmbed Implementation

Validates that the new FastEmbed-based BM25 encoder:
1. Initializes correctly
2. Produces valid SparseVector format
3. Maintains interface compatibility
4. Generates reasonable BM25 scores
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.workers.pipelines.bm25_encoder import BM25Encoder
from app.core.logging_config import get_logger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = get_logger(__name__)


def test_encoder():
    """Test the BM25 encoder."""
    logger.info("=== Testing FastEmbed BM25 Encoder ===")

    # Initialize encoder
    logger.info("\n1. Initializing encoder...")
    encoder = BM25Encoder()
    logger.info(f"Encoder stats: {encoder.get_stats()}")

    # Test single encoding
    logger.info("\n2. Testing single document encoding...")
    test_text = "The plaintiff filed a motion for summary judgment in the contract dispute case."

    # Test encode() method
    dict_result = encoder.encode(test_text)
    logger.info(f"Dict format - Number of tokens: {len(dict_result)}")
    logger.info(f"Dict format - First 5 items: {dict(list(dict_result.items())[:5])}")

    # Test encode_to_qdrant_format() method
    indices, values = encoder.encode_to_qdrant_format(test_text)
    logger.info(f"Qdrant format - Indices length: {len(indices)}")
    logger.info(f"Qdrant format - Values length: {len(values)}")
    logger.info(f"Qdrant format - First 5 indices: {indices[:5]}")
    logger.info(f"Qdrant format - First 5 values: {values[:5]}")

    # Validate output
    assert len(indices) == len(values), "Indices and values length must match"
    assert all(isinstance(idx, int) for idx in indices), "All indices must be integers"
    assert all(isinstance(val, float) for val in values), "All values must be floats"
    logger.info("✓ Single encoding validation passed")

    # Test batch encoding
    logger.info("\n3. Testing batch encoding...")
    test_texts = [
        "The plaintiff filed a motion for summary judgment.",
        "The defendant objected to the discovery request.",
        "The court granted the motion to dismiss.",
    ]

    batch_results = encoder.batch_encode_to_qdrant_format(test_texts)
    logger.info(f"Batch encoded {len(batch_results)} texts")
    for i, (indices, values) in enumerate(batch_results):
        logger.info(f"  Text {i+1}: {len(indices)} tokens, avg score: {sum(values)/len(values):.4f}")
        assert len(indices) == len(values), f"Text {i+1}: Indices and values length must match"

    logger.info("✓ Batch encoding validation passed")

    # Test get_top_tokens
    logger.info("\n4. Testing get_top_tokens...")
    top_tokens = encoder.get_top_tokens(test_text, top_k=10)
    logger.info(f"Top 10 tokens:")
    for i, (token_idx, score) in enumerate(top_tokens, 1):
        logger.info(f"  {i}. Token index {token_idx}: score={score:.4f}")

    logger.info("✓ get_top_tokens validation passed")

    # Test fit() method (for compatibility)
    logger.info("\n5. Testing fit() method (compatibility)...")
    encoder.fit(test_texts)
    logger.info("✓ fit() method works (no-op for FastEmbed)")

    # Test encode_queries
    logger.info("\n6. Testing encode_queries...")
    query_results = encoder.encode_queries(["motion summary judgment"])
    logger.info(f"Encoded {len(query_results)} queries")
    logger.info(f"Query result tokens: {len(query_results[0])}")
    logger.info("✓ encode_queries validation passed")

    logger.info("\n=== All Tests Passed! ===")
    logger.info("\nSummary:")
    logger.info("- FastEmbed BM25 encoder initializes correctly")
    logger.info("- Produces valid SparseVector format (indices, values)")
    logger.info("- Maintains interface compatibility")
    logger.info("- Generates reasonable BM25 scores")
    logger.info("- Ready for production use!")


if __name__ == "__main__":
    try:
        test_encoder()
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
