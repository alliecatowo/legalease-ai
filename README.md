# LegalEase

LegalEase is a self-hosted workspace for legal teams to organise case material, process documents, and run fast hybrid search without sending data to external services. The platform couples a FastAPI + Celery backend with a Nuxt 4 dashboard and ships sensible defaults for MinIO, PostgreSQL, Qdrant, Redis, Neo4j, and Ollama in Docker.

- Case-centric document intake with Docling-based parsing, OCR, and hierarchical chunking
- Hybrid retrieval that fuses BM25 and dense vectors stored in Qdrant
- Audio and video transcription with optional WhisperX GPU support and fallback heuristics
- Transcript summarisation, key moments, and speaker statistics generated via local Ollama models
- Evidence intake helpers for Cellebrite/AXIOM style forensic exports
- Everything runs locally; network access is only needed for pulling container images or AI models

---

## Architecture Overview

| Component | Role | Notes |
|-----------|------|-------|
| `frontend/` (Nuxt 4) | Dashboard, upload flows, search UI, transcript review | Talks to FastAPI via `NUXT_PUBLIC_API_BASE` |
| `backend/` (FastAPI) | REST API, Celery task orchestration, database models | Uses SQLAlchemy, async DB engine, and shared services |
| Celery worker | Long-running jobs (document processing, transcription, summarisation) | GPU-aware when available |
| PostgreSQL | Primary relational store | See `docker-compose.yml` |
| Qdrant | Vector search (document chunks + transcript segments) | Hybrid API v1.10+ |
| MinIO | Object storage for originals, derived artefacts, and page images | Buckets created automatically |
| Redis | Caching + Celery broker/result backend |  |
| Ollama | Local LLM inference for summaries and tagging | Default model configurable |
| Optional: Neo4j | Knowledge graph scaffolding (currently experimental) | Disabled logic does not block core workflows |

---

## Quick Start (Docker Compose)

### 1. Requirements

- Docker Engine 24+ and Docker Compose v2
- `make` (or translate commands to `docker compose`)
- 16 GB RAM minimum for the full stack; GPU strongly recommended for WhisperX
- Optional: Hugging Face token (`HF_TOKEN`) if you want Pyannote diarisation accuracy

### 2. Clone and prepare configuration

```bash
git clone https://github.com/AlliecatOwO/legalease-ai.git
cd legalease-ai

cp .env.example .env                # sets HF_TOKEN/FORENSIC_EXPORTS_PATH placeholders
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Edit the newly created files:

- Replace `HF_TOKEN=` with your token if you plan to use Pyannote-based speaker diarisation (optional).
- Point `FORENSIC_EXPORTS_PATH` to a directory containing Cellebrite/AXIOM exports if you intend to scan evidence.
- Adjust database passwords or port mappings if they conflict with existing services.

### 3. Start infrastructure, run migrations, and pull LLMs

```bash
make setup         # starts infra containers, runs alembic, pulls default Ollama models
make up            # launches backend, worker, beat, and frontend containers
```

The stack exposes:

- Frontend: http://localhost:3000
- FastAPI (OpenAPI docs): http://localhost:8000/api/docs
- MinIO console: http://localhost:9001 (legalease / legalease_dev_secret)
- Qdrant dashboard (if enabled): http://localhost:6333/dashboard
- Neo4j Browser: http://localhost:7474 (neo4j / legalease_dev) — optional

Monitor logs with `docker compose logs -f backend worker frontend`.

### 4. Shut down

```bash
make down          # stop containers (data persisted)
make down-v        # stop and clear volumes (destructive)
```

---

## Useful Make Targets

| Command | Description |
|---------|-------------|
| `make up` / `make down` | Start or stop the full stack |
| `make up-infra` | Start only databases, MinIO, Qdrant, Ollama |
| `make migrate` | Apply latest Alembic migrations |
| `make logs-backend` / `make logs-worker` | Follow service-specific logs |
| `make test` | Run backend pytest suite inside the container |
| `make ollama-pull-<model>` | Download an additional Ollama model |
| `make restart-backend` | Restart a single container without touching others |

Run `make help` for the full catalogue.

---

## Core Workflows

### Document Processing & Search

1. Create a case via the dashboard or `POST /api/v1/cases`.
2. Upload PDFs, DOCX, text, or images. Files are stored in MinIO and queued for processing.
3. Docling extracts structure, optionally runs OCR, and produces hierarchical chunks (`summary`, `section`, `microblock`).
4. Dense embeddings (FastEmbed) and BM25 sparse vectors are written to Qdrant; chunk metadata with bounding boxes lives in PostgreSQL.
5. The search API performs multi-vector hybrid retrieval with optional reranking disabled by default.

### Transcription & Analysis

- Audio/video uploads hit `POST /api/v1/cases/{case_id}/transcriptions`.
- The worker attempts WhisperX first (GPU recommended). If WhisperX is not installed, it falls back to OpenAI Whisper via `OPENAI_API_KEY`, or uses heuristic diarisation when Pyannote is unavailable.
- Summaries, key moments, timelines, speaker stats, and action items are generated asynchronously through Ollama (`settings.OLLAMA_MODEL_SUMMARIZATION`).
- Transcript downloads support DOCX/SRT/VTT/TXT/JSON formats.

### Forensic Export Intake

- Mount forensic exports into the worker (`FORENSIC_EXPORTS_PATH` in `.env`).
- Use `POST /api/v1/cases/{case_id}/forensic-exports/scan` to catalogue Cellebrite/AXIOM style directories. The service parses `ExportSummary.json` and exposes file listings via the API.

---

## Feature Maturity

| Area | Status |
|------|--------|
| Case management, document upload, hybrid search | ✅ Production ready |
| Transcription + summarisation | ✅ Functional; WhisperX and Pyannote optional |
| Forensic export ingestion | ✅ Functional |
| Entity extraction & knowledge graph | ⚠️ Experimental — models wired but schema is still evolving |
| Analytics dashboards (search volume, etc.) | ⚠️ Prototype UI with placeholder data |

Contributions that harden the experimental areas are very welcome.

---

## Developing Without Docker

You can run services locally for faster iteration, but you still need infrastructure services (Postgres, Redis, Qdrant, MinIO, Ollama, etc.) available. Start them with Docker (`make up-infra`) and then run apps on the host.

### Backend (FastAPI + Celery)

```bash
cd backend
uv sync                    # install dependencies into .venv
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Celery worker (in a second shell):

```bash
cd backend
uv run celery -A app.workers.celery_app worker --loglevel=info
uv run celery -A app.workers.celery_app beat --loglevel=info   # for scheduled jobs
```

Ensure your environment variables match the infra endpoints (e.g., `DATABASE_URL=postgresql+asyncpg://legalease:legalease@localhost:5432/legalease`).

### Frontend (Nuxt 4)

```bash
cd frontend
pnpm install
NUXT_PUBLIC_API_BASE=http://localhost:8000 pnpm dev
```

### Landing Docs

The marketing/docs site under `landing/` uses Nuxt Content:

```bash
cd landing
pnpm install
pnpm dev
```

---

## Testing & Linting

- Backend: `docker compose exec backend pytest`, or locally `uv run pytest`.
- Linting: Ruff config lives in `pyproject.toml`; run `uv run ruff check backend/app`.
- Frontend: Nuxt ESLint is enabled (`pnpm lint`). There is currently no automated unit test suite for the dashboard.

---

## Documentation

- Product docs are maintained under `landing/content` and surfaced via the landing site.
- `RESET.md` documents how to rebuild the dataset with sample PDFs and audio.
- API schema is available at `/api/docs` once the backend is running.

---

## Contributing

Open issues or pull requests are welcome. Please keep doc updates scoped and factual—many features are evolving and we want the documentation to stay honest about current behaviour. For larger changes, start a discussion in the issue tracker.

---

## License

MIT License. See [`LICENSE`](LICENSE) for details.
