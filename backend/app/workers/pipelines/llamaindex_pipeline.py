"""
LlamaIndex Document Ingestion Pipeline

Production-grade document processing using LlamaIndex with:
- Docling for parsing (tables, images, structure preservation)
- FastEmbed for embeddings (fast, lightweight, Qdrant-native)
- Hierarchical chunking (summary, section, microblock)
- BM25 sparse encoding for hybrid search
- Qdrant vector store integration
- Contextual retrieval with sliding windows
"""

import logging
from typing import List, Dict, Any, Optional, BinaryIO
from pathlib import Path

from llama_index.core import Document as LlamaDocument
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.schema import BaseNode, TextNode, MetadataMode
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from app.workers.pipelines.embeddings import FastEmbedPipeline
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.readers.docling import DoclingReader

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, NamedVector, NamedSparseVector

from app.workers.pipelines.bm25_encoder import BM25Encoder
from app.core.config import settings

logger = logging.getLogger(__name__)


class LlamaIndexDocumentPipeline:
    """
    Advanced document processing pipeline using LlamaIndex.

    Pipeline stages:
    1. Parse with Docling (PDF, DOCX, tables, images)
    2. Hierarchical chunking (summary, section, microblock)
    3. Contextual enrichment (parent/child context)
    4. Dense embedding with FastEmbed
    5. Sparse encoding with BM25
    6. Index to Qdrant with named vectors
    """

    def __init__(
        self,
        embedding_model: str = "BAAI/bge-small-en-v1.5",
        use_bm25: bool = True,
        use_docling_ocr: bool = True,
        qdrant_client: Optional[QdrantClient] = None,
        collection_name: Optional[str] = None,
    ):
        """
        Initialize the LlamaIndex pipeline.

        Args:
            embedding_model: FastEmbed model name
            use_bm25: Enable BM25 sparse vectors
            use_docling_ocr: Enable Docling OCR for scanned documents
            qdrant_client: Qdrant client instance
            collection_name: Qdrant collection name
        """
        self.embedding_model_name = embedding_model
        self.use_bm25 = use_bm25
        self.use_docling_ocr = use_docling_ocr
        self.collection_name = collection_name or settings.QDRANT_COLLECTION

        logger.info(f"Initializing LlamaIndexDocumentPipeline")
        logger.info(f"  Embedding model: {embedding_model}")
        logger.info(f"  BM25 enabled: {use_bm25}")
        logger.info(f"  Docling OCR: {use_docling_ocr}")

        # Initialize components
        self.embed_model = FastEmbedEmbedding(model_name=embedding_model)
        self.docling_reader = DoclingReader()

        # BM25 encoder for sparse vectors
        if self.use_bm25:
            self.bm25_encoder = BM25Encoder()
        else:
            self.bm25_encoder = None

        # Qdrant client
        if qdrant_client:
            self.qdrant_client = qdrant_client
        else:
            self.qdrant_client = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
            )

        # Get embedding dimension
        self.embedding_dim = self._get_embedding_dim()
        logger.info(f"  Embedding dimension: {self.embedding_dim}")

    def _get_embedding_dim(self) -> int:
        """Get embedding dimension from model."""
        try:
            # Embed a test string to get dimension
            test_embedding = self.embed_model.get_text_embedding("test")
            return len(test_embedding)
        except Exception as e:
            logger.warning(f"Could not determine embedding dimension: {e}")
            # Default for bge-small
            return 384

    def parse_document(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[bytes] = None,
        filename: Optional[str] = None,
        document_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[LlamaDocument]:
        """
        Parse document using Docling.

        Args:
            file_path: Path to file on disk
            file_content: File content as bytes
            filename: Filename (required if using file_content)
            document_metadata: Additional metadata to attach

        Returns:
            List of LlamaIndex Document objects
        """
        try:
            if file_path:
                logger.info(f"Parsing document from path: {file_path}")
                documents = self.docling_reader.load_data(file_path=file_path)
            elif file_content and filename:
                logger.info(f"Parsing document from bytes: {filename}")
                # Write to temp file for Docling
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp:
                    tmp.write(file_content)
                    tmp_path = tmp.name

                try:
                    documents = self.docling_reader.load_data(file_path=tmp_path)
                finally:
                    # Clean up temp file
                    import os
                    os.unlink(tmp_path)
            else:
                raise ValueError("Must provide either file_path or (file_content + filename)")

            # Attach metadata
            if document_metadata:
                for doc in documents:
                    doc.metadata.update(document_metadata)

            logger.info(f"Parsed {len(documents)} documents from Docling")
            return documents

        except Exception as e:
            logger.error(f"Error parsing document with Docling: {e}")
            raise

    def create_hierarchical_chunks(
        self,
        documents: List[LlamaDocument],
    ) -> Dict[str, List[TextNode]]:
        """
        Create hierarchical chunks at multiple granularities.

        Returns:
            Dict with keys: "summary", "section", "microblock"
        """
        chunks = {
            "summary": [],
            "section": [],
            "microblock": [],
        }

        # Summary: One per document (or large chunks)
        summary_splitter = SentenceSplitter(
            chunk_size=2048,
            chunk_overlap=200,
        )
        summary_nodes = summary_splitter.get_nodes_from_documents(documents)
        chunks["summary"] = summary_nodes

        # Section: Medium chunks (paragraphs/sections)
        section_splitter = SentenceSplitter(
            chunk_size=512,
            chunk_overlap=50,
        )
        section_nodes = section_splitter.get_nodes_from_documents(documents)
        chunks["section"] = section_nodes

        # Microblock: Small chunks (sentences)
        microblock_splitter = SentenceSplitter(
            chunk_size=128,
            chunk_overlap=20,
        )
        microblock_nodes = microblock_splitter.get_nodes_from_documents(documents)
        chunks["microblock"] = microblock_nodes

        logger.info(f"Created hierarchical chunks:")
        logger.info(f"  Summary: {len(chunks['summary'])}")
        logger.info(f"  Section: {len(chunks['section'])}")
        logger.info(f"  Microblock: {len(chunks['microblock'])}")

        return chunks

    def embed_nodes(
        self,
        nodes: List[TextNode],
    ) -> List[TextNode]:
        """
        Generate embeddings for nodes using FastEmbed.

        Args:
            nodes: List of TextNode objects

        Returns:
            Nodes with embeddings attached
        """
        if not nodes:
            return []

        # Extract texts
        texts = [node.get_content(metadata_mode=MetadataMode.NONE) for node in nodes]

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(texts)} nodes")
        for i, node in enumerate(nodes):
            embedding = self.embed_model.get_text_embedding(texts[i])
            node.embedding = embedding

        return nodes

    def add_bm25_vectors(
        self,
        nodes: List[TextNode],
    ) -> List[Dict[str, Any]]:
        """
        Add BM25 sparse vectors to nodes.

        Args:
            nodes: List of TextNode objects

        Returns:
            List of dicts with dense and sparse vectors
        """
        if not self.bm25_encoder:
            return [{"node": node, "bm25_vector": None} for node in nodes]

        results = []
        for node in nodes:
            text = node.get_content(metadata_mode=MetadataMode.NONE)
            indices, values = self.bm25_encoder.encode_to_qdrant_format(text)

            results.append({
                "node": node,
                "bm25_indices": indices,
                "bm25_values": values,
            })

        return results

    def index_to_qdrant(
        self,
        chunks_dict: Dict[str, List[TextNode]],
        document_id: int,
        case_id: int,
    ) -> int:
        """
        Index all chunks to Qdrant with named vectors.

        Args:
            chunks_dict: Dict of chunk type -> nodes
            document_id: Database document ID
            case_id: Database case ID

        Returns:
            Number of points indexed
        """
        all_points = []

        for chunk_type, nodes in chunks_dict.items():
            logger.info(f"Indexing {len(nodes)} {chunk_type} chunks")

            # Embed nodes
            nodes_with_embeddings = self.embed_nodes(nodes)

            # Add BM25 vectors
            nodes_with_bm25 = self.add_bm25_vectors(nodes_with_embeddings)

            # Create Qdrant points
            for i, item in enumerate(nodes_with_bm25):
                node = item["node"]

                # Build named vectors dict (dense vectors)
                named_vectors = {}
                if node.embedding:
                    # All chunk types use the same embedding
                    # But stored under different named vectors for search flexibility
                    named_vectors[chunk_type] = node.embedding

                # Build payload
                payload = {
                    "document_id": document_id,
                    "case_id": case_id,
                    "chunk_type": chunk_type,
                    "text": node.get_content(metadata_mode=MetadataMode.NONE),
                    "position": i,
                    "metadata": node.metadata,
                }

                # Create point
                point = PointStruct(
                    id=hash(f"{document_id}_{chunk_type}_{i}") % (2**63 - 1),  # Unique ID
                    vector=named_vectors,
                    payload=payload,
                )

                # Add sparse vector if available
                if self.use_bm25 and item.get("bm25_indices"):
                    point.vector["bm25"] = NamedSparseVector(
                        name="bm25",
                        vector={
                            "indices": item["bm25_indices"],
                            "values": item["bm25_values"],
                        }
                    )

                all_points.append(point)

        # Upsert to Qdrant
        if all_points:
            logger.info(f"Upserting {len(all_points)} points to Qdrant")
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=all_points,
                wait=True,
            )

        return len(all_points)

    def process(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[bytes] = None,
        filename: Optional[str] = None,
        document_id: int = None,
        case_id: int = None,
        document_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Complete document processing pipeline.

        Args:
            file_path: Path to file
            file_content: File content as bytes
            filename: Filename
            document_id: Database document ID
            case_id: Database case ID
            document_metadata: Additional metadata

        Returns:
            Processing result summary
        """
        try:
            # 1. Parse with Docling
            documents = self.parse_document(
                file_path=file_path,
                file_content=file_content,
                filename=filename,
                document_metadata=document_metadata or {},
            )

            # 2. Create hierarchical chunks
            chunks_dict = self.create_hierarchical_chunks(documents)

            # 3. Index to Qdrant
            total_points = self.index_to_qdrant(
                chunks_dict=chunks_dict,
                document_id=document_id,
                case_id=case_id,
            )

            result = {
                "success": True,
                "documents_parsed": len(documents),
                "chunks_created": {
                    "summary": len(chunks_dict["summary"]),
                    "section": len(chunks_dict["section"]),
                    "microblock": len(chunks_dict["microblock"]),
                    "total": total_points,
                },
                "indexed_points": total_points,
            }

            logger.info(f"Document processing complete: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in document processing pipeline: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "chunks_created": {"summary": 0, "section": 0, "microblock": 0, "total": 0},
                "indexed_points": 0,
            }
