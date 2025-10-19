"""Transcription API module - combines all transcription-related endpoints."""

from fastapi import APIRouter

# Import sub-routers
from app.api.v1.transcriptions.endpoints import router as endpoints_router
from app.api.v1.transcriptions.streaming import router as streaming_router
from app.api.v1.transcriptions.exports import router as exports_router
from app.api.v1.transcriptions.summarization import router as summarization_router
from app.api.v1.transcriptions.key_moments import router as key_moments_router

# Create main router that combines all transcription endpoints
router = APIRouter()

# Include all sub-routers
router.include_router(endpoints_router)
router.include_router(streaming_router)
router.include_router(exports_router)
router.include_router(summarization_router)
router.include_router(key_moments_router)
