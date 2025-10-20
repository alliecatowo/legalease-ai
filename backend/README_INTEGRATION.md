# Integration & Testing Setup - Quick Start

This document provides a quick reference for setting up and testing the LegalEase Backend v2 integration.

## Quick Start

### 1. One-Command Setup

```bash
# Full setup: dependencies + migrations + infrastructure
mise run setup
```

This will:
1. Install all Python dependencies via `uv sync`
2. Run database migrations via Alembic
3. Initialize infrastructure (OpenSearch, Qdrant, Neo4j)

### 2. Manual Setup

If you prefer step-by-step:

```bash
# Install dependencies
mise run install

# Run migrations
mise run migrate

# Initialize infrastructure
mise run init
```

## Running Tests

### All Tests

```bash
mise run test
```

### Unit Tests Only (Fast)

```bash
mise run test:unit
```

### Integration Tests (Requires Services)

```bash
# Ensure services are running
mise run docker:up

# Run integration tests
mise run test:integration
```

### Test Coverage

```bash
mise run test:coverage
```

## Development Workflow

### Start Development Server

```bash
# Terminal 1: API server
mise run dev

# Terminal 2: Celery worker
mise run worker

# Terminal 3: Celery beat (optional)
mise run beat

# Terminal 4: Flower monitoring (optional)
mise run flower
```

### Using Docker Compose

```bash
# Start all services
mise run docker:up

# View logs
mise run docker:logs

# Stop all services
mise run docker:down
```

## Health Checks

### Quick Health Check

```bash
curl http://localhost:8000/health
```

### Detailed Health Check

```bash
mise run health:check

# Or manually:
curl http://localhost:8000/api/v2/health/detailed | jq
```

## Scripts Reference

All scripts are in the `scripts/` directory:

| Script | Purpose | Usage |
|--------|---------|-------|
| `setup_dependencies.sh` | Install Python deps | `./scripts/setup_dependencies.sh` |
| `run_migrations.sh` | Run DB migrations | `./scripts/run_migrations.sh` |
| `init_infrastructure.py` | Initialize services | `./scripts/init_infrastructure.py` |

## File Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── v1/           # Original API
│   │   └── v2/           # New deep research API
│   │       ├── routes/
│   │       │   ├── health.py       # Health checks
│   │       │   ├── research.py     # Research endpoints
│   │       │   ├── evidence.py     # Evidence search
│   │       │   └── graph.py        # Knowledge graph
│   │       ├── schemas/
│   │       └── websockets/
│   ├── application/      # Use cases & handlers
│   ├── domain/          # Business logic
│   └── infrastructure/  # External integrations
│       ├── pipelines/   # Haystack pipelines
│       ├── agents/      # LangGraph agents
│       ├── workflows/   # Temporal workflows
│       └── persistence/ # Stores & repositories
├── tests/
│   ├── unit/            # Fast unit tests
│   │   ├── test_haystack_components.py
│   │   └── test_langgraph_agents.py
│   └── integration/     # Integration tests
│       ├── conftest.py
│       └── test_deep_research_workflow.py
├── scripts/
│   ├── setup_dependencies.sh
│   ├── run_migrations.sh
│   └── init_infrastructure.py
├── mise.toml            # Task runner config
├── pytest.ini           # Test configuration
├── .env.example         # Environment template
└── DEPLOYMENT.md        # Deployment guide
```

## Common Tasks

### Add a New Migration

```bash
mise run migrate-create -- "description of changes"
```

### Reset Database

```bash
mise run db:reset
```

### View All Routes

```bash
mise run routes
```

### Format Code

```bash
mise run format
```

### Lint Code

```bash
mise run lint
```

### Type Check

```bash
mise run typecheck
```

### Run All Validations

```bash
mise run validate
```

## Troubleshooting

### Services Not Starting

```bash
# Check service status
mise run docker:ps

# View logs
mise run docker:logs

# Restart specific service
docker-compose restart <service-name>
```

### Migration Errors

```bash
# Check current migration version
alembic current

# View migration history
alembic history

# Rollback if needed
alembic downgrade -1
```

### Dependency Issues

```bash
# Clean and reinstall
rm -rf .venv
mise run install
```

### Permission Issues

```bash
# Make scripts executable
chmod +x scripts/*.sh scripts/*.py
```

## Environment Variables

Key variables to configure in `.env`:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://legalease:password@localhost:5432/legalease

# Vector Store
QDRANT_URL=http://localhost:6333

# Search
OPENSEARCH_URL=http://localhost:9200

# Knowledge Graph
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# LLM
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:latest

# Research
RESEARCH_MAX_CONCURRENT_AGENTS=4
RESEARCH_DEFAULT_TIMEOUT=14400
```

See `.env.example` for complete list.

## Next Steps

1. **Development**: Start with `mise run dev` and `mise run worker`
2. **Testing**: Run `mise run test:unit` to verify setup
3. **Integration**: Run `mise run test:integration` with services running
4. **Production**: See `DEPLOYMENT.md` for production deployment

## Getting Help

- Check `DEPLOYMENT.md` for detailed deployment guide
- Review `mise tasks ls` for all available commands
- Check service logs: `mise run docker:logs`
- Run health checks: `mise run health:check`

---

**Quick Reference Commands**:

```bash
# Setup
mise run setup              # Full setup

# Development
mise run dev                # Start API
mise run worker             # Start worker
mise run docker:up          # Start services

# Testing
mise run test               # All tests
mise run test:unit          # Unit tests
mise run test:integration   # Integration tests

# Utilities
mise run health:check       # Check health
mise run format             # Format code
mise run lint               # Lint code
mise run migrate            # Run migrations
```
