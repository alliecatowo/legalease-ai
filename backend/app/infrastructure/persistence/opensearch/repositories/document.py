"""
Document BM25 repository for OpenSearch.

This repository handles indexing and searching legal document chunks
with specialized support for citations and legal terminology.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.domain.evidence.value_objects.chunk import Chunk
from app.infrastructure.persistence.opensearch.client import OpenSearchClient
from app.infrastructure.persistence.opensearch.repositories.base import (
    BaseBM25Repository,
    SearchResults
)
from app.infrastructure.persistence.opensearch.schemas import DOCUMENTS_INDEX
from app.shared.exceptions.domain_exceptions import RepositoryException


logger = logging.getLogger(__name__)


class OpenSearchDocumentRepository(BaseBM25Repository):
    """
    OpenSearch repository for legal document chunks.

    Provides BM25 search over document text with:
    - Legal terminology analysis
    - Citation matching
    - Case and document filtering
    - Chunk type filtering
    """

    def __init__(self, client: OpenSearchClient):
        """
        Initialize document repository.

        Args:
            client: OpenSearch client instance
        """
        super().__init__(client, DOCUMENTS_INDEX)

    async def index_document_chunks(
        self,
        document_id: UUID,
        case_id: UUID,
        chunks: List[Chunk]
    ) -> int:
        """
        Index all chunks from a document.

        Args:
            document_id: Document UUID
            case_id: Case UUID
            chunks: List of document chunks

        Returns:
            Number of chunks indexed

        Raises:
            RepositoryException: If indexing fails
        """
        try:
            documents = []

            for chunk in chunks:
                # Build document for indexing
                doc = {
                    "id": f"{document_id}_{chunk.position}",  # Unique chunk ID
                    "case_id": str(case_id),
                    "document_id": str(document_id),
                    "chunk_type": chunk.chunk_type.value,
                    "text": chunk.text,
                    "position": chunk.position,
                    "page_number": chunk.get_page_number(),
                    "metadata": chunk.metadata,
                    "created_at": datetime.utcnow().isoformat(),
                }

                documents.append(doc)

            # Bulk index
            indexed_count = await self.bulk_index(documents, refresh=False)

            logger.info(
                f"Indexed {indexed_count} chunks for document {document_id} "
                f"in case {case_id}"
            )

            return indexed_count

        except Exception as e:
            raise RepositoryException(
                f"Failed to index document chunks",
                context={
                    "document_id": str(document_id),
                    "case_id": str(case_id),
                    "chunk_count": len(chunks)
                },
                original_exception=e
            )

    async def search_documents(
        self,
        query: str,
        case_ids: Optional[List[UUID]] = None,
        document_ids: Optional[List[UUID]] = None,
        chunk_types: Optional[List[str]] = None,
        from_: int = 0,
        top_k: int = 10
    ) -> SearchResults:
        """
        Search document chunks using BM25.

        Args:
            query: Search query text
            case_ids: Optional list of case UUIDs to filter by
            document_ids: Optional list of document UUIDs to filter by
            chunk_types: Optional list of chunk types to filter by
            from_: Pagination offset
            top_k: Number of results to return

        Returns:
            SearchResults with matching chunks

        Raises:
            RepositoryException: If search fails
        """
        try:
            # Build filters
            filters: Dict[str, Any] = {}

            if case_ids:
                filters["case_id"] = [str(cid) for cid in case_ids]

            if document_ids:
                filters["document_id"] = [str(did) for did in document_ids]

            if chunk_types:
                filters["chunk_type"] = chunk_types

            # Search with multiple field variants
            results = await self.search(
                query=query,
                filters=filters,
                from_=from_,
                size=top_k,
                fields=["text^3", "text.shingles^2", "text.citation"],  # Boost main text
                highlight_fields=["text"]
            )

            logger.debug(
                f"Document search returned {len(results.results)} results "
                f"(total: {results.total}) in {results.took}ms"
            )

            return results

        except Exception as e:
            raise RepositoryException(
                f"Document search failed",
                context={"query": query, "case_ids": case_ids},
                original_exception=e
            )

    async def search_by_citation(
        self,
        citation: str,
        case_ids: Optional[List[UUID]] = None,
        top_k: int = 10
    ) -> SearchResults:
        """
        Search for documents containing a specific legal citation.

        Uses citation analyzer for precise matching of case law references,
        statute citations, etc.

        Args:
            citation: Citation to search for (e.g., "123 F.3d 456")
            case_ids: Optional list of case UUIDs to filter by
            top_k: Number of results to return

        Returns:
            SearchResults with matching chunks

        Raises:
            RepositoryException: If search fails
        """
        try:
            client = self._get_client()

            # Build citation match query
            must_clauses = [{
                "match": {
                    "text.citation": {
                        "query": citation,
                        "operator": "and",
                    }
                }
            }]

            # Add case filter
            filter_clauses = []
            if case_ids:
                filter_clauses.append({
                    "terms": {"case_id": [str(cid) for cid in case_ids]}
                })

            # Build query
            search_body = {
                "query": {
                    "bool": {
                        "must": must_clauses,
                        "filter": filter_clauses,
                    }
                },
                "size": top_k,
                "highlight": {
                    "fields": {"text": {}},
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"],
                }
            }

            # Execute search
            response = await client.search(
                index=self.index_name,
                body=search_body
            )

            # Parse results using base class helper
            hits = response.get('hits', {})
            from app.infrastructure.persistence.opensearch.repositories.base import SearchResult

            results = [
                SearchResult(
                    id=hit['_id'],
                    score=hit['_score'],
                    source=hit['_source'],
                    highlights=hit.get('highlight')
                )
                for hit in hits.get('hits', [])
            ]

            search_results = SearchResults(
                results=results,
                total=hits.get('total', {}).get('value', 0),
                took=response.get('took', 0),
                max_score=hits.get('max_score')
            )

            logger.debug(
                f"Citation search for '{citation}' returned {len(results)} results"
            )

            return search_results

        except Exception as e:
            raise RepositoryException(
                f"Citation search failed",
                context={"citation": citation},
                original_exception=e
            )

    async def delete_document(self, document_id: UUID) -> int:
        """
        Delete all chunks for a document.

        Args:
            document_id: Document UUID

        Returns:
            Number of chunks deleted

        Raises:
            RepositoryException: If deletion fails
        """
        try:
            query = {
                "term": {"document_id": str(document_id)}
            }

            deleted = await self.delete_by_query(query)

            logger.info(f"Deleted {deleted} chunks for document {document_id}")

            return deleted

        except Exception as e:
            raise RepositoryException(
                f"Failed to delete document chunks",
                context={"document_id": str(document_id)},
                original_exception=e
            )

    async def delete_case_documents(self, case_id: UUID) -> int:
        """
        Delete all document chunks for a case.

        Args:
            case_id: Case UUID

        Returns:
            Number of chunks deleted

        Raises:
            RepositoryException: If deletion fails
        """
        try:
            query = {
                "term": {"case_id": str(case_id)}
            }

            deleted = await self.delete_by_query(query)

            logger.info(f"Deleted {deleted} document chunks for case {case_id}")

            return deleted

        except Exception as e:
            raise RepositoryException(
                f"Failed to delete case documents",
                context={"case_id": str(case_id)},
                original_exception=e
            )

    async def get_document_chunk_count(self, document_id: UUID) -> int:
        """
        Get the number of indexed chunks for a document.

        Args:
            document_id: Document UUID

        Returns:
            Number of indexed chunks

        Raises:
            RepositoryException: If count fails
        """
        try:
            query = {
                "term": {"document_id": str(document_id)}
            }

            count = await self.count(query)

            return count

        except Exception as e:
            raise RepositoryException(
                f"Failed to count document chunks",
                context={"document_id": str(document_id)},
                original_exception=e
            )
