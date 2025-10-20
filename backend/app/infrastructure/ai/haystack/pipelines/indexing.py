"""
Haystack indexing pipelines for legal evidence.

This module contains complete indexing pipelines for:
- Documents (PDF, DOCX, DOC, TXT)
- Transcripts (audio/video transcriptions with speaker diarization)
- Communications (Cellebrite exports: messages, emails, chats)

All pipelines support dual-store architecture:
- Qdrant for dense vector search
- OpenSearch for BM25 sparse search
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

from haystack import Pipeline

from app.infrastructure.ai.haystack.components.docling_converter import DoclingDocumentConverter
from app.infrastructure.ai.haystack.components.document_cleaner import LegalDocumentCleaner
from app.infrastructure.ai.haystack.components.embedders import (
    FastEmbedDocumentEmbedder,
    SparseEmbedder,
)
from app.infrastructure.ai.haystack.components.transcript_converter import (
    TranscriptSegmentConverter,
    SpeakerAwareChunker,
)
from app.infrastructure.ai.haystack.components.communication_converter import (
    CommunicationConverter,
    ThreadGrouper,
)
from app.infrastructure.ai.haystack.stores.dual_store_writer import DualStoreWriter
from app.domain.evidence.value_objects.chunk import Chunk, ChunkType
from app.domain.evidence.entities.transcript import TranscriptSegment
from app.domain.evidence.entities.communication import Communication

logger = logging.getLogger(__name__)


class DocumentIndexingPipeline:
    """
    Pipeline for indexing legal documents.

    Flow:
        File Path → DoclingConverter → Cleaner → [Chunker Placeholder]
        → Dense Embedder → Sparse Embedder → DualStoreWriter

    Features:
    - Multi-format support (PDF, DOCX, DOC, TXT)
    - OCR for scanned documents
    - Document cleaning and normalization
    - Hierarchical embeddings (summary, section, microblock)
    - Dual-store indexing (Qdrant + OpenSearch)

    Usage:
        >>> pipeline = DocumentIndexingPipeline(
        ...     dual_store_writer=writer,
        ...     use_ocr=True
        ... )
        >>> result = await pipeline.run(
        ...     file_path="/path/to/document.pdf",
        ...     case_id=case_uuid,
        ...     document_id=doc_uuid,
        ...     chunks=chunks
        ... )
    """

    def __init__(
        self,
        dual_store_writer: DualStoreWriter,
        use_ocr: bool = True,
        model_name: str = "BAAI/bge-small-en-v1.5",
        batch_size: int = 100,
    ):
        """
        Initialize the document indexing pipeline.

        Args:
            dual_store_writer: DualStoreWriter component for Qdrant + OpenSearch
            use_ocr: Whether to use OCR for scanned documents
            model_name: FastEmbed model name
            batch_size: Batch size for embedding generation
        """
        self.dual_store_writer = dual_store_writer

        # Initialize components
        self.converter = DoclingDocumentConverter(use_ocr=use_ocr)
        self.cleaner = LegalDocumentCleaner()

        # We need 3 separate embedders for hierarchical embeddings
        self.embedder_summary = FastEmbedDocumentEmbedder(
            model_name=model_name,
            batch_size=batch_size,
            prefix="summary: ",
        )
        self.embedder_section = FastEmbedDocumentEmbedder(
            model_name=model_name,
            batch_size=batch_size,
            prefix="passage: ",
        )
        self.embedder_microblock = FastEmbedDocumentEmbedder(
            model_name=model_name,
            batch_size=batch_size,
            prefix="passage: ",
        )

        self.sparse_embedder = SparseEmbedder()

        logger.info(
            f"Initialized DocumentIndexingPipeline "
            f"(OCR={use_ocr}, model={model_name})"
        )

    async def run(
        self,
        file_path: str,
        case_id: UUID,
        document_id: UUID,
        chunks: List[Chunk],
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Index a document.

        Args:
            file_path: Path to document file
            case_id: Case UUID
            document_id: Document UUID
            chunks: List of Chunk value objects (pre-chunked)
            meta: Optional metadata

        Returns:
            Dictionary with:
                - success: Whether indexing succeeded
                - chunks_indexed: Number of chunks indexed
                - errors: List of error messages
        """
        try:
            logger.info(f"Indexing document {document_id} from {file_path}")

            # Step 1: Convert document
            logger.debug("Step 1: Converting document with Docling")
            converter_result = self.converter.run_from_path(
                file_path=file_path,
                meta={"case_id": str(case_id), "document_id": str(document_id)},
            )
            documents = converter_result["documents"]

            if not documents:
                raise ValueError("Document conversion produced no results")

            # Step 2: Clean document
            logger.debug("Step 2: Cleaning document")
            cleaner_result = self.cleaner.run(documents=documents)
            cleaned_docs = cleaner_result["documents"]

            if not cleaned_docs:
                raise ValueError("Document cleaning produced no results")

            # Step 3: Prepare chunks for embedding
            # NOTE: In a full implementation, we'd use a proper LegalChunker here
            # For now, we use the provided chunks
            logger.debug(f"Step 3: Using {len(chunks)} pre-chunked segments")

            chunk_texts = [chunk.text for chunk in chunks]

            # Step 4: Generate hierarchical embeddings
            logger.debug("Step 4: Generating hierarchical embeddings")

            # For simplicity, we'll use the same chunk texts for all levels
            # In production, you'd generate different granularities
            from haystack import Document as HaystackDoc
            haystack_chunks = [HaystackDoc(content=text) for text in chunk_texts]

            # Summary-level (broader context)
            summary_result = self.embedder_summary.run(documents=haystack_chunks)
            summary_embeddings = summary_result["embeddings"]

            # Section-level (medium granularity)
            section_result = self.embedder_section.run(documents=haystack_chunks)
            section_embeddings = section_result["embeddings"]

            # Microblock-level (fine-grained)
            microblock_result = self.embedder_microblock.run(documents=haystack_chunks)
            microblock_embeddings = microblock_result["embeddings"]

            embeddings = {
                "summary": summary_embeddings,
                "section": section_embeddings,
                "microblock": microblock_embeddings,
            }

            # Step 5: Generate sparse vectors (placeholder)
            logger.debug("Step 5: Generating sparse vectors")
            sparse_result = self.sparse_embedder.run(documents=haystack_chunks)
            sparse_vectors = sparse_result["sparse_vectors"]

            # Step 6: Write to dual stores
            logger.debug("Step 6: Writing to Qdrant and OpenSearch")
            write_result = await self.dual_store_writer.run(
                documents=haystack_chunks,
                case_id=case_id,
                document_id=document_id,
                chunks=chunks,
                embeddings=embeddings,
                sparse_vectors=sparse_vectors,
            )

            if not write_result["success"]:
                raise RuntimeError(
                    f"Dual store write failed: {write_result.get('errors', [])}"
                )

            logger.info(
                f"Successfully indexed {write_result['documents_written']} chunks "
                f"for document {document_id}"
            )

            return {
                "success": True,
                "chunks_indexed": write_result["documents_written"],
                "errors": [],
            }

        except Exception as e:
            error_msg = f"Document indexing failed: {e}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "chunks_indexed": 0,
                "errors": [error_msg],
            }


class TranscriptIndexingPipeline:
    """
    Pipeline for indexing transcript segments.

    Flow:
        TranscriptSegments → Converter → SpeakerChunker
        → Dense Embedder → Sparse Embedder → DualStoreWriter

    Features:
    - Speaker-aware chunking
    - Temporal metadata preservation
    - Confidence score tracking
    - Dual-store indexing

    Usage:
        >>> pipeline = TranscriptIndexingPipeline(
        ...     dual_store_writer=writer
        ... )
        >>> result = await pipeline.run(
        ...     segments=segments,
        ...     transcript_id=transcript_uuid,
        ...     case_id=case_uuid
        ... )
    """

    def __init__(
        self,
        dual_store_writer: DualStoreWriter,
        model_name: str = "BAAI/bge-small-en-v1.5",
        batch_size: int = 100,
        max_chunk_size: int = 500,
    ):
        """
        Initialize the transcript indexing pipeline.

        Args:
            dual_store_writer: DualStoreWriter component
            model_name: FastEmbed model name
            batch_size: Batch size for embedding generation
            max_chunk_size: Maximum chunk size for speaker turns
        """
        self.dual_store_writer = dual_store_writer

        # Initialize components
        self.converter = TranscriptSegmentConverter()
        self.chunker = SpeakerAwareChunker(max_chunk_size=max_chunk_size)
        self.embedder = FastEmbedDocumentEmbedder(
            model_name=model_name,
            batch_size=batch_size,
        )
        self.sparse_embedder = SparseEmbedder()

        logger.info(
            f"Initialized TranscriptIndexingPipeline "
            f"(model={model_name}, max_chunk_size={max_chunk_size})"
        )

    async def run(
        self,
        segments: List[TranscriptSegment],
        transcript_id: UUID,
        case_id: UUID,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Index transcript segments.

        Args:
            segments: List of TranscriptSegment entities
            transcript_id: Transcript UUID
            case_id: Case UUID
            meta: Optional metadata

        Returns:
            Dictionary with:
                - success: Whether indexing succeeded
                - segments_indexed: Number of segments indexed
                - errors: List of error messages
        """
        try:
            logger.info(
                f"Indexing transcript {transcript_id} with {len(segments)} segments"
            )

            # Step 1: Convert segments to documents
            logger.debug("Step 1: Converting transcript segments")
            converter_result = self.converter.run(
                segments=segments,
                transcript_id=str(transcript_id),
                case_id=str(case_id),
                meta=meta,
            )
            documents = converter_result["documents"]

            if not documents:
                raise ValueError("Segment conversion produced no results")

            # Step 2: Chunk by speaker turns
            logger.debug("Step 2: Chunking by speaker turns")
            chunker_result = self.chunker.run(documents=documents)
            chunked_docs = chunker_result["documents"]

            # Step 3: Generate embeddings
            logger.debug("Step 3: Generating dense embeddings")
            embedder_result = self.embedder.run(documents=chunked_docs)
            embeddings = embedder_result["embeddings"]

            # Step 4: Generate sparse vectors
            logger.debug("Step 4: Generating sparse vectors")
            sparse_result = self.sparse_embedder.run(documents=chunked_docs)
            sparse_vectors = sparse_result["sparse_vectors"]

            # Step 5: Write to dual stores
            logger.debug("Step 5: Writing to Qdrant and OpenSearch")
            write_result = await self.dual_store_writer.run(
                documents=chunked_docs,
                case_id=case_id,
                transcript_id=transcript_id,
                segments=segments,
                embeddings=embeddings,
                sparse_vectors=sparse_vectors,
            )

            if not write_result["success"]:
                raise RuntimeError(
                    f"Dual store write failed: {write_result.get('errors', [])}"
                )

            logger.info(
                f"Successfully indexed {write_result['documents_written']} segments "
                f"for transcript {transcript_id}"
            )

            return {
                "success": True,
                "segments_indexed": write_result["documents_written"],
                "errors": [],
            }

        except Exception as e:
            error_msg = f"Transcript indexing failed: {e}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "segments_indexed": 0,
                "errors": [error_msg],
            }


class CommunicationIndexingPipeline:
    """
    Pipeline for indexing communications from forensic exports.

    Flow:
        Communications → Converter → ThreadGrouper
        → Dense Embedder → Sparse Embedder → DualStoreWriter

    Features:
    - Thread-based grouping
    - Participant metadata preservation
    - Platform and device tracking
    - Dual-store indexing

    Usage:
        >>> pipeline = CommunicationIndexingPipeline(
        ...     dual_store_writer=writer
        ... )
        >>> result = await pipeline.run(
        ...     communications=comms,
        ...     case_id=case_uuid
        ... )
    """

    def __init__(
        self,
        dual_store_writer: DualStoreWriter,
        model_name: str = "BAAI/bge-small-en-v1.5",
        batch_size: int = 100,
        max_messages_per_group: int = 10,
    ):
        """
        Initialize the communication indexing pipeline.

        Args:
            dual_store_writer: DualStoreWriter component
            model_name: FastEmbed model name
            batch_size: Batch size for embedding generation
            max_messages_per_group: Maximum messages per thread group
        """
        self.dual_store_writer = dual_store_writer

        # Initialize components
        self.converter = CommunicationConverter()
        self.grouper = ThreadGrouper(
            max_messages_per_group=max_messages_per_group
        )
        self.embedder = FastEmbedDocumentEmbedder(
            model_name=model_name,
            batch_size=batch_size,
        )
        self.sparse_embedder = SparseEmbedder()

        logger.info(
            f"Initialized CommunicationIndexingPipeline "
            f"(model={model_name}, max_messages_per_group={max_messages_per_group})"
        )

    async def run(
        self,
        communications: List[Communication],
        case_id: UUID,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Index communications.

        Args:
            communications: List of Communication entities
            case_id: Case UUID
            meta: Optional metadata

        Returns:
            Dictionary with:
                - success: Whether indexing succeeded
                - communications_indexed: Number of communications indexed
                - errors: List of error messages
        """
        try:
            logger.info(
                f"Indexing {len(communications)} communications for case {case_id}"
            )

            # Step 1: Convert communications to documents
            logger.debug("Step 1: Converting communications")
            converter_result = self.converter.run(
                communications=communications,
                case_id=str(case_id),
                meta=meta,
            )
            documents = converter_result["documents"]

            if not documents:
                raise ValueError("Communication conversion produced no results")

            # Step 2: Group by thread
            logger.debug("Step 2: Grouping by thread")
            grouper_result = self.grouper.run(documents=documents)
            grouped_docs = grouper_result["documents"]

            # Step 3: Generate embeddings
            logger.debug("Step 3: Generating dense embeddings")
            embedder_result = self.embedder.run(documents=grouped_docs)
            embeddings = embedder_result["embeddings"]

            # Step 4: Generate sparse vectors
            logger.debug("Step 4: Generating sparse vectors")
            sparse_result = self.sparse_embedder.run(documents=grouped_docs)
            sparse_vectors = sparse_result["sparse_vectors"]

            # Step 5: Write to dual stores
            logger.debug("Step 5: Writing to Qdrant and OpenSearch")
            write_result = await self.dual_store_writer.run(
                documents=grouped_docs,
                case_id=case_id,
                communications=communications,
                embeddings=embeddings,
                sparse_vectors=sparse_vectors,
            )

            if not write_result["success"]:
                raise RuntimeError(
                    f"Dual store write failed: {write_result.get('errors', [])}"
                )

            logger.info(
                f"Successfully indexed {write_result['documents_written']} communications "
                f"for case {case_id}"
            )

            return {
                "success": True,
                "communications_indexed": write_result["documents_written"],
                "errors": [],
            }

        except Exception as e:
            error_msg = f"Communication indexing failed: {e}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "communications_indexed": 0,
                "errors": [error_msg],
            }
