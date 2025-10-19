"""
FastEmbed Embedding Pipeline

Provides fast, lightweight dense vector embeddings using Qdrant's FastEmbed library.
Optimized for production with ONNX runtime, smaller memory footprint, and faster inference.
"""

import logging
from typing import List, Optional, Dict, Any, Iterator
import numpy as np
from fastembed import TextEmbedding

logger = logging.getLogger(__name__)


class FastEmbedPipeline:
    """
    Pipeline for generating dense embeddings using FastEmbed.

    FastEmbed advantages:
    - 4x faster than sentence-transformers (ONNX runtime)
    - Lightweight: No PyTorch dependency
    - Serverless-friendly: Small memory footprint
    - Qdrant-native integration
    - CPU optimized with quantization

    Features:
    - Automatic model caching
    - Batch processing for efficiency
    - Multi-size support (summary/section/microblock)
    - Parallel encoding
    """

    # Class-level cache for models to avoid reloading
    _model_cache: Dict[str, TextEmbedding] = {}

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        cache_dir: Optional[str] = None,
        threads: Optional[int] = None,
        parallel: Optional[int] = None,
    ):
        """
        Initialize the FastEmbed pipeline.

        Args:
            model_name: HuggingFace model identifier
                       Popular options:
                       - "BAAI/bge-small-en-v1.5" (384 dim, fast, good quality)
                       - "BAAI/bge-base-en-v1.5" (768 dim, balanced)
                       - "sentence-transformers/all-MiniLM-L6-v2" (384 dim, very fast)
            cache_dir: Directory to cache models (default: ~/.cache/fastembed)
            threads: Number of threads for encoding (default: None = auto)
            parallel: Number of parallel workers for encoding (default: None = auto)
        """
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.threads = threads
        self.parallel = parallel

        logger.info(f"Initializing FastEmbedPipeline with model={model_name}")

        # Load or retrieve cached model
        self.model = self._load_model()

        # Get embedding dimension
        # Generate a dummy embedding to determine dimension
        dummy_embedding = list(self.model.embed(["test"]))[0]
        self.embedding_dim = len(dummy_embedding)
        logger.info(f"Model loaded. Embedding dimension: {self.embedding_dim}")

    def _load_model(self) -> TextEmbedding:
        """
        Load the FastEmbed model with caching.

        Returns:
            TextEmbedding model instance
        """
        cache_key = self.model_name

        if cache_key in self._model_cache:
            logger.info(f"Using cached model: {cache_key}")
            return self._model_cache[cache_key]

        logger.info(f"Loading FastEmbed model: {self.model_name}")

        # Initialize model with configuration
        kwargs = {
            "model_name": self.model_name,
        }

        if self.cache_dir:
            kwargs["cache_dir"] = self.cache_dir
        if self.threads:
            kwargs["threads"] = self.threads
        if self.parallel:
            kwargs["parallel"] = self.parallel

        model = TextEmbedding(**kwargs)

        # Cache the model
        self._model_cache[cache_key] = model

        return model

    def generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = 100,
        show_progress: bool = False,
    ) -> np.ndarray:
        """
        Generate embeddings for a list of texts with memory-efficient streaming.

        This method processes embeddings in batches and accumulates them incrementally
        to avoid loading all embeddings into memory at once (critical for large documents).

        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process in each batch (default: 100 for memory efficiency)
            show_progress: Whether to show progress bar

        Returns:
            Array of embeddings with shape (len(texts), embedding_dim)
        """
        if not texts:
            logger.warning("Empty text list provided to generate_embeddings")
            return np.array([])

        total_texts = len(texts)
        logger.debug(f"Generating embeddings for {total_texts} texts (batch_size={batch_size})")

        try:
            # Memory-efficient batch processing
            # We MUST split texts into smaller chunks BEFORE calling embed()
            # FastEmbed pre-processes all texts before yielding, causing OOM on large batches
            all_embeddings = []
            processed = 0

            # Process texts in small batches to prevent memory spikes
            for batch_start in range(0, total_texts, batch_size):
                batch_end = min(batch_start + batch_size, total_texts)
                batch_texts = texts[batch_start:batch_end]
                batch_num = (batch_start // batch_size) + 1
                total_batches = (total_texts + batch_size - 1) // batch_size

                logger.debug(
                    f"  Processing batch {batch_num}/{total_batches}: "
                    f"texts {batch_start+1}-{batch_end} "
                    f"({processed*100//total_texts}% complete)"
                )

                # Generate embeddings for this batch only
                # Use smaller batch_size for FastEmbed's internal batching
                embeddings_generator = self.model.embed(
                    batch_texts,
                    batch_size=min(batch_size, 32),  # Cap internal batch size
                )

                # Collect all embeddings from this batch
                batch_embeddings = []
                for embedding in embeddings_generator:
                    batch_embeddings.append(embedding)

                # Stack batch and append to results
                batch_array = np.vstack(batch_embeddings)
                all_embeddings.append(batch_array)

                processed = batch_end
                logger.debug(f"  Batch {batch_num}/{total_batches} complete ({processed}/{total_texts})")

            # Final stack of all batches
            embeddings = np.vstack(all_embeddings)

            logger.debug(f"Generated embeddings with shape: {embeddings.shape}")
            return embeddings

        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise

    def generate_single_embedding(
        self,
        text: str,
    ) -> np.ndarray:
        """
        Generate embedding for a single text.

        Args:
            text: Text string to embed

        Returns:
            Embedding vector with shape (embedding_dim,)
        """
        embeddings = self.generate_embeddings([text], show_progress=False)
        return embeddings[0] if len(embeddings) > 0 else np.array([])

    def generate_embeddings_by_size(
        self,
        texts_dict: Dict[str, List[str]],
        batch_size: int = 256,
    ) -> Dict[str, np.ndarray]:
        """
        Generate embeddings for texts of different sizes.

        Useful for processing different granularities:
        - summary: Document-level summaries
        - section: Section-level chunks
        - microblock: Sentence or paragraph-level chunks

        Args:
            texts_dict: Dictionary mapping size type to list of texts
                       e.g., {"summary": [...], "section": [...], "microblock": [...]}
            batch_size: Batch size for encoding

        Returns:
            Dictionary mapping size type to embeddings array
        """
        logger.info(f"Generating embeddings for {len(texts_dict)} size types")

        embeddings_dict = {}

        for size_type, texts in texts_dict.items():
            logger.info(f"Processing {len(texts)} {size_type} texts")
            embeddings = self.generate_embeddings(texts, batch_size=batch_size)
            embeddings_dict[size_type] = embeddings

        return embeddings_dict

    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a search query.

        Some models support query prefixes like "query:" or "search_query:".
        This method adds appropriate prefixes if needed.

        Args:
            query: Search query text

        Returns:
            Query embedding vector
        """
        # Some models (like BGE) support query prefix
        # FastEmbed automatically handles this for supported models
        return self.generate_single_embedding(query)

    def embed_documents(self, documents: List[str], batch_size: int = 256) -> np.ndarray:
        """
        Embed a list of documents.

        Some models support document prefixes like "passage:" or "search_document:".
        This method adds appropriate prefixes if needed.

        Args:
            documents: List of document texts
            batch_size: Batch size for encoding

        Returns:
            Array of document embeddings
        """
        # FastEmbed automatically handles document/passage prefixes
        return self.generate_embeddings(documents, batch_size=batch_size)

    def compute_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray,
    ) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score between -1 and 1
        """
        # FastEmbed embeddings are already normalized
        return float(np.dot(embedding1, embedding2))

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model configuration.

        Returns:
            Dictionary with model information
        """
        return {
            "model_name": self.model_name,
            "embedding_dim": self.embedding_dim,
            "cache_dir": self.cache_dir,
            "threads": self.threads,
            "parallel": self.parallel,
            "backend": "FastEmbed (ONNX)",
        }

    @classmethod
    def list_supported_models(cls) -> List[str]:
        """
        List all supported FastEmbed models.

        Returns:
            List of model names
        """
        try:
            from fastembed import TextEmbedding
            return TextEmbedding.list_supported_models()
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []

    @classmethod
    def clear_cache(cls):
        """Clear the model cache to free memory."""
        logger.info("Clearing model cache")
        cls._model_cache.clear()


# Convenience function for quick embedding generation
def generate_embeddings(
    texts: List[str],
    model: str = "BAAI/bge-small-en-v1.5",
    batch_size: int = 256,
) -> np.ndarray:
    """
    Convenience function to generate embeddings without creating a pipeline instance.

    Args:
        texts: List of text strings to embed
        model: HuggingFace model identifier
        batch_size: Number of texts to process in each batch

    Returns:
        Array of embeddings with shape (len(texts), embedding_dim)
    """
    pipeline = FastEmbedPipeline(model_name=model)
    return pipeline.generate_embeddings(texts, batch_size=batch_size)
