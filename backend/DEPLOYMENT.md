# LegalEase Backend - Deployment Guide

This guide covers deploying LegalEase Backend v2 with the new deep research capabilities.

## Table of Contents

- [Infrastructure Requirements](#infrastructure-requirements)
- [Environment Setup](#environment-setup)
- [Installation](#installation)
- [Database Migrations](#database-migrations)
- [Infrastructure Initialization](#infrastructure-initialization)
- [Running the Application](#running-the-application)
- [Migration Guide (v1 to v2)](#migration-guide-v1-to-v2)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Rollback Procedures](#rollback-procedures)

## Infrastructure Requirements

### Required Services

| Service | Version | Purpose | Port |
|---------|---------|---------|------|
| PostgreSQL | 14+ | Primary database | 5432 |
| Redis | 7+ | Cache & Celery broker | 6379 |
| Qdrant | 1.14+ | Vector search | 6333 |
| OpenSearch | 2.7+ | BM25 keyword search | 9200 |
| Neo4j | 5.x | Knowledge graph | 7687 |
| MinIO | Latest | Object storage | 9000 |

### Optional Services

| Service | Version | Purpose | Port |
|---------|---------|---------|------|
| Temporal | 1.8+ | Workflow orchestration | 7233 |
| Ollama | Latest | Local LLM inference | 11434 |

### Hardware Requirements

**Minimum (Development)**:
- CPU: 4 cores
- RAM: 16GB
- Storage: 50GB SSD
- GPU: Optional (CPU inference possible)

**Recommended (Production)**:
- CPU: 8+ cores
- RAM: 32GB+
- Storage: 200GB+ SSD
- GPU: NVIDIA GPU with 8GB+ VRAM (for faster inference)

## Environment Setup

### 1. Clone and Install Dependencies

```bash
cd /home/Allie/develop/legalease/backend

# Install Python dependencies
mise run install

# Install dev dependencies
mise run install-dev

# Install worker dependencies (for transcription)
mise run install-worker
```

### 2. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit with your settings
vim .env
```

**Critical Variables**:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://legalease:password@localhost:5432/legalease

# Redis
REDIS_URL=redis://localhost:6379/0

# Qdrant
QDRANT_URL=http://localhost:6333

# OpenSearch
OPENSEARCH_URL=http://localhost:9200

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# Temporal (optional)
TEMPORAL_HOST=localhost:7233
TEMPORAL_NAMESPACE=legalease

# Ollama (optional)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:latest
```

### 3. Start Infrastructure Services

Using Docker Compose:

```bash
# Start all services
mise run docker:up

# Or start individually
docker-compose up -d postgres redis qdrant opensearch neo4j minio

# Optional services
docker-compose up -d temporal ollama
```

Verify services are running:

```bash
mise run docker:ps
```

## Installation

### Quick Setup (All in One)

```bash
# Full setup: dependencies + migrations + infrastructure
mise run setup
```

### Manual Setup

```bash
# 1. Install dependencies
mise run install

# 2. Run database migrations
mise run migrate

# 3. Initialize infrastructure (indexes, collections, schema)
mise run init
```

## Database Migrations

### Running Migrations

```bash
# Upgrade to latest
mise run migrate

# Or use the script directly
./scripts/run_migrations.sh
```

### Creating New Migrations

```bash
# Auto-generate migration from model changes
mise run migrate-create -- "description of changes"

# Example
mise run migrate-create -- "add research_run table"
```

### Migration History

```bash
# View current version
alembic current

# View migration history
alembic history

# Upgrade to specific version
alembic upgrade <revision>

# Downgrade
alembic downgrade -1  # one step back
alembic downgrade <revision>  # to specific version
```

## Infrastructure Initialization

The initialization script creates:

1. **OpenSearch Indexes**:
   - `legalease_documents` - Document chunks
   - `legalease_transcripts` - Transcript segments

2. **Qdrant Collections**:
   - `legalease_documents` - Document embeddings
   - `legalease_transcripts` - Transcript embeddings

3. **Neo4j Schema**:
   - Constraints for uniqueness
   - Indexes for performance

```bash
# Run initialization
mise run init

# Or run script directly
python scripts/init_infrastructure.py
```

**Verify Initialization**:

```bash
# Check health of all services
mise run health:check

# Or manually:
curl http://localhost:8000/api/v2/health/detailed
```

## Running the Application

### Development Mode

```bash
# Start API server with hot reload
mise run dev

# Start Celery worker (in another terminal)
mise run worker

# Start Celery beat scheduler (in another terminal)
mise run beat

# Optional: Start Flower for monitoring
mise run flower
```

### Production Mode

```bash
# Start API server (4 workers)
mise run start

# Start Celery worker with autoscaling
mise run worker

# Start Celery beat
mise run beat
```

### Using Docker Compose

```bash
# Start all services including API and workers
docker-compose up -d

# View logs
docker-compose logs -f api worker

# Stop all services
docker-compose down
```

### Temporal Workflows (Optional)

```bash
# Terminal 1: Start Temporal server (dev mode)
mise run temporal

# Terminal 2: Start Temporal worker
mise run temporal:worker

# Terminal 3: Start API
mise run dev
```

## Migration Guide (v1 to v2)

### Overview

v2 introduces:
- Deep research workflows with multi-agent systems
- Hybrid search (semantic + keyword)
- Knowledge graph capabilities
- Temporal workflow orchestration

### Pre-Migration Checklist

- [ ] Backup existing database
- [ ] Backup Qdrant collections
- [ ] Document current environment variables
- [ ] Test rollback procedure
- [ ] Schedule maintenance window

### Migration Steps

#### 1. Backup Data

```bash
# Backup PostgreSQL
pg_dump -h localhost -U legalease legalease > backup_$(date +%Y%m%d).sql

# Backup Qdrant collections
# Use Qdrant snapshots API or export data programmatically

# Backup MinIO buckets
mc mirror legalease/legalease backup/minio/
```

#### 2. Update Codebase

```bash
cd /home/Allie/develop/legalease/backend
git pull origin feat/deep-research
```

#### 3. Update Dependencies

```bash
mise run install
```

#### 4. Update Environment Variables

Add new v2 variables to `.env`:

```bash
# OpenSearch
OPENSEARCH_URL=http://localhost:9200

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Temporal
TEMPORAL_HOST=localhost:7233
TEMPORAL_NAMESPACE=legalease

# Research
RESEARCH_MAX_CONCURRENT_AGENTS=4
RESEARCH_DEFAULT_TIMEOUT=14400
```

#### 5. Start New Services

```bash
# Start OpenSearch
docker-compose up -d opensearch

# Start Neo4j
docker-compose up -d neo4j

# Optional: Start Temporal
docker-compose up -d temporal
```

#### 6. Run Migrations

```bash
mise run migrate
```

#### 7. Initialize New Infrastructure

```bash
mise run init
```

#### 8. Restart Application

```bash
# Stop old version
docker-compose down api worker

# Start new version
docker-compose up -d api worker
```

#### 9. Verify Migration

```bash
# Check health
curl http://localhost:8000/api/v2/health/detailed

# Run integration tests
mise run test:integration

# Check logs
docker-compose logs api worker
```

### Data Migration (If Needed)

If you need to migrate existing data to new indexes:

```bash
# Re-index documents to OpenSearch
python scripts/reindex_opensearch.py

# Re-build knowledge graph
python scripts/rebuild_knowledge_graph.py
```

## Monitoring

### Health Checks

```bash
# Simple health check
curl http://localhost:8000/health

# Detailed health check
curl http://localhost:8000/api/v2/health/detailed

# Kubernetes probes
curl http://localhost:8000/api/v2/health/readiness
curl http://localhost:8000/api/v2/health/liveness
```

### Metrics

**Celery (Flower)**:
```bash
# Start Flower
mise run flower

# Access at: http://localhost:5555
```

**Temporal UI** (if using Temporal):
```bash
# Access at: http://localhost:8233
```

**Logs**:
```bash
# API logs
mise run logs:api

# Worker logs
mise run logs:worker

# All Docker logs
mise run docker:logs
```

## Troubleshooting

### Common Issues

#### 1. Services Not Starting

**Problem**: Database connection errors

```bash
# Check if PostgreSQL is running
docker-compose ps postgres
pg_isready -h localhost -U legalease

# Check logs
docker-compose logs postgres
```

**Problem**: Qdrant connection refused

```bash
# Check if Qdrant is running
curl http://localhost:6333/collections

# Restart Qdrant
docker-compose restart qdrant
```

#### 2. Migration Failures

**Problem**: Alembic migration fails

```bash
# Check current version
alembic current

# Check for conflicts
alembic heads

# If stuck, downgrade and retry
alembic downgrade -1
alembic upgrade head
```

#### 3. Infrastructure Initialization Fails

**Problem**: OpenSearch index creation fails

```bash
# Check OpenSearch logs
docker-compose logs opensearch

# Manually verify connection
curl http://localhost:9200/_cluster/health

# Delete and recreate indexes
curl -X DELETE http://localhost:9200/legalease_*
python scripts/init_infrastructure.py
```

#### 4. Memory Issues

**Problem**: Workers crashing due to OOM

```bash
# Reduce worker concurrency
export CELERY_WORKER_AUTOSCALE=2,1

# Reduce Ollama concurrency
export OLLAMA_MAX_CONCURRENT_REQUESTS=1

# Use smaller models
export OLLAMA_MODEL=llama3.2:1b
export WHISPER_MODEL=base
```

#### 5. Performance Issues

**Problem**: Slow search queries

```bash
# Check Qdrant collection status
curl http://localhost:6333/collections/legalease_documents

# Rebuild indexes if needed
curl -X POST http://localhost:6333/collections/legalease_documents/index

# Check Neo4j indexes
cypher-shell "SHOW INDEXES"
```

## Rollback Procedures

### Emergency Rollback

If v2 deployment fails, rollback to v1:

#### 1. Stop v2 Services

```bash
docker-compose down
```

#### 2. Restore Database

```bash
# Restore from backup
psql -h localhost -U legalease legalease < backup_YYYYMMDD.sql
```

#### 3. Checkout v1 Code

```bash
git checkout main  # or previous stable branch
```

#### 4. Downgrade Dependencies

```bash
mise run install
```

#### 5. Rollback Migrations

```bash
# Find previous migration revision
alembic history

# Downgrade to v1 schema
alembic downgrade <v1_revision>
```

#### 6. Restart v1 Services

```bash
docker-compose up -d postgres redis qdrant minio
docker-compose up -d api worker
```

#### 7. Verify Rollback

```bash
curl http://localhost:8000/health
mise run test:unit
```

### Partial Rollback

If only specific features fail:

**Disable Deep Research**:
```bash
# In .env
RESEARCH_ENABLE_STREAMING=false

# Restart API
docker-compose restart api
```

**Disable Temporal Workflows**:
```bash
# Stop Temporal worker
docker-compose stop temporal-worker

# API will fallback to direct execution
```

**Disable Knowledge Graph**:
```bash
# Stop Neo4j
docker-compose stop neo4j

# Features using graph will gracefully degrade
```

## Production Best Practices

### Security

- [ ] Use strong passwords for all services
- [ ] Enable SSL/TLS for production
- [ ] Use secrets management (Vault, AWS Secrets Manager)
- [ ] Enable authentication on OpenSearch
- [ ] Use network policies to isolate services

### Performance

- [ ] Use connection pooling for databases
- [ ] Enable Redis persistence
- [ ] Configure Qdrant for production (replicas, persistence)
- [ ] Use CDN for static assets
- [ ] Enable response caching

### Reliability

- [ ] Set up automated backups
- [ ] Configure health check alerts
- [ ] Use container orchestration (Kubernetes)
- [ ] Implement circuit breakers
- [ ] Set up log aggregation

### Monitoring

- [ ] Set up Prometheus metrics
- [ ] Configure Grafana dashboards
- [ ] Enable distributed tracing (Jaeger)
- [ ] Set up error tracking (Sentry)
- [ ] Configure uptime monitoring

## Support

For issues or questions:

1. Check the [troubleshooting guide](#troubleshooting)
2. Review logs: `mise run docker:logs`
3. Run health checks: `mise run health:check`
4. Check integration tests: `mise run test:integration`

## Changelog

### v2.0.0 (Deep Research Release)

**New Features**:
- Multi-agent deep research system
- Hybrid search (semantic + keyword)
- Knowledge graph with Neo4j
- Temporal workflow orchestration
- Streaming research results via WebSocket

**Infrastructure**:
- Added OpenSearch for BM25 search
- Added Neo4j for knowledge graph
- Added Temporal for workflow orchestration
- Enhanced Qdrant integration

**API Changes**:
- New v2 API endpoints (`/api/v2/*`)
- WebSocket endpoint for research streaming
- Enhanced health check endpoints

**Breaking Changes**:
- None (v1 API remains backward compatible)

---

Last updated: 2025-10-19
