"""
Ollama Semaphore Service

Manages concurrent access to Ollama using Redis-based distributed semaphore.
Prevents RAM/VRAM exhaustion when multiple workers try to call Ollama simultaneously.
"""
import logging
import redis
from contextlib import contextmanager
from typing import Optional
import time

from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaSemaphore:
    """
    Distributed semaphore for managing concurrent Ollama requests across Celery workers.

    Uses Redis to implement a distributed counting semaphore that limits concurrent
    access to Ollama LLM, preventing RAM/VRAM exhaustion.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_concurrent: Optional[int] = None,
        semaphore_key: str = "ollama:semaphore",
        timeout: int = 120  # 2 minutes default timeout
    ):
        """
        Initialize Ollama semaphore.

        Args:
            redis_url: Redis connection URL (defaults to settings.REDIS_URL)
            max_concurrent: Maximum concurrent requests (defaults to settings.OLLAMA_MAX_CONCURRENT_REQUESTS)
            semaphore_key: Redis key for the semaphore
            timeout: Maximum time to wait for semaphore acquisition (seconds)
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.max_concurrent = max_concurrent or settings.OLLAMA_MAX_CONCURRENT_REQUESTS
        self.semaphore_key = semaphore_key
        self.timeout = timeout

        # Create Redis connection
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"OllamaSemaphore initialized: max_concurrent={self.max_concurrent}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis for Ollama semaphore: {e}")
            self.redis_client = None

    @contextmanager
    def acquire(self, blocking: bool = True, timeout: Optional[int] = None):
        """
        Acquire semaphore for Ollama access.

        Args:
            blocking: If True, wait for semaphore. If False, fail immediately if unavailable.
            timeout: Override default timeout (seconds)

        Yields:
            True if semaphore acquired, raises Exception if failed

        Example:
            semaphore = OllamaSemaphore()
            with semaphore.acquire():
                # Make Ollama API call
                result = await ollama_client.generate(...)
        """
        if not self.redis_client:
            # Redis unavailable, allow request to proceed (degraded mode)
            logger.warning("Redis unavailable, bypassing Ollama semaphore (degraded mode)")
            yield True
            return

        acquired = False
        token = None
        timeout = timeout or self.timeout
        start_time = time.time()

        try:
            # Try to acquire semaphore
            while True:
                # Get current count of active requests
                current_count = self.redis_client.get(self.semaphore_key)
                current_count = int(current_count) if current_count else 0

                if current_count < self.max_concurrent:
                    # Increment counter atomically
                    new_count = self.redis_client.incr(self.semaphore_key)

                    if new_count <= self.max_concurrent:
                        # Successfully acquired
                        acquired = True
                        token = new_count
                        logger.info(f"Ollama semaphore acquired ({new_count}/{self.max_concurrent})")
                        break
                    else:
                        # Race condition: another worker incremented first
                        # Decrement and retry
                        self.redis_client.decr(self.semaphore_key)

                # Check if we should continue waiting
                if not blocking:
                    raise TimeoutError("Ollama semaphore unavailable (non-blocking mode)")

                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    raise TimeoutError(
                        f"Timeout waiting for Ollama semaphore after {elapsed:.1f}s "
                        f"({current_count}/{self.max_concurrent} slots in use)"
                    )

                # Wait and retry
                wait_time = min(1.0, timeout - elapsed)
                logger.debug(f"Waiting for Ollama semaphore... ({current_count}/{self.max_concurrent} slots in use)")
                time.sleep(wait_time)

            yield True

        finally:
            # Release semaphore
            if acquired and self.redis_client:
                try:
                    new_count = self.redis_client.decr(self.semaphore_key)
                    logger.info(f"Ollama semaphore released ({new_count}/{self.max_concurrent})")

                    # Clean up if count reaches 0
                    if new_count <= 0:
                        self.redis_client.delete(self.semaphore_key)
                        logger.debug("Ollama semaphore cleaned up (count reached 0)")

                except Exception as e:
                    logger.error(f"Failed to release Ollama semaphore: {e}")

    def get_current_usage(self) -> int:
        """
        Get current number of active Ollama requests.

        Returns:
            Current usage count
        """
        if not self.redis_client:
            return 0

        try:
            count = self.redis_client.get(self.semaphore_key)
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Failed to get Ollama semaphore usage: {e}")
            return 0

    def reset(self):
        """
        Reset semaphore counter (emergency use only).

        This should only be used if workers crash and leave the semaphore in an inconsistent state.
        """
        if not self.redis_client:
            return

        try:
            self.redis_client.delete(self.semaphore_key)
            logger.warning("Ollama semaphore forcefully reset")
        except Exception as e:
            logger.error(f"Failed to reset Ollama semaphore: {e}")


# Global singleton instance
_ollama_semaphore = None


def get_ollama_semaphore() -> OllamaSemaphore:
    """
    Get or create global Ollama semaphore instance.

    Returns:
        OllamaSemaphore instance
    """
    global _ollama_semaphore

    if _ollama_semaphore is None:
        _ollama_semaphore = OllamaSemaphore()

    return _ollama_semaphore
