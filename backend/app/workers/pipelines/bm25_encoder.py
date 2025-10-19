"""
BM25 Sparse Vector Encoder - FastEmbed Implementation

Generates sparse vectors for BM25-based keyword matching using FastEmbed's
Qdrant/bm25 model. This replaces the custom BM25 implementation with a
production-ready FastEmbed model that leverages Qdrant's native IDF support.
"""

from typing import List, Dict, Optional, Tuple
from fastembed import SparseTextEmbedding
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class BM25Encoder:
    """
    BM25 encoder using FastEmbed's Qdrant/bm25 model.

    Features:
    - Production-ready BM25 implementation via FastEmbed
    - Leverages Qdrant's native IDF support (Modifier.IDF)
    - Drop-in replacement for custom BM25 encoder
    - Qdrant-compatible sparse vector format
    """

    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        epsilon: float = 0.25,
        use_legal_stopwords: bool = True,
    ):
        """
        Initialize BM25 encoder with FastEmbed.

        Args:
            k1: BM25 k1 parameter (kept for interface compatibility, not used)
            b: BM25 b parameter (kept for interface compatibility, not used)
            epsilon: Small value (kept for interface compatibility, not used)
            use_legal_stopwords: Whether to filter stopwords (kept for interface compatibility, not used)

        Note: Parameters are kept for backward compatibility but not used.
        FastEmbed's Qdrant/bm25 model uses its own internal parameters.
        """
        self.k1 = k1
        self.b = b
        self.epsilon = epsilon
        self.use_legal_stopwords = use_legal_stopwords

        # Initialize FastEmbed BM25 model
        # This model is specifically designed for Qdrant and produces
        # sparse vectors with proper BM25 scoring
        self.model = SparseTextEmbedding(model_name="Qdrant/bm25")

        # Statistics (for compatibility with old interface)
        self.num_docs = 0
        self.doc_freqs: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.doc_lengths: List[int] = []
        self.avg_doc_length: float = 0.0

        logger.info("Initialized BM25Encoder with FastEmbed (model=Qdrant/bm25)")

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text (for interface compatibility).

        Note: FastEmbed handles tokenization internally.
        This method is kept for backward compatibility.

        Args:
            text: Input text

        Returns:
            Empty list (tokenization handled by FastEmbed)
        """
        # FastEmbed handles tokenization internally
        # Return empty list for compatibility
        return []

    def fit(self, documents: List[str]) -> None:
        """
        Fit the BM25 model (for interface compatibility).

        Note: FastEmbed's Qdrant/bm25 model is pre-trained and doesn't
        require fitting. This method is kept for backward compatibility
        and logs a warning.

        Args:
            documents: List of document texts (ignored)
        """
        logger.info(
            f"BM25Encoder.fit() called with {len(documents)} documents - "
            "FastEmbed model is pre-trained, no fitting needed"
        )
        self.num_docs = len(documents)

    def encode(self, text: str) -> Dict[str, float]:
        """
        Encode a single document into a BM25 sparse vector.

        Note: This returns a dictionary format for compatibility.
        For Qdrant indexing, use encode_to_qdrant_format() instead.

        Args:
            text: Document text

        Returns:
            Dictionary mapping token indices to BM25 scores
        """
        # Use FastEmbed to generate sparse embedding
        embeddings = list(self.model.embed([text]))

        if not embeddings:
            return {}

        embedding = embeddings[0]

        # Convert to dictionary format (index -> score)
        result = {}
        for idx, value in zip(embedding.indices, embedding.values):
            result[str(idx)] = float(value)

        return result

    def encode_queries(self, queries: List[str]) -> List[Dict[str, float]]:
        """
        Encode multiple queries into BM25 sparse vectors.

        Args:
            queries: List of query texts

        Returns:
            List of sparse vector dictionaries
        """
        logger.info(f"Encoding {len(queries)} queries")
        return [self.encode(query) for query in queries]

    def encode_to_qdrant_format(
        self,
        text: str,
        token_to_id: Optional[Dict[str, int]] = None,
    ) -> Tuple[List[int], List[float]]:
        """
        Encode text to Qdrant sparse vector format.

        This is the primary method for generating sparse vectors for Qdrant.
        FastEmbed produces vectors in the correct format directly.

        Args:
            text: Document text
            token_to_id: Optional mapping (ignored, FastEmbed handles this)

        Returns:
            Tuple of (indices, values) for Qdrant sparse vector
        """
        # Use FastEmbed to generate sparse embedding
        embeddings = list(self.model.embed([text]))

        if not embeddings:
            return [], []

        embedding = embeddings[0]

        # FastEmbed already returns indices and values in correct format
        indices = [int(idx) for idx in embedding.indices]
        values = [float(val) for val in embedding.values]

        return indices, values

    def batch_encode_to_qdrant_format(
        self,
        texts: List[str],
    ) -> List[Tuple[List[int], List[float]]]:
        """
        Batch encode texts to Qdrant sparse vector format.

        This is optimized for batch processing using FastEmbed's
        built-in batching capabilities.

        Args:
            texts: List of document texts

        Returns:
            List of (indices, values) tuples
        """
        logger.info(f"Batch encoding {len(texts)} texts to Qdrant format")

        results = []

        # FastEmbed's embed() method handles batching efficiently
        for embedding in self.model.embed(texts):
            indices = [int(idx) for idx in embedding.indices]
            values = [float(val) for val in embedding.values]
            results.append((indices, values))

        return results

    def get_top_tokens(self, text: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Get the top-k tokens with highest BM25 scores.

        Note: FastEmbed doesn't expose token strings, only indices.
        This method returns (index_as_string, score) for compatibility.

        Args:
            text: Document text
            top_k: Number of top tokens to return

        Returns:
            List of (token_index, score) tuples sorted by score
        """
        indices, values = self.encode_to_qdrant_format(text)

        # Combine and sort by values
        token_scores = list(zip(indices, values))
        token_scores.sort(key=lambda x: x[1], reverse=True)

        # Return top-k as (index_as_string, score)
        return [(str(idx), score) for idx, score in token_scores[:top_k]]

    def get_stats(self) -> Dict[str, any]:
        """
        Get statistics about the BM25 model.

        Returns:
            Dictionary with model statistics
        """
        return {
            "model_name": "Qdrant/bm25",
            "model_type": "FastEmbed SparseTextEmbedding",
            "num_docs": self.num_docs,
            "vocab_size": 0,  # Not exposed by FastEmbed
            "avg_doc_length": 0.0,  # Not tracked by FastEmbed
            "k1": self.k1,
            "b": self.b,
            "use_legal_stopwords": self.use_legal_stopwords,
        }


# Convenience function for quick encoding
def encode_bm25(
    text: str,
    corpus: Optional[List[str]] = None,
    k1: float = 1.5,
    b: float = 0.75,
) -> Dict[str, float]:
    """
    Convenience function to encode text with BM25.

    Note: Corpus parameter is ignored as FastEmbed model is pre-trained.

    Args:
        text: Text to encode
        corpus: Optional corpus (ignored)
        k1: BM25 k1 parameter (ignored)
        b: BM25 b parameter (ignored)

    Returns:
        BM25 sparse vector as dictionary
    """
    encoder = BM25Encoder(k1=k1, b=b)
    return encoder.encode(text)
