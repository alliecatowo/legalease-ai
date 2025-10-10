"""
Embedding Generation Pipeline

Provides dense vector embeddings for document chunks using sentence-transformers.
Supports multi-size chunks (summary, section, microblock) and automatic GPU/CPU detection.
"""

import logging
from typing import List, Optional, Dict, Any
import torch
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingPipeline:
    """
    Pipeline for generating dense embeddings using sentence-transformers.

    Features:
    - Automatic GPU/CPU detection
    - Batch processing for efficiency
    - Multi-size support (summary/section/microblock)
    - Model caching for performance
    """

    # Class-level cache for models to avoid reloading
    _model_cache: Dict[str, SentenceTransformer] = {}

    def __init__(
        self,
        model_name: str = "BAAI/bge-base-en-v1.5",
        device: Optional[str] = None,
        batch_size: int = 32,
        normalize_embeddings: bool = True,
    ):
        """
        Initialize the embedding pipeline.

        Args:
            model_name: HuggingFace model identifier (default: BAAI/bge-base-en-v1.5)
            device: Device to use ('cuda', 'cpu', or None for auto-detection)
            batch_size: Number of texts to process in each batch
            normalize_embeddings: Whether to L2-normalize embeddings (recommended for cosine similarity)
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.normalize_embeddings = normalize_embeddings

        # Auto-detect device if not specified
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(f"Initializing EmbeddingPipeline with model={model_name}, device={self.device}")

        # Load or retrieve cached model
        self.model = self._load_model()

        # Get embedding dimension
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded. Embedding dimension: {self.embedding_dim}")

    def _load_model(self) -> SentenceTransformer:
        """
        Load the sentence transformer model with caching.

        Returns:
            SentenceTransformer model instance
        """
        cache_key = f"{self.model_name}_{self.device}"

        if cache_key in self._model_cache:
            logger.info(f"Using cached model: {cache_key}")
            return self._model_cache[cache_key]

        logger.info(f"Loading model: {self.model_name}")
        model = SentenceTransformer(self.model_name, device=self.device)

        # Cache the model
        self._model_cache[cache_key] = model

        return model

    def generate_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None,
        show_progress: bool = False,
        convert_to_numpy: bool = True,
    ) -> np.ndarray:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed
            model: Optional model override (will reinitialize if different from current)
            show_progress: Whether to show progress bar
            convert_to_numpy: Whether to convert to numpy array (default: True)

        Returns:
            Array of embeddings with shape (len(texts), embedding_dim)
        """
        if not texts:
            logger.warning("Empty text list provided to generate_embeddings")
            return np.array([])

        # Reinitialize if different model requested
        if model and model != self.model_name:
            logger.info(f"Switching model from {self.model_name} to {model}")
            self.model_name = model
            self.model = self._load_model()
            self.embedding_dim = self.model.get_sentence_embedding_dimension()

        logger.info(f"Generating embeddings for {len(texts)} texts")

        try:
            # Generate embeddings in batches
            embeddings = self.model.encode(
                texts,
                batch_size=self.batch_size,
                show_progress_bar=show_progress,
                normalize_embeddings=self.normalize_embeddings,
                convert_to_numpy=convert_to_numpy,
            )

            logger.info(f"Generated embeddings with shape: {embeddings.shape}")
            return embeddings

        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise

    def generate_single_embedding(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> np.ndarray:
        """
        Generate embedding for a single text.

        Args:
            text: Text string to embed
            model: Optional model override

        Returns:
            Embedding vector with shape (embedding_dim,)
        """
        embeddings = self.generate_embeddings([text], model=model, show_progress=False)
        return embeddings[0] if len(embeddings) > 0 else np.array([])

    def generate_embeddings_by_size(
        self,
        texts_dict: Dict[str, List[str]],
        model: Optional[str] = None,
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
            model: Optional model override

        Returns:
            Dictionary mapping size type to embeddings array
        """
        logger.info(f"Generating embeddings for {len(texts_dict)} size types")

        embeddings_dict = {}

        for size_type, texts in texts_dict.items():
            logger.info(f"Processing {len(texts)} {size_type} texts")
            embeddings = self.generate_embeddings(texts, model=model)
            embeddings_dict[size_type] = embeddings

        return embeddings_dict

    def batch_generate(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        model: Optional[str] = None,
    ) -> List[np.ndarray]:
        """
        Generate embeddings with custom batch processing.

        Args:
            texts: List of text strings to embed
            batch_size: Custom batch size (overrides default)
            model: Optional model override

        Returns:
            List of embedding arrays (one per batch)
        """
        batch_size = batch_size or self.batch_size
        batches = []

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = self.generate_embeddings(
                batch_texts,
                model=model,
                show_progress=False,
            )
            batches.append(batch_embeddings)

        return batches

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
        # Ensure embeddings are normalized
        if not self.normalize_embeddings:
            embedding1 = embedding1 / np.linalg.norm(embedding1)
            embedding2 = embedding2 / np.linalg.norm(embedding2)

        return float(np.dot(embedding1, embedding2))

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model configuration.

        Returns:
            Dictionary with model information
        """
        return {
            "model_name": self.model_name,
            "device": self.device,
            "embedding_dim": self.embedding_dim,
            "batch_size": self.batch_size,
            "normalize_embeddings": self.normalize_embeddings,
            "cuda_available": torch.cuda.is_available(),
        }

    @classmethod
    def clear_cache(cls):
        """Clear the model cache to free memory."""
        logger.info("Clearing model cache")
        cls._model_cache.clear()


# Convenience function for quick embedding generation
def generate_embeddings(
    texts: List[str],
    model: str = "BAAI/bge-base-en-v1.5",
    device: Optional[str] = None,
    batch_size: int = 32,
) -> np.ndarray:
    """
    Convenience function to generate embeddings without creating a pipeline instance.

    Args:
        texts: List of text strings to embed
        model: HuggingFace model identifier
        device: Device to use ('cuda', 'cpu', or None for auto-detection)
        batch_size: Number of texts to process in each batch

    Returns:
        Array of embeddings with shape (len(texts), embedding_dim)
    """
    pipeline = EmbeddingPipeline(
        model_name=model,
        device=device,
        batch_size=batch_size,
    )
    return pipeline.generate_embeddings(texts)
