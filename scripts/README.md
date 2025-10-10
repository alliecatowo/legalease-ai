# LegalEase Setup Scripts

This directory contains scripts to set up and manage the LegalEase development environment.

## Scripts Overview

### setup.sh
**Purpose**: Complete development environment setup

**What it does**:
- Checks for mise installation
- Installs project tools (Node.js, pnpm, Python, Poetry)
- Starts Docker services
- Installs frontend and backend dependencies
- Initializes the database
- Optionally downloads AI models

**Usage**:
```bash
./scripts/setup.sh
```

### download_models.sh
**Purpose**: Download AI/ML models required by LegalEase

**What it does**:
- Pulls Ollama models:
  - `llama3.1:70b` - General legal reasoning and document analysis
  - `nuextract` - Structured data extraction
  - `llava:13b` - Video and image analysis
- Downloads Whisper models (base and medium) for audio transcription
- Downloads BGE-base-en embedding model for semantic search
- Optionally downloads legal-specific models

**Usage**:
```bash
./scripts/download_models.sh
# Or using mise:
mise run download-models
```

**Note**: This script may take a while to complete as models are large.

### init_db.py
**Purpose**: Initialize the PostgreSQL database

**What it does**:
- Waits for PostgreSQL to be ready
- Creates the database if it doesn't exist
- Creates default roles and admin user
- Should be run after Alembic migrations

**Usage**:
```bash
python scripts/init_db.py
```

**Default credentials**:
- Email: `admin@legalease.com`
- Password: `admin123`
- **Important**: Change the password after first login!

## Quick Start

1. **First-time setup**:
   ```bash
   ./scripts/setup.sh
   ```

2. **Download AI models** (if skipped during setup):
   ```bash
   mise run download-models
   ```

3. **Initialize database** (after migrations):
   ```bash
   python scripts/init_db.py
   ```

## Requirements

- **mise**: Tool version manager ([installation guide](https://mise.jdx.dev/getting-started.html))
- **Docker**: For running services
- **Git**: Version control

## Troubleshooting

### mise not found
Install mise first:
```bash
curl https://mise.run | sh
```

### Docker not running
Start Docker Desktop or Docker daemon:
```bash
sudo systemctl start docker  # Linux
# or start Docker Desktop on macOS/Windows
```

### PostgreSQL connection errors
Ensure Docker services are running:
```bash
mise run up
docker compose ps
```

### Model download failures
Check Ollama is running:
```bash
curl http://localhost:11434/api/version
```

If not running:
```bash
docker compose up -d ollama
```

## Environment Variables

All environment variables are documented in `.env.example`. Copy it to `.env` and update the values:

```bash
cp .env.example .env
```

Key variables to configure:
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT secret (generate with: `openssl rand -hex 32`)
- `OLLAMA_BASE_URL` - Ollama API endpoint
- `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` - Object storage credentials

## Development Workflow

1. **Start services**:
   ```bash
   mise run up
   ```

2. **Run migrations**:
   ```bash
   mise run db-migrate
   ```

3. **Start development servers**:
   ```bash
   # In separate terminals:
   mise run dev-frontend   # Frontend on :3000
   mise run dev-backend    # Backend on :8000
   mise run dev-worker     # Celery worker
   ```

4. **View logs**:
   ```bash
   mise run logs
   ```

5. **Stop services**:
   ```bash
   mise run down
   ```

## Available Mise Tasks

Run `mise tasks` to see all available tasks:

- `dev-frontend` - Start Nuxt development server
- `dev-backend` - Start FastAPI with auto-reload
- `dev-worker` - Start Celery worker
- `up` - Start all Docker services
- `down` - Stop all Docker services
- `logs` - View Docker logs
- `build` - Build Docker images
- `db-migrate` - Apply database migrations
- `db-rollback` - Rollback last migration
- `download-models` - Download AI models

## Model Storage

Models are stored in the following locations:

- **Ollama models**: `~/.ollama/models` (or Docker volume)
- **Whisper models**: `./models/whisper`
- **Embedding models**: `./models/embeddings`

## Support

For issues or questions:
1. Check the main README.md
2. Review logs: `mise run logs`
3. Check service status: `docker compose ps`
4. Verify environment variables in `.env`
