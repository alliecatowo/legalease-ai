# Database Reset Guide

Quick guide to reset the database and reseed with test data.

## Steps

```bash
# 1. Stop all services and remove volumes
make down-v

# 2. Start infrastructure
make up-infra

# 3. Wait for services (15 seconds)
sleep 15

# 4. Start backend
docker compose up -d backend

# 5. Wait for backend to be ready (10 seconds)
sleep 10

# 6. Run migrations
docker compose exec backend /app/.venv/bin/alembic upgrade head

# 7. Seed with real PDFs and test audio
docker compose exec backend python scripts/seed_with_real_pdfs.py --clear-db

# 8. Start all remaining services
docker compose up -d
```

## One-Liner (For Quick Reset)

```bash
make down-v && make up-infra && sleep 15 && docker compose up -d backend && sleep 10 && docker compose exec backend /app/.venv/bin/alembic upgrade head && docker compose exec backend python scripts/seed_with_real_pdfs.py --clear-db && docker compose up -d
```

## What Gets Created

- **Sample legal documents** with full processing (Docling, chunking, embeddings, Qdrant)
- **Test audio** (`testaudio.mp3`) with sample transcription
- **Clean database** with no stale search results
- **All services** running and ready

## Verify

After reset:
1. Open http://localhost:3000
2. Try searching - all results should link to valid documents
3. Check transcriptions page - should have test audio transcription
