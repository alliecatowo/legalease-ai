"""
Document Processing Pipeline

Main orchestrator for end-to-end document processing:
Parser -> Chunker -> Embedder -> Indexer

Handles the complete workflow from raw document to indexed vectors in Qdrant.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from app.workers.pipelines.docling_parser import DoclingParser
from app.workers.pipelines.chunker import DocumentChunker
from app.workers.pipelines.embeddings import EmbeddingPipeline
from app.workers.pipelines.bm25_encoder import BM25Encoder
from app.workers.pipelines.indexer import QdrantIndexer

logger = logging.getLogger(__name__)


class ProcessingStage(str, Enum):
    """Document processing stages."""
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProcessingResult:
    """Result of document processing."""
    success: bool
    stage: ProcessingStage
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DocumentProcessor:
    """
    Main document processing pipeline orchestrator.

    Coordinates all stages of document processing:
    1. Parse document (extract text)
    2. Chunk text (hierarchical chunking)
    3. Generate embeddings (dense + sparse)
    4. Index to Qdrant (vector storage)
    """

    def __init__(
        self,
        use_ocr: bool = True,
        use_bm25: bool = True,
        embedding_model: str = "BAAI/bge-base-en-v1.5",
        summary_max_tokens: int = 2000,
        section_max_tokens: int = 500,
        microblock_max_tokens: int = 128,
    ):
        """
        Initialize the document processor.

        Args:
            use_ocr: Whether to use OCR for scanned documents
            use_bm25: Whether to generate BM25 sparse vectors
            embedding_model: HuggingFace model for dense embeddings
            summary_max_tokens: Max tokens for summary chunks
            section_max_tokens: Max tokens for section chunks
            microblock_max_tokens: Max tokens for microblock chunks
        """
        self.use_ocr = use_ocr
        self.use_bm25 = use_bm25

        # Initialize pipeline components
        self.parser = DoclingParser(use_ocr=use_ocr)
        self.chunker = DocumentChunker(
            summary_max_tokens=summary_max_tokens,
            section_max_tokens=section_max_tokens,
            microblock_max_tokens=microblock_max_tokens,
        )
        self.embedder = EmbeddingPipeline(model_name=embedding_model)
        self.bm25_encoder = BM25Encoder() if use_bm25 else None
        self.indexer = QdrantIndexer()

        logger.info(
            f"Initialized DocumentProcessor (OCR={use_ocr}, BM25={use_bm25}, "
            f"model={embedding_model})"
        )

    def process(
        self,
        file_content: bytes,
        filename: str,
        document_id: int,
        case_id: int,
        mime_type: Optional[str] = None,
    ) -> ProcessingResult:
        """
        Process a document through the complete pipeline.

        Args:
            file_content: Raw document bytes
            filename: Original filename
            document_id: Database document ID
            case_id: Database case ID
            mime_type: Optional MIME type

        Returns:
            ProcessingResult with success status and details
        """
        logger.info(f"Starting document processing: {filename} (doc_id={document_id}, case_id={case_id})")

        try:
            # Stage 1: Parse document
            logger.info("Stage 1/4: Parsing document")
            parse_result = self._parse_document(file_content, filename, mime_type)
            if not parse_result.success:
                return parse_result

            parsed_data = parse_result.data
            text = parsed_data["text"]
            pages = parsed_data.get("pages", [])
            metadata = parsed_data.get("metadata", {})

            logger.info(f"Parsed document: {len(text)} chars, {len(pages)} pages")

            # Stage 2: Chunk document
            logger.info("Stage 2/4: Chunking document")
            chunk_result = self._chunk_document(text, pages, metadata)
            if not chunk_result.success:
                return chunk_result

            chunks = chunk_result.data["chunks"]
            logger.info(f"Created {len(chunks)} chunks")

            # Stage 3: Generate embeddings
            logger.info("Stage 3/4: Generating embeddings")
            embedding_result = self._generate_embeddings(chunks)
            if not embedding_result.success:
                return embedding_result

            embeddings = embedding_result.data["embeddings"]
            sparse_vectors = embedding_result.data.get("sparse_vectors")

            # Stage 4: Index to Qdrant
            logger.info("Stage 4/4: Indexing to Qdrant")
            index_result = self._index_chunks(
                chunks=chunks,
                embeddings=embeddings,
                sparse_vectors=sparse_vectors,
                document_id=document_id,
                case_id=case_id,
            )
            if not index_result.success:
                return index_result

            # Success!
            logger.info(f"Successfully processed document {document_id}")
            return ProcessingResult(
                success=True,
                stage=ProcessingStage.COMPLETED,
                message="Document processed successfully",
                data={
                    "document_id": document_id,
                    "case_id": case_id,
                    "chunks_count": len(chunks),
                    "text_length": len(text),
                    "pages_count": len(pages),
                },
            )

        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                stage=ProcessingStage.FAILED,
                message="Document processing failed",
                error=str(e),
            )

    def _parse_document(
        self,
        file_content: bytes,
        filename: str,
        mime_type: Optional[str] = None,
    ) -> ProcessingResult:
        """
        Parse document to extract text.

        Args:
            file_content: Raw document bytes
            filename: Original filename
            mime_type: Optional MIME type

        Returns:
            ProcessingResult
        """
        try:
            parsed_data = self.parser.parse(
                file_content=file_content,
                filename=filename,
                mime_type=mime_type,
            )

            if not parsed_data.get("text"):
                return ProcessingResult(
                    success=False,
                    stage=ProcessingStage.PARSING,
                    message="No text extracted from document",
                    error="Empty text",
                )

            return ProcessingResult(
                success=True,
                stage=ProcessingStage.PARSING,
                message="Document parsed successfully",
                data=parsed_data,
            )

        except Exception as e:
            logger.error(f"Error parsing document: {e}")
            return ProcessingResult(
                success=False,
                stage=ProcessingStage.PARSING,
                message="Failed to parse document",
                error=str(e),
            )

    def _chunk_document(
        self,
        text: str,
        pages: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProcessingResult:
        """
        Chunk document into hierarchical chunks.

        Args:
            text: Document text
            pages: Optional page data
            metadata: Optional metadata

        Returns:
            ProcessingResult
        """
        try:
            chunks_by_type = self.chunker.chunk_document(
                text=text,
                pages=pages,
                metadata=metadata,
            )

            # Flatten all chunks into single list
            all_chunks = []
            for chunk_type, type_chunks in chunks_by_type.items():
                for chunk in type_chunks:
                    all_chunks.append({
                        "text": chunk.text,
                        "chunk_type": chunk.chunk_type,
                        "position": chunk.position,
                        "page_number": chunk.page_number,
                        "metadata": chunk.metadata or {},
                    })

            if not all_chunks:
                return ProcessingResult(
                    success=False,
                    stage=ProcessingStage.CHUNKING,
                    message="No chunks created",
                    error="Empty chunks",
                )

            return ProcessingResult(
                success=True,
                stage=ProcessingStage.CHUNKING,
                message="Document chunked successfully",
                data={
                    "chunks": all_chunks,
                    "chunks_by_type": chunks_by_type,
                },
            )

        except Exception as e:
            logger.error(f"Error chunking document: {e}")
            return ProcessingResult(
                success=False,
                stage=ProcessingStage.CHUNKING,
                message="Failed to chunk document",
                error=str(e),
            )

    def _generate_embeddings(
        self,
        chunks: List[Dict[str, Any]],
    ) -> ProcessingResult:
        """
        Generate dense and sparse embeddings for chunks.

        Args:
            chunks: List of chunk dictionaries

        Returns:
            ProcessingResult
        """
        try:
            # Group chunks by type
            chunks_by_type = {}
            for chunk in chunks:
                chunk_type = chunk.get("chunk_type", "section")
                if chunk_type not in chunks_by_type:
                    chunks_by_type[chunk_type] = []
                chunks_by_type[chunk_type].append(chunk)

            # Generate dense embeddings for each type
            embeddings = {}
            for chunk_type, type_chunks in chunks_by_type.items():
                texts = [c["text"] for c in type_chunks]
                logger.info(f"Generating {chunk_type} embeddings for {len(texts)} chunks")

                type_embeddings = self.embedder.generate_embeddings(texts)
                embeddings[chunk_type] = type_embeddings.tolist()

            # Generate sparse vectors if enabled
            sparse_vectors = None
            if self.use_bm25:
                logger.info("Generating BM25 sparse vectors")
                all_texts = [c["text"] for c in chunks]

                # Fit BM25 on all chunks
                self.bm25_encoder.fit(all_texts)

                # Encode each chunk
                sparse_vectors = self.bm25_encoder.batch_encode_to_qdrant_format(all_texts)

            return ProcessingResult(
                success=True,
                stage=ProcessingStage.EMBEDDING,
                message="Embeddings generated successfully",
                data={
                    "embeddings": embeddings,
                    "sparse_vectors": sparse_vectors,
                },
            )

        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return ProcessingResult(
                success=False,
                stage=ProcessingStage.EMBEDDING,
                message="Failed to generate embeddings",
                error=str(e),
            )

    def _index_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: Dict[str, List[List[float]]],
        sparse_vectors: Optional[List] = None,
        document_id: int = None,
        case_id: int = None,
    ) -> ProcessingResult:
        """
        Index chunks to Qdrant.

        Args:
            chunks: List of chunk dictionaries
            embeddings: Dictionary of embeddings by type
            sparse_vectors: Optional sparse vectors
            document_id: Database document ID
            case_id: Database case ID

        Returns:
            ProcessingResult
        """
        try:
            success = self.indexer.index_chunks(
                chunks=chunks,
                embeddings=embeddings,
                sparse_vectors=sparse_vectors,
                document_id=document_id,
                case_id=case_id,
            )

            if not success:
                return ProcessingResult(
                    success=False,
                    stage=ProcessingStage.INDEXING,
                    message="Failed to index chunks",
                    error="Indexing returned False",
                )

            return ProcessingResult(
                success=True,
                stage=ProcessingStage.INDEXING,
                message="Chunks indexed successfully",
                data={
                    "indexed_count": len(chunks),
                },
            )

        except Exception as e:
            logger.error(f"Error indexing chunks: {e}")
            return ProcessingResult(
                success=False,
                stage=ProcessingStage.INDEXING,
                message="Failed to index chunks",
                error=str(e),
            )

    def get_pipeline_info(self) -> Dict[str, Any]:
        """
        Get information about the pipeline configuration.

        Returns:
            Dictionary with pipeline info
        """
        return {
            "use_ocr": self.use_ocr,
            "use_bm25": self.use_bm25,
            "embedder_info": self.embedder.get_model_info(),
            "bm25_info": self.bm25_encoder.get_stats() if self.bm25_encoder else None,
            "indexer_info": self.indexer.get_stats(),
        }


# Convenience function for quick processing
def process_document(
    file_content: bytes,
    filename: str,
    document_id: int,
    case_id: int,
    mime_type: Optional[str] = None,
    use_ocr: bool = True,
    use_bm25: bool = True,
) -> ProcessingResult:
    """
    Convenience function to process a document.

    Args:
        file_content: Raw document bytes
        filename: Original filename
        document_id: Database document ID
        case_id: Database case ID
        mime_type: Optional MIME type
        use_ocr: Whether to use OCR
        use_bm25: Whether to generate BM25 vectors

    Returns:
        ProcessingResult
    """
    processor = DocumentProcessor(use_ocr=use_ocr, use_bm25=use_bm25)
    return processor.process(
        file_content=file_content,
        filename=filename,
        document_id=document_id,
        case_id=case_id,
        mime_type=mime_type,
    )
