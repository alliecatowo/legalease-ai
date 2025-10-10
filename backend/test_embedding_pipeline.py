"""
Test script for embedding generation pipeline.

Tests both dense embeddings (EmbeddingPipeline) and sparse vectors (BM25Encoder).
"""

import sys
import logging
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.workers.pipelines.embeddings import EmbeddingPipeline
from app.workers.pipelines.bm25_encoder import BM25Encoder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_embedding_pipeline():
    """Test the dense embedding pipeline."""
    logger.info("=" * 80)
    logger.info("Testing EmbeddingPipeline (Dense Vectors)")
    logger.info("=" * 80)

    # Sample legal document texts
    texts = [
        "This is a contract between Party A and Party B for the sale of goods.",
        "The plaintiff alleges breach of contract and seeks damages.",
        "The defendant denies all allegations and moves to dismiss.",
        "Whereas the parties agree to the following terms and conditions.",
        "This agreement shall be governed by the laws of the State of California.",
    ]

    # Initialize the pipeline
    logger.info("\n1. Initializing EmbeddingPipeline...")
    pipeline = EmbeddingPipeline(
        model_name="BAAI/bge-base-en-v1.5",
        batch_size=32,
        normalize_embeddings=True,
    )

    # Get model info
    info = pipeline.get_model_info()
    logger.info(f"\nModel Information:")
    for key, value in info.items():
        logger.info(f"  {key}: {value}")

    # Generate embeddings
    logger.info(f"\n2. Generating embeddings for {len(texts)} texts...")
    embeddings = pipeline.generate_embeddings(texts, show_progress=True)
    logger.info(f"Embeddings shape: {embeddings.shape}")
    logger.info(f"First embedding (first 10 dims): {embeddings[0][:10]}")

    # Test single embedding
    logger.info("\n3. Testing single embedding generation...")
    single_text = "Test legal document about contract law."
    single_embedding = pipeline.generate_single_embedding(single_text)
    logger.info(f"Single embedding shape: {single_embedding.shape}")

    # Test similarity computation
    logger.info("\n4. Testing similarity computation...")
    similarity = pipeline.compute_similarity(embeddings[0], embeddings[1])
    logger.info(f"Similarity between text 0 and text 1: {similarity:.4f}")

    # Test multi-size embeddings
    logger.info("\n5. Testing multi-size embeddings...")
    texts_by_size = {
        "summary": ["This is a summary of the entire legal case."],
        "section": [
            "Section 1: Introduction to the case",
            "Section 2: Facts and background",
        ],
        "microblock": [
            "The plaintiff filed the complaint on January 1, 2024.",
            "The defendant responded with a motion to dismiss.",
            "The court scheduled a hearing for February 15, 2024.",
        ],
    }

    embeddings_by_size = pipeline.generate_embeddings_by_size(texts_by_size)
    for size_type, embs in embeddings_by_size.items():
        logger.info(f"  {size_type}: {embs.shape}")

    logger.info("\n" + "=" * 80)
    logger.info("EmbeddingPipeline test completed successfully!")
    logger.info("=" * 80 + "\n")

    return pipeline, embeddings


def test_bm25_encoder():
    """Test the BM25 sparse vector encoder."""
    logger.info("=" * 80)
    logger.info("Testing BM25Encoder (Sparse Vectors)")
    logger.info("=" * 80)

    # Sample corpus for fitting
    corpus = [
        "This is a contract between Party A and Party B for the sale of goods.",
        "The plaintiff alleges breach of contract and seeks damages.",
        "The defendant denies all allegations and moves to dismiss.",
        "Whereas the parties agree to the following terms and conditions.",
        "This agreement shall be governed by the laws of the State of California.",
        "The court finds in favor of the plaintiff and awards monetary damages.",
        "The arbitration clause requires disputes to be resolved through mediation.",
        "All parties must sign the agreement before it becomes binding.",
    ]

    # Initialize and fit the encoder
    logger.info("\n1. Initializing and fitting BM25Encoder...")
    encoder = BM25Encoder(k1=1.5, b=0.75)
    encoder.fit(corpus)

    # Get encoder info
    info = encoder.get_encoder_info()
    logger.info(f"\nEncoder Information:")
    for key, value in info.items():
        logger.info(f"  {key}: {value}")

    # Encode a single text
    logger.info("\n2. Encoding a single text...")
    test_text = "The plaintiff seeks damages for breach of contract."
    indices, values = encoder.encode(test_text)
    logger.info(f"Sparse vector has {len(indices)} non-zero dimensions")
    logger.info(f"Indices (first 10): {indices[:10]}")
    logger.info(f"Values (first 10): {[f'{v:.4f}' for v in values[:10]]}")

    # Decode to see tokens
    logger.info("\n3. Decoding sparse vector (top 5 tokens)...")
    token_scores = encoder.decode_sparse_vector(indices, values, top_k=5)
    for token, score in token_scores:
        logger.info(f"  '{token}': {score:.4f}")

    # Encode for Qdrant
    logger.info("\n4. Encoding for Qdrant format...")
    qdrant_sparse = encoder.encode_for_qdrant(test_text)
    logger.info(f"Qdrant sparse vector keys: {list(qdrant_sparse.keys())}")
    logger.info(f"Number of non-zero values: {len(qdrant_sparse['values'])}")

    # Batch encoding
    logger.info("\n5. Testing batch encoding...")
    batch_texts = [
        "Contract law governs agreements between parties.",
        "The court ruled in favor of the defendant.",
        "Mediation can resolve disputes without litigation.",
    ]
    batch_sparse = encoder.encode_batch_for_qdrant(batch_texts)
    logger.info(f"Encoded {len(batch_sparse)} texts")
    for i, sparse in enumerate(batch_sparse):
        logger.info(f"  Text {i}: {len(sparse['indices'])} non-zero dimensions")

    logger.info("\n" + "=" * 80)
    logger.info("BM25Encoder test completed successfully!")
    logger.info("=" * 80 + "\n")

    return encoder


def test_combined_pipeline():
    """Test using both dense and sparse vectors together."""
    logger.info("=" * 80)
    logger.info("Testing Combined Dense + Sparse Pipeline for Qdrant")
    logger.info("=" * 80)

    # Sample documents
    documents = [
        "This is a contract for the sale of real property.",
        "The plaintiff alleges negligence and seeks compensation.",
        "The terms and conditions are outlined in Section 5.",
    ]

    # Initialize both pipelines
    logger.info("\n1. Initializing both pipelines...")
    embedding_pipeline = EmbeddingPipeline(model_name="BAAI/bge-base-en-v1.5")
    bm25_encoder = BM25Encoder()
    bm25_encoder.fit(documents)

    # Generate both vector types
    logger.info("\n2. Generating dense and sparse vectors...")

    test_doc = "The contract includes a clause about property rights."

    # Dense embedding
    dense_vector = embedding_pipeline.generate_single_embedding(test_doc)
    logger.info(f"Dense vector dimension: {len(dense_vector)}")
    logger.info(f"Dense vector (first 5): {dense_vector[:5]}")

    # Sparse vector
    sparse_vector = bm25_encoder.encode_for_qdrant(test_doc)
    logger.info(f"Sparse vector non-zero dims: {len(sparse_vector['indices'])}")
    logger.info(f"Sparse indices (first 5): {sparse_vector['indices'][:5]}")
    logger.info(f"Sparse values (first 5): {[f'{v:.4f}' for v in sparse_vector['values'][:5]]}")

    # Create a Qdrant-compatible point
    logger.info("\n3. Creating Qdrant-compatible point structure...")
    point = {
        "id": 1,
        "vector": {
            "dense": dense_vector.tolist(),
            "sparse": sparse_vector,
        },
        "payload": {
            "text": test_doc,
            "doc_type": "contract",
        },
    }

    logger.info("Point structure created successfully:")
    logger.info(f"  - ID: {point['id']}")
    logger.info(f"  - Dense vector length: {len(point['vector']['dense'])}")
    logger.info(f"  - Sparse vector non-zero dims: {len(point['vector']['sparse']['indices'])}")
    logger.info(f"  - Payload keys: {list(point['payload'].keys())}")

    logger.info("\n" + "=" * 80)
    logger.info("Combined pipeline test completed successfully!")
    logger.info("=" * 80 + "\n")

    return point


def main():
    """Run all tests."""
    logger.info("\n\n")
    logger.info("*" * 80)
    logger.info("EMBEDDING GENERATION PIPELINE TEST SUITE")
    logger.info("*" * 80)
    logger.info("\n")

    try:
        # Test dense embeddings
        embedding_pipeline, embeddings = test_embedding_pipeline()

        # Test sparse vectors
        bm25_encoder = test_bm25_encoder()

        # Test combined usage
        point = test_combined_pipeline()

        logger.info("\n" + "*" * 80)
        logger.info("ALL TESTS PASSED SUCCESSFULLY!")
        logger.info("*" * 80)
        logger.info("\nThe embedding pipeline is ready for use with Qdrant.")
        logger.info("You can now use EmbeddingPipeline and BM25Encoder in your application.")

    except Exception as e:
        logger.error(f"\n\nTEST FAILED: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
