"""
BM25 Sparse Vector Encoder

Generates sparse vectors for BM25-based keyword matching.
Used alongside dense embeddings for hybrid search in Qdrant.
"""

import logging
from typing import List, Dict, Optional, Tuple
import re
from collections import Counter
import math
import hashlib
import numpy as np

logger = logging.getLogger(__name__)


class BM25Encoder:
    """
    BM25 encoder for generating sparse vectors for keyword-based retrieval.

    Features:
    - TF-IDF-based sparse vectors
    - Configurable BM25 parameters (k1, b)
    - Token preprocessing for legal documents
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
        Initialize BM25 encoder.

        Args:
            k1: BM25 k1 parameter (term frequency saturation)
            b: BM25 b parameter (length normalization)
            epsilon: Small value to avoid division by zero
            use_legal_stopwords: Whether to filter legal-specific stopwords
        """
        self.k1 = k1
        self.b = b
        self.epsilon = epsilon
        self.use_legal_stopwords = use_legal_stopwords

        # Document statistics
        self.doc_freqs: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.doc_lengths: List[int] = []
        self.avg_doc_length: float = 0.0
        self.num_docs: int = 0

        # Legal-specific stopwords (in addition to common English stopwords)
        self.legal_stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'must', 'can', 'shall',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it',
            'we', 'they', 'what', 'which', 'who', 'when', 'where', 'why', 'how',
        }

        logger.info(f"Initialized BM25Encoder (k1={k1}, b={b})")

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text for BM25 encoding.

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        # Convert to lowercase
        text = text.lower()

        # Remove special characters but keep alphanumeric and spaces
        text = re.sub(r'[^a-z0-9\s]', ' ', text)

        # Split into tokens
        tokens = text.split()

        # Filter stopwords if enabled
        if self.use_legal_stopwords:
            tokens = [t for t in tokens if t not in self.legal_stopwords]

        # Remove very short tokens (< 2 chars)
        tokens = [t for t in tokens if len(t) >= 2]

        return tokens

    def fit(self, documents: List[str]) -> None:
        """
        Fit the BM25 model on a corpus of documents.

        This computes document frequencies and IDF scores.

        Args:
            documents: List of document texts
        """
        logger.info(f"Fitting BM25 on {len(documents)} documents")

        self.num_docs = len(documents)
        self.doc_freqs = {}
        self.doc_lengths = []

        # Count document frequencies
        for doc in documents:
            tokens = self.tokenize(doc)
            self.doc_lengths.append(len(tokens))

            # Count unique tokens in this document
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

        # Compute average document length
        self.avg_doc_length = sum(self.doc_lengths) / max(len(self.doc_lengths), 1)

        # Compute IDF scores
        self.idf = {}
        for token, df in self.doc_freqs.items():
            # IDF formula: log((N - df + 0.5) / (df + 0.5) + 1)
            idf_score = math.log(
                (self.num_docs - df + 0.5) / (df + 0.5) + 1
            )
            self.idf[token] = idf_score

        logger.info(f"BM25 fitted: {len(self.doc_freqs)} unique tokens, avg_doc_len={self.avg_doc_length:.2f}")

    def encode(self, text: str) -> Dict[str, float]:
        """
        Encode a single document into a BM25 sparse vector.

        Args:
            text: Document text

        Returns:
            Dictionary mapping token indices to BM25 scores
        """
        tokens = self.tokenize(text)
        doc_length = len(tokens)

        # Count term frequencies
        term_freqs = Counter(tokens)

        # Compute BM25 scores
        bm25_scores = {}

        # If not fitted, use default values for better keyword matching
        if not self.idf:
            # Not fitted - use TF-based scoring with default IDF
            default_idf = 2.0  # Reasonable default IDF value
            avg_len = 100.0  # Assume average document length

            for token, tf in term_freqs.items():
                # BM25 formula with default values
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (
                    1 - self.b + self.b * (doc_length / avg_len)
                )
                bm25_score = default_idf * (numerator / denominator)

                if bm25_score > 0:
                    bm25_scores[token] = float(bm25_score)
        else:
            # Fitted - use actual IDF scores
            for token, tf in term_freqs.items():
                # Get IDF (or use default if token not seen during fitting)
                idf_score = self.idf.get(token, 1.0)  # Increased from epsilon (0.25) to 1.0

                # BM25 formula
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (
                    1 - self.b + self.b * (doc_length / max(self.avg_doc_length, 1))
                )
                bm25_score = idf_score * (numerator / denominator)

                if bm25_score > 0:
                    bm25_scores[token] = float(bm25_score)

        return bm25_scores

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

        Args:
            text: Document text
            token_to_id: Optional mapping from tokens to indices

        Returns:
            Tuple of (indices, values) for Qdrant sparse vector
        """
        bm25_scores = self.encode(text)

        if token_to_id is None:
            # Auto-generate token IDs based on hash
            token_to_id = {}

        indices = []
        values = []

        for token, score in bm25_scores.items():
            # Get or create token ID using deterministic hash
            if token not in token_to_id:
                # Use SHA256 for deterministic hashing across Python processes
                token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
                token_to_id[token] = int(token_hash[:8], 16)  # Use first 8 hex chars (32-bit)

            token_id = token_to_id[token]
            indices.append(token_id)
            values.append(score)

        # Sort by indices
        sorted_pairs = sorted(zip(indices, values))
        if sorted_pairs:
            indices, values = zip(*sorted_pairs)
            return list(indices), list(values)
        else:
            return [], []

    def batch_encode_to_qdrant_format(
        self,
        texts: List[str],
    ) -> List[Tuple[List[int], List[float]]]:
        """
        Batch encode texts to Qdrant sparse vector format.

        Args:
            texts: List of document texts

        Returns:
            List of (indices, values) tuples
        """
        logger.info(f"Batch encoding {len(texts)} texts to Qdrant format")

        # Build shared token_to_id mapping
        token_to_id: Dict[str, int] = {}

        results = []
        for text in texts:
            sparse_vec = self.encode_to_qdrant_format(text, token_to_id)
            results.append(sparse_vec)

        return results

    def get_top_tokens(self, text: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Get the top-k tokens with highest BM25 scores.

        Args:
            text: Document text
            top_k: Number of top tokens to return

        Returns:
            List of (token, score) tuples sorted by score
        """
        bm25_scores = self.encode(text)
        sorted_tokens = sorted(bm25_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_tokens[:top_k]

    def get_stats(self) -> Dict[str, any]:
        """
        Get statistics about the BM25 model.

        Returns:
            Dictionary with model statistics
        """
        return {
            "num_docs": self.num_docs,
            "vocab_size": len(self.doc_freqs),
            "avg_doc_length": self.avg_doc_length,
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

    Args:
        text: Text to encode
        corpus: Optional corpus to fit BM25 model (if None, fits on single text)
        k1: BM25 k1 parameter
        b: BM25 b parameter

    Returns:
        BM25 sparse vector as dictionary
    """
    encoder = BM25Encoder(k1=k1, b=b)

    if corpus:
        encoder.fit(corpus)
    else:
        encoder.fit([text])

    return encoder.encode(text)
