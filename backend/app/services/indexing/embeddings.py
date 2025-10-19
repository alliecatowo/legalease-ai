"""
Embedding generation module for document indexing.

This module handles the generation of dense vector embeddings for text chunks.
It supports multi-vector embeddings (summary, section, microblock) for hierarchical
semantic search capabilities.
"""

from typing import Dict, List
import logging

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generator for multi-vector dense embeddings.

    This class handles the creation of semantic embeddings for text using
    SentenceTransformer models. It generates multiple vector types to support
    different granularities of semantic search.

    Attributes:
        embedding_model: SentenceTransformer model for generating embeddings
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize the embedding generator.

        Args:
            model_name: Name of the SentenceTransformer model to use
        """
        self.embedding_model = SentenceTransformer(model_name)
        logger.info(f"EmbeddingGenerator initialized with model: {model_name}")

    def generate_embeddings(self, text: str) -> Dict[str, List[float]]:
        """
        Generate embeddings for all vector types.

        Creates dense embeddings for summary, section, and microblock vectors.
        In this implementation, we use the same base embedding for all types,
        but in production you might use different models or text preprocessing
        for each vector type.

        Args:
            text: Input text to embed

        Returns:
            Dictionary mapping vector names to embedding lists

        Raises:
            Exception: If embedding generation fails
        """
        try:
            # Generate base embedding
            embedding = self.embedding_model.encode(text, convert_to_tensor=False)
            embedding_list = embedding.tolist()

            # For now, use the same embedding for all vector types
            # In production, you might want different processing per type:
            # - summary: embed the full document summary
            # - section: embed section-level text
            # - microblock: embed paragraph/sentence-level text
            return {
                "summary": embedding_list,
                "section": embedding_list,
                "microblock": embedding_list,
            }
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise

    def generate_batch_embeddings(
        self, texts: List[str], batch_size: int = 32
    ) -> List[Dict[str, List[float]]]:
        """
        Generate embeddings for multiple texts in batch.

        This method processes multiple texts efficiently by leveraging
        batch encoding capabilities of the embedding model.

        Args:
            texts: List of input texts to embed
            batch_size: Batch size for encoding (default: 32)

        Returns:
            List of embedding dictionaries, one per input text

        Raises:
            Exception: If batch embedding generation fails
        """
        try:
            # Generate embeddings for all texts in batch
            embeddings = self.embedding_model.encode(
                texts, convert_to_tensor=False, batch_size=batch_size
            )

            # Convert to list of dictionaries
            results = []
            for embedding in embeddings:
                embedding_list = embedding.tolist()
                results.append({
                    "summary": embedding_list,
                    "section": embedding_list,
                    "microblock": embedding_list,
                })

            return results
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this model.

        Returns:
            Embedding dimension size
        """
        return self.embedding_model.get_sentence_embedding_dimension()

    def encode_query(self, query: str) -> List[float]:
        """
        Encode a search query into an embedding vector.

        This method is optimized for query encoding, which may differ
        from document encoding in some models.

        Args:
            query: Search query text

        Returns:
            Embedding vector for the query

        Raises:
            Exception: If query encoding fails
        """
        try:
            embedding = self.embedding_model.encode(query, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error encoding query: {e}")
            raise
