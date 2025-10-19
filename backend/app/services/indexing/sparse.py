"""
Sparse vector creation module for BM25-based keyword search.

This module handles the creation of sparse vectors for keyword-based search
using BM25 algorithm. Sparse vectors complement dense embeddings by providing
exact keyword matching capabilities.
"""

from typing import Dict, Any, Optional, List
import logging
import re
from collections import defaultdict

logger = logging.getLogger(__name__)


class SparseVectorGenerator:
    """
    Generator for BM25 sparse vectors.

    This class creates sparse vector representations of text for keyword-based
    search. It uses a hash-based token indexing approach compatible with
    Qdrant's sparse vector implementation.
    """

    def __init__(self):
        """Initialize the sparse vector generator."""
        logger.info("SparseVectorGenerator initialized")

    def create_bm25_vector(
        self, text: str, metadata_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create BM25 sparse vector from text and optional metadata.

        This implementation creates a simplified BM25-style sparse vector
        by tokenizing text and counting term frequencies. The sparse vector
        format is compatible with Qdrant's sparse vector storage.

        Args:
            text: Input text to vectorize
            metadata_text: Optional metadata text to include in search

        Returns:
            Dictionary with indices and values for sparse vector format:
            {
                "indices": [int, ...],  # Token hash indices
                "values": [float, ...]  # Token frequencies
            }
        """
        # Combine text and metadata for BM25 indexing
        combined_text = text
        if metadata_text:
            combined_text = f"{metadata_text}\n{text}"

        # Tokenize and create sparse vector
        token_counts = self._tokenize_and_count(combined_text)
        return self._create_sparse_vector(token_counts)

    def _tokenize_and_count(self, text: str) -> Dict[str, int]:
        """
        Tokenize text and count token frequencies.

        Performs simple tokenization by:
        1. Converting to lowercase
        2. Removing punctuation
        3. Splitting on whitespace
        4. Counting occurrences

        Args:
            text: Input text to tokenize

        Returns:
            Dictionary mapping tokens to their frequencies
        """
        # Convert to lowercase
        text = text.lower()

        # Remove punctuation, keeping only alphanumeric and spaces
        text = re.sub(r'[^\w\s]', ' ', text)

        # Split into tokens
        tokens = text.split()

        # Count token frequencies
        token_counts = defaultdict(int)
        for token in tokens:
            if token:  # Skip empty tokens
                token_counts[token] += 1

        return dict(token_counts)

    def _create_sparse_vector(
        self, token_counts: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Create sparse vector representation from token counts.

        Converts token frequencies into the sparse vector format expected
        by Qdrant. Uses hash-based indexing to map tokens to indices.

        Args:
            token_counts: Dictionary mapping tokens to frequencies

        Returns:
            Dictionary with indices and values arrays
        """
        indices = []
        values = []

        for token, count in token_counts.items():
            # Use hash for token->index mapping
            # Keep positive by using modulo with 2^31
            token_idx = hash(token) % (2**31)
            indices.append(token_idx)
            values.append(float(count))

        return {"indices": indices, "values": values}

    def create_batch_bm25_vectors(
        self,
        texts: List[str],
        metadata_texts: Optional[List[Optional[str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Create BM25 sparse vectors for multiple texts in batch.

        Args:
            texts: List of input texts to vectorize
            metadata_texts: Optional list of metadata texts (same length as texts)

        Returns:
            List of sparse vector dictionaries

        Raises:
            ValueError: If metadata_texts is provided but length doesn't match texts
        """
        if metadata_texts is not None and len(metadata_texts) != len(texts):
            raise ValueError(
                f"metadata_texts length ({len(metadata_texts)}) must match "
                f"texts length ({len(texts)})"
            )

        results = []
        for i, text in enumerate(texts):
            metadata = metadata_texts[i] if metadata_texts else None
            sparse_vector = self.create_bm25_vector(text, metadata)
            results.append(sparse_vector)

        return results

    def build_metadata_text(
        self, document_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Build searchable metadata text from document metadata.

        Extracts key metadata fields and combines them into a single
        searchable text string that will be included in the BM25 vector.

        Args:
            document_metadata: Dictionary containing document metadata

        Returns:
            Combined metadata text or None if no metadata
        """
        if not document_metadata:
            return None

        metadata_parts = []

        # Include filename (most important for search)
        if document_metadata.get('filename'):
            filename = document_metadata['filename']
            # Add filename with and without extension for better matching
            metadata_parts.append(filename)

            # Also add filename without extension
            import os
            filename_without_ext = os.path.splitext(filename)[0]
            if filename_without_ext != filename:
                metadata_parts.append(filename_without_ext)

        # Include document type if available
        if document_metadata.get('document_type'):
            metadata_parts.append(document_metadata['document_type'])

        # Include title if available
        if document_metadata.get('title'):
            metadata_parts.append(document_metadata['title'])

        # Include tags if available
        if document_metadata.get('tags'):
            tags = document_metadata['tags']
            if isinstance(tags, list):
                metadata_parts.extend(tags)
            elif isinstance(tags, str):
                metadata_parts.append(tags)

        # Combine metadata into searchable text
        return " ".join(metadata_parts) if metadata_parts else None
