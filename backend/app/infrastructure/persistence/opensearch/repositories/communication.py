"""
Communication BM25 repository for OpenSearch.

This repository handles indexing and searching digital communications
with support for thread grouping, participant filtering, and temporal queries.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.domain.evidence.entities.communication import Communication
from app.infrastructure.persistence.opensearch.client import OpenSearchClient
from app.infrastructure.persistence.opensearch.repositories.base import (
    BaseBM25Repository,
    SearchResults,
    SearchResult
)
from app.infrastructure.persistence.opensearch.schemas import COMMUNICATIONS_INDEX
from app.shared.exceptions.domain_exceptions import RepositoryException


logger = logging.getLogger(__name__)


class OpenSearchCommunicationRepository(BaseBM25Repository):
    """
    OpenSearch repository for digital communications.

    Provides BM25 search over communications with:
    - Thread-based grouping
    - Participant filtering
    - Temporal range queries
    - Platform filtering
    """

    def __init__(self, client: OpenSearchClient):
        """
        Initialize communication repository.

        Args:
            client: OpenSearch client instance
        """
        super().__init__(client, COMMUNICATIONS_INDEX)

    async def index_communications(
        self,
        case_id: UUID,
        communications: List[Communication]
    ) -> int:
        """
        Index multiple communications.

        Args:
            case_id: Case UUID
            communications: List of communication entities

        Returns:
            Number of communications indexed

        Raises:
            RepositoryException: If indexing fails
        """
        try:
            documents = []

            for comm in communications:
                # Build document for indexing
                doc = {
                    "id": str(comm.id),
                    "case_id": str(case_id),
                    "thread_id": comm.thread_id,
                    "body": comm.body,
                    "sender": comm.sender.name or comm.sender.identifier,
                    "sender_identifier": comm.sender.identifier,
                    "participants": [p.identifier for p in comm.participants],
                    "participant_names": [
                        p.name for p in comm.participants if p.name
                    ],
                    "timestamp": comm.timestamp.isoformat(),
                    "platform": comm.platform.value,
                    "communication_type": comm.communication_type.value,
                    "device_id": comm.device_id,
                    "has_attachments": comm.has_attachments(),
                    "attachment_count": comm.get_attachment_count(),
                    "metadata": comm.metadata,
                    "created_at": comm.created_at.isoformat(),
                }

                documents.append(doc)

            # Bulk index
            indexed_count = await self.bulk_index(documents, refresh=False)

            logger.info(
                f"Indexed {indexed_count} communications for case {case_id}"
            )

            return indexed_count

        except Exception as e:
            raise RepositoryException(
                f"Failed to index communications",
                context={
                    "case_id": str(case_id),
                    "communication_count": len(communications)
                },
                original_exception=e
            )

    async def search_communications(
        self,
        query: str,
        case_ids: Optional[List[UUID]] = None,
        participants: Optional[List[str]] = None,
        platforms: Optional[List[str]] = None,
        from_: int = 0,
        top_k: int = 10
    ) -> SearchResults:
        """
        Search communications using BM25.

        Args:
            query: Search query text
            case_ids: Optional list of case UUIDs to filter by
            participants: Optional list of participant identifiers
            platforms: Optional list of platform names
            from_: Pagination offset
            top_k: Number of results to return

        Returns:
            SearchResults with matching communications

        Raises:
            RepositoryException: If search fails
        """
        try:
            # Build filters
            filters: Dict[str, Any] = {}

            if case_ids:
                filters["case_id"] = [str(cid) for cid in case_ids]

            if participants:
                # Will match any participant
                filters["participants"] = participants

            if platforms:
                filters["platform"] = platforms

            # Search body text and participant names
            results = await self.search(
                query=query,
                filters=filters,
                from_=from_,
                size=top_k,
                fields=["body^3", "participant_names^2", "sender"],
                highlight_fields=["body"]
            )

            logger.debug(
                f"Communication search returned {len(results.results)} results "
                f"(total: {results.total}) in {results.took}ms"
            )

            return results

        except Exception as e:
            raise RepositoryException(
                f"Communication search failed",
                context={"query": query},
                original_exception=e
            )

    async def search_threads(
        self,
        query: str,
        case_ids: Optional[List[UUID]] = None,
        participants: Optional[List[str]] = None,
        from_: int = 0,
        top_k: int = 10
    ) -> SearchResults:
        """
        Search communications and group by thread.

        Args:
            query: Search query text
            case_ids: Optional list of case UUIDs to filter by
            participants: Optional list of participant identifiers
            from_: Pagination offset
            top_k: Number of results to return

        Returns:
            SearchResults with matching communications

        Raises:
            RepositoryException: If search fails
        """
        try:
            client = self._get_client()

            # Build query
            must_clauses = [{
                "multi_match": {
                    "query": query,
                    "fields": ["body^3", "participant_names^2"],
                    "type": "best_fields",
                    "operator": "or",
                }
            }]

            # Build filters
            filter_clauses = []

            if case_ids:
                filter_clauses.append({
                    "terms": {"case_id": [str(cid) for cid in case_ids]}
                })

            if participants:
                filter_clauses.append({
                    "terms": {"participants": participants}
                })

            # Build search with collapse by thread_id
            search_body = {
                "query": {
                    "bool": {
                        "must": must_clauses,
                        "filter": filter_clauses,
                    }
                },
                "from": from_,
                "size": top_k,
                "collapse": {
                    "field": "thread_id",
                    "inner_hits": {
                        "name": "thread_messages",
                        "size": 5,  # Show up to 5 messages per thread
                        "sort": [{"timestamp": "desc"}]
                    }
                },
                "sort": [
                    "_score",
                    {"timestamp": "desc"}
                ]
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

            search_results = SearchResults(
                results=results,
                total=hits.get('total', {}).get('value', 0),
                took=response.get('took', 0),
                max_score=hits.get('max_score')
            )

            logger.debug(
                f"Thread search returned {len(results)} threads"
            )

            return search_results

        except Exception as e:
            raise RepositoryException(
                f"Thread search failed",
                context={"query": query},
                original_exception=e
            )

    async def search_by_timerange(
        self,
        start: datetime,
        end: datetime,
        case_ids: Optional[List[UUID]] = None,
        query: Optional[str] = None,
        from_: int = 0,
        top_k: int = 100
    ) -> SearchResults:
        """
        Search communications within a time range.

        Args:
            start: Start datetime (inclusive)
            end: End datetime (inclusive)
            case_ids: Optional list of case UUIDs to filter by
            query: Optional text query to further filter results
            from_: Pagination offset
            top_k: Number of results to return

        Returns:
            SearchResults with communications in time range

        Raises:
            RepositoryException: If search fails
        """
        try:
            client = self._get_client()

            # Build must clauses
            must_clauses = []
            if query:
                must_clauses.append({
                    "multi_match": {
                        "query": query,
                        "fields": ["body", "participant_names"],
                    }
                })

            # Build filters
            filter_clauses = [{
                "range": {
                    "timestamp": {
                        "gte": start.isoformat(),
                        "lte": end.isoformat(),
                    }
                }
            }]

            if case_ids:
                filter_clauses.append({
                    "terms": {"case_id": [str(cid) for cid in case_ids]}
                })

            # Build search body
            search_body = {
                "query": {
                    "bool": {
                        "must": must_clauses if must_clauses else [{"match_all": {}}],
                        "filter": filter_clauses,
                    }
                },
                "from": from_,
                "size": top_k,
                "sort": [{"timestamp": "asc"}]  # Sort by time
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
                    score=hit.get('_score', 0.0),
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
                f"Time range search returned {len(results)} results "
                f"from {start} to {end}"
            )

            return search_results

        except Exception as e:
            raise RepositoryException(
                f"Time range search failed",
                context={
                    "start": start.isoformat(),
                    "end": end.isoformat()
                },
                original_exception=e
            )

    async def delete_communication(self, communication_id: UUID) -> bool:
        """
        Delete a single communication.

        Args:
            communication_id: Communication UUID

        Returns:
            True if deleted successfully

        Raises:
            RepositoryException: If deletion fails
        """
        try:
            deleted = await self.delete_by_id([str(communication_id)])

            logger.info(f"Deleted communication {communication_id}")

            return deleted > 0

        except Exception as e:
            raise RepositoryException(
                f"Failed to delete communication",
                context={"communication_id": str(communication_id)},
                original_exception=e
            )

    async def delete_case_communications(self, case_id: UUID) -> int:
        """
        Delete all communications for a case.

        Args:
            case_id: Case UUID

        Returns:
            Number of communications deleted

        Raises:
            RepositoryException: If deletion fails
        """
        try:
            query = {
                "term": {"case_id": str(case_id)}
            }

            deleted = await self.delete_by_query(query)

            logger.info(f"Deleted {deleted} communications for case {case_id}")

            return deleted

        except Exception as e:
            raise RepositoryException(
                f"Failed to delete case communications",
                context={"case_id": str(case_id)},
                original_exception=e
            )

    async def get_thread_messages(
        self,
        thread_id: str,
        top_k: int = 100
    ) -> SearchResults:
        """
        Get all messages in a thread, sorted by time.

        Args:
            thread_id: Thread identifier
            top_k: Maximum number of messages to return

        Returns:
            SearchResults with thread messages

        Raises:
            RepositoryException: If query fails
        """
        try:
            client = self._get_client()

            # Match all messages in thread
            search_body = {
                "query": {
                    "term": {"thread_id": thread_id}
                },
                "size": top_k,
                "sort": [{"timestamp": "asc"}]
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
                    score=hit.get('_score', 0.0),
                    source=hit['_source'],
                    highlights=None
                )
                for hit in hits.get('hits', [])
            ]

            return SearchResults(
                results=results,
                total=hits.get('total', {}).get('value', 0),
                took=response.get('took', 0),
                max_score=None
            )

        except Exception as e:
            raise RepositoryException(
                f"Failed to get thread messages",
                context={"thread_id": thread_id},
                original_exception=e
            )
