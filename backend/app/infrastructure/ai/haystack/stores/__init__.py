"""
Haystack store components for dual-store architecture.

This package contains components for writing to both:
- Qdrant (dense vector search)
- OpenSearch (BM25 sparse search)
"""

from app.infrastructure.ai.haystack.stores.dual_store_writer import DualStoreWriter

__all__ = [
    "DualStoreWriter",
]
