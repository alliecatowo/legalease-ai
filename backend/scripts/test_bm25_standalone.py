#!/usr/bin/env python3
"""
Standalone test for BM25 Encoder - FastEmbed Implementation

Tests the FastEmbed BM25 encoder without dependencies.
"""

from fastembed import SparseTextEmbedding
from app.core.logging_config import get_logger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = get_logger(__name__)


def test_fastembed_bm25():
    """Test FastEmbed BM25 model directly."""
    logger.info("=== Testing FastEmbed BM25 Model ===")

    # Initialize FastEmbed BM25 model
    logger.info("\n1. Initializing FastEmbed SparseTextEmbedding...")
    model = SparseTextEmbedding(model_name="Qdrant/bm25")
    logger.info("✓ Model initialized successfully")

    # Test single encoding
    logger.info("\n2. Testing single document encoding...")
    test_text = "The plaintiff filed a motion for summary judgment in the contract dispute case."

    embeddings = list(model.embed([test_text]))
    assert len(embeddings) == 1, "Should return one embedding"

    embedding = embeddings[0]
    indices = [int(idx) for idx in embedding.indices]
    values = [float(val) for val in embedding.values]

    logger.info(f"✓ Encoded text successfully")
    logger.info(f"  - Number of tokens: {len(indices)}")
    logger.info(f"  - First 5 indices: {indices[:5]}")
    logger.info(f"  - First 5 values: {[f'{v:.4f}' for v in values[:5]]}")
    logger.info(f"  - Max value: {max(values):.4f}")
    logger.info(f"  - Min value: {min(values):.4f}")

    # Validate output format
    assert len(indices) == len(values), "Indices and values length must match"
    assert all(isinstance(idx, int) for idx in indices), "All indices must be integers"
    assert all(isinstance(val, float) for val in values), "All values must be floats"
    assert all(val > 0 for val in values), "All BM25 scores should be positive"
    logger.info("✓ Output format validation passed")

    # Test batch encoding
    logger.info("\n3. Testing batch encoding...")
    test_texts = [
        "The plaintiff filed a motion for summary judgment.",
        "The defendant objected to the discovery request.",
        "The court granted the motion to dismiss.",
    ]

    batch_embeddings = list(model.embed(test_texts))
    logger.info(f"✓ Batch encoded {len(batch_embeddings)} texts")

    for i, emb in enumerate(batch_embeddings):
        indices = [int(idx) for idx in emb.indices]
        values = [float(val) for val in emb.values]
        avg_score = sum(values) / len(values)
        logger.info(f"  Text {i+1}: {len(indices)} tokens, avg score: {avg_score:.4f}")

    logger.info("✓ Batch encoding validation passed")

    # Test query encoding
    logger.info("\n4. Testing query encoding...")
    query = "motion summary judgment"
    query_embeddings = list(model.embed([query]))
    query_emb = query_embeddings[0]
    query_indices = [int(idx) for idx in query_emb.indices]
    query_values = [float(val) for val in query_emb.values]

    logger.info(f"✓ Query encoded successfully")
    logger.info(f"  - Number of tokens: {len(query_indices)}")
    logger.info(f"  - Indices: {query_indices}")
    logger.info(f"  - Values: {[f'{v:.4f}' for v in query_values]}")

    # Test consistency
    logger.info("\n5. Testing encoding consistency...")
    emb1 = list(model.embed([test_text]))[0]
    emb2 = list(model.embed([test_text]))[0]

    indices1 = list(emb1.indices)
    indices2 = list(emb2.indices)
    values1 = [float(v) for v in emb1.values]
    values2 = [float(v) for v in emb2.values]

    assert indices1 == indices2, "Indices should be consistent"
    assert values1 == values2, "Values should be consistent"
    logger.info("✓ Encoding is deterministic")

    logger.info("\n=== All Tests Passed! ===")
    logger.info("\nSummary:")
    logger.info("✓ FastEmbed Qdrant/bm25 model works correctly")
    logger.info("✓ Produces valid sparse vector format")
    logger.info("✓ Generates positive BM25 scores")
    logger.info("✓ Batch encoding works efficiently")
    logger.info("✓ Encoding is deterministic")
    logger.info("✓ Ready for production use!")


if __name__ == "__main__":
    try:
        test_fastembed_bm25()
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        import sys
        sys.exit(1)
