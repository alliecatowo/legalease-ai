"""
Custom Haystack retrievers for hybrid search.

Provides retrievers that wrap Qdrant and OpenSearch repositories
for use in Haystack 2.x pipelines.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

from haystack import component, Document
from haystack.dataclasses import StreamingChunk

from app.infrastructure.persistence.qdrant.repositories.document import QdrantDocumentRepository
from app.infrastructure.persistence.qdrant.repositories.transcript import QdrantTranscriptRepository
from app.infrastructure.persistence.qdrant.repositories.communication import QdrantCommunicationRepository
from app.infrastructure.persistence.opensearch.repositories.document import OpenSearchDocumentRepository
from app.infrastructure.persistence.opensearch.repositories.transcript import OpenSearchTranscriptRepository
from app.infrastructure.persistence.opensearch.repositories.communication import OpenSearchCommunicationRepository
from app.infrastructure.persistence.opensearch.client import get_opensearch_client

logger = logging.getLogger(__name__)


@component
class QdrantHybridRetriever:
    """
    Haystack retriever for dense vector search across Qdrant repositories.

    Searches across document, transcript, and communication collections
    based on evidence_types filter.

    Features:
    - Multi-collection search (documents, transcripts, communications)
    - Dense embedding search
    - Metadata filtering (case_id, document_id, chunk_types)
    - Score threshold filtering
    """

    def __init__(
        self,
        default_top_k: int = 10,
        default_score_threshold: Optional[float] = None,
    ):
        """
        Initialize Qdrant hybrid retriever.

        Args:
            default_top_k: Default number of results to return
            default_score_threshold: Default minimum score threshold
        """
        self.default_top_k = default_top_k
        self.default_score_threshold = default_score_threshold

        # Initialize repositories
        self.document_repo = QdrantDocumentRepository()
        self.transcript_repo = QdrantTranscriptRepository()
        self.communication_repo = QdrantCommunicationRepository()

        logger.info(f"Initialized QdrantHybridRetriever (top_k={default_top_k})")

    @component.output_types(documents=List[Document])
    async def run(
        self,
        query_embedding: List[float],
        filters: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        evidence_types: Optional[List[str]] = None,
    ) -> Dict[str, List[Document]]:
        """
        Run dense vector search on Qdrant.

        Args:
            query_embedding: Dense embedding vector for the query
            filters: Metadata filters (case_ids, document_ids, chunk_types)
            top_k: Number of results to return
            score_threshold: Minimum score threshold
            evidence_types: Types of evidence to search (documents, transcripts, communications)

        Returns:
            Dict with 'documents' key containing search results
        """
        top_k = top_k or self.default_top_k
        score_threshold = score_threshold or self.default_score_threshold

        # Default to all evidence types
        if not evidence_types:
            evidence_types = ["documents", "transcripts", "communications"]

        # Extract filters
        case_ids = None
        document_ids = None
        chunk_types = None

        if filters:
            case_ids = filters.get("case_ids")
            document_ids = filters.get("document_ids")
            chunk_types = filters.get("chunk_types")

            # Convert string UUIDs to UUID objects
            if case_ids:
                case_ids = [UUID(cid) if isinstance(cid, str) else cid for cid in case_ids]
            if document_ids:
                document_ids = [UUID(did) if isinstance(did, str) else did for did in document_ids]

        # Build query embeddings dict for hierarchical search
        query_embeddings = {
            "summary": query_embedding,
            "section": query_embedding,
            "microblock": query_embedding,
        }

        all_results = []

        # Search documents
        if "documents" in evidence_types:
            try:
                doc_results = await self.document_repo.search_documents(
                    query_embeddings=query_embeddings,
                    case_ids=case_ids,
                    document_ids=document_ids,
                    chunk_types=chunk_types,
                    top_k=top_k * 2,  # Get more for deduplication
                    score_threshold=score_threshold,
                )
                all_results.extend(doc_results)
                logger.info(f"Qdrant document search returned {len(doc_results)} results")
            except Exception as e:
                logger.error(f"Error searching documents in Qdrant: {e}", exc_info=True)

        # Search transcripts
        if "transcripts" in evidence_types:
            try:
                transcript_results = await self.transcript_repo.search_transcripts(
                    query_embeddings=query_embeddings,
                    case_ids=case_ids,
                    document_ids=document_ids,
                    top_k=top_k * 2,
                    score_threshold=score_threshold,
                )
                all_results.extend(transcript_results)
                logger.info(f"Qdrant transcript search returned {len(transcript_results)} results")
            except Exception as e:
                logger.error(f"Error searching transcripts in Qdrant: {e}", exc_info=True)

        # Search communications
        if "communications" in evidence_types:
            try:
                comm_results = await self.communication_repo.search_communications(
                    query_embeddings=query_embeddings,
                    case_ids=case_ids,
                    top_k=top_k * 2,
                    score_threshold=score_threshold,
                )
                all_results.extend(comm_results)
                logger.info(f"Qdrant communication search returned {len(comm_results)} results")
            except Exception as e:
                logger.error(f"Error searching communications in Qdrant: {e}", exc_info=True)

        # Convert to Haystack Documents
        documents = self._convert_to_haystack_documents(all_results, source="qdrant")

        # Sort by score descending
        documents.sort(key=lambda d: d.score or 0.0, reverse=True)

        # Limit to top_k
        documents = documents[:top_k]

        logger.info(f"QdrantHybridRetriever returned {len(documents)} documents")

        return {"documents": documents}

    def _convert_to_haystack_documents(
        self,
        results: List[Dict[str, Any]],
        source: str,
    ) -> List[Document]:
        """
        Convert search results to Haystack Document objects.

        Args:
            results: Raw search results from repositories
            source: Source of results (qdrant or opensearch)

        Returns:
            List of Haystack Document objects
        """
        documents = []

        for result in results:
            payload = result.get("payload", {})

            # Create Haystack Document
            doc = Document(
                id=str(result.get("id")),
                content=payload.get("text", ""),
                score=result.get("score", 0.0),
                meta={
                    "source": source,
                    "case_id": payload.get("case_id"),
                    "document_id": payload.get("document_id"),
                    "chunk_type": payload.get("chunk_type"),
                    "position": payload.get("position"),
                    "page_number": payload.get("page_number"),
                    "bboxes": payload.get("bboxes", []),
                    **payload,  # Include all other metadata
                },
            )
            documents.append(doc)

        return documents


@component
class OpenSearchHybridRetriever:
    """
    Haystack retriever for BM25 keyword search across OpenSearch repositories.

    Searches across document, transcript, and communication indexes
    based on evidence_types filter.

    Features:
    - Multi-index search (documents, transcripts, communications)
    - BM25 keyword search
    - Legal terminology analysis
    - Citation matching
    - Metadata filtering
    """

    def __init__(
        self,
        default_top_k: int = 10,
    ):
        """
        Initialize OpenSearch hybrid retriever.

        Args:
            default_top_k: Default number of results to return
        """
        self.default_top_k = default_top_k

        # Initialize repositories
        opensearch_client = get_opensearch_client()
        self.document_repo = OpenSearchDocumentRepository(opensearch_client)
        self.transcript_repo = OpenSearchTranscriptRepository(opensearch_client)
        self.communication_repo = OpenSearchCommunicationRepository(opensearch_client)

        logger.info(f"Initialized OpenSearchHybridRetriever (top_k={default_top_k})")

    @component.output_types(documents=List[Document])
    async def run(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None,
        evidence_types: Optional[List[str]] = None,
    ) -> Dict[str, List[Document]]:
        """
        Run BM25 keyword search on OpenSearch.

        Args:
            query: Search query string
            filters: Metadata filters (case_ids, document_ids, chunk_types)
            top_k: Number of results to return
            evidence_types: Types of evidence to search (documents, transcripts, communications)

        Returns:
            Dict with 'documents' key containing search results
        """
        top_k = top_k or self.default_top_k

        # Default to all evidence types
        if not evidence_types:
            evidence_types = ["documents", "transcripts", "communications"]

        # Extract filters
        case_ids = None
        document_ids = None
        chunk_types = None

        if filters:
            case_ids = filters.get("case_ids")
            document_ids = filters.get("document_ids")
            chunk_types = filters.get("chunk_types")

            # Convert string UUIDs to UUID objects
            if case_ids:
                case_ids = [UUID(cid) if isinstance(cid, str) else cid for cid in case_ids]
            if document_ids:
                document_ids = [UUID(did) if isinstance(did, str) else did for did in document_ids]

        all_results = []

        # Search documents
        if "documents" in evidence_types:
            try:
                doc_results = await self.document_repo.search_documents(
                    query=query,
                    case_ids=case_ids,
                    document_ids=document_ids,
                    chunk_types=chunk_types,
                    from_=0,
                    top_k=top_k * 2,  # Get more for deduplication
                )
                # Convert SearchResults to list of dicts
                for result in doc_results.results:
                    all_results.append({
                        "id": result.id,
                        "score": result.score,
                        "source": result.source,
                        "highlights": result.highlights,
                    })
                logger.info(f"OpenSearch document search returned {len(doc_results.results)} results")
            except Exception as e:
                logger.error(f"Error searching documents in OpenSearch: {e}", exc_info=True)

        # Search transcripts
        if "transcripts" in evidence_types:
            try:
                transcript_results = await self.transcript_repo.search_transcripts(
                    query=query,
                    case_ids=case_ids,
                    from_=0,
                    top_k=top_k * 2,
                )
                for result in transcript_results.results:
                    all_results.append({
                        "id": result.id,
                        "score": result.score,
                        "source": result.source,
                        "highlights": result.highlights,
                    })
                logger.info(f"OpenSearch transcript search returned {len(transcript_results.results)} results")
            except Exception as e:
                logger.error(f"Error searching transcripts in OpenSearch: {e}", exc_info=True)

        # Search communications
        if "communications" in evidence_types:
            try:
                comm_results = await self.communication_repo.search_communications(
                    query=query,
                    case_ids=case_ids,
                    from_=0,
                    top_k=top_k * 2,
                )
                for result in comm_results.results:
                    all_results.append({
                        "id": result.id,
                        "score": result.score,
                        "source": result.source,
                        "highlights": result.highlights,
                    })
                logger.info(f"OpenSearch communication search returned {len(comm_results.results)} results")
            except Exception as e:
                logger.error(f"Error searching communications in OpenSearch: {e}", exc_info=True)

        # Convert to Haystack Documents
        documents = self._convert_to_haystack_documents(all_results, source="opensearch")

        # Sort by score descending
        documents.sort(key=lambda d: d.score or 0.0, reverse=True)

        # Limit to top_k
        documents = documents[:top_k]

        logger.info(f"OpenSearchHybridRetriever returned {len(documents)} documents")

        return {"documents": documents}

    def _convert_to_haystack_documents(
        self,
        results: List[Dict[str, Any]],
        source: str,
    ) -> List[Document]:
        """
        Convert search results to Haystack Document objects.

        Args:
            results: Raw search results from repositories
            source: Source of results (opensearch)

        Returns:
            List of Haystack Document objects
        """
        documents = []

        for result in results:
            result_source = result.get("source", {})

            # Create Haystack Document
            doc = Document(
                id=str(result.get("id")),
                content=result_source.get("text", ""),
                score=result.get("score", 0.0),
                meta={
                    "source": source,
                    "case_id": result_source.get("case_id"),
                    "document_id": result_source.get("document_id"),
                    "chunk_type": result_source.get("chunk_type"),
                    "position": result_source.get("position"),
                    "page_number": result_source.get("page_number"),
                    "highlights": result.get("highlights", {}),
                    **result_source,  # Include all other metadata
                },
            )
            documents.append(doc)

        return documents
