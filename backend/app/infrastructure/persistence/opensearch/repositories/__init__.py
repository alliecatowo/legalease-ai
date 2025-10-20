"""
OpenSearch repositories for BM25 lexical search.

This package provides repositories for searching legal documents,
transcripts, communications, and findings using BM25 ranking.
"""

from app.infrastructure.persistence.opensearch.repositories.base import (
    BaseBM25Repository,
    SearchResult,
    SearchResults,
)
from app.infrastructure.persistence.opensearch.repositories.document import (
    OpenSearchDocumentRepository,
)
from app.infrastructure.persistence.opensearch.repositories.transcript import (
    OpenSearchTranscriptRepository,
)
from app.infrastructure.persistence.opensearch.repositories.communication import (
    OpenSearchCommunicationRepository,
)
from app.infrastructure.persistence.opensearch.repositories.finding import (
    OpenSearchFindingRepository,
)


__all__ = [
    # Base classes
    "BaseBM25Repository",
    "SearchResult",
    "SearchResults",
    # Repositories
    "OpenSearchDocumentRepository",
    "OpenSearchTranscriptRepository",
    "OpenSearchCommunicationRepository",
    "OpenSearchFindingRepository",
]
