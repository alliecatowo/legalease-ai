"""
OpenSearch infrastructure for BM25 lexical search.

This package provides:
- Async OpenSearch client with connection management
- Custom analyzers for legal text processing
- Index schemas for documents, transcripts, communications, and findings
- BM25 repositories for each data type
- Index lifecycle management

Example:
    >>> from app.infrastructure.persistence.opensearch import (
    ...     get_opensearch_client,
    ...     OpenSearchDocumentRepository,
    ...     get_index_manager
    ... )
    >>>
    >>> # Initialize client
    >>> client = await get_opensearch_client()
    >>>
    >>> # Create indexes
    >>> manager = await get_index_manager()
    >>> await manager.create_all_indexes()
    >>>
    >>> # Use repository
    >>> doc_repo = OpenSearchDocumentRepository(client)
    >>> results = await doc_repo.search_documents("contract terms", case_ids=[case_id])
"""

from app.infrastructure.persistence.opensearch.client import (
    OpenSearchClient,
    get_opensearch_client,
    close_opensearch_client,
    opensearch_client_context,
)
from app.infrastructure.persistence.opensearch.index_manager import (
    OpenSearchIndexManager,
    get_index_manager,
)
from app.infrastructure.persistence.opensearch.repositories import (
    BaseBM25Repository,
    SearchResult,
    SearchResults,
    OpenSearchDocumentRepository,
    OpenSearchTranscriptRepository,
    OpenSearchCommunicationRepository,
    OpenSearchFindingRepository,
)
from app.infrastructure.persistence.opensearch.schemas import (
    DOCUMENTS_INDEX,
    TRANSCRIPTS_INDEX,
    COMMUNICATIONS_INDEX,
    FINDINGS_INDEX,
    get_index_name,
)


__all__ = [
    # Client
    "OpenSearchClient",
    "get_opensearch_client",
    "close_opensearch_client",
    "opensearch_client_context",
    # Index management
    "OpenSearchIndexManager",
    "get_index_manager",
    # Repositories
    "BaseBM25Repository",
    "SearchResult",
    "SearchResults",
    "OpenSearchDocumentRepository",
    "OpenSearchTranscriptRepository",
    "OpenSearchCommunicationRepository",
    "OpenSearchFindingRepository",
    # Index names
    "DOCUMENTS_INDEX",
    "TRANSCRIPTS_INDEX",
    "COMMUNICATIONS_INDEX",
    "FINDINGS_INDEX",
    "get_index_name",
]
