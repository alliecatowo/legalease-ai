#!/usr/bin/env python3
"""
Demo script for OpenSearch BM25 repositories.

This script demonstrates:
1. Initializing OpenSearch client
2. Creating indexes
3. Indexing sample documents
4. Performing BM25 searches
5. Cleaning up

Usage:
    python scripts/opensearch_demo.py
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.domain.evidence.value_objects.chunk import Chunk, ChunkType
from app.infrastructure.persistence.opensearch import (
    get_opensearch_client,
    close_opensearch_client,
    OpenSearchDocumentRepository,
    OpenSearchIndexManager,
)


async def main():
    """Run OpenSearch demo."""
    print("=" * 60)
    print("OpenSearch BM25 Repository Demo")
    print("=" * 60)
    print()

    try:
        # Initialize client
        print("1. Initializing OpenSearch client...")
        client = await get_opensearch_client()
        print("   ✓ Client initialized")
        print()

        # Check health
        print("2. Checking cluster health...")
        is_healthy = await client.health_check()
        print(f"   ✓ Cluster healthy: {is_healthy}")
        print()

        # Create indexes
        print("3. Creating indexes...")
        manager = OpenSearchIndexManager(client)
        results = await manager.create_all_indexes()
        for index_name, created in results.items():
            status = "Created" if created else "Already exists"
            print(f"   - {index_name}: {status}")
        print()

        # Check index health
        print("4. Checking index health...")
        health = await manager.check_index_health()
        for index_name, info in health.items():
            if info.get("exists"):
                print(f"   - {index_name}:")
                print(f"     Documents: {info['doc_count']}")
                print(f"     Size: {info['size_mb']} MB")
            else:
                print(f"   - {index_name}: Does not exist")
        print()

        # Create document repository
        print("5. Initializing document repository...")
        doc_repo = OpenSearchDocumentRepository(client)
        print("   ✓ Repository initialized")
        print()

        # Create sample data
        print("6. Indexing sample legal documents...")
        case_id = uuid4()
        document_id = uuid4()

        chunks = [
            Chunk(
                text="The plaintiff hereby alleges breach of contract by the defendant on March 15, 2024.",
                chunk_type=ChunkType.PARAGRAPH,
                position=0,
                metadata={"page": 1, "paragraph": 1}
            ),
            Chunk(
                text="The contract terms specified delivery within 30 days of order confirmation.",
                chunk_type=ChunkType.PARAGRAPH,
                position=1,
                metadata={"page": 1, "paragraph": 2}
            ),
            Chunk(
                text="The defendant failed to deliver the goods as specified, causing damages of $50,000.",
                chunk_type=ChunkType.PARAGRAPH,
                position=2,
                metadata={"page": 2, "paragraph": 1}
            ),
            Chunk(
                text="Pursuant to Section 365 of the Bankruptcy Code, the trustee may assume or reject executory contracts.",
                chunk_type=ChunkType.PARAGRAPH,
                position=3,
                metadata={"page": 3, "paragraph": 1}
            ),
        ]

        indexed = await doc_repo.index_document_chunks(document_id, case_id, chunks)
        print(f"   ✓ Indexed {indexed} chunks")

        # Refresh index to make documents searchable
        await client.refresh_index(doc_repo.index_name)
        print("   ✓ Refreshed index")
        print()

        # Perform searches
        print("7. Performing BM25 searches...")

        # Search 1: Contract terms
        print("   a) Search: 'contract terms'")
        results = await doc_repo.search_documents(
            query="contract terms",
            case_ids=[case_id],
            top_k=5
        )
        print(f"      Found {results.total} results in {results.took}ms")
        for i, result in enumerate(results.results, 1):
            preview = result.source['text'][:80] + "..."
            print(f"      {i}. Score: {result.score:.2f} - {preview}")
        print()

        # Search 2: Damages
        print("   b) Search: 'damages plaintiff'")
        results = await doc_repo.search_documents(
            query="damages plaintiff",
            case_ids=[case_id],
            top_k=5
        )
        print(f"      Found {results.total} results in {results.took}ms")
        for i, result in enumerate(results.results, 1):
            preview = result.source['text'][:80] + "..."
            print(f"      {i}. Score: {result.score:.2f} - {preview}")
        print()

        # Search 3: Bankruptcy Code citation
        print("   c) Search by citation: 'Section 365'")
        results = await doc_repo.search_by_citation(
            citation="Section 365",
            case_ids=[case_id],
            top_k=5
        )
        print(f"      Found {results.total} results in {results.took}ms")
        for i, result in enumerate(results.results, 1):
            preview = result.source['text'][:80] + "..."
            print(f"      {i}. Score: {result.score:.2f} - {preview}")
        print()

        # Get document stats
        print("8. Document statistics...")
        chunk_count = await doc_repo.get_document_chunk_count(document_id)
        print(f"   Total chunks indexed: {chunk_count}")
        print()

        # Cleanup
        print("9. Cleaning up...")
        deleted = await doc_repo.delete_document(document_id)
        print(f"   ✓ Deleted {deleted} chunks")
        print()

        print("=" * 60)
        print("Demo completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # Close client
        print("\nClosing OpenSearch client...")
        await close_opensearch_client()
        print("✓ Client closed")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
