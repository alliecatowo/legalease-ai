"""Health check endpoints for monitoring infrastructure."""
from fastapi import APIRouter, status
from pydantic import BaseModel
from typing import Dict
import asyncio

router = APIRouter(tags=["health"])


class ServiceHealth(BaseModel):
    """Individual service health status."""
    status: str
    message: str = ""
    latency_ms: float | None = None


class HealthResponse(BaseModel):
    """Overall health check response."""
    status: str
    services: Dict[str, ServiceHealth]


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}


@router.get("/health/detailed", response_model=HealthResponse)
async def detailed_health_check():
    """
    Detailed health check for all services.

    Returns the health status of:
    - PostgreSQL
    - Redis
    - Qdrant
    - OpenSearch
    - Neo4j
    - Ollama (optional)
    - Temporal (optional)
    """
    # Run all checks in parallel
    services = await asyncio.gather(
        check_postgres(),
        check_redis(),
        check_qdrant(),
        check_opensearch(),
        check_neo4j(),
        check_ollama(),
        check_temporal(),
        return_exceptions=True,
    )

    health = {
        "postgres": services[0] if not isinstance(services[0], Exception) else ServiceHealth(status="unhealthy", message=str(services[0])),
        "redis": services[1] if not isinstance(services[1], Exception) else ServiceHealth(status="unhealthy", message=str(services[1])),
        "qdrant": services[2] if not isinstance(services[2], Exception) else ServiceHealth(status="unhealthy", message=str(services[2])),
        "opensearch": services[3] if not isinstance(services[3], Exception) else ServiceHealth(status="unhealthy", message=str(services[3])),
        "neo4j": services[4] if not isinstance(services[4], Exception) else ServiceHealth(status="unhealthy", message=str(services[4])),
        "ollama": services[5] if not isinstance(services[5], Exception) else ServiceHealth(status="unhealthy", message=str(services[5])),
        "temporal": services[6] if not isinstance(services[6], Exception) else ServiceHealth(status="unhealthy", message=str(services[6])),
    }

    # Determine overall status
    all_healthy = all(
        svc.status == "healthy"
        for key, svc in health.items()
        if key not in ["ollama", "temporal"]  # Optional services
    )

    overall_status = "healthy" if all_healthy else "degraded"

    return HealthResponse(status=overall_status, services=health)


async def check_postgres() -> ServiceHealth:
    """Check PostgreSQL connection."""
    import time
    from sqlalchemy.ext.asyncio import create_async_engine
    from app.core.config import settings

    try:
        start = time.time()
        engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)

        async with engine.begin() as conn:
            await conn.execute("SELECT 1")

        await engine.dispose()
        latency = (time.time() - start) * 1000

        return ServiceHealth(
            status="healthy",
            message="Connected",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        return ServiceHealth(
            status="unhealthy",
            message=f"Connection failed: {str(e)[:100]}",
        )


async def check_redis() -> ServiceHealth:
    """Check Redis connection."""
    import time
    import redis.asyncio as redis
    from app.core.config import settings

    try:
        start = time.time()
        client = redis.from_url(settings.REDIS_URL)
        await client.ping()
        await client.close()
        latency = (time.time() - start) * 1000

        return ServiceHealth(
            status="healthy",
            message="Connected",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        return ServiceHealth(
            status="unhealthy",
            message=f"Connection failed: {str(e)[:100]}",
        )


async def check_qdrant() -> ServiceHealth:
    """Check Qdrant connection."""
    import time
    from qdrant_client import AsyncQdrantClient
    from app.core.config import settings

    try:
        start = time.time()
        client = AsyncQdrantClient(url=settings.QDRANT_URL)
        collections = await client.get_collections()
        await client.close()
        latency = (time.time() - start) * 1000

        return ServiceHealth(
            status="healthy",
            message=f"Connected ({len(collections.collections)} collections)",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        return ServiceHealth(
            status="unhealthy",
            message=f"Connection failed: {str(e)[:100]}",
        )


async def check_opensearch() -> ServiceHealth:
    """Check OpenSearch connection."""
    import time
    from opensearchpy import AsyncOpenSearch
    from app.core.config import settings

    try:
        start = time.time()
        client = AsyncOpenSearch(
            hosts=[settings.OPENSEARCH_URL],
            use_ssl=False,
            verify_certs=False,
        )

        info = await client.info()
        await client.close()
        latency = (time.time() - start) * 1000

        return ServiceHealth(
            status="healthy",
            message=f"Connected (v{info['version']['number']})",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        return ServiceHealth(
            status="unhealthy",
            message=f"Connection failed: {str(e)[:100]}",
        )


async def check_neo4j() -> ServiceHealth:
    """Check Neo4j connection."""
    import time
    from neo4j import AsyncGraphDatabase
    from app.core.config import settings

    try:
        start = time.time()
        driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )

        async with driver.session() as session:
            result = await session.run("RETURN 1 as num")
            await result.consume()

        await driver.close()
        latency = (time.time() - start) * 1000

        return ServiceHealth(
            status="healthy",
            message="Connected",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        return ServiceHealth(
            status="unhealthy",
            message=f"Connection failed: {str(e)[:100]}",
        )


async def check_ollama() -> ServiceHealth:
    """Check Ollama connection (optional)."""
    import time
    import httpx
    from app.core.config import settings

    try:
        start = time.time()
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()

        latency = (time.time() - start) * 1000

        return ServiceHealth(
            status="healthy",
            message="Connected",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        return ServiceHealth(
            status="degraded",
            message=f"Connection failed: {str(e)[:100]}",
        )


async def check_temporal() -> ServiceHealth:
    """Check Temporal connection (optional)."""
    import time
    from app.core.config import settings

    try:
        # Import here to avoid issues if Temporal not configured
        from temporalio.client import Client

        start = time.time()
        client = await Client.connect(
            settings.TEMPORAL_HOST,
            namespace=settings.TEMPORAL_NAMESPACE,
        )

        # Simple connection test
        await client.list_workflows()

        latency = (time.time() - start) * 1000

        return ServiceHealth(
            status="healthy",
            message="Connected",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        return ServiceHealth(
            status="degraded",
            message=f"Connection failed: {str(e)[:100]}",
        )


@router.get("/health/readiness")
async def readiness_check():
    """
    Kubernetes readiness probe.

    Returns 200 if the service is ready to accept traffic.
    """
    # Check critical services only
    checks = await asyncio.gather(
        check_postgres(),
        check_redis(),
        return_exceptions=True,
    )

    postgres_ok = not isinstance(checks[0], Exception) and checks[0].status == "healthy"
    redis_ok = not isinstance(checks[1], Exception) and checks[1].status == "healthy"

    if postgres_ok and redis_ok:
        return {"status": "ready"}
    else:
        return {"status": "not ready"}, 503


@router.get("/health/liveness")
async def liveness_check():
    """
    Kubernetes liveness probe.

    Returns 200 if the service is alive (no deadlocks, etc).
    """
    return {"status": "alive"}
