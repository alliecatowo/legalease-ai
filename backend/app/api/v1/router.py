"""API v1 Router."""
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.v1 import auth, cases, documents, indexing, transcriptions

api_router = APIRouter()
protected_router = APIRouter(dependencies=[Depends(get_current_user)])

protected_router.include_router(cases.router, prefix="/cases", tags=["cases"])
protected_router.include_router(documents.router, tags=["documents"])
protected_router.include_router(indexing.router, prefix="/index", tags=["indexing"])
protected_router.include_router(transcriptions.router, tags=["transcriptions"])

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(protected_router)


@api_router.get("/health")
async def v1_health():
    """API v1 health check"""
    return {"status": "healthy", "version": "v1"}
