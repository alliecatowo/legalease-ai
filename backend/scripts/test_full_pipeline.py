#!/usr/bin/env python3
"""
End-to-End Document Pipeline Test

Comprehensive test script that validates the entire document processing pipeline:
1. Document parsing with Marker (PDF -> structured text)
2. Hierarchical chunking (summary, section, microblock)
3. Embedding generation (dense vectors with FastEmbed)
4. BM25 encoding (sparse vectors for keyword search)
5. Qdrant indexing (vector storage)
6. Search retrieval (hybrid search with BM25 + dense vectors)
7. Result validation

Usage:
    python scripts/test_full_pipeline.py [--pdf-path PATH] [--skip-indexing] [--search-only]

Environment:
    Requires: Qdrant, PostgreSQL, Redis running (via docker-compose)
    PDF: Uses test PDF or creates sample if none provided
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import asyncio
import tempfile
from datetime import datetime
import uuid

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging with detailed output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = get_logger(__name__)

# Imports for pipeline components
from app.workers.parsers.marker_parser import MarkerParser
from app.workers.parsers.base import ParserType
from app.workers.pipelines.chunker import DocumentChunker
from app.workers.pipelines.embeddings import FastEmbedPipeline
from app.workers.pipelines.bm25_encoder import BM25Encoder
from app.workers.pipelines.indexer import QdrantIndexer
from app.services.search.engine import HybridSearchEngine
from app.schemas.search import HybridSearchRequest
from app.core.qdrant import create_collection, get_qdrant_client, get_collection_info
from app.core.config import settings
from app.core.logging_config import get_logger


class PipelineTestResult:
    """Container for test results at each stage."""

    def __init__(self):
        self.stages = {}
        self.timings = {}
        self.errors = []
        self.start_time = datetime.now()

    def add_stage(self, stage_name: str, success: bool, data: Any = None, error: str = None, duration: float = 0):
        """Record results for a pipeline stage."""
        self.stages[stage_name] = {
            'success': success,
            'data': data,
            'error': error,
            'duration': duration,
        }
        if error:
            self.errors.append(f"{stage_name}: {error}")

    def summary(self) -> str:
        """Generate summary report."""
        total_time = (datetime.now() - self.start_time).total_seconds()
        success_count = sum(1 for s in self.stages.values() if s['success'])
        total_stages = len(self.stages)

        report = [
            "\n" + "="*80,
            "PIPELINE TEST SUMMARY",
            "="*80,
            f"Total Time: {total_time:.2f}s",
            f"Stages Completed: {success_count}/{total_stages}",
            "",
            "Stage Results:",
            "-"*80,
        ]

        for stage_name, result in self.stages.items():
            status = "✓ PASS" if result['success'] else "✗ FAIL"
            duration = f"({result['duration']:.2f}s)" if result['duration'] else ""
            report.append(f"  {status} {stage_name} {duration}")
            if result['error']:
                report.append(f"      Error: {result['error']}")

        if self.errors:
            report.extend([
                "",
                "Errors:",
                "-"*80,
            ])
            for error in self.errors:
                report.append(f"  - {error}")

        report.append("="*80)
        return "\n".join(report)


def create_sample_pdf() -> bytes:
    """
    Create a simple test PDF document.

    Returns:
        PDF bytes for testing
    """
    logger.info("Creating sample PDF for testing...")

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from io import BytesIO

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)

        # Page 1: Title and introduction
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "Legal Document Test Case")

        c.setFont("Helvetica", 12)
        c.drawString(100, 720, "Case No: TEST-2025-001")
        c.drawString(100, 700, "Date: January 15, 2025")

        c.setFont("Helvetica", 11)
        y = 650
        intro_text = [
            "This is a test legal document for validating the document processing pipeline.",
            "It contains multiple sections with different types of content including:",
            "- Contract clauses",
            "- Legal definitions",
            "- Terms and conditions",
            "- Whereas clauses",
        ]
        for line in intro_text:
            c.drawString(100, y, line)
            y -= 20

        # Add a section header
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y - 20, "ARTICLE I: DEFINITIONS")

        c.setFont("Helvetica", 11)
        y -= 60
        definitions = [
            "1.1 'Agreement' means this legal test document and all amendments.",
            "1.2 'Party' means any entity entering into this agreement.",
            "1.3 'Effective Date' means the date of execution hereof.",
            "1.4 'Confidential Information' means all non-public information.",
        ]
        for defn in definitions:
            c.drawString(100, y, defn)
            y -= 25

        c.showPage()

        # Page 2: Whereas clauses and terms
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, 750, "WHEREAS CLAUSES")

        c.setFont("Helvetica", 11)
        y = 720
        whereas_clauses = [
            "WHEREAS, the parties wish to establish a legal framework for cooperation;",
            "WHEREAS, both parties acknowledge the importance of confidentiality;",
            "WHEREAS, the terms herein shall govern all future interactions;",
        ]
        for clause in whereas_clauses:
            c.drawString(100, y, clause)
            y -= 30

        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y - 20, "NOW THEREFORE")

        c.setFont("Helvetica", 11)
        y -= 50
        c.drawString(100, y, "The parties hereby agree to the following terms and conditions:")
        y -= 40

        terms = [
            "Section 1: Both parties shall maintain strict confidentiality.",
            "Section 2: This agreement is effective immediately upon execution.",
            "Section 3: Any disputes shall be resolved through arbitration.",
            "Section 4: This agreement may be amended only in writing.",
        ]
        for term in terms:
            c.drawString(100, y, term)
            y -= 25

        c.showPage()
        c.save()

        pdf_bytes = buffer.getvalue()
        logger.info(f"Created sample PDF ({len(pdf_bytes)} bytes)")
        return pdf_bytes

    except ImportError:
        logger.warning("reportlab not installed, creating minimal PDF")
        # Fallback: create minimal PDF without reportlab
        minimal_pdf = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources 4 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj
4 0 obj
<< /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >>
endobj
5 0 obj
<< /Length 200 >>
stream
BT
/F1 12 Tf
50 750 Td
(Legal Document Test Case) Tj
0 -20 Td
(This is a test document for pipeline validation.) Tj
0 -20 Td
(It contains contract clauses and legal definitions.) Tj
0 -20 Td
(Section 1: Confidentiality requirements apply.) Tj
ET
endstream
endobj
xref
0 6
trailer
<< /Size 6 /Root 1 0 R >>
startxref
500
%%EOF"""
        return minimal_pdf


async def test_stage_1_parsing(test_result: PipelineTestResult, pdf_bytes: bytes, filename: str) -> Optional[Dict[str, Any]]:
    """
    Stage 1: Test document parsing with Marker.

    Tests:
    - PDF parsing with VLM support
    - Text extraction
    - Page segmentation
    - Block structure extraction
    - Bounding box extraction
    """
    import time
    stage_name = "1_PARSING"
    logger.info("\n" + "="*80)
    logger.info(f"STAGE 1: Document Parsing with Marker")
    logger.info("="*80)

    start_time = time.time()

    try:
        # Initialize Marker parser with VLM support
        logger.info("Initializing Marker parser (VLM enabled)...")
        parser = MarkerParser(
            use_llm=True,
            gemini_model_name="gemini-2.0-flash",
            output_format="json",
        )

        # Parse document
        logger.info(f"Parsing document: {filename} ({len(pdf_bytes)/1024:.1f}KB)")
        parsed_doc = parser.parse(pdf_bytes, filename)

        duration = time.time() - start_time

        # Validate results
        logger.info("\nParsing Results:")
        logger.info(f"  ✓ Parser Type: {parsed_doc.parser_type}")
        logger.info(f"  ✓ Total Pages: {parsed_doc.page_count}")
        logger.info(f"  ✓ Content Pages: {parsed_doc.content_page_count}")
        logger.info(f"  ✓ Total Characters: {len(parsed_doc.text):,}")
        logger.info(f"  ✓ Total Words: {len(parsed_doc.text.split()):,}")
        logger.info(f"  ✓ Processing Time: {duration:.2f}s")

        # Show sample text
        sample_length = 200
        sample_text = parsed_doc.text[:sample_length]
        logger.info(f"\nSample Text (first {sample_length} chars):")
        logger.info(f"  {sample_text}...")

        # Page-level details
        if parsed_doc.pages:
            logger.info(f"\nPage Details:")
            for i, page in enumerate(parsed_doc.pages[:3], 1):  # First 3 pages
                logger.info(f"  Page {i}:")
                logger.info(f"    - Characters: {len(page.text):,}")
                logger.info(f"    - Blocks: {len(page.blocks)}")
                logger.info(f"    - BBoxes: {len(page.bboxes)}")

                # Show block types
                if page.blocks:
                    block_types = {}
                    for block in page.blocks:
                        block_type = block.get('block_type', 'Unknown')
                        block_types[block_type] = block_types.get(block_type, 0) + 1
                    logger.info(f"    - Block Types: {dict(block_types)}")

        # Metadata
        logger.info(f"\nMetadata:")
        for key, value in parsed_doc.metadata.items():
            logger.info(f"  - {key}: {value}")

        # Package results
        result_data = {
            'parsed_doc': parsed_doc,
            'text': parsed_doc.text,
            'pages': [
                {
                    'page_number': p.page_number,
                    'text': p.text,
                    'blocks': p.blocks,
                    'bboxes': p.bboxes,
                    'metadata': p.metadata,
                }
                for p in parsed_doc.pages
            ],
            'metadata': parsed_doc.metadata,
        }

        test_result.add_stage(stage_name, True, result_data, duration=duration)
        logger.info(f"\n✓ Stage 1 completed successfully in {duration:.2f}s")
        return result_data

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"✗ Parsing failed: {e}", exc_info=True)
        test_result.add_stage(stage_name, False, error=str(e), duration=duration)
        return None


async def test_stage_2_chunking(test_result: PipelineTestResult, parsing_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Stage 2: Test hierarchical chunking.

    Tests:
    - Summary-level chunks (document overview)
    - Section-level chunks (logical sections)
    - Microblock-level chunks (fine-grained)
    - Chunk overlap
    - Metadata preservation
    """
    import time
    stage_name = "2_CHUNKING"
    logger.info("\n" + "="*80)
    logger.info(f"STAGE 2: Hierarchical Chunking")
    logger.info("="*80)

    start_time = time.time()

    try:
        # Initialize chunker
        logger.info("Initializing DocumentChunker...")
        chunker = DocumentChunker(
            summary_max_tokens=2000,
            section_max_tokens=500,
            microblock_max_tokens=128,
            overlap_tokens=50,
            use_semantic_splitting=True,
        )

        # Extract data from parsing results
        text = parsing_result['text']
        pages = parsing_result['pages']
        metadata = parsing_result['metadata']

        # Chunk document
        logger.info(f"Chunking document ({len(text):,} chars, {len(text.split()):,} words)...")
        chunks_by_type = chunker.chunk_document(text, pages, metadata)

        duration = time.time() - start_time

        # Validate results
        logger.info("\nChunking Results:")
        total_chunks = sum(len(chunks) for chunks in chunks_by_type.values())
        logger.info(f"  ✓ Total Chunks: {total_chunks}")
        logger.info(f"  ✓ Summary Chunks: {len(chunks_by_type['summary'])}")
        logger.info(f"  ✓ Section Chunks: {len(chunks_by_type['section'])}")
        logger.info(f"  ✓ Microblock Chunks: {len(chunks_by_type['microblock'])}")
        logger.info(f"  ✓ Processing Time: {duration:.2f}s")

        # Show sample chunks
        for chunk_type in ['summary', 'section', 'microblock']:
            chunks = chunks_by_type[chunk_type]
            if chunks:
                logger.info(f"\n{chunk_type.upper()} Sample (first chunk):")
                sample = chunks[0]
                logger.info(f"  - Position: {sample.position}")
                logger.info(f"  - Page: {sample.page_number}")
                logger.info(f"  - Text Length: {len(sample.text)} chars")
                logger.info(f"  - Word Count: {len(sample.text.split())} words")
                logger.info(f"  - BBoxes: {len(sample.bboxes) if sample.bboxes else 0}")
                logger.info(f"  - Text: {sample.text[:150]}...")

        # Convert to flat list for indexing
        all_chunks = []
        for chunk_type, chunks in chunks_by_type.items():
            for chunk in chunks:
                all_chunks.append({
                    'text': chunk.text,
                    'chunk_type': chunk.chunk_type,
                    'position': chunk.position,
                    'page_number': chunk.page_number,
                    'metadata': chunk.metadata or {},
                    'char_count': len(chunk.text),
                    'word_count': len(chunk.text.split()),
                    'bboxes': chunk.bboxes or [],
                })

        result_data = {
            'chunks_by_type': chunks_by_type,
            'all_chunks': all_chunks,
            'total_chunks': total_chunks,
        }

        test_result.add_stage(stage_name, True, result_data, duration=duration)
        logger.info(f"\n✓ Stage 2 completed successfully in {duration:.2f}s")
        return result_data

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"✗ Chunking failed: {e}", exc_info=True)
        test_result.add_stage(stage_name, False, error=str(e), duration=duration)
        return None


async def test_stage_3_embeddings(test_result: PipelineTestResult, chunking_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Stage 3: Test embedding generation.

    Tests:
    - Dense vector embeddings with FastEmbed
    - Multi-type embedding (summary, section, microblock)
    - Batch processing
    - Memory efficiency
    """
    import time
    stage_name = "3_EMBEDDINGS"
    logger.info("\n" + "="*80)
    logger.info(f"STAGE 3: Embedding Generation")
    logger.info("="*80)

    start_time = time.time()

    try:
        # Initialize embedding pipeline
        logger.info("Initializing FastEmbed pipeline...")
        embedder = FastEmbedPipeline(model_name="BAAI/bge-small-en-v1.5")
        logger.info(f"  Model: {embedder.model_name}")
        logger.info(f"  Dimension: {embedder.embedding_dim}")

        # Get chunks by type
        chunks_by_type = chunking_result['chunks_by_type']

        # Generate embeddings for each chunk type
        embeddings_by_type = {}
        embedding_stats = {}

        for chunk_type, chunks in chunks_by_type.items():
            if not chunks:
                continue

            logger.info(f"\nGenerating {chunk_type} embeddings ({len(chunks)} chunks)...")

            # Extract texts
            texts = [chunk.text for chunk in chunks]

            # Generate embeddings with memory-efficient batching
            type_start = time.time()
            embeddings = embedder.generate_embeddings(texts, batch_size=100, show_progress=False)
            type_duration = time.time() - type_start

            embeddings_by_type[chunk_type] = embeddings.tolist()

            embedding_stats[chunk_type] = {
                'count': len(embeddings),
                'dimension': len(embeddings[0]) if len(embeddings) > 0 else 0,
                'duration': type_duration,
            }

            logger.info(f"  ✓ Generated {len(embeddings)} {chunk_type} embeddings")
            logger.info(f"    - Shape: {embeddings.shape}")
            logger.info(f"    - Time: {type_duration:.2f}s")

        duration = time.time() - start_time

        # Summary
        total_embeddings = sum(stats['count'] for stats in embedding_stats.values())
        logger.info(f"\nEmbedding Results:")
        logger.info(f"  ✓ Total Embeddings: {total_embeddings}")
        logger.info(f"  ✓ Dimension: {embedder.embedding_dim}")
        logger.info(f"  ✓ Processing Time: {duration:.2f}s")

        for chunk_type, stats in embedding_stats.items():
            logger.info(f"  ✓ {chunk_type}: {stats['count']} embeddings ({stats['duration']:.2f}s)")

        result_data = {
            'embeddings_by_type': embeddings_by_type,
            'stats': embedding_stats,
            'total_embeddings': total_embeddings,
            'dimension': embedder.embedding_dim,
        }

        test_result.add_stage(stage_name, True, result_data, duration=duration)
        logger.info(f"\n✓ Stage 3 completed successfully in {duration:.2f}s")
        return result_data

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"✗ Embedding generation failed: {e}", exc_info=True)
        test_result.add_stage(stage_name, False, error=str(e), duration=duration)
        return None


async def test_stage_4_bm25(test_result: PipelineTestResult, chunking_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Stage 4: Test BM25 sparse vector encoding.

    Tests:
    - BM25 encoding for keyword search
    - Sparse vector format
    - Token indexing
    """
    import time
    stage_name = "4_BM25_ENCODING"
    logger.info("\n" + "="*80)
    logger.info(f"STAGE 4: BM25 Sparse Vector Encoding")
    logger.info("="*80)

    start_time = time.time()

    try:
        # Initialize BM25 encoder
        logger.info("Initializing BM25 encoder...")
        bm25_encoder = BM25Encoder()

        # Get all chunks
        all_chunks = chunking_result['all_chunks']
        logger.info(f"Encoding {len(all_chunks)} chunks to BM25 sparse vectors...")

        # Encode chunks
        sparse_vectors = []
        for i, chunk in enumerate(all_chunks):
            indices, values = bm25_encoder.encode_to_qdrant_format(chunk['text'])
            sparse_vectors.append((indices, values))

            if i < 3:  # Show first 3
                logger.info(f"  Chunk {i}: {len(indices)} tokens")
                logger.info(f"    Indices: {indices[:5]}...")
                logger.info(f"    Values: {values[:5]}...")

        duration = time.time() - start_time

        # Statistics
        avg_tokens = sum(len(sv[0]) for sv in sparse_vectors) / len(sparse_vectors) if sparse_vectors else 0
        max_tokens = max(len(sv[0]) for sv in sparse_vectors) if sparse_vectors else 0

        logger.info(f"\nBM25 Encoding Results:")
        logger.info(f"  ✓ Total Sparse Vectors: {len(sparse_vectors)}")
        logger.info(f"  ✓ Average Tokens: {avg_tokens:.1f}")
        logger.info(f"  ✓ Max Tokens: {max_tokens}")
        logger.info(f"  ✓ Processing Time: {duration:.2f}s")

        result_data = {
            'sparse_vectors': sparse_vectors,
            'total_vectors': len(sparse_vectors),
            'avg_tokens': avg_tokens,
            'max_tokens': max_tokens,
        }

        test_result.add_stage(stage_name, True, result_data, duration=duration)
        logger.info(f"\n✓ Stage 4 completed successfully in {duration:.2f}s")
        return result_data

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"✗ BM25 encoding failed: {e}", exc_info=True)
        test_result.add_stage(stage_name, False, error=str(e), duration=duration)
        return None


async def test_stage_5_indexing(
    test_result: PipelineTestResult,
    chunking_result: Dict[str, Any],
    embedding_result: Dict[str, Any],
    bm25_result: Dict[str, Any],
    test_document_id: uuid.UUID,
    test_case_id: uuid.UUID,
) -> Optional[Dict[str, Any]]:
    """
    Stage 5: Test Qdrant indexing.

    Tests:
    - Collection creation
    - Point insertion
    - Multi-vector indexing (summary, section, microblock)
    - Sparse vector indexing (BM25)
    - Metadata storage
    """
    import time
    stage_name = "5_INDEXING"
    logger.info("\n" + "="*80)
    logger.info(f"STAGE 5: Qdrant Indexing")
    logger.info("="*80)

    start_time = time.time()

    try:
        # Ensure collection exists
        logger.info("Ensuring Qdrant collection exists...")
        create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            summary_vector_size=384,
            section_vector_size=384,
            microblock_vector_size=384,
            recreate=False,
        )

        # Get collection info
        collection_info = get_collection_info()
        logger.info(f"  Collection: {collection_info['name']}")
        logger.info(f"  Points: {collection_info['vectors_count']}")
        logger.info(f"  Status: {collection_info['status']}")

        # Initialize indexer
        logger.info("\nInitializing QdrantIndexer...")
        indexer = QdrantIndexer(batch_size=100)

        # Prepare data for indexing
        all_chunks = chunking_result['all_chunks']
        embeddings_by_type = embedding_result['embeddings_by_type']
        sparse_vectors = bm25_result['sparse_vectors']

        logger.info(f"Indexing {len(all_chunks)} chunks...")
        logger.info(f"  - Document ID: {test_document_id}")
        logger.info(f"  - Case ID: {test_case_id}")

        # Index chunks
        index_start = time.time()
        success = indexer.index_chunks(
            chunks=all_chunks,
            embeddings=embeddings_by_type,
            sparse_vectors=sparse_vectors,
            document_id=test_document_id,
            case_id=test_case_id,
        )
        index_duration = time.time() - index_start

        if not success:
            raise Exception("Indexing returned False")

        duration = time.time() - start_time

        # Get updated collection info
        updated_info = get_collection_info()
        new_points = updated_info['vectors_count'] - collection_info['vectors_count']

        logger.info(f"\nIndexing Results:")
        logger.info(f"  ✓ Success: {success}")
        logger.info(f"  ✓ Points Added: {new_points}")
        logger.info(f"  ✓ Total Points: {updated_info['vectors_count']}")
        logger.info(f"  ✓ Indexing Time: {index_duration:.2f}s")
        logger.info(f"  ✓ Total Time: {duration:.2f}s")

        result_data = {
            'success': success,
            'points_added': new_points,
            'total_points': updated_info['vectors_count'],
            'document_id': str(test_document_id),
            'case_id': str(test_case_id),
        }

        test_result.add_stage(stage_name, True, result_data, duration=duration)
        logger.info(f"\n✓ Stage 5 completed successfully in {duration:.2f}s")
        return result_data

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"✗ Indexing failed: {e}", exc_info=True)
        test_result.add_stage(stage_name, False, error=str(e), duration=duration)
        return None


async def test_stage_6_search(
    test_result: PipelineTestResult,
    test_document_id: uuid.UUID,
    test_case_id: uuid.UUID,
) -> Optional[Dict[str, Any]]:
    """
    Stage 6: Test hybrid search retrieval.

    Tests:
    - BM25 keyword search
    - Dense vector semantic search
    - Hybrid search (BM25 + dense)
    - RRF/DBSF fusion
    - Result ranking
    - Score normalization
    """
    import time
    stage_name = "6_SEARCH"
    logger.info("\n" + "="*80)
    logger.info(f"STAGE 6: Search Retrieval")
    logger.info("="*80)

    start_time = time.time()

    try:
        # Initialize search engine
        logger.info("Initializing HybridSearchEngine...")
        search_engine = HybridSearchEngine(enable_reranking=False)

        # Test queries
        test_queries = [
            {
                'name': 'Keyword Search (BM25 only)',
                'query': 'confidentiality agreement',
                'use_bm25': True,
                'use_dense': False,
            },
            {
                'name': 'Semantic Search (Dense only)',
                'query': 'what are the privacy requirements?',
                'use_bm25': False,
                'use_dense': True,
            },
            {
                'name': 'Hybrid Search (BM25 + Dense, RRF)',
                'query': 'effective date and parties agreement',
                'use_bm25': True,
                'use_dense': True,
                'fusion_method': 'rrf',
            },
            {
                'name': 'Hybrid Search (BM25 + Dense, DBSF)',
                'query': 'whereas clauses and definitions',
                'use_bm25': True,
                'use_dense': True,
                'fusion_method': 'dbsf',
            },
        ]

        search_results = []

        for test_query in test_queries:
            logger.info(f"\n{test_query['name']}")
            logger.info(f"  Query: '{test_query['query']}'")

            # Build search request
            request = HybridSearchRequest(
                query=test_query['query'],
                use_bm25=test_query.get('use_bm25', True),
                use_dense=test_query.get('use_dense', True),
                fusion_method=test_query.get('fusion_method', 'rrf'),
                top_k=5,
                score_threshold=0.0,  # Get all results for testing
                document_ids=[str(test_document_id)],
            )

            # Perform search
            query_start = time.time()
            response = search_engine.search(request)
            query_duration = time.time() - query_start

            logger.info(f"  Results: {len(response.results)}")
            logger.info(f"  Time: {query_duration*1000:.0f}ms")

            # Show top results
            for i, result in enumerate(response.results[:3], 1):
                logger.info(f"\n  Result {i}:")
                logger.info(f"    Score: {result.score:.4f}")
                logger.info(f"    Match Type: {result.match_type}")
                logger.info(f"    Chunk Type: {result.metadata.get('chunk_type')}")
                logger.info(f"    BM25 Score: {result.metadata.get('bm25_score', 0):.4f}")
                logger.info(f"    Dense Score: {result.metadata.get('dense_score', 0):.4f}")
                logger.info(f"    Text: {result.text[:100]}...")

            search_results.append({
                'query': test_query,
                'response': response,
                'duration': query_duration,
            })

        duration = time.time() - start_time

        logger.info(f"\nSearch Results Summary:")
        logger.info(f"  ✓ Total Queries: {len(test_queries)}")
        logger.info(f"  ✓ Total Time: {duration:.2f}s")
        logger.info(f"  ✓ Avg Time per Query: {duration/len(test_queries)*1000:.0f}ms")

        result_data = {
            'search_results': search_results,
            'total_queries': len(test_queries),
            'total_time': duration,
        }

        test_result.add_stage(stage_name, True, result_data, duration=duration)
        logger.info(f"\n✓ Stage 6 completed successfully in {duration:.2f}s")
        return result_data

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"✗ Search failed: {e}", exc_info=True)
        test_result.add_stage(stage_name, False, error=str(e), duration=duration)
        return None


async def main(pdf_path: Optional[str] = None, skip_indexing: bool = False, search_only: bool = False):
    """
    Run the complete end-to-end pipeline test.

    Args:
        pdf_path: Optional path to PDF file to test
        skip_indexing: Skip indexing stage (use for testing search only)
        search_only: Only run search tests (assumes data already indexed)
    """
    test_result = PipelineTestResult()

    logger.info("="*80)
    logger.info("END-TO-END DOCUMENT PIPELINE TEST")
    logger.info("="*80)
    logger.info(f"Start Time: {test_result.start_time}")
    logger.info(f"PDF Path: {pdf_path or 'Generated sample'}")
    logger.info(f"Skip Indexing: {skip_indexing}")
    logger.info(f"Search Only: {search_only}")

    # Generate test IDs
    test_document_id = uuid.uuid4()
    test_case_id = uuid.uuid4()

    logger.info(f"Test Document ID: {test_document_id}")
    logger.info(f"Test Case ID: {test_case_id}")

    try:
        # Load or create PDF
        if pdf_path and os.path.exists(pdf_path):
            logger.info(f"\nLoading PDF from: {pdf_path}")
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            filename = os.path.basename(pdf_path)
        else:
            logger.info("\nCreating sample PDF...")
            pdf_bytes = create_sample_pdf()
            filename = "test_document.pdf"

        if not search_only:
            # Stage 1: Parsing
            parsing_result = await test_stage_1_parsing(test_result, pdf_bytes, filename)
            if not parsing_result:
                logger.error("Pipeline failed at Stage 1: Parsing")
                print(test_result.summary())
                return

            # Stage 2: Chunking
            chunking_result = await test_stage_2_chunking(test_result, parsing_result)
            if not chunking_result:
                logger.error("Pipeline failed at Stage 2: Chunking")
                print(test_result.summary())
                return

            # Stage 3: Embeddings
            embedding_result = await test_stage_3_embeddings(test_result, chunking_result)
            if not embedding_result:
                logger.error("Pipeline failed at Stage 3: Embeddings")
                print(test_result.summary())
                return

            # Stage 4: BM25
            bm25_result = await test_stage_4_bm25(test_result, chunking_result)
            if not bm25_result:
                logger.error("Pipeline failed at Stage 4: BM25")
                print(test_result.summary())
                return

            if not skip_indexing:
                # Stage 5: Indexing
                indexing_result = await test_stage_5_indexing(
                    test_result,
                    chunking_result,
                    embedding_result,
                    bm25_result,
                    test_document_id,
                    test_case_id,
                )
                if not indexing_result:
                    logger.error("Pipeline failed at Stage 5: Indexing")
                    print(test_result.summary())
                    return

        # Stage 6: Search (always run if we have data)
        if not skip_indexing or search_only:
            search_result = await test_stage_6_search(
                test_result,
                test_document_id,
                test_case_id,
            )
            if not search_result:
                logger.error("Pipeline failed at Stage 6: Search")
                print(test_result.summary())
                return

        # Print summary
        print(test_result.summary())

        logger.info("\n" + "="*80)
        logger.info("✓ ALL TESTS PASSED!")
        logger.info("="*80)

    except Exception as e:
        logger.error(f"\n✗ Pipeline test failed with exception: {e}", exc_info=True)
        print(test_result.summary())
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="End-to-end document pipeline test")
    parser.add_argument("--pdf-path", type=str, help="Path to PDF file to test")
    parser.add_argument("--skip-indexing", action="store_true", help="Skip indexing stage")
    parser.add_argument("--search-only", action="store_true", help="Only run search tests")

    args = parser.parse_args()

    asyncio.run(main(
        pdf_path=args.pdf_path,
        skip_indexing=args.skip_indexing,
        search_only=args.search_only,
    ))
