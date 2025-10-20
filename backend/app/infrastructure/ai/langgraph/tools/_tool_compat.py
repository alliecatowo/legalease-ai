"""
Compatibility helpers for LangChain Tool.

The production code expects ``langchain.tools.Tool`` to be available, but the
test environment may not have LangChain installed. To keep the architecture
decoupled from optional dependencies, we provide a lightweight fallback
implementation that mimics the relevant behaviour.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional

try:  # pragma: no cover - prefer the real implementation when available
    from langchain.tools import Tool  # type: ignore
except ImportError:  # pragma: no cover

    class Tool:  # type: ignore
        """Minimal stub compatible with LangChain's Tool interface."""

        def __init__(
            self,
            name: str,
            description: str,
            func: Callable[..., Any],
            coroutine: Optional[Callable[..., Awaitable[Any]]] = None,
        ) -> None:
            self.name = name
            self.description = description
            self.func = func
            self.coroutine = coroutine or _wrap_sync(func)

        async def arun(self, *args: Any, **kwargs: Any) -> Any:
            """Async execution helper."""
            return await self.coroutine(*args, **kwargs)

        def run(self, *args: Any, **kwargs: Any) -> Any:
            """Synchronous execution helper."""
            return self.func(*args, **kwargs)


def _wrap_sync(func: Callable[..., Any]) -> Callable[..., Awaitable[Any]]:
    """Wrap a sync function so it can be awaited like a coroutine."""

    async def _inner(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    return _inner


__all__ = ["Tool"]
