"""
Integration Example: Using Embedding Pipeline with Celery + Qdrant

This example shows how to integrate the embedding pipeline into your
LegalEase document processing workflow.
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

# These would be your actual imports
# from qdrant_client import QdrantClient
# from qdrant_client.models import PointStruct
# from app.workers.celery_app import celery_app

from app.workers.pipelines import EmbeddingPipeline, BM25Encoder

logger = logging.getLogger(__name__)


# ============================================================================
# Example 1: Document Indexing Task
# ============================================================================

def index_document_to_qdrant(
    document_id: int,
    text: str,
    chunks: List[str],
    metadata: Dict[str, Any],
    collection_name: str = "legal_documents",
):
    """
    Index a document with its chunks to Qdrant using hybrid search.

    Args:
        document_id: Unique document ID
        text: Full document text
        chunks: List of text chunks (sections, microblocks, etc.)
        metadata: Document metadata (type, date, parties, etc.)
        collection_name: Qdrant collection name
    """
    logger.info(f"Indexing document {document_id} with {len(chunks)} chunks")

    # Initialize pipelines
    embedding_pipeline = EmbeddingPipeline(
        model_name="BAAI/bge-base-en-v1.5",
        batch_size=32,
    )

    bm25_encoder = BM25Encoder(k1=1.5, b=0.75)

    # Fit BM25 on the document chunks
    # (In production, you'd fit on your entire corpus periodically)
    bm25_encoder.fit(chunks)

    # Generate embeddings for all chunks
    dense_embeddings = embedding_pipeline.generate_embeddings(
        chunks,
        show_progress=True
    )

    # Generate sparse vectors for all chunks
    sparse_vectors = bm25_encoder.batch_encode_to_qdrant_format(chunks)

    # Create Qdrant points
    points = []
    for idx, (chunk_text, dense_emb, (sparse_idx, sparse_vals)) in enumerate(
        zip(chunks, dense_embeddings, sparse_vectors)
    ):
        point = {
            "id": f"{document_id}_{idx}",  # Composite ID
            "vector": {
                "dense": dense_emb.tolist(),
                "sparse": {
                    "indices": sparse_idx,
                    "values": sparse_vals,
                },
            },
            "payload": {
                "document_id": document_id,
                "chunk_index": idx,
                "text": chunk_text,
                "doc_metadata": metadata,
                "indexed_at": datetime.utcnow().isoformat(),
            },
        }
        points.append(point)

    # Upsert to Qdrant
    # client = QdrantClient(host="localhost", port=6333)
    # client.upsert(
    #     collection_name=collection_name,
    #     points=[PointStruct(**p) for p in points]
    # )

    logger.info(f"Successfully indexed {len(points)} chunks for document {document_id}")
    return points


# ============================================================================
# Example 2: Celery Task
# ============================================================================

# @celery_app.task(name="index_document_embeddings", queue="ai")
def index_document_embeddings_task(
    document_id: int,
    chunks: List[str],
    metadata: Dict[str, Any],
):
    """
    Celery task to generate and index document embeddings.

    This task would be called after document chunking is complete.
    """
    try:
        logger.info(f"Starting embedding task for document {document_id}")

        # Call the indexing function
        points = index_document_to_qdrant(
            document_id=document_id,
            text="",  # Full text if needed
            chunks=chunks,
            metadata=metadata,
        )

        return {
            "status": "success",
            "document_id": document_id,
            "chunks_indexed": len(points),
        }

    except Exception as e:
        logger.error(f"Failed to index document {document_id}: {e}", exc_info=True)
        raise


# ============================================================================
# Example 3: Multi-Granularity Indexing
# ============================================================================

def index_multi_granularity(
    document_id: int,
    summary: str,
    sections: List[str],
    microblocks: List[str],
    metadata: Dict[str, Any],
):
    """
    Index document at multiple granularities (summary, section, microblock).

    This enables searching at different levels of detail.
    """
    logger.info(f"Indexing document {document_id} at 3 granularities")

    # Initialize pipelines
    embedding_pipeline = EmbeddingPipeline()
    bm25_encoder = BM25Encoder()

    # Combine all texts for BM25 fitting
    all_texts = [summary] + sections + microblocks
    bm25_encoder.fit(all_texts)

    # Generate embeddings by granularity
    embeddings_by_size = embedding_pipeline.generate_embeddings_by_size({
        "summary": [summary],
        "section": sections,
        "microblock": microblocks,
    })

    # Generate sparse vectors
    sparse_summary = bm25_encoder.encode_to_qdrant_format(summary)
    sparse_sections = bm25_encoder.batch_encode_to_qdrant_format(sections)
    sparse_microblocks = bm25_encoder.batch_encode_to_qdrant_format(microblocks)

    # Create points for each granularity
    points = []

    # Summary point
    points.append({
        "id": f"{document_id}_summary",
        "vector": {
            "dense": embeddings_by_size["summary"][0].tolist(),
            "sparse": {
                "indices": sparse_summary[0],
                "values": sparse_summary[1],
            },
        },
        "payload": {
            "document_id": document_id,
            "granularity": "summary",
            "text": summary,
            **metadata,
        },
    })

    # Section points
    for idx, (dense, (sp_idx, sp_vals), text) in enumerate(
        zip(embeddings_by_size["section"], sparse_sections, sections)
    ):
        points.append({
            "id": f"{document_id}_section_{idx}",
            "vector": {
                "dense": dense.tolist(),
                "sparse": {"indices": sp_idx, "values": sp_vals},
            },
            "payload": {
                "document_id": document_id,
                "granularity": "section",
                "section_index": idx,
                "text": text,
                **metadata,
            },
        })

    # Microblock points
    for idx, (dense, (sp_idx, sp_vals), text) in enumerate(
        zip(embeddings_by_size["microblock"], sparse_microblocks, microblocks)
    ):
        points.append({
            "id": f"{document_id}_micro_{idx}",
            "vector": {
                "dense": dense.tolist(),
                "sparse": {"indices": sp_idx, "values": sp_vals},
            },
            "payload": {
                "document_id": document_id,
                "granularity": "microblock",
                "microblock_index": idx,
                "text": text,
                **metadata,
            },
        })

    logger.info(f"Created {len(points)} points across 3 granularities")
    return points


# ============================================================================
# Example 4: Semantic Search Query
# ============================================================================

def search_documents(
    query: str,
    top_k: int = 10,
    granularity: Optional[str] = None,
    collection_name: str = "legal_documents",
):
    """
    Search documents using hybrid dense + sparse search.

    Args:
        query: Search query text
        top_k: Number of results to return
        granularity: Optional filter by granularity (summary/section/microblock)
        collection_name: Qdrant collection name
    """
    logger.info(f"Searching for: '{query}' (top_k={top_k})")

    # Initialize pipelines
    embedding_pipeline = EmbeddingPipeline()
    bm25_encoder = BM25Encoder()

    # Note: BM25 encoder should be pre-fitted on your corpus
    # For demo purposes, we're showing the structure

    # Generate query vectors
    query_dense = embedding_pipeline.generate_single_embedding(query)
    query_sparse_idx, query_sparse_vals = bm25_encoder.encode_to_qdrant_format(query)

    # Prepare Qdrant search
    search_params = {
        "collection_name": collection_name,
        "query_vector": {
            "dense": query_dense.tolist(),
            "sparse": {
                "indices": query_sparse_idx,
                "values": query_sparse_vals,
            },
        },
        "limit": top_k,
    }

    # Add filters if needed
    if granularity:
        search_params["query_filter"] = {
            "must": [
                {
                    "key": "granularity",
                    "match": {"value": granularity}
                }
            ]
        }

    # Execute search
    # client = QdrantClient(host="localhost", port=6333)
    # results = client.search(**search_params)

    logger.info(f"Search completed")
    # return results


# ============================================================================
# Example 5: Batch Document Processing
# ============================================================================

def batch_process_documents(
    documents: List[Dict[str, Any]],
    batch_size: int = 32,
):
    """
    Process multiple documents in batches for efficiency.

    Args:
        documents: List of document dictionaries with 'id', 'chunks', 'metadata'
        batch_size: Batch size for embedding generation
    """
    logger.info(f"Batch processing {len(documents)} documents")

    # Initialize pipelines
    embedding_pipeline = EmbeddingPipeline(batch_size=batch_size)
    bm25_encoder = BM25Encoder()

    # Collect all chunks for BM25 fitting
    all_chunks = []
    for doc in documents:
        all_chunks.extend(doc["chunks"])

    # Fit BM25 once on entire corpus
    logger.info(f"Fitting BM25 on {len(all_chunks)} total chunks")
    bm25_encoder.fit(all_chunks)

    # Process each document
    all_points = []
    for doc in documents:
        chunks = doc["chunks"]

        # Generate embeddings in batches
        dense_embeddings = embedding_pipeline.generate_embeddings(chunks)

        # Generate sparse vectors
        sparse_vectors = bm25_encoder.batch_encode_to_qdrant_format(chunks)

        # Create points
        for idx, (chunk, dense, (sp_idx, sp_vals)) in enumerate(
            zip(chunks, dense_embeddings, sparse_vectors)
        ):
            point = {
                "id": f"{doc['id']}_{idx}",
                "vector": {
                    "dense": dense.tolist(),
                    "sparse": {"indices": sp_idx, "values": sp_vals},
                },
                "payload": {
                    "document_id": doc["id"],
                    "chunk_index": idx,
                    "text": chunk,
                    **doc["metadata"],
                },
            }
            all_points.append(point)

    logger.info(f"Created {len(all_points)} points for {len(documents)} documents")
    return all_points


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Example: Index a single document
    sample_chunks = [
        "This contract is entered into on January 1, 2024.",
        "The parties agree to the following terms and conditions.",
        "Payment shall be made within 30 days of invoice.",
        "Either party may terminate with 60 days written notice.",
    ]

    sample_metadata = {
        "doc_type": "contract",
        "parties": ["Company A", "Company B"],
        "date": "2024-01-01",
        "jurisdiction": "California",
    }

    # Index document
    points = index_document_to_qdrant(
        document_id=12345,
        text="",
        chunks=sample_chunks,
        metadata=sample_metadata,
    )

    print(f"Created {len(points)} Qdrant points")
    print(f"First point structure: {list(points[0].keys())}")
    print(f"Dense vector dimension: {len(points[0]['vector']['dense'])}")
    print(f"Sparse vector non-zero dims: {len(points[0]['vector']['sparse']['indices'])}")
