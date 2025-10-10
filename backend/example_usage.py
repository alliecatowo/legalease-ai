"""
Example usage of the Qdrant vector database integration.

This file demonstrates how to:
1. Initialize the Qdrant collection
2. Index document chunks
3. Perform hybrid search
"""

import asyncio
from app.core.qdrant import create_collection, upsert_points, get_collection_info
from app.services.search_service import get_search_engine
from app.schemas.search import HybridSearchRequest, DocumentChunk
from qdrant_client.models import PointStruct, NamedVector, SparseVector


async def example_setup_collection():
    """Example: Create the Qdrant collection."""
    print("Creating Qdrant collection...")

    create_collection(
        summary_vector_size=384,  # all-MiniLM-L6-v2 produces 384-dim vectors
        section_vector_size=384,
        microblock_vector_size=384,
        recreate=False,  # Set to True to recreate existing collection
    )

    # Get collection info
    info = get_collection_info()
    print(f"Collection info: {info}")


async def example_index_documents():
    """Example: Index document chunks into Qdrant."""
    from sentence_transformers import SentenceTransformer

    print("\nIndexing sample documents...")

    # Initialize embedding model
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    # Sample legal document chunks
    sample_chunks = [
        {
            "chunk_id": 1,
            "document_id": 1,
            "case_id": 1,
            "text": "The defendant breached the contract by failing to deliver goods on the agreed date of January 15, 2024.",
            "chunk_type": "section",
            "position": 1,
            "page_number": 3,
        },
        {
            "chunk_id": 2,
            "document_id": 1,
            "case_id": 1,
            "text": "Plaintiff seeks damages in the amount of $50,000 for breach of contract and loss of business opportunity.",
            "chunk_type": "section",
            "position": 2,
            "page_number": 4,
        },
        {
            "chunk_id": 3,
            "document_id": 2,
            "case_id": 1,
            "text": "Employment discrimination case: Employee was wrongfully terminated based on age in violation of federal law.",
            "chunk_type": "summary",
            "position": 0,
            "page_number": 1,
        },
    ]

    # Create points for Qdrant
    points = []
    for chunk in sample_chunks:
        # Generate embedding
        embedding = model.encode(chunk["text"]).tolist()

        # Create simple BM25 sparse vector (token counts)
        tokens = chunk["text"].lower().split()
        token_counts = {}
        for token in tokens:
            token_counts[token] = token_counts.get(token, 0) + 1

        sparse_indices = [hash(token) % (2**31) for token in token_counts.keys()]
        sparse_values = [float(count) for count in token_counts.values()]

        # Create point
        point = PointStruct(
            id=chunk["chunk_id"],
            vector={
                "summary": embedding,
                "section": embedding,
                "microblock": embedding,
                "bm25": SparseVector(indices=sparse_indices, values=sparse_values),
            },
            payload={
                "text": chunk["text"],
                "document_id": chunk["document_id"],
                "case_id": chunk["case_id"],
                "chunk_type": chunk["chunk_type"],
                "position": chunk["position"],
                "page_number": chunk["page_number"],
            }
        )
        points.append(point)

    # Upsert to Qdrant
    upsert_points(points)
    print(f"Indexed {len(points)} document chunks")


async def example_hybrid_search():
    """Example: Perform hybrid search."""
    print("\nPerforming hybrid search...")

    # Get search engine
    search_engine = get_search_engine()

    # Create search request
    request = HybridSearchRequest(
        query="contract breach damages",
        case_ids=[1],  # Filter by case
        top_k=5,
        fusion_method="rrf",
        rrf_k=60,
        use_bm25=True,
        use_dense=True,
    )

    # Execute search
    response = search_engine.search(request)

    # Display results
    print(f"\nSearch results for: '{request.query}'")
    print(f"Total results: {response.total_results}")
    print(f"Search time: {response.search_metadata['search_time_ms']}ms")
    print(f"Vectors used: {response.search_metadata['vectors_used']}\n")

    for i, result in enumerate(response.results, 1):
        print(f"{i}. Score: {result.score:.4f} | Type: {result.vector_type}")
        print(f"   Text: {result.text[:100]}...")
        print(f"   Metadata: {result.metadata}")
        if result.highlights:
            print(f"   Highlights: {result.highlights[:2]}")
        print()


async def example_filter_search():
    """Example: Search with filters."""
    print("\nPerforming filtered search...")

    search_engine = get_search_engine()

    # Search only in summaries
    request = HybridSearchRequest(
        query="employment discrimination wrongful termination",
        chunk_types=["summary"],  # Only search summaries
        top_k=3,
        use_bm25=True,
        use_dense=True,
    )

    response = search_engine.search(request)

    print(f"Found {response.total_results} summary chunks")
    for result in response.results:
        print(f"- {result.text[:80]}... (score: {result.score:.4f})")


async def main():
    """Run all examples."""
    print("=" * 80)
    print("Qdrant Vector Database Integration - Example Usage")
    print("=" * 80)

    try:
        # 1. Setup collection
        await example_setup_collection()

        # 2. Index documents
        await example_index_documents()

        # 3. Perform searches
        await example_hybrid_search()
        await example_filter_search()

        print("\n" + "=" * 80)
        print("Examples completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
