"""
API v1 Router
Aggregates all v1 endpoints
"""
from fastapi import APIRouter

api_router = APIRouter()

# Import and include sub-routers
try:
    from app.api.v1 import health
    api_router.include_router(health.router, tags=["health"])
except ImportError as e:
    print(f"Warning: Could not import health router: {e}")

try:
    from app.api.v1 import cases
    api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
except ImportError as e:
    print(f"Warning: Could not import cases router: {e}")

try:
    from app.api.v1 import documents
    api_router.include_router(documents.router, tags=["documents"])
except ImportError as e:
    print(f"Warning: Could not import documents router: {e}")

try:
    from app.api.v1 import search
    api_router.include_router(search.router, prefix="/search", tags=["search"])
except ImportError as e:
    print(f"Warning: Could not import search router: {e}")

try:
    from app.api.v1 import transcriptions
    api_router.include_router(transcriptions.router, tags=["transcriptions"])
except ImportError as e:
    print(f"Warning: Could not import transcriptions router: {e}")
