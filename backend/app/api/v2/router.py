"""
API v2 Router.

Aggregates all v2 API routes and WebSocket endpoints into a single router
for registration with the FastAPI application.
"""

from fastapi import APIRouter

from app.api.v2.routes import research, evidence, graph
from app.api.v2.websockets import research_stream


# Create main API v2 router
api_router = APIRouter()

# Include REST endpoints
api_router.include_router(
    research.router,
    prefix="/research",
    tags=["research"],
)

api_router.include_router(
    evidence.router,
    tags=["evidence"],
)

api_router.include_router(
    graph.router,
    tags=["knowledge-graph"],
)

# Include WebSocket endpoints
api_router.include_router(
    research_stream.router,
    tags=["websockets"],
)
