"""
DualStoreWriter component for Haystack pipelines.

Writes documents to both Qdrant (dense vectors) and OpenSearch (BM25)
in a single operation with proper error handling and rollback support.
"""

import logging
from typing import List, Dict, Any, Optional, Literal
from uuid import UUID

from haystack import component, Document

from app.infrastructure.persistence.qdrant.repositories.document import QdrantDocumentRepository
from app.infrastructure.persistence.qdrant.repositories.transcript import QdrantTranscriptRepository
from app.infrastructure.persistence.qdrant.repositories.communication import QdrantCommunicationRepository
from app.infrastructure.persistence.opensearch.repositories.document import OpenSearchDocumentRepository
from app.infrastructure.persistence.opensearch.repositories.transcript import OpenSearchTranscriptRepository
from app.infrastructure.persistence.opensearch.repositories.communication import OpenSearchCommunicationRepository
from app.domain.evidence.value_objects.chunk import Chunk
from app.domain.evidence.entities.transcript import TranscriptSegment
from app.domain.evidence.entities.communication import Communication

logger = logging.getLogger(__name__)


EvidenceType = Literal["document", "transcript", "communication"]


@component
class DualStoreWriter:
    """
    Haystack component that writes documents to both Qdrant and OpenSearch.

    This component ensures that documents are indexed in both stores atomically,
    with proper error handling and rollback on failure.

    Features:
    - Atomic write to both stores (rollback on failure)
    - Support for documents, transcripts, and communications
    - Batch processing for efficiency
    - Detailed error reporting
    - Partial failure recovery

    Usage:
        >>> writer = DualStoreWriter(
        ...     evidence_type="document",
        ...     qdrant_document_repo=qdrant_doc_repo,
        ...     opensearch_document_repo=opensearch_doc_repo
        ... )
        >>> result = writer.run(
        ...     documents=haystack_docs,
        ...     case_id=case_uuid,
        ...     document_id=doc_uuid,
        ...     chunks=chunks,
        ...     embeddings={"summary": [...], "section": [...], "microblock": [...]},
        ... )
    """

    def __init__(
        self,
        evidence_type: EvidenceType,
        qdrant_document_repo: Optional[QdrantDocumentRepository] = None,
        qdrant_transcript_repo: Optional[QdrantTranscriptRepository] = None,
        qdrant_communication_repo: Optional[QdrantCommunicationRepository] = None,
        opensearch_document_repo: Optional[OpenSearchDocumentRepository] = None,
        opensearch_transcript_repo: Optional[OpenSearchTranscriptRepository] = None,
        opensearch_communication_repo: Optional[OpenSearchCommunicationRepository] = None,
    ):
        """
        Initialize the DualStoreWriter.

        Args:
            evidence_type: Type of evidence being indexed ("document", "transcript", "communication")
            qdrant_document_repo: Repository for Qdrant document operations
            qdrant_transcript_repo: Repository for Qdrant transcript operations
            qdrant_communication_repo: Repository for Qdrant communication operations
            opensearch_document_repo: Repository for OpenSearch document operations
            opensearch_transcript_repo: Repository for OpenSearch transcript operations
            opensearch_communication_repo: Repository for OpenSearch communication operations
        """
        self.evidence_type = evidence_type

        # Qdrant repositories
        self.qdrant_document_repo = qdrant_document_repo
        self.qdrant_transcript_repo = qdrant_transcript_repo
        self.qdrant_communication_repo = qdrant_communication_repo

        # OpenSearch repositories
        self.opensearch_document_repo = opensearch_document_repo
        self.opensearch_transcript_repo = opensearch_transcript_repo
        self.opensearch_communication_repo = opensearch_communication_repo

        # Validate that we have the required repositories for the evidence type
        if evidence_type == "document":
            if not qdrant_document_repo or not opensearch_document_repo:
                raise ValueError(
                    "Document repositories required for evidence_type='document'"
                )
        elif evidence_type == "transcript":
            if not qdrant_transcript_repo or not opensearch_transcript_repo:
                raise ValueError(
                    "Transcript repositories required for evidence_type='transcript'"
                )
        elif evidence_type == "communication":
            if not qdrant_communication_repo or not opensearch_communication_repo:
                raise ValueError(
                    "Communication repositories required for evidence_type='communication'"
                )
        else:
            raise ValueError(f"Invalid evidence_type: {evidence_type}")

        logger.info(f"Initialized DualStoreWriter for evidence_type={evidence_type}")

    @component.output_types(documents_written=int, success=bool, errors=List[str])
    async def run(
        self,
        documents: List[Document],
        case_id: UUID,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Write documents to both Qdrant and OpenSearch.

        Args:
            documents: List of Haystack Documents to index
            case_id: UUID of the case
            **kwargs: Additional parameters specific to evidence type
                For documents: document_id, chunks, embeddings
                For transcripts: transcript_id, segments, embeddings
                For communications: communications, embeddings

        Returns:
            Dictionary with:
                - documents_written: Number of documents successfully written
                - success: True if all writes succeeded
                - errors: List of error messages (empty if success)
        """
        errors = []
        documents_written = 0

        try:
            if self.evidence_type == "document":
                documents_written = await self._write_documents(
                    case_id=case_id,
                    **kwargs,
                )
            elif self.evidence_type == "transcript":
                documents_written = await self._write_transcripts(
                    case_id=case_id,
                    **kwargs,
                )
            elif self.evidence_type == "communication":
                documents_written = await self._write_communications(
                    case_id=case_id,
                    **kwargs,
                )

            logger.info(
                f"Successfully wrote {documents_written} {self.evidence_type} items "
                f"to both stores for case {case_id}"
            )

            return {
                "documents_written": documents_written,
                "success": True,
                "errors": [],
            }

        except Exception as e:
            error_msg = f"Failed to write {self.evidence_type} to dual stores: {e}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)

            return {
                "documents_written": 0,
                "success": False,
                "errors": errors,
            }

    async def _write_documents(
        self,
        case_id: UUID,
        document_id: UUID,
        chunks: List[Chunk],
        embeddings: Dict[str, List[List[float]]],
        sparse_vectors: Optional[List[Any]] = None,
    ) -> int:
        """
        Write document chunks to both Qdrant and OpenSearch.

        Args:
            case_id: Case UUID
            document_id: Document UUID
            chunks: List of Chunk value objects
            embeddings: Dictionary of embeddings by type (summary, section, microblock)
            sparse_vectors: Optional sparse vectors for BM25

        Returns:
            Number of chunks written

        Raises:
            Exception: If write fails to either store
        """
        # Write to Qdrant first (vector store)
        logger.info(f"Writing {len(chunks)} chunks to Qdrant for document {document_id}")
        qdrant_success = await self.qdrant_document_repo.index_document(
            document_id=document_id,
            case_id=case_id,
            chunks=chunks,
            embeddings=embeddings,
            sparse_vectors=sparse_vectors,
        )

        if not qdrant_success:
            raise RuntimeError("Failed to write to Qdrant")

        # Write to OpenSearch (BM25)
        logger.info(f"Writing {len(chunks)} chunks to OpenSearch for document {document_id}")
        try:
            opensearch_count = await self.opensearch_document_repo.index_document_chunks(
                document_id=document_id,
                case_id=case_id,
                chunks=chunks,
            )

            logger.info(f"Successfully wrote {opensearch_count} chunks to OpenSearch")

        except Exception as e:
            # Rollback Qdrant write
            logger.error(f"OpenSearch write failed, rolling back Qdrant write: {e}")
            try:
                await self.qdrant_document_repo.delete_document(document_id)
                logger.info(f"Successfully rolled back Qdrant write for document {document_id}")
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {rollback_error}")

            raise RuntimeError(f"Failed to write to OpenSearch: {e}") from e

        return len(chunks)

    async def _write_transcripts(
        self,
        case_id: UUID,
        transcript_id: UUID,
        segments: List[TranscriptSegment],
        embeddings: List[List[float]],
        sparse_vectors: Optional[List[Any]] = None,
    ) -> int:
        """
        Write transcript segments to both Qdrant and OpenSearch.

        Args:
            case_id: Case UUID
            transcript_id: Transcript UUID
            segments: List of TranscriptSegment entities
            embeddings: List of dense embeddings (one per segment)
            sparse_vectors: Optional sparse vectors for BM25

        Returns:
            Number of segments written

        Raises:
            Exception: If write fails to either store
        """
        # Write to Qdrant first
        logger.info(f"Writing {len(segments)} segments to Qdrant for transcript {transcript_id}")
        qdrant_success = await self.qdrant_transcript_repo.index_transcript(
            transcript_id=transcript_id,
            case_id=case_id,
            segments=segments,
            embeddings=embeddings,
            sparse_vectors=sparse_vectors,
        )

        if not qdrant_success:
            raise RuntimeError("Failed to write to Qdrant")

        # Write to OpenSearch
        logger.info(f"Writing {len(segments)} segments to OpenSearch for transcript {transcript_id}")
        try:
            opensearch_count = await self.opensearch_transcript_repo.index_transcript_segments(
                transcript_id=transcript_id,
                case_id=case_id,
                segments=segments,
            )

            logger.info(f"Successfully wrote {opensearch_count} segments to OpenSearch")

        except Exception as e:
            # Rollback Qdrant write
            logger.error(f"OpenSearch write failed, rolling back Qdrant write: {e}")
            try:
                await self.qdrant_transcript_repo.delete_transcript(transcript_id)
                logger.info(f"Successfully rolled back Qdrant write for transcript {transcript_id}")
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {rollback_error}")

            raise RuntimeError(f"Failed to write to OpenSearch: {e}") from e

        return len(segments)

    async def _write_communications(
        self,
        case_id: UUID,
        communications: List[Communication],
        embeddings: List[List[float]],
        sparse_vectors: Optional[List[Any]] = None,
    ) -> int:
        """
        Write communications to both Qdrant and OpenSearch.

        Args:
            case_id: Case UUID
            communications: List of Communication entities
            embeddings: List of dense embeddings (one per communication)
            sparse_vectors: Optional sparse vectors for BM25

        Returns:
            Number of communications written

        Raises:
            Exception: If write fails to either store
        """
        # Write to Qdrant first
        logger.info(f"Writing {len(communications)} communications to Qdrant for case {case_id}")
        qdrant_success = await self.qdrant_communication_repo.index_communications(
            case_id=case_id,
            communications=communications,
            embeddings=embeddings,
            sparse_vectors=sparse_vectors,
        )

        if not qdrant_success:
            raise RuntimeError("Failed to write to Qdrant")

        # Write to OpenSearch
        logger.info(f"Writing {len(communications)} communications to OpenSearch for case {case_id}")
        try:
            opensearch_count = await self.opensearch_communication_repo.index_communications(
                case_id=case_id,
                communications=communications,
            )

            logger.info(f"Successfully wrote {opensearch_count} communications to OpenSearch")

        except Exception as e:
            # Rollback Qdrant write
            logger.error(f"OpenSearch write failed, rolling back Qdrant write: {e}")
            try:
                await self.qdrant_communication_repo.delete_communications(case_id)
                logger.warning(
                    f"Rolled back all communications for case {case_id} "
                    f"(may affect other communications)"
                )
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {rollback_error}")

            raise RuntimeError(f"Failed to write to OpenSearch: {e}") from e

        return len(communications)
