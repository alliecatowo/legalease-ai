#!/usr/bin/env python3
"""
Initialize Qdrant collections for LegalEase.

This script creates all necessary Qdrant collections with proper schemas
for documents, transcripts, communications, and findings.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.infrastructure.persistence.qdrant import (
    CollectionManager,
    get_qdrant_client,
    close_qdrant_client,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Initialize all Qdrant collections."""
    logger.info("Starting Qdrant collection initialization...")

    try:
        # Check Qdrant health
        client = get_qdrant_client()
        is_healthy = await client.health_check()

        if not is_healthy:
            logger.error("Qdrant server is not healthy. Please check the connection.")
            return 1

        logger.info("Qdrant server is healthy")

        # Create all collections
        recreate = "--recreate" in sys.argv
        if recreate:
            logger.warning("Recreating all collections (existing data will be lost)")

        await CollectionManager.create_all_collections(recreate=recreate)

        # Print collection stats
        logger.info("\n" + "=" * 60)
        logger.info("Collection Statistics:")
        logger.info("=" * 60)

        stats = await CollectionManager.get_collection_stats()
        for collection_name, collection_stats in stats.items():
            logger.info(f"\n{collection_name}:")
            if collection_stats.get("exists") is False:
                logger.info("  Status: Does not exist")
            elif "error" in collection_stats:
                logger.error(f"  Error: {collection_stats['error']}")
            else:
                logger.info(f"  Status: {collection_stats.get('status', 'unknown')}")
                logger.info(f"  Points: {collection_stats.get('points_count', 0)}")
                logger.info(
                    f"  Dense vectors: {', '.join(collection_stats.get('vectors', []))}"
                )
                logger.info(
                    f"  Sparse vectors: {', '.join(collection_stats.get('sparse_vectors', []))}"
                )

        logger.info("\n" + "=" * 60)
        logger.info("Qdrant collection initialization completed successfully!")

        return 0

    except Exception as e:
        logger.error(f"Error initializing collections: {e}", exc_info=True)
        return 1

    finally:
        await close_qdrant_client()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
