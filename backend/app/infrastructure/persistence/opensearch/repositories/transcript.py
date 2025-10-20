"""
Transcript BM25 repository for OpenSearch.

This repository handles indexing and searching transcript segments
with support for speaker filtering, timecode ranges, and exact quote matching.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

from app.domain.evidence.entities.transcript import TranscriptSegment
from app.infrastructure.persistence.opensearch.client import OpenSearchClient
from app.infrastructure.persistence.opensearch.repositories.base import (
    BaseBM25Repository,
    SearchResults,
    SearchResult
)
from app.infrastructure.persistence.opensearch.schemas import TRANSCRIPTS_INDEX
from app.shared.exceptions.domain_exceptions import RepositoryException


logger = logging.getLogger(__name__)


class OpenSearchTranscriptRepository(BaseBM25Repository):
    """
    OpenSearch repository for transcript segments.

    Provides BM25 search over transcript text with:
    - Speaker filtering
    - Timecode range queries
    - Exact quote matching
    - Confidence-based filtering
    """

    def __init__(self, client: OpenSearchClient):
        """
        Initialize transcript repository.

        Args:
            client: OpenSearch client instance
        """
        super().__init__(client, TRANSCRIPTS_INDEX)

    async def index_transcript_segments(
        self,
        transcript_id: UUID,
        case_id: UUID,
        segments: List[TranscriptSegment]
    ) -> int:
        """
        Index all segments from a transcript.

        Args:
            transcript_id: Transcript UUID
            case_id: Case UUID
            segments: List of transcript segments

        Returns:
            Number of segments indexed

        Raises:
            RepositoryException: If indexing fails
        """
        try:
            documents = []

            for idx, segment in enumerate(segments):
                # Build document for indexing
                doc = {
                    "id": f"{transcript_id}_{segment.id}",  # Unique segment ID
                    "case_id": str(case_id),
                    "transcript_id": str(transcript_id),
                    "segment_id": segment.id,
                    "text": segment.text,
                    "speaker": segment.speaker.name if segment.speaker else None,
                    "speaker_id": segment.speaker.id if segment.speaker else None,
                    "timecode_start": segment.start,
                    "timecode_end": segment.end,
                    "duration": segment.duration,
                    "confidence": segment.confidence,
                    "position": idx,
                    "metadata": {
                        "segment_type": segment.segment_type.value,
                        "words": segment.words,
                    },
                    "created_at": datetime.utcnow().isoformat(),
                }

                documents.append(doc)

            # Bulk index
            indexed_count = await self.bulk_index(documents, refresh=False)

            logger.info(
                f"Indexed {indexed_count} segments for transcript {transcript_id} "
                f"in case {case_id}"
            )

            return indexed_count

        except Exception as e:
            raise RepositoryException(
                f"Failed to index transcript segments",
                context={
                    "transcript_id": str(transcript_id),
                    "case_id": str(case_id),
                    "segment_count": len(segments)
                },
                original_exception=e
            )

    async def search_transcripts(
        self,
        query: str,
        case_ids: Optional[List[UUID]] = None,
        transcript_ids: Optional[List[UUID]] = None,
        speaker: Optional[str] = None,
        time_range: Optional[Tuple[float, float]] = None,
        from_: int = 0,
        top_k: int = 10
    ) -> SearchResults:
        """
        Search transcript segments using BM25.

        Args:
            query: Search query text
            case_ids: Optional list of case UUIDs to filter by
            transcript_ids: Optional list of transcript UUIDs to filter by
            speaker: Optional speaker name/ID to filter by
            time_range: Optional (start, end) timecode range in seconds
            from_: Pagination offset
            top_k: Number of results to return

        Returns:
            SearchResults with matching segments

        Raises:
            RepositoryException: If search fails
        """
        try:
            client = self._get_client()

            # Build query
            must_clauses = [{
                "multi_match": {
                    "query": query,
                    "fields": ["text^3", "text.shingles^2"],
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

            if transcript_ids:
                filter_clauses.append({
                    "terms": {"transcript_id": [str(tid) for tid in transcript_ids]}
                })

            if speaker:
                # Match speaker name or ID
                filter_clauses.append({
                    "bool": {
                        "should": [
                            {"match": {"speaker": speaker}},
                            {"term": {"speaker_id": speaker}},
                        ]
                    }
                })

            if time_range:
                start, end = time_range
                # Match segments that overlap with the time range
                filter_clauses.append({
                    "bool": {
                        "must": [
                            {"range": {"timecode_end": {"gte": start}}},
                            {"range": {"timecode_start": {"lte": end}}},
                        ]
                    }
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
                    {"timecode_start": "asc"}  # Secondary sort by time
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
                f"Transcript search returned {len(results)} results "
                f"(total: {search_results.total}) in {search_results.took}ms"
            )

            return search_results

        except Exception as e:
            raise RepositoryException(
                f"Transcript search failed",
                context={"query": query},
                original_exception=e
            )

    async def search_quotes(
        self,
        phrase: str,
        case_ids: Optional[List[UUID]] = None,
        exact: bool = True,
        top_k: int = 10
    ) -> SearchResults:
        """
        Search for exact or near-exact quotes in transcripts.

        Args:
            phrase: Phrase to search for
            case_ids: Optional list of case UUIDs to filter by
            exact: If True, use exact match; otherwise use phrase match
            top_k: Number of results to return

        Returns:
            SearchResults with matching segments

        Raises:
            RepositoryException: If search fails
        """
        try:
            client = self._get_client()

            # Build query based on exact flag
            if exact:
                # Use term query on exact field for perfect match
                must_clauses = [{
                    "match_phrase": {
                        "text": {
                            "query": phrase,
                            "slop": 0,  # No word gaps allowed
                        }
                    }
                }]
            else:
                # Use phrase match with some slop
                must_clauses = [{
                    "match_phrase": {
                        "text": {
                            "query": phrase,
                            "slop": 2,  # Allow 2 word gaps
                        }
                    }
                }]

            # Build filters
            filter_clauses = []
            if case_ids:
                filter_clauses.append({
                    "terms": {"case_id": [str(cid) for cid in case_ids]}
                })

            # Build search body
            search_body = {
                "query": {
                    "bool": {
                        "must": must_clauses,
                        "filter": filter_clauses,
                    }
                },
                "size": top_k,
                "highlight": {
                    "fields": {
                        "text": {
                            "type": "plain",
                            "fragment_size": 200,
                        }
                    },
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"],
                },
                "sort": [
                    "_score",
                    {"timecode_start": "asc"}
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
                f"Quote search for '{phrase}' returned {len(results)} results"
            )

            return search_results

        except Exception as e:
            raise RepositoryException(
                f"Quote search failed",
                context={"phrase": phrase, "exact": exact},
                original_exception=e
            )

    async def delete_transcript(self, transcript_id: UUID) -> int:
        """
        Delete all segments for a transcript.

        Args:
            transcript_id: Transcript UUID

        Returns:
            Number of segments deleted

        Raises:
            RepositoryException: If deletion fails
        """
        try:
            query = {
                "term": {"transcript_id": str(transcript_id)}
            }

            deleted = await self.delete_by_query(query)

            logger.info(f"Deleted {deleted} segments for transcript {transcript_id}")

            return deleted

        except Exception as e:
            raise RepositoryException(
                f"Failed to delete transcript segments",
                context={"transcript_id": str(transcript_id)},
                original_exception=e
            )

    async def get_segments_by_speaker(
        self,
        transcript_id: UUID,
        speaker_id: str,
        top_k: int = 100
    ) -> SearchResults:
        """
        Get all segments spoken by a specific speaker.

        Args:
            transcript_id: Transcript UUID
            speaker_id: Speaker identifier
            top_k: Maximum number of segments to return

        Returns:
            SearchResults with segments from speaker

        Raises:
            RepositoryException: If query fails
        """
        try:
            client = self._get_client()

            # Match all segments from this speaker
            search_body = {
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"transcript_id": str(transcript_id)}},
                            {"term": {"speaker_id": speaker_id}},
                        ]
                    }
                },
                "size": top_k,
                "sort": [{"timecode_start": "asc"}]
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
                f"Failed to get segments by speaker",
                context={"transcript_id": str(transcript_id), "speaker_id": speaker_id},
                original_exception=e
            )
