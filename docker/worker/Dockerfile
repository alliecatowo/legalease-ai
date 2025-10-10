# Base stage with Python 3.11
FROM python:3.11-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY backend/pyproject.toml backend/uv.lock* ./

# Development stage
FROM base AS development

# Install all dependencies including dev dependencies
RUN uv sync

# Copy application code
COPY backend/ ./

# Create cache directory for models
RUN mkdir -p /root/.cache

# Start Celery worker
CMD ["uv", "run", "celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info", "--concurrency=2"]

# Production dependencies stage
FROM base AS dependencies

# Install production dependencies only
RUN uv sync --no-dev

# Production stage
FROM python:3.11-slim AS production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy installed dependencies from dependencies stage
COPY --from=dependencies /app/.venv /app/.venv

# Copy application code
COPY backend/ ./

# Create non-root user
RUN useradd -m -u 1000 legalease && \
    mkdir -p /home/legalease/.cache && \
    chown -R legalease:legalease /app /home/legalease/.cache

USER legalease

# Set cache directory
ENV HOME=/home/legalease

# Start Celery worker with optimized settings
CMD ["uv", "run", "celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info", "--concurrency=4", "--max-tasks-per-child=100"]
