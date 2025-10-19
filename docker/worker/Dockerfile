# Base stage with Python 3.11
FROM python:3.11-slim AS base

# Install system dependencies (no CUDA - PyTorch bundles it)
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    git \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    ffmpeg \
    ca-certificates \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY backend/pyproject.toml backend/uv.lock* ./

# Development stage
FROM base AS development

# Install dependencies FIRST (cached layer - only rebuilds when pyproject.toml or uv.lock changes)
# Use BuildKit cache mount to persist downloaded packages across builds
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --group worker

# Copy application code SECOND (changes frequently)
COPY backend/ ./

# Install project itself LAST (fast - just links the project into the venv)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --group worker

# Create cache directory for models
RUN mkdir -p /root/.cache

# Set environment variables
ENV LD_LIBRARY_PATH=/app/.venv/lib/python3.11/site-packages/nvidia/cudnn/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/cublas/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/cuda_runtime/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/cusparse/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/cufft/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/curand/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/cusolver/lib

# Configure Tesseract language data path
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

# Create CuDNN library symlinks for version compatibility
RUN for lib_dir in cudnn cublas cuda_runtime cusparse cufft curand cusolver; do \
        if [ -d /app/.venv/lib/python3.11/site-packages/nvidia/$lib_dir/lib ]; then \
            cd /app/.venv/lib/python3.11/site-packages/nvidia/$lib_dir/lib; \
            for f in *.so.9; do \
                if [ -f "$f" ]; then \
                    ln -sf "$f" "${f}.1.0" && ln -sf "$f" "${f}.1"; \
                fi; \
            done; \
        fi; \
    done 2>/dev/null || true

# Start Celery worker
CMD ["uv", "run", "celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info", "--concurrency=2"]

# Production dependencies stage
FROM base AS dependencies

# Install production dependencies with worker group (dependencies only, not the project)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --group worker

# Production stage
FROM python:3.11-slim AS production

# Install runtime dependencies (no CUDA - PyTorch bundles it)
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    git \
    ffmpeg \
    ca-certificates \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first
COPY backend/pyproject.toml backend/uv.lock ./

# Copy installed dependencies from dependencies stage
COPY --from=dependencies /app/.venv /app/.venv

# Copy application code
COPY backend/ ./

# Install project itself (fast - just links)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --group worker

# Create non-root user
RUN useradd -m -u 1000 legalease && \
    mkdir -p /home/legalease/.cache && \
    chown -R legalease:legalease /app /home/legalease/.cache

USER legalease

# Set cache directory
ENV HOME=/home/legalease

# Set environment variables
ENV LD_LIBRARY_PATH=/app/.venv/lib/python3.11/site-packages/nvidia/cudnn/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/cublas/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/cuda_runtime/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/cusparse/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/cufft/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/curand/lib:\
/app/.venv/lib/python3.11/site-packages/nvidia/cusolver/lib

# Configure Tesseract language data path
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

# Create CuDNN library symlinks for version compatibility
RUN for lib_dir in cudnn cublas cuda_runtime cusparse cufft curand cusolver; do \
        if [ -d /app/.venv/lib/python3.11/site-packages/nvidia/$lib_dir/lib ]; then \
            cd /app/.venv/lib/python3.11/site-packages/nvidia/$lib_dir/lib; \
            for f in *.so.9; do \
                if [ -f "$f" ]; then \
                    ln -sf "$f" "${f}.1.0" && ln -sf "$f" "${f}.1"; \
                fi; \
            done; \
        fi; \
    done 2>/dev/null || true

# Start Celery worker with optimized settings
CMD ["uv", "run", "celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info", "--concurrency=4", "--max-tasks-per-child=100"]
