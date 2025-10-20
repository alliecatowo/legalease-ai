#!/usr/bin/env python
"""Initialize all infrastructure components."""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.config import settings


async def check_postgres():
    """Check PostgreSQL connection."""
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        engine = create_async_engine(settings.DATABASE_URL)
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return True
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False


async def check_redis():
    """Check Redis connection."""
    try:
        import redis.asyncio as redis
        client = redis.from_url(settings.REDIS_URL)
        await client.ping()
        if hasattr(client, "aclose"):
            await client.aclose()
        else:
            await client.close()
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False


async def init_opensearch():
    """Initialize OpenSearch indexes."""
    try:
        from opensearchpy import AsyncOpenSearch

        client = AsyncOpenSearch(
            hosts=[settings.OPENSEARCH_URL],
            use_ssl=False,
            verify_certs=False,
        )

        # Check connection
        info = await client.info()
        print(f"  Connected to OpenSearch {info['version']['number']}")

        # Create indexes
        indexes = {
            "legalease_documents": {
                "mappings": {
                    "properties": {
                        "case_id": {"type": "keyword"},
                        "document_id": {"type": "keyword"},
                        "chunk_id": {"type": "keyword"},
                        "content": {"type": "text", "analyzer": "standard"},
                        "document_type": {"type": "keyword"},
                        "page_number": {"type": "integer"},
                        "metadata": {"type": "object"},
                        "created_at": {"type": "date"},
                    }
                },
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                }
            },
            "legalease_transcripts": {
                "mappings": {
                    "properties": {
                        "case_id": {"type": "keyword"},
                        "transcript_id": {"type": "keyword"},
                        "segment_id": {"type": "keyword"},
                        "text": {"type": "text", "analyzer": "standard"},
                        "speaker": {"type": "keyword"},
                        "start_time": {"type": "float"},
                        "end_time": {"type": "float"},
                        "metadata": {"type": "object"},
                        "created_at": {"type": "date"},
                    }
                },
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                }
            },
        }

        for index_name, config in indexes.items():
            if await client.indices.exists(index=index_name):
                print(f"  Index '{index_name}' already exists, skipping")
            else:
                await client.indices.create(index=index_name, body=config)
                print(f"  ✓ Created index '{index_name}'")

        if hasattr(client, "aclose"):
            await client.aclose()
        else:
            await client.close()
        return True
    except Exception as e:
        print(f"❌ OpenSearch initialization failed: {e}")
        return False


async def init_qdrant():
    """Initialize Qdrant collections."""
    try:
        from qdrant_client import AsyncQdrantClient
        from qdrant_client.models import Distance, VectorParams

        client = AsyncQdrantClient(url=settings.QDRANT_URL)

        # Check connection
        collections = await client.get_collections()
        print(f"  Connected to Qdrant ({len(collections.collections)} existing collections)")

        # Create collections
        collections_config = {
            "legalease_documents": {
                "size": 384,  # fastembed default
                "distance": Distance.COSINE,
            },
            "legalease_transcripts": {
                "size": 384,
                "distance": Distance.COSINE,
            },
        }

        existing = {c.name for c in collections.collections}

        for collection_name, config in collections_config.items():
            if collection_name in existing:
                print(f"  Collection '{collection_name}' already exists, skipping")
            else:
                await client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=config["size"],
                        distance=config["distance"],
                    )
                )
                print(f"  ✓ Created collection '{collection_name}'")

        await client.close()
        return True
    except Exception as e:
        print(f"❌ Qdrant initialization failed: {e}")
        return False


async def init_neo4j():
    """Initialize Neo4j schema."""
    try:
        from neo4j import AsyncGraphDatabase

        driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )

        async with driver.session() as session:
            # Check connection
            result = await session.run("RETURN 1 as num")
            await result.consume()
            print("  Connected to Neo4j")

            # Create constraints and indexes
            constraints = [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Case) REQUIRE c.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE",
            ]

            indexes = [
                "CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.name)",
                "CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.case_id)",
                "CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.name)",
                "CREATE INDEX IF NOT EXISTS FOR (o:Organization) ON (o.name)",
            ]

            for constraint in constraints:
                await session.run(constraint)
            print(f"  ✓ Created {len(constraints)} constraints")

            for index in indexes:
                await session.run(index)
            print(f"  ✓ Created {len(indexes)} indexes")

        await driver.close()
        return True
    except Exception as e:
        print(f"❌ Neo4j initialization failed: {e}")
        return False


async def main():
    """Main initialization flow."""
    print("🚀 Initializing LegalEase infrastructure...")
    print("=" * 60)

    # 1. Check prerequisites
    print("\n1️⃣  Checking database connections...")
    postgres_ok = await check_postgres()
    if not postgres_ok:
        print("⚠️  PostgreSQL is not available. Please ensure it's running.")
        print("   Run: docker-compose up -d postgres")
        return 1
    print("  ✓ PostgreSQL is ready")

    redis_ok = await check_redis()
    if not redis_ok:
        print("⚠️  Redis is not available. Please ensure it's running.")
        print("   Run: docker-compose up -d redis")
        return 1
    print("  ✓ Redis is ready")

    # 2. OpenSearch indexes
    print("\n2️⃣  Creating OpenSearch indexes...")
    if not await init_opensearch():
        print("⚠️  OpenSearch initialization failed")
        return 1
    print("  ✅ OpenSearch indexes created")

    # 3. Qdrant collections
    print("\n3️⃣  Creating Qdrant collections...")
    if not await init_qdrant():
        print("⚠️  Qdrant initialization failed")
        return 1
    print("  ✅ Qdrant collections created")

    # 4. Neo4j schema
    print("\n4️⃣  Creating Neo4j constraints and indexes...")
    if not await init_neo4j():
        print("⚠️  Neo4j initialization failed")
        return 1
    print("  ✅ Neo4j schema created")

    print("\n" + "=" * 60)
    print("🎉 Infrastructure initialization complete!")
    print("\nNext steps:")
    print("  1. Run migrations: mise run migrate")
    print("  2. Start the API: mise run dev")
    print("  3. Run tests: mise run test:integration")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
