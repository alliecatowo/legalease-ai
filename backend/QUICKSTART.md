# LegalEase Backend - Quick Start Guide

## Start the Application

```bash
cd /home/Allie/develop/legalease/backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Verify It's Working

The server should start with output:
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## Access the API

- **API Root**: http://localhost:8000/
- **Health Check**: http://localhost:8000/health
- **API Docs (Swagger)**: http://localhost:8000/api/docs
- **API Docs (ReDoc)**: http://localhost:8000/api/redoc

## Core Files

### Configuration
- `.env` - Environment variables
- `app/core/config.py` - Settings class

### Application Entry Point
- `app/main.py` - FastAPI app with CORS, lifespan events

### API Structure
- `app/api/v1/__init__.py` - Router aggregator
- `app/api/v1/health.py` - Health checks
- `app/api/v1/cases.py` - Case management
- `app/api/v1/documents.py` - Document handling
- `app/api/v1/search.py` - Search functionality
- `app/api/v1/transcriptions.py` - Transcriptions

## Key Features

1. **CORS Middleware** - Configured for localhost:3000 and localhost:5173
2. **Health Checks** - `/health`, `/api/v1/health`, `/api/v1/health/live`, `/api/v1/health/ready`
3. **Startup/Shutdown Events** - Lifespan context manager for DB connections
4. **API v1 Router** - Mounted at `/api/v1` with all endpoints
5. **Environment Config** - Pydantic Settings loading from `.env`

## Test Structure

```bash
uv run python test_startup.py
```

This validates:
- Configuration loading
- FastAPI app creation
- API routes registration
- Middleware setup

## Next Steps

The application is ready to run. Services (PostgreSQL, Redis, Qdrant, MinIO) will be connected when needed through lazy initialization.

For detailed information, see `SETUP_SUMMARY.md`.
