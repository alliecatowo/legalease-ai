"""
Pipeline factory for creating configured Haystack indexing pipelines.

Provides factory methods to instantiate pipelines with proper dependency injection
and configuration from app settings.
"""

import logging
from typing import Optional

from app.core.config import settings
from app.infrastructure.ai.haystack.pipelines.indexing import (
    DocumentIndexingPipeline,
    TranscriptIndexingPipeline,
    CommunicationIndexingPipeline,
)
from app.infrastructure.ai.haystack.stores.dual_store_writer import DualStoreWriter
from app.infrastructure.persistence.qdrant.repositories.document import QdrantDocumentRepository
from app.infrastructure.persistence.qdrant.repositories.transcript import QdrantTranscriptRepository
from app.infrastructure.persistence.qdrant.repositories.communication import QdrantCommunicationRepository
from app.infrastructure.persistence.opensearch.repositories.document import OpenSearchDocumentRepository
from app.infrastructure.persistence.opensearch.repositories.transcript import OpenSearchTranscriptRepository
from app.infrastructure.persistence.opensearch.repositories.communication import OpenSearchCommunicationRepository
from app.infrastructure.persistence.opensearch.client import OpenSearchClient

logger = logging.getLogger(__name__)


class PipelineFactory:
    """
    Factory for creating configured Haystack indexing pipelines.

    Handles dependency injection and configuration loading for all pipeline types.

    Features:
    - Repository injection
    - Configuration from settings
    - Singleton pattern for reusability
    - Type-safe pipeline creation

    Usage:
        >>> factory = PipelineFactory()
        >>> doc_pipeline = await factory.create_document_indexing_pipeline()
        >>> result = await doc_pipeline.run(...)
    """

    def __init__(
        self,
        opensearch_client: Optional[OpenSearchClient] = None,
    ):
        """
        Initialize the pipeline factory.

        Args:
            opensearch_client: Optional OpenSearch client (will create if not provided)
        """
        self.opensearch_client = opensearch_client
        self._opensearch_client_created = False

        logger.info("Initialized PipelineFactory")

    async def _get_opensearch_client(self) -> OpenSearchClient:
        """
        Get or create OpenSearch client.

        Returns:
            OpenSearchClient instance
        """
        if self.opensearch_client is None:
            logger.info("Creating new OpenSearchClient")
            self.opensearch_client = OpenSearchClient()
            await self.opensearch_client.initialize()
            self._opensearch_client_created = True

        return self.opensearch_client

    async def create_document_indexing_pipeline(
        self,
        use_ocr: Optional[bool] = None,
        model_name: Optional[str] = None,
        batch_size: Optional[int] = None,
    ) -> DocumentIndexingPipeline:
        """
        Create a document indexing pipeline with configured repositories.

        Args:
            use_ocr: Whether to use OCR (default: True)
            model_name: FastEmbed model name (default: BAAI/bge-small-en-v1.5)
            batch_size: Embedding batch size (default: 100)

        Returns:
            Configured DocumentIndexingPipeline
        """
        logger.info("Creating document indexing pipeline")

        # Get OpenSearch client
        opensearch_client = await self._get_opensearch_client()

        # Initialize repositories
        qdrant_repo = QdrantDocumentRepository()
        opensearch_repo = OpenSearchDocumentRepository(client=opensearch_client)

        # Create dual store writer
        dual_store_writer = DualStoreWriter(
            evidence_type="document",
            qdrant_document_repo=qdrant_repo,
            opensearch_document_repo=opensearch_repo,
        )

        # Create pipeline with configuration
        pipeline = DocumentIndexingPipeline(
            dual_store_writer=dual_store_writer,
            use_ocr=use_ocr if use_ocr is not None else True,
            model_name=model_name or "BAAI/bge-small-en-v1.5",
            batch_size=batch_size or 100,
        )

        logger.info("Document indexing pipeline created successfully")
        return pipeline

    async def create_transcript_indexing_pipeline(
        self,
        model_name: Optional[str] = None,
        batch_size: Optional[int] = None,
        max_chunk_size: Optional[int] = None,
    ) -> TranscriptIndexingPipeline:
        """
        Create a transcript indexing pipeline with configured repositories.

        Args:
            model_name: FastEmbed model name (default: BAAI/bge-small-en-v1.5)
            batch_size: Embedding batch size (default: 100)
            max_chunk_size: Maximum chunk size for speaker turns (default: 500)

        Returns:
            Configured TranscriptIndexingPipeline
        """
        logger.info("Creating transcript indexing pipeline")

        # Get OpenSearch client
        opensearch_client = await self._get_opensearch_client()

        # Initialize repositories
        qdrant_repo = QdrantTranscriptRepository()
        opensearch_repo = OpenSearchTranscriptRepository(client=opensearch_client)

        # Create dual store writer
        dual_store_writer = DualStoreWriter(
            evidence_type="transcript",
            qdrant_transcript_repo=qdrant_repo,
            opensearch_transcript_repo=opensearch_repo,
        )

        # Create pipeline with configuration
        pipeline = TranscriptIndexingPipeline(
            dual_store_writer=dual_store_writer,
            model_name=model_name or "BAAI/bge-small-en-v1.5",
            batch_size=batch_size or 100,
            max_chunk_size=max_chunk_size or 500,
        )

        logger.info("Transcript indexing pipeline created successfully")
        return pipeline

    async def create_communication_indexing_pipeline(
        self,
        model_name: Optional[str] = None,
        batch_size: Optional[int] = None,
        max_messages_per_group: Optional[int] = None,
    ) -> CommunicationIndexingPipeline:
        """
        Create a communication indexing pipeline with configured repositories.

        Args:
            model_name: FastEmbed model name (default: BAAI/bge-small-en-v1.5)
            batch_size: Embedding batch size (default: 100)
            max_messages_per_group: Maximum messages per thread group (default: 10)

        Returns:
            Configured CommunicationIndexingPipeline
        """
        logger.info("Creating communication indexing pipeline")

        # Get OpenSearch client
        opensearch_client = await self._get_opensearch_client()

        # Initialize repositories
        qdrant_repo = QdrantCommunicationRepository()
        opensearch_repo = OpenSearchCommunicationRepository(client=opensearch_client)

        # Create dual store writer
        dual_store_writer = DualStoreWriter(
            evidence_type="communication",
            qdrant_communication_repo=qdrant_repo,
            opensearch_communication_repo=opensearch_repo,
        )

        # Create pipeline with configuration
        pipeline = CommunicationIndexingPipeline(
            dual_store_writer=dual_store_writer,
            model_name=model_name or "BAAI/bge-small-en-v1.5",
            batch_size=batch_size or 100,
            max_messages_per_group=max_messages_per_group or 10,
        )

        logger.info("Communication indexing pipeline created successfully")
        return pipeline

    async def close(self):
        """
        Close any resources created by the factory.

        Should be called when the factory is no longer needed.
        """
        if self._opensearch_client_created and self.opensearch_client:
            logger.info("Closing OpenSearch client")
            await self.opensearch_client.close()
            self._opensearch_client_created = False
            self.opensearch_client = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Convenience functions for quick pipeline creation


async def create_document_pipeline(**kwargs) -> DocumentIndexingPipeline:
    """
    Convenience function to create a document indexing pipeline.

    Args:
        **kwargs: Arguments passed to create_document_indexing_pipeline

    Returns:
        DocumentIndexingPipeline instance

    Note:
        Remember to close the pipeline's resources when done.
        Consider using PipelineFactory as a context manager instead.
    """
    factory = PipelineFactory()
    try:
        pipeline = await factory.create_document_indexing_pipeline(**kwargs)
        return pipeline
    except Exception:
        await factory.close()
        raise


async def create_transcript_pipeline(**kwargs) -> TranscriptIndexingPipeline:
    """
    Convenience function to create a transcript indexing pipeline.

    Args:
        **kwargs: Arguments passed to create_transcript_indexing_pipeline

    Returns:
        TranscriptIndexingPipeline instance

    Note:
        Remember to close the pipeline's resources when done.
        Consider using PipelineFactory as a context manager instead.
    """
    factory = PipelineFactory()
    try:
        pipeline = await factory.create_transcript_indexing_pipeline(**kwargs)
        return pipeline
    except Exception:
        await factory.close()
        raise


async def create_communication_pipeline(**kwargs) -> CommunicationIndexingPipeline:
    """
    Convenience function to create a communication indexing pipeline.

    Args:
        **kwargs: Arguments passed to create_communication_indexing_pipeline

    Returns:
        CommunicationIndexingPipeline instance

    Note:
        Remember to close the pipeline's resources when done.
        Consider using PipelineFactory as a context manager instead.
    """
    factory = PipelineFactory()
    try:
        pipeline = await factory.create_communication_indexing_pipeline(**kwargs)
        return pipeline
    except Exception:
        await factory.close()
        raise
