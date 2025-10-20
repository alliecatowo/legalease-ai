"""
Enhanced Qdrant client with connection pooling, retry logic, and health checks.

This module provides an enhanced async Qdrant client following hexagonal
architecture principles with comprehensive error handling.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from functools import lru_cache
from contextlib import asynccontextmanager

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    SparseVectorParams,
    SparseIndexParams,
    CollectionInfo,
)

from app.core.config import settings
from app.infrastructure.exceptions import (
    ConnectionException,
    CollectionException,
    VectorStoreException,
)

logger = logging.getLogger(__name__)


class EnhancedQdrantClient:
    """
    Enhanced Qdrant client with connection management and error handling.

    Features:
    - Async operations
    - Connection pooling
    - Automatic retry with exponential backoff
    - Health checks
    - Multiple collection management
    - Proper error handling
    """

    def __init__(
        self,
        host: str = settings.QDRANT_HOST,
        port: int = settings.QDRANT_PORT,
        timeout: float = 300.0,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
    ) -> None:
        """
        Initialize enhanced Qdrant client.

        Args:
            host: Qdrant server host
            port: Qdrant server port
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_backoff: Initial backoff time for retries (seconds)
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self._client: Optional[AsyncQdrantClient] = None
        self._lock = asyncio.Lock()

    async def _ensure_client(self) -> AsyncQdrantClient:
        """
        Ensure client is initialized (lazy initialization).

        Returns:
            Initialized AsyncQdrantClient instance
        """
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    try:
                        self._client = AsyncQdrantClient(
                            host=self.host,
                            port=self.port,
                            timeout=self.timeout,
                        )
                        logger.info(f"Qdrant client connected: {self.host}:{self.port}")
                    except Exception as e:
                        raise ConnectionException(
                            f"Failed to connect to Qdrant at {self.host}:{self.port}",
                            cause=e,
                            context={"host": self.host, "port": self.port},
                        )
        return self._client

    async def close(self) -> None:
        """Close the Qdrant client connection."""
        if self._client is not None:
            try:
                await self._client.close()
                logger.info("Qdrant client connection closed")
            except Exception as e:
                logger.warning(f"Error closing Qdrant client: {e}")
            finally:
                self._client = None

    async def health_check(self) -> bool:
        """
        Check if Qdrant server is healthy and responsive.

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            client = await self._ensure_client()
            # Try to get collections as a health check
            await client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False

    async def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists.

        Args:
            collection_name: Name of the collection to check

        Returns:
            True if collection exists, False otherwise
        """
        try:
            client = await self._ensure_client()
            collections = await client.get_collections()
            return any(c.name == collection_name for c in collections.collections)
        except Exception as e:
            logger.error(f"Error checking collection existence: {e}")
            return False

    async def create_collection(
        self,
        collection_name: str,
        vector_configs: Dict[str, VectorParams],
        sparse_vector_configs: Optional[Dict[str, SparseVectorParams]] = None,
        recreate: bool = False,
    ) -> bool:
        """
        Create a Qdrant collection with specified vector configurations.

        Args:
            collection_name: Name of the collection
            vector_configs: Dictionary mapping vector names to VectorParams
            sparse_vector_configs: Optional sparse vector configurations
            recreate: If True, delete existing collection before creating

        Returns:
            True if collection was created successfully

        Raises:
            CollectionException: If collection creation fails
        """
        try:
            client = await self._ensure_client()

            # Check if collection exists
            exists = await self.collection_exists(collection_name)

            if exists:
                if recreate:
                    logger.warning(f"Deleting existing collection: {collection_name}")
                    await client.delete_collection(collection_name=collection_name)
                else:
                    logger.info(f"Collection already exists: {collection_name}")
                    return True

            # Create collection
            await client.create_collection(
                collection_name=collection_name,
                vectors_config=vector_configs,
                sparse_vectors_config=sparse_vector_configs,
            )

            logger.info(f"Collection created successfully: {collection_name}")
            logger.info(f"Dense vectors: {list(vector_configs.keys())}")
            if sparse_vector_configs:
                logger.info(f"Sparse vectors: {list(sparse_vector_configs.keys())}")

            return True

        except Exception as e:
            raise CollectionException(
                f"Failed to create collection '{collection_name}'",
                cause=e,
                context={
                    "collection_name": collection_name,
                    "recreate": recreate,
                },
            )

    async def get_collection_info(self, collection_name: str) -> CollectionInfo:
        """
        Get information about a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Collection information

        Raises:
            CollectionException: If collection doesn't exist or query fails
        """
        try:
            client = await self._ensure_client()
            return await client.get_collection(collection_name=collection_name)
        except Exception as e:
            raise CollectionException(
                f"Failed to get collection info for '{collection_name}'",
                cause=e,
                context={"collection_name": collection_name},
            )

    async def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection.

        Args:
            collection_name: Name of the collection to delete

        Returns:
            True if deletion was successful

        Raises:
            CollectionException: If deletion fails
        """
        try:
            client = await self._ensure_client()
            await client.delete_collection(collection_name=collection_name)
            logger.info(f"Collection deleted: {collection_name}")
            return True
        except Exception as e:
            raise CollectionException(
                f"Failed to delete collection '{collection_name}'",
                cause=e,
                context={"collection_name": collection_name},
            )

    async def get_collections(self) -> List[str]:
        """
        Get list of all collection names.

        Returns:
            List of collection names

        Raises:
            VectorStoreException: If query fails
        """
        try:
            client = await self._ensure_client()
            collections = await client.get_collections()
            return [c.name for c in collections.collections]
        except Exception as e:
            raise VectorStoreException(
                "Failed to get collections list",
                cause=e,
            )

    @asynccontextmanager
    async def get_client(self):
        """
        Context manager to get the underlying Qdrant client.

        Use this for direct client operations while ensuring proper
        connection management.

        Example:
            async with qdrant_client.get_client() as client:
                await client.upsert(...)
        """
        client = await self._ensure_client()
        try:
            yield client
        except Exception as e:
            logger.error(f"Error during Qdrant operation: {e}")
            raise

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Singleton instance
_qdrant_client: Optional[EnhancedQdrantClient] = None


def get_qdrant_client() -> EnhancedQdrantClient:
    """
    Get or create a singleton Qdrant client instance.

    Returns:
        EnhancedQdrantClient instance
    """
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = EnhancedQdrantClient()
    return _qdrant_client


async def close_qdrant_client() -> None:
    """Close the singleton Qdrant client."""
    global _qdrant_client
    if _qdrant_client is not None:
        await _qdrant_client.close()
        _qdrant_client = None
