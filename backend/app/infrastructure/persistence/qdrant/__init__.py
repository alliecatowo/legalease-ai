"""
Qdrant vector database integration.

This package provides vector storage and retrieval functionality using Qdrant,
following hexagonal architecture principles with clean separation of concerns.
"""

from app.infrastructure.persistence.qdrant.client import (
    EnhancedQdrantClient,
    get_qdrant_client,
    close_qdrant_client,
)
from app.infrastructure.persistence.qdrant.collection_manager import (
    CollectionManager,
    CollectionName,
)
from app.infrastructure.persistence.qdrant.repositories import (
    BaseQdrantRepository,
    QdrantDocumentRepository,
    QdrantTranscriptRepository,
    QdrantCommunicationRepository,
    QdrantFindingRepository,
)

__all__ = [
    # Client
    "EnhancedQdrantClient",
    "get_qdrant_client",
    "close_qdrant_client",
    # Collection management
    "CollectionManager",
    "CollectionName",
    # Repositories
    "BaseQdrantRepository",
    "QdrantDocumentRepository",
    "QdrantTranscriptRepository",
    "QdrantCommunicationRepository",
    "QdrantFindingRepository",
]
