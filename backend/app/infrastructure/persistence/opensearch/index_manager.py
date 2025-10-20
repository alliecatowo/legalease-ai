"""
OpenSearch index lifecycle manager.

This module handles creation, deletion, and management of all
OpenSearch indexes with proper mappings and settings.
"""

import logging
from typing import Dict, Any, List, Optional

from app.infrastructure.persistence.opensearch.client import OpenSearchClient
from app.infrastructure.persistence.opensearch.schemas import (
    INDEX_CONFIGS,
    DOCUMENTS_INDEX,
    TRANSCRIPTS_INDEX,
    COMMUNICATIONS_INDEX,
    FINDINGS_INDEX,
)
from app.shared.exceptions.domain_exceptions import InfrastructureException


logger = logging.getLogger(__name__)


class OpenSearchIndexManager:
    """
    Manages OpenSearch index lifecycle operations.

    Handles:
    - Creating all indexes with proper mappings
    - Deleting indexes
    - Reindexing operations
    - Index health checks
    """

    def __init__(self, client: OpenSearchClient):
        """
        Initialize index manager.

        Args:
            client: OpenSearch client instance
        """
        self.client = client

    async def create_all_indexes(self, force: bool = False) -> Dict[str, bool]:
        """
        Create all indexes defined in INDEX_CONFIGS.

        Args:
            force: If True, delete existing indexes before creating

        Returns:
            Dictionary mapping index names to creation success status

        Raises:
            InfrastructureException: If creation fails
        """
        results = {}

        try:
            for index_name, config in INDEX_CONFIGS.items():
                # Delete if force flag set
                if force and await self.client.index_exists(index_name):
                    logger.info(f"Force flag set, deleting existing index: {index_name}")
                    await self.client.delete_index(index_name)

                # Create index
                created = await self.client.create_index(
                    index_name=index_name,
                    mappings=config["mappings"],
                    settings=config["settings"]
                )

                results[index_name] = created

                if created:
                    logger.info(f"Successfully created index: {index_name}")
                else:
                    logger.info(f"Index already exists: {index_name}")

            return results

        except Exception as e:
            raise InfrastructureException(
                "Failed to create all indexes",
                context={"partial_results": results},
                original_exception=e
            )

    async def delete_all_indexes(self, confirm: bool = False) -> Dict[str, bool]:
        """
        Delete all indexes defined in INDEX_CONFIGS.

        CAUTION: This will permanently delete all data in these indexes.

        Args:
            confirm: Must be True to proceed (safety check)

        Returns:
            Dictionary mapping index names to deletion success status

        Raises:
            InfrastructureException: If deletion fails or not confirmed
        """
        if not confirm:
            raise InfrastructureException(
                "Cannot delete all indexes without confirmation. "
                "Set confirm=True to proceed."
            )

        results = {}

        try:
            for index_name in INDEX_CONFIGS.keys():
                deleted = await self.client.delete_index(
                    index_name=index_name,
                    ignore_missing=True
                )

                results[index_name] = deleted

                if deleted:
                    logger.info(f"Successfully deleted index: {index_name}")
                else:
                    logger.info(f"Index did not exist: {index_name}")

            return results

        except Exception as e:
            raise InfrastructureException(
                "Failed to delete all indexes",
                context={"partial_results": results},
                original_exception=e
            )

    async def recreate_all_indexes(self) -> Dict[str, bool]:
        """
        Delete and recreate all indexes.

        CAUTION: This will permanently delete all data in these indexes.

        Returns:
            Dictionary mapping index names to creation success status

        Raises:
            InfrastructureException: If operation fails
        """
        logger.warning("Recreating all indexes - all data will be lost!")

        # Delete all indexes
        await self.delete_all_indexes(confirm=True)

        # Create all indexes
        results = await self.create_all_indexes()

        logger.info("Successfully recreated all indexes")

        return results

    async def check_index_health(self) -> Dict[str, Dict[str, Any]]:
        """
        Check health and stats for all indexes.

        Returns:
            Dictionary mapping index names to health info

        Raises:
            InfrastructureException: If health check fails
        """
        health_info = {}

        try:
            for index_name in INDEX_CONFIGS.keys():
                if not await self.client.index_exists(index_name):
                    health_info[index_name] = {
                        "exists": False,
                        "error": "Index does not exist"
                    }
                    continue

                # Get index stats
                stats = await self.client.get_index_stats(index_name)

                # Extract useful stats
                index_stats = stats.get("indices", {}).get(index_name, {})
                total = index_stats.get("total", {})

                health_info[index_name] = {
                    "exists": True,
                    "doc_count": total.get("docs", {}).get("count", 0),
                    "size_bytes": total.get("store", {}).get("size_in_bytes", 0),
                    "size_mb": round(
                        total.get("store", {}).get("size_in_bytes", 0) / (1024 * 1024),
                        2
                    ),
                }

            return health_info

        except Exception as e:
            raise InfrastructureException(
                "Failed to check index health",
                original_exception=e
            )

    async def reindex(
        self,
        source_index: str,
        dest_index: str,
        wait_for_completion: bool = True
    ) -> Dict[str, Any]:
        """
        Reindex data from source to destination index.

        Useful for schema migrations or index optimizations.

        Args:
            source_index: Source index name
            dest_index: Destination index name
            wait_for_completion: If True, wait for reindex to complete

        Returns:
            Reindex operation response

        Raises:
            InfrastructureException: If reindex fails
        """
        try:
            client = self.client.get_client()

            # Check source exists
            if not await self.client.index_exists(source_index):
                raise InfrastructureException(
                    f"Source index '{source_index}' does not exist",
                    context={"source": source_index}
                )

            # Build reindex body
            body = {
                "source": {"index": source_index},
                "dest": {"index": dest_index}
            }

            logger.info(f"Starting reindex from {source_index} to {dest_index}")

            # Execute reindex
            response = await client.reindex(
                body=body,
                wait_for_completion=wait_for_completion
            )

            logger.info(
                f"Reindex completed: {response.get('total', 0)} documents processed"
            )

            return response

        except Exception as e:
            raise InfrastructureException(
                f"Failed to reindex from {source_index} to {dest_index}",
                context={"source": source_index, "dest": dest_index},
                original_exception=e
            )

    async def update_index_settings(
        self,
        index_name: str,
        settings: Dict[str, Any]
    ) -> bool:
        """
        Update settings for an existing index.

        Note: Some settings require the index to be closed first.

        Args:
            index_name: Name of the index
            settings: Settings to update

        Returns:
            True if update successful

        Raises:
            InfrastructureException: If update fails
        """
        try:
            client = self.client.get_client()

            # Check index exists
            if not await self.client.index_exists(index_name):
                raise InfrastructureException(
                    f"Index '{index_name}' does not exist",
                    context={"index": index_name}
                )

            # Update settings
            await client.indices.put_settings(
                index=index_name,
                body=settings
            )

            logger.info(f"Updated settings for index: {index_name}")

            return True

        except Exception as e:
            raise InfrastructureException(
                f"Failed to update index settings",
                context={"index": index_name},
                original_exception=e
            )

    async def refresh_all_indexes(self) -> Dict[str, bool]:
        """
        Refresh all indexes to make recent changes searchable.

        Returns:
            Dictionary mapping index names to refresh success status

        Raises:
            InfrastructureException: If refresh fails
        """
        results = {}

        try:
            for index_name in INDEX_CONFIGS.keys():
                if not await self.client.index_exists(index_name):
                    results[index_name] = False
                    continue

                await self.client.refresh_index(index_name)
                results[index_name] = True

            logger.info("Refreshed all indexes")

            return results

        except Exception as e:
            raise InfrastructureException(
                "Failed to refresh all indexes",
                context={"partial_results": results},
                original_exception=e
            )

    async def get_index_mapping(self, index_name: str) -> Dict[str, Any]:
        """
        Get the current mapping for an index.

        Args:
            index_name: Name of the index

        Returns:
            Index mapping dictionary

        Raises:
            InfrastructureException: If operation fails
        """
        try:
            client = self.client.get_client()

            # Check index exists
            if not await self.client.index_exists(index_name):
                raise InfrastructureException(
                    f"Index '{index_name}' does not exist",
                    context={"index": index_name}
                )

            # Get mapping
            response = await client.indices.get_mapping(index=index_name)

            return response.get(index_name, {})

        except Exception as e:
            raise InfrastructureException(
                f"Failed to get index mapping",
                context={"index": index_name},
                original_exception=e
            )


async def get_index_manager() -> OpenSearchIndexManager:
    """
    Get an index manager instance.

    Returns:
        OpenSearchIndexManager instance

    Example:
        >>> from app.infrastructure.persistence.opensearch.client import get_opensearch_client
        >>> client = await get_opensearch_client()
        >>> manager = OpenSearchIndexManager(client)
        >>> await manager.create_all_indexes()
    """
    from app.infrastructure.persistence.opensearch.client import get_opensearch_client

    client = await get_opensearch_client()
    return OpenSearchIndexManager(client)
