# Base stage with Python 3.11
FROM python:3.11-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_VERSION=1.8.3
ENV POETRY_HOME=/opt/poetry
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=false
ENV POETRY_VIRTUALENVS_CREATE=false

RUN curl -sSL https://install.python-poetry.org | python3 - && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry

# Set working directory
WORKDIR /app

# Copy dependency files
COPY backend/pyproject.toml backend/poetry.lock* ./

# Development stage
FROM base AS development

# Install all dependencies including dev dependencies
RUN poetry install --no-root

# Copy application code
COPY backend/ ./

# Create cache directory for models
RUN mkdir -p /root/.cache

# Start Celery worker
CMD ["celery", "-A", "app.worker", "worker", "--loglevel=info", "--concurrency=2"]

# Production dependencies stage
FROM base AS dependencies

# Install production dependencies only
RUN poetry install --no-root --only main

# Production stage
FROM python:3.11-slim AS production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed dependencies from dependencies stage
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

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
CMD ["celery", "-A", "app.worker", "worker", "--loglevel=info", "--concurrency=4", "--max-tasks-per-child=100"]
