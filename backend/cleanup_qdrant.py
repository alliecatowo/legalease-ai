"""
Cleanup Qdrant Index - Remove Orphaned Vectors

This script removes vectors from Qdrant that reference deleted documents.
Run this after database changes to ensure search results are accurate.

Usage:
    uv run python cleanup_qdrant.py
"""

import asyncio
from sqlalchemy.orm import Session
from qdrant_client import QdrantClient

from app.core.config import settings
from app.core.database import get_db
from app.models.document import Document


async def cleanup_qdrant():
    """Remove vectors for documents that no longer exist in the database."""

    print("🧹 Starting Qdrant cleanup...")

    # Connect to Qdrant
    qdrant = QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT
    )

    # Get all valid document IDs from database
    db: Session = next(get_db())
    try:
        valid_doc_ids = set(doc.id for doc in db.query(Document.id).all())
        print(f"✅ Found {len(valid_doc_ids)} valid documents in database")
        print(f"   Valid IDs: {sorted(valid_doc_ids)}")
    finally:
        db.close()

    # Get all vectors from Qdrant
    collection_name = settings.QDRANT_COLLECTION_NAME

    try:
        # Scroll through all points in the collection
        offset = None
        total_vectors = 0
        orphaned_count = 0
        orphaned_ids = []

        while True:
            records, offset = qdrant.scroll(
                collection_name=collection_name,
                limit=100,
                offset=offset,
                with_payload=True
            )

            if not records:
                break

            for record in records:
                total_vectors += 1
                # Extract document_id from payload
                doc_id = record.payload.get("document_id")

                if doc_id and doc_id not in valid_doc_ids:
                    orphaned_count += 1
                    orphaned_ids.append((record.id, doc_id))
                    print(f"   ⚠️  Found orphaned vector: point_id={record.id}, document_id={doc_id}")

            if offset is None:
                break

        print(f"\n📊 Scan complete:")
        print(f"   Total vectors in Qdrant: {total_vectors}")
        print(f"   Orphaned vectors found: {orphaned_count}")

        if orphaned_count > 0:
            print(f"\n🗑️  Deleting {orphaned_count} orphaned vectors...")

            # Delete orphaned points in batches
            batch_size = 100
            for i in range(0, len(orphaned_ids), batch_size):
                batch = orphaned_ids[i:i+batch_size]
                point_ids = [point_id for point_id, _ in batch]

                qdrant.delete(
                    collection_name=collection_name,
                    points_selector=point_ids
                )
                print(f"   Deleted batch {i//batch_size + 1} ({len(point_ids)} vectors)")

            print(f"\n✅ Cleanup complete! Deleted {orphaned_count} orphaned vectors.")
        else:
            print("\n✅ No orphaned vectors found. Qdrant index is clean!")

        # Verify final state
        collection_info = qdrant.get_collection(collection_name)
        print(f"\n📈 Final Qdrant state:")
        print(f"   Vectors count: {collection_info.vectors_count}")
        print(f"   Points count: {collection_info.points_count}")

    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(cleanup_qdrant())
