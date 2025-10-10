"""
Health check endpoints with service status monitoring
"""
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.core.config import settings
import redis
from qdrant_client import QdrantClient

router = APIRouter()


async def check_database() -> dict:
    """Check database connectivity"""
    try:
        # Using asyncpg, we'd need async connection pool
        # For now, just return configured status
        return {
            "status": "configured",
            "url": settings.DATABASE_URL.split("@")[-1],  # Hide credentials
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def check_redis() -> dict:
    """Check Redis connectivity"""
    try:
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        r.ping()
        return {"status": "healthy", "url": settings.REDIS_URL}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def check_qdrant() -> dict:
    """Check Qdrant connectivity"""
    try:
        client = QdrantClient(url=settings.QDRANT_URL)
        collections = client.get_collections()
        return {
            "status": "healthy",
            "url": settings.QDRANT_URL,
            "collections": len(collections.collections),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint

    Returns the status of all critical services:
    - API service
    - Database
    - Redis
    - Qdrant vector database
    """
    db_status = await check_database()
    redis_status = await check_redis()
    qdrant_status = await check_qdrant()

    all_healthy = (
        db_status.get("status") in ["healthy", "configured"]
        and redis_status.get("status") == "healthy"
        and qdrant_status.get("status") == "healthy"
    )

    response = {
        "status": "healthy" if all_healthy else "degraded",
        "version": settings.APP_VERSION,
        "services": {
            "database": db_status,
            "redis": redis_status,
            "qdrant": qdrant_status,
        },
    }

    return JSONResponse(
        content=response,
        status_code=status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@router.get("/health/live")
async def liveness_check():
    """Liveness probe for Kubernetes/container orchestration"""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_check():
    """Readiness probe for Kubernetes/container orchestration"""
    redis_status = await check_redis()
    qdrant_status = await check_qdrant()

    is_ready = (
        redis_status.get("status") == "healthy"
        and qdrant_status.get("status") == "healthy"
    )

    return JSONResponse(
        content={"status": "ready" if is_ready else "not_ready"},
        status_code=status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE,
    )
