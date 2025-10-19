"""Indexing API module - combines all indexing-related endpoints."""

from fastapi import APIRouter

# Import sub-routers
from app.api.v1.indexing.documents import router as documents_router
from app.api.v1.indexing.cases import router as cases_router
from app.api.v1.indexing.debug import router as debug_router

# Create main router that combines all indexing endpoints
router = APIRouter()

# Include all sub-routers
router.include_router(documents_router)
router.include_router(cases_router)
router.include_router(debug_router)
