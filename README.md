# LegalEase

**World-class AI-powered legal document search and analysis platform**

LegalEase is a comprehensive, self-hosted platform for legal professionals to search, analyze, and manage documents with advanced AI capabilities. Built with privacy and security as top priorities, it runs entirely on your local infrastructure with no external API dependencies.

## ✨ Key Features

### 🔍 Hybrid Search Engine
- **BM25 + Semantic Search**: Combines traditional keyword search with AI-powered semantic understanding
- **Document Highlighting**: Click search results to jump directly to relevant sections in PDFs
- **Real-time Search**: Instant results as you type with <100ms latency
- **Advanced Filters**: Filter by case, document type, date range, entities, and tags

### 📁 Case-Based Organization
- **Load/Unload Cases**: Control which cases are actively searchable while preserving all files
- **Bulk Upload**: Drag-and-drop multiple files with progress tracking
- **Case Management**: Create, archive, and delete cases with full metadata tracking
- **Status Tracking**: Monitor processing status and storage usage per case

### 🎙️ AI Transcription
- **Speaker Diarization**: Automatically identify and label different speakers (Speaker 1, 2, 3...)
- **Word-Level Timestamps**: Precise timing for every word with millisecond accuracy
- **Audio Sync**: Click transcript segments to jump to exact audio position
- **Export Options**: DOCX (formatted), SRT/VTT subtitles, JSON
- **70x Real-Time**: Process 1 hour of audio in ~50 seconds

### 🤖 AI-Powered Analysis
- **Auto-Summarization**: LLM-generated summaries for documents and transcripts
- **Entity Extraction**: Identify parties, dates, amounts, citations, courts using GLiNER + LexNLP
- **Smart Tagging**: Automatic categorization and tagging of document types
- **Knowledge Graphs**: Visualize entity relationships and citation networks using Neo4j

### 🎨 Beautiful UI
- **Nuxt 4 + Nuxt UI 4**: Modern Vue.js interface with instant search
- **PDF Viewer**: Native PDF rendering with search term highlighting
- **Responsive Design**: Works seamlessly on desktop and mobile
- **Dark/Light Modes**: Automatic theme switching

### 🔒 Privacy & Security
- **100% Local**: All processing happens on your hardware
- **No External APIs**: Uses local Ollama models (Llama 3.1 70B)
- **Data Isolation**: PostgreSQL + MinIO + Qdrant for complete data control
- **Audit Logging**: Track all operations and access
- **Encrypted Storage**: Optional disk encryption support

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Services      │
│   (Nuxt 4)      │◄──►│   (FastAPI)     │◄──►│   (Docker)      │
│                 │    │                 │    │                 │
│ • Search UI     │    │ • REST API      │    │ • PostgreSQL    │
│ • PDF Viewer    │    │ • Case Mgmt     │    │ • Qdrant        │
│ • Case Mgmt     │    │ • File Upload   │    │ • MinIO         │
│ • Transcripts   │    │ • Search API    │    │ • Redis         │
│ • Knowledge Viz │    │ • AI Services   │    │ • Neo4j         │
└─────────────────┘    └─────────────────┘    │ • Ollama        │
                                              └─────────────────┘
```

## 🚀 Performance Targets

- **Search Latency**: <100ms for 95th percentile
- **Document Processing**: <1 minute per 100-page PDF
- **Transcription**: ~70x real-time (1 hour audio → 50 seconds)
- **UI Responsiveness**: <16ms for interactions (60fps)
- **Memory Usage**: <8GB RAM for backend services
- **Disk Usage**: ~2x original file size (embeddings + indexes)

## Prerequisites

- Docker Engine 24.0+ and Docker Compose V2
- Git
- Minimum 8GB RAM (16GB recommended)
- 20GB available disk space

## Quick Start with Docker

### Starting All Services

Start all services in detached mode:

```bash
docker compose up -d
```

Start specific services:

```bash
docker compose up -d postgres redis qdrant
```

View logs while starting:

```bash
docker compose up
```

### Stopping Services

Stop all services:

```bash
docker compose down
```

Stop and remove volumes (WARNING: deletes all data):

```bash
docker compose down -v
```

Stop specific services:

```bash
docker compose stop backend worker
```

### Viewing Logs

View all logs:

```bash
docker compose logs
```

Follow logs in real-time:

```bash
docker compose logs -f
```

View logs for specific service:

```bash
docker compose logs -f backend
```

View last 100 lines:

```bash
docker compose logs --tail=100 backend
```

### Rebuilding Services

Rebuild after code changes:

```bash
docker compose build
```

Rebuild specific service:

```bash
docker compose build backend
```

Force rebuild without cache:

```bash
docker compose build --no-cache
```

Rebuild and restart:

```bash
docker compose up -d --build
```

### Service Management

Restart a service:

```bash
docker compose restart backend
```

Execute commands in running container:

```bash
# Backend shell
docker compose exec backend bash

# Run database migrations
docker compose exec backend alembic upgrade head

# Run tests
docker compose exec backend pytest

# Frontend shell
docker compose exec frontend sh

# Redis CLI
docker compose exec redis redis-cli
```

### Checking Service Health

Check status of all services:

```bash
docker compose ps
```

Check resource usage:

```bash
docker stats
```

### Initial Setup

After starting services for the first time:

1. **Pull Ollama models** (if using LLM features):
```bash
docker compose exec ollama ollama pull llama3.1
docker compose exec ollama ollama pull nomic-embed-text
```

2. **Run database migrations**:
```bash
docker compose exec backend alembic upgrade head
```

3. **Create MinIO buckets**:
```bash
docker compose exec backend python -m app.scripts.setup_storage
```

4. **Initialize vector database**:
```bash
docker compose exec backend python -m app.scripts.setup_qdrant
```

## Port Mappings

| Service    | Port(s)      | Description                          |
|------------|--------------|--------------------------------------|
| Frontend   | 3000         | Nuxt.js application                  |
| Backend    | 8000         | FastAPI REST API                     |
| PostgreSQL | 5432         | Main database                        |
| Redis      | 6379         | Cache and message broker             |
| Qdrant     | 6333, 6334   | Vector database (HTTP, gRPC)         |
| MinIO      | 9000, 9001   | Object storage (API, Console)        |
| Neo4j      | 7474, 7687   | Graph database (HTTP, Bolt)          |
| Ollama     | 11434        | LLM inference server                 |

## Service URLs

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (legalease / legalease_dev_secret)
- **Neo4j Browser**: http://localhost:7474 (neo4j / legalease_dev)
- **Qdrant Dashboard**: http://localhost:6333/dashboard

## Environment Variables

Default development credentials are set in `docker-compose.yml`. For production:

1. Copy `.env.example` to `.env`
2. Update all passwords and secrets
3. Set `ENVIRONMENT=production`
4. Use `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`

## Development Workflow

### Hot Reload

Both frontend and backend support hot reload in development mode:

- **Frontend**: Changes to `frontend/` directory trigger automatic rebuild
- **Backend**: Changes to `backend/` directory trigger automatic reload (via `--reload` flag)

### Running Tests

Backend tests:

```bash
docker compose exec backend pytest
docker compose exec backend pytest -v --cov=app
```

Frontend tests:

```bash
docker compose exec frontend pnpm test
docker compose exec frontend pnpm test:unit
```

### Database Management

Access PostgreSQL:

```bash
docker compose exec postgres psql -U legalease -d legalease
```

Create migration:

```bash
docker compose exec backend alembic revision --autogenerate -m "description"
```

Apply migrations:

```bash
docker compose exec backend alembic upgrade head
```

Rollback migration:

```bash
docker compose exec backend alembic downgrade -1
```

### Celery Tasks

Monitor Celery worker:

```bash
docker compose logs -f worker
```

Inspect active tasks:

```bash
docker compose exec worker celery -A app.worker inspect active
```

Purge all tasks:

```bash
docker compose exec worker celery -A app.worker purge
```

## Troubleshooting

### Services won't start

Check logs:
```bash
docker compose logs
```

Check disk space:
```bash
df -h
```

Remove all containers and volumes:
```bash
docker compose down -v
docker system prune -a
```

### Database connection issues

Ensure PostgreSQL is healthy:
```bash
docker compose ps postgres
docker compose logs postgres
```

Reset database:
```bash
docker compose down
docker volume rm legalease-postgres-data
docker compose up -d postgres
```

### Out of memory

Increase Docker memory limit in Docker Desktop settings or adjust service memory limits in `docker-compose.yml`.

### Permission issues

Fix file permissions:
```bash
sudo chown -R $USER:$USER .
```

## Production Deployment

For production deployment:

1. Use separate `docker-compose.prod.yml`
2. Set strong passwords for all services
3. Enable TLS/SSL certificates
4. Configure proper backup strategy
5. Set up monitoring and logging
6. Use external managed databases for critical data
7. Enable GPU support for Ollama if available

## GPU Support (Optional)

To enable GPU acceleration for Ollama, uncomment the deploy section in `docker-compose.yml`:

```yaml
ollama:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

Requires:
- NVIDIA GPU
- NVIDIA Container Toolkit installed
- Docker with GPU support

## Architecture

```
┌─────────────┐     ┌─────────────┐
│  Frontend   │────▶│   Backend   │
│  (Nuxt 4)   │     │  (FastAPI)  │
└─────────────┘     └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         ┌─────────┐  ┌────────┐  ┌────────┐
         │PostgreSQL│  │ Redis  │  │ Celery │
         └─────────┘  └────────┘  │ Worker │
                                  └────────┘
              ▼            ▼            ▼
         ┌─────────┐  ┌────────┐  ┌────────┐
         │ Qdrant  │  │ MinIO  │  │ Neo4j  │
         └─────────┘  └────────┘  └────────┘
                           ▼
                      ┌────────┐
                      │ Ollama │
                      └────────┘
```

## License

MIT License - See LICENSE file for details
