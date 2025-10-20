"""
FastEmbed-based embedding components for Haystack pipelines.

Provides dense and sparse embedding generation using FastEmbed.
"""

import logging
from typing import List, Dict, Any, Optional

from haystack import component, Document
import numpy as np

from app.workers.pipelines.embeddings import FastEmbedPipeline

logger = logging.getLogger(__name__)


@component
class FastEmbedDocumentEmbedder:
    """
    Haystack component that generates dense embeddings using FastEmbed.

    Wraps the existing FastEmbedPipeline to provide Haystack-compatible
    document embedding with support for batch processing.

    Features:
    - Fast ONNX-based inference
    - Batch processing for efficiency
    - Model caching
    - Multi-size support (summary, section, microblock)

    Usage:
        >>> embedder = FastEmbedDocumentEmbedder(
        ...     model_name="BAAI/bge-small-en-v1.5",
        ...     batch_size=100
        ... )
        >>> result = embedder.run(documents=[doc1, doc2])
        >>> embeddings = result["embeddings"]
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        batch_size: int = 100,
        cache_dir: Optional[str] = None,
        prefix: Optional[str] = None,
    ):
        """
        Initialize the FastEmbed document embedder.

        Args:
            model_name: HuggingFace model identifier
            batch_size: Batch size for embedding generation
            cache_dir: Directory to cache models
            prefix: Optional prefix to add to all documents (e.g., "passage: ")
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.prefix = prefix

        # Initialize FastEmbed pipeline
        self.pipeline = FastEmbedPipeline(
            model_name=model_name,
            cache_dir=cache_dir,
        )

        self.embedding_dim = self.pipeline.embedding_dim

        logger.info(
            f"Initialized FastEmbedDocumentEmbedder (model={model_name}, "
            f"dim={self.embedding_dim}, batch_size={batch_size})"
        )

    @component.output_types(embeddings=List[List[float]], embedding_dim=int)
    def run(self, documents: List[Document]) -> Dict[str, Any]:
        """
        Generate embeddings for documents.

        Args:
            documents: List of Haystack Documents to embed

        Returns:
            Dictionary with:
                - embeddings: List of embedding vectors (one per document)
                - embedding_dim: Dimensionality of embeddings
        """
        if not documents:
            logger.warning("No documents provided to FastEmbedDocumentEmbedder")
            return {"embeddings": [], "embedding_dim": self.embedding_dim}

        # Extract text from documents
        texts = []
        for doc in documents:
            text = doc.content
            if self.prefix:
                text = f"{self.prefix}{text}"
            texts.append(text)

        logger.info(f"Generating embeddings for {len(texts)} documents")

        # Generate embeddings
        embeddings_array = self.pipeline.generate_embeddings(
            texts=texts,
            batch_size=self.batch_size,
        )

        # Convert to list of lists
        embeddings = embeddings_array.tolist()

        logger.info(
            f"Generated {len(embeddings)} embeddings "
            f"(dim={self.embedding_dim})"
        )

        return {
            "embeddings": embeddings,
            "embedding_dim": self.embedding_dim,
        }


@component
class FastEmbedQueryEmbedder:
    """
    Haystack component that generates query embeddings using FastEmbed.

    Similar to FastEmbedDocumentEmbedder but optimized for query embedding.
    Some models support different prefixes for queries vs documents.

    Usage:
        >>> embedder = FastEmbedQueryEmbedder(
        ...     model_name="BAAI/bge-small-en-v1.5"
        ... )
        >>> result = embedder.run(query="What is the contract date?")
        >>> embedding = result["embedding"]
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        cache_dir: Optional[str] = None,
        prefix: Optional[str] = None,
    ):
        """
        Initialize the FastEmbed query embedder.

        Args:
            model_name: HuggingFace model identifier
            cache_dir: Directory to cache models
            prefix: Optional prefix to add to query (e.g., "query: ")
        """
        self.model_name = model_name
        self.prefix = prefix

        # Initialize FastEmbed pipeline
        self.pipeline = FastEmbedPipeline(
            model_name=model_name,
            cache_dir=cache_dir,
        )

        self.embedding_dim = self.pipeline.embedding_dim

        logger.info(
            f"Initialized FastEmbedQueryEmbedder (model={model_name}, "
            f"dim={self.embedding_dim})"
        )

    @component.output_types(embedding=List[float], embedding_dim=int)
    def run(self, query: str) -> Dict[str, Any]:
        """
        Generate embedding for a query.

        Args:
            query: Query text to embed

        Returns:
            Dictionary with:
                - embedding: Query embedding vector
                - embedding_dim: Dimensionality of embedding
        """
        if not query or not query.strip():
            logger.warning("Empty query provided to FastEmbedQueryEmbedder")
            return {
                "embedding": [0.0] * self.embedding_dim,
                "embedding_dim": self.embedding_dim,
            }

        # Add prefix if configured
        text = query
        if self.prefix:
            text = f"{self.prefix}{text}"

        logger.debug(f"Generating query embedding for: {query[:100]}...")

        # Generate embedding
        embedding_array = self.pipeline.embed_query(text)

        # Convert to list
        embedding = embedding_array.tolist()

        return {
            "embedding": embedding,
            "embedding_dim": self.embedding_dim,
        }


@component
class SparseEmbedder:
    """
    Haystack component that generates sparse embeddings for BM25.

    This is a placeholder component. In practice, sparse embeddings
    are typically generated by the search engine (OpenSearch) during indexing.
    This component exists for pipeline completeness.

    Usage:
        >>> embedder = SparseEmbedder()
        >>> result = embedder.run(documents=[doc1, doc2])
        >>> sparse_vectors = result["sparse_vectors"]
    """

    def __init__(self):
        """Initialize the sparse embedder."""
        logger.info("Initialized SparseEmbedder (placeholder)")

    @component.output_types(sparse_vectors=Optional[List[Any]])
    def run(self, documents: List[Document]) -> Dict[str, Any]:
        """
        Generate sparse vectors (placeholder).

        Args:
            documents: List of Haystack Documents

        Returns:
            Dictionary with:
                - sparse_vectors: None (OpenSearch handles BM25)
        """
        logger.debug(f"SparseEmbedder passthrough for {len(documents)} documents")

        # Return None - OpenSearch will generate BM25 vectors automatically
        return {"sparse_vectors": None}
