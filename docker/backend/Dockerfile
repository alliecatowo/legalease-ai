# Base stage with Python 3.11
FROM python:3.11-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    git \
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

# Install all dependencies including dev dependencies (but exclude worker group)
RUN uv sync --no-group worker

# Copy application code
COPY backend/ ./

# Expose FastAPI port
EXPOSE 8000

# Start development server with auto-reload
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production dependencies stage
FROM base AS dependencies

# Install production dependencies only (exclude worker group)
RUN uv sync --no-dev --no-group worker

# Production stage
FROM python:3.11-slim AS production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy installed dependencies from dependencies stage
COPY --from=dependencies /app/.venv /app/.venv

# Copy application code
COPY backend/ ./

# Create non-root user
RUN useradd -m -u 1000 legalease && chown -R legalease:legalease /app
USER legalease

# Expose production port
EXPOSE 8000

# Start production server
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
