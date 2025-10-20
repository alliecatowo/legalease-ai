"""
Base BM25 repository for OpenSearch operations.

This module provides an abstract base class for all OpenSearch repositories
with common search and indexing operations.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Generic, TypeVar

from opensearchpy import AsyncOpenSearch, exceptions as opensearch_exceptions

from app.infrastructure.persistence.opensearch.client import OpenSearchClient
from app.shared.exceptions.domain_exceptions import InfrastructureException, RepositoryException


logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class SearchResult:
    """
    Search result with document and metadata.

    Attributes:
        id: Document ID
        score: BM25 relevance score
        source: Document source data
        highlights: Optional highlighted text snippets
    """
    id: str
    score: float
    source: Dict[str, Any]
    highlights: Optional[Dict[str, List[str]]] = None


@dataclass
class SearchResults:
    """
    Collection of search results with pagination metadata.

    Attributes:
        results: List of search results
        total: Total number of matching documents
        took: Query execution time in milliseconds
        max_score: Highest relevance score in results
    """
    results: List[SearchResult]
    total: int
    took: int
    max_score: Optional[float] = None


class BaseBM25Repository(ABC):
    """
    Abstract base repository for OpenSearch BM25 operations.

    Provides common methods for indexing, searching, and deleting documents
    with BM25 ranking. Subclasses should implement index-specific logic.
    """

    def __init__(self, client: OpenSearchClient, index_name: str):
        """
        Initialize repository.

        Args:
            client: OpenSearch client instance
            index_name: Name of the index to operate on
        """
        self.client = client
        self.index_name = index_name

    def _get_client(self) -> AsyncOpenSearch:
        """Get the underlying OpenSearch client."""
        return self.client.get_client()

    async def index_document(
        self,
        doc_id: str,
        document: Dict[str, Any],
        refresh: bool = False
    ) -> bool:
        """
        Index a single document.

        Args:
            doc_id: Document ID
            document: Document data to index
            refresh: If True, refresh index immediately

        Returns:
            True if indexed successfully

        Raises:
            RepositoryException: If indexing fails
        """
        try:
            client = self._get_client()

            await client.index(
                index=self.index_name,
                id=doc_id,
                body=document,
                refresh=refresh
            )

            logger.debug(f"Indexed document {doc_id} in {self.index_name}")
            return True

        except opensearch_exceptions.RequestError as e:
            raise RepositoryException(
                f"Invalid document format for indexing",
                context={"index": self.index_name, "doc_id": doc_id},
                original_exception=e
            )
        except Exception as e:
            raise RepositoryException(
                f"Failed to index document",
                context={"index": self.index_name, "doc_id": doc_id},
                original_exception=e
            )

    async def bulk_index(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 500,
        refresh: bool = False
    ) -> int:
        """
        Bulk index multiple documents.

        Args:
            documents: List of documents to index (must have 'id' field)
            batch_size: Number of documents per batch
            refresh: If True, refresh index after bulk operation

        Returns:
            Number of documents successfully indexed

        Raises:
            RepositoryException: If bulk indexing fails
        """
        try:
            client = self._get_client()
            indexed_count = 0

            # Process in batches
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]

                # Build bulk operations
                operations = []
                for doc in batch:
                    if 'id' not in doc:
                        logger.warning(f"Document missing 'id' field, skipping")
                        continue

                    doc_id = doc.pop('id')

                    # Index action
                    operations.append({
                        "index": {
                            "_index": self.index_name,
                            "_id": doc_id,
                        }
                    })
                    # Document data
                    operations.append(doc)

                if not operations:
                    continue

                # Execute bulk operation
                response = await client.bulk(body=operations, refresh=refresh)

                # Count successful operations
                if response.get('errors'):
                    for item in response.get('items', []):
                        if 'index' in item:
                            if item['index'].get('status') in [200, 201]:
                                indexed_count += 1
                            else:
                                logger.error(f"Failed to index document: {item['index'].get('error')}")
                else:
                    indexed_count += len(batch)

            logger.info(f"Bulk indexed {indexed_count}/{len(documents)} documents in {self.index_name}")
            return indexed_count

        except Exception as e:
            raise RepositoryException(
                f"Bulk indexing failed",
                context={"index": self.index_name, "total_docs": len(documents)},
                original_exception=e
            )

    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        from_: int = 0,
        size: int = 10,
        fields: Optional[List[str]] = None,
        highlight_fields: Optional[List[str]] = None,
    ) -> SearchResults:
        """
        Search documents using BM25 ranking.

        Args:
            query: Search query string
            filters: Optional filters (e.g., {"case_id": "123"})
            from_: Pagination offset
            size: Number of results to return
            fields: Fields to search (defaults to ["text"])
            highlight_fields: Fields to highlight in results

        Returns:
            SearchResults with matching documents

        Raises:
            RepositoryException: If search fails
        """
        try:
            client = self._get_client()

            # Default to searching text field
            if fields is None:
                fields = ["text"]

            # Build multi-match query
            must_clauses = [{
                "multi_match": {
                    "query": query,
                    "fields": fields,
                    "type": "best_fields",
                    "operator": "or",
                }
            }]

            # Add filters
            filter_clauses = []
            if filters:
                for field, value in filters.items():
                    if isinstance(value, list):
                        filter_clauses.append({"terms": {field: value}})
                    else:
                        filter_clauses.append({"term": {field: value}})

            # Build query
            search_body: Dict[str, Any] = {
                "query": {
                    "bool": {
                        "must": must_clauses,
                        "filter": filter_clauses,
                    }
                },
                "from": from_,
                "size": size,
            }

            # Add highlighting
            if highlight_fields:
                search_body["highlight"] = {
                    "fields": {field: {} for field in highlight_fields},
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"],
                }

            # Execute search
            response = await client.search(
                index=self.index_name,
                body=search_body
            )

            # Parse results
            hits = response.get('hits', {})
            results = [
                SearchResult(
                    id=hit['_id'],
                    score=hit['_score'],
                    source=hit['_source'],
                    highlights=hit.get('highlight')
                )
                for hit in hits.get('hits', [])
            ]

            return SearchResults(
                results=results,
                total=hits.get('total', {}).get('value', 0),
                took=response.get('took', 0),
                max_score=hits.get('max_score')
            )

        except opensearch_exceptions.RequestError as e:
            raise RepositoryException(
                f"Invalid search query",
                context={"index": self.index_name, "query": query},
                original_exception=e
            )
        except Exception as e:
            raise RepositoryException(
                f"Search failed",
                context={"index": self.index_name, "query": query},
                original_exception=e
            )

    async def delete_by_id(self, doc_ids: List[str]) -> int:
        """
        Delete documents by ID.

        Args:
            doc_ids: List of document IDs to delete

        Returns:
            Number of documents deleted

        Raises:
            RepositoryException: If deletion fails
        """
        try:
            client = self._get_client()
            deleted_count = 0

            # Build bulk delete operations
            operations = []
            for doc_id in doc_ids:
                operations.append({
                    "delete": {
                        "_index": self.index_name,
                        "_id": doc_id,
                    }
                })

            if not operations:
                return 0

            # Execute bulk delete
            response = await client.bulk(body=operations, refresh=True)

            # Count successful deletions
            for item in response.get('items', []):
                if 'delete' in item:
                    if item['delete'].get('status') in [200, 404]:  # 404 = already deleted
                        deleted_count += 1

            logger.info(f"Deleted {deleted_count}/{len(doc_ids)} documents from {self.index_name}")
            return deleted_count

        except Exception as e:
            raise RepositoryException(
                f"Failed to delete documents",
                context={"index": self.index_name, "count": len(doc_ids)},
                original_exception=e
            )

    async def delete_by_query(self, query: Dict[str, Any]) -> int:
        """
        Delete documents matching a query.

        Args:
            query: OpenSearch query DSL

        Returns:
            Number of documents deleted

        Raises:
            RepositoryException: If deletion fails
        """
        try:
            client = self._get_client()

            response = await client.delete_by_query(
                index=self.index_name,
                body={"query": query},
                refresh=True
            )

            deleted = response.get('deleted', 0)
            logger.info(f"Deleted {deleted} documents from {self.index_name}")

            return deleted

        except Exception as e:
            raise RepositoryException(
                f"Failed to delete by query",
                context={"index": self.index_name},
                original_exception=e
            )

    async def count(self, query: Optional[Dict[str, Any]] = None) -> int:
        """
        Count documents matching a query.

        Args:
            query: Optional query DSL (counts all if None)

        Returns:
            Number of matching documents

        Raises:
            RepositoryException: If count fails
        """
        try:
            client = self._get_client()

            body = {"query": query} if query else None
            response = await client.count(index=self.index_name, body=body)

            return response.get('count', 0)

        except Exception as e:
            raise RepositoryException(
                f"Failed to count documents",
                context={"index": self.index_name},
                original_exception=e
            )
