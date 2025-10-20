"""
Finding BM25 repository for OpenSearch.

This repository handles indexing and searching research findings
with support for type, confidence, and tag filtering.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.domain.research.entities.finding import Finding
from app.infrastructure.persistence.opensearch.client import OpenSearchClient
from app.infrastructure.persistence.opensearch.repositories.base import (
    BaseBM25Repository,
    SearchResults,
    SearchResult
)
from app.infrastructure.persistence.opensearch.schemas import FINDINGS_INDEX
from app.shared.exceptions.domain_exceptions import RepositoryException


logger = logging.getLogger(__name__)


class OpenSearchFindingRepository(BaseBM25Repository):
    """
    OpenSearch repository for research findings.

    Provides BM25 search over findings with:
    - Type filtering (fact, pattern, anomaly, etc.)
    - Confidence-based filtering
    - Relevance scoring
    - Tag-based organization
    """

    def __init__(self, client: OpenSearchClient):
        """
        Initialize finding repository.

        Args:
            client: OpenSearch client instance
        """
        super().__init__(client, FINDINGS_INDEX)

    async def index_findings(
        self,
        findings: List[Finding]
    ) -> int:
        """
        Index multiple findings.

        Args:
            findings: List of finding entities

        Returns:
            Number of findings indexed

        Raises:
            RepositoryException: If indexing fails
        """
        try:
            documents = []

            for finding in findings:
                # Build document for indexing
                doc = {
                    "id": str(finding.id),
                    "research_run_id": str(finding.research_run_id),
                    "finding_type": finding.finding_type.value,
                    "text": finding.text,
                    "entities": [str(eid) for eid in finding.entities],
                    "citations": [str(cid) for cid in finding.citations],
                    "confidence": finding.confidence,
                    "relevance": finding.relevance,
                    "tags": finding.tags,
                    "metadata": finding.metadata,
                    "created_at": datetime.utcnow().isoformat(),
                }

                documents.append(doc)

            # Bulk index
            indexed_count = await self.bulk_index(documents, refresh=False)

            logger.info(f"Indexed {indexed_count} findings")

            return indexed_count

        except Exception as e:
            raise RepositoryException(
                f"Failed to index findings",
                context={"finding_count": len(findings)},
                original_exception=e
            )

    async def search_findings(
        self,
        query: str,
        research_run_ids: Optional[List[UUID]] = None,
        finding_types: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        min_confidence: Optional[float] = None,
        min_relevance: Optional[float] = None,
        from_: int = 0,
        top_k: int = 10
    ) -> SearchResults:
        """
        Search findings using BM25.

        Args:
            query: Search query text
            research_run_ids: Optional list of research run UUIDs
            finding_types: Optional list of finding types to filter by
            tags: Optional list of tags to filter by
            min_confidence: Minimum confidence score (0.0-1.0)
            min_relevance: Minimum relevance score (0.0-1.0)
            from_: Pagination offset
            top_k: Number of results to return

        Returns:
            SearchResults with matching findings

        Raises:
            RepositoryException: If search fails
        """
        try:
            client = self._get_client()

            # Build query
            must_clauses = [{
                "multi_match": {
                    "query": query,
                    "fields": ["text^3", "tags^2"],
                    "type": "best_fields",
                    "operator": "or",
                }
            }]

            # Build filters
            filter_clauses = []

            if research_run_ids:
                filter_clauses.append({
                    "terms": {"research_run_id": [str(rid) for rid in research_run_ids]}
                })

            if finding_types:
                filter_clauses.append({
                    "terms": {"finding_type": finding_types}
                })

            if tags:
                filter_clauses.append({
                    "terms": {"tags": tags}
                })

            if min_confidence is not None:
                filter_clauses.append({
                    "range": {"confidence": {"gte": min_confidence}}
                })

            if min_relevance is not None:
                filter_clauses.append({
                    "range": {"relevance": {"gte": min_relevance}}
                })

            # Build search body
            search_body = {
                "query": {
                    "bool": {
                        "must": must_clauses,
                        "filter": filter_clauses,
                    }
                },
                "from": from_,
                "size": top_k,
                "highlight": {
                    "fields": {"text": {}},
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"],
                },
                "sort": [
                    "_score",
                    {"confidence": "desc"},  # Secondary sort by confidence
                    {"relevance": "desc"}    # Tertiary sort by relevance
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
                f"Finding search returned {len(results)} results "
                f"(total: {search_results.total}) in {search_results.took}ms"
            )

            return search_results

        except Exception as e:
            raise RepositoryException(
                f"Finding search failed",
                context={"query": query},
                original_exception=e
            )

    async def search_by_tags(
        self,
        tags: List[str],
        match_all: bool = True,
        from_: int = 0,
        top_k: int = 50
    ) -> SearchResults:
        """
        Search findings by tags.

        Args:
            tags: List of tags to search for
            match_all: If True, require all tags; if False, require any tag
            from_: Pagination offset
            top_k: Number of results to return

        Returns:
            SearchResults with matching findings

        Raises:
            RepositoryException: If search fails
        """
        try:
            client = self._get_client()

            # Build tag query
            if match_all:
                # Must have all tags
                filter_clauses = [
                    {"term": {"tags": tag}} for tag in tags
                ]
                query_clause = {
                    "bool": {
                        "filter": filter_clauses
                    }
                }
            else:
                # Must have at least one tag
                query_clause = {
                    "terms": {"tags": tags}
                }

            # Build search body
            search_body = {
                "query": query_clause,
                "from": from_,
                "size": top_k,
                "sort": [
                    {"confidence": "desc"},
                    {"relevance": "desc"}
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
                    score=hit.get('_score', 0.0),
                    source=hit['_source'],
                    highlights=None
                )
                for hit in hits.get('hits', [])
            ]

            search_results = SearchResults(
                results=results,
                total=hits.get('total', {}).get('value', 0),
                took=response.get('took', 0),
                max_score=None
            )

            logger.debug(
                f"Tag search for {tags} returned {len(results)} results"
            )

            return search_results

        except Exception as e:
            raise RepositoryException(
                f"Tag search failed",
                context={"tags": tags, "match_all": match_all},
                original_exception=e
            )

    async def delete_finding(self, finding_id: UUID) -> bool:
        """
        Delete a single finding.

        Args:
            finding_id: Finding UUID

        Returns:
            True if deleted successfully

        Raises:
            RepositoryException: If deletion fails
        """
        try:
            deleted = await self.delete_by_id([str(finding_id)])

            logger.info(f"Deleted finding {finding_id}")

            return deleted > 0

        except Exception as e:
            raise RepositoryException(
                f"Failed to delete finding",
                context={"finding_id": str(finding_id)},
                original_exception=e
            )

    async def delete_research_findings(self, research_run_id: UUID) -> int:
        """
        Delete all findings for a research run.

        Args:
            research_run_id: Research run UUID

        Returns:
            Number of findings deleted

        Raises:
            RepositoryException: If deletion fails
        """
        try:
            query = {
                "term": {"research_run_id": str(research_run_id)}
            }

            deleted = await self.delete_by_query(query)

            logger.info(f"Deleted {deleted} findings for research run {research_run_id}")

            return deleted

        except Exception as e:
            raise RepositoryException(
                f"Failed to delete research findings",
                context={"research_run_id": str(research_run_id)},
                original_exception=e
            )

    async def get_high_confidence_findings(
        self,
        research_run_id: UUID,
        min_confidence: float = 0.8,
        top_k: int = 50
    ) -> SearchResults:
        """
        Get high-confidence findings for a research run.

        Args:
            research_run_id: Research run UUID
            min_confidence: Minimum confidence threshold
            top_k: Maximum number of findings to return

        Returns:
            SearchResults with high-confidence findings

        Raises:
            RepositoryException: If query fails
        """
        try:
            client = self._get_client()

            # Match high-confidence findings
            search_body = {
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"research_run_id": str(research_run_id)}},
                            {"range": {"confidence": {"gte": min_confidence}}},
                        ]
                    }
                },
                "size": top_k,
                "sort": [
                    {"confidence": "desc"},
                    {"relevance": "desc"}
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
                f"Failed to get high-confidence findings",
                context={
                    "research_run_id": str(research_run_id),
                    "min_confidence": min_confidence
                },
                original_exception=e
            )
