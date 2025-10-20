# LegalEase Backend v2 - Quick Start

Get up and running in 5 minutes!

## Prerequisites

- Python 3.11+ (managed by mise)
- Docker and Docker Compose
- mise (task runner)

## Setup (One Command)

```bash
cd /home/Allie/develop/legalease/backend

# Trust mise configuration
mise trust

# Configure environment
cp .env.example .env
# Edit .env if needed (defaults work for local development)

# Start infrastructure services
docker-compose up -d

# Run full setup
mise run setup
```

This will:
1. Install all dependencies (30-60 seconds)
2. Run database migrations (5-10 seconds)
3. Initialize infrastructure (10-20 seconds)

## Start Development

```bash
# Terminal 1: API server
mise run dev

# Terminal 2: Celery worker
mise run worker
```

Access the API at: http://localhost:8000

## Verify Everything Works

```bash
# Check health
curl http://localhost:8000/api/v2/health/detailed

# Or use mise task
mise run health:check

# Run tests
mise run test:unit
```

## Next Steps

- **API Documentation**: http://localhost:8000/api/docs
- **Flower (Celery monitoring)**: `mise run flower` → http://localhost:5555
- **Integration Guide**: See `README_INTEGRATION.md`
- **Deployment Guide**: See `DEPLOYMENT.md`

## Common Commands

```bash
mise run dev              # Start API
mise run worker           # Start worker
mise run test             # Run tests
mise run format           # Format code
mise run lint             # Lint code
mise run health:check     # Check services
```

## Troubleshooting

**Services not starting?**
```bash
mise run docker:up
mise run docker:ps
```

**Database errors?**
```bash
mise run migrate
```

**Need to reset?**
```bash
mise run db:reset
```

## Documentation

- `README_INTEGRATION.md` - Detailed integration guide
- `DEPLOYMENT.md` - Production deployment
- `INTEGRATION_SUMMARY.md` - What was created
- `.env.example` - Configuration reference

---

**You're ready to develop!** 🚀
