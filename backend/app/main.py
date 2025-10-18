"""
LegalEase FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.api.v1 import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events for startup and shutdown"""
    # Startup
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"Database URL: {settings.DATABASE_URL.split('@')[-1]}")  # Hide credentials
    print(f"Redis URL: {settings.REDIS_URL}")
    print(f"Qdrant URL: {settings.QDRANT_URL}")
    print(f"MinIO Endpoint: {settings.MINIO_ENDPOINT}")

    yield

    # Shutdown
    print(f"Shutting down {settings.APP_NAME}")


# Create FastAPI app instance
app = FastAPI(
    title="LegalEase API",
    description="AI-powered legal document processing and case management system",
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.localhost",  # Production-like HTTPS frontend
        "http://app.localhost",   # HTTP fallback
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/api/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "legalease-backend",
            "version": settings.APP_VERSION,
        },
        status_code=200,
    )


# Include API v1 router
app.include_router(api_router, prefix="/api/v1", tags=["v1"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
