"""
Document indexing service package.

This package provides comprehensive document indexing capabilities for the
Qdrant vector database, including:
- Dense embedding generation for semantic search
- Sparse BM25 vectors for keyword search
- Multi-vector indexing (summary, section, microblock)
- Batch indexing and updates
- Case and document-level operations

Main exports:
- IndexingService: Main service class for orchestrating indexing operations
- get_indexing_service: Factory function for singleton service instance
- EmbeddingGenerator: Dense embedding generation
- SparseVectorGenerator: BM25 sparse vector generation
"""

from app.services.indexing.core import IndexingService, get_indexing_service
from app.services.indexing.embeddings import EmbeddingGenerator
from app.services.indexing.sparse import SparseVectorGenerator

__all__ = [
    "IndexingService",
    "get_indexing_service",
    "EmbeddingGenerator",
    "SparseVectorGenerator",
]
