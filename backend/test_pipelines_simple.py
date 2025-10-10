"""
Simple test for embedding pipelines without app dependencies.
"""

import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import directly from the pipeline files
sys.path.insert(0, str(Path(__file__).parent / "app" / "workers" / "pipelines"))

from embeddings import EmbeddingPipeline
from bm25_encoder import BM25Encoder


def test_embeddings():
    """Test embedding generation."""
    logger.info("=" * 80)
    logger.info("Testing Dense Embeddings")
    logger.info("=" * 80)

    texts = [
        "This contract governs the sale of goods between parties.",
        "The plaintiff seeks damages for breach of contract.",
        "The defendant denies liability and moves to dismiss.",
    ]

    pipeline = EmbeddingPipeline(
        model_name="BAAI/bge-base-en-v1.5",
        batch_size=32,
    )

    logger.info(f"Model info: {pipeline.get_model_info()}")

    embeddings = pipeline.generate_embeddings(texts)
    logger.info(f"Generated embeddings shape: {embeddings.shape}")
    logger.info(f"First embedding (first 5 dims): {embeddings[0][:5]}")

    # Test similarity
    similarity = pipeline.compute_similarity(embeddings[0], embeddings[1])
    logger.info(f"Similarity between doc 0 and 1: {similarity:.4f}")

    logger.info("Dense embeddings test PASSED\n")
    return pipeline


def test_bm25():
    """Test BM25 encoding."""
    logger.info("=" * 80)
    logger.info("Testing BM25 Sparse Vectors")
    logger.info("=" * 80)

    corpus = [
        "This contract governs the sale of goods between parties.",
        "The plaintiff seeks damages for breach of contract.",
        "The defendant denies liability and moves to dismiss.",
        "The court finds in favor of the plaintiff.",
        "All parties must comply with arbitration procedures.",
    ]

    encoder = BM25Encoder(k1=1.5, b=0.75)
    encoder.fit(corpus)

    logger.info(f"Encoder stats: {encoder.get_stats()}")

    test_text = "The plaintiff alleges breach of contract."
    indices, values = encoder.encode_to_qdrant_format(test_text)

    logger.info(f"Sparse vector has {len(indices)} non-zero dimensions")
    logger.info(f"Indices (first 10): {indices[:10]}")
    logger.info(f"Values (first 10): {[f'{v:.4f}' for v in values[:10]]}")

    # Get top tokens
    top_tokens = encoder.get_top_tokens(test_text, top_k=5)
    logger.info(f"Top 5 tokens:")
    for token, score in top_tokens:
        logger.info(f"  '{token}': {score:.4f}")

    logger.info("BM25 sparse vectors test PASSED\n")
    return encoder


def test_combined():
    """Test combined dense + sparse for Qdrant."""
    logger.info("=" * 80)
    logger.info("Testing Combined Pipeline for Qdrant")
    logger.info("=" * 80)

    # Sample documents
    documents = [
        "This is a contract for the sale of real property.",
        "The plaintiff alleges negligence and seeks compensation.",
        "The terms and conditions are outlined in Section 5.",
    ]

    # Initialize pipelines
    embedding_pipeline = EmbeddingPipeline()
    bm25_encoder = BM25Encoder()
    bm25_encoder.fit(documents)

    # Test document
    test_doc = "The contract includes a clause about property rights."

    # Generate both vectors
    dense_vector = embedding_pipeline.generate_single_embedding(test_doc)
    sparse_indices, sparse_values = bm25_encoder.encode_to_qdrant_format(test_doc)

    logger.info(f"Dense vector dimension: {len(dense_vector)}")
    logger.info(f"Sparse vector non-zero dims: {len(sparse_indices)}")

    # Create Qdrant point structure
    point = {
        "id": 1,
        "vector": {
            "dense": dense_vector.tolist(),
            "sparse": {
                "indices": sparse_indices,
                "values": sparse_values,
            },
        },
        "payload": {
            "text": test_doc,
            "doc_type": "contract",
        },
    }

    logger.info("Qdrant point structure:")
    logger.info(f"  - ID: {point['id']}")
    logger.info(f"  - Dense vector length: {len(point['vector']['dense'])}")
    logger.info(f"  - Sparse indices length: {len(point['vector']['sparse']['indices'])}")
    logger.info(f"  - Sparse values length: {len(point['vector']['sparse']['values'])}")
    logger.info(f"  - Payload keys: {list(point['payload'].keys())}")

    logger.info("Combined pipeline test PASSED\n")
    return point


def main():
    """Run all tests."""
    logger.info("\n" + "*" * 80)
    logger.info("EMBEDDING PIPELINE TEST SUITE")
    logger.info("*" * 80 + "\n")

    try:
        # Test dense embeddings
        pipeline = test_embeddings()

        # Test sparse BM25
        encoder = test_bm25()

        # Test combined
        point = test_combined()

        logger.info("*" * 80)
        logger.info("ALL TESTS PASSED!")
        logger.info("*" * 80)
        logger.info("\nThe embedding pipeline is ready for Qdrant integration.")

    except Exception as e:
        logger.error(f"TEST FAILED: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
