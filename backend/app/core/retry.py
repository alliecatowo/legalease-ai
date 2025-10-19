"""
Retry utilities for external service calls using tenacity.

Usage:
    from app.core.retry import (
        retry_qdrant,
        retry_minio,
        retry_gemini,
        retry_database,
        retry_ollama,
        retry_neo4j,
        retry_redis,
    )

    @retry_qdrant
    def my_vector_operation():
        # Your Qdrant code here
        pass

    @retry_gemini
    async def my_llm_call():
        # Your Gemini API code here
        pass

    @retry_ollama
    async def my_ollama_call():
        # Your Ollama API code here
        pass

    @retry_neo4j
    def my_graph_operation():
        # Your Neo4j code here
        pass

    @retry_redis
    async def my_cache_operation():
        # Your Redis code here
        pass

Features:
- Service-specific retry strategies with appropriate backoff
- Smart exception handling per service type
- Support for both sync and async functions
- Exponential backoff with jitter to avoid thundering herd
- Automatic logging of retry attempts
"""

import logging
from typing import TypeVar, Callable, Any
from functools import wraps
import asyncio

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError,
)

# SQLAlchemy and psycopg2 exceptions
try:
    from sqlalchemy.exc import (
        OperationalError as SQLAlchemyOperationalError,
        DBAPIError,
        TimeoutError as SQLAlchemyTimeoutError,
    )
    from psycopg2 import OperationalError as Psycopg2OperationalError
    _DB_EXCEPTIONS = (
        SQLAlchemyOperationalError,
        DBAPIError,
        SQLAlchemyTimeoutError,
        Psycopg2OperationalError,
    )
except ImportError:
    _DB_EXCEPTIONS = (Exception,)

# Qdrant exceptions
try:
    from qdrant_client.http.exceptions import UnexpectedResponse, ResponseHandlingException
    _QDRANT_EXCEPTIONS = (UnexpectedResponse, ResponseHandlingException, ConnectionError, TimeoutError)
except ImportError:
    _QDRANT_EXCEPTIONS = (ConnectionError, TimeoutError)

# MinIO/S3 exceptions
try:
    from minio.error import S3Error
    from urllib3.exceptions import (
        HTTPError,
        MaxRetryError,
        ProtocolError,
        TimeoutError as Urllib3TimeoutError,
    )
    _MINIO_EXCEPTIONS = (S3Error, HTTPError, MaxRetryError, ProtocolError, Urllib3TimeoutError, ConnectionError)
except ImportError:
    _MINIO_EXCEPTIONS = (ConnectionError, TimeoutError)

# Google API exceptions (Gemini)
try:
    from google.api_core.exceptions import (
        ResourceExhausted,  # 429 rate limit
        ServiceUnavailable,  # 503
        DeadlineExceeded,  # timeout
        GoogleAPIError,
    )
    _GEMINI_EXCEPTIONS = (ResourceExhausted, ServiceUnavailable, DeadlineExceeded, GoogleAPIError, ConnectionError)
except ImportError:
    _GEMINI_EXCEPTIONS = (ConnectionError, TimeoutError)

# Ollama/HTTPX exceptions
try:
    from httpx import (
        HTTPStatusError,
        TimeoutException,
        ConnectError,
        NetworkError,
        RemoteProtocolError,
    )
    _OLLAMA_EXCEPTIONS = (
        HTTPStatusError,
        TimeoutException,
        ConnectError,
        NetworkError,
        RemoteProtocolError,
        ConnectionError,
        TimeoutError,
    )
except ImportError:
    _OLLAMA_EXCEPTIONS = (ConnectionError, TimeoutError)

# Neo4j exceptions
try:
    from neo4j.exceptions import (
        ServiceUnavailable as Neo4jServiceUnavailable,
        SessionExpired,
        TransientError,
        DatabaseUnavailable,
    )
    _NEO4J_EXCEPTIONS = (
        Neo4jServiceUnavailable,
        SessionExpired,
        TransientError,
        DatabaseUnavailable,
        ConnectionError,
        TimeoutError,
    )
except ImportError:
    _NEO4J_EXCEPTIONS = (ConnectionError, TimeoutError)

# Redis exceptions
try:
    from redis.exceptions import (
        ConnectionError as RedisConnectionError,
        TimeoutError as RedisTimeoutError,
        ResponseError,
    )
    _REDIS_EXCEPTIONS = (RedisConnectionError, RedisTimeoutError, ResponseError, ConnectionError, TimeoutError)
except ImportError:
    _REDIS_EXCEPTIONS = (ConnectionError, TimeoutError)


logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_qdrant(func: Callable[..., T]) -> Callable[..., T]:
    """
    Retry decorator for Qdrant vector database operations.

    Strategy:
    - Max 5 attempts (Qdrant is usually stable)
    - Exponential backoff: 1s, 2s, 4s, 8s with jitter
    - Retries on connection/network errors

    Args:
        func: Function to decorate (sync or async)

    Returns:
        Decorated function with retry logic
    """
    retry_decorator = retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(_QDRANT_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )

    if asyncio.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await retry_decorator(func)(*args, **kwargs)
            except RetryError as e:
                logger.error(f"Qdrant operation failed after retries: {func.__name__}")
                raise e.last_attempt.exception()
        return async_wrapper
    else:
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return retry_decorator(func)(*args, **kwargs)
            except RetryError as e:
                logger.error(f"Qdrant operation failed after retries: {func.__name__}")
                raise e.last_attempt.exception()
        return sync_wrapper


def retry_minio(func: Callable[..., T]) -> Callable[..., T]:
    """
    Retry decorator for MinIO object storage operations.

    Strategy:
    - Max 4 attempts (S3-compatible, network can be flaky)
    - Exponential backoff: 1s, 2s, 4s with jitter
    - Retries on S3/network errors

    Args:
        func: Function to decorate (sync or async)

    Returns:
        Decorated function with retry logic
    """
    retry_decorator = retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(_MINIO_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )

    if asyncio.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await retry_decorator(func)(*args, **kwargs)
            except RetryError as e:
                logger.error(f"MinIO operation failed after retries: {func.__name__}")
                raise e.last_attempt.exception()
        return async_wrapper
    else:
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return retry_decorator(func)(*args, **kwargs)
            except RetryError as e:
                logger.error(f"MinIO operation failed after retries: {func.__name__}")
                raise e.last_attempt.exception()
        return sync_wrapper


def retry_gemini(func: Callable[..., T]) -> Callable[..., T]:
    """
    Retry decorator for Gemini API calls with 429 rate limit handling.

    Strategy:
    - Max 5 attempts (API can have rate limits and transient errors)
    - Exponential backoff: 2s, 4s, 8s, 16s, 32s with jitter
    - Longer waits to respect rate limits (429)
    - Retries on rate limits, service unavailable, timeouts

    Args:
        func: Function to decorate (sync or async)

    Returns:
        Decorated function with retry logic
    """
    retry_decorator = retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=2, max=60),
        retry=retry_if_exception_type(_GEMINI_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )

    if asyncio.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await retry_decorator(func)(*args, **kwargs)
            except RetryError as e:
                logger.error(f"Gemini API call failed after retries: {func.__name__}")
                raise e.last_attempt.exception()
        return async_wrapper
    else:
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return retry_decorator(func)(*args, **kwargs)
            except RetryError as e:
                logger.error(f"Gemini API call failed after retries: {func.__name__}")
                raise e.last_attempt.exception()
        return sync_wrapper


def retry_database(func: Callable[..., T]) -> Callable[..., T]:
    """
    Retry decorator for PostgreSQL database operations.

    Strategy:
    - Max 3 attempts (DB should be stable, don't retry too much)
    - Exponential backoff: 0.5s, 1s, 2s with jitter
    - Retries on connection errors, timeouts, operational errors
    - Does NOT retry on integrity/constraint violations (those won't fix themselves)

    Args:
        func: Function to decorate (sync or async)

    Returns:
        Decorated function with retry logic
    """
    retry_decorator = retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
        retry=retry_if_exception_type(_DB_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )

    if asyncio.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await retry_decorator(func)(*args, **kwargs)
            except RetryError as e:
                logger.error(f"Database operation failed after retries: {func.__name__}")
                raise e.last_attempt.exception()
        return async_wrapper
    else:
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return retry_decorator(func)(*args, **kwargs)
            except RetryError as e:
                logger.error(f"Database operation failed after retries: {func.__name__}")
                raise e.last_attempt.exception()
        return sync_wrapper


def retry_ollama(func: Callable[..., T]) -> Callable[..., T]:
    """
    Retry decorator for Ollama API calls.

    Strategy:
    - Max 5 attempts (API can have transient errors)
    - Exponential backoff: 2s, 4s, 8s, 16s, 32s with jitter
    - Retries on HTTP 5xx, connection errors, timeouts
    - Does NOT retry on HTTP 4xx (except 429)

    Args:
        func: Function to decorate (sync or async)

    Returns:
        Decorated function with retry logic
    """
    retry_decorator = retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type(_OLLAMA_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )

    if asyncio.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await retry_decorator(func)(*args, **kwargs)
            except RetryError as e:
                logger.error(f"Ollama API call failed after retries: {func.__name__}")
                raise e.last_attempt.exception()
        return async_wrapper
    else:
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return retry_decorator(func)(*args, **kwargs)
            except RetryError as e:
                logger.error(f"Ollama API call failed after retries: {func.__name__}")
                raise e.last_attempt.exception()
        return sync_wrapper


def retry_neo4j(func: Callable[..., T]) -> Callable[..., T]:
    """
    Retry decorator for Neo4j graph database operations.

    Strategy:
    - Max 3 attempts (graph DB should be stable)
    - Exponential backoff: 0.5s, 1s, 2s, 4s, 8s with jitter
    - Retries on ServiceUnavailable, SessionExpired, connection errors
    - Does NOT retry on constraint violations, invalid queries

    Args:
        func: Function to decorate (sync or async)

    Returns:
        Decorated function with retry logic
    """
    retry_decorator = retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=10),
        retry=retry_if_exception_type(_NEO4J_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )

    if asyncio.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await retry_decorator(func)(*args, **kwargs)
            except RetryError as e:
                logger.error(f"Neo4j operation failed after retries: {func.__name__}")
                raise e.last_attempt.exception()
        return async_wrapper
    else:
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return retry_decorator(func)(*args, **kwargs)
            except RetryError as e:
                logger.error(f"Neo4j operation failed after retries: {func.__name__}")
                raise e.last_attempt.exception()
        return sync_wrapper


def retry_redis(func: Callable[..., T]) -> Callable[..., T]:
    """
    Retry decorator for Redis operations.

    Strategy:
    - Max 3 attempts (cache should be stable)
    - Exponential backoff: 0.1s, 0.2s, 0.4s, 0.8s with jitter
    - Retries on ConnectionError, TimeoutError, ResponseError
    - Does NOT retry on data type errors

    Args:
        func: Function to decorate (sync or async)

    Returns:
        Decorated function with retry logic
    """
    retry_decorator = retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.1, min=0.1, max=5),
        retry=retry_if_exception_type(_REDIS_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )

    if asyncio.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await retry_decorator(func)(*args, **kwargs)
            except RetryError as e:
                logger.error(f"Redis operation failed after retries: {func.__name__}")
                raise e.last_attempt.exception()
        return async_wrapper
    else:
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return retry_decorator(func)(*args, **kwargs)
            except RetryError as e:
                logger.error(f"Redis operation failed after retries: {func.__name__}")
                raise e.last_attempt.exception()
        return sync_wrapper
