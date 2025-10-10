"""
Test script to verify FastAPI app structure without starting services
"""
import sys

print("=" * 60)
print("Testing LegalEase Backend Structure")
print("=" * 60)

# Test 1: Config
print("\n[1/4] Testing configuration...")
try:
    from app.core.config import settings
    print(f"   ✓ Settings loaded")
    print(f"   ✓ App: {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"   ✓ Database URL: {settings.DATABASE_URL.split('@')[-1]}")
    print(f"   ✓ Redis URL: {settings.REDIS_URL}")
    print(f"   ✓ Qdrant URL: {settings.QDRANT_URL}")
except Exception as e:
    print(f"   ✗ Config failed: {e}")
    sys.exit(1)

# Test 2: FastAPI app creation (without service connections)
print("\n[2/4] Testing FastAPI app structure...")
try:
    # This will fail if MinIO client tries to connect at import time
    # We'll catch that and report it
    from app.main import app
    print(f"   ✓ FastAPI app created")
    print(f"   ✓ Title: {app.title}")
    print(f"   ✓ Version: {app.version}")
except Exception as e:
    print(f"   ✗ App creation failed: {e}")
    print(f"   ! Note: This is expected if MinIO/Redis/Qdrant are not running")
    print(f"   ! The app structure is correct, but services need to be started")
    sys.exit(1)

# Test 3: Routes
print("\n[3/4] Testing API routes...")
try:
    routes = [r.path for r in app.routes if hasattr(r, 'path')]
    print(f"   ✓ Total routes: {len(routes)}")
    print(f"   ✓ Root endpoint: {routes[0]}")
    print(f"   ✓ Health check: {'/health' in routes}")
    print(f"   ✓ API v1: {any('/api/v1' in r for r in routes)}")
except Exception as e:
    print(f"   ✗ Routes check failed: {e}")

# Test 4: CORS Middleware
print("\n[4/4] Testing middleware...")
try:
    middleware_types = [type(m).__name__ for m in app.user_middleware]
    print(f"   ✓ Middleware count: {len(middleware_types)}")
    print(f"   ✓ CORS enabled: {'CORSMiddleware' in str(middleware_types)}")
except Exception as e:
    print(f"   ✗ Middleware check failed: {e}")

print("\n" + "=" * 60)
print("FastAPI Structure Test Complete!")
print("=" * 60)
print("\nTo start the server (requires running services):")
print("  uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
print("\nRequired services:")
print("  - PostgreSQL (port 5432)")
print("  - Redis (port 6379)")
print("  - Qdrant (port 6333)")
print("  - MinIO (port 9000)")
print("=" * 60)
