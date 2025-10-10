"""
API v1 Router
"""
from fastapi import APIRouter
from app.api.v1 import cases, documents, indexing, transcriptions

api_router = APIRouter()

# Include sub-routers
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(indexing.router, prefix="/index", tags=["indexing"])
api_router.include_router(transcriptions.router, tags=["transcriptions"])


@api_router.get("/health")
async def v1_health():
    """API v1 health check"""
    return {"status": "healthy", "version": "v1"}
