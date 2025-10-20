"""
Enhanced Neo4j client with production-ready features.

This module provides a production-grade Neo4j client with:
- Connection pooling
- Retry logic with exponential backoff
- Transaction management
- Health checks
- Read/write session handling
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional, AsyncContextManager
from contextlib import asynccontextmanager

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession, AsyncManagedTransaction
from neo4j.exceptions import (
    ServiceUnavailable,
    SessionExpired,
    TransientError,
    Neo4jError,
)

from app.core.config import settings
from app.shared.exceptions.domain_exceptions import RepositoryException

logger = logging.getLogger(__name__)


class Neo4jClient:
    """
    Production-ready Neo4j client with connection management and reliability features.

    This client handles:
    - Asynchronous operations via async driver
    - Connection pooling with configurable pool size
    - Automatic retry with exponential backoff for transient errors
    - Transaction management with context managers
    - Health checks for monitoring
    - Separate read and write sessions for optimal performance

    Example:
        >>> client = Neo4jClient()
        >>> await client.initialize()
        >>> async with client.write_transaction() as tx:
        ...     result = await tx.run("CREATE (n:Person {name: $name})", name="Alice")
        >>> await client.close()
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        max_connection_pool_size: Optional[int] = None,
        connection_timeout: Optional[int] = None,
        max_transaction_retry_time: Optional[int] = None,
    ):
        """
        Initialize Neo4j client.

        Args:
            uri: Neo4j connection URI (default from settings)
            user: Neo4j username (default from settings)
            password: Neo4j password (default from settings)
            max_connection_pool_size: Maximum connection pool size (default from settings)
            connection_timeout: Connection timeout in seconds (default from settings)
            max_transaction_retry_time: Max retry time in seconds (default from settings)
        """
        self.uri = uri or settings.NEO4J_URI
        self.user = user or settings.NEO4J_USER
        self.password = password or settings.NEO4J_PASSWORD
        self.max_connection_pool_size = (
            max_connection_pool_size or settings.NEO4J_MAX_CONNECTION_POOL_SIZE
        )
        self.connection_timeout = (
            connection_timeout or settings.NEO4J_CONNECTION_TIMEOUT
        )
        self.max_transaction_retry_time = (
            max_transaction_retry_time or settings.NEO4J_MAX_TRANSACTION_RETRY_TIME
        )

        self._driver: Optional[AsyncDriver] = None
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize the Neo4j driver and connection pool.

        This should be called during application startup.

        Raises:
            RepositoryException: If initialization fails
        """
        if self._initialized:
            logger.warning("Neo4j client already initialized")
            return

        try:
            logger.info(
                f"Initializing Neo4j client: uri={self.uri}, "
                f"pool_size={self.max_connection_pool_size}"
            )

            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_pool_size=self.max_connection_pool_size,
                connection_timeout=self.connection_timeout,
                max_transaction_retry_time=self.max_transaction_retry_time,
            )

            # Verify connectivity
            await self._driver.verify_connectivity()

            self._initialized = True
            logger.info("Neo4j client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Neo4j client: {e}")
            raise RepositoryException(
                "Failed to initialize Neo4j connection",
                context={"uri": self.uri},
                original_exception=e,
            )

    async def close(self) -> None:
        """
        Close the Neo4j driver and release all connections.

        This should be called during application shutdown.
        """
        if not self._initialized:
            return

        try:
            if self._driver:
                await self._driver.close()
                logger.info("Neo4j client closed successfully")
        except Exception as e:
            logger.error(f"Error closing Neo4j client: {e}")
        finally:
            self._driver = None
            self._initialized = False

    def get_driver(self) -> AsyncDriver:
        """
        Get the Neo4j async driver.

        Returns:
            AsyncDriver instance

        Raises:
            RepositoryException: If client not initialized
        """
        if not self._initialized or not self._driver:
            raise RepositoryException(
                "Neo4j client not initialized. Call initialize() first."
            )
        return self._driver

    async def health_check(self) -> bool:
        """
        Check if Neo4j is accessible and healthy.

        Returns:
            True if healthy, False otherwise
        """
        if not self._initialized or not self._driver:
            logger.warning("Health check failed: client not initialized")
            return False

        try:
            async with self._driver.session() as session:
                result = await session.run("RETURN 1 AS health")
                record = await result.single()
                return record and record["health"] == 1
        except ServiceUnavailable:
            logger.error("Health check failed: Neo4j service unavailable")
            return False
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    @asynccontextmanager
    async def session(
        self,
        database: Optional[str] = None,
        default_access_mode: str = "WRITE"
    ) -> AsyncContextManager[AsyncSession]:
        """
        Context manager for Neo4j session.

        Args:
            database: Optional database name
            default_access_mode: "READ" or "WRITE"

        Yields:
            AsyncSession instance

        Example:
            >>> async with client.session() as session:
            ...     result = await session.run("MATCH (n) RETURN n LIMIT 1")
        """
        driver = self.get_driver()

        session = driver.session(
            database=database,
            default_access_mode=default_access_mode
        )

        try:
            yield session
        finally:
            await session.close()

    @asynccontextmanager
    async def read_session(
        self,
        database: Optional[str] = None
    ) -> AsyncContextManager[AsyncSession]:
        """
        Context manager for read-only session.

        Use this for queries that only read data for optimal routing.

        Args:
            database: Optional database name

        Yields:
            AsyncSession configured for reading
        """
        async with self.session(database=database, default_access_mode="READ") as session:
            yield session

    @asynccontextmanager
    async def write_session(
        self,
        database: Optional[str] = None
    ) -> AsyncContextManager[AsyncSession]:
        """
        Context manager for write session.

        Use this for queries that modify data.

        Args:
            database: Optional database name

        Yields:
            AsyncSession configured for writing
        """
        async with self.session(database=database, default_access_mode="WRITE") as session:
            yield session

    @asynccontextmanager
    async def read_transaction(
        self,
        database: Optional[str] = None
    ) -> AsyncContextManager[AsyncManagedTransaction]:
        """
        Context manager for read transaction.

        Args:
            database: Optional database name

        Yields:
            AsyncManagedTransaction for reading

        Example:
            >>> async with client.read_transaction() as tx:
            ...     result = await tx.run("MATCH (n:Person) RETURN n")
        """
        async with self.read_session(database=database) as session:
            async with session.begin_transaction() as tx:
                yield tx

    @asynccontextmanager
    async def write_transaction(
        self,
        database: Optional[str] = None
    ) -> AsyncContextManager[AsyncManagedTransaction]:
        """
        Context manager for write transaction.

        Args:
            database: Optional database name

        Yields:
            AsyncManagedTransaction for writing

        Example:
            >>> async with client.write_transaction() as tx:
            ...     await tx.run("CREATE (n:Person {name: $name})", name="Alice")
        """
        async with self.write_session(database=database) as session:
            async with session.begin_transaction() as tx:
                yield tx

    async def execute_read(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a read query with automatic retry.

        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Optional database name

        Returns:
            List of result records as dictionaries

        Raises:
            RepositoryException: If query fails after retries
        """
        parameters = parameters or {}

        return await self._execute_with_retry(
            query=query,
            parameters=parameters,
            database=database,
            read_mode=True,
        )

    async def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a write query with automatic retry.

        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Optional database name

        Returns:
            List of result records as dictionaries

        Raises:
            RepositoryException: If query fails after retries
        """
        parameters = parameters or {}

        return await self._execute_with_retry(
            query=query,
            parameters=parameters,
            database=database,
            read_mode=False,
        )

    async def _execute_with_retry(
        self,
        query: str,
        parameters: Dict[str, Any],
        database: Optional[str],
        read_mode: bool,
        max_retries: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Execute query with exponential backoff retry.

        Args:
            query: Cypher query
            parameters: Query parameters
            database: Optional database name
            read_mode: True for read, False for write
            max_retries: Maximum retry attempts

        Returns:
            List of result records

        Raises:
            RepositoryException: If all retries fail
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                session_context = (
                    self.read_session(database) if read_mode
                    else self.write_session(database)
                )

                async with session_context as session:
                    result = await session.run(query, parameters)
                    records = await result.data()
                    return records

            except (ServiceUnavailable, SessionExpired, TransientError) as e:
                last_exception = e

                if attempt < max_retries:
                    # Exponential backoff: 1s, 2s, 4s
                    delay = 2 ** attempt
                    logger.warning(
                        f"Query failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Query failed after {max_retries + 1} attempts: {e}")

            except Neo4jError as e:
                # Non-transient errors should not be retried
                logger.error(f"Neo4j error executing query: {e}")
                raise RepositoryException(
                    f"Neo4j query failed: {e.message}",
                    context={"query": query, "parameters": parameters},
                    original_exception=e,
                )

            except Exception as e:
                logger.error(f"Unexpected error executing query: {e}")
                raise RepositoryException(
                    "Unexpected error executing Neo4j query",
                    context={"query": query, "parameters": parameters},
                    original_exception=e,
                )

        # All retries exhausted
        raise RepositoryException(
            f"Query failed after {max_retries + 1} attempts",
            context={"query": query, "parameters": parameters},
            original_exception=last_exception,
        )


# Global client instance
_neo4j_client: Optional[Neo4jClient] = None


def get_neo4j_client() -> Neo4jClient:
    """
    Get the global Neo4j client instance.

    Returns:
        Neo4jClient instance

    Raises:
        RepositoryException: If client not initialized
    """
    global _neo4j_client

    if _neo4j_client is None:
        raise RepositoryException("Neo4j client not initialized")

    return _neo4j_client


async def init_neo4j() -> Neo4jClient:
    """
    Initialize the global Neo4j client.

    This should be called during application startup.

    Returns:
        Initialized Neo4jClient instance
    """
    global _neo4j_client

    if _neo4j_client is not None:
        logger.warning("Neo4j client already initialized")
        return _neo4j_client

    _neo4j_client = Neo4jClient()
    await _neo4j_client.initialize()

    return _neo4j_client


async def close_neo4j() -> None:
    """
    Close the global Neo4j client.

    This should be called during application shutdown.
    """
    global _neo4j_client

    if _neo4j_client is not None:
        await _neo4j_client.close()
        _neo4j_client = None
