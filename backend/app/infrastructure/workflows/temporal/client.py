"""
Temporal client setup with singleton pattern.

Provides a centralized Temporal client instance for starting workflows,
querying workflow status, and managing workflow execution.
"""

import asyncio
import logging
from typing import Optional
from temporalio.client import Client, WorkflowFailureError, WorkflowHandle
from temporalio.service import RPCError

from app.core.config import settings


logger = logging.getLogger(__name__)


class TemporalClient:
    """
    Singleton Temporal client manager.

    Provides a single shared client instance with automatic reconnection
    and health checking capabilities.

    Example:
        >>> client_manager = TemporalClient()
        >>> client = await client_manager.get_client()
        >>> is_healthy = await client_manager.health_check()
    """

    _instance: Optional['TemporalClient'] = None
    _client: Optional[Client] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __new__(cls) -> 'TemporalClient':
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def get_client(self) -> Client:
        """
        Get or create the Temporal client instance.

        Returns:
            Connected Temporal client

        Raises:
            ConnectionError: If unable to connect to Temporal server
        """
        if self._client is not None:
            return self._client

        async with self._lock:
            # Double-check after acquiring lock
            if self._client is not None:
                return self._client

            try:
                logger.info(
                    f"Connecting to Temporal at {settings.TEMPORAL_HOST} "
                    f"(namespace: {settings.TEMPORAL_NAMESPACE})"
                )

                self._client = await Client.connect(
                    settings.TEMPORAL_HOST,
                    namespace=settings.TEMPORAL_NAMESPACE,
                )

                logger.info("Successfully connected to Temporal")
                return self._client

            except Exception as e:
                logger.error(f"Failed to connect to Temporal: {e}")
                raise ConnectionError(
                    f"Unable to connect to Temporal server at {settings.TEMPORAL_HOST}: {e}"
                ) from e

    async def health_check(self) -> bool:
        """
        Check if Temporal server is healthy and accessible.

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            client = await self.get_client()

            # Try to list workflows as a health check
            # This is a lightweight operation that verifies connectivity
            async for _ in client.list_workflows():
                break

            logger.debug("Temporal health check: OK")
            return True

        except RPCError as e:
            logger.warning(f"Temporal health check failed (RPC error): {e}")
            return False
        except ConnectionError as e:
            logger.warning(f"Temporal health check failed (connection): {e}")
            return False
        except Exception as e:
            logger.error(f"Temporal health check failed (unexpected): {e}")
            return False

    async def close(self) -> None:
        """
        Close the Temporal client connection.

        Should be called during application shutdown.
        """
        if self._client is not None:
            async with self._lock:
                if self._client is not None:
                    await self._client.close()
                    self._client = None
                    logger.info("Temporal client connection closed")

    async def get_workflow_handle(self, workflow_id: str) -> WorkflowHandle:
        """
        Get a handle to an existing workflow.

        Args:
            workflow_id: The workflow ID

        Returns:
            WorkflowHandle for querying and signaling the workflow

        Raises:
            ValueError: If workflow not found
        """
        client = await self.get_client()

        try:
            handle = client.get_workflow_handle(workflow_id)
            # Verify workflow exists by fetching description
            await handle.describe()
            return handle
        except Exception as e:
            raise ValueError(f"Workflow {workflow_id} not found: {e}") from e


# ==================== Convenience Functions ====================

_client_manager: Optional[TemporalClient] = None


async def get_temporal_client() -> Client:
    """
    Get the singleton Temporal client instance.

    This is the primary function to use for getting a Temporal client
    throughout the application.

    Returns:
        Connected Temporal client

    Example:
        >>> from app.infrastructure.workflows.temporal.client import get_temporal_client
        >>> client = await get_temporal_client()
        >>> handle = await client.start_workflow(...)
    """
    global _client_manager

    if _client_manager is None:
        _client_manager = TemporalClient()

    return await _client_manager.get_client()


async def temporal_health_check() -> bool:
    """
    Check if Temporal server is healthy.

    Returns:
        True if healthy, False otherwise

    Example:
        >>> from app.infrastructure.workflows.temporal.client import temporal_health_check
        >>> is_healthy = await temporal_health_check()
        >>> if not is_healthy:
        ...     logger.error("Temporal server is down!")
    """
    global _client_manager

    if _client_manager is None:
        _client_manager = TemporalClient()

    return await _client_manager.health_check()


async def close_temporal_client() -> None:
    """
    Close the Temporal client connection.

    Should be called during application shutdown.

    Example:
        >>> from app.infrastructure.workflows.temporal.client import close_temporal_client
        >>> await close_temporal_client()
    """
    global _client_manager

    if _client_manager is not None:
        await _client_manager.close()
