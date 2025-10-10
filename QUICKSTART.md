# LegalEase Quick Start Guide

Get LegalEase up and running in minutes!

## Prerequisites

Before you begin, ensure you have:

- **mise** - Tool version manager ([install here](https://mise.jdx.dev/getting-started.html))
- **Docker** - For running services ([install here](https://docs.docker.com/get-docker/))
- **Git** - Version control

## Installation

### Step 1: Install mise (if not already installed)

```bash
curl https://mise.run | sh
```

Follow the instructions to add mise to your shell.

### Step 2: Run the setup script

```bash
cd /home/Allie/develop/legalease
./scripts/setup.sh
```

This will:
- Install Node.js, pnpm, Python, and Poetry
- Start Docker services (PostgreSQL, Redis, Qdrant, MinIO, Neo4j, Ollama)
- Install frontend and backend dependencies
- Initialize the database
- Optionally download AI models

### Step 3: Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and update any values as needed. At minimum, change:
- `SECRET_KEY` - Generate with: `openssl rand -hex 32`

### Step 4: Run database migrations

```bash
mise run db-migrate
```

### Step 5: Create default data

```bash
python scripts/init_db.py
```

This creates:
- Default roles (admin, lawyer, client)
- Admin user:
  - Email: `admin@legalease.com`
  - Password: `admin123`
  - **Change this password after first login!**

## Running LegalEase

### Start all services

```bash
# Start Docker services
mise run up

# In separate terminal windows:
mise run dev-frontend   # Frontend at http://localhost:3000
mise run dev-backend    # Backend at http://localhost:8000
mise run dev-worker     # Celery worker
```

### Access the application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (admin/minioadmin)
- **Neo4j Browser**: http://localhost:7474 (neo4j/password)

## Available Commands

View all available mise tasks:
```bash
mise tasks
```

### Development Tasks

```bash
mise run dev-frontend   # Start Nuxt dev server
mise run dev-backend    # Start FastAPI with auto-reload
mise run dev-worker     # Start Celery worker
```

### Docker Tasks

```bash
mise run up      # Start all services
mise run down    # Stop all services
mise run logs    # View service logs
mise run build   # Rebuild Docker images
```

### Database Tasks

```bash
mise run db-migrate   # Apply migrations
mise run db-rollback  # Rollback last migration
```

### AI Models

```bash
mise run download-models  # Download all AI models
```

## Project Structure

```
legalease/
├── frontend/           # Nuxt 3 frontend application
├── backend/            # FastAPI backend application
├── scripts/            # Setup and utility scripts
├── models/             # Downloaded AI models
├── .mise.toml          # Mise configuration
├── .env.example        # Environment variables template
├── docker-compose.yml  # Docker services configuration
└── QUICKSTART.md       # This file
```

## Troubleshooting

### Services not starting

Check Docker status:
```bash
docker compose ps
```

View logs:
```bash
mise run logs
```

### Database connection errors

Ensure PostgreSQL is running:
```bash
docker compose ps postgres
```

Reset database (warning: destroys data):
```bash
docker compose down -v
mise run up
mise run db-migrate
python scripts/init_db.py
```

### Frontend build errors

Clear cache and reinstall:
```bash
cd frontend
rm -rf node_modules .nuxt .output
pnpm install
```

### Backend dependency issues

Reinstall dependencies:
```bash
cd backend
poetry install
```

### AI models not working

Verify Ollama is running:
```bash
curl http://localhost:11434/api/version
```

Download models:
```bash
mise run download-models
```

## Development Workflow

1. **Start services**:
   ```bash
   mise run up
   ```

2. **Start development servers** (in separate terminals):
   ```bash
   mise run dev-frontend
   mise run dev-backend
   mise run dev-worker
   ```

3. **Make changes** to code - servers will auto-reload

4. **Run migrations** when database schema changes:
   ```bash
   cd backend
   poetry run alembic revision --autogenerate -m "description"
   mise run db-migrate
   ```

5. **Commit changes**:
   ```bash
   git add .
   git commit -m "Your commit message"
   ```

## Next Steps

- Read the full documentation in `README.md`
- Check out the API documentation at http://localhost:8000/docs
- Review the frontend components in `frontend/components/`
- Explore the backend API routes in `backend/app/api/`
- Configure AI models in `.env`

## Getting Help

- Check the main `README.md` for detailed documentation
- Review `scripts/README.md` for script documentation
- Check `.env.example` for all configuration options
- View logs: `mise run logs`

## Important Notes

- **Never commit `.env`** - it contains secrets
- **Change default passwords** in production
- **Download models** before using AI features
- **Run migrations** after pulling database changes

Happy coding!
