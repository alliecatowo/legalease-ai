"""
OpenSearch client configuration and connection management.

This module provides async client wrapper around opensearch-py with:
- Connection pooling
- Retry logic with exponential backoff
- Health checks
- Index management
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List, AsyncGenerator

from opensearchpy import AsyncOpenSearch, exceptions as opensearch_exceptions

from app.core.config import settings
from app.shared.exceptions.domain_exceptions import InfrastructureException


logger = logging.getLogger(__name__)


class OpenSearchClient:
    """
    Async OpenSearch client wrapper with connection management and retry logic.

    This class provides a singleton-like client that manages connection pooling,
    implements retry logic for transient failures, and provides helper methods
    for index management.

    Example:
        >>> client = OpenSearchClient()
        >>> await client.initialize()
        >>> is_healthy = await client.health_check()
        >>> await client.close()
    """

    def __init__(self) -> None:
        """Initialize OpenSearch client (does not connect yet)."""
        self._client: Optional[AsyncOpenSearch] = None
        self._initialized: bool = False

    async def initialize(self) -> None:
        """
        Initialize the OpenSearch client connection.

        Creates the async client with connection pooling and retry configuration.

        Raises:
            InfrastructureException: If connection fails
        """
        if self._initialized:
            logger.warning("OpenSearch client already initialized")
            return

        try:
            self._client = AsyncOpenSearch(
                hosts=[settings.OPENSEARCH_URL],
                timeout=settings.OPENSEARCH_TIMEOUT,
                max_retries=settings.OPENSEARCH_MAX_RETRIES,
                retry_on_timeout=True,
                # Connection pool settings
                maxsize=25,  # Max connections per host
                # SSL/TLS settings (disable for local dev)
                use_ssl=settings.OPENSEARCH_URL.startswith("https"),
                verify_certs=False,
                ssl_show_warn=False,
            )

            # Verify connection
            await self._client.info()
            self._initialized = True
            logger.info(f"OpenSearch client initialized successfully: {settings.OPENSEARCH_URL}")

        except opensearch_exceptions.ConnectionError as e:
            raise InfrastructureException(
                f"Failed to connect to OpenSearch at {settings.OPENSEARCH_URL}",
                context={"url": settings.OPENSEARCH_URL},
                original_exception=e
            )
        except Exception as e:
            raise InfrastructureException(
                "Failed to initialize OpenSearch client",
                context={"url": settings.OPENSEARCH_URL},
                original_exception=e
            )

    async def close(self) -> None:
        """Close the OpenSearch client connection."""
        if self._client:
            await self._client.close()
            self._initialized = False
            logger.info("OpenSearch client closed")

    def get_client(self) -> AsyncOpenSearch:
        """
        Get the async OpenSearch client.

        Returns:
            AsyncOpenSearch client instance

        Raises:
            InfrastructureException: If client not initialized
        """
        if not self._initialized or not self._client:
            raise InfrastructureException(
                "OpenSearch client not initialized. Call initialize() first."
            )
        return self._client

    async def health_check(self) -> bool:
        """
        Check if OpenSearch cluster is healthy.

        Returns:
            True if cluster is healthy (green or yellow status)

        Raises:
            InfrastructureException: If health check fails
        """
        try:
            client = self.get_client()
            health = await client.cluster.health()
            status = health.get("status", "unknown")

            logger.debug(f"OpenSearch cluster health: {status}")

            return status in ["green", "yellow"]

        except opensearch_exceptions.ConnectionError as e:
            raise InfrastructureException(
                "Failed to connect to OpenSearch for health check",
                context={"url": settings.OPENSEARCH_URL},
                original_exception=e
            )
        except Exception as e:
            raise InfrastructureException(
                "OpenSearch health check failed",
                context={"url": settings.OPENSEARCH_URL},
                original_exception=e
            )

    async def index_exists(self, index_name: str) -> bool:
        """
        Check if an index exists.

        Args:
            index_name: Name of the index to check

        Returns:
            True if index exists

        Raises:
            InfrastructureException: If operation fails
        """
        try:
            client = self.get_client()
            exists = await client.indices.exists(index=index_name)
            return exists

        except Exception as e:
            raise InfrastructureException(
                f"Failed to check if index '{index_name}' exists",
                context={"index": index_name},
                original_exception=e
            )

    async def create_index(
        self,
        index_name: str,
        mappings: Dict[str, Any],
        settings: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create an index with specified mappings and settings.

        Args:
            index_name: Name of the index to create
            mappings: Index mappings (field types, analyzers, etc.)
            settings: Optional index settings (replicas, shards, etc.)

        Returns:
            True if index created successfully

        Raises:
            InfrastructureException: If creation fails
        """
        try:
            client = self.get_client()

            # Check if index already exists
            if await self.index_exists(index_name):
                logger.warning(f"Index '{index_name}' already exists, skipping creation")
                return False

            # Build index body
            body: Dict[str, Any] = {"mappings": mappings}
            if settings:
                body["settings"] = settings

            # Create index
            await client.indices.create(index=index_name, body=body)
            logger.info(f"Created OpenSearch index: {index_name}")

            return True

        except opensearch_exceptions.RequestError as e:
            raise InfrastructureException(
                f"Invalid request when creating index '{index_name}'",
                context={"index": index_name, "error": str(e)},
                original_exception=e
            )
        except Exception as e:
            raise InfrastructureException(
                f"Failed to create index '{index_name}'",
                context={"index": index_name},
                original_exception=e
            )

    async def delete_index(self, index_name: str, ignore_missing: bool = True) -> bool:
        """
        Delete an index.

        Args:
            index_name: Name of the index to delete
            ignore_missing: If True, don't raise error if index doesn't exist

        Returns:
            True if index deleted successfully

        Raises:
            InfrastructureException: If deletion fails
        """
        try:
            client = self.get_client()

            # Check if index exists
            if not await self.index_exists(index_name):
                if ignore_missing:
                    logger.warning(f"Index '{index_name}' does not exist, skipping deletion")
                    return False
                raise InfrastructureException(
                    f"Cannot delete index '{index_name}': index does not exist",
                    context={"index": index_name}
                )

            # Delete index
            await client.indices.delete(index=index_name)
            logger.info(f"Deleted OpenSearch index: {index_name}")

            return True

        except Exception as e:
            raise InfrastructureException(
                f"Failed to delete index '{index_name}'",
                context={"index": index_name},
                original_exception=e
            )

    async def refresh_index(self, index_name: str) -> None:
        """
        Refresh an index to make recent operations available for search.

        Args:
            index_name: Name of the index to refresh

        Raises:
            InfrastructureException: If refresh fails
        """
        try:
            client = self.get_client()
            await client.indices.refresh(index=index_name)
            logger.debug(f"Refreshed index: {index_name}")

        except Exception as e:
            raise InfrastructureException(
                f"Failed to refresh index '{index_name}'",
                context={"index": index_name},
                original_exception=e
            )

    async def get_index_stats(self, index_name: str) -> Dict[str, Any]:
        """
        Get statistics for an index.

        Args:
            index_name: Name of the index

        Returns:
            Index statistics dictionary

        Raises:
            InfrastructureException: If operation fails
        """
        try:
            client = self.get_client()
            stats = await client.indices.stats(index=index_name)
            return stats

        except Exception as e:
            raise InfrastructureException(
                f"Failed to get stats for index '{index_name}'",
                context={"index": index_name},
                original_exception=e
            )


# Global client instance
_opensearch_client: Optional[OpenSearchClient] = None


async def get_opensearch_client() -> OpenSearchClient:
    """
    Get or create the global OpenSearch client instance.

    Returns:
        OpenSearchClient instance

    Example:
        >>> client = await get_opensearch_client()
        >>> is_healthy = await client.health_check()
    """
    global _opensearch_client

    if _opensearch_client is None:
        _opensearch_client = OpenSearchClient()
        await _opensearch_client.initialize()

    return _opensearch_client


async def close_opensearch_client() -> None:
    """Close the global OpenSearch client instance."""
    global _opensearch_client

    if _opensearch_client:
        await _opensearch_client.close()
        _opensearch_client = None


@asynccontextmanager
async def opensearch_client_context() -> AsyncGenerator[OpenSearchClient, None]:
    """
    Context manager for OpenSearch client lifecycle.

    Example:
        >>> async with opensearch_client_context() as client:
        ...     await client.health_check()
    """
    client = await get_opensearch_client()
    try:
        yield client
    finally:
        # Don't close here - let application lifecycle manage it
        pass
